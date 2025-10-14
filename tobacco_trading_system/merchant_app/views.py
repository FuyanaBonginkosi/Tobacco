from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Sum, Count, Avg
from django.core.paginator import Paginator
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from decimal import Decimal
import json
import uuid

from timb_dashboard.models import Merchant, TobaccoGrade, Transaction
from .models import (
    MerchantProfile, MerchantInventory, CustomGrade, GradeComponent,
    ClientOrder, FarmerRiskAssessment, PurchaseRecommendation,
    DashboardWidget, InterMerchantCommunication, InterMerchantTrade,
    AggregationRuleSet, AggregatedGrade
)

# AI integration
try:
    from ai_models.views import run_farmer_risk_assessment, run_fraud_detection
except ImportError:
    def run_farmer_risk_assessment(data):
        return {'risk_score': 0.5, 'risk_level': 'MEDIUM', 'recommendation': 'Manual review required'}
    def run_fraud_detection(transaction):
        return {'is_fraud': False, 'confidence': 0.0, 'risk_factors': []}


@login_required
def dashboard(request):
    """Enhanced merchant dashboard with customization"""
    if not request.user.is_merchant:
        return redirect('home')
    
    try:
        merchant = request.user.merchant_profile
    except:
        messages.error(request, 'Merchant profile not found. Please contact support.')
        return redirect('profile')
    
    # Get or create extended profile
    profile, created = MerchantProfile.objects.get_or_create(merchant=merchant)
    
    # Dashboard statistics
    today = timezone.now().date()
    this_month = timezone.now().replace(day=1).date()
    
    stats = {
        'total_inventory_value': MerchantInventory.objects.filter(
            merchant=merchant
        ).aggregate(
            total=Sum('quantity') * Sum('average_cost')
        )['total'] or 0,
        
        'active_orders': ClientOrder.objects.filter(
            merchant=merchant,
            status__in=['PENDING', 'CONFIRMED', 'IN_PROGRESS']
        ).count(),
        
        'todays_transactions': Transaction.objects.filter(
            Q(buyer=request.user) | Q(seller=request.user),
            timestamp__date=today
        ).count(),
        
        'monthly_volume': Transaction.objects.filter(
            Q(buyer=request.user) | Q(seller=request.user),
            timestamp__date__gte=this_month
        ).aggregate(total=Sum('quantity'))['total'] or 0,
        
        'low_stock_items': MerchantInventory.objects.filter(
            merchant=merchant
        ).filter(quantity__lte=models.F('minimum_threshold')).count(),
        
        'pending_assessments': FarmerRiskAssessment.objects.filter(
            merchant=merchant,
            is_approved=False
        ).count()
    }
    
    # Recent inventory
    inventory = MerchantInventory.objects.filter(
        merchant=merchant
    ).select_related('grade').order_by('-last_updated')[:5]
    
    # Active orders
    active_orders = ClientOrder.objects.filter(
        merchant=merchant,
        status__in=['PENDING', 'CONFIRMED', 'IN_PROGRESS']
    ).order_by('-created_at')[:5]
    
    # AI recommendations
    recommendations = PurchaseRecommendation.objects.filter(
        merchant=merchant,
        is_active=True,
        expires_at__gt=timezone.now()
    ).order_by('-priority', '-confidence_score')[:5]
    
    # Risk alerts
    risks = FarmerRiskAssessment.objects.filter(
        merchant=merchant,
        risk_level__in=['HIGH', 'CRITICAL']
    ).order_by('-assessment_date')[:3]
    
    # Get dashboard widgets
    widgets = DashboardWidget.objects.filter(
        merchant=merchant,
        is_visible=True,
        is_approved=True
    ).order_by('position_y', 'position_x')
    
    context = {
        'merchant': merchant,
        'profile': profile,
        'stats': stats,
        'inventory': inventory,
        'active_orders': active_orders,
        'recommendations': recommendations,
        'risks': risks,
        'widgets': widgets,
    }
    
    return render(request, 'merchant_app/dashboard.html', context)


