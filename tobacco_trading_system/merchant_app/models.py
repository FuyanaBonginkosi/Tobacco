from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from timb_dashboard.models import Merchant, TobaccoGrade
from utils.encryption import encryption
import json
import uuid


class MerchantProfile(models.Model):
    """Extended merchant profile for customization and branding"""
    
    BUSINESS_TYPES = [
        ('PROCESSOR', 'Tobacco Processor'),
        ('EXPORTER', 'Tobacco Exporter'),
        ('MANUFACTURER', 'Tobacco Manufacturer'),
        ('TRADER', 'Tobacco Trader'),
        ('WAREHOUSE', 'Warehouse Operator'),
    ]
    
    VISIBILITY_CHOICES = [
        ('PUBLIC', 'Public - Visible to all'),
        ('MERCHANTS_ONLY', 'Merchants Only'),
        ('PRIVATE', 'Private - Not visible'),
    ]
    
    THEME_CHOICES = [
        ('light', 'Light Theme'),
        ('dark', 'Dark Theme'),
        ('blue', 'Blue Theme'),
        ('green', 'Green Theme'),
        ('custom', 'Custom Theme'),
    ]
    
    merchant = models.OneToOneField(Merchant, on_delete=models.CASCADE, related_name='extended_profile')
    
    # Branding and Customization
    company_logo = models.ImageField(upload_to='merchant_logos/', blank=True, null=True)
    company_banner = models.ImageField(upload_to='merchant_banners/', blank=True, null=True)
    brand_colors = models.JSONField(default=dict, blank=True)
    theme_preference = models.CharField(max_length=20, choices=THEME_CHOICES, default='light')
    custom_css = models.TextField(blank=True)
    
    # Business Information
    business_type = models.CharField(max_length=20, choices=BUSINESS_TYPES, default='TRADER')
    business_description = models.TextField(max_length=1000, blank=True)
    founding_year = models.IntegerField(blank=True, null=True)
    number_of_employees = models.CharField(max_length=50, blank=True)
    annual_capacity = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, help_text="Annual processing capacity in kg")
    
    # Contact & Location
    headquarters_address = models.TextField(blank=True)
    phone_primary = models.CharField(max_length=20, blank=True)
    phone_secondary = models.CharField(max_length=20, blank=True)
    email_business = models.EmailField(blank=True)
    website_url = models.URLField(blank=True)
    
    # Social Media
    linkedin_url = models.URLField(blank=True)
    facebook_url = models.URLField(blank=True)
    twitter_url = models.URLField(blank=True)
    
    # Certifications & Standards
    certifications = models.JSONField(default=list, blank=True)
    quality_standards = models.JSONField(default=list, blank=True)
    
    # Trading Preferences
    preferred_grades = models.ManyToManyField(TobaccoGrade, blank=True)
    minimum_order_value = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    payment_terms = models.CharField(max_length=100, blank=True)
    delivery_regions = models.JSONField(default=list, blank=True)
    
    # Public Visibility
    profile_visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default='MERCHANTS_ONLY')
    show_contact_info = models.BooleanField(default=False)
    show_business_stats = models.BooleanField(default=True)
    show_certifications = models.BooleanField(default=True)
    allow_direct_contact = models.BooleanField(default=True)
    allow_public_advertising = models.BooleanField(default=False)
    
    # Feature Preferences
    enable_ai_recommendations = models.BooleanField(default=True)
    enable_risk_assessment = models.BooleanField(default=True)
    enable_custom_grades = models.BooleanField(default=True)
    enable_inventory_management = models.BooleanField(default=True)
    enable_order_management = models.BooleanField(default=True)
    enable_inter_merchant_trading = models.BooleanField(default=True)
    
    # Dashboard Customization
    dashboard_layout = models.JSONField(default=dict, blank=True)
    widget_preferences = models.JSONField(default=dict, blank=True)
    theme_customization = models.JSONField(default=dict, blank=True)
    
    # Notification Preferences
    email_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=False)
    price_alert_threshold = models.DecimalField(max_digits=5, decimal_places=2, default=10.00)
    
    # Encrypted sensitive business data
    encrypted_business_data = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Merchant Profile'
        verbose_name_plural = 'Merchant Profiles'
    
    def __str__(self):
        return f"{self.merchant.company_name} - Extended Profile"
    
    def set_business_data(self, data):
        """Encrypt and store sensitive business data"""
        if data:
            self.encrypted_business_data = encryption.encrypt_data(data)
    
    def get_business_data(self):
        """Decrypt and retrieve sensitive business data"""
        if self.encrypted_business_data:
            return encryption.decrypt_data(self.encrypted_business_data)
        return {}


