"""
File Parsers for Supplier Price List Consolidation Tool
Handles parsing of various file formats: CSV, XLS, XLSX, PDF
"""

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
    
    def parse(self, file_path: str, supplier_name: str = None) -> pd.DataFrame:
        """
        Parse a file and return a DataFrame.
        
        Args:
            file_path: Path to the file to parse
            supplier_name: Name of the supplier (for supplier-specific settings)
        
        Returns:
            Parsed data as DataFrame
        """
        raise NotImplementedError("Subclasses must implement parse method")
    
    def _detect_header_row(self, df: pd.DataFrame, max_rows: int = 10) -> int:
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
            row = df.iloc[i]
            # Check if row has reasonable number of non-null values
            non_null_count = row.notna().sum()
            if non_null_count >= 3:  # At least 3 columns with data
                # Check if values look like headers (strings, not numbers)
                string_count = sum(1 for val in row if isinstance(val, str) and len(str(val).strip()) > 0)
                if string_count >= 2:  # At least 2 string values
                    return i
        
        return 0  # Default to first row
    
    def _clean_column_names(self, columns: List[str]) -> List[str]:
        """
        Clean column names for better matching.
        
        Args:
            columns: List of column names
        
        Returns:
            Cleaned column names
        """
        cleaned = []
        for col in columns:
            if pd.isna(col):
                cleaned.append(f"unnamed_column_{len(cleaned)}")
            else:
                # Convert to string and clean
                col_str = str(col).strip().lower()
                # Remove extra whitespace and newlines
                col_str = re.sub(r'\s+', ' ', col_str)
                # Remove special characters except spaces and underscores
                col_str = re.sub(r'[^\w\s]', '', col_str)
                cleaned.append(col_str)
        
        return cleaned


class CSVParser(BaseParser):
    """Parser for CSV files."""
    
    def parse(self, file_path: str, supplier_name: str = None) -> pd.DataFrame:
        """Parse a CSV file."""
        try:
            # Detect encoding
            encoding = self._detect_encoding(file_path)
            
            # Try different delimiters
            delimiters = [',', ';', '\t', '|']
            df = None
            
            for delimiter in delimiters:
                try:
                    df = pd.read_csv(file_path, encoding=encoding, delimiter=delimiter, 
                                   header=None, dtype=str)
                    # Check if we got reasonable data
                    if len(df.columns) > 1 and len(df) > 0:
                        break
                except Exception:
                    continue
            
            if df is None:
                raise ValueError("Could not parse CSV file with any delimiter")
            
            # Detect header row
            header_row = self._detect_header_row(df)
            
            # Re-read with proper header
            df = pd.read_csv(file_path, encoding=encoding, delimiter=delimiter,
                           header=header_row, dtype=str)
            
            # Clean column names
            df.columns = self._clean_column_names(df.columns.tolist())
            
            # Remove empty rows if configured
            if self.file_processing_config.get('skip_empty_rows', True):
                df = df.dropna(how='all')
            
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
    
    def parse(self, file_path: str, supplier_name: str = None) -> pd.DataFrame:
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
    
    def _parse_xlsx(self, file_path: Path, supplier_name: str = None) -> pd.DataFrame:
        """Parse XLSX file using openpyxl."""
        # Get sheet name from supplier config if available
        sheet_name = None
        if supplier_name:
            # This would come from supplier-specific config
            pass
        
        # Read all sheets to find the one with data
        excel_file = pd.ExcelFile(file_path, engine='openpyxl')
        
        if sheet_name and sheet_name in excel_file.sheet_names:
            target_sheet = sheet_name
        else:
            # Use first sheet or find sheet with most data
            target_sheet = excel_file.sheet_names[0]
            if len(excel_file.sheet_names) > 1:
                max_rows = 0
                for sheet in excel_file.sheet_names:
                    try:
                        temp_df = pd.read_excel(excel_file, sheet_name=sheet, header=None, nrows=100)
                        if len(temp_df) > max_rows:
                            max_rows = len(temp_df)
                            target_sheet = sheet
                    except Exception:
                        continue
        
        # Read the target sheet
        df = pd.read_excel(excel_file, sheet_name=target_sheet, header=None, dtype=str)
        
        # Detect header row
        header_row = self._detect_header_row(df)
        
        # Re-read with proper header
        df = pd.read_excel(excel_file, sheet_name=target_sheet, header=header_row, dtype=str)
        
        # Clean column names
        df.columns = self._clean_column_names(df.columns.tolist())
        
        # Remove empty rows
        if self.file_processing_config.get('skip_empty_rows', True):
            df = df.dropna(how='all')
        
        logging.info(f"Successfully parsed XLSX file: {file_path}, sheet: {target_sheet}")
        return df
    
    def _parse_xls(self, file_path: Path, supplier_name: str = None) -> pd.DataFrame:
        """Parse XLS file using xlrd."""
        # Read with xlrd engine
        df = pd.read_excel(file_path, engine='xlrd', header=None, dtype=str)
        
        # Detect header row
        header_row = self._detect_header_row(df)
        
        # Re-read with proper header
        df = pd.read_excel(file_path, engine='xlrd', header=header_row, dtype=str)
        
        # Clean column names
        df.columns = self._clean_column_names(df.columns.tolist())
        
        # Remove empty rows
        if self.file_processing_config.get('skip_empty_rows', True):
            df = df.dropna(how='all')
        
        logging.info(f"Successfully parsed XLS file: {file_path}")
        return df


