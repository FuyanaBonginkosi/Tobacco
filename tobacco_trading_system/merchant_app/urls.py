from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='merchant_dashboard'),
    
    # Profile Management
    path('profile/customize/', views.profile_customization, name='merchant_profile_customization'),
    path('dashboard/customize/', views.dashboard_customization, name='merchant_dashboard_customization'),
    
    # Inventory Management
    path('inventory/', views.inventory_management, name='merchant_inventory'),
    path('inventory/add/', views.add_inventory_item, name='merchant_add_inventory'),
    path('inventory/qr-report/', views.generate_qr_report, name='merchant_generate_qr_report'),
    path('inventory/report/', views.inventory_report, name='merchant_inventory_report'),
    
    # Custom Grades
    path('grades/', views.custom_grades_management, name='merchant_custom_grades'),
    path('grades/create/', views.create_custom_grade, name='merchant_create_custom_grade'),
    
    # Order Management
    path('orders/', views.orders_management, name='merchant_orders'),
    path('orders/create/', views.create_order, name='merchant_create_order'),
    
    # AI Features
    path('ai/recommendations/', views.ai_recommendations, name='merchant_ai_recommendations'),
    path('ai/recommendations/<int:recommendation_id>/implement/', views.implement_recommendation, name='merchant_implement_recommendation'),
    path('farmer-risk/', views.farmer_risk_assessment, name='merchant_farmer_risk_assessment'),
    
    # Aggregation
    path('aggregation/', views.aggregation_dashboard, name='merchant_aggregation_dashboard'),
    path('aggregation/rule/save/', views.save_aggregation_rule, name='merchant_save_aggregation_rule'),
    path('aggregation/rule/<int:rule_id>/run/', views.run_aggregation_rule, name='merchant_run_aggregation_rule'),
    path('aggregation/output/<int:aggregated_id>/', views.aggregated_grade_detail, name='merchant_aggregated_grade_detail'),

    # Inter-Merchant Features
    path('communications/', views.inter_merchant_communications, name='merchant_communications'),
    path('communications/send/', views.send_message, name='merchant_send_message'),
    path('trading/', views.inter_merchant_trading, name='merchant_inter_trading'),
    path('trading/propose/', views.propose_trade, name='merchant_propose_trade'),
    
    # API Endpoints
    path('api/dashboard-data/', views.api_dashboard_data, name='merchant_api_dashboard_data'),
    path('api/price-alerts/', views.api_price_alerts, name='merchant_api_price_alerts'),
    path('api/grades/', views.api_list_grades, name='merchant_api_list_grades'),
    path('api/orders/<int:order_id>/', views.api_order_detail, name='merchant_api_order_detail'),
    path('api/orders/<int:order_id>/available-inventory/', views.api_order_available_inventory, name='merchant_api_order_available_inventory'),
    path('api/orders/<int:order_id>/process/', views.api_order_process, name='merchant_api_order_process'),
]