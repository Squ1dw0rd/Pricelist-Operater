"""
Data Validation Engine for Supplier Price List Consolidation Tool
Handles validation of processed data according to business rules.
"""

import polars as pl
import logging
import re
from typing import Dict, List, Optional, Tuple, Any, Union
from datetime import datetime

class ValidationResult:
    """Container for validation results."""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.info = []
        self.flagged_rows = []
        self.statistics = {}
    
    def add_error(self, message: str, row_index: int = None):
        """Add an error message."""
        self.errors.append({'message': message, 'row': row_index})
        if row_index is not None:
            self.flagged_rows.append(row_index)
    
    def add_warning(self, message: str, row_index: int = None):
        """Add a warning message."""
        self.warnings.append({'message': message, 'row': row_index})
        if row_index is not None:
            self.flagged_rows.append(row_index)
    
    def add_info(self, message: str):
        """Add an info message."""
        self.info.append(message)
    
    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return len(self.errors) > 0
    
    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return len(self.warnings) > 0
    
    def get_summary(self) -> Dict[str, Any]:
        """Get validation summary."""
        return {
            'error_count': len(self.errors),
            'warning_count': len(self.warnings),
            'flagged_rows': len(set(self.flagged_rows)),
            'statistics': self.statistics
        }


class DataValidator:
    """Validates supplier data according to business rules."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the data validator.
        
        Args:
            config: Configuration dictionary containing validation rules
        """
        self.config = config
        self.validation_rules = config.get('validation_rules', {})
        self.required_fields = config.get('master_schema', {}).get('required_fields', [])
    
    def validate(self, df: pl.DataFrame, supplier_name: str = None) -> ValidationResult:
        """
        Validate a DataFrame according to configured rules.

        Args:
            df: DataFrame to validate
            supplier_name: Name of the supplier (for context)

        Returns:
            ValidationResult object
        """
        result = ValidationResult()

        logging.info(f"Starting validation for {supplier_name or 'unknown supplier'}")

        # Convert to pandas for validation (easier compatibility)
        df_pd = df.to_pandas()

        # Basic validation
        self._validate_required_fields(df_pd, result)
        self._validate_data_types(df_pd, result)
        
        # Business rule validation
        if self.validation_rules.get('price_range_check', {}).get('enabled', False):
            self._validate_price_range(df_pd, result)

        if self.validation_rules.get('iqr_outlier_detection', {}).get('enabled', False):
            self._detect_price_outliers(df_pd, result)

        if self.validation_rules.get('duplicate_sku_check', False):
            self._check_duplicate_skus(df_pd, result)

        # Additional validations
        self._validate_data_completeness(df_pd, result)
        self._validate_data_formats(df_pd, result)

        # Generate statistics
        self._generate_statistics(df_pd, result)
        
        logging.info(f"Validation completed: {len(result.errors)} errors, {len(result.warnings)} warnings")
        
        return result
    
    def _validate_required_fields(self, df: pd.DataFrame, result: ValidationResult):
        """Validate that required fields are present and not empty."""
        for field in self.required_fields:
            if field not in df.columns:
                result.add_error(f"Required field '{field}' is missing")
                continue
            
            # Check for empty values in required fields
            empty_mask = df[field].isna() | (df[field].astype(str).str.strip() == '')
            empty_count = empty_mask.sum()
            
            if empty_count > 0:
                result.add_warning(f"Required field '{field}' has {empty_count} empty values")
                
                # Flag individual rows with empty required fields
                for idx in df[empty_mask].index:
                    result.add_warning(f"Row {idx}: Required field '{field}' is empty", idx)
    
    def _validate_data_types(self, df: pd.DataFrame, result: ValidationResult):
        """Validate data types for specific fields."""
        # Validate numeric fields
        numeric_fields = ['unit_price', 'discount_1', 'discount_2', 'net_price']
        
        for field in numeric_fields:
            if field in df.columns:
                self._validate_numeric_field(df, field, result)
    
    def _validate_numeric_field(self, df: pd.DataFrame, field: str, result: ValidationResult):
        """Validate that a field contains valid numeric values."""
        non_null_mask = df[field].notna() & (df[field].astype(str).str.strip() != '')
        
        if not non_null_mask.any():
            return  # No data to validate
        
        # Try to convert to numeric
        numeric_values = pd.to_numeric(df.loc[non_null_mask, field], errors='coerce')
        invalid_mask = numeric_values.isna()
        
        if invalid_mask.any():
            invalid_count = invalid_mask.sum()
            result.add_warning(f"Field '{field}' has {invalid_count} non-numeric values")
            
            # Flag individual invalid rows
            invalid_indices = df.loc[non_null_mask].index[invalid_mask]
            for idx in invalid_indices:
                value = df.loc[idx, field]
                result.add_warning(f"Row {idx}: Invalid numeric value in '{field}': '{value}'", idx)
    
    def _validate_price_range(self, df: pd.DataFrame, result: ValidationResult):
        """Validate that prices are within acceptable range."""
        price_config = self.validation_rules['price_range_check']
        min_price = price_config.get('min_price', 0.01)
        max_price = price_config.get('max_price', 100000.00)
        
        price_fields = ['unit_price', 'net_price']
        
        for field in price_fields:
            if field not in df.columns:
                continue
            
            # Convert to numeric
            numeric_prices = pd.to_numeric(df[field], errors='coerce')
            valid_mask = numeric_prices.notna()
            
            if not valid_mask.any():
                continue
            
            # Check range
            too_low_mask = (numeric_prices < min_price) & valid_mask
            too_high_mask = (numeric_prices > max_price) & valid_mask
            
            if too_low_mask.any():
                count = too_low_mask.sum()
                result.add_warning(f"Field '{field}' has {count} values below minimum (${min_price})")
                
                for idx in df[too_low_mask].index:
                    value = numeric_prices.loc[idx]
                    result.add_warning(f"Row {idx}: {field} too low: ${value:.2f}", idx)
            
            if too_high_mask.any():
                count = too_high_mask.sum()
                result.add_warning(f"Field '{field}' has {count} values above maximum (${max_price})")
                
                for idx in df[too_high_mask].index:
                    value = numeric_prices.loc[idx]
                    result.add_warning(f"Row {idx}: {field} too high: ${value:.2f}", idx)
    
    def _detect_price_outliers(self, df: pd.DataFrame, result: ValidationResult):
        """Detect price outliers using IQR method."""
        iqr_config = self.validation_rules['iqr_outlier_detection']
        multiplier = iqr_config.get('multiplier', 1.5)
        
        price_fields = ['unit_price', 'net_price']
        
        for field in price_fields:
            if field not in df.columns:
                continue
            
            # Convert to numeric
            numeric_prices = pd.to_numeric(df[field], errors='coerce')
            valid_mask = numeric_prices.notna() & (numeric_prices > 0)
            
            if valid_mask.sum() < 4:  # Need at least 4 values for IQR
                continue
            
            valid_prices = numeric_prices[valid_mask]
            
            # Calculate IQR
            q1 = valid_prices.quantile(0.25)
            q3 = valid_prices.quantile(0.75)
            iqr = q3 - q1
            
            # Define outlier bounds
            lower_bound = q1 - multiplier * iqr
            upper_bound = q3 + multiplier * iqr
            
            # Find outliers
            outlier_mask = valid_mask & ((numeric_prices < lower_bound) | (numeric_prices > upper_bound))
            
            if outlier_mask.any():
                count = outlier_mask.sum()
                result.add_info(f"Field '{field}' has {count} potential outliers (IQR method)")
                
                for idx in df[outlier_mask].index:
                    value = numeric_prices.loc[idx]
                    result.add_warning(f"Row {idx}: Potential price outlier in '{field}': ${value:.2f}", idx)
    
    def _check_duplicate_skus(self, df: pd.DataFrame, result: ValidationResult):
        """Check for duplicate SKUs."""
        if 'sku' not in df.columns:
            return
        
        # Remove empty SKUs
        non_empty_skus = df['sku'].dropna()
        non_empty_skus = non_empty_skus[non_empty_skus.astype(str).str.strip() != '']
        
        if len(non_empty_skus) == 0:
            return
        
        # Find duplicates
        duplicate_skus = non_empty_skus[non_empty_skus.duplicated(keep=False)]
        
        if len(duplicate_skus) > 0:
            unique_duplicates = duplicate_skus.unique()
            result.add_warning(f"Found {len(unique_duplicates)} duplicate SKUs affecting {len(duplicate_skus)} rows")
            
            for sku in unique_duplicates:
                duplicate_indices = df[df['sku'] == sku].index.tolist()
                result.add_warning(f"Duplicate SKU '{sku}' found in rows: {duplicate_indices}")
                
                for idx in duplicate_indices:
                    result.add_warning(f"Row {idx}: Duplicate SKU '{sku}'", idx)
    
    def _validate_data_completeness(self, df: pd.DataFrame, result: ValidationResult):
        """Validate overall data completeness."""
        total_rows = len(df)
        
        if total_rows == 0:
            result.add_error("DataFrame is empty")
            return
        
        # Check completeness for each column
        for column in df.columns:
            non_null_count = df[column].notna().sum()
            completeness = non_null_count / total_rows
            
            if completeness < 0.5:  # Less than 50% complete
                result.add_warning(f"Column '{column}' is only {completeness:.1%} complete")
            
            result.statistics[f'{column}_completeness'] = completeness
    
    def _validate_data_formats(self, df: pd.DataFrame, result: ValidationResult):
        """Validate data formats for specific fields."""
        # Validate SKU format (should not be too short or contain only numbers)
        if 'sku' in df.columns:
            self._validate_sku_format(df, result)
        
        # Validate currency format if present
        if 'currency' in df.columns:
            self._validate_currency_format(df, result)
    
    def _validate_sku_format(self, df: pd.DataFrame, result: ValidationResult):
        """Validate SKU format."""
        sku_series = df['sku'].dropna()
        
        for idx, sku in sku_series.items():
            sku_str = str(sku).strip()
            
            if len(sku_str) < 2:
                result.add_warning(f"Row {idx}: SKU too short: '{sku_str}'", idx)
            
            # Check if SKU is only numbers (might be valid but worth flagging)
            if sku_str.isdigit() and len(sku_str) > 10:
                result.add_info(f"Row {idx}: SKU is all numeric: '{sku_str}'")
    
    def _validate_currency_format(self, df: pd.DataFrame, result: ValidationResult):
        """Validate currency format."""
        currency_series = df['currency'].dropna()
        valid_currencies = ['USD', 'AUD', 'EUR', 'GBP', 'CAD', 'JPY']  # Add more as needed
        
        for idx, currency in currency_series.items():
            currency_str = str(currency).strip().upper()
            
            if currency_str not in valid_currencies:
                result.add_warning(f"Row {idx}: Unknown currency code: '{currency_str}'", idx)
    
    def _generate_statistics(self, df: pd.DataFrame, result: ValidationResult):
        """Generate validation statistics."""
        result.statistics['total_rows'] = len(df)
        result.statistics['total_columns'] = len(df.columns)
        
        # Price statistics
        for field in ['unit_price', 'net_price']:
            if field in df.columns:
                numeric_prices = pd.to_numeric(df[field], errors='coerce')
                valid_prices = numeric_prices.dropna()
                
                if len(valid_prices) > 0:
                    result.statistics[f'{field}_count'] = len(valid_prices)
                    result.statistics[f'{field}_min'] = float(valid_prices.min())
                    result.statistics[f'{field}_max'] = float(valid_prices.max())
                    result.statistics[f'{field}_mean'] = float(valid_prices.mean())
                    result.statistics[f'{field}_median'] = float(valid_prices.median())
        
        # SKU statistics
        if 'sku' in df.columns:
            non_empty_skus = df['sku'].dropna()
            non_empty_skus = non_empty_skus[non_empty_skus.astype(str).str.strip() != '']
            
            result.statistics['sku_count'] = len(non_empty_skus)
            result.statistics['unique_sku_count'] = non_empty_skus.nunique()
            result.statistics['duplicate_sku_count'] = len(non_empty_skus) - non_empty_skus.nunique()


