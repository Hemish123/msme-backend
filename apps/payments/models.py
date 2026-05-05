from django.db import models
from django.conf import settings


class CreditTimeline(models.Model):
    """Credit timeline assignment for a customer."""
    TIER_CHOICES = [
        ('PLATINUM', 'Platinum'),
        ('GOLD', 'Gold'),
        ('SILVER', 'Silver'),
        ('BRONZE', 'Bronze'),
        ('BLACKLIST', 'Blacklist'),
    ]

    CREDIT_DAYS_CHOICES = [
        (7, '7 days'),
        (15, '15 days'),
        (30, '30 days'),
        (45, '45 days'),
        (60, '60 days'),
        (90, '90 days'),
    ]

    customer = models.ForeignKey(
        'customers.Customer', on_delete=models.CASCADE, related_name='credit_timelines'
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='assigned_credits'
    )
    credit_days = models.IntegerField(choices=CREDIT_DAYS_CHOICES)
    reason = models.TextField(blank=True, default='')
    score = models.FloatField(default=0)
    tier = models.CharField(max_length=10, choices=TIER_CHOICES, default='BRONZE')
    assigned_at = models.DateTimeField(auto_now_add=True)
    valid_until = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['-assigned_at']

    def __str__(self):
        return f"{self.customer.name} - {self.tier} ({self.credit_days} days)"


class PaymentAnalytics(models.Model):
    """Denormalized payment analytics for fast dashboard queries."""
    customer = models.OneToOneField(
        'customers.Customer', on_delete=models.CASCADE, related_name='analytics'
    )
    total_invoices = models.IntegerField(default=0)
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_paid = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    on_time_count = models.IntegerField(default=0)
    late_count = models.IntegerField(default=0)
    overdue_count = models.IntegerField(default=0)
    avg_days_late = models.FloatField(default=0)
    last_payment_date = models.DateField(null=True, blank=True)
    payment_score = models.FloatField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Payment Analytics'

    def __str__(self):
        return f"Analytics for {self.customer.name} (Score: {self.payment_score})"

    @staticmethod
    def compute_score(total_invoices, on_time_count, late_count, avg_days_late, overdue_count, has_partial):
        """
        Credit score algorithm:
        - Base starts at 50 (Silver)
        - Increases up to 100 based on the on-time payment rate (on_time / total_invoices).
        - Deductions applied for late payments and overdue invoices.
        """
        if total_invoices == 0:
            return 50.0

        # Calculate on-time rate using TOTAL invoices (including pending)
        on_time_rate = on_time_count / total_invoices
        
        # Base score starts at 50 and scales up to 100 based on the on_time_rate
        score = 50.0 + (on_time_rate * 50.0)

        # Deduct for avg days late (max 40)
        score -= min(avg_days_late * 2, 40)

        # Late payment rate penalties based on TOTAL invoices
        late_rate = (late_count / total_invoices) * 100 if total_invoices > 0 else 0
        if late_rate > 50:
            score -= 20
        elif late_rate > 20:
            score -= 10

        # Overdue invoice penalties (max -45)
        score -= min(overdue_count * 15, 45)

        # Partial payment penalty
        if has_partial:
            score -= 5

        return max(0, min(100, round(score, 2)))

    @staticmethod
    def get_tier(score):
        """Return credit tier based on score."""
        if score >= 85:
            return 'PLATINUM'
        elif score >= 70:
            return 'GOLD'
        elif score >= 50:
            return 'SILVER'
        elif score >= 30:
            return 'BRONZE'
        else:
            return 'BLACKLIST'

    @staticmethod
    def get_credit_days(tier):
        """Return eligible credit days based on tier."""
        mapping = {
            'PLATINUM': 90,
            'GOLD': 60,
            'SILVER': 30,
            'BRONZE': 15,
            'BLACKLIST': 0,
        }
        return mapping.get(tier, 0)
