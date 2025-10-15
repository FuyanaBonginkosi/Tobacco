from django.urls import path
from . import views

app_name = 'timb_dashboard'

urlpatterns = [
    # Main dashboard
    path('', views.dashboard_view, name='dashboard'),
    
    # Transaction management
    path('record-transaction/', views.record_transaction_view, name='record_transaction'),
    path('transactions/', views.TransactionListView.as_view(), name='transaction_list'),
    path('transactions/<str:transaction_id>/', views.TransactionDetailView.as_view(), name='transaction_detail'),
    path('analytics/', views.transaction_analytics_view, name='transaction_analytics'),
    
    # Price management
    path('prices/', views.price_monitoring_view, name='price_monitoring'),
    path('update-daily-prices/', views.update_daily_prices, name='update_daily_prices'),
    path('market/open/', views.open_market, name='open_market'),
    path('market/close/', views.close_market, name='close_market'),
    
    # Floor management
    path('floors/', views.floor_management_view, name='floor_management'),
    
    # Grade management
    path('grades/', views.grade_management_view, name='grade_management'),
    
    # API endpoints
    path('api/realtime-data/', views.api_realtime_data, name='api_realtime_data'),
]