def validate_data(df: pl.DataFrame, config: Dict[str, Any], supplier_name: str = None) -> ValidationResult:
    """
    Validate a DataFrame using the configured validation rules.
    
    Args:
        df: DataFrame to validate
        config: Configuration dictionary
        supplier_name: Name of the supplier (for context)
    
    Returns:
        ValidationResult object
    """
    validator = DataValidator(config)
    return validator.validate(df, supplier_name)


def create_validation_report(result: ValidationResult, supplier_name: str = None) -> str:
    """
    Create a human-readable validation report.
    
    Args:
        result: ValidationResult object
        supplier_name: Name of the supplier
    
    Returns:
        Formatted validation report as string
    """
    report_lines = []
    
    # Header
    supplier_text = f" for {supplier_name}" if supplier_name else ""
    report_lines.append(f"Validation Report{supplier_text}")
    report_lines.append("=" * 50)
    
    # Summary
    summary = result.get_summary()
    report_lines.append(f"Total Rows: {summary['statistics'].get('total_rows', 0)}")
    report_lines.append(f"Errors: {summary['error_count']}")
    report_lines.append(f"Warnings: {summary['warning_count']}")
    report_lines.append(f"Flagged Rows: {summary['flagged_rows']}")
    report_lines.append("")
    
    # Errors
    if result.errors:
        report_lines.append("ERRORS:")
        for error in result.errors:
            row_text = f" (Row {error['row']})" if error['row'] is not None else ""
            report_lines.append(f"  - {error['message']}{row_text}")
        report_lines.append("")
    
    # Warnings
    if result.warnings:
        report_lines.append("WARNINGS:")
        for warning in result.warnings:
            row_text = f" (Row {warning['row']})" if warning['row'] is not None else ""
            report_lines.append(f"  - {warning['message']}{row_text}")
        report_lines.append("")
    
    # Statistics
    if result.statistics:
        report_lines.append("STATISTICS:")
        for key, value in result.statistics.items():
            if isinstance(value, float):
                report_lines.append(f"  {key}: {value:.2f}")
            else:
                report_lines.append(f"  {key}: {value}")
    
    return "\n".join(report_lines)