@login_required
def profile_customization(request):
    """Enhanced profile customization and branding"""
    if not request.user.is_merchant:
        return redirect('home')

    try:
        merchant = request.user.merchant_profile
    except:
        messages.error(request, 'Merchant profile not found. Please contact support.')
        return redirect('profile')
    profile, created = MerchantProfile.objects.get_or_create(merchant=merchant)
    
    if request.method == 'POST':
        section = request.POST.get('section')
        
        if section == 'branding':
            # Handle branding updates
            profile.business_type = request.POST.get('business_type', profile.business_type)
            profile.business_description = request.POST.get('business_description', profile.business_description)
            profile.founding_year = request.POST.get('founding_year') or None
            profile.number_of_employees = request.POST.get('number_of_employees', profile.number_of_employees)
            profile.annual_capacity = request.POST.get('annual_capacity') or None
            
            # Handle file uploads
            if 'company_logo' in request.FILES:
                profile.company_logo = request.FILES['company_logo']
            if 'company_banner' in request.FILES:
                profile.company_banner = request.FILES['company_banner']
            
            # Handle brand colors
            brand_colors = {
                'primary': request.POST.get('primary_color', '#5D5CDE'),
                'secondary': request.POST.get('secondary_color', '#6B7280'),
                'accent': request.POST.get('accent_color', '#10B981')
            }
            profile.brand_colors = brand_colors
            
            profile.save()
            messages.success(request, 'Branding settings updated successfully!')
        
        elif section == 'contact':
            # Handle contact information
            profile.headquarters_address = request.POST.get('headquarters_address', profile.headquarters_address)
            profile.phone_primary = request.POST.get('phone_primary', profile.phone_primary)
            profile.phone_secondary = request.POST.get('phone_secondary', profile.phone_secondary)
            profile.email_business = request.POST.get('email_business', profile.email_business)
            profile.website_url = request.POST.get('website_url', profile.website_url)
            
            profile.save()
            messages.success(request, 'Contact information updated successfully!')
        
        elif section == 'visibility':
            # Handle visibility settings
            profile.profile_visibility = request.POST.get('profile_visibility', profile.profile_visibility)
            profile.show_contact_info = bool(request.POST.get('show_contact_info'))
            profile.show_business_stats = bool(request.POST.get('show_business_stats'))
            profile.show_certifications = bool(request.POST.get('show_certifications'))
            profile.allow_direct_contact = bool(request.POST.get('allow_direct_contact'))
            profile.allow_public_advertising = bool(request.POST.get('allow_public_advertising'))
            
            profile.save()
            messages.success(request, 'Visibility settings updated successfully!')
        
        return redirect('merchant_profile_customization')
    
    context = {
        'merchant': merchant,
        'profile': profile,
        'business_types': MerchantProfile.BUSINESS_TYPES,
        'visibility_choices': MerchantProfile.VISIBILITY_CHOICES,
    }
    
    return render(request, 'merchant_app/profile_customization.html', context)


@login_required
def inventory_management(request):
    """Enhanced inventory management with AI insights"""
    if not request.user.is_merchant:
        return redirect('home')

    try:
        merchant = request.user.merchant_profile
    except:
        messages.error(request, 'Merchant profile not found. Please contact support.')
        return redirect('profile')
    
    # Get inventory with filtering
    inventory = MerchantInventory.objects.filter(
        merchant=merchant
    ).select_related('grade').order_by('-last_updated')
    
    # Filter by grade category
    category_filter = request.GET.get('category')
    if category_filter:
        inventory = inventory.filter(grade__category=category_filter)
    
    # Search functionality
    search_query = request.GET.get('search')
    if search_query:
        inventory = inventory.filter(
            Q(grade__grade_name__icontains=search_query) |
            Q(grade__grade_code__icontains=search_query) |
            Q(storage_location__icontains=search_query)
        )
    
    # Calculate totals
    total_value = sum(item.total_value for item in inventory)
    total_quantity = sum(item.quantity for item in inventory)
    
    # Low stock items
    low_stock_items = inventory.filter(quantity__lte=models.F('minimum_threshold'))
    
    # Pagination
    paginator = Paginator(inventory, 20)
    page_number = request.GET.get('page')
    inventory_page = paginator.get_page(page_number)
    
    context = {
        'merchant': merchant,
        'inventory': inventory_page,
        'total_value': total_value,
        'total_quantity': total_quantity,
        'low_stock_items': low_stock_items,
        'grade_categories': TobaccoGrade.GRADE_CATEGORIES,
        'search_query': search_query,
        'category_filter': category_filter,
    }
    
    return render(request, 'merchant_app/inventory.html', context)