class MerchantInventory(models.Model):
    """Enhanced merchant inventory management"""
    
    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name='inventory')
    grade = models.ForeignKey(TobaccoGrade, on_delete=models.CASCADE)
    
    # Inventory Details
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    reserved_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    average_cost = models.DecimalField(max_digits=8, decimal_places=2)
    
    # Quality Information
    quality_grade = models.CharField(max_length=20, blank=True)
    moisture_content = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    origin_location = models.CharField(max_length=100, blank=True)
    harvest_season = models.CharField(max_length=20, blank=True)
    batch_number = models.CharField(max_length=50, blank=True)
    
    # Storage Information
    storage_location = models.CharField(max_length=100, blank=True)
    storage_conditions = models.JSONField(default=dict, blank=True)
    warehouse_section = models.CharField(max_length=50, blank=True)
    
    # Alerts and Thresholds
    minimum_threshold = models.DecimalField(max_digits=10, decimal_places=2, default=100)
    reorder_point = models.DecimalField(max_digits=10, decimal_places=2, default=200)
    maximum_capacity = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    
    # Dates
    last_purchase_date = models.DateTimeField(blank=True, null=True)
    expiry_date = models.DateField(blank=True, null=True)
    last_movement_date = models.DateTimeField(auto_now=True)
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['merchant', 'grade', 'batch_number']
        verbose_name = 'Merchant Inventory'
        verbose_name_plural = 'Merchant Inventories'
    
    def __str__(self):
        return f"{self.merchant.company_name} - {self.grade.grade_name}: {self.quantity}kg"
    
    @property
    def available_quantity(self):
        """Get available quantity (total - reserved)"""
        return self.quantity - self.reserved_quantity
    
    @property
    def total_value(self):
        """Calculate total inventory value"""
        return self.quantity * self.average_cost
    
    @property
    def is_low_stock(self):
        """Check if inventory is below minimum threshold"""
        return self.available_quantity <= self.minimum_threshold
    
    @property
    def turnover_days(self):
        """Calculate inventory turnover in days"""
        if self.last_movement_date and self.last_purchase_date:
            return (self.last_movement_date - self.last_purchase_date).days
        return 0
    
    def reserve_quantity(self, amount):
        """Reserve quantity for an order"""
        if amount <= self.available_quantity:
            self.reserved_quantity += amount
            self.save()
            return True
        return False
    
    def release_quantity(self, amount):
        """Release reserved quantity"""
        if amount <= self.reserved_quantity:
            self.reserved_quantity -= amount
            self.save()
            return True
        return False


class CustomGrade(models.Model):
    """Enhanced custom tobacco grades created by merchants"""
    
    QUALITY_STANDARDS = [
        ('PREMIUM', 'Premium'),
        ('STANDARD', 'Standard'),
        ('BASIC', 'Basic'),
    ]
    
    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name='custom_grades')
    custom_grade_name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    # Pricing
    target_price = models.DecimalField(max_digits=8, decimal_places=2)
    minimum_order_quantity = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    price_markup_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=15.00)
    
    # Quality specifications
    quality_standard = models.CharField(max_length=20, choices=QUALITY_STANDARDS, default='STANDARD')
    flavor_profile = models.CharField(max_length=50, blank=True)
    burn_rate = models.CharField(max_length=20, blank=True)
    moisture_content = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    nicotine_level = models.CharField(max_length=20, blank=True)
    ash_content = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    
    # Market positioning
    target_market = models.CharField(max_length=100, blank=True)
    competitive_advantages = models.JSONField(default=list, blank=True)
    marketing_description = models.TextField(blank=True)
    
    # Production tracking
    total_produced = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_sold = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    production_cost_per_kg = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    is_draft = models.BooleanField(default=False)
    is_public = models.BooleanField(default=False)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['merchant', 'custom_grade_name']
        verbose_name = 'Custom Grade'
        verbose_name_plural = 'Custom Grades'
    
    def __str__(self):
        return f"{self.merchant.company_name} - {self.custom_grade_name}"
    
    @property
    def base_cost(self):
        """Calculate base cost from components"""
        total_cost = 0
        total_percentage = 0
        
        for component in self.components.all():
            if component.percentage > 0:
                cost_contribution = (component.percentage / 100) * component.base_grade.base_price
                total_cost += cost_contribution
                total_percentage += component.percentage
        
        return total_cost if total_percentage > 0 else 0
    
    @property
    def profit_margin(self):
        """Calculate profit margin"""
        base_cost = self.base_cost
        if base_cost > 0:
            return ((self.target_price - base_cost) / base_cost) * 100
        return 0
    
    @property
    def inventory_available(self):
        """Calculate available inventory for this custom grade"""
        # This would require complex calculation based on component availability
        # For now, return a simplified version
        return self.total_produced - self.total_sold


