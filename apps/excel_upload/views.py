import threading
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser

from utils.response import api_response, api_error
from .models import UploadedFile
from .serializers import UploadedFileSerializer, UploadStatusSerializer
from .azure_extractor import AzureExcelExtractor


class ExcelUploadView(APIView):
    """Upload Excel file for processing."""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    def post(self, request):
        file_obj = request.FILES.get('file')
        if not file_obj:
            return api_error(message='No file provided')

        # Validate extension
        filename = file_obj.name.lower()
        if not filename.endswith(('.xlsx', '.xls', '.csv')):
            return api_error(message='Unsupported file type. Use .xlsx, .xls, or .csv')

        # Save uploaded file record
        uploaded = UploadedFile.objects.create(
            file=file_obj,
            original_filename=file_obj.name,
            uploaded_by=request.user,
            upload_status='PENDING'
        )

        # Process in background thread
        extractor = AzureExcelExtractor(uploaded, request.user)
        thread = threading.Thread(target=extractor.process, daemon=True)
        thread.start()

        serializer = UploadedFileSerializer(uploaded)
        return api_response(
            data=serializer.data,
            message='File uploaded, processing started',
            status_code=status.HTTP_201_CREATED
        )


class UploadStatusView(APIView):
    """Poll upload processing status."""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            uploaded = UploadedFile.objects.get(pk=pk, uploaded_by=request.user)
        except UploadedFile.DoesNotExist:
            return api_error(message='Upload not found', status_code=status.HTTP_404_NOT_FOUND)

        serializer = UploadStatusSerializer(uploaded)
        return api_response(data=serializer.data)


class UploadHistoryView(APIView):
    """List all uploads by the current user."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        uploads = UploadedFile.objects.filter(uploaded_by=request.user)
        serializer = UploadStatusSerializer(uploads, many=True)
        return api_response(data=serializer.data)
