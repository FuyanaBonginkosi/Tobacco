from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
import random

from timb_dashboard.models import TobaccoGrade, TobaccoFloor, Transaction, Merchant
from merchant_app.models import MerchantInventory

User = get_user_model()

class Command(BaseCommand):
    help = 'Load demo data for TIMB system demonstration'

    def handle(self, *args, **options):
        self.stdout.write('Creating demo users and merchants...')
        admin = self.ensure_superuser()
        timb_staff = self.ensure_timb_staff()
        merchants = self.ensure_demo_merchants()

        self.stdout.write('Ensuring grades and floors exist...')
        self.ensure_minimum_grades()
        self.ensure_minimum_floors()

        self.stdout.write('Opening market and creating demo transactions...')
        self.open_market()
        self.create_demo_transactions(timb_staff, merchants)

        self.stdout.write(self.style.SUCCESS('Demo data loaded successfully'))

    def ensure_superuser(self):
        if not User.objects.filter(is_superuser=True).exists():
            user = User.objects.create_superuser(
                username='admin', email='admin@example.com', password='admin123', is_timb_staff=True
            )
            return user
        return User.objects.filter(is_superuser=True).first()

    def ensure_timb_staff(self):
        user, _ = User.objects.get_or_create(
            username='timb_demo',
            defaults={
                'email': 'timb_demo@example.com',
                'is_timb_staff': True,
            }
        )
        if not user.has_usable_password():
            user.set_password('timb123')
            user.save()
        return user

    def ensure_demo_merchants(self):
        demo = []
        for i in range(1, 4):
            username = f'merchant{i}'
            user, _ = User.objects.get_or_create(
                username=username,
                defaults={'email': f'{username}@example.com', 'is_merchant': True}
            )
            if not user.has_usable_password():
                user.set_password('merchant123')
                user.save()
            merchant, _ = Merchant.objects.get_or_create(
                user=user,
                defaults={
                    'company_name': f'Demo Merchant {i}',
                    'license_number': f'LIC-DEMO-{i:03d}',
                    'is_active': True,
                }
            )
            demo.append(merchant)
        return demo

    def ensure_minimum_grades(self):
        base = [
            ('A1', 'STRIP', 5.50), ('A2', 'STRIP', 5.00), ('L1', 'LEAF', 4.20), ('L2', 'LEAF', 3.80),
            ('X1', 'LUG', 3.20), ('T1', 'TIP', 2.50), ('H1', 'SMOKING', 1.80), ('C1', 'CUTTER', 2.20),
        ]
        for code, cat, price in base:
            TobaccoGrade.objects.get_or_create(
                grade_code=code,
                defaults={'grade_name': f'{code} Grade', 'category': cat, 'base_price': Decimal(str(price))}
            )

    def ensure_minimum_floors(self):
        floors = [('Harare Tobacco Floors', 'Harare'), ('Bulawayo Tobacco Floors', 'Bulawayo')]
        for name, loc in floors:
            TobaccoFloor.objects.get_or_create(name=name, defaults={'location': loc, 'capacity': 200000, 'is_active': True})

    def open_market(self):
        from timb_dashboard.models import TobaccoFloor
        TobaccoFloor.objects.filter(is_active=True).update(market_open=True)

    def create_demo_transactions(self, timb_staff, merchants):
        grades = list(TobaccoGrade.objects.filter(is_active=True))
        floors = list(TobaccoFloor.objects.filter(is_active=True))
        if not grades or not floors:
            return
        for _ in range(20):
            grade = random.choice(grades)
            floor = random.choice(floors)
            seller = timb_staff  # For demo, TIMB records transactions between merchants
            buyer_user = random.choice(merchants).user
            qty = Decimal(str(round(random.uniform(100, 1000), 2)))
            price = Decimal(str(round(float(grade.base_price) * random.uniform(0.9, 1.1), 2)))
            Transaction.objects.create(
                transaction_type='FLOOR_SALE',
                seller=seller,
                buyer=buyer_user,
                grade=grade,
                quantity=qty,
                price_per_kg=price,
                total_amount=qty * price,
                floor=floor,
                payment_method='BANK_TRANSFER',
                created_by=timb_staff,
            )