class GradeComponent(models.Model):
    """Enhanced components that make up a custom grade"""
    
    custom_grade = models.ForeignKey(CustomGrade, on_delete=models.CASCADE, related_name='components')
    base_grade = models.ForeignKey(TobaccoGrade, on_delete=models.CASCADE)
    percentage = models.DecimalField(max_digits=5, decimal_places=2)
    minimum_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Quality requirements for this component
    min_moisture_content = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    max_moisture_content = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    quality_notes = models.TextField(blank=True)
    
    # Cost tracking
    average_cost_per_kg = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    total_used = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    class Meta:
        unique_together = ['custom_grade', 'base_grade']
        verbose_name = 'Grade Component'
        verbose_name_plural = 'Grade Components'
    
    def __str__(self):
        return f"{self.custom_grade.custom_grade_name} - {self.base_grade.grade_name} ({self.percentage}%)"
    
    @property
    def cost_contribution(self):
        """Calculate this component's contribution to total cost"""
        if self.average_cost_per_kg:
            return (self.percentage / 100) * self.average_cost_per_kg
        return (self.percentage / 100) * self.base_grade.base_price


class ClientOrder(models.Model):
    """Enhanced orders from clients to merchants"""
    
    ORDER_STATUS = [
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('IN_PROGRESS', 'In Progress'),
        ('PARTIALLY_FILLED', 'Partially Filled'),
        ('READY', 'Ready for Delivery'),
        ('DELIVERED', 'Delivered'),
        ('CANCELLED', 'Cancelled'),
        ('ON_HOLD', 'On Hold'),
    ]
    
    PAYMENT_STATUS = [
        ('PENDING', 'Pending'),
        ('PARTIAL', 'Partial Payment'),
        ('PAID', 'Fully Paid'),
        ('OVERDUE', 'Overdue'),
    ]
    
    PRIORITY_LEVELS = [
        ('LOW', 'Low'),
        ('NORMAL', 'Normal'),
        ('HIGH', 'High'),
        ('URGENT', 'Urgent'),
    ]
    
    order_number = models.CharField(max_length=50, unique=True)
    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name='client_orders')
    
    # Client Information
    client_name = models.CharField(max_length=200)
    client_email = models.EmailField(blank=True)
    client_phone = models.CharField(max_length=20, blank=True)
    client_address = models.TextField(blank=True)
    client_company = models.CharField(max_length=200, blank=True)
    
    # Order Details
    grade = models.ForeignKey(TobaccoGrade, on_delete=models.CASCADE, blank=True, null=True)
    custom_grade = models.ForeignKey(CustomGrade, on_delete=models.CASCADE, blank=True, null=True)
    requested_quantity = models.DecimalField(max_digits=10, decimal_places=2)
    filled_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    target_price = models.DecimalField(max_digits=8, decimal_places=2)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Order Management
    priority = models.CharField(max_length=10, choices=PRIORITY_LEVELS, default='NORMAL')
    expected_delivery_date = models.DateField(blank=True, null=True)
    actual_delivery_date = models.DateField(blank=True, null=True)
    
    # Status
    status = models.CharField(max_length=20, choices=ORDER_STATUS, default='PENDING')
    payment_status = models.CharField(max_length=10, choices=PAYMENT_STATUS, default='PENDING')
    
    # Quality Requirements
    quality_specifications = models.JSONField(default=dict, blank=True)
    moisture_requirement = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    packaging_requirements = models.TextField(blank=True)
    
    # Dates
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    
    # Notes and Communication
    order_notes = models.TextField(blank=True)
    special_requirements = models.TextField(blank=True)
    internal_notes = models.TextField(blank=True)
    
    # Tracking
    tracking_number = models.CharField(max_length=100, blank=True)
    shipping_method = models.CharField(max_length=100, blank=True)
    
    class Meta:
        verbose_name = 'Client Order'
        verbose_name_plural = 'Client Orders'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Order {self.order_number} - {self.client_name}"
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
        
        # Calculate total amount
        self.total_amount = self.requested_quantity * self.target_price
        
        super().save(*args, **kwargs)
    
    def generate_order_number(self):
        """Generate unique order number"""
        prefix = f"ORD-{timezone.now().strftime('%Y%m%d')}"
        return f"{prefix}-{str(uuid.uuid4())[:8].upper()}"
    
    @property
    def get_grade_name(self):
        """Get the grade name (regular or custom)"""
        if self.custom_grade:
            return self.custom_grade.custom_grade_name
        elif self.grade:
            return self.grade.grade_name
        return "Unknown Grade"
    
    @property
    def completion_percentage(self):
        """Calculate order completion percentage"""
        if self.requested_quantity > 0:
            return (self.filled_quantity / self.requested_quantity) * 100
        return 0
    
    @property
    def is_overdue(self):
        """Check if order is overdue"""
        if self.expected_delivery_date and self.status not in ['DELIVERED', 'CANCELLED']:
            return timezone.now().date() > self.expected_delivery_date
        return False


