from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from django.db import models
from .models import Transaction, DashboardMetric, SystemAlert, TobaccoGrade, Merchant
from merchant_app.models import MerchantInventory


@receiver(post_save, sender=Transaction)
def update_transaction_metrics(sender, instance, created, **kwargs):
    """Update dashboard metrics when transaction is created/updated"""
    if created:
        today = timezone.now().date()
        
        # Update transaction count metric
        DashboardMetric.objects.create(
            metric_type='TRANSACTION_COUNT',
            value=Transaction.objects.filter(timestamp__date=today).count(),
            floor=instance.floor,
            grade=instance.grade,
            metadata={
                'transaction_id': instance.transaction_id,
                'transaction_type': instance.transaction_type
            }
        )
        
        # Update volume metric
        total_volume = Transaction.objects.filter(
            timestamp__date=today
        ).aggregate(total=models.Sum('quantity'))['total'] or 0
        
        DashboardMetric.objects.create(
            metric_type='TOTAL_VOLUME',
            value=total_volume,
            metadata={'date': today.isoformat()}
        )
        
        # Update value metric
        total_value = Transaction.objects.filter(
            timestamp__date=today
        ).aggregate(total=models.Sum('total_amount'))['total'] or 0
        
        DashboardMetric.objects.create(
            metric_type='TOTAL_VALUE',
            value=total_value,
            metadata={'date': today.isoformat()}
        )
        
        # Check for unusual activity
        recent_transactions = Transaction.objects.filter(
            seller=instance.seller,
            timestamp__gte=timezone.now() - timezone.timedelta(hours=1)
        ).count()
        
        if recent_transactions > 10:  # More than 10 transactions in an hour
            SystemAlert.objects.create(
                title=f'High transaction volume: {instance.seller.username}',
                message=f'User {instance.seller.username} has {recent_transactions} transactions in the last hour',
                alert_type='BUSINESS',
                severity='MEDIUM',
                metadata={
                    'user_id': instance.seller.id,
                    'transaction_count': recent_transactions,
                    'time_period': '1_hour'
                }
            )

        # Auto inventory capture to merchant buyer
        try:
            # Only apply when buyer is a merchant user
            buyer_user = instance.buyer
            if hasattr(buyer_user, 'merchant_profile') and instance.quantity and instance.grade:
                merchant = buyer_user.merchant_profile
                # Find or create inventory record for this grade
                inventory, _ = MerchantInventory.objects.get_or_create(
                    merchant=merchant,
                    grade=instance.grade,
                    batch_number=instance.lot_number or '',
                    defaults={
                        'quantity': 0,
                        'reserved_quantity': 0,
                        'average_cost': instance.price_per_kg,
                        'storage_location': merchant.business_address or '',
                        'last_purchase_date': instance.timestamp,
                    }
                )
                # Weighted average cost update
                try:
                    existing_total_value = inventory.quantity * inventory.average_cost
                    new_total_value = instance.quantity * instance.price_per_kg
                    new_quantity = inventory.quantity + instance.quantity
                    inventory.average_cost = (existing_total_value + new_total_value) / new_quantity if new_quantity > 0 else inventory.average_cost
                except Exception:
                    # Fallback to transaction price if any numeric issue
                    inventory.average_cost = instance.price_per_kg

                inventory.quantity = (inventory.quantity or 0) + instance.quantity
                inventory.last_purchase_date = instance.timestamp
                inventory.last_movement_date = timezone.now()
                inventory.save()
        except Exception:
            # Fail-safe: do not break transaction save on inventory sync issues
            pass


@receiver(post_save, sender=SystemAlert)
def update_alert_metrics(sender, instance, created, **kwargs):
    """Update alert metrics when new alert is created"""
    if created:
        active_alerts = SystemAlert.objects.filter(is_active=True).count()
        
        DashboardMetric.objects.create(
            metric_type='FRAUD_ALERTS',
            value=active_alerts,
            metadata={
                'alert_type': instance.alert_type,
                'severity': instance.severity,
                'alert_id': instance.id
            }
        )