@login_required
@require_http_methods(["POST"])
def add_inventory_item(request):
    """Add new inventory item"""
    if not request.user.is_merchant:
        return JsonResponse({'success': False, 'error': 'Unauthorized'})
    
    try:
        merchant = request.user.merchant_profile
        
        data = json.loads(request.body)
        
        # Create inventory item
        item = MerchantInventory.objects.create(
            merchant=merchant,
            grade_id=data['grade_id'],
            quantity=Decimal(data['quantity']),
            average_cost=Decimal(data['average_cost']),
            storage_location=data.get('storage_location', ''),
            quality_grade=data.get('quality_grade', ''),
            moisture_content=data.get('moisture_content'),
            batch_number=data.get('batch_number', ''),
            minimum_threshold=data.get('minimum_threshold', 100),
            storage_conditions=data.get('storage_conditions', {})
        )
        
        messages.success(request, f'Added {item.quantity}kg of {item.grade.grade_name} to inventory')
        
        return JsonResponse({
            'success': True,
            'item_id': item.id,
            'message': 'Inventory item added successfully'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def custom_grades_management(request):
    """Enhanced custom grades creation and management"""
    if not request.user.is_merchant:
        return redirect('home')

    try:
        merchant = request.user.merchant_profile
    except:
        messages.error(request, 'Merchant profile not found. Please contact support.')
        return redirect('profile')
    
    # Get custom grades
    custom_grades = CustomGrade.objects.filter(
        merchant=merchant
    ).prefetch_related('components__base_grade').order_by('-created_at')
    
    # Get base grades for component selection
    base_grades = TobaccoGrade.objects.filter(
        is_active=True
    ).order_by('category', 'grade_code')
    
    # Get aggregation rules (if needed)
    # aggregation_rules = AggregationRule.objects.filter(merchant=merchant)
    
    context = {
        'merchant': merchant,
        'custom_grades': custom_grades,
        'base_grades': base_grades,
        # 'aggregation_rules': aggregation_rules,
    }
    
    return render(request, 'merchant_app/custom_grades.html', context)


@login_required
def create_custom_grade(request):
    """Create new custom tobacco grade"""
    if not request.user.is_merchant:
        return redirect('home')

    try:
        merchant = request.user.merchant_profile
    except:
        messages.error(request, 'Merchant profile not found. Please contact support.')
        return redirect('profile')
    base_grades = TobaccoGrade.objects.filter(is_active=True).order_by('category', 'grade_code')
    
    if request.method == 'POST':
        try:
            # Create custom grade
            custom_grade = CustomGrade.objects.create(
                merchant=merchant,
                custom_grade_name=request.POST['custom_grade_name'],
                description=request.POST.get('description', ''),
                target_price=Decimal(request.POST['target_price']),
                minimum_order_quantity=request.POST.get('minimum_order_quantity') or None,
                quality_standard=request.POST.get('quality_standard', 'STANDARD'),
                flavor_profile=request.POST.get('flavor_profile', ''),
                burn_rate=request.POST.get('burn_rate', ''),
                moisture_content=request.POST.get('moisture_content') or None,
                nicotine_level=request.POST.get('nicotine_level', ''),
                target_market=request.POST.get('target_market', ''),
                marketing_description=request.POST.get('marketing_description', ''),
                is_draft=bool(request.POST.get('is_draft', False))
            )
            
            # Add components
            components_data = json.loads(request.POST.get('components', '[]'))
            total_percentage = 0
            
            for component_data in components_data:
                if component_data.get('base_grade_id') and component_data.get('percentage'):
                    GradeComponent.objects.create(
                        custom_grade=custom_grade,
                        base_grade_id=component_data['base_grade_id'],
                        percentage=Decimal(component_data['percentage']),
                        minimum_quantity=Decimal(component_data.get('minimum_quantity', 0)),
                        quality_notes=component_data.get('quality_notes', '')
                    )
                    total_percentage += float(component_data['percentage'])
            
            if abs(total_percentage - 100) > 0.1:  # Allow small rounding errors
                messages.warning(request, f'Total component percentage is {total_percentage}%. Consider adjusting to 100%.')
            
            messages.success(request, f'Custom grade "{custom_grade.custom_grade_name}" created successfully!')
            return redirect('merchant_custom_grades')
            
        except Exception as e:
            messages.error(request, f'Error creating custom grade: {str(e)}')
    
    context = {
        'merchant': merchant,
        'base_grades': base_grades,
        'quality_standards': CustomGrade.QUALITY_STANDARDS,
    }
    
    return render(request, 'merchant_app/create_custom_grade.html', context)


@login_required
def orders_management(request):
    """Enhanced order management with tracking"""
    if not request.user.is_merchant:
        return redirect('home')

    try:
        merchant = request.user.merchant_profile
    except:
        messages.error(request, 'Merchant profile not found. Please contact support.')
        return redirect('profile')
    
    # Get orders with filtering
    orders = ClientOrder.objects.filter(
        merchant=merchant
    ).select_related('grade', 'custom_grade').order_by('-created_at')
    
    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    # Search functionality
    search_query = request.GET.get('search')
    if search_query:
        orders = orders.filter(
            Q(order_number__icontains=search_query) |
            Q(client_name__icontains=search_query) |
            Q(client_company__icontains=search_query)
        )
    
    # Calculate order statistics
    order_stats = {
        'pending': orders.filter(status='PENDING').count(),
        'processing': orders.filter(status__in=['CONFIRMED', 'IN_PROGRESS']).count(),
        'completed': orders.filter(status='DELIVERED').count(),
        'total_value': orders.aggregate(total=Sum('total_amount'))['total'] or 0
    }
    
    # Pagination
    paginator = Paginator(orders, 15)
    page_number = request.GET.get('page')
    orders_page = paginator.get_page(page_number)
    
    context = {
        'merchant': merchant,
        'orders': orders_page,
        'order_stats': order_stats,
        'order_statuses': ClientOrder.ORDER_STATUS,
        'status_filter': status_filter,
        'search_query': search_query,
    }
    
    return render(request, 'merchant_app/orders.html', context)


# ---------------------- Aggregation: rules and runs ----------------------

@login_required
@require_http_methods(["GET"])  # List rule sets and latest outputs
def aggregation_dashboard(request):
    if not request.user.is_merchant:
        return redirect('home')
    merchant = request.user.merchant_profile
    rules = AggregationRuleSet.objects.filter(merchant=merchant).order_by('-created_at')
    outputs = AggregatedGrade.objects.filter(merchant=merchant).select_related('rule_set').order_by('-computed_at')[:20]
    return render(request, 'merchant_app/aggregation.html', {
        'merchant': merchant,
        'rules': rules,
        'outputs': outputs,
    })


@login_required
@require_http_methods(["POST"])  # Create or update rule sets
def save_aggregation_rule(request):
    if not request.user.is_merchant:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    merchant = request.user.merchant_profile
    try:
        data = json.loads(request.body)
        rule_id = data.get('id')
        payload = {
            'name': data['name'],
            'rule_type': data['rule_type'],
            'description': data.get('description', ''),
            'parameters': data.get('parameters', {}),
            'limit_to_inventory': bool(data.get('limit_to_inventory', False)),
            'is_active': bool(data.get('is_active', True)),
        }
        if rule_id:
            rule = AggregationRuleSet.objects.get(id=rule_id, merchant=merchant)
            for k, v in payload.items():
                setattr(rule, k, v)
            rule.save()
        else:
            rule = AggregationRuleSet.objects.create(merchant=merchant, **payload)
        return JsonResponse({'success': True, 'rule_id': rule.id})
    except AggregationRuleSet.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Rule not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])  # Run rule set to generate outputs
