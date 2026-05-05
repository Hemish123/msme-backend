"""
Azure OpenAI integration for intelligent Excel column extraction.
Falls back to heuristic matching when Azure credentials are not available.
"""
import json
import logging
import pandas as pd
from datetime import date, datetime
from decimal import Decimal

from django.conf import settings
from django.db.models import Avg, Count, Sum, Q

from apps.customers.models import Customer, PaymentRecord
from apps.payments.models import PaymentAnalytics
from .parsers import ExcelParser

logger = logging.getLogger(__name__)


class AzureExcelExtractor:
    """
    1. Read the uploaded Excel file with pandas
    2. Try to auto-detect columns using heuristics
    3. Optionally use Azure OpenAI GPT-4o for smart column mapping
    4. Extract all rows using the mapping
    5. Compute days_late and payment status
    6. Upsert Customer and PaymentRecord records
    7. Recompute PaymentAnalytics for each affected customer
    8. Compute credit scores and assign tiers
    """

    def __init__(self, uploaded_file, user):
        self.uploaded_file = uploaded_file
        self.user = user
        self.parser = ExcelParser()
        self.azure_available = bool(
            settings.AZURE_OPENAI_API_KEY and settings.AZURE_OPENAI_ENDPOINT
        )

    def process(self):
        """Main processing pipeline."""
        try:
            self.uploaded_file.upload_status = 'PROCESSING'
            self.uploaded_file.save()

            # Step 1: Read file
            file_path = self.uploaded_file.file.path
            df = self.parser.read_file(file_path)
            self.uploaded_file.total_rows = len(df)
            self.uploaded_file.save()

            # Check if this is a Customer Template (profile data, not payment data)
            customer_template_markers = ['Display Name *', 'First Name *', 'GST Treatment *']
            columns_set = set(df.columns)
            if any(marker in columns_set for marker in customer_template_markers):
                logger.info("Detected Customer Template format — routing to customer bulk import")
                self._process_customer_template(file_path)
                return

            # Step 2-3: Get column mapping (payment data)
            mapping = self._get_column_mapping(df)

            # Step 4: Extract and process rows
            customers_affected = self._process_rows(df, mapping)

            # Step 7-10: Recompute analytics for affected customers
            for customer in customers_affected:
                self._recompute_analytics(customer)

            self.uploaded_file.upload_status = 'DONE'
            self.uploaded_file.save()

            logger.info(f"Successfully processed {self.uploaded_file.processed_rows} rows")

        except Exception as e:
            logger.error(f"Processing failed: {e}")
            self.uploaded_file.upload_status = 'FAILED'
            self.uploaded_file.error_message = str(e)
            self.uploaded_file.save()
            raise

    def _process_customer_template(self, file_path):
        """Handle customer profile template files using the customer bulk import logic."""
        from apps.customers.bulk_upload import parse_and_import

        with open(file_path, 'rb') as f:
            result = parse_and_import(f, self.user)

        self.uploaded_file.processed_rows = result.get('imported', 0)
        self.uploaded_file.total_rows = result.get('total', 0)

        if result.get('errors') and result['imported'] == 0:
            self.uploaded_file.upload_status = 'FAILED'
            error_msgs = [e['reason'] for e in result['errors'][:5]]
            self.uploaded_file.error_message = '; '.join(error_msgs)
        else:
            self.uploaded_file.upload_status = 'DONE'

        self.uploaded_file.save()
        logger.info(f"Customer template import: {result['imported']} imported, {result['skipped']} skipped")

    def _get_column_mapping(self, df):
        """Get column mapping using Azure OpenAI or heuristics."""
        # First try heuristics
        heuristic_mapping = self.parser.heuristic_column_mapping(list(df.columns))
        is_valid, missing = self.parser.validate_mapping(heuristic_mapping)

        if is_valid and not self.azure_available:
            logger.info("Using heuristic column mapping")
            return heuristic_mapping

        if self.azure_available:
            try:
                ai_mapping = self._ai_column_mapping(df)
                if ai_mapping:
                    logger.info("Using AI column mapping")
                    return ai_mapping
            except Exception as e:
                logger.warning(f"AI mapping failed, falling back to heuristic: {e}")

        if not is_valid:
            raise ValueError(
                f"Could not detect required columns: {missing}. "
                f"Please ensure your file has columns for: customer name, amount"
            )

        return heuristic_mapping

    def _ai_column_mapping(self, df):
        """Use Azure OpenAI to detect column mappings."""
        from openai import AzureOpenAI

        client = AzureOpenAI(
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version=settings.AZURE_OPENAI_API_VERSION,
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
        )

        sample_data = self.parser.get_sample_data(df)

        # Build prompt
        system_prompt = (
            "You are a financial data extraction expert. Given column names and sample rows "
            "from an Excel file, map them to: customer_name, invoice_number, invoice_date, "
            "due_date, amount, paid_amount, paid_date. Return ONLY a JSON mapping of "
            "{detected_column_name: standard_field_name}. If a field is not found, map to null."
        )

        user_prompt = (
            f"Column names: {sample_data['columns']}\n\n"
            f"Sample rows (first 5):\n{json.dumps(sample_data['sample_rows'], default=str, indent=2)}\n\n"
            f"Data types: {sample_data['dtypes']}"
        )

        response = client.chat.completions.create(
            model=settings.AZURE_OPENAI_DEPLOYMENT,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
            max_tokens=500,
        )

        raw = response.choices[0].message.content.strip()
        # Extract JSON from possible markdown code block
        if '```' in raw:
            raw = raw.split('```')[1]
            if raw.startswith('json'):
                raw = raw[4:]
            raw = raw.strip()

        ai_result = json.loads(raw)

        # Convert AI result: {detected_col: standard_field} → {standard_field: detected_col}
        mapping = {}
        for detected_col, standard_field in ai_result.items():
            if standard_field and standard_field in [
                'customer_name', 'invoice_number', 'invoice_date',
                'due_date', 'amount', 'paid_amount', 'paid_date'
            ]:
                mapping[standard_field] = detected_col

        return mapping if mapping else None

    def _process_rows(self, df, mapping):
        """Process DataFrame rows and create Customer/PaymentRecord objects."""
        customers_affected = set()
        processed = 0

        for idx, row in df.iterrows():
            try:
                # Extract customer name
                customer_name = str(row.get(mapping.get('customer_name', ''), '')).strip()
                if not customer_name or customer_name == 'nan':
                    continue

                # Get or create customer
                customer, _ = Customer.objects.get_or_create(
                    name=customer_name,
                    msme_owner=self.user,
                    defaults={
                        'company': customer_name,
                    }
                )
                customers_affected.add(customer)

                # Extract fields with safe defaults
                invoice_number = str(row.get(mapping.get('invoice_number', ''), f'INV-{idx}')).strip()
                if invoice_number == 'nan':
                    invoice_number = f'INV-{idx}'

                invoice_date = self._parse_date(row.get(mapping.get('invoice_date', ''), None))
                due_date = self._parse_date(row.get(mapping.get('due_date', ''), None))
                amount = self._parse_decimal(row.get(mapping.get('amount', ''), 0))
                paid_amount = self._parse_decimal(row.get(mapping.get('paid_amount', ''), 0))
                paid_date = self._parse_date(row.get(mapping.get('paid_date', ''), None))

                # Default dates if missing
                if not invoice_date:
                    invoice_date = date.today()
                if not due_date:
                    from datetime import timedelta
                    due_date = invoice_date + timedelta(days=30)

                # Compute days_late and status
                days_late = 0
                if paid_date and due_date:
                    days_late = max(0, (paid_date - due_date).days)

                if paid_date and paid_amount >= amount:
                    status = 'LATE' if days_late > 0 else 'PAID'
                elif paid_date and paid_amount > 0:
                    status = 'PARTIAL'
                elif not paid_date and due_date and due_date < date.today():
                    status = 'OVERDUE'
                else:
                    status = 'PENDING'

                # Create or update payment record
                PaymentRecord.objects.update_or_create(
                    customer=customer,
                    invoice_number=invoice_number,
                    defaults={
                        'invoice_date': invoice_date,
                        'due_date': due_date,
                        'amount': amount,
                        'paid_amount': paid_amount,
                        'paid_date': paid_date,
                        'days_late': days_late,
                        'status': status,
                    }
                )

                processed += 1
                if processed % 50 == 0:
                    self.uploaded_file.processed_rows = processed
                    self.uploaded_file.save()

            except Exception as e:
                logger.warning(f"Error processing row {idx}: {e}")
                continue

        self.uploaded_file.processed_rows = processed
        self.uploaded_file.save()

        return customers_affected

    def _recompute_analytics(self, customer):
        """Recompute PaymentAnalytics for a customer."""
        records = customer.payment_records.all()

        total_invoices = records.count()
        total_amount = records.aggregate(s=Sum('amount'))['s'] or 0
        total_paid = records.aggregate(s=Sum('paid_amount'))['s'] or 0
        on_time_count = records.filter(status='PAID').count()
        late_count = records.filter(status__in=['LATE']).count()
        overdue_count = records.filter(status='OVERDUE').count()
        has_partial = records.filter(status='PARTIAL').exists()
        avg_days_late = records.filter(days_late__gt=0).aggregate(a=Avg('days_late'))['a'] or 0
        last_payment = records.filter(paid_date__isnull=False).order_by('-paid_date').first()
        last_payment_date = last_payment.paid_date if last_payment else None

        # Compute score
        score = PaymentAnalytics.compute_score(
            total_invoices, on_time_count, late_count,
            avg_days_late, overdue_count, has_partial
        )

        PaymentAnalytics.objects.update_or_create(
            customer=customer,
            defaults={
                'total_invoices': total_invoices,
                'total_amount': total_amount,
                'total_paid': total_paid,
                'on_time_count': on_time_count,
                'late_count': late_count,
                'overdue_count': overdue_count,
                'avg_days_late': round(avg_days_late, 2),
                'last_payment_date': last_payment_date,
                'payment_score': score,
            }
        )

    @staticmethod
    def _parse_date(value):
        """Safely parse a date value."""
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return None
        if isinstance(value, (date, datetime)):
            return value if isinstance(value, date) else value.date()
        if isinstance(value, pd.Timestamp):
            return value.date()
        try:
            return pd.to_datetime(str(value)).date()
        except Exception:
            return None

    @staticmethod
    def _parse_decimal(value):
        """Safely parse a decimal value."""
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return Decimal('0')
        try:
            return Decimal(str(value).replace(',', ''))
        except Exception:
            return Decimal('0')
