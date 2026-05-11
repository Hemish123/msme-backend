from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    """Custom user model for MSME business owners."""
    email = models.EmailField(unique=True)
    company_name = models.CharField(max_length=255, blank=True, default='')
    company_gst = models.CharField(max_length=50, blank=True, default='')
    company_street = models.CharField(max_length=255, blank=True, default='')
    company_city = models.CharField(max_length=100, blank=True, default='')
    company_state = models.CharField(max_length=100, blank=True, default='')
    company_pin = models.CharField(max_length=20, blank=True, default='')
    company_email = models.EmailField(blank=True, default='')
    bank_name = models.CharField(max_length=255, blank=True, default='')
    bank_account_number = models.CharField(max_length=50, blank=True, default='')
    bank_ifsc = models.CharField(max_length=20, blank=True, default='')
    company_logo = models.ImageField(upload_to='company_logos/', null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-created_at']

    def __str__(self):
        return self.email