def run_aggregation_rule(request, rule_id):
    if not request.user.is_merchant:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    from .aggregation_engine import run_rule_set
    merchant = request.user.merchant_profile
    try:
        rule = AggregationRuleSet.objects.get(id=rule_id, merchant=merchant, is_active=True)
        outputs = run_rule_set(rule)
        return JsonResponse({
            'success': True,
            'generated': len(outputs),
            'output_ids': [o.id for o in outputs]
        })
    except AggregationRuleSet.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Rule not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_http_methods(["GET"])  # Details of a specific aggregated grade
def aggregated_grade_detail(request, aggregated_id):
    if not request.user.is_merchant:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    merchant = request.user.merchant_profile
    try:
        agg = AggregatedGrade.objects.select_related('rule_set').prefetch_related('components__base_grade').get(
            id=aggregated_id, merchant=merchant
        )
        return JsonResponse({
            'success': True,
            'grade': {
                'id': agg.id,
                'name': agg.name,
                'label': agg.label,
                'characteristics': agg.characteristics,
                'total_quantity_kg': float(agg.total_quantity_kg),
                'computed_at': agg.computed_at.isoformat(),
                'rule': {'id': agg.rule_set.id, 'name': agg.rule_set.name, 'type': agg.rule_set.rule_type},
                'components': [
                    {
                        'base_grade_code': c.base_grade.grade_code,
                        'base_grade_name': c.base_grade.grade_name,
                        'percentage': float(c.percentage),
                        'kilograms': float(c.kilograms),
                    }
                    for c in agg.components.all()
                ],
            }
        })
    except AggregatedGrade.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Aggregated grade not found'}, status=404)


# ---------------------- Utility APIs used by templates ----------------------

@login_required
@require_http_methods(["GET"])  # Provide list of grades for inventory modal
def api_list_grades(request):
    grades = TobaccoGrade.objects.filter(is_active=True).order_by('category', 'grade_code')
    return JsonResponse({
        'success': True,
        'grades': [
            {
                'id': g.id,
                'grade_code': g.grade_code,
                'grade_name': g.grade_name,
                'category': g.category,
                'base_price': float(g.base_price),
            }
            for g in grades
        ]
    })


@login_required
@require_http_methods(["POST"])  # Inventory export stub
def inventory_report(request):
    # For now, return JSON; in production, generate PDF/CSV
    if not request.user.is_merchant:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    merchant = request.user.merchant_profile
    items = MerchantInventory.objects.filter(merchant=merchant).select_related('grade')
    data = [
        {
            'grade': i.grade.grade_code,
            'name': i.grade.grade_name,
            'quantity': float(i.quantity),
            'avg_cost': float(i.average_cost),
            'total_value': float(i.total_value),
            'location': i.storage_location,
        }
        for i in items
    ]
    return JsonResponse({'success': True, 'items': data})