class PDFParser(BaseParser):
    """Parser for PDF files."""

    def parse(self, file_path: str, supplier_name: str = None) -> pd.DataFrame:
        """Parse a PDF file, with fallback to text extraction."""
        try:
            # Check for a custom strategy in supplier-specific config
            strategy = self.config.get('file_settings', {}).get('pdf_options', {}).get('strategy')

            if strategy == 'pointtech_custom':
                df_custom = self._parse_pointtech_custom(file_path, supplier_name)
                if df_custom is not None and not df_custom.empty:
                    logging.info(f"Successfully parsed PDF with custom strategy '{strategy}'")
                    return df_custom

            # First, try to extract tables
            df = self._parse_tables(file_path)
            
            # Check if table parsing was successful
            required_fields = self.config.get('master_schema', {}).get('required_fields', [])
            if required_fields and df is not None:
                # Clean column names before checking
                df.columns = self._clean_column_names(df.columns.tolist())

                mapped_cols = [col for col in df.columns if col in required_fields]
                # If we don't have at least 2 required fields, try text parsing
                if len(mapped_cols) < 2:
                    logging.warning(f"Table parsing yielded few required columns for {file_path}. Trying text extraction.")
                    df_text = self._parse_text_with_regex(file_path, supplier_name)
                    if df_text is not None and not df_text.empty:
                        logging.info(f"Successfully parsed text from PDF file: {file_path}")
                        return df_text
            
            if df is not None:
                logging.info(f"Successfully parsed tables from PDF file: {file_path}")
                return df
            
            # If table parsing failed or was insufficient, try text parsing as a fallback
            logging.warning(f"Table parsing failed or was insufficient for {file_path}. Trying text extraction.")
            df_text = self._parse_text_with_regex(file_path, supplier_name)
            if df_text is not None and not df_text.empty:
                logging.info(f"Successfully parsed text from PDF file: {file_path}")
                return df_text

            raise ValueError("Could not extract any usable data from PDF")

        except Exception as e:
            logging.error(f"Error parsing PDF file {file_path}: {e}")
            # As a last resort, try text parsing if it hasn't been tried
            if 'df' not in locals() or df is None:
                 try:
                    df_text = self._parse_text_with_regex(file_path, supplier_name)
                    if df_text is not None and not df_text.empty:
                        logging.info(f"Successfully parsed text from PDF file after initial error: {file_path}")
                        return df_text
                 except Exception as text_e:
                    logging.error(f"Text parsing fallback also failed: {text_e}")

            raise e

    def _parse_tables(self, file_path: str) -> Optional[pd.DataFrame]:
        """Extracts tables from a PDF."""
        tables = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                # Use more robust table extraction settings
                page_tables = page.extract_tables(table_settings={
                    "vertical_strategy": "lines",
                    "horizontal_strategy": "lines",
                    "snap_tolerance": 5,
                })
                for table in page_tables:
                    if table and len(table) > 1:
                        df = pd.DataFrame(table[1:], columns=table[0])
                        df = df.dropna(how='all').loc[:, df.notna().any()]
                        if not df.empty and len(df.columns) > 1:
                            tables.append(df)

        if not tables:
            return None

        # Concatenate all found tables
        full_df = pd.concat(tables, ignore_index=True)

        # Clean column names
        full_df.columns = self._clean_column_names(full_df.columns.tolist())
        return full_df.astype(str)

    def _parse_text_with_regex(self, file_path: str, supplier_name: str = None) -> Optional[pd.DataFrame]:
        """Fallback to extract data from PDF using regex on raw text."""
        logging.info(f"Attempting regex-based text extraction for {file_path}")

        # Regex to capture SKU, Description, and Price. This is a generic pattern.
        # It looks for:
        # 1. SKU: Starts with a word character, can contain letters, numbers, hyphens, dots.
        # 2. Description: Any characters, non-greedy.
        # 3. Price: A decimal number, optionally with a dollar sign and commas.
        product_line_regex = re.compile(
            r'^(?P<sku>[\w.-]+)\s+'
            r'(?P<description>.*?)\s{2,}'
            r'(?P<price>\$?\d{1,3}(?:,?\d{3})*\.\d{2})\s*$'
        )

        data = []
        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text(x_tolerance=2, y_tolerance=2)
                if not text:
                    continue

                for line_num, line in enumerate(text.split('\n')):
                    line = line.strip()
                    if not line:
                        continue

                    match = product_line_regex.match(line)
                    if match:
                        data.append(match.groupdict())
                    else:
                        # Log lines that don't match for debugging, but be careful not to be too verbose
                        if page_num < 3 and line_num < 20: # Limit logging to first few lines of first few pages
                             logging.debug(f"Line did not match regex on page {page_num}: '{line}'")

        if not data:
            logging.warning(f"Regex parsing found no data in {file_path}")
            return None

        df = pd.DataFrame(data)

        # Rename columns to match the expected schema
        column_rename = {
            'sku': 'sku',
            'description': 'product_name',
            'price': 'unit_price'
        }
        df.rename(columns=column_rename, inplace=True)

        # Add supplier name if it's not in the data
        if 'supplier_name' not in df.columns and supplier_name:
            df['supplier_name'] = supplier_name

        logging.info(f"Successfully extracted {len(df)} records using regex from {file_path}")
        return df

    def _parse_pointtech_custom(self, file_path: str, supplier_name: str) -> Optional[pd.DataFrame]:
        """Custom parser for Pointtech PDFs."""
        logging.info(f"Using custom Pointtech PDF parser for {file_path}")
        data = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue
                for line in text.split('\n'):
                    parts = line.strip().split()
                    if len(parts) > 2:
                        # Assume SKU is the first part, price is the last, description is the middle
                        sku = parts[0]
                        price = parts[-1]
                        description = " ".join(parts[1:-1])

                        # Basic validation to see if it looks like a product line
                        is_price = re.match(r'^\$?\d+\.\d{2}$', price)
                        if is_price and len(sku) > 3:
                            data.append({
                                'sku': sku,
                                'product_name': description,
                                'unit_price': price,
                                'supplier_name': supplier_name
                            })
        if not data:
            return None

        return pd.DataFrame(data)


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


def parse_file(file_path: str, config: Dict[str, Any], supplier_name: str = None) -> pd.DataFrame:
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
