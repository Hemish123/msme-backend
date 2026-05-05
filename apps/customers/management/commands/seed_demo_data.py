"""
Management command to seed demo data for testing.
Creates 1 demo MSME user and 50 sample customers with payment records.
"""
import random
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from apps.customers.models import Customer, PaymentRecord
from apps.payments.models import PaymentAnalytics, CreditTimeline

User = get_user_model()

COMPANY_NAMES = [
    'Tata Steel Ltd', 'Reliance Industries', 'Infosys Solutions', 'Wipro Technologies',
    'HCL Systems', 'Mahindra Manufacturing', 'Bajaj Enterprises', 'Godrej Industries',
    'Larsen & Toubro', 'Bharat Electronics', 'Sun Pharma', 'Dr. Reddys Labs',
    'Asian Paints', 'Hindustan Unilever', 'ITC Limited', 'Maruti Suzuki',
    'Hero MotoCorp', 'Bharti Airtel', 'Adani Group', 'JSW Steel',
    'Vedanta Resources', 'Grasim Industries', 'UltraTech Cement', 'ACC Limited',
    'Ambuja Cements', 'Dalmia Bharat', 'Shree Cement', 'Ramco Cements',
    'Berger Paints', 'Kansai Nerolac', 'Pidilite Industries', 'Havells India',
    'Crompton Greaves', 'Voltas Limited', 'Blue Star', 'Symphony Limited',
    'Titan Company', 'Tanishq Jewellers', 'Raymond Limited', 'Arvind Limited',
    'Page Industries', 'Bata India', 'Relaxo Footwear', 'Ceat Limited',
    'MRF Limited', 'Apollo Tyres', 'Britannia Industries', 'Nestle India',
    'Dabur India', 'Marico Limited',
]

CONTACT_NAMES = [
    'Rajesh Kumar', 'Priya Sharma', 'Amit Patel', 'Sunita Reddy',
    'Vikram Singh', 'Anita Verma', 'Deepak Joshi', 'Meera Nair',
    'Sanjay Gupta', 'Kavita Desai', 'Rohit Mehta', 'Nisha Agarwal',
    'Arun Krishnan', 'Pooja Bhatt', 'Suresh Iyer', 'Radha Menon',
    'Prakash Rao', 'Lakshmi Venkat', 'Vinod Kapoor', 'Sarita Mishra',
    'Manish Tiwari', 'Geeta Banerjee', 'Harsh Vardhan', 'Uma Shankar',
    'Kiran Bedi', 'Naveen Jain', 'Pallavi Saxena', 'Ravi Shankar',
    'Archana Pillai', 'Dinesh Choudhary', 'Swati Pandey', 'Gaurav Malhotra',
    'Rekha Devi', 'Ajay Chauhan', 'Bhavna Shah', 'Nitin Gadkari',
    'Shobha Rani', 'Tarun Khanna', 'Jyoti Prasad', 'Mohan Das',
    'Vandana Luthra', 'Ashok Leyland', 'Pankaj Udhas', 'Smita Patil',
    'Rani Mukerji', 'Farhan Akhtar', 'Zoya Hussain', 'Kabir Khan',
    'Imtiaz Ali', 'Dia Mirza',
]


