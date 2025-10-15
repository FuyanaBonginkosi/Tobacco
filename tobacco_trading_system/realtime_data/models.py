from django.db import models
from django.utils import timezone
from timb_dashboard.models import TobaccoGrade, TobaccoFloor, Merchant
from utils.encryption import encryption
import json

class RealTimePrice(models.Model):
    """Enhanced real-time tobacco prices with market data"""
    
    grade = models.ForeignKey(TobaccoGrade, on_delete=models.CASCADE)
    floor = models.ForeignKey(TobaccoFloor, on_delete=models.CASCADE, blank=True, null=True)
    
    # Price data
    current_price = models.DecimalField(max_digits=8, decimal_places=2)
    previous_price = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    price_change = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    
    # Market data
    opening_price = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    high_price = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    low_price = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    volume_traded_today = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Market indicators
    bid_price = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    ask_price = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    market_depth = models.JSONField(default=dict, blank=True)
    
    # Volatility and trends
    volatility_index = models.DecimalField(max_digits=5, decimal_places=3, default=0)
    trend_indicator = models.CharField(max_length=10, choices=[
        ('BULLISH', 'Bullish'),
        ('BEARISH', 'Bearish'),
        ('NEUTRAL', 'Neutral'),
        ('VOLATILE', 'Volatile')
    ], default='NEUTRAL')
    
    # Timestamps
    last_updated = models.DateTimeField(auto_now=True)
    last_trade_time = models.DateTimeField(blank=True, null=True)
    
    # Encrypted market data for sensitive information
    encrypted_market_data = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['grade', 'floor']
        ordering = ['grade__category', 'grade__grade_code']
        verbose_name = 'Real-Time Price'
        verbose_name_plural = 'Real-Time Prices'
        indexes = [
            models.Index(fields=['grade', 'floor']),
            models.Index(fields=['-last_updated']),
        ]
    
    def __str__(self):
        return f"{self.grade.grade_name} - ${self.current_price}"
    
    def set_market_data(self, data):
        """Encrypt and store sensitive market data"""
        if data:
            self.encrypted_market_data = encryption.encrypt_data(data)
    
    def get_market_data(self):
        """Decrypt and retrieve market data"""
        if self.encrypted_market_data:
            return encryption.decrypt_data(self.encrypted_market_data)
        return {}
    
    @property
    def percentage_change(self):
        """Calculate percentage price change"""
        if self.previous_price and self.previous_price > 0:
            return (self.price_change / self.previous_price) * 100
        return 0
    
    @property
    def is_trending_up(self):
        """Check if price is trending upward"""
        return self.price_change > 0
    
    def update_volatility(self):
        """Calculate and update volatility index"""
        # Simplified volatility calculation
        if self.previous_price and self.previous_price > 0:
            change_rate = abs(self.price_change / self.previous_price)
            self.volatility_index = min(change_rate * 100, 100)  # Cap at 100
        else:
            self.volatility_index = 0


class LiveTransaction(models.Model):
    """Enhanced live transaction feed"""
    
    transaction_id = models.CharField(max_length=50, unique=True)
    floor = models.ForeignKey(TobaccoFloor, on_delete=models.CASCADE, blank=True, null=True)
    grade = models.ForeignKey(TobaccoGrade, on_delete=models.CASCADE)
    
    # Transaction details
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    total_value = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Parties (anonymized for public feed)
    buyer_info = models.CharField(max_length=100)
    seller_info = models.CharField(max_length=100)
    
    # Market impact
    price_impact = models.DecimalField(max_digits=5, decimal_places=3, default=0)
    volume_impact = models.DecimalField(max_digits=5, decimal_places=3, default=0)
    
    # Flags and indicators
    is_flagged = models.BooleanField(default=False)
    is_large_trade = models.BooleanField(default=False)
    is_broadcast = models.BooleanField(default=True)
    
    # AI analysis
    fraud_probability = models.DecimalField(max_digits=5, decimal_places=3, blank=True, null=True)
    market_anomaly_score = models.DecimalField(max_digits=5, decimal_places=3, default=0)
    
    # Geographic and temporal data
    region = models.CharField(max_length=100, blank=True)
    trading_session = models.CharField(max_length=20, choices=[
        ('MORNING', 'Morning Session'),
        ('AFTERNOON', 'Afternoon Session'),
        ('EVENING', 'Evening Session')
    ], blank=True)
    
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp', 'grade']),
            models.Index(fields=['is_broadcast', 'timestamp']),
            models.Index(fields=['is_flagged']),
        ]
        verbose_name = 'Live Transaction'
        verbose_name_plural = 'Live Transactions'
    
    def __str__(self):
        return f"{self.transaction_id} - {self.grade.grade_name} ({self.quantity}kg)"
    
    def save(self, *args, **kwargs):
        # Calculate total value
        self.total_value = self.quantity * self.price
        
        # Determine if it's a large trade (>1000kg or >$10000)
        self.is_large_trade = self.quantity > 1000 or self.total_value > 10000
        
        # Determine trading session
        hour = timezone.now().hour
        if 6 <= hour < 12:
            self.trading_session = 'MORNING'
        elif 12 <= hour < 17:
            self.trading_session = 'AFTERNOON'
        else:
            self.trading_session = 'EVENING'
        
        super().save(*args, **kwargs)