class FarmerRiskAssessment(models.Model):
    """Enhanced AI-powered farmer risk assessment"""
    
    RISK_LEVELS = [
        ('LOW', 'Low Risk'),
        ('MEDIUM', 'Medium Risk'),
        ('HIGH', 'High Risk'),
        ('CRITICAL', 'Critical Risk'),
    ]
    
    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name='farmer_assessments')
    
    # Farmer Information
    farmer_name = models.CharField(max_length=200)
    farmer_id = models.CharField(max_length=50, blank=True)
    location = models.CharField(max_length=200)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    
    # Farm Details
    total_hectares = models.DecimalField(max_digits=10, decimal_places=2)
    years_experience = models.IntegerField()
    primary_tobacco_type = models.CharField(max_length=50)
    previous_yields = models.JSONField(default=list, blank=True)
    farming_methods = models.CharField(max_length=100, blank=True)
    irrigation_available = models.BooleanField(default=False)
    
    # Financial Information
    annual_income = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    debt_level = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    credit_score = models.IntegerField(blank=True, null=True)
    previous_defaults = models.IntegerField(default=0)
    bank_references = models.TextField(blank=True)
    collateral_available = models.TextField(blank=True)
    
    # Contract Details
    proposed_contract_value = models.DecimalField(max_digits=12, decimal_places=2)
    proposed_quantity = models.DecimalField(max_digits=10, decimal_places=2)
    contract_duration_months = models.IntegerField()
    proposed_price_per_kg = models.DecimalField(max_digits=8, decimal_places=2)
    
    # Additional Risk Factors
    weather_risk_area = models.BooleanField(default=False)
    market_access_score = models.IntegerField(default=70)
    transportation_distance = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    alternative_buyers_count = models.IntegerField(default=0)
    
    # AI Assessment Results
    risk_score = models.DecimalField(max_digits=5, decimal_places=3, blank=True, null=True)
    risk_level = models.CharField(max_length=10, choices=RISK_LEVELS, blank=True)
    ai_recommendation = models.TextField(blank=True)
    risk_factors = models.JSONField(default=list, blank=True)
    mitigation_strategies = models.JSONField(default=list, blank=True)
    
    # Financial Metrics (calculated by AI)
    debt_to_income_ratio = models.DecimalField(max_digits=5, decimal_places=3, blank=True, null=True)
    contract_to_income_ratio = models.DecimalField(max_digits=5, decimal_places=3, blank=True, null=True)
    projected_yield_per_hectare = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    
    # Assessment metadata
    assessment_date = models.DateTimeField(auto_now_add=True)
    assessed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    is_approved = models.BooleanField(default=False)
    approval_notes = models.TextField(blank=True)
    
    # Contract tracking
    contract_signed = models.BooleanField(default=False)
    contract_signed_date = models.DateTimeField(blank=True, null=True)
    
    # Encrypted sensitive data
    encrypted_farmer_data = models.TextField(blank=True)
    
    class Meta:
        verbose_name = 'Farmer Risk Assessment'
        verbose_name_plural = 'Farmer Risk Assessments'
        ordering = ['-assessment_date']
    
    def __str__(self):
        return f"Risk Assessment - {self.farmer_name} ({self.get_risk_level_display()})"
    
    def set_farmer_data(self, data):
        """Encrypt and store sensitive farmer data"""
        if data:
            self.encrypted_farmer_data = encryption.encrypt_data(data)
    
    def get_farmer_data(self):
        """Decrypt and retrieve sensitive farmer data"""
        if self.encrypted_farmer_data:
            return encryption.decrypt_data(self.encrypted_farmer_data)
        return {}


