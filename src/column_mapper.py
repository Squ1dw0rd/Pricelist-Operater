"""
Column Mapping Engine for Supplier Price List Consolidation Tool
Handles mapping of supplier columns to standardized schema.
"""

import polars as pl
import logging
from typing import Dict, List, Optional, Tuple, Any
from fuzzywuzzy import fuzz, process
import re
import copy

class ColumnMapper:
    """Maps supplier columns to standardized schema fields."""
    
    def __init__(self, config: Dict[str, Any], supplier_name: str = None, config_manager=None, logger: logging.Logger = None): # Add logger param
        """
        Initialize the column mapper.
        
        Args:
            config: Configuration dictionary
            supplier_name: Name of the supplier (for supplier-specific mappings)
            config_manager: ConfigManager instance for loading supplier configs
            logger: Logger instance to use for logging
        """
        self.logger = logger if logger else logging.getLogger(__name__) # Use passed logger or get a new one
        self.config = config
        self.supplier_name = supplier_name
        self.config_manager = config_manager
        self.column_mappings = self._get_column_mappings()
        
        # For test compatibility, handle both 'default_column_mappings' and 'column_mappings'
        if 'default_column_mappings' in config:
            self.column_mappings = config['default_column_mappings']
        elif 'column_mappings' in config:
            self.column_mappings = config['column_mappings']
        else:
            # Fallback to empty dict if no mappings found
            self.column_mappings = {}
            if self.logger:
                self.logger.warning(f"No column mappings found in config for {supplier_name or 'default'}")
        
        # For test compatibility, handle both 'master_schema' and direct field definitions
        if 'master_schema' in config:
            master_schema = config['master_schema']
            self.required_fields = master_schema.get('required_fields', [])
            self.optional_fields = master_schema.get('optional_fields', [])
        else:
            # Default values for tests
            self.required_fields = config.get('required_fields', ['sku', 'product_name', 'unit_price'])
            self.optional_fields = config.get('optional_fields', ['description', 'category'])
        
    def _get_column_mappings(self) -> Dict[str, List[str]]:
        """Get column mappings for the supplier."""
        default_mappings = self.config.get('default_column_mappings', {})
        
        if self.supplier_name and self.config_manager:
            # Get supplier-specific mappings from config manager
            try:
                supplier_mappings = self.config_manager.get_column_mappings(self.supplier_name)
                if supplier_mappings:
                    self.logger.info(f"Loaded supplier-specific mappings for {self.supplier_name}")
                    return supplier_mappings
                else:
                    self.logger.warning(f"No supplier-specific config found for {self.supplier_name}, using default mappings")
            except Exception as e:
                self.logger.error(f"Error loading supplier config for {self.supplier_name}: {e}, using default mappings")
        
        return default_mappings
    
    def reload_mappings(self):
        """Reload column mappings (useful when config_manager is set after initialization)."""
        self.column_mappings = self._get_column_mappings()
    
    def map_columns(self, columns, supplier_mappings=None) -> Tuple[Dict[str, str], List[str]]:
        """
        Map column names to standardized schema.
        
        Args:
            columns: List of column names
            supplier_mappings: Optional supplier-specific mappings
        
        Returns:
            Tuple of (mapped columns dict, unmapped columns list)
        """
        # Use supplier mappings if provided, otherwise use default mappings
        if supplier_mappings:
            column_mappings = supplier_mappings
        else:
            column_mappings = self.column_mappings
        
        original_columns = columns
        # Create mapping dictionary
        mapped_columns = {}
        unmapped_columns = []
        used_columns = set()
        
        if not column_mappings:
            self.logger.warning("No column mappings available, cannot map columns")
            return {}, original_columns
        
        # Map each standardized field
        for field_name, possible_names in column_mappings.items():
            for column in original_columns:
                if column not in used_columns:
                    # Try exact match first (case insensitive)
                    if column.lower().replace(' ', '_').replace('-', '_') == field_name.lower().replace(' ', '_').replace('-', '_'):
                        mapped_columns[field_name] = column
                        used_columns.add(column)
                        break
                    
                    # Try exact match with possible names
                    for possible_name in possible_names:
                        if column.lower().replace(' ', '_').replace('-', '_') == possible_name.lower().replace(' ', '_').replace('-', '_'):
                            mapped_columns[field_name] = column
                            used_columns.add(column)
                            break
                    else:
                        continue
                    break
        
        # Track unmapped columns
        unmapped_columns = [col for col in original_columns if col not in used_columns]
        
        return mapped_columns, unmapped_columns
    
    def _find_best_column_match(self, field_name: str, available_columns: List[str], 
                               used_columns: set) -> Optional[str]:
        """
        Find the best matching column for a standardized field.
        
        Args:
            field_name: Name of the standardized field
            available_columns: List of available column names
            used_columns: Set of already used columns
        
        Returns:
            Best matching column name or None
        """
        if field_name not in self.column_mappings:
            return None
        
        possible_names = self.column_mappings[field_name]
        unused_columns = [col for col in available_columns if col not in used_columns]
        
        # Try exact matches first
        for possible_name in possible_names:
            for column in unused_columns:
                if self._is_exact_match(possible_name, column):
                    return column
        
        # Try fuzzy matching
        best_match = None
        best_score = 0
        
        for possible_name in possible_names:
            for column in unused_columns:
                score = self._calculate_similarity(possible_name, column)
                if score > best_score and score >= 70:  # Minimum threshold
                    best_score = score
                    best_match = column
        
        return best_match
    
    def _is_exact_match(self, pattern: str, column: str) -> bool:
        """Check if column name exactly matches pattern."""
        pattern_clean = self._normalize_string(pattern)
        column_clean = self._normalize_string(column)
        return pattern_clean == column_clean
    
    def _calculate_similarity(self, pattern: str, column: str) -> float:
        """Calculate similarity score between pattern and column name."""
        pattern_clean = self._normalize_string(pattern)
        column_clean = self._normalize_string(column)
        
        # Use multiple fuzzy matching algorithms
        ratio = fuzz.ratio(pattern_clean, column_clean)
        partial_ratio = fuzz.partial_ratio(pattern_clean, column_clean)
        token_sort_ratio = fuzz.token_sort_ratio(pattern_clean, column_clean)
        token_set_ratio = fuzz.token_set_ratio(pattern_clean, column_clean)
        
        # Weighted average (token-based methods are more reliable for column names)
        score = (ratio * 0.2 + partial_ratio * 0.3 + token_sort_ratio * 0.25 + token_set_ratio * 0.25)
        
        return score
    
    def _normalize_string(self, text: str) -> str:
        """Normalize string for comparison."""
        if text is None or str(text).lower() in ('nan', 'none', ''):
            return ""

        # Convert to lowercase and remove extra whitespace
        text = str(text).lower().strip()

        # Remove special characters except spaces
        text = re.sub(r'[^\w\s]', ' ', text)

        # Replace multiple spaces with single space
        text = re.sub(r'\s+', ' ', text)

        return text.strip()
    
    def _calculate_confidence(self, field_name: str, mapped_column: str) -> float:
        """Calculate confidence score for a mapping."""
        if field_name not in self.column_mappings:
            return 0.0
        
        possible_names = self.column_mappings[field_name]
        max_score = 0
        
        for possible_name in possible_names:
            score = self._calculate_similarity(possible_name, mapped_column)
            max_score = max(max_score, score)
        
        return max_score / 100.0  # Convert to 0-1 scale
    
    def _create_mapped_dataframe(self, df: pl.DataFrame, column_mapping: Dict[str, str]) -> pl.DataFrame:
        """
        Create a new DataFrame with mapped column names.

        Args:
            df: Original DataFrame
            column_mapping: Dictionary mapping original columns to standardized fields

        Returns:
            DataFrame with standardized column names
        """
        # Start with select for known columns
        select_exprs = []
        for original_col, standard_field in column_mapping.items():
            if original_col in df.columns:
                select_exprs.append(pl.col(original_col).alias(standard_field))

        if select_exprs:
            mapped_df = df.select(select_exprs)
        else:
            mapped_df = pl.DataFrame()

        # Ensure all required fields exist (even if empty)
        for field in self.required_fields:
            if field not in mapped_df.columns:
                mapped_df = mapped_df.with_columns(pl.lit(None).alias(field))

        # Add optional fields that were mapped
        for field in self.optional_fields:
            if field in column_mapping.values() and field not in mapped_df.columns:
                original_col = next(k for k, v in column_mapping.items() if v == field)
                if original_col in df.columns:
                    mapped_df = mapped_df.with_columns(pl.col(original_col).alias(field))

        return mapped_df
    
    def suggest_mappings(self, df: pl.DataFrame, threshold: float = 0.6) -> Dict[str, List[Tuple[str, float]]]:
        """
        Suggest possible mappings for manual review.

        Args:
            df: Input DataFrame
            threshold: Minimum confidence threshold for suggestions

        Returns:
            Dictionary of field -> [(column, confidence), ...] suggestions
        """
        suggestions = {}
        original_columns = list(df.columns)
        
        for field_name in self.required_fields + self.optional_fields:
            if field_name not in self.column_mappings:
                continue
            
            field_suggestions = []
            possible_names = self.column_mappings[field_name]
            
            for column in original_columns:
                max_score = 0
                for possible_name in possible_names:
                    score = self._calculate_similarity(possible_name, column)
                    max_score = max(max_score, score)
                
                confidence = max_score / 100.0
                if confidence >= threshold:
                    field_suggestions.append((column, confidence))
            
            # Sort by confidence (highest first)
            field_suggestions.sort(key=lambda x: x[1], reverse=True)
            
            if field_suggestions:
                suggestions[field_name] = field_suggestions
        
        return suggestions
    
    def map_columns_with_confidence(self, columns):
        """
        Map column names to standardized schema with confidence scores.
        
        Args:
            columns: List of column names
        
        Returns:
            Tuple of (mapped columns dict, unmapped columns list, confidence scores dict)
        """
        mapped_columns, unmapped_columns = self.map_columns(columns)
        
        # Calculate confidence scores
        confidence_scores = {}
        for field_name, column_name in mapped_columns.items():
            confidence_scores[field_name] = self._calculate_confidence(field_name, column_name)
        
        return mapped_columns, unmapped_columns, confidence_scores
    
    def transform_data(self, data: pl.DataFrame, mappings: Dict[str, str], supplier_name: str) -> pl.DataFrame:
        """
        Transform data according to mappings.

        Args:
            data: DataFrame with original data
            mappings: Dictionary mapping standardized fields to column names
            supplier_name: Name of the supplier

        Returns:
            Transformed DataFrame
        """
        if data.is_empty():
            # Create empty DataFrame with required columns
            schema = {field: pl.Utf8 for field in list(mappings.keys()) + ['supplier_name']}
            transformed_data = pl.DataFrame(schema=schema)
        else:
            # Create new DataFrame with mapped columns
            select_exprs = []
            for field_name, column_name in mappings.items():
                if column_name in data.columns:
                    select_exprs.append(pl.col(column_name).alias(field_name))

            if select_exprs:
                transformed_data = data.select(select_exprs)
            else:
                transformed_data = pl.DataFrame()

            # Add supplier name
            transformed_data = transformed_data.with_columns(pl.lit(supplier_name).alias('supplier_name'))

            # Convert data types
            if 'unit_price' in transformed_data.columns:
                transformed_data = transformed_data.with_columns(
                    pl.col('unit_price').cast(pl.Float64, strict=False)
                )

        return transformed_data
    
    def get_missing_required_fields(self, mappings):
        """
        Get list of missing required fields.
        
        Args:
            mappings: Dictionary of mapped columns
        
        Returns:
            List of missing required fields
        """
        mapped_fields = set(mappings.keys())
        required_fields = set(self.required_fields)
        return list(required_fields - mapped_fields)
    
    def validate_mapping(self, mapping_report: Dict[str, Any]) -> List[str]:
        """
        Validate the mapping results.
        
        Args:
            mapping_report: Report from map_columns method
        
        Returns:
            List of validation warnings/errors
        """
        issues = []
        
        # Check for missing required fields
        if mapping_report['missing_required_fields']:
            issues.append(f"Missing required fields: {', '.join(mapping_report['missing_required_fields'])}")
        
        # Check for low confidence mappings
        low_confidence_fields = []
        for field, confidence in mapping_report['confidence_scores'].items():
            if confidence < 0.7:  # 70% confidence threshold
                low_confidence_fields.append(f"{field} ({confidence:.2f})")
        
        if low_confidence_fields:
            issues.append(f"Low confidence mappings: {', '.join(low_confidence_fields)}")
        
        # Check for many unmapped columns
        unmapped_count = len(mapping_report['unmapped_columns'])
        total_columns = len(mapping_report['original_columns'])
        
        if unmapped_count > total_columns * 0.5:  # More than 50% unmapped
            issues.append(f"High number of unmapped columns: {unmapped_count}/{total_columns}")
        
        return issues


def create_column_mapper(config: Dict[str, Any], supplier_name: str = None, config_manager=None, logger: logging.Logger = None) -> ColumnMapper:
    """
    Create a column mapper instance.
    
    Args:
        config: Configuration dictionary
        supplier_name: Name of the supplier
        config_manager: ConfigManager instance (optional)
        logger: Logger instance to use for logging
    
    Returns:
        ColumnMapper instance
    """
    return ColumnMapper(config, supplier_name, config_manager=config_manager, logger=logger)
