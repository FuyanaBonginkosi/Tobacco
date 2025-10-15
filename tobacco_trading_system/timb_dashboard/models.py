from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.conf import settings
from datetime import datetime, timedelta
import json

User = get_user_model()


class Merchant(models.Model):
    """Merchant/Trader model extending User"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='merchant_profile')
    
    # Business Information
    company_name = models.CharField(max_length=200, blank=True)
    business_registration_number = models.CharField(max_length=100, blank=True)
    license_number = models.CharField(max_length=100, unique=True)
    license_issue_date = models.DateField(null=True, blank=True)
    license_expiry_date = models.DateField(null=True, blank=True)
    
    # Contact Information
    business_address = models.TextField(blank=True)
    business_phone = models.CharField(max_length=20, blank=True)
    business_email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    
    # Bank Information
    bank_name = models.CharField(max_length=100, blank=True)
    bank_account_number = models.CharField(max_length=50, blank=True)
    bank_branch = models.CharField(max_length=100, blank=True)
    
    # Trading Information
    annual_trading_volume = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    preferred_grades = models.ManyToManyField('TobaccoGrade', blank=True)
    trading_regions = models.JSONField(default=list, blank=True)
    
    # Status
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    verification_date = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_merchants')
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'timb_merchants'
        ordering = ['company_name', 'user__username']
        indexes = [
            models.Index(fields=['license_number']),
            models.Index(fields=['is_verified', 'is_active']),
            models.Index(fields=['company_name']),
        ]
    
    def __str__(self):
        return f"{self.company_name or self.user.username} ({self.license_number})"
    
    @property
    def is_license_valid(self):
        """Check if license is still valid"""
        if self.license_expiry_date:
            return self.license_expiry_date >= timezone.now().date()
        return True
    
    @property
    def license_days_remaining(self):
        """Get days remaining until license expires"""
        if self.license_expiry_date:
            delta = self.license_expiry_date - timezone.now().date()
            return max(0, delta.days)
        return None


class TobaccoGrade(models.Model):
    """TIMB Official Tobacco Grades from Excel"""
    GRADE_CATEGORIES = [
        ('PRIMING', 'Priming Grades (P)'),
        ('LUG', 'Lug Grades (X)'),
        ('LEAF', 'Leaf Grades (L)'),
        ('TIP', 'Tip Grades (T)'),
        ('STRIP', 'Strip Grades (A)'),
        ('CUTTER', 'Cutter Grades (C)'),
        ('SMOKING', 'Smoking Grades (H)'),
        ('SCRAP', 'Scrap Grades (B)'),
        ('LOOSE_LEAF', 'Loose Leaf'),
        ('REJECTION', 'Rejection Codes'),
        ('DEFECT', 'Defect Codes'),
    ]
    
    QUALITY_LEVELS = [
        (1, 'Grade 1 - Premium'),
        (2, 'Grade 2 - High Quality'),
        (3, 'Grade 3 - Good Quality'),
        (4, 'Grade 4 - Standard'),
        (5, 'Grade 5 - Basic'),
    ]
    
    grade_code = models.CharField(max_length=20, unique=True, db_index=True)
    grade_name = models.CharField(max_length=200)
    category = models.CharField(max_length=20, choices=GRADE_CATEGORIES, db_index=True)
    quality_level = models.IntegerField(choices=QUALITY_LEVELS, null=True, blank=True)
    base_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    minimum_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    maximum_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    description = models.TextField(blank=True)
    specifications = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    is_tradeable = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'timb_tobacco_grades'
        ordering = ['category', 'quality_level', 'grade_code']
        indexes = [
            models.Index(fields=['category', 'quality_level']),
            models.Index(fields=['grade_code']),
            models.Index(fields=['is_active', 'is_tradeable']),
        ]
    
    def __str__(self):
        return f"{self.grade_code} - {self.grade_name}"
    
    @property
    def is_rejection_code(self):
        return self.category == 'REJECTION'
    
    @property
    def is_defect_code(self):
        return self.category == 'DEFECT'


class TobaccoFloor(models.Model):
    """TIMB Tobacco Auction Floors"""
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=200)
    address = models.TextField()
    manager = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    capacity = models.IntegerField(help_text="Maximum bales capacity")
    current_stock = models.IntegerField(default=0)
    operating_hours = models.JSONField(default=dict)
    coordinates = models.JSONField(default=dict, blank=True)  # lat, lng
    is_active = models.BooleanField(default=True)
    market_open = models.BooleanField(default=False, help_text="Whether trading is open on this floor")
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        db_table = 'timb_tobacco_floors'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} - {self.location}"
    
    @property
    def utilization_percentage(self):
        if self.capacity > 0:
            return (self.current_stock / self.capacity) * 100
        return 0


class Transaction(models.Model):
    """Tobacco Trading Transactions"""
    TRANSACTION_TYPES = [
        ('FLOOR_SALE', 'Floor Sale'),
        ('CONTRACT_SALE', 'Contract Sale'),
        ('DIRECT_SALE', 'Direct Sale'),
        ('EXPORT', 'Export Sale'),
        ('INTERNAL_TRANSFER', 'Internal Transfer'),
    ]
    
    PAYMENT_METHODS = [
        ('CASH', 'Cash'),
        ('BANK_TRANSFER', 'Bank Transfer'),
        ('CHEQUE', 'Cheque'),
        ('MOBILE_MONEY', 'Mobile Money'),
        ('LETTER_OF_CREDIT', 'Letter of Credit'),
    ]
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
        ('DISPUTED', 'Disputed'),
    ]
    
    # Transaction Details
    transaction_id = models.CharField(max_length=50, unique=True, db_index=True)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    # Parties
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='sales')
    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='purchases')
    
    # Product Details
    grade = models.ForeignKey(TobaccoGrade, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)  # in kg
    price_per_kg = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=15, decimal_places=2)
    
    # Floor and Location
    floor = models.ForeignKey(TobaccoFloor, on_delete=models.SET_NULL, null=True, blank=True)
    sale_number = models.CharField(max_length=50, blank=True)
    lot_number = models.CharField(max_length=50, blank=True)
    
    # Quality Information
    moisture_content = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    quality_assessment = models.TextField(blank=True)
    quality_score = models.IntegerField(null=True, blank=True)  # 1-100
    
    # Payment
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, blank=True)
    payment_reference = models.CharField(max_length=100, blank=True)
    payment_date = models.DateTimeField(null=True, blank=True)
    
    # Fraud Detection
    is_flagged = models.BooleanField(default=False)
    fraud_score = models.DecimalField(max_digits=5, decimal_places=4, default=0)
    fraud_reasons = models.JSONField(default=list, blank=True)
    
    # Timestamps
    timestamp = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_transactions')
    updated_at = models.DateTimeField(auto_now=True)
    
    # Additional Data
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        db_table = 'timb_transactions'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['transaction_id']),
            models.Index(fields=['seller', '-timestamp']),
            models.Index(fields=['buyer', '-timestamp']),
            models.Index(fields=['grade', '-timestamp']),
            models.Index(fields=['floor', '-timestamp']),
            models.Index(fields=['-timestamp']),
            models.Index(fields=['is_flagged', '-timestamp']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.transaction_id:
            self.transaction_id = self.generate_transaction_id()
        if not self.total_amount:
            self.total_amount = self.quantity * self.price_per_kg
        super().save(*args, **kwargs)
    
    def generate_transaction_id(self):
        """Generate unique transaction ID"""
        from django.utils.crypto import get_random_string
        timestamp = timezone.now().strftime('%Y%m%d')
        random_part = get_random_string(6, allowed_chars='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ')
        return f"TIMB{timestamp}{random_part}"
    
    def __str__(self):
        return f"{self.transaction_id} - {self.seller.username} → {self.buyer.username}"


class DailyPrice(models.Model):
    """Daily tobacco prices for each grade"""
    grade = models.ForeignKey(TobaccoGrade, on_delete=models.CASCADE)
    date = models.DateField(db_index=True)
    opening_price = models.DecimalField(max_digits=10, decimal_places=2)
    closing_price = models.DecimalField(max_digits=10, decimal_places=2)
    high_price = models.DecimalField(max_digits=10, decimal_places=2)
    low_price = models.DecimalField(max_digits=10, decimal_places=2)
    average_price = models.DecimalField(max_digits=10, decimal_places=2)
    volume_traded = models.DecimalField(max_digits=15, decimal_places=2, default=0)  # kg
    number_of_transactions = models.IntegerField(default=0)
    floor = models.ForeignKey(TobaccoFloor, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        db_table = 'timb_daily_prices'
        unique_together = ['grade', 'date', 'floor']
        ordering = ['-date', 'grade__grade_code']
        indexes = [
            models.Index(fields=['grade', '-date']),
            models.Index(fields=['-date']),
            models.Index(fields=['floor', '-date']),
        ]
    
    def __str__(self):
        return f"{self.grade.grade_code} - {self.date} - ${self.closing_price}/kg"
    
    @property
    def price_change(self):
        """Calculate price change from opening to closing"""
        return self.closing_price - self.opening_price
    
    @property
    def price_change_percentage(self):
        """Calculate percentage change"""
        if self.opening_price > 0:
            return ((self.closing_price - self.opening_price) / self.opening_price) * 100
        return 0


class DashboardMetric(models.Model):
    """Real-time dashboard metrics"""
    METRIC_TYPES = [
        ('TRANSACTION_COUNT', 'Transaction Count'),
        ('TOTAL_VOLUME', 'Total Volume'),
        ('TOTAL_VALUE', 'Total Value'),
        ('ACTIVE_MERCHANTS', 'Active Merchants'),
        ('FRAUD_ALERTS', 'Fraud Alerts'),
        ('SYSTEM_STATUS', 'System Status'),
        ('FLOOR_ACTIVITY', 'Floor Activity'),
        ('GRADE_PERFORMANCE', 'Grade Performance'),
    ]
    
    metric_type = models.CharField(max_length=50, choices=METRIC_TYPES)
    value = models.DecimalField(max_digits=15, decimal_places=2)
    timestamp = models.DateTimeField(default=timezone.now)
    floor = models.ForeignKey(TobaccoFloor, on_delete=models.SET_NULL, null=True, blank=True)
    grade = models.ForeignKey(TobaccoGrade, on_delete=models.SET_NULL, null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        db_table = 'timb_dashboard_metrics'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['metric_type', '-timestamp']),
            models.Index(fields=['floor', '-timestamp']),
            models.Index(fields=['grade', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.get_metric_type_display()}: {self.value} at {self.timestamp}"


class SystemAlert(models.Model):
    """System alerts and notifications"""
    SEVERITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    ]
    
    ALERT_TYPES = [
        ('FRAUD', 'Fraud Detection'),
        ('SYSTEM', 'System Error'),
        ('PERFORMANCE', 'Performance Issue'),
        ('SECURITY', 'Security Alert'),
        ('BUSINESS', 'Business Rule Violation'),
        ('PRICE', 'Price Alert'),
        ('VOLUME', 'Volume Alert'),
        ('FLOOR', 'Floor Alert'),
    ]
    
    title = models.CharField(max_length=200)
    message = models.TextField()
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES)
    is_active = models.BooleanField(default=True)
    transaction = models.ForeignKey(Transaction, on_delete=models.SET_NULL, null=True, blank=True)
    floor = models.ForeignKey(TobaccoFloor, on_delete=models.SET_NULL, null=True, blank=True)
    grade = models.ForeignKey(TobaccoGrade, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        db_table = 'timb_system_alerts'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['alert_type', '-created_at']),
            models.Index(fields=['severity', 'is_active']),
            models.Index(fields=['floor', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.severity})"
    
    def resolve(self, user=None):
        """Mark alert as resolved"""
        self.is_active = False
        self.resolved_at = timezone.now()
        self.resolved_by = user
        self.save()


class UserSession(models.Model):
    """Track user sessions for dashboard metrics"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    session_key = models.CharField(max_length=40, unique=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    login_time = models.DateTimeField(default=timezone.now)
    last_activity = models.DateTimeField(default=timezone.now)
    logout_time = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'timb_user_sessions'
        ordering = ['-login_time']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['session_key']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.ip_address}"
    
    @property
    def duration(self):
        """Calculate session duration"""
        end_time = self.logout_time or timezone.now()
        return end_time - self.login_time
    
    @classmethod
    def get_active_count(cls):
        """Get count of active sessions"""
        return cls.objects.filter(
            is_active=True,
            last_activity__gte=timezone.now() - timedelta(minutes=30)
        ).count()


class FarmerProfile(models.Model):
    """Farmer profile for risk assessment"""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='farmer_profile')
    farmer_id = models.CharField(max_length=50, unique=True)
    farm_name = models.CharField(max_length=200, blank=True)
    farm_location = models.CharField(max_length=200)
    farm_size_hectares = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Contact Information
    contact_phone = models.CharField(max_length=20)
    contact_address = models.TextField()
    
    # Farming Details
    years_of_experience = models.IntegerField()
    primary_tobacco_type = models.CharField(max_length=100)
    annual_production_capacity = models.DecimalField(max_digits=15, decimal_places=2)
    
    # Bank Information
    bank_name = models.CharField(max_length=100, blank=True)
    bank_account_number = models.CharField(max_length=50, blank=True)
    
    # Status
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'timb_farmer_profiles'
        ordering = ['farm_name', 'user__username']
    
    def __str__(self):
        return f"{self.farm_name or self.user.username} ({self.farmer_id})"