class PurchaseRecommendation(models.Model):
    """Enhanced AI purchase recommendations for merchants"""
    
    RECOMMENDATION_TYPES = [
        ('INVENTORY_GAP', 'Inventory Gap'),
        ('MARKET_OPPORTUNITY', 'Market Opportunity'),
        ('SEASONAL_BUY', 'Seasonal Purchase'),
        ('PRICE_ARBITRAGE', 'Price Arbitrage'),
        ('CUSTOM_GRADE_COMPONENT', 'Custom Grade Component'),
        ('RISK_MITIGATION', 'Risk Mitigation'),
    ]
    
    PRIORITY_LEVELS = [
        ('LOW', 'Low Priority'),
        ('MEDIUM', 'Medium Priority'),
        ('HIGH', 'High Priority'),
        ('URGENT', 'Urgent'),
    ]
    
    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name='purchase_recommendations')
    recommendation_type = models.CharField(max_length=30, choices=RECOMMENDATION_TYPES)
    grade = models.ForeignKey(TobaccoGrade, on_delete=models.CASCADE)
    
    # Recommendation Details
    recommended_quantity = models.DecimalField(max_digits=10, decimal_places=2)
    recommended_price = models.DecimalField(max_digits=8, decimal_places=2)
    estimated_cost = models.DecimalField(max_digits=12, decimal_places=2)
    expected_roi = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    
    # Market Analysis
    current_market_price = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    price_trend = models.CharField(max_length=20, blank=True)
    market_demand_level = models.CharField(max_length=20, blank=True)
    competitor_activity = models.TextField(blank=True)
    
    # AI Analysis
    confidence_score = models.DecimalField(max_digits=5, decimal_places=3)
    priority = models.CharField(max_length=10, choices=PRIORITY_LEVELS, default='MEDIUM')
    reasoning = models.TextField()
    market_factors = models.JSONField(default=list, blank=True)
    risk_assessment = models.JSONField(default=dict, blank=True)
    
    # Timing
    optimal_purchase_window_start = models.DateTimeField(blank=True, null=True)
    optimal_purchase_window_end = models.DateTimeField(blank=True, null=True)
    urgency_score = models.DecimalField(max_digits=5, decimal_places=2, default=50.00)
    
    # Status and Tracking
    is_active = models.BooleanField(default=True)
    is_implemented = models.BooleanField(default=False)
    implementation_notes = models.TextField(blank=True)
    implemented_at = models.DateTimeField(blank=True, null=True)
    
    # Metadata
    generated_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    updated_at = models.DateTimeField(auto_now=True)
    
    # Performance tracking
    actual_purchase_quantity = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    actual_purchase_price = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    actual_roi = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    
    class Meta:
        verbose_name = 'Purchase Recommendation'
        verbose_name_plural = 'Purchase Recommendations'
        ordering = ['-priority', '-confidence_score', '-generated_at']
    
    def __str__(self):
        return f"{self.merchant.company_name} - {self.grade.grade_name} ({self.get_priority_display()})"
    
    def save(self, *args, **kwargs):
        if not self.expires_at:
            # Set expiry to 7 days from generation
            self.expires_at = timezone.now() + timezone.timedelta(days=7)
        super().save(*args, **kwargs)
    
    @property
    def is_expired(self):
        """Check if recommendation has expired"""
        return timezone.now() > self.expires_at
    
    @property
    def days_until_expiry(self):
        """Calculate days until expiry"""
        if self.expires_at:
            delta = self.expires_at - timezone.now()
            return max(0, delta.days)
        return 0
    
    @property
    def potential_profit(self):
        """Calculate potential profit from recommendation"""
        if self.expected_roi and self.estimated_cost:
            return (self.expected_roi / 100) * self.estimated_cost
        return 0


class DashboardWidget(models.Model):
    """Enhanced customizable dashboard widgets for merchants"""
    
    WIDGET_TYPES = [
        ('INVENTORY_SUMMARY', 'Inventory Summary'),
        ('PRICE_TRENDS', 'Price Trends'),
        ('ORDER_STATUS', 'Order Status'),
        ('AI_RECOMMENDATIONS', 'AI Recommendations'),
        ('MARKET_NEWS', 'Market News'),
        ('FINANCIAL_OVERVIEW', 'Financial Overview'),
        ('RISK_ALERTS', 'Risk Alerts'),
        ('CUSTOM_GRADES', 'Custom Grades'),
        ('FARMER_ASSESSMENTS', 'Farmer Assessments'),
        ('TRANSACTION_HISTORY', 'Transaction History'),
        ('PERFORMANCE_METRICS', 'Performance Metrics'),
        ('WEATHER_FORECAST', 'Weather Forecast'),
    ]
    
    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name='dashboard_widgets')
    widget_type = models.CharField(max_length=30, choices=WIDGET_TYPES)
    title = models.CharField(max_length=100)
    
    # Layout
    position_x = models.IntegerField(default=0)
    position_y = models.IntegerField(default=0)
    width = models.IntegerField(default=4)
    height = models.IntegerField(default=3)
    
    # Appearance
    is_visible = models.BooleanField(default=True)
    background_color = models.CharField(max_length=7, default='#ffffff')
    text_color = models.CharField(max_length=7, default='#000000')
    border_style = models.CharField(max_length=50, default='solid')
    
    # Configuration
    settings = models.JSONField(default=dict, blank=True)
    refresh_interval = models.IntegerField(default=300)  # seconds
    data_filters = models.JSONField(default=dict, blank=True)
    
    # Permissions
    requires_approval = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['merchant', 'widget_type']
        ordering = ['position_y', 'position_x']
        verbose_name = 'Dashboard Widget'
        verbose_name_plural = 'Dashboard Widgets'
    
    def __str__(self):
        return f"{self.merchant.company_name} - {self.title}"