class Command(BaseCommand):
    help = 'Seed demo data: 1 MSME user + 50 customers + payment records'

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true', help='Clear existing demo data first')

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing data...')
            PaymentAnalytics.objects.all().delete()
            CreditTimeline.objects.all().delete()
            PaymentRecord.objects.all().delete()
            Customer.objects.all().delete()
            User.objects.filter(email='demo@msmepaytrack.com').delete()

        # Create demo user
        user, created = User.objects.get_or_create(
            email='demo@msmepaytrack.com',
            defaults={
                'username': 'demo_msme',
                'first_name': 'Demo',
                'last_name': 'User',
                'company_name': 'PayTrack Demo MSME',
                'phone': '+91-9876543210',
            }
        )
        if created:
            user.set_password('demo1234')
            user.save()
            self.stdout.write(self.style.SUCCESS(f'Created demo user: demo@msmepaytrack.com / demo1234'))
        else:
            self.stdout.write(f'Demo user already exists: {user.email}')

        # Create 50 customers
        customers = []
        for i in range(50):
            customer, _ = Customer.objects.get_or_create(
                name=CONTACT_NAMES[i],
                msme_owner=user,
                defaults={
                    'company': COMPANY_NAMES[i],
                    'email': f'{CONTACT_NAMES[i].lower().replace(" ", ".")}@{COMPANY_NAMES[i].lower().replace(" ", "").replace("&", "")[:12]}.com',
                    'phone': f'+91-{random.randint(7000000000, 9999999999)}',
                    'gstin': f'{random.randint(10, 35)}{self._random_gstin()}',
                    'address': f'{random.randint(1, 500)}, Industrial Area, Sector {random.randint(1, 60)}, Delhi NCR',
                }
            )
            customers.append(customer)

        self.stdout.write(f'Created/found {len(customers)} customers')

        # Create payment records spanning 5-10 years
        total_records = 0
        for customer in customers:
            if customer.payment_records.exists():
                continue

            # Determine customer payment personality
            personality = random.choice(['excellent', 'good', 'average', 'poor', 'terrible'])
            years_of_history = random.randint(3, 10)
            invoices_per_year = random.randint(6, 24)

            start_date = date.today() - timedelta(days=years_of_history * 365)

            for y in range(years_of_history):
                for m in range(invoices_per_year):
                    invoice_date = start_date + timedelta(
                        days=y * 365 + int(m * (365 / invoices_per_year)) + random.randint(-5, 5)
                    )
                    if invoice_date > date.today():
                        continue

                    amount = Decimal(str(random.randint(10000, 500000)))
                    due_date = invoice_date + timedelta(days=random.choice([15, 30, 45, 60]))

                    # Determine payment behavior based on personality
                    paid_date, paid_amount, days_late, pay_status = self._generate_payment(
                        personality, due_date, amount
                    )

                    inv_num = f'INV-{customer.id:04d}-{invoice_date.strftime("%Y%m")}-{m+1:03d}'

                    PaymentRecord.objects.create(
                        customer=customer,
                        invoice_number=inv_num,
                        invoice_date=invoice_date,
                        due_date=due_date,
                        amount=amount,
                        paid_amount=paid_amount,
                        paid_date=paid_date,
                        days_late=days_late,
                        status=pay_status,
                    )
                    total_records += 1

        self.stdout.write(f'Created {total_records} payment records')

        # Compute analytics
        for customer in customers:
            self._compute_analytics(customer)

        self.stdout.write(self.style.SUCCESS(f'Successfully seeded demo data!'))
        self.stdout.write(f'  Login: demo@msmepaytrack.com / demo1234')
        self.stdout.write(f'  Customers: {len(customers)}')
        self.stdout.write(f'  Payment records: {total_records}')

    def _generate_payment(self, personality, due_date, amount):
        """Generate payment data based on customer personality."""
        today = date.today()

        if personality == 'excellent':
            # 90% on-time, 10% 1-5 days late
            if random.random() < 0.9:
                paid_date = due_date - timedelta(days=random.randint(0, 5))
                days_late = 0
            else:
                late_days = random.randint(1, 5)
                paid_date = due_date + timedelta(days=late_days)
                days_late = late_days
            paid_amount = amount
            status = 'PAID' if days_late == 0 else 'LATE'

        elif personality == 'good':
            # 70% on-time, 30% 1-15 days late
            if random.random() < 0.7:
                paid_date = due_date - timedelta(days=random.randint(0, 3))
                days_late = 0
                status = 'PAID'
            else:
                late_days = random.randint(1, 15)
                paid_date = due_date + timedelta(days=late_days)
                days_late = late_days
                status = 'LATE'
            paid_amount = amount

        elif personality == 'average':
            # 50% on-time, 30% late, 15% partial, 5% overdue
            roll = random.random()
            if roll < 0.5:
                paid_date = due_date - timedelta(days=random.randint(0, 3))
                days_late = 0
                paid_amount = amount
                status = 'PAID'
            elif roll < 0.8:
                late_days = random.randint(5, 30)
                paid_date = due_date + timedelta(days=late_days)
                days_late = late_days
                paid_amount = amount
                status = 'LATE'
            elif roll < 0.95:
                paid_date = due_date + timedelta(days=random.randint(0, 20))
                days_late = max(0, (paid_date - due_date).days)
                paid_amount = amount * Decimal(str(random.uniform(0.3, 0.9)))
                paid_amount = paid_amount.quantize(Decimal('0.01'))
                status = 'PARTIAL'
            else:
                if due_date < today:
                    paid_date = None
                    days_late = 0
                    paid_amount = Decimal('0')
                    status = 'OVERDUE'
                else:
                    paid_date = None
                    days_late = 0
                    paid_amount = Decimal('0')
                    status = 'PENDING'

        elif personality == 'poor':
            # 20% on-time, 40% late (15-60 days), 20% partial, 20% overdue
            roll = random.random()
            if roll < 0.2:
                paid_date = due_date
                days_late = 0
                paid_amount = amount
                status = 'PAID'
            elif roll < 0.6:
                late_days = random.randint(15, 60)
                paid_date = due_date + timedelta(days=late_days)
                days_late = late_days
                paid_amount = amount
                status = 'LATE'
            elif roll < 0.8:
                paid_date = due_date + timedelta(days=random.randint(10, 40))
                days_late = max(0, (paid_date - due_date).days)
                paid_amount = amount * Decimal(str(random.uniform(0.2, 0.7)))
                paid_amount = paid_amount.quantize(Decimal('0.01'))
                status = 'PARTIAL'
            else:
                if due_date < today:
                    paid_date = None
                    days_late = 0
                    paid_amount = Decimal('0')
                    status = 'OVERDUE'
                else:
                    paid_date = None
                    days_late = 0
                    paid_amount = Decimal('0')
                    status = 'PENDING'

        else:  # terrible
            # 10% on-time, 30% late (30-90 days), 20% partial, 40% overdue
            roll = random.random()
            if roll < 0.1:
                paid_date = due_date
                days_late = 0
                paid_amount = amount
                status = 'PAID'
            elif roll < 0.4:
                late_days = random.randint(30, 90)
                paid_date = due_date + timedelta(days=late_days)
                days_late = late_days
                paid_amount = amount
                status = 'LATE'
            elif roll < 0.6:
                paid_date = due_date + timedelta(days=random.randint(20, 60))
                days_late = max(0, (paid_date - due_date).days)
                paid_amount = amount * Decimal(str(random.uniform(0.1, 0.5)))
                paid_amount = paid_amount.quantize(Decimal('0.01'))
                status = 'PARTIAL'
            else:
                if due_date < today:
                    paid_date = None
                    days_late = 0
                    paid_amount = Decimal('0')
                    status = 'OVERDUE'
                else:
                    paid_date = None
                    days_late = 0
                    paid_amount = Decimal('0')
                    status = 'PENDING'

        # Don't set future paid dates
        if paid_date and paid_date > today:
            paid_date = None
            paid_amount = Decimal('0')
            status = 'PENDING' if due_date >= today else 'OVERDUE'
            days_late = 0

        return paid_date, paid_amount, days_late, status

    def _compute_analytics(self, customer):
        """Compute and save analytics for a customer."""
        from django.db.models import Sum, Avg, Count, Q

        records = customer.payment_records.all()
        total_invoices = records.count()
        if total_invoices == 0:
            return

        total_amount = records.aggregate(s=Sum('amount'))['s'] or 0
        total_paid = records.aggregate(s=Sum('paid_amount'))['s'] or 0
        on_time = records.filter(status='PAID').count()
        late = records.filter(status='LATE').count()
        overdue = records.filter(status='OVERDUE').count()
        has_partial = records.filter(status='PARTIAL').exists()
        avg_late = records.filter(days_late__gt=0).aggregate(a=Avg('days_late'))['a'] or 0
        last_pay = records.filter(paid_date__isnull=False).order_by('-paid_date').first()

        score = PaymentAnalytics.compute_score(
            total_invoices, on_time, late, avg_late, overdue, has_partial
        )

        PaymentAnalytics.objects.update_or_create(
            customer=customer,
            defaults={
                'total_invoices': total_invoices,
                'total_amount': total_amount,
                'total_paid': total_paid,
                'on_time_count': on_time,
                'late_count': late,
                'avg_days_late': round(avg_late, 2),
                'last_payment_date': last_pay.paid_date if last_pay else None,
                'payment_score': score,
            }
        )

    def _random_gstin(self):
        """Generate a random-ish GSTIN suffix."""
        chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        return ''.join(random.choice(chars) for _ in range(13))
