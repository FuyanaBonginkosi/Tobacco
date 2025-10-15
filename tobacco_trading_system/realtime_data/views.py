from django.shortcuts import render
from django.http import JsonResponse, StreamingHttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db.models import Q, Sum, Count, Avg
from decimal import Decimal
import json
import time
import random

from .models import RealTimePrice, LiveTransaction, MarketAlert, SystemNotification, MarketDataSnapshot
from timb_dashboard.models import TobaccoGrade, TobaccoFloor, Transaction
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


@login_required
def realtime_dashboard(request):
    """Real-time market monitoring dashboard"""
    # Get latest price data
    latest_prices = RealTimePrice.objects.select_related(
        'grade', 'floor'
    ).order_by('-last_updated')[:10]
    
    # Get recent transactions (only when market open anywhere)
    recent_transactions = LiveTransaction.objects.select_related(
        'grade', 'floor'
    ).filter(is_broadcast=True, floor__market_open=True).order_by('-timestamp')[:20]
    
    # Get active alerts
    active_alerts = MarketAlert.objects.filter(
        is_resolved=False
    ).order_by('-severity', '-created_at')[:5]
    
    # Market summary
    today = timezone.now().date()
    market_summary = {
        'total_volume': LiveTransaction.objects.filter(
            timestamp__date=today
        ).aggregate(total=Sum('quantity'))['total'] or 0,
        'total_value': LiveTransaction.objects.filter(
            timestamp__date=today
        ).aggregate(total=Sum('total_value'))['total'] or 0,
        'transaction_count': LiveTransaction.objects.filter(
            timestamp__date=today
        ).count(),
        'average_price': LiveTransaction.objects.filter(
            timestamp__date=today
        ).aggregate(avg=Avg('price'))['avg'] or 0
    }
    
    context = {
        'latest_prices': latest_prices,
        'recent_transactions': recent_transactions,
        'active_alerts': active_alerts,
        'market_summary': market_summary,
    }
    
    return render(request, 'realtime_data/dashboard.html', context)


@login_required
@require_http_methods(["GET"])
def api_live_prices(request):
    """API endpoint for live price data"""
    # Only broadcast when market is open
    prices = RealTimePrice.objects.select_related('grade', 'floor').filter(
        models.Q(floor__market_open=True) | models.Q(floor__isnull=True)
    )
    
    price_data = []
    for price in prices:
        price_data.append({
            'grade_code': price.grade.grade_code,
            'grade_name': price.grade.grade_name,
            'floor_name': price.floor.name if price.floor else 'All Floors',
            'current_price': float(price.current_price),
            'previous_price': float(price.previous_price) if price.previous_price else None,
            'price_change': float(price.price_change),
            'percentage_change': float(price.percentage_change),
            'volume_today': float(price.volume_traded_today),
            'trend': price.trend_indicator,
            'last_updated': price.last_updated.isoformat(),
            'volatility': float(price.volatility_index)
        })
    
    return JsonResponse({
        'success': True,
        'prices': price_data,
        'timestamp': timezone.now().isoformat()
    })


@login_required
@require_http_methods(["GET"])
def api_live_transactions(request):
    """API endpoint for live transaction feed"""
    limit = int(request.GET.get('limit', 50))
    
    transactions = LiveTransaction.objects.select_related(
        'grade', 'floor'
    ).filter(is_broadcast=True).order_by('-timestamp')[:limit]
    
    transaction_data = []
    for tx in transactions:
        transaction_data.append({
            'transaction_id': tx.transaction_id,
            'grade_name': tx.grade.grade_name,
            'floor_name': tx.floor.name if tx.floor else 'Unknown',
            'quantity': float(tx.quantity),
            'price': float(tx.price),
            'total_value': float(tx.total_value),
            'buyer': tx.buyer_info,
            'seller': tx.seller_info,
            'timestamp': tx.timestamp.isoformat(),
            'is_flagged': tx.is_flagged,
            'is_large_trade': tx.is_large_trade,
            'trading_session': tx.trading_session
        })
    
    return JsonResponse({
        'success': True,
        'transactions': transaction_data,
        'timestamp': timezone.now().isoformat()
    })