class MarketAlert(models.Model):
    """Enhanced market alerts and notifications"""
    
    ALERT_TYPES = [
        ('PRICE_SPIKE', 'Price Spike'),
        ('PRICE_DROP', 'Price Drop'),
        ('VOLUME_SURGE', 'Volume Surge'),
        ('MARKET_ANOMALY', 'Market Anomaly'),
        ('LIQUIDITY_ISSUE', 'Liquidity Issue'),
        ('GRADE_SHORTAGE', 'Grade Shortage'),
        ('QUALITY_CONCERN', 'Quality Concern'),
        ('REGULATORY_UPDATE', 'Regulatory Update'),
        ('WEATHER_IMPACT', 'Weather Impact'),
        ('EXPORT_OPPORTUNITY', 'Export Opportunity'),
    ]
    
    SEVERITY_LEVELS = [
        ('INFO', 'Information'),
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    ]
    
    alert_type = models.CharField(max_length=30, choices=ALERT_TYPES)
    severity = models.CharField(max_length=10, choices=SEVERITY_LEVELS)
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    # Related objects
    grade = models.ForeignKey(TobaccoGrade, on_delete=models.CASCADE, blank=True, null=True)
    floor = models.ForeignKey(TobaccoFloor, on_delete=models.CASCADE, blank=True, null=True)
    affected_merchants = models.ManyToManyField(Merchant, blank=True)
    
    # Alert data
    threshold_value = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    current_value = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    
    # Geographic scope
    affected_regions = models.JSONField(default=list, blank=True)
    market_impact_radius = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    
    # Response and resolution
    is_resolved = models.BooleanField(default=False)
    resolution_notes = models.TextField(blank=True)
    resolution_time = models.DateTimeField(blank=True, null=True)
    
    # Notification tracking
    notification_sent = models.BooleanField(default=False)
    email_sent = models.BooleanField(default=False)
    sms_sent = models.BooleanField(default=False)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(blank=True, null=True)
    
    # Encrypted alert data for sensitive information
    encrypted_alert_data = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['alert_type', 'severity']),
            models.Index(fields=['is_resolved', 'created_at']),
            models.Index(fields=['grade', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.get_severity_display()} - {self.title}"
    
    def set_alert_data(self, data):
        """Encrypt and store sensitive alert data"""
        if data:
            self.encrypted_alert_data = encryption.encrypt_data(data)
    
    def get_alert_data(self):
        """Decrypt and retrieve alert data"""
        if self.encrypted_alert_data:
            return encryption.decrypt_data(self.encrypted_alert_data)
        return {}
    
    @property
    def is_expired(self):
        """Check if alert has expired"""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
    
    def resolve_alert(self, notes=''):
        """Mark alert as resolved"""
        self.is_resolved = True
        self.resolution_time = timezone.now()
        self.resolution_notes = notes
        self.save()


class SystemNotification(models.Model):
    """Enhanced system-wide notifications"""
    
    NOTIFICATION_TYPES = [
        ('SYSTEM_UPDATE', 'System Update'),
        ('MAINTENANCE', 'Maintenance Notice'),
        ('SECURITY_ALERT', 'Security Alert'),
        ('MARKET_NEWS', 'Market News'),
        ('REGULATORY_CHANGE', 'Regulatory Change'),
        ('PRICE_ALERT', 'Price Alert'),
        ('TRANSACTION_ALERT', 'Transaction Alert'),
        ('PERFORMANCE_REPORT', 'Performance Report'),
        ('TRAINING_ANNOUNCEMENT', 'Training Announcement'),
        ('FEATURE_UPDATE', 'Feature Update'),
    ]
    
    PRIORITY_LEVELS = [
        ('LOW', 'Low Priority'),
        ('NORMAL', 'Normal Priority'),
        ('HIGH', 'High Priority'),
        ('URGENT', 'Urgent'),
    ]
    
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES)
    priority = models.CharField(max_length=10, choices=PRIORITY_LEVELS, default='NORMAL')
    
    # Recipients
    recipient = models.ForeignKey('authentication.User', on_delete=models.CASCADE, blank=True, null=True)
    recipient_group = models.CharField(max_length=50, choices=[
        ('ALL_USERS', 'All Users'),
        ('TIMB_STAFF', 'TIMB Staff'),
        ('MERCHANTS', 'All Merchants'),
        ('ACTIVE_TRADERS', 'Active Traders'),
        ('SPECIFIC_MERCHANTS', 'Specific Merchants'),
    ], default='ALL_USERS')
    
    # Message content
    title = models.CharField(max_length=200)
    message = models.TextField()
    action_url = models.URLField(blank=True)
    action_text = models.CharField(max_length=50, blank=True)
    
    # Rich content
    image_url = models.URLField(blank=True)
    attachment_url = models.URLField(blank=True)
    
    # Delivery tracking
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(blank=True, null=True)
    delivered_at = models.DateTimeField(blank=True, null=True)
    
    # Scheduling
    scheduled_for = models.DateTimeField(blank=True, null=True)
    expires_at = models.DateTimeField(blank=True, null=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('authentication.User', on_delete=models.CASCADE, related_name='created_notifications')
    
    # Encrypted sensitive metadata
    encrypted_metadata = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['notification_type', 'created_at']),
            models.Index(fields=['priority', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.get_priority_display()}"
    
    def set_metadata(self, data):
        """Encrypt and store sensitive metadata"""
        if data:
            self.encrypted_metadata = encryption.encrypt_data(data)
    
    def get_metadata(self):
        """Decrypt and retrieve metadata"""
        if self.encrypted_metadata:
            return encryption.decrypt_data(self.encrypted_metadata)
        return {}
    
    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()
    
    @property
    def is_expired(self):
        """Check if notification has expired"""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False


class MarketDataSnapshot(models.Model):
    """Enhanced periodic snapshots of market data for analysis"""
    
    snapshot_date = models.DateTimeField(auto_now_add=True)
    
    # Market summary
    total_transactions = models.IntegerField(default=0)
    total_volume = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_value = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    average_price = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    
    # Price movements
    top_gainer_grade = models.ForeignKey(TobaccoGrade, on_delete=models.CASCADE, blank=True, null=True, related_name='top_gainer_snapshots')
    top_gainer_change = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    top_loser_grade = models.ForeignKey(TobaccoGrade, on_delete=models.CASCADE, blank=True, null=True, related_name='top_loser_snapshots')
    top_loser_change = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    
    # Volume leaders
    highest_volume_grade = models.ForeignKey(TobaccoGrade, on_delete=models.CASCADE, blank=True, null=True, related_name='volume_leader_snapshots')
    highest_volume_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Market sentiment
    market_sentiment = models.CharField(max_length=20, choices=[
        ('VERY_BULLISH', 'Very Bullish'),
        ('BULLISH', 'Bullish'),
        ('NEUTRAL', 'Neutral'),
        ('BEARISH', 'Bearish'),
        ('VERY_BEARISH', 'Very Bearish'),
    ], default='NEUTRAL')
    
    volatility_index = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Floor activity
    most_active_floor = models.ForeignKey(TobaccoFloor, on_delete=models.CASCADE, blank=True, null=True)
    floor_activity_scores = models.JSONField(default=dict, blank=True)
    
    # Regional data
    regional_data = models.JSONField(default=dict, blank=True)
    
    # Weather and external factors
    weather_impact_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    external_factors = models.JSONField(default=list, blank=True)
    
    class Meta:
        ordering = ['-snapshot_date']
        indexes = [
            models.Index(fields=['snapshot_date']),
        ]
    
    def __str__(self):
        return f"Market Snapshot - {self.snapshot_date.strftime('%Y-%m-%d %H:%M')}"