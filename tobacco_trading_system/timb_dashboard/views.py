from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.db.models import Count, Sum, Avg, Q, F
from django.utils import timezone
from django.contrib import messages
from datetime import datetime, timedelta
from decimal import Decimal
import json

from .models import (
    Transaction, TobaccoGrade, TobaccoFloor, DailyPrice, 
    DashboardMetric, SystemAlert, UserSession
)
from authentication.models import User
from django.db import models


def is_timb_staff(user):
    """Check if user is TIMB staff"""
    return user.is_authenticated and (user.is_staff or user.is_timb_staff)


@login_required
@user_passes_test(is_timb_staff)
def dashboard_view(request):
    """Main TIMB dashboard view"""
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    
    # Get basic statistics
    stats = {
        'total_merchants': User.objects.filter(groups__name='Merchants').count(),
        'total_transactions_today': Transaction.objects.filter(timestamp__date=today).count(),
        'total_volume_today': Transaction.objects.filter(
            timestamp__date=today
        ).aggregate(total=Sum('quantity'))['total'] or 0,
        'active_alerts': SystemAlert.objects.filter(is_active=True).count(),
        'critical_alerts': SystemAlert.objects.filter(
            is_active=True, severity='CRITICAL'
        ).count(),
    }
    
    # Recent transactions
    recent_transactions = Transaction.objects.select_related(
        'seller', 'buyer', 'grade', 'floor'
    ).order_by('-timestamp')[:20]
    
    # Fraud alerts
    fraud_alerts = SystemAlert.objects.filter(
        alert_type='FRAUD', is_active=True
    ).order_by('-created_at')[:10]
    
    # Volume trends for chart
    volume_trends = []
    for i in range(7):
        date = today - timedelta(days=i)
        volume = Transaction.objects.filter(
            timestamp__date=date
        ).aggregate(total=Sum('quantity'))['total'] or 0
        volume_trends.append({
            'date': date.isoformat(),
            'volume': float(volume)
        })
    
    volume_trends.reverse()
    
    context = {
        'stats': stats,
        'recent_transactions': recent_transactions,
        'fraud_alerts': [],
        'volume_trends': json.dumps(volume_trends),
    }
    
    return render(request, 'timb_dashboard/dashboard.html', context)