@login_required
def price_stream(request):
    """Server-Sent Events stream for real-time price updates"""
    def event_stream():
        while True:
            # Get latest price updates
            recent_updates = RealTimePrice.objects.filter(
                last_updated__gte=timezone.now() - timezone.timedelta(seconds=30)
            ).select_related('grade', 'floor')
            
            if recent_updates.exists():
                updates = []
                for price in recent_updates:
                    updates.append({
                        'grade_code': price.grade.grade_code,
                        'current_price': float(price.current_price),
                        'price_change': float(price.price_change),
                        'percentage_change': float(price.percentage_change),
                        'volume': float(price.volume_traded_today),
                        'timestamp': price.last_updated.isoformat()
                    })
                
                yield f"data: {json.dumps({'type': 'price_update', 'data': updates})}\n\n"
            
            # Send heartbeat
            yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': timezone.now().isoformat()})}\n\n"
            
            time.sleep(5)  # Update every 5 seconds
    
    response = StreamingHttpResponse(event_stream(), content_type='text/plain')
    response['Cache-Control'] = 'no-cache'
    response['Connection'] = 'keep-alive'
    return response


@login_required
def transaction_stream(request):
    """Server-Sent Events stream for real-time transactions"""
    def event_stream():
        last_check = timezone.now()
        
        while True:
            # Get new transactions since last check
            new_transactions = LiveTransaction.objects.filter(
                timestamp__gt=last_check,
                is_broadcast=True
            ).select_related('grade', 'floor').order_by('-timestamp')
            
            if new_transactions.exists():
                transactions = []
                for tx in new_transactions:
                    transactions.append({
                        'transaction_id': tx.transaction_id,
                        'grade_name': tx.grade.grade_name,
                        'quantity': float(tx.quantity),
                        'price': float(tx.price),
                        'total_value': float(tx.total_value),
                        'timestamp': tx.timestamp.isoformat(),
                        'is_flagged': tx.is_flagged
                    })
                
                yield f"data: {json.dumps({'type': 'new_transactions', 'data': transactions})}\n\n"
                
                last_check = timezone.now()
            
            time.sleep(2)  # Check every 2 seconds
    
    response = StreamingHttpResponse(event_stream(), content_type='text/plain')
    response['Cache-Control'] = 'no-cache'
    response['Connection'] = 'keep-alive'
    return response


