from django.db.models import Q, F, Sum, Avg
from timb_dashboard.models import TobaccoGrade, Transaction
from merchant_app.models import MerchantInventory, CustomGrade
from merchant_app.models import AggregatedGrade
from decimal import Decimal
import pandas as pd
from datetime import datetime, timedelta
from django.utils import timezone

class TIMBGradeRecommendationEngine:
    """AI-powered purchase recommendations using official TIMB grades"""
    
    def __init__(self, merchant):
        self.merchant = merchant
        self.current_date = timezone.now()
        
    def get_purchase_recommendations(self):
        """Get comprehensive purchase recommendations"""
        recommendations = []
        
        # Analyze current inventory gaps
        inventory_recommendations = self._analyze_inventory_gaps()
        recommendations.extend(inventory_recommendations)
        
        # Analyze market trends
        market_recommendations = self._analyze_market_trends()
        recommendations.extend(market_recommendations)
        
        # Analyze custom grade requirements
        custom_grade_recommendations = self._analyze_custom_grade_needs()
        recommendations.extend(custom_grade_recommendations)
        
        # Analyze seasonal opportunities
        seasonal_recommendations = self._analyze_seasonal_opportunities()
        recommendations.extend(seasonal_recommendations)

        # Consider aggregated grades demand coverage vs inventory
        aggregated_recommendations = self._analyze_aggregated_grade_coverage()
        recommendations.extend(aggregated_recommendations)
        
        # Sort by priority and return top recommendations
        recommendations = sorted(recommendations, key=lambda x: x['priority_score'], reverse=True)
        return recommendations[:10]
    
    def _analyze_inventory_gaps(self):
        """Analyze current inventory for gaps in TIMB grades"""
        recommendations = []
        
        # Get current inventory
        current_inventory = MerchantInventory.objects.filter(
            merchant=self.merchant,
            quantity__gt=0
        ).select_related('grade')
        
        # Get inventory by category
        inventory_by_category = {}
        for item in current_inventory:
            category = item.grade.category
            if category not in inventory_by_category:
                inventory_by_category[category] = {
                    'total_quantity': 0,
                    'total_value': 0,
                    'grades': []
                }
            inventory_by_category[category]['total_quantity'] += item.quantity
            inventory_by_category[category]['total_value'] += item.quantity * item.average_cost
            inventory_by_category[category]['grades'].append(item.grade.grade_code)
        
        # Identify missing high-value categories
        essential_categories = ['PRIMING', 'LUG', 'LEAF']
        for category in essential_categories:
            if category not in inventory_by_category:
                # No inventory in this category - high priority
                top_grades = self._get_top_grades_in_category(category)
                for grade in top_grades[:3]:
                    recommendations.append({
                        'type': 'INVENTORY_GAP',
                        'grade': grade,
                        'reason': f'No {category.lower()} grades in inventory',
                        'recommended_quantity': 500,
                        'estimated_cost': float(grade.base_price * 500),
                        'priority_score': 9.0,
                        'potential_profit': float(grade.base_price * 500 * 0.15),
                        'risk_level': 'LOW'
                    })
        
        # Identify low inventory in existing categories
        for category, data in inventory_by_category.items():
            if data['total_quantity'] < 200:  # Low inventory threshold
                top_grades = self._get_top_grades_in_category(category, exclude=data['grades'])
                for grade in top_grades[:2]:
                    recommendations.append({
                        'type': 'LOW_INVENTORY',
                        'grade': grade,
                        'reason': f'Low inventory in {category.lower()} grades ({data["total_quantity"]}kg)',
                        'recommended_quantity': 300,
                        'estimated_cost': float(grade.base_price * 300),
                        'priority_score': 7.5,
                        'potential_profit': float(grade.base_price * 300 * 0.12),
                        'risk_level': 'LOW'
                    })
        
        return recommendations

    def _analyze_aggregated_grade_coverage(self):
        """Recommend base grades missing to realize recent aggregated outputs."""
        recommendations = []
        recent_outputs = AggregatedGrade.objects.filter(merchant=self.merchant).order_by('-computed_at')[:10]
        inv_map = {
            i.grade_id: i.quantity for i in MerchantInventory.objects.filter(merchant=self.merchant)
        }
        for agg in recent_outputs:
            for comp in agg.components.select_related('base_grade'):
                needed = float(comp.kilograms)
                have = float(inv_map.get(comp.base_grade_id, 0))
                if needed > 0 and have < needed:
                    short = max(0.0, needed - have)
                    recommendations.append({
                        'type': 'AGGREGATED_COMPONENT_GAP',
                        'grade': comp.base_grade,
                        'reason': f'Missing component for aggregated "{agg.name}"',
                        'recommended_quantity': int(short),
                        'estimated_cost': float(comp.base_grade.base_price) * short,
                        'priority_score': 8.2,
                        'risk_level': 'LOW',
                    })
        return recommendations
    
    def _analyze_market_trends(self):
        """Analyze market trends for TIMB grades"""
        recommendations = []
        
        # Get recent transaction data (last 30 days)
        recent_transactions = Transaction.objects.filter(
            timestamp__gte=self.current_date - timedelta(days=30)
        ).select_related('grade')
        
        # Analyze price trends
        grade_stats = {}
        for transaction in recent_transactions:
            grade_code = transaction.grade.grade_code
            if grade_code not in grade_stats:
                grade_stats[grade_code] = {
                    'prices': [],
                    'volumes': [],
                    'grade': transaction.grade
                }
            grade_stats[grade_code]['prices'].append(float(transaction.price_per_kg))
            grade_stats[grade_code]['volumes'].append(float(transaction.quantity))
        
        # Identify trending grades
        for grade_code, stats in grade_stats.items():
            if len(stats['prices']) >= 3:  # Minimum data points
                recent_prices = stats['prices'][-5:]  # Last 5 transactions
                avg_recent = sum(recent_prices) / len(recent_prices)
                base_price = float(stats['grade'].base_price)
                
                # Price above base price indicates strong demand
                if avg_recent > base_price * 1.1:
                    total_volume = sum(stats['volumes'])
                    recommendations.append({
                        'type': 'MARKET_TREND',
                        'grade': stats['grade'],
                        'reason': f'Strong market demand - trading {((avg_recent/base_price - 1) * 100):.1f}% above base price',
                        'recommended_quantity': min(400, int(total_volume * 0.1)),
                        'estimated_cost': float(stats['grade'].base_price * 400),
                        'priority_score': 8.5,
                        'potential_profit': float((avg_recent - base_price) * 400),
                        'risk_level': 'MEDIUM',
                        'market_price': avg_recent
                    })
        
        return recommendations
    
    def _analyze_custom_grade_needs(self):
        """Analyze needs for custom grade production"""
        recommendations = []
        
        # Get active custom grades
        try:
            custom_grades = CustomGrade.objects.filter(
                merchant=self.merchant,
                is_active=True
            ).prefetch_related('components__base_grade')
            
            for custom_grade in custom_grades:
                for component in custom_grade.components.all():
                    base_grade = component.base_grade
                    required_quantity = component.minimum_quantity or 100
                    
                    # Check current inventory of this base grade
                    try:
                        inventory = MerchantInventory.objects.get(
                            merchant=self.merchant,
                            grade=base_grade
                        )
                        current_stock = inventory.quantity
                    except MerchantInventory.DoesNotExist:
                        current_stock = 0
                    
                    # If stock is below requirement, recommend purchase
                    if current_stock < required_quantity:
                        needed_quantity = required_quantity - current_stock + 50  # Buffer
                        recommendations.append({
                            'type': 'CUSTOM_GRADE_COMPONENT',
                            'grade': base_grade,
                            'reason': f'Needed for custom grade "{custom_grade.custom_grade_name}" ({component.percentage}%)',
                            'recommended_quantity': needed_quantity,
                            'estimated_cost': float(base_grade.base_price * needed_quantity),
                            'priority_score': 8.0,
                            'potential_profit': float((custom_grade.target_price - base_grade.base_price) * needed_quantity * (component.percentage / 100)),
                            'risk_level': 'LOW',
                            'custom_grade': custom_grade.custom_grade_name
                        })
        except Exception as e:
            # Handle case where CustomGrade model doesn't exist yet
            print(f"CustomGrade model not available: {e}")
        
        return recommendations
    
    def _analyze_seasonal_opportunities(self):
        """Analyze seasonal opportunities in TIMB grades"""
        recommendations = []
        
        current_month = self.current_date.month
        
        # Seasonal grade opportunities
        seasonal_patterns = {
            # March-May: Harvest season - good time to buy priming and lug grades
            (3, 4, 5): {
                'categories': ['PRIMING', 'LUG'],
                'multiplier': 0.95,  # 5% discount during harvest
                'reason': 'Harvest season - favorable buying opportunity'
            },
            # June-August: Processing season - good for leaf grades
            (6, 7, 8): {
                'categories': ['LEAF', 'STRIP'],
                'multiplier': 1.0,
                'reason': 'Processing season - stable prices for processed grades'
            },
            # September-November: Export season - premium grades in demand
            (9, 10, 11): {
                'categories': ['PRIMING', 'LUG'],
                'multiplier': 1.1,  # 10% premium during export season
                'reason': 'Export season - high demand for premium grades'
            },
            # December-February: Planning season - good for bulk purchases
            (12, 1, 2): {
                'categories': ['LEAF', 'TIP', 'STRIP'],
                'multiplier': 0.98,
                'reason': 'Planning season - good bulk purchase opportunity'
            }
        }
        
        for months, pattern in seasonal_patterns.items():
            if current_month in months:
                for category in pattern['categories']:
                    top_grades = self._get_top_grades_in_category(category)
                    for grade in top_grades[:2]:
                        adjusted_price = grade.base_price * Decimal(str(pattern['multiplier']))
                        profit_potential = (grade.base_price - adjusted_price) * 300
                        
                        recommendations.append({
                            'type': 'SEASONAL_OPPORTUNITY',
                            'grade': grade,
                            'reason': pattern['reason'],
                            'recommended_quantity': 300,
                            'estimated_cost': float(adjusted_price * 300),
                            'priority_score': 6.5,
                            'potential_profit': float(profit_potential),
                            'risk_level': 'LOW',
                            'seasonal_adjustment': pattern['multiplier']
                        })
        
        return recommendations
    
    def _get_top_grades_in_category(self, category, exclude=None, limit=5):
        """Get top grades in a category by market demand and pricing"""
        exclude = exclude or []
        
        grades = TobaccoGrade.objects.filter(
            category=category,
            is_active=True
        ).exclude(
            grade_code__in=exclude
        ).exclude(
            market_demand='REJECT'
        ).order_by(
            '-market_demand',  # High demand first
            'position_number',  # Lower position numbers (higher quality)
            '-base_price'  # Higher prices (premium grades)
        )[:limit]
        
        return list(grades)
    
    def get_grade_analysis(self, grade_id):
        """Get detailed analysis for a specific grade"""
        try:
            grade = TobaccoGrade.objects.get(id=grade_id)
        except TobaccoGrade.DoesNotExist:
            return None
        
        # Get recent transaction history
        recent_transactions = Transaction.objects.filter(
            grade=grade,
            timestamp__gte=self.current_date - timedelta(days=60)
        ).order_by('-timestamp')
        
        # Calculate statistics
        if recent_transactions.exists():
            prices = [float(t.price_per_kg) for t in recent_transactions]
            volumes = [float(t.quantity) for t in recent_transactions]
            
            avg_price = sum(prices) / len(prices)
            price_volatility = self._calculate_volatility(prices)
            total_volume = sum(volumes)
            trend = self._calculate_price_trend(prices)
        else:
            avg_price = float(grade.base_price)
            price_volatility = 0.1  # Default volatility
            total_volume = 0
            trend = 'STABLE'
        
        # Get current inventory
        try:
            inventory = MerchantInventory.objects.get(
                merchant=self.merchant,
                grade=grade
            )
            current_stock = inventory.quantity
            avg_cost = inventory.average_cost
        except:
            current_stock = 0
            avg_cost = grade.base_price
        
        return {
            'grade': grade,
            'current_stock': current_stock,
            'avg_cost': float(avg_cost),
            'market_stats': {
                'avg_price': avg_price,
                'base_price': float(grade.base_price),
                'price_variance': ((avg_price / float(grade.base_price)) - 1) * 100,
                'volatility': price_volatility,
                'volume_30d': total_volume,
                'trend': trend,
                'transactions_count': recent_transactions.count()
            },
            'recommendation': self._get_grade_recommendation(grade, avg_price, price_volatility, current_stock)
        }
    
    def _calculate_volatility(self, prices):
        """Calculate price volatility"""
        if len(prices) < 2:
            return 0.1
        
        import statistics
        return statistics.stdev(prices) / statistics.mean(prices)
    
    def _calculate_price_trend(self, prices):
        """Calculate price trend over time"""
        if len(prices) < 3:
            return 'STABLE'
        
        # Simple trend calculation
        recent_half = prices[:len(prices)//2]
        older_half = prices[len(prices)//2:]
        
        recent_avg = sum(recent_half) / len(recent_half)
        older_avg = sum(older_half) / len(older_half)
        
        change = (recent_avg / older_avg) - 1
        
        if change > 0.05:
            return 'RISING'
        elif change < -0.05:
            return 'FALLING'
        else:
            return 'STABLE'
    
    def _get_grade_recommendation(self, grade, avg_price, volatility, current_stock):
        """Get recommendation for a specific grade"""
        base_price = float(grade.base_price)
        
        # Determine action
        if avg_price < base_price * 0.95 and volatility < 0.2:
            action = 'BUY'
            confidence = 'HIGH'
            reason = 'Below base price with low volatility - good buying opportunity'
        elif avg_price > base_price * 1.15:
            action = 'SELL' if current_stock > 0 else 'WAIT'
            confidence = 'HIGH'
            reason = 'Above base price - good selling opportunity' if current_stock > 0 else 'Overpriced - wait for better opportunity'
        elif current_stock < 50:
            action = 'BUY'
            confidence = 'MEDIUM'
            reason = 'Low inventory - consider restocking'
        else:
            action = 'HOLD'
            confidence = 'MEDIUM'
            reason = 'Stable conditions - maintain current position'
        
        return {
            'action': action,
            'confidence': confidence,
            'reason': reason,
            'suggested_quantity': 200 if action == 'BUY' else 0,
            'price_target': base_price * 0.95 if action == 'BUY' else base_price * 1.1
        }