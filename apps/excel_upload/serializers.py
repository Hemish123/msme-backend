from rest_framework import serializers
from .models import UploadedFile


class UploadedFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UploadedFile
        fields = ['id', 'file', 'original_filename', 'uploaded_by', 'upload_status',
                  'total_rows', 'processed_rows', 'error_message', 'created_at']
        read_only_fields = ['id', 'uploaded_by', 'upload_status', 'total_rows',
                           'processed_rows', 'error_message', 'created_at']


class UploadStatusSerializer(serializers.ModelSerializer):
    progress_percent = serializers.SerializerMethodField()

    class Meta:
        model = UploadedFile
        fields = ['id', 'original_filename', 'upload_status', 'total_rows',
                  'processed_rows', 'progress_percent', 'error_message', 'created_at']

    def get_progress_percent(self, obj):
        if obj.total_rows == 0:
            return 0
        return round((obj.processed_rows / obj.total_rows) * 100, 1)