class InterMerchantCommunication(models.Model):
    """Enhanced private communication between merchants"""
    
    MESSAGE_TYPES = [
        ('INQUIRY', 'General Inquiry'),
        ('TRADE_REQUEST', 'Trade Request'),
        ('NEGOTIATION', 'Price Negotiation'),
        ('CONTRACT_DISCUSSION', 'Contract Discussion'),
        ('LOGISTICS', 'Logistics Coordination'),
        ('QUALITY_ISSUE', 'Quality Issue'),
        ('PAYMENT_DISCUSSION', 'Payment Discussion'),
    ]
    
    from_merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name='sent_messages')
    to_merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name='received_messages')
    message_type = models.CharField(max_length=30, choices=MESSAGE_TYPES, default='INQUIRY')
    subject = models.CharField(max_length=200)
    message = models.TextField()
    
    # Attachments
    attachment_1 = models.FileField(upload_to='merchant_communications/', blank=True, null=True)
    attachment_2 = models.FileField(upload_to='merchant_communications/', blank=True, null=True)
    attachment_3 = models.FileField(upload_to='merchant_communications/', blank=True, null=True)
    
    # Related trade data (encrypted)
    encrypted_trade_data = models.TextField(blank=True)
    
    # Message status
    is_read = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)
    is_starred = models.BooleanField(default=False)
    
    # AI analysis
    is_flagged_by_ai = models.BooleanField(default=False)
    flagged_reason = models.TextField(blank=True)
    sentiment_score = models.DecimalField(max_digits=5, decimal_places=3, blank=True, null=True)
    
    # Threading
    parent_message = models.ForeignKey('self', on_delete=models.CASCADE, blank=True, null=True, related_name='replies')
    thread_id = models.CharField(max_length=50, blank=True)
    
    # Timestamps
    sent_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        verbose_name = 'Inter-Merchant Communication'
        verbose_name_plural = 'Inter-Merchant Communications'
        ordering = ['-sent_at']
    
    def __str__(self):
        return f"{self.from_merchant.company_name} → {self.to_merchant.company_name}: {self.subject}"
    
    def save(self, *args, **kwargs):
        if not self.thread_id:
            if self.parent_message:
                self.thread_id = self.parent_message.thread_id
            else:
                self.thread_id = str(uuid.uuid4())[:12]
        super().save(*args, **kwargs)
    
    def set_trade_data(self, data):
        """Encrypt and store trade-related data"""
        if data:
            self.encrypted_trade_data = encryption.encrypt_data(data)
    
    def get_trade_data(self):
        """Decrypt and retrieve trade-related data"""
        if self.encrypted_trade_data:
            return encryption.decrypt_data(self.encrypted_trade_data)
        return {}


class InterMerchantTrade(models.Model):
    """Enhanced trading between merchants with TIMB oversight"""
    
    TRADE_STATUS = [
        ('PROPOSED', 'Proposed'),
        ('NEGOTIATING', 'Under Negotiation'),
        ('AGREED', 'Agreed'),
        ('PENDING_TIMB_APPROVAL', 'Pending TIMB Approval'),
        ('APPROVED', 'TIMB Approved'),
        ('REJECTED', 'TIMB Rejected'),
        ('IN_TRANSIT', 'In Transit'),
        ('DELIVERED', 'Delivered'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
        ('DISPUTED', 'Disputed'),
    ]
    
    PAYMENT_TERMS = [
        ('CASH_ON_DELIVERY', 'Cash on Delivery'),
        ('NET_30', 'Net 30 Days'),
        ('NET_60', 'Net 60 Days'),
        ('ADVANCE_PAYMENT', 'Advance Payment'),
        ('ESCROW', 'Escrow Service'),
    ]
    
    trade_id = models.CharField(max_length=50, unique=True)
    seller_merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name='sales')
    buyer_merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name='purchases')
    
    # Trade Details
    grade = models.ForeignKey(TobaccoGrade, on_delete=models.CASCADE)
    custom_grade = models.ForeignKey(CustomGrade, on_delete=models.CASCADE, blank=True, null=True)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    agreed_price_per_kg = models.DecimalField(max_digits=8, decimal_places=2)
    total_value = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Terms and Conditions
    payment_terms = models.CharField(max_length=30, choices=PAYMENT_TERMS, default='NET_30')
    delivery_terms = models.TextField(blank=True)
    quality_requirements = models.JSONField(default=dict, blank=True)
    delivery_location = models.CharField(max_length=200, blank=True)
    delivery_date = models.DateField(blank=True, null=True)
    
    # Trade Status
    status = models.CharField(max_length=25, choices=TRADE_STATUS, default='PROPOSED')
    proposed_at = models.DateTimeField(auto_now_add=True)
    agreed_at = models.DateTimeField(blank=True, null=True)
    timb_reviewed_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    
    # TIMB Oversight
    timb_reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True)
    timb_notes = models.TextField(blank=True)
    is_flagged_for_review = models.BooleanField(default=False)
    fraud_risk_score = models.DecimalField(max_digits=5, decimal_places=3, blank=True, null=True)
    
    # AI Analysis
    price_fairness_score = models.DecimalField(max_digits=5, decimal_places=3, blank=True, null=True)
    market_price_deviation = models.DecimalField(max_digits=5, decimal_places=3, blank=True, null=True)
    risk_factors = models.JSONField(default=list, blank=True)
    
    # Documentation
    contract_document = models.FileField(upload_to='trade_contracts/', blank=True, null=True)
    delivery_receipt = models.FileField(upload_to='delivery_receipts/', blank=True, null=True)
    quality_certificate = models.FileField(upload_to='quality_certificates/', blank=True, null=True)
    
    # Financial
    deposit_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    deposit_paid = models.BooleanField(default=False)
    payment_completed = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = 'Inter-Merchant Trade'
        verbose_name_plural = 'Inter-Merchant Trades'
        ordering = ['-proposed_at']
    
    def __str__(self):
        return f"Trade {self.trade_id} - {self.seller_merchant.company_name} → {self.buyer_merchant.company_name}"
    
    def save(self, *args, **kwargs):
        if not self.trade_id:
            self.trade_id = self.generate_trade_id()
        
        # Calculate total value
        self.total_value = self.quantity * self.agreed_price_per_kg
        
        super().save(*args, **kwargs)
    
    def generate_trade_id(self):
        """Generate unique trade ID"""
        return f"TRD-{timezone.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
    
    @property
    def is_overdue(self):
        """Check if trade is overdue"""
        if self.delivery_date and self.status not in ['COMPLETED', 'CANCELLED']:
            return timezone.now().date() > self.delivery_date
        return False
    
    @property
    def days_since_proposal(self):
        """Calculate days since trade was proposed"""
        return (timezone.now() - self.proposed_at).days