@login_required
@require_http_methods(["POST"])
def create_market_alert(request):
    """Create a new market alert"""
    if not request.user.is_timb_staff:
        return JsonResponse({'success': False, 'error': 'Unauthorized'})
    
    try:
        data = json.loads(request.body)
        
        alert = MarketAlert.objects.create(
            alert_type=data['alert_type'],
            severity=data['severity'],
            title=data['title'],
            message=data['message'],
            grade_id=data.get('grade_id'),
            floor_id=data.get('floor_id'),
            threshold_value=data.get('threshold_value'),
            current_value=data.get('current_value'),
            affected_regions=data.get('affected_regions', []),
            expires_at=data.get('expires_at')
        )
        
        # Broadcast alert
        channel_layer = get_channel_layer()
        if channel_layer:
            alert_data = {
                'id': alert.id,
                'type': alert.alert_type,
                'severity': alert.severity,
                'title': alert.title,
                'message': alert.message,
                'timestamp': alert.created_at.isoformat()
            }
            
            async_to_sync(channel_layer.group_send)(
                'market_alerts',
                {
                    'type': 'market_alert',
                    'data': alert_data
                }
            )
        
        return JsonResponse({
            'success': True,
            'alert_id': alert.id
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_http_methods(["GET"])
def market_analytics(request):
    """Market analytics and insights"""
    # Get date range
    days = int(request.GET.get('days', 7))
    end_date = timezone.now().date()
    start_date = end_date - timezone.timedelta(days=days)
    
    # Transaction analytics
    transactions = Transaction.objects.filter(
        timestamp__date__range=[start_date, end_date]
    )
    
    analytics = {
        'transaction_count': transactions.count(),
        'total_volume': float(transactions.aggregate(total=Sum('quantity'))['total'] or 0),
        'total_value': float(transactions.aggregate(total=Sum('total_amount'))['total'] or 0),
        'average_price': float(transactions.aggregate(avg=Avg('price_per_kg'))['avg'] or 0),
        'grade_distribution': {},
        'daily_trends': [],
        'price_trends': {}
    }
    
    # Grade distribution
    grade_stats = transactions.values('grade__grade_name').annotate(
        count=Count('id'),
        volume=Sum('quantity'),
        value=Sum('total_amount')
    ).order_by('-volume')
    
    for stat in grade_stats:
        analytics['grade_distribution'][stat['grade__grade_name']] = {
            'count': stat['count'],
            'volume': float(stat['volume']),
            'value': float(stat['value'])
        }
    
    # Daily trends
    for i in range(days):
        date = start_date + timezone.timedelta(days=i)
        day_transactions = transactions.filter(timestamp__date=date)
        
        analytics['daily_trends'].append({
            'date': date.isoformat(),
            'count': day_transactions.count(),
            'volume': float(day_transactions.aggregate(total=Sum('quantity'))['total'] or 0),
            'value': float(day_transactions.aggregate(total=Sum('total_amount'))['total'] or 0)
        })
    
    return JsonResponse({
        'success': True,
        'analytics': analytics,
        'period': f'{days} days',
        'generated_at': timezone.now().isoformat()
    })


def simulate_market_data():
    """Simulate real-time market data for demonstration"""
    # This function would be called periodically to generate realistic market data
    
    grades = TobaccoGrade.objects.filter(is_active=True)
    floors = TobaccoFloor.objects.filter(is_active=True)
    
    for grade in grades:
        # Update or create real-time price
        real_time_price, created = RealTimePrice.objects.get_or_create(
            grade=grade,
            defaults={
                'current_price': grade.base_price,
                'previous_price': grade.base_price,
                'price_change': 0
            }
        )
        
        if not created:
            # Simulate price movement
            change_percent = random.uniform(-0.05, 0.05)  # ±5% change
            new_price = real_time_price.current_price * (1 + change_percent)
            
            real_time_price.previous_price = real_time_price.current_price
            real_time_price.current_price = new_price
            real_time_price.price_change = new_price - real_time_price.previous_price
            
            # Update volatility
            real_time_price.update_volatility()
            
            # Simulate volume
            real_time_price.volume_traded_today += random.uniform(100, 1000)
            
            real_time_price.save()
        
        # Simulate some transactions
        if random.random() < 0.3:  # 30% chance of new transaction
            floor = random.choice(floors) if floors else None
            quantity = random.uniform(100, 2000)
            price = float(real_time_price.current_price) * random.uniform(0.95, 1.05)
            
            LiveTransaction.objects.create(
                transaction_id=f"SIM-{timezone.now().strftime('%Y%m%d%H%M%S')}-{random.randint(1000, 9999)}",
                floor=floor,
                grade=grade,
                quantity=quantity,
                price=price,
                buyer_info=f"Buyer_{random.randint(1, 100)}",
                seller_info=f"Seller_{random.randint(1, 100)}",
                is_flagged=random.random() < 0.05  # 5% chance of being flagged
            )


@login_required
@require_http_methods(["POST"])
def generate_market_snapshot(request):
    """Generate a market data snapshot"""
    if not request.user.is_timb_staff:
        return JsonResponse({'success': False, 'error': 'Unauthorized'})
    
    try:
        today = timezone.now().date()
        
        # Calculate market summary
        today_transactions = Transaction.objects.filter(timestamp__date=today)
        
        total_transactions = today_transactions.count()
        total_volume = today_transactions.aggregate(total=Sum('quantity'))['total'] or 0
        total_value = today_transactions.aggregate(total=Sum('total_amount'))['total'] or 0
        average_price = today_transactions.aggregate(avg=Avg('price_per_kg'))['avg'] or 0
        
        # Find top gainers and losers
        price_changes = RealTimePrice.objects.exclude(previous_price__isnull=True)
        top_gainer = price_changes.order_by('-price_change').first()
        top_loser = price_changes.order_by('price_change').first()
        
        # Find volume leader
        volume_leader = today_transactions.values('grade').annotate(
            total_volume=Sum('quantity')
        ).order_by('-total_volume').first()
        
        highest_volume_grade = None
        highest_volume_amount = 0
        if volume_leader:
            highest_volume_grade = TobaccoGrade.objects.get(id=volume_leader['grade'])
            highest_volume_amount = volume_leader['total_volume']
        
        # Create snapshot
        snapshot = MarketDataSnapshot.objects.create(
            total_transactions=total_transactions,
            total_volume=total_volume,
            total_value=total_value,
            average_price=average_price,
            top_gainer_grade=top_gainer.grade if top_gainer else None,
            top_gainer_change=top_gainer.price_change if top_gainer else 0,
            top_loser_grade=top_loser.grade if top_loser else None,
            top_loser_change=top_loser.price_change if top_loser else 0,
            highest_volume_grade=highest_volume_grade,
            highest_volume_amount=highest_volume_amount or 0,
            volatility_index=calculate_market_volatility()
        )
        
        return JsonResponse({
            'success': True,
            'snapshot_id': snapshot.id,
            'summary': {
                'transactions': total_transactions,
                'volume': float(total_volume),
                'value': float(total_value),
                'average_price': float(average_price)
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


def calculate_market_volatility():
    """Calculate overall market volatility index"""
    prices = RealTimePrice.objects.exclude(previous_price__isnull=True)
    
    if not prices.exists():
        return 0
    
    total_volatility = sum(float(price.volatility_index) for price in prices)
    return total_volatility / prices.count()