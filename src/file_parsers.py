"""
File Parsers for Supplier Price List Consolidation Tool
Handles parsing of various file formats: CSV, XLS, XLSX, PDF
"""

import polars as pl
import pandas as pd
import xlrd
import pdfplumber
import logging
import chardet
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import re

class BaseParser:
    """Base class for file parsers."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the parser.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.file_processing_config = config.get('file_processing', {})
    
    def parse(self, file_path: str, supplier_name: str = None) -> pl.DataFrame:
        """
        Parse a file and return a DataFrame.

        Args:
            file_path: Path to the file to parse
            supplier_name: Name of the supplier (for supplier-specific settings)

        Returns:
            Parsed data as DataFrame
        """
        raise NotImplementedError("Subclasses must implement parse method")
    
    def _detect_header_row(self, df: pl.DataFrame, max_rows: int = 10) -> int:
        """
        Detect the header row in a DataFrame.

        Args:
            df: DataFrame to analyze
            max_rows: Maximum number of rows to check

        Returns:
            Index of the header row
        """
        max_rows = min(max_rows, len(df))

        for i in range(max_rows):
            row = df.row(i)
            # Check if row has reasonable number of non-null values
            non_null_count = sum(1 for val in row if val is not None and str(val).strip() != "")
            if non_null_count >= 3:  # At least 3 columns with data
                # Check if values look like headers (strings, not numbers)
                string_count = sum(1 for val in row if isinstance(val, str) and len(str(val).strip()) > 0)
                if string_count >= 2:  # At least 2 string values
                    return i

        return 0  # Default to first row
    
    def _clean_column_names(self, columns: List[Any]) -> List[str]:
        """
        Clean column names for better matching.
 
        Args:
            columns: List of column names (can be any type)
 
        Returns:
            Cleaned column names
        """
        cleaned = []
        for i, col in enumerate(columns):
            # Handle non-string columns (e.g., lists, dicts, datetime, NaN, etc.)
            if isinstance(col, (list, dict)):
                col = str(col)
            elif col is None:
                col = f"unnamed_column_{i}"
            else:
                # Force conversion to string for any other type (datetime, int, float, etc.)
                col = str(col)

            # Clean the string
            col_str = col.strip().lower()
            # Remove extra whitespace and newlines
            col_str = re.sub(r'\s+', ' ', col_str)
            # Remove special characters except spaces and underscores
            col_str = re.sub(r'[^\w\s]', '', col_str)
            cleaned.append(col_str)

        return cleaned


class CSVParser(BaseParser):
    """Parser for CSV files."""
    
    def parse(self, file_path: str, supplier_name: str = None) -> pl.DataFrame:
        """Parse a CSV file."""
        try:
            # Detect encoding
            encoding = self._detect_encoding(file_path)
            
            # Try different delimiters
            delimiters = [',', ';', '\t', '|']
            df = None
            
            for delimiter in delimiters:
                try:
                    df = pl.read_csv(file_path, encoding=encoding, separator=delimiter,
                                    has_header=False)
                    print(f"DEBUG CSV initial read - columns: {list(df.columns)}")
                    print(f"DEBUG CSV initial read - column types: {[str(dtype) for dtype in df.dtypes]}")
                    print(f"DEBUG CSV initial read - first few rows: {df.head(2).to_dicts()}")
                    # Check if we got reasonable data
                    if len(df.columns) > 1 and len(df) > 0:
                        break
                except Exception as delim_err:
                    print(f"DEBUG CSV delimiter {delimiter} failed: {delim_err}")
                    continue

            if df is None:
                raise ValueError("Could not parse CSV file with any delimiter")

            # Detect header row
            header_row = self._detect_header_row(df)
            print(f"DEBUG CSV detected header row: {header_row}")

            # Re-read with proper header
            df = pl.read_csv(file_path, encoding=encoding, separator=delimiter,
                            skip_rows=header_row, has_header=True)
            print(f"DEBUG CSV re-read columns: {list(df.columns)}")
            print(f"DEBUG CSV re-read column types: {[str(dtype) for dtype in df.dtypes]}")

            # Clean column names
            df = df.rename({old: new for old, new in zip(df.columns, self._clean_column_names(list(df.columns)))})

            # Remove empty rows if configured
            if self.file_processing_config.get('skip_empty_rows', True):
                df = df.filter(~pl.all_horizontal(pl.col("*").is_null()))
            
            logging.info(f"Successfully parsed CSV file: {file_path}")
            return df
            
        except Exception as e:
            logging.error(f"Error parsing CSV file {file_path}: {e}")
            raise
    
    def _detect_encoding(self, file_path: str) -> str:
        """Detect file encoding."""
        if not self.file_processing_config.get('encoding_detection', True):
            return 'utf-8'
        
        try:
            with open(file_path, 'rb') as file:
                raw_data = file.read(10000)  # Read first 10KB
                result = chardet.detect(raw_data)
                encoding = result['encoding']
                if encoding and result['confidence'] > 0.7:
                    return encoding
        except Exception:
            pass
        
        return 'utf-8'  # Default fallback


class ExcelParser(BaseParser):
    """Parser for Excel files (.xls and .xlsx)."""
    
    def parse(self, file_path: str, supplier_name: str = None) -> pl.DataFrame:
        """Parse an Excel file."""
        try:
            file_path = Path(file_path)
            
            if file_path.suffix.lower() == '.xls':
                return self._parse_xls(file_path, supplier_name)
            else:
                return self._parse_xlsx(file_path, supplier_name)
                
        except Exception as e:
            logging.error(f"Error parsing Excel file {file_path}: {e}")
            raise
    
    def _parse_xlsx(self, file_path: Path, supplier_name: str = None) -> pl.DataFrame:
        """Parse XLSX file using polars."""
        # Get sheet name from supplier config if available
        sheet_name = None
        if supplier_name:
            # This would come from supplier-specific config
            pass

        # Read all sheets to find the one with data
        # Polars doesn't have ExcelFile equivalent, so read each sheet
        import openpyxl
        wb = openpyxl.load_workbook(file_path, read_only=True)
        sheet_names = wb.sheetnames

        if sheet_name and sheet_name in sheet_names:
            target_sheet = sheet_name
        else:
            # Use first sheet or find sheet with most data
            target_sheet = sheet_names[0]
            if len(sheet_names) > 1:
                max_rows = 0
                for sheet in sheet_names:
                    try:
                        temp_df = pl.read_excel(file_path, sheet_name=sheet, has_header=False, n_rows=100, engine='openpyxl')
                        if len(temp_df) > max_rows:
                            max_rows = len(temp_df)
                            target_sheet = sheet
                    except Exception:
                        continue

        # Read the target sheet
        df = pl.read_excel(file_path, sheet_name=target_sheet, has_header=False, engine='openpyxl')
        print(f"DEBUG XLSX initial read - sheet: {target_sheet}, columns: {list(df.columns)}")
        print(f"DEBUG XLSX initial read - column types: {[str(dtype) for dtype in df.dtypes]}")
        print(f"DEBUG XLSX initial read - first few rows: {df.head(2).to_dicts()}")

        # Detect header row
        header_row = self._detect_header_row(df)
        print(f"DEBUG XLSX detected header row: {header_row}")

        # Re-read full sheet without header, then slice for skip_rows
        full_df = pl.read_excel(file_path, sheet_name=target_sheet, has_header=False, engine='openpyxl')
        
        # Use header_row as column names
        header_values = full_df.row(header_row)
        num_cols = len(full_df.columns)
        header_list = [header_values[i] if i < len(header_values) else None for i in range(num_cols)]
        cleaned_headers = self._clean_column_names(header_list)
        column_dict = {old: new for old, new in zip(full_df.columns, cleaned_headers)}
        full_df = full_df.rename(column_dict)
        
        # Slice data starting after header_row
        df = full_df.slice(header_row + 1, None)
        
        print(f"DEBUG XLSX re-read columns: {list(df.columns)}")
        print(f"DEBUG XLSX re-read column types: {[str(dtype) for dtype in df.dtypes]}")

        # Remove empty rows
        if self.file_processing_config.get('skip_empty_rows', True):
            df = df.filter(~pl.all_horizontal(pl.col("*").is_null()))

        logging.info(f"Successfully parsed XLSX file: {file_path}, sheet: {target_sheet}")
        return df
    
    def _parse_xls(self, file_path: Path, supplier_name: str = None) -> pl.DataFrame:
        """Parse XLS file using xlrd."""
        # Read with xlrd engine
        df_pd = pd.read_excel(file_path, engine='xlrd', header=None, dtype=str)
        print(f"DEBUG XLS initial read - columns: {df_pd.columns.tolist()}")
        print(f"DEBUG XLS initial read - column types: {[type(c) for c in df_pd.columns]}")
        print(f"DEBUG XLS initial read - first few rows: {df_pd.head(2).to_dict('records')}")

        # Detect header row
        header_row = self._detect_header_row(pl.from_pandas(df_pd))
        print(f"DEBUG XLS detected header row: {header_row}")

        # Re-read with proper header
        df_pd = pd.read_excel(file_path, engine='xlrd', header=header_row, dtype=str)
        print(f"DEBUG XLS re-read columns: {df_pd.columns.tolist()}")
        print(f"DEBUG XLS re-read column types: {[type(c) for c in df_pd.columns]}")

        # Clean column names
        df_pd.columns = self._clean_column_names(df_pd.columns.tolist())

        # Remove empty rows
        if self.file_processing_config.get('skip_empty_rows', True):
            df_pd = df_pd.dropna(how='all')

        # Convert to polars
        df = pl.from_pandas(df_pd)

        logging.info(f"Successfully parsed XLS file: {file_path}")
        return df


class PDFParser(BaseParser):
    """Parser for PDF files."""
    
    def parse(self, file_path: str, supplier_name: str = None) -> pd.DataFrame:
        """Parse a PDF file."""
        try:
            tables = []
            
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    # Extract tables from the page
                    page_tables = page.extract_tables()
                    
                    for table_idx, table in enumerate(page_tables):
                        if table and len(table) > 1:  # Must have header and at least one data row
                            print(f"DEBUG PDF page {page_num+1}, table {table_idx}: header row = {table[0]}")
                            print(f"DEBUG PDF header types: {[type(cell) for cell in table[0]]}")
                            # Convert table to DataFrame
                            df = pl.DataFrame(table[1:], schema=table[0])
                            print(f"DEBUG PDF df columns: {list(df.columns)}")
                            print(f"DEBUG PDF df column types: {[str(dtype) for dtype in df.dtypes]}")

                            # Clean and filter
                            df = df.filter(~pl.all_horizontal(pl.col("*").is_null()))  # Remove empty rows
                            df = df.select([pl.col(col) for col in df.columns if not df[col].is_null().all()])  # Remove empty columns

                            if len(df) > 0 and len(df.columns) > 2:  # Must have reasonable data
                                tables.append(df)
            
            if not tables:
                raise ValueError("No tables found in PDF")
            
            # Combine all tables or use the largest one
            if len(tables) == 1:
                df = tables[0]
            else:
                # Use the table with the most rows
                df = max(tables, key=len)

            print(f"DEBUG PDF final df columns: {list(df.columns)}")

            # Clean column names
            df = df.rename({old: new for old, new in zip(df.columns, self._clean_column_names(list(df.columns)))})

            # Convert all data to string type for consistency
            df = df.cast(pl.Utf8)

            logging.info(f"Successfully parsed PDF file: {file_path}")
            return df
            
        except Exception as e:
            logging.error(f"Error parsing PDF file {file_path}: {e}")
            raise


class FileParserFactory:
    """Factory class for creating appropriate file parsers."""
    
    @staticmethod
    def create_parser(file_path: str, config: Dict[str, Any]) -> BaseParser:
        """
        Create appropriate parser based on file extension.
        
        Args:
            file_path: Path to the file
            config: Configuration dictionary
        
        Returns:
            Appropriate parser instance
        """
        file_path = Path(file_path)
        extension = file_path.suffix.lower()
        
        if extension == '.csv':
            return CSVParser(config)
        elif extension in ['.xls', '.xlsx']:
            return ExcelParser(config)
        elif extension == '.pdf':
            return PDFParser(config)
        else:
            raise ValueError(f"Unsupported file format: {extension}")
    
    @staticmethod
    def get_supported_formats() -> List[str]:
        """Get list of supported file formats."""
        return ['.csv', '.xls', '.xlsx', '.pdf']


def parse_file(file_path: str, config: Dict[str, Any], supplier_name: str = None) -> pl.DataFrame:
    """
    Parse a file using the appropriate parser.
    
    Args:
        file_path: Path to the file to parse
        config: Configuration dictionary
        supplier_name: Name of the supplier (optional)
    
    Returns:
        Parsed data as DataFrame
    """
    parser = FileParserFactory.create_parser(file_path, config)
    return parser.parse(file_path, supplier_name)