class AggregationRuleSet(models.Model):
    """Merchant-configurable rule set for generating aggregated grades.

    Four rule types are supported:
    - AI_TREND: AI aggregates based on TIMB grade trends (e.g., by category/price clusters)
    - AI_SPEC: AI aggregates to match a user-described spec (color, position, nicotine, end product)
    - USER_RULE: Explicit user-defined composition rules
    - AI_CLIENT_DEMAND: AI aggregates to satisfy active client order demand
    """

    RULE_TYPES = [
        ("AI_TREND", "AI aggregation - market trends"),
        ("AI_SPEC", "AI aggregation - user specification"),
        ("USER_RULE", "User-defined aggregation rule"),
        ("AI_CLIENT_DEMAND", "AI aggregation - client demand"),
    ]

    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name="aggregation_rule_sets")
    name = models.CharField(max_length=120)
    rule_type = models.CharField(max_length=20, choices=RULE_TYPES)
    description = models.TextField(blank=True)
    # Arbitrary parameters depending on rule type (e.g., desired color, nicotine range, end product, constraints)
    parameters = models.JSONField(default=dict, blank=True)

    # Whether to limit results to current inventory (otherwise consider all TIMB grades first)
    limit_to_inventory = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Aggregation Rule Set"
        verbose_name_plural = "Aggregation Rule Sets"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["merchant", "rule_type", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.merchant.company_name} - {self.name} ({self.rule_type})"


class AggregatedGrade(models.Model):
    """Aggregated grade output produced by a rule run.

    Stores the calculated composition by TIMB grades along with derived
    characteristics (e.g., color, expected nicotine range) and quantity plan.
    """

    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name="aggregated_grades")
    rule_set = models.ForeignKey(AggregationRuleSet, on_delete=models.CASCADE, related_name="outputs")

    # Identity
    name = models.CharField(max_length=120)
    label = models.CharField(max_length=120, blank=True)

    # Derived characteristics (summary the UI can render)
    characteristics = models.JSONField(default=dict, blank=True)

    # Quantity planning (computed using inventory snapshot when applicable)
    total_quantity_kg = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    inventory_snapshot = models.JSONField(default=dict, blank=True)

    # Timestamps
    computed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-computed_at", "name"]
        indexes = [
            models.Index(fields=["merchant", "-computed_at"]),
            models.Index(fields=["rule_set", "-computed_at"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.merchant.company_name})"

    @property
    def composition_percentages(self):
        """Return {grade_id: percentage} mapping from components."""
        percentages = {}
        for c in self.components.all():
            percentages[c.base_grade_id] = float(c.percentage)
        return percentages


class AggregatedGradeComponent(models.Model):
    """Normalized composition of an aggregated grade by base TIMB grades."""

    aggregated_grade = models.ForeignKey(
        AggregatedGrade,
        on_delete=models.CASCADE,
        related_name="components",
    )
    base_grade = models.ForeignKey(TobaccoGrade, on_delete=models.CASCADE)
    percentage = models.DecimalField(max_digits=5, decimal_places=2)
    kilograms = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ["aggregated_grade", "base_grade"]
        verbose_name = "Aggregated Grade Component"
        verbose_name_plural = "Aggregated Grade Components"

    def __str__(self):
        return f"{self.aggregated_grade.name} - {self.base_grade.grade_code} ({self.percentage}%)"

class AIRecommendation(models.Model):
    """AI-generated recommendations for merchants"""
    RECOMMENDATION_TYPES = [
        ('PRICING', 'Pricing Optimization'),
        ('INVENTORY', 'Inventory Management'),
        ('MARKET', 'Market Opportunity'),
        ('RISK', 'Risk Assessment'),
        ('QUALITY', 'Quality Improvement'),
    ]
    
    CONFIDENCE_LEVELS = [
        ('LOW', 'Low (< 60%)'),
        ('MEDIUM', 'Medium (60-80%)'),
        ('HIGH', 'High (> 80%)'),
    ]
    
    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name='ai_recommendations')
    recommendation_type = models.CharField(max_length=20, choices=RECOMMENDATION_TYPES)
    title = models.CharField(max_length=200)
    description = models.TextField()
    
    # AI analysis data
    confidence_level = models.CharField(max_length=10, choices=CONFIDENCE_LEVELS)
    confidence_score = models.DecimalField(max_digits=5, decimal_places=2)  # 0-100
    data_sources = models.JSONField(default=list)
    analysis_results = models.JSONField(default=dict)
    
    # Recommendation details
    recommended_action = models.TextField()
    potential_impact = models.TextField()
    implementation_steps = models.JSONField(default=list)
    
    # Related objects
    grade = models.ForeignKey(TobaccoGrade, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    is_implemented = models.BooleanField(default=False)
    implementation_date = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'merchant_ai_recommendations'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['merchant', '-created_at']),
            models.Index(fields=['recommendation_type']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.merchant.company_name}"
    
    @property
    def is_expired(self):
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False


