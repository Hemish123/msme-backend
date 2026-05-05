"""
Bulk customer upload utility — parses Excel files and creates Customer records.
Uses pandas for parsing and validates each row before import.
"""
import re
import logging
from datetime import date, datetime
from decimal import Decimal
import pandas as pd
from django.db.models import Sum, Avg
from apps.customers.models import Customer, PaymentRecord
from apps.payments.models import PaymentAnalytics

logger = logging.getLogger(__name__)

GST_REGEX = re.compile(r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$')
PAN_REGEX = re.compile(r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$')

GST_TREATMENTS = [
    'Registered Business - Regular',
    'Registered Business - Composition',
    'Unregistered Business',
    'Consumer',
    'Overseas',
    'Special Economic Zone',
    'Deemed Export',
]

PAYMENT_TERMS_MAP = {
    'Due on Receipt': 0,
    'Net 15': 15,
    'Net 30': 30,
    'Net 45': 45,
    'Net 60': 60,
    'Net 90': 90,
}

# Flexible column name mapping: standard_key → list of possible header names
COLUMN_ALIASES = {
    'customer_type': ['Customer Type (Business/Individual)', 'Customer Type', 'Type'],
    'salutation': ['Salutation (Mr./Mrs./Ms./Dr./Prof.)', 'Salutation'],
    'first_name': ['First Name *', 'First Name'],
    'last_name': ['Last Name *', 'Last Name'],
    'company_name': ['Company Name *', 'Company Name', 'Company'],
    'display_name': ['Display Name *', 'Display Name'],
    'email': ['Email Address *', 'Email Address', 'Email'],
    'work_phone': ['Work Phone', 'Phone', 'Work Phone Number'],
    'mobile': ['Mobile', 'Mobile Number', 'Mobile Phone'],
    'gst_treatment': ['GST Treatment *', 'GST Treatment'],
    'gstin': ['GSTIN (GST Number)', 'GSTIN', 'GST Number', 'GSTIN Number'],
    'pan_number': ['PAN Number', 'PAN', 'PAN No'],
    'place_of_supply': ['Place of Supply *', 'Place of Supply', 'State'],
    'tax_preference': ['Tax Preference (Taxable/Tax Exempt)', 'Tax Preference'],
    'payment_terms': ['Payment Terms (Due on Receipt/Net 15/Net 30/Net 45/Net 60/Net 90)',
                      'Payment Terms', 'Terms'],
    'billing_street1': ['Billing Street 1', 'Billing Address 1', 'Billing Street'],
    'billing_street2': ['Billing Street 2', 'Billing Address 2'],
    'billing_city': ['Billing City'],
    'billing_state': ['Billing State'],
    'billing_zip': ['Billing ZIP', 'Billing Zip', 'Billing Pincode'],
    'shipping_street1': ['Shipping Street 1', 'Shipping Address 1', 'Shipping Street'],
    'shipping_street2': ['Shipping Street 2', 'Shipping Address 2'],
    'shipping_city': ['Shipping City'],
    'shipping_state': ['Shipping State'],
    'shipping_zip': ['Shipping ZIP', 'Shipping Zip', 'Shipping Pincode'],
    'remarks': ['Remarks', 'Notes', 'Comments'],
    'invoice_number': ['Invoice Number', 'Invoice No', 'Invoice #', 'Invoice ID'],
    'invoice_date': ['Invoice Date (YYYY-MM-DD)', 'Invoice Date', 'Bill Date', 'Inv Date'],
    'due_date': ['Due Date (YYYY-MM-DD)', 'Due Date', 'Payment Due'],
    'amount': ['Invoice Amount (INR)', 'Invoice Amount', 'Amount', 'Total Amount', 'Bill Amount'],
    'paid_amount': ['Paid Amount (INR)', 'Paid Amount', 'Amount Paid'],
    'paid_date': ['Paid Date (YYYY-MM-DD)', 'Paid Date', 'Payment Date'],
}


def _clean(val):
    """Return stripped string or empty string for NaN/None."""
    if pd.isna(val) or val is None:
        return ''
    return str(val).strip()


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


def _parse_decimal(value):
    """Safely parse a decimal value."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return Decimal('0')
    try:
        return Decimal(str(value).replace(',', ''))
    except Exception:
        return Decimal('0')


def _resolve_columns(df_columns):
    """
    Build a mapping from standard_key → actual column name in the DataFrame.
    Uses flexible matching: exact match first, then case-insensitive substring.
    """
    resolved = {}
    cols_list = list(df_columns)
    cols_lower = {c: c.lower().strip() for c in cols_list}

    for std_key, aliases in COLUMN_ALIASES.items():
        # Try exact match first
        for alias in aliases:
            if alias in cols_list:
                resolved[std_key] = alias
                break
        if std_key in resolved:
            continue
        # Try case-insensitive match
        for alias in aliases:
            alias_lower = alias.lower().strip()
            for col, col_lower in cols_lower.items():
                if col_lower == alias_lower:
                    resolved[std_key] = col
                    break
            if std_key in resolved:
                break
        if std_key in resolved:
            continue
        # Try substring match (for truncated headers)
        for alias in aliases:
            alias_base = alias.replace(' *', '').lower().strip()
            for col, col_lower in cols_lower.items():
                if alias_base in col_lower or col_lower in alias_base:
                    resolved[std_key] = col
                    break
            if std_key in resolved:
                break

    return resolved


def _get_val(row, col_map, key, default=''):
    """Get a value from a row using the resolved column map."""
    col_name = col_map.get(key)
    if not col_name:
        return default
    return _clean(row.get(col_name, default))


def parse_and_import(file_obj, user):
    """
    Parse an uploaded Excel file and import valid customer rows.
    Returns dict: {total, imported, skipped, errors: [{row, reason}], preview: [...]}
    """
    try:
        df = pd.read_excel(file_obj, engine='openpyxl')
    except Exception as e:
        return {'total': 0, 'imported': 0, 'skipped': 0,
                'errors': [{'row': 0, 'reason': 'Failed to read Excel file: %s' % str(e)}]}

    # Clean column names
    df.columns = df.columns.str.strip()

    # Resolve flexible column names
    col_map = _resolve_columns(df.columns)
    logger.info("Resolved column mapping: %s", col_map)

    # Drop template sample/instruction rows (check first 3 rows)
    rows_to_drop = []
    for i in range(min(3, len(df))):
        if len(df.columns) == 0:
            break
        first_val = _clean(df.iloc[i].values[0])
        # Instructions row
        if first_val.startswith('*') or first_val.startswith('Do not'):
            rows_to_drop.append(i)
        # Known sample row from template (Business + Raj)
        elif len(df.columns) > 2:
            third_val = _clean(df.iloc[i].values[2])
            if first_val == 'Business' and third_val == 'Raj':
                rows_to_drop.append(i)
    if rows_to_drop:
        df = df.drop(df.index[rows_to_drop]).reset_index(drop=True)
        logger.info("Dropped %d template rows", len(rows_to_drop))

    total = len(df)
    imported = 0
    skipped = 0
    errors = []
    preview_rows = []
    affected_customers = set()

    for idx, row in df.iterrows():
        row_num = idx + 2  # 1-indexed, +1 for header
        row_errors = []
        row_warnings = []

        # Extract fields using flexible column map
        customer_type = _get_val(row, col_map, 'customer_type', 'Business')
        if customer_type not in ('Business', 'Individual'):
            customer_type = 'Business'

        salutation = _get_val(row, col_map, 'salutation')
        first_name = _get_val(row, col_map, 'first_name')
        last_name = _get_val(row, col_map, 'last_name')
        company_name = _get_val(row, col_map, 'company_name')
        display_name = _get_val(row, col_map, 'display_name')
        email = _get_val(row, col_map, 'email')
        work_phone = _get_val(row, col_map, 'work_phone')
        mobile_phone = _get_val(row, col_map, 'mobile')
        gst_treatment = _get_val(row, col_map, 'gst_treatment')
        gstin = _get_val(row, col_map, 'gstin')
        pan_number = _get_val(row, col_map, 'pan_number')
        place_of_supply = _get_val(row, col_map, 'place_of_supply')
        tax_preference = _get_val(row, col_map, 'tax_preference', 'Taxable')
        payment_terms_str = _get_val(row, col_map, 'payment_terms', 'Due on Receipt')
        billing_street1 = _get_val(row, col_map, 'billing_street1')
        billing_street2 = _get_val(row, col_map, 'billing_street2')
        billing_city = _get_val(row, col_map, 'billing_city')
        billing_state = _get_val(row, col_map, 'billing_state')
        billing_zip = _get_val(row, col_map, 'billing_zip')
        shipping_street1 = _get_val(row, col_map, 'shipping_street1')
        shipping_street2 = _get_val(row, col_map, 'shipping_street2')
        shipping_city = _get_val(row, col_map, 'shipping_city')
        shipping_state = _get_val(row, col_map, 'shipping_state')
        shipping_zip = _get_val(row, col_map, 'shipping_zip')
        remarks_val = _get_val(row, col_map, 'remarks')

        # Build display name from first/last if missing
        if not display_name and first_name:
            display_name = ('%s %s' % (first_name, last_name)).strip()

        # Validate only truly required fields (name and email)
        name = display_name or ('%s %s' % (first_name, last_name)).strip() or company_name
        if not name:
            row_errors.append('Name is required (Display Name or First Name)')
        if not email:
            row_errors.append('Email is required')

        # GST treatment: try to auto-fix common values
        if gst_treatment:
            gst_lower = gst_treatment.lower()
            if gst_treatment not in GST_TREATMENTS:
                # Try fuzzy matching
                matched = False
                for valid_gst in GST_TREATMENTS:
                    if gst_lower in valid_gst.lower() or valid_gst.lower().startswith(gst_lower):
                        gst_treatment = valid_gst
                        matched = True
                        break
                if not matched:
                    # Default based on customer type
                    if customer_type == 'Business':
                        gst_treatment = 'Registered Business - Regular'
                    else:
                        gst_treatment = 'Unregistered Business'
                    row_warnings.append('Auto-corrected GST Treatment to: %s' % gst_treatment)
        else:
            # Default GST treatment
            if customer_type == 'Business':
                gst_treatment = 'Registered Business - Regular'
            else:
                gst_treatment = 'Unregistered Business'

        # Place of supply: default to billing state if empty
        if not place_of_supply and billing_state:
            place_of_supply = billing_state
        if not place_of_supply:
            place_of_supply = 'Gujarat'  # safe default

        # GSTIN/PAN validation: warn but don't block import
        if gstin and not GST_REGEX.match(gstin.upper()):
            row_warnings.append('GSTIN format may be invalid: %s' % gstin)
        if pan_number and not PAN_REGEX.match(pan_number.upper()):
            row_warnings.append('PAN format may be invalid: %s' % pan_number)

        # Tax preference
        if tax_preference not in ('Taxable', 'Tax Exempt'):
            tax_preference = 'Taxable'

        # Payment terms
        payment_terms_days = PAYMENT_TERMS_MAP.get(payment_terms_str, 0)

        # Build preview row
        preview_rows.append({
            'row': row_num,
            'name': name,
            'email': email,
            'phone': work_phone or mobile_phone,
            'gst': gstin,
            'state': place_of_supply,
            'valid': len(row_errors) == 0,
            'errors': '; '.join(row_errors) if row_errors else '',
        })

        if row_errors:
            errors.append({'row': row_num, 'reason': '; '.join(row_errors)})
            skipped += 1
            continue

        # Create or update customer (use update_or_create to handle duplicates gracefully)
        try:
            customer, created = Customer.objects.update_or_create(
                msme_owner=user,
                name=name,
                defaults={
                    'email': email,
                    'phone': work_phone,
                    'company': company_name,
                    'gstin': gstin.upper() if gstin else '',
                    'customer_type': customer_type,
                    'salutation': salutation,
                    'first_name': first_name,
                    'last_name': last_name,
                    'display_name': display_name,
                    'work_phone': work_phone,
                    'mobile': mobile_phone,
                    'gst_treatment': gst_treatment,
                    'place_of_supply': place_of_supply,
                    'pan_number': pan_number.upper() if pan_number else '',
                    'tax_preference': tax_preference,
                    'currency': 'INR',
                    'payment_terms_days': payment_terms_days,
                    'billing_street1': billing_street1,
                    'billing_street2': billing_street2,
                    'billing_city': billing_city,
                    'billing_state': billing_state,
                    'billing_zip': billing_zip,
                    'shipping_street1': shipping_street1,
                    'shipping_street2': shipping_street2,
                    'shipping_city': shipping_city,
                    'shipping_state': shipping_state,
                    'shipping_zip': shipping_zip,
                    'remarks': remarks_val,
                }
            )

            # Extract invoice data if present
            raw_invoice_num = _get_val(row, col_map, 'invoice_number')
            raw_amount = row.get(col_map.get('amount', ''))
            
            # If we have either an amount or an invoice number, try to create a PaymentRecord
            if raw_invoice_num or (raw_amount and str(raw_amount).strip() and str(raw_amount).strip() != 'nan'):
                invoice_number = raw_invoice_num if raw_invoice_num else f'INV-{idx}'
                
                invoice_date = _parse_date(row.get(col_map.get('invoice_date', '')))
                due_date = _parse_date(row.get(col_map.get('due_date', '')))
                amount = _parse_decimal(raw_amount)
                paid_amount = _parse_decimal(row.get(col_map.get('paid_amount', '')))
                paid_date = _parse_date(row.get(col_map.get('paid_date', '')))

                # Default dates if missing
                if not invoice_date:
                    invoice_date = date.today()
                if not due_date:
                    from datetime import timedelta
                    due_date = invoice_date + timedelta(days=payment_terms_days if payment_terms_days else 30)

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
                        'status': status,
                        'days_late': days_late,
                    }
                )
                affected_customers.add(customer)

            # Create default PaymentAnalytics if customer is new and no invoices were added
            if created and customer not in affected_customers:
                PaymentAnalytics.objects.get_or_create(
                    customer=customer,
                    defaults={
                        'total_invoices': 0,
                        'total_amount': 0,
                        'total_paid': 0,
                        'on_time_count': 0,
                        'late_count': 0,
                        'avg_days_late': 0,
                        'last_payment_date': None,
                        'payment_score': 50.0,  # New customer starts at SILVER
                    }
                )

            imported += 1
            if row_warnings:
                logger.info("Row %d imported with warnings: %s", row_num, '; '.join(row_warnings))

        except Exception as e:
            logger.error("Row %d import failed: %s", row_num, str(e))
            errors.append({'row': row_num, 'reason': str(e)})
            skipped += 1

    # Recalculate analytics for all affected customers
    for customer in affected_customers:
        _recompute_analytics(customer)

    return {
        'total': total,
        'imported': imported,
        'skipped': skipped,
        'errors': errors,
        'preview': preview_rows,
    }


def _recompute_analytics(customer):
    """Recompute PaymentAnalytics for a customer based on their PaymentRecords."""
    records = PaymentRecord.objects.filter(customer=customer)
    total_invoices = records.count()
    
    if total_invoices == 0:
        return

    # Aggregates
    aggs = records.aggregate(
        amount=Sum('amount'),
        paid=Sum('paid_amount')
    )
    total_amount = aggs['amount'] or Decimal('0')
    total_paid = aggs['paid'] or Decimal('0')

    # Status counts
    on_time_count = records.filter(status='PAID').count()
    late_count = records.filter(status='LATE').count()
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
