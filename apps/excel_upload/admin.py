from django.contrib import admin
from .models import UploadedFile


@admin.register(UploadedFile)
class UploadedFileAdmin(admin.ModelAdmin):
    list_display = ['original_filename', 'uploaded_by', 'upload_status',
                    'total_rows', 'processed_rows', 'created_at']
    search_fields = ['original_filename', 'uploaded_by__email']
    list_filter = ['upload_status', 'created_at']
    ordering = ['-created_at']