@login_required
@user_passes_test(is_timb_staff)
def record_transaction_view(request):
    """Record new tobacco transaction"""
    if request.method == 'POST':
        try:
            # Get form data
            transaction_type = request.POST.get('transaction_type')
            seller_id = request.POST.get('seller')
            buyer_id = request.POST.get('buyer')
            grade_id = request.POST.get('grade')
            quantity = Decimal(request.POST.get('quantity', '0'))
            price_per_kg = Decimal(request.POST.get('price_per_kg', '0'))
            floor_id = request.POST.get('floor')
            payment_method = request.POST.get('payment_method')
            moisture_content = request.POST.get('moisture_content')
            quality_assessment = request.POST.get('quality_assessment', '')
            
            # Get related objects
            seller = get_object_or_404(User, id=seller_id)
            buyer = get_object_or_404(User, id=buyer_id)
            grade = get_object_or_404(TobaccoGrade, id=grade_id)
            floor = get_object_or_404(TobaccoFloor, id=floor_id) if floor_id else None
            
            # Create transaction
            transaction = Transaction.objects.create(
                transaction_type=transaction_type,
                seller=seller,
                buyer=buyer,
                grade=grade,
                quantity=quantity,
                price_per_kg=price_per_kg,
                total_amount=quantity * price_per_kg,
                floor=floor,
                payment_method=payment_method,
                moisture_content=Decimal(moisture_content) if moisture_content else None,
                quality_assessment=quality_assessment,
                created_by=request.user,
            )
            
            # AI fraud detection removed; TIMB staff decide legitimacy per policy
            
            return JsonResponse({
                'success': True,
                'transaction_id': transaction.transaction_id,
                'message': 'Transaction recorded successfully'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    # GET request - show form
    context = {
        'transaction_types': Transaction.TRANSACTION_TYPES,
        'merchants': User.objects.filter(groups__name='Merchants').order_by('username'),
        'grades': TobaccoGrade.objects.filter(is_active=True, is_tradeable=True).order_by('grade_code'),
        'floors': TobaccoFloor.objects.filter(is_active=True).order_by('name'),
    }
    
    return render(request, 'timb_dashboard/record_transaction.html', context)


@login_required
@user_passes_test(is_timb_staff)
def price_monitoring_view(request):
    """Price monitoring and management"""
    today = timezone.now().date()
    
    # Get filter parameters
    grade_filter = request.GET.get('grade')
    floor_filter = request.GET.get('floor')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    # Build query
    prices_query = DailyPrice.objects.select_related('grade', 'floor').order_by('-date', 'grade__grade_code')
    
    if grade_filter:
        prices_query = prices_query.filter(grade__grade_code__icontains=grade_filter)
    if floor_filter:
        prices_query = prices_query.filter(floor_id=floor_filter)
    if date_from:
        prices_query = prices_query.filter(date__gte=date_from)
    if date_to:
        prices_query = prices_query.filter(date__lte=date_to)
    
    # Pagination
    paginator = Paginator(prices_query, 25)
    page_number = request.GET.get('page')
    prices = paginator.get_page(page_number)
    
    # Get summary statistics
    summary_stats = prices_query.aggregate(
        avg_price=Avg('closing_price'),
        total_volume=Sum('volume_traded'),
        total_transactions=Sum('number_of_transactions')
    )
    
    context = {
        'prices': prices,
        'summary_stats': summary_stats,
        'grades': TobaccoGrade.objects.filter(is_active=True, is_tradeable=True).order_by('grade_code'),
        'floors': TobaccoFloor.objects.filter(is_active=True).order_by('name'),
        'filters': {
            'grade': grade_filter,
            'floor': floor_filter,
            'date_from': date_from,
            'date_to': date_to,
        }
    }
    
    return render(request, 'timb_dashboard/price_monitoring.html', context)


@login_required
@user_passes_test(is_timb_staff)
def open_market(request):
    """Open market for all active floors (or selected)."""
    floor_id = request.GET.get('floor_id')
    if floor_id:
        TobaccoFloor.objects.filter(id=floor_id, is_active=True).update(market_open=True)
    else:
        TobaccoFloor.objects.filter(is_active=True).update(market_open=True)
    messages.success(request, 'Market opened')
    return redirect('timb_dashboard:dashboard')


@login_required
@user_passes_test(is_timb_staff)
def close_market(request):
    """Close market for all floors (or selected)."""
    floor_id = request.GET.get('floor_id')
    if floor_id:
        TobaccoFloor.objects.filter(id=floor_id).update(market_open=False)
    else:
        TobaccoFloor.objects.update(market_open=False)
    messages.success(request, 'Market closed')
    return redirect('timb_dashboard:dashboard')


@login_required
@user_passes_test(is_timb_staff)
def update_daily_prices(request):
    """Update daily prices for all grades"""
    if request.method == 'POST':
        try:
            today = timezone.now().date()
            updated_count = 0
            
            # Get all tradeable grades
            grades = TobaccoGrade.objects.filter(is_active=True, is_tradeable=True)
            
            for grade in grades:
                # Get transactions for today
                transactions = Transaction.objects.filter(
                    grade=grade,
                    timestamp__date=today,
                    status='COMPLETED'
                )
                
                if transactions.exists():
                    # Calculate price statistics
                    prices = [t.price_per_kg for t in transactions]
                    volumes = [t.quantity for t in transactions]
                    
                    opening_price = prices[0] if prices else grade.base_price
                    closing_price = prices[-1] if prices else grade.base_price
                    high_price = max(prices) if prices else grade.base_price
                    low_price = min(prices) if prices else grade.base_price
                    avg_price = sum(prices) / len(prices) if prices else grade.base_price
                    total_volume = sum(volumes) if volumes else 0
                    
                    # Create or update daily price
                    daily_price, created = DailyPrice.objects.get_or_create(
                        grade=grade,
                        date=today,
                        defaults={
                            'opening_price': opening_price,
                            'closing_price': closing_price,
                            'high_price': high_price,
                            'low_price': low_price,
                            'average_price': avg_price,
                            'volume_traded': total_volume,
                            'number_of_transactions': transactions.count(),
                        }
                    )
                    
                    if not created:
                        # Update existing record
                        daily_price.closing_price = closing_price
                        daily_price.high_price = max(daily_price.high_price, high_price)
                        daily_price.low_price = min(daily_price.low_price, low_price)
                        daily_price.average_price = avg_price
                        daily_price.volume_traded = total_volume
                        daily_price.number_of_transactions = transactions.count()
                        daily_price.save()
                    
                    updated_count += 1
            
            return JsonResponse({
                'success': True,
                'updated_count': updated_count,
                'message': f'Updated prices for {updated_count} grades'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


@login_required
@user_passes_test(is_timb_staff)
def api_realtime_data(request):
    """API endpoint for real-time dashboard data"""
    today = timezone.now().date()
    
    data = {
        'transactions_today': Transaction.objects.filter(timestamp__date=today).count(),
        'volume_today': float(
            Transaction.objects.filter(timestamp__date=today).aggregate(
                total=Sum('quantity')
            )['total'] or 0
        ),
        'fraud_alerts': SystemAlert.objects.filter(
            alert_type='FRAUD', is_active=True
        ).count(),
        'active_users': UserSession.get_active_count(),
        'timestamp': timezone.now().isoformat()
    }
    
    return JsonResponse(data)


@login_required
@user_passes_test(is_timb_staff)
def floor_management_view(request):
    """Tobacco floors management"""
    floors = TobaccoFloor.objects.annotate(
        total_transactions=Count('transaction'),
        total_volume=Sum('transaction__quantity')
    ).order_by('name')
    
    context = {
        'floors': floors,
    }
    
    return render(request, 'timb_dashboard/floor_management.html', context)


@login_required
@user_passes_test(is_timb_staff)
def grade_management_view(request):
    """Tobacco grades management"""
    # Get filter parameters
    category_filter = request.GET.get('category')
    quality_filter = request.GET.get('quality')
    search_query = request.GET.get('search')
    
    # Build query
    grades_query = TobaccoGrade.objects.annotate(
        total_transactions=Count('transaction'),
        total_volume=Sum('transaction__quantity'),
        avg_price=Avg('transaction__price_per_kg')
    ).order_by('category', 'quality_level', 'grade_code')
    
    if category_filter:
        grades_query = grades_query.filter(category=category_filter)
    if quality_filter:
        grades_query = grades_query.filter(quality_level=quality_filter)
    if search_query:
        grades_query = grades_query.filter(
            Q(grade_code__icontains=search_query) |
            Q(grade_name__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(grades_query, 50)
    page_number = request.GET.get('page')
    grades = paginator.get_page(page_number)
    
    context = {
        'grades': grades,
        'categories': TobaccoGrade.GRADE_CATEGORIES,
        'quality_levels': TobaccoGrade.QUALITY_LEVELS,
        'filters': {
            'category': category_filter,
            'quality': quality_filter,
            'search': search_query,
        }
    }
    
    return render(request, 'timb_dashboard/grade_management.html', context)


@login_required
@user_passes_test(is_timb_staff)
def transaction_analytics_view(request):
    """Transaction analytics and reports"""
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # Get date range from request
    date_from = request.GET.get('date_from', week_ago.isoformat())
    date_to = request.GET.get('date_to', today.isoformat())
    
    if isinstance(date_from, str):
        date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
    if isinstance(date_to, str):
        date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
    
    # Get transactions in date range
    transactions = Transaction.objects.filter(
        timestamp__date__range=[date_from, date_to]
    )
    
    # Analytics data
    analytics = {
        'total_transactions': transactions.count(),
        'total_volume': transactions.aggregate(Sum('quantity'))['quantity__sum'] or 0,
        'total_value': transactions.aggregate(Sum('total_amount'))['total_amount__sum'] or 0,
        'avg_price': transactions.aggregate(Avg('price_per_kg'))['price_per_kg__avg'] or 0,
        'fraud_rate': (transactions.filter(is_flagged=True).count() / max(transactions.count(), 1)) * 100,
    }
    
    # Top grades by volume
    top_grades = transactions.values('grade__grade_code', 'grade__grade_name').annotate(
        total_volume=Sum('quantity'),
        total_value=Sum('total_amount'),
        avg_price=Avg('price_per_kg'),
        transaction_count=Count('id')
    ).order_by('-total_volume')[:10]
    
    # Top floors by volume
    top_floors = transactions.exclude(floor__isnull=True).values(
        'floor__name', 'floor__location'
    ).annotate(
        total_volume=Sum('quantity'),
        total_value=Sum('total_amount'),
        transaction_count=Count('id')
    ).order_by('-total_volume')[:10]
    
    # Daily trends
    daily_trends = []
    current_date = date_from
    while current_date <= date_to:
        day_transactions = transactions.filter(timestamp__date=current_date)
        daily_trends.append({
            'date': current_date.isoformat(),
            'volume': float(day_transactions.aggregate(Sum('quantity'))['quantity__sum'] or 0),
            'value': float(day_transactions.aggregate(Sum('total_amount'))['total_amount__sum'] or 0),
            'transactions': day_transactions.count(),
            'avg_price': float(day_transactions.aggregate(Avg('price_per_kg'))['price_per_kg__avg'] or 0)
        })
        current_date += timedelta(days=1)
    
    context = {
        'analytics': analytics,
        'top_grades': top_grades,
        'top_floors': top_floors,
        'daily_trends': json.dumps(daily_trends),
        'date_from': date_from,
        'date_to': date_to,
    }
    
    return render(request, 'timb_dashboard/transaction_analytics.html', context)


class TransactionListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """List all transactions with filtering"""
    model = Transaction
    template_name = 'timb_dashboard/transaction_list.html'
    context_object_name = 'transactions'
    paginate_by = 25
    
    def test_func(self):
        return is_timb_staff(self.request.user)
    
    def get_queryset(self):
        queryset = Transaction.objects.select_related(
            'seller', 'buyer', 'grade', 'floor', 'created_by'
        ).order_by('-timestamp')
        
        # Apply filters
        transaction_type = self.request.GET.get('type')
        status = self.request.GET.get('status')
        grade = self.request.GET.get('grade')
        floor = self.request.GET.get('floor')
        flagged = self.request.GET.get('flagged')
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        
        if transaction_type:
            queryset = queryset.filter(transaction_type=transaction_type)
        if status:
            queryset = queryset.filter(status=status)
        if grade:
            queryset = queryset.filter(grade__grade_code__icontains=grade)
        if floor:
            queryset = queryset.filter(floor_id=floor)
        if flagged:
            queryset = queryset.filter(is_flagged=True)
        if date_from:
            queryset = queryset.filter(timestamp__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(timestamp__date__lte=date_to)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['transaction_types'] = Transaction.TRANSACTION_TYPES
        context['status_choices'] = Transaction.STATUS_CHOICES
        context['floors'] = TobaccoFloor.objects.filter(is_active=True)
        context['filters'] = {
            'type': self.request.GET.get('type'),
            'status': self.request.GET.get('status'),
            'grade': self.request.GET.get('grade'),
            'floor': self.request.GET.get('floor'),
            'flagged': self.request.GET.get('flagged'),
            'date_from': self.request.GET.get('date_from'),
            'date_to': self.request.GET.get('date_to'),
        }
        return context


class TransactionDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    """Transaction detail view"""
    model = Transaction
    template_name = 'timb_dashboard/transaction_detail.html'
    context_object_name = 'transaction'
    slug_field = 'transaction_id'
    slug_url_kwarg = 'transaction_id'
    
    def test_func(self):
        return is_timb_staff(self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get related alerts
        context['alerts'] = SystemAlert.objects.filter(
            transaction=self.object
        ).order_by('-created_at')
        
        return context