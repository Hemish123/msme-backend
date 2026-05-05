"""
Excel file parser using pandas.
Handles reading and basic validation of uploaded Excel/CSV files.
"""
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class ExcelParser:
    """Parse uploaded Excel/CSV files into DataFrames."""

    SUPPORTED_EXTENSIONS = ['.xlsx', '.xls', '.csv']

    @staticmethod
    def read_file(file_path):
        """Read an Excel or CSV file and return a DataFrame."""
        file_str = str(file_path).lower()

        try:
            if file_str.endswith('.csv'):
                df = pd.read_csv(file_path)
            elif file_str.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(file_path, engine='openpyxl')
            else:
                raise ValueError(f"Unsupported file format: {file_str}")

            # Clean column names
            df.columns = df.columns.str.strip()

            # Drop completely empty rows
            df = df.dropna(how='all')

            logger.info(f"Successfully read file with {len(df)} rows and {len(df.columns)} columns")
            return df

        except Exception as e:
            logger.error(f"Error reading file: {e}")
            raise

    @staticmethod
    def get_sample_data(df, n=5):
        """Get sample rows and column info for AI analysis."""
        sample = df.head(n)
        return {
            'columns': list(df.columns),
            'sample_rows': sample.to_dict('records'),
            'total_rows': len(df),
            'dtypes': {col: str(dtype) for col, dtype in df.dtypes.items()},
        }

    @staticmethod
    def heuristic_column_mapping(columns):
        """
        Attempt to auto-detect column mappings using keyword matching.
        Returns a dict mapping detected columns to standard field names.
        """
        mapping = {}
        columns_lower = {col: col.lower().replace('_', ' ').replace('-', ' ') for col in columns}

        patterns = {
            'customer_name': ['customer name', 'customer', 'client name', 'client', 'party name',
                            'party', 'buyer name', 'buyer', 'name'],
            'invoice_number': ['invoice number', 'invoice no', 'invoice #', 'invoice id',
                             'bill number', 'bill no', 'inv no', 'invoice'],
            'invoice_date': ['invoice date', 'bill date', 'inv date', 'date of invoice'],
            'due_date': ['due date', 'payment due', 'due by', 'payment date due'],
            'amount': ['amount', 'invoice amount', 'total amount', 'bill amount',
                      'invoice value', 'total', 'value'],
            'paid_amount': ['paid amount', 'amount paid', 'payment amount', 'received amount',
                          'paid', 'payment received', 'amount received'],
            'paid_date': ['paid date', 'payment date', 'date paid', 'received date',
                        'date of payment', 'payment received date'],
        }

        for standard_field, keywords in patterns.items():
            for col, col_lower in columns_lower.items():
                if col_lower in keywords or any(kw in col_lower for kw in keywords):
                    if standard_field not in mapping:
                        mapping[standard_field] = col
                        break

        return mapping

    @staticmethod
    def validate_mapping(mapping):
        """Check if essential columns are mapped."""
        required = ['customer_name', 'amount']
        missing = [f for f in required if f not in mapping or mapping[f] is None]
        return len(missing) == 0, missing