@login_required
@require_http_methods(["POST"])
def create_order(request):
    """Create new client order"""
    if not request.user.is_merchant:
        return JsonResponse({'success': False, 'error': 'Unauthorized'})
    
    try:
        merchant = request.user.merchant_profile
        data = json.loads(request.body)
        
        order = ClientOrder.objects.create(
            merchant=merchant,
            client_name=data['client_name'],
            client_email=data.get('client_email', ''),
            client_phone=data.get('client_phone', ''),
            client_address=data.get('client_address', ''),
            client_company=data.get('client_company', ''),
            grade_id=data.get('grade_id'),
            custom_grade_id=data.get('custom_grade_id'),
            requested_quantity=Decimal(data['requested_quantity']),
            target_price=Decimal(data['target_price']),
            expected_delivery_date=data.get('expected_delivery_date'),
            priority=data.get('priority', 'NORMAL'),
            order_notes=data.get('order_notes', ''),
            special_requirements=data.get('special_requirements', ''),
            quality_specifications=data.get('quality_specifications', {}),
            packaging_requirements=data.get('packaging_requirements', '')
        )
        
        messages.success(request, f'Order {order.order_number} created successfully!')
        
        return JsonResponse({
            'success': True,
            'order_id': order.id,
            'order_number': order.order_number
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def farmer_risk_assessment(request):
    """AI-powered farmer risk assessment"""
    if not request.user.is_merchant:
        return redirect('home')
    
    merchant = request.user.merchant_profile
    
    # Get existing assessments
    assessments = FarmerRiskAssessment.objects.filter(
        merchant=merchant
    ).order_by('-assessment_date')
    
    if request.method == 'POST':
        try:
            # Collect farmer data
            farmer_data = {
                'farmer_name': request.POST['farmer_name'],
                'farmer_id': request.POST.get('farmer_id', ''),
                'location': request.POST['location'],
                'phone': request.POST.get('phone', ''),
                'email': request.POST.get('email', ''),
                'total_hectares': float(request.POST['total_hectares']),
                'years_experience': int(request.POST['years_experience']),
                'primary_tobacco_type': request.POST['primary_tobacco_type'],
                'annual_income': float(request.POST.get('annual_income', 0)),
                'debt_level': float(request.POST.get('debt_level', 0)),
                'credit_score': int(request.POST.get('credit_score', 70)),
                'previous_defaults': int(request.POST.get('previous_defaults', 0)),
                'proposed_contract_value': float(request.POST['proposed_contract_value']),
                'proposed_quantity': float(request.POST['proposed_quantity']),
                'contract_duration_months': int(request.POST['contract_duration_months']),
                'proposed_price_per_kg': float(request.POST['proposed_price_per_kg']),
            }
            
            # Run AI risk assessment
            ai_result = run_farmer_risk_assessment(farmer_data)
            
            # Create assessment record
            assessment = FarmerRiskAssessment.objects.create(
                merchant=merchant,
                assessed_by=request.user,
                **{k: v for k, v in farmer_data.items() if k != 'proposed_price_per_kg'},
                proposed_price_per_kg=Decimal(str(farmer_data['proposed_price_per_kg'])),
                risk_score=Decimal(str(ai_result.get('risk_score', 0.5))),
                risk_level=ai_result.get('risk_level', 'MEDIUM'),
                ai_recommendation=ai_result.get('recommendation', ''),
                risk_factors=ai_result.get('risk_factors', []),
                mitigation_strategies=ai_result.get('mitigation_strategies', []),
                debt_to_income_ratio=ai_result.get('financial_metrics', {}).get('debt_to_income_ratio'),
                contract_to_income_ratio=ai_result.get('financial_metrics', {}).get('contract_to_income_ratio'),
                projected_yield_per_hectare=ai_result.get('financial_metrics', {}).get('projected_yield_per_hectare')
            )
            
            # Store sensitive data encrypted
            sensitive_data = {
                'bank_details': request.POST.get('bank_details', ''),
                'collateral_details': request.POST.get('collateral_details', ''),
                'additional_notes': request.POST.get('additional_notes', '')
            }
            assessment.set_farmer_data(sensitive_data)
            assessment.save()
            
            messages.success(request, f'Risk assessment completed for {farmer_data["farmer_name"]}')
            return redirect('merchant_farmer_risk_assessment')
            
        except Exception as e:
            messages.error(request, f'Error conducting risk assessment: {str(e)}')
    
    context = {
        'merchant': merchant,
        'assessments': assessments,
    }
    
    return render(request, 'merchant_app/farmer_risk_assessment.html', context)


@login_required
def inter_merchant_communications(request):
    """Private communications between merchants"""
    if not request.user.is_merchant:
        return redirect('home')
    
    merchant = request.user.merchant_profile
    
    # Get conversations
    conversations = InterMerchantCommunication.objects.filter(
        Q(from_merchant=merchant) | Q(to_merchant=merchant)
    ).select_related('from_merchant', 'to_merchant').order_by('-sent_at')
    
    # Filter options
    filter_type = request.GET.get('filter', 'all')
    if filter_type == 'sent':
        conversations = conversations.filter(from_merchant=merchant)
    elif filter_type == 'received':
        conversations = conversations.filter(to_merchant=merchant)
    elif filter_type == 'unread':
        conversations = conversations.filter(to_merchant=merchant, is_read=False)
    
    # Search functionality
    search_query = request.GET.get('search')
    if search_query:
        conversations = conversations.filter(
            Q(subject__icontains=search_query) |
            Q(message__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(conversations, 20)
    page_number = request.GET.get('page')
    conversations_page = paginator.get_page(page_number)
    
    # Get other merchants for new messages
    other_merchants = Merchant.objects.exclude(id=merchant.id).filter(
        status='ACTIVE'
    ).order_by('company_name')
    
    context = {
        'merchant': merchant,
        'conversations': conversations_page,
        'other_merchants': other_merchants,
        'message_types': InterMerchantCommunication.MESSAGE_TYPES,
        'filter_type': filter_type,
        'search_query': search_query,
    }
    
    return render(request, 'merchant_app/communications.html', context)


@login_required
@require_http_methods(["POST"])
def send_message(request):
    """Send message to another merchant"""
    if not request.user.is_merchant:
        return JsonResponse({'success': False, 'error': 'Unauthorized'})
    
    try:
        merchant = request.user.merchant_profile
        data = json.loads(request.body)
        
        message = InterMerchantCommunication.objects.create(
            from_merchant=merchant,
            to_merchant_id=data['to_merchant_id'],
            message_type=data.get('message_type', 'INQUIRY'),
            subject=data['subject'],
            message=data['message'],
            parent_message_id=data.get('parent_message_id')
        )
        
        # Store trade data if provided
        if data.get('trade_data'):
            message.set_trade_data(data['trade_data'])
            message.save()
        
        return JsonResponse({
            'success': True,
            'message_id': message.id,
            'thread_id': message.thread_id
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def inter_merchant_trading(request):
    """Inter-merchant trading platform"""
    if not request.user.is_merchant:
        return redirect('home')
    
    merchant = request.user.merchant_profile
    
    # Get trades
    trades = InterMerchantTrade.objects.filter(
        Q(seller_merchant=merchant) | Q(buyer_merchant=merchant)
    ).select_related(
        'seller_merchant', 'buyer_merchant', 'grade', 'custom_grade'
    ).order_by('-proposed_at')
    
    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        trades = trades.filter(status=status_filter)
    
    # Get available inventory for selling
    available_inventory = MerchantInventory.objects.filter(
        merchant=merchant,
        available_quantity__gt=0
    ).select_related('grade')
    
    # Get other merchants
    other_merchants = Merchant.objects.exclude(id=merchant.id).filter(
        status='ACTIVE'
    ).order_by('company_name')
    
    context = {
        'merchant': merchant,
        'trades': trades,
        'available_inventory': available_inventory,
        'other_merchants': other_merchants,
        'trade_statuses': InterMerchantTrade.TRADE_STATUS,
        'payment_terms': InterMerchantTrade.PAYMENT_TERMS,
        'status_filter': status_filter,
    }
    
    return render(request, 'merchant_app/inter_merchant_trading.html', context)


@login_required
@require_http_methods(["POST"])
def propose_trade(request):
    """Propose a trade to another merchant"""
    if not request.user.is_merchant:
        return JsonResponse({'success': False, 'error': 'Unauthorized'})
    
    try:
        merchant = request.user.merchant_profile
        data = json.loads(request.body)
        
        trade = InterMerchantTrade.objects.create(
            seller_merchant=merchant,
            buyer_merchant_id=data['buyer_merchant_id'],
            grade_id=data.get('grade_id'),
            custom_grade_id=data.get('custom_grade_id'),
            quantity=Decimal(data['quantity']),
            agreed_price_per_kg=Decimal(data['price_per_kg']),
            payment_terms=data.get('payment_terms', 'NET_30'),
            delivery_terms=data.get('delivery_terms', ''),
            delivery_location=data.get('delivery_location', ''),
            delivery_date=data.get('delivery_date'),
            quality_requirements=data.get('quality_requirements', {})
        )
        
        # Check if trade needs TIMB review (high value, unusual pricing, etc.)
        if trade.total_value > 100000 or trade.agreed_price_per_kg > trade.grade.base_price * 1.3:
            trade.is_flagged_for_review = True
            trade.save()
        
        return JsonResponse({
            'success': True,
            'trade_id': trade.trade_id,
            'requires_timb_approval': trade.is_flagged_for_review
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def ai_recommendations(request):
    """AI purchase recommendations dashboard"""
    if not request.user.is_merchant:
        return redirect('home')

    try:
        merchant = request.user.merchant_profile
    except:
        messages.error(request, 'Merchant profile not found. Please contact support.')
        return redirect('profile')
    
    # Get active recommendations
    recommendations = PurchaseRecommendation.objects.filter(
        merchant=merchant,
        is_active=True,
        expires_at__gt=timezone.now()
    ).select_related('grade').order_by('-priority', '-confidence_score')
    
    # Filter by recommendation type
    type_filter = request.GET.get('type')
    if type_filter:
        recommendations = recommendations.filter(recommendation_type=type_filter)
    
    # Get recommendation statistics
    recommendation_stats = {
        'total_active': recommendations.count(),
        'high_priority': recommendations.filter(priority='HIGH').count(),
        'implemented_this_month': PurchaseRecommendation.objects.filter(
            merchant=merchant,
            is_implemented=True,
            implemented_at__gte=timezone.now().replace(day=1)
        ).count(),
        'average_roi': recommendations.aggregate(
            avg=Avg('expected_roi')
        )['avg'] or 0
    }
    
    context = {
        'merchant': merchant,
        'recommendations': recommendations,
        'recommendation_stats': recommendation_stats,
        'recommendation_types': PurchaseRecommendation.RECOMMENDATION_TYPES,
        'type_filter': type_filter,
    }
    
    return render(request, 'merchant_app/ai_recommendations.html', context)


# ---------------------- Order APIs used by template ----------------------

@login_required
@require_http_methods(["GET"])  # Order detail JSON
def api_order_detail(request, order_id):
    if not request.user.is_merchant:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    merchant = request.user.merchant_profile
    try:
        order = ClientOrder.objects.select_related('grade', 'custom_grade').get(id=order_id, merchant=merchant)
        return JsonResponse({
            'success': True,
            'order_number': order.order_number,
            'client_name': order.client_name,
            'status': order.status,
            'created_at': order.created_at.isoformat(),
            'delivery_date': order.expected_delivery_date.isoformat() if order.expected_delivery_date else None,
            'requested_quantity': float(order.requested_quantity),
            'filled_quantity': float(order.filled_quantity),
            'target_price': float(order.target_price),
        })
    except ClientOrder.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Order not found'}, status=404)


@login_required
@require_http_methods(["GET"])  # Available inventory to fulfill order
def api_order_available_inventory(request, order_id):
    if not request.user.is_merchant:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    merchant = request.user.merchant_profile
    try:
        order = ClientOrder.objects.get(id=order_id, merchant=merchant)
    except ClientOrder.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Order not found'}, status=404)
    items = MerchantInventory.objects.filter(merchant=merchant).select_related('grade')
    data = [{
        'id': i.id,
        'grade': i.grade.grade_code,
        'quantity': float(i.available_quantity),
        'location': i.storage_location,
    } for i in items]
    return JsonResponse({'success': True, 'inventory': data})


@login_required
@require_http_methods(["POST"])  # Process fulfilling quantity from inventory
def api_order_process(request, order_id):
    if not request.user.is_merchant:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    merchant = request.user.merchant_profile
    try:
        order = ClientOrder.objects.select_for_update().get(id=order_id, merchant=merchant)
        data = json.loads(request.body)
        fill_qty = Decimal(str(data.get('fill_quantity', 0)))
        source_inventory_id = data.get('source_inventory')
        inv = MerchantInventory.objects.select_for_update().get(id=source_inventory_id, merchant=merchant)
        if fill_qty <= 0 or fill_qty > inv.available_quantity:
            return JsonResponse({'success': False, 'error': 'Invalid quantity'}, status=400)
        inv.reserved_quantity += fill_qty
        inv.quantity -= fill_qty
        inv.save()
        order.filled_quantity += fill_qty
        if order.filled_quantity >= order.requested_quantity:
            order.status = 'READY'
        else:
            order.status = 'IN_PROGRESS'
        order.save()
        return JsonResponse({'success': True})
    except (ClientOrder.DoesNotExist, MerchantInventory.DoesNotExist):
        return JsonResponse({'success': False, 'error': 'Not found'}, status=404)


@login_required
@require_http_methods(["POST"])
def implement_recommendation(request, recommendation_id):
    """Mark recommendation as implemented"""
    if not request.user.is_merchant:
        return JsonResponse({'success': False, 'error': 'Unauthorized'})
    
    try:
        merchant = request.user.merchant_profile
        recommendation = get_object_or_404(
            PurchaseRecommendation,
            id=recommendation_id,
            merchant=merchant
        )
        
        data = json.loads(request.body)
        
        recommendation.is_implemented = True
        recommendation.implemented_at = timezone.now()
        recommendation.implementation_notes = data.get('notes', '')
        recommendation.actual_purchase_quantity = data.get('actual_quantity')
        recommendation.actual_purchase_price = data.get('actual_price')
        recommendation.save()
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def dashboard_customization(request):
    """Dashboard layout and widget customization"""
    if not request.user.is_merchant:
        return redirect('timb_dashboard')
    
    merchant = request.user.merchant_profile
    
    # Get current widgets
    widgets = DashboardWidget.objects.filter(
        merchant=merchant
    ).order_by('position_y', 'position_x')
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            action = data.get('action')
            
            if action == 'add_widget':
                widget = DashboardWidget.objects.create(
                    merchant=merchant,
                    widget_type=data['widget_type'],
                    title=data['title'],
                    position_x=data.get('position_x', 0),
                    position_y=data.get('position_y', 0),
                    width=data.get('width', 4),
                    height=data.get('height', 3),
                    settings=data.get('settings', {}),
                    refresh_interval=data.get('refresh_interval', 300)
                )
                
                return JsonResponse({
                    'success': True,
                    'widget_id': widget.id
                })
            
            elif action == 'update_layout':
                for widget_data in data.get('widgets', []):
                    try:
                        widget = DashboardWidget.objects.get(
                            id=widget_data['id'],
                            merchant=merchant
                        )
                        widget.position_x = widget_data['x']
                        widget.position_y = widget_data['y']
                        widget.width = widget_data['width']
                        widget.height = widget_data['height']
                        widget.save()
                    except DashboardWidget.DoesNotExist:
                        continue
                
                return JsonResponse({'success': True})
            
            elif action == 'remove_widget':
                widget = DashboardWidget.objects.get(
                    id=data['widget_id'],
                    merchant=merchant
                )
                widget.delete()
                
                return JsonResponse({'success': True})
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    context = {
        'merchant': merchant,
        'widgets': widgets,
        'widget_types': DashboardWidget.WIDGET_TYPES,
    }
    
    return render(request, 'merchant_app/dashboard_customization.html', context)


@login_required
@require_http_methods(["GET"])
def generate_qr_report(request):
    """Generate secure QR code for inventory report"""
    if not request.user.is_merchant:
        return JsonResponse({'success': False, 'error': 'Unauthorized'})
    
    try:
        from utils.qr_code import qr_manager
        
        merchant = request.user.merchant_profile
        
        # Compile inventory data
        inventory_data = []
        for item in MerchantInventory.objects.filter(merchant=merchant):
            inventory_data.append({
                'grade': item.grade.grade_name,
                'quantity': float(item.quantity),
                'location': item.storage_location,
                'value': float(item.total_value),
                'last_updated': item.last_updated.isoformat()
            })
        
        report_data = {
            'merchant_name': merchant.company_name,
            'report_type': 'inventory_summary',
            'generated_at': timezone.now().isoformat(),
            'inventory': inventory_data,
            'total_items': len(inventory_data),
            'total_value': sum(item['value'] for item in inventory_data)
        }
        
        # Generate QR code
        qr_result = qr_manager.generate_access_token(report_data, expiry_minutes=120)
        
        return JsonResponse({
            'success': True,
            'qr_code': qr_result['qr_code'],
            'expires_at': qr_result['expires_at'],
            'token': qr_result['token']
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


# API endpoints for real-time updates
@login_required
@require_http_methods(["GET"])
def api_dashboard_data(request):
    """API endpoint for dashboard data"""
    if not request.user.is_merchant:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    merchant = request.user.merchant_profile
    today = timezone.now().date()
    
    data = {
        'inventory_count': MerchantInventory.objects.filter(merchant=merchant).count(),
        'low_stock_count': MerchantInventory.objects.filter(
            merchant=merchant,
            quantity__lte=models.F('minimum_threshold')
        ).count(),
        'active_orders': ClientOrder.objects.filter(
            merchant=merchant,
            status__in=['PENDING', 'CONFIRMED', 'IN_PROGRESS']
        ).count(),
        'todays_transactions': Transaction.objects.filter(
            Q(buyer=request.user) | Q(seller=request.user),
            timestamp__date=today
        ).count(),
        'unread_messages': InterMerchantCommunication.objects.filter(
            to_merchant=merchant,
            is_read=False
        ).count(),
        'pending_assessments': FarmerRiskAssessment.objects.filter(
            merchant=merchant,
            is_approved=False
        ).count()
    }
    
    return JsonResponse(data)


@login_required
@require_http_methods(["GET"])
def api_price_alerts(request):
    """API endpoint for price alerts"""
    if not request.user.is_merchant:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    # This would integrate with real-time price monitoring
    # For now, return mock data
    alerts = [
        {
            'grade': 'A1',
            'current_price': 5.25,
            'change': 0.15,
            'percentage_change': 2.95,
            'trend': 'UP'
        },
        {
            'grade': 'L2',
            'current_price': 3.80,
            'change': -0.10,
            'percentage_change': -2.56,
            'trend': 'DOWN'
        }
    ]
    
    return JsonResponse({'alerts': alerts})