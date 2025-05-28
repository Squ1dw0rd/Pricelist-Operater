"""
Column Mapping Engine for Supplier Price List Consolidation Tool
Handles mapping of supplier columns to standardized schema.
"""

import pandas as pd
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
        
        self.logger.debug(f"ColumnMapper init - config keys: {config.keys()}") # Use self.logger
        self.logger.debug(f"ColumnMapper init - transformations: {config.get('transformations')}") # Use self.logger

        # Determine if supplier_name should be treated as a field to be mapped or a default value
        supplier_name_default_value = self.config.get('transformations', {}).get('supplier_name', {}).get('default_value')

        # Conditionally build required_fields
        self.required_fields = [
            field for field in config.get('master_schema', {}).get('required_fields', [])
            if not (field == 'supplier_name' and supplier_name_default_value)
        ]
        
        # Conditionally build optional_fields
        self.optional_fields = [
            field for field in config.get('master_schema', {}).get('optional_fields', [])
            if not (field == 'supplier_name' and supplier_name_default_value)
        ]
        
    def _get_column_mappings(self) -> Dict[str, List[str]]:
        """Get column mappings for the supplier."""
        default_mappings = self.config.get('default_column_mappings', {})
        
        if self.supplier_name and self.config_manager:
            # Get supplier-specific mappings from config manager
            supplier_mappings = self.config_manager.get_column_mappings(self.supplier_name)
            if supplier_mappings:
                return supplier_mappings
        
        return default_mappings
    
    def reload_mappings(self):
        """Reload column mappings (useful when config_manager is set after initialization)."""
        self.column_mappings = self._get_column_mappings()
    
    def map_columns(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Map DataFrame columns to standardized schema.
        
        Args:
            df: Input DataFrame with original column names
        
        Returns:
            Tuple of (mapped DataFrame, mapping report)
        """
        original_columns = df.columns.tolist()
        mapping_report = {
            'original_columns': original_columns,
            'mapped_fields': {},
            'unmapped_columns': [],
            'missing_required_fields': [],
            'confidence_scores': {}
        }
        
        # Create mapping dictionary
        column_mapping = {}
        used_columns = set()
        
        # Determine if supplier_name should be treated as a field to be populated by default
        supplier_name_default_value = self.config.get('transformations', {}).get('supplier_name', {}).get('default_value')

        # Filter required and optional fields for iteration
        fields_to_map = []
        for field in self.required_fields + self.optional_fields:
            if field == 'supplier_name' and supplier_name_default_value:
                continue # Skip supplier_name if it has a default value
            fields_to_map.append(field)

        self.logger.debug(f"ColumnMapper map_columns - fields_to_map: {fields_to_map}")
        
        # Map each standardized field
        for field_name in fields_to_map: # Iterate over the filtered list
            mapped_column = self._find_best_column_match(field_name, original_columns, used_columns)
            
            if mapped_column:
                column_mapping[mapped_column] = field_name
                used_columns.add(mapped_column)
                mapping_report['mapped_fields'][field_name] = mapped_column
                
                # Calculate confidence score
                confidence = self._calculate_confidence(field_name, mapped_column)
                mapping_report['confidence_scores'][field_name] = confidence
                
                self.logger.info(f"Mapped '{mapped_column}' -> '{field_name}' (confidence: {confidence:.2f})") # Use self.logger
            else:
                # Only warn if it's a required field and not supplier_name (which is handled separately)
                if field_name in self.required_fields: # Check against original required_fields
                    mapping_report['missing_required_fields'].append(field_name)
                    self.logger.warning(f"Required field '{field_name}' could not be mapped") # Use self.logger
        
        # Track unmapped columns
        mapping_report['unmapped_columns'] = [col for col in original_columns if col not in used_columns]
        
        # Create mapped DataFrame
        mapped_df = self._create_mapped_dataframe(df, column_mapping)
        
        # Add supplier name if not present or apply default transformation
        if 'supplier_name' not in mapped_df.columns:
            supplier_name_default = self.config.get('transformations', {}).get('supplier_name', {}).get('default_value')
            if supplier_name_default:
                mapped_df['supplier_name'] = supplier_name_default
            else:
                mapped_df['supplier_name'] = self.supplier_name or 'Unknown'
        
        return mapped_df, mapping_report
    
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
        if pd.isna(text):
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
    
    def _create_mapped_dataframe(self, df: pd.DataFrame, column_mapping: Dict[str, str]) -> pd.DataFrame:
        """
        Create a new DataFrame with mapped column names.
        
        Args:
            df: Original DataFrame
            column_mapping: Dictionary mapping original columns to standardized fields
        
        Returns:
            DataFrame with standardized column names
        """
        mapped_df = pd.DataFrame()
        
        # Map known columns
        for original_col, standard_field in column_mapping.items():
            if original_col in df.columns:
                mapped_df[standard_field] = df[original_col]
        
        # Ensure all required fields exist (even if empty)
        for field in self.required_fields:
            if field not in mapped_df.columns:
                mapped_df[field] = None
        
        # Add optional fields that were mapped
        for field in self.optional_fields:
            if field in column_mapping.values() and field not in mapped_df.columns:
                original_col = next(k for k, v in column_mapping.items() if v == field)
                if original_col in df.columns:
                    mapped_df[field] = df[original_col]
        
        return mapped_df
    
    def suggest_mappings(self, df: pd.DataFrame, threshold: float = 0.6) -> Dict[str, List[Tuple[str, float]]]:
        """
        Suggest possible mappings for manual review.
        
        Args:
            df: Input DataFrame
            threshold: Minimum confidence threshold for suggestions
        
        Returns:
            Dictionary of field -> [(column, confidence), ...] suggestions
        """
        suggestions = {}
        original_columns = df.columns.tolist()
        
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


def create_column_mapper(config: Dict[str, Any], supplier_name: str = None, logger: logging.Logger = None) -> ColumnMapper:
    """
    Create a column mapper instance.
    
    Args:
        config: Configuration dictionary
        supplier_name: Name of the supplier
        logger: Logger instance to use for logging
    
    Returns:
        ColumnMapper instance
    """
    return ColumnMapper(config, supplier_name, logger=logger)