class MarketAnalysis(models.Model):
    """Market analysis and trends"""
    ANALYSIS_TYPES = [
        ('PRICE_TREND', 'Price Trend Analysis'),
        ('DEMAND_FORECAST', 'Demand Forecasting'),
        ('SUPPLY_ANALYSIS', 'Supply Analysis'),
        ('SEASONAL_PATTERN', 'Seasonal Pattern'),
        ('GRADE_PERFORMANCE', 'Grade Performance'),
    ]
    
    analysis_type = models.CharField(max_length=20, choices=ANALYSIS_TYPES)
    title = models.CharField(max_length=200)
    description = models.TextField()
    
    # Analysis data
    analysis_period_start = models.DateField()
    analysis_period_end = models.DateField()
    data_points = models.JSONField(default=list)
    statistical_results = models.JSONField(default=dict)
    
    # Results
    key_findings = models.JSONField(default=list)
    recommendations = models.TextField()
    confidence_score = models.DecimalField(max_digits=5, decimal_places=2)
    
    # Related objects
    grade = models.ForeignKey(TobaccoGrade, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Status
    is_published = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'merchant_market_analysis'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['analysis_type']),
            models.Index(fields=['grade']),
            models.Index(fields=['is_published']),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.analysis_period_start} - {self.analysis_period_end})"


class PriceAlert(models.Model):
    """Price alerts for merchants"""
    ALERT_TYPES = [
        ('PRICE_INCREASE', 'Price Increase'),
        ('PRICE_DECREASE', 'Price Decrease'),
        ('TARGET_PRICE', 'Target Price Reached'),
        ('VOLATILITY', 'High Volatility'),
    ]
    
    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name='price_alerts')
    grade = models.ForeignKey(TobaccoGrade, on_delete=models.CASCADE)
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    
    # Alert conditions
    target_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    percentage_change = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    is_triggered = models.BooleanField(default=False)
    triggered_at = models.DateTimeField(null=True, blank=True)
    triggered_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'merchant_price_alerts'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['merchant', 'grade']),
            models.Index(fields=['is_active', 'is_triggered']),
        ]
    
    def __str__(self):
        return f"{self.merchant.company_name} - {self.grade.grade_code} Alert"


class AggregationRule(models.Model):
    """Data aggregation rules for analytics"""
    AGGREGATION_TYPES = [
        ('SUM', 'Sum'),
        ('AVERAGE', 'Average'),
        ('COUNT', 'Count'),
        ('MIN', 'Minimum'),
        ('MAX', 'Maximum'),
    ]
    
    TIME_PERIODS = [
        ('DAILY', 'Daily'),
        ('WEEKLY', 'Weekly'),
        ('MONTHLY', 'Monthly'),
        ('QUARTERLY', 'Quarterly'),
        ('YEARLY', 'Yearly'),
    ]
    
    name = models.CharField(max_length=100)
    description = models.TextField()
    source_model = models.CharField(max_length=100)
    source_field = models.CharField(max_length=100)
    aggregation_type = models.CharField(max_length=10, choices=AGGREGATION_TYPES)
    time_period = models.CharField(max_length=20, choices=TIME_PERIODS)
    
    # Filtering conditions
    filter_conditions = models.JSONField(default=dict, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'merchant_aggregation_rules'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class TradingSession(models.Model):
    """Track merchant trading sessions"""
    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name='trading_sessions')
    session_id = models.CharField(max_length=100, unique=True)
    
    # Session details
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    
    # Activity tracking
    transactions_count = models.IntegerField(default=0)
    total_volume_traded = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_value_traded = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Status
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'merchant_trading_sessions'
        ordering = ['-start_time']
    
    def __str__(self):
        return f"{self.merchant.company_name} - {self.start_time}"
    
    @property
    def duration(self):
        end = self.end_time or timezone.now()
        return end - self.start_time