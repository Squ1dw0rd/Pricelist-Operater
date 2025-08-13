"""
Configuration Manager for Supplier Price List Consolidation Tool
Handles loading and managing configuration settings.
"""

import os
import yaml
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
import copy

class ConfigManager:
    """Manages configuration settings for the application."""
    
    def __init__(self, config_dir: str = "config", logger: Optional[logging.Logger] = None):
        """
        Initialize the configuration manager.
        
        Args:
            config_dir: Directory containing configuration files
            logger: Optional logger instance
        """
        self.config_dir = Path(config_dir)
        self.default_config_path = self.config_dir / "default_config.yaml"
        self.supplier_configs_dir = self.config_dir / "suppliers"
        self.config = {}
        self.supplier_configs = {}

        if logger:
            self.logger = logger
        else:
            # Create a basic logger if none is provided
            self.logger = logging.getLogger(__name__)
            if not self.logger.handlers:
                handler = logging.StreamHandler()
                formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                handler.setFormatter(formatter)
                self.logger.addHandler(handler)
                self.logger.setLevel(logging.INFO)
        
        # Create supplier configs directory if it doesn't exist
        self.supplier_configs_dir.mkdir(exist_ok=True)
        
        self._load_default_config()
        self._load_supplier_configs()
    
    def _load_default_config(self) -> None:
        """Load the default configuration."""
        try:
            with open(self.default_config_path, 'r', encoding='utf-8') as file:
                self.config = yaml.safe_load(file)
            self.logger.info(f"Loaded default configuration from {self.default_config_path}")
        except FileNotFoundError:
            self.logger.error(f"Default configuration file not found: {self.default_config_path}")
            raise
        except yaml.YAMLError as e:
            self.logger.error(f"Error parsing default configuration: {e}")
            raise
    
    def _load_supplier_configs(self) -> None:
        """Load supplier-specific configurations."""
        for config_file in self.supplier_configs_dir.glob("*.yaml"):
            supplier_name = config_file.stem
            try:
                with open(config_file, 'r', encoding='utf-8') as file:
                    supplier_config = yaml.safe_load(file)
                    self.supplier_configs[supplier_name] = supplier_config
                self.logger.info(f"Loaded supplier configuration for {supplier_name}")
            except yaml.YAMLError as e:
                self.logger.error(f"Error parsing supplier configuration {config_file}: {e}")
    
    def get_config(self, key: str = None) -> Any:
        """
        Get configuration value(s).
        
        Args:
            key: Configuration key (dot notation supported, e.g., 'validation_rules.price_range_check')
                 If None, returns entire configuration
        
        Returns:
            Configuration value or entire config if key is None
        """
        if key is None:
            return self.config
        
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return None
        
        return value
    
    def get_supplier_config(self, supplier_name: str) -> Dict[str, Any]:
        """
        Get configuration for a specific supplier.
        
        Args:
            supplier_name: Name of the supplier
        
        Returns:
            Supplier-specific configuration merged with defaults
        """
        # Start with default configuration
        merged_config = copy.deepcopy(self.config)
        self.logger.debug(f"get_supplier_config: Initial merged_config (from default): {merged_config.keys()}")
        
        # Merge supplier-specific configuration if it exists
        if supplier_name in self.supplier_configs:
            supplier_config = self.supplier_configs[supplier_name]
            self.logger.debug(f"get_supplier_config: Supplier config for {supplier_name}: {supplier_config.keys()}")
            merged_config = self._deep_merge(merged_config, supplier_config)
            self.logger.debug(f"get_supplier_config: Merged config after deep_merge: {merged_config.keys()}")
        
        self.logger.debug(f"get_supplier_config: Final merged_config transformations: {merged_config.get('transformations')}")
        return merged_config
    
    def get_column_mappings(self, supplier_name: str = None) -> Dict[str, List[str]]:
        """
        Get column mappings for a supplier or default mappings.
        
        Args:
            supplier_name: Name of the supplier (optional)
        
        Returns:
            Dictionary of field mappings
        """
        if supplier_name:
            # Try exact match first
            if supplier_name in self.supplier_configs:
                supplier_config = self.supplier_configs[supplier_name]
                if 'column_mappings' in supplier_config:
                    # Merge with default mappings
                    default_mappings = self.config.get('default_column_mappings', {})
                    supplier_mappings = supplier_config['column_mappings']
                    return self._deep_merge(default_mappings, supplier_mappings)
            
            # Try fuzzy matching with config file names
            normalized_supplier = self._normalize_supplier_name(supplier_name)
            for config_name, supplier_config in self.supplier_configs.items():
                normalized_config = self._normalize_supplier_name(config_name)
                if normalized_supplier == normalized_config:
                    if 'column_mappings' in supplier_config:
                        default_mappings = self.config.get('default_column_mappings', {})
                        supplier_mappings = supplier_config['column_mappings']
                        return self._deep_merge(default_mappings, supplier_mappings)
        
        return self.config.get('default_column_mappings', {})
    
    def _normalize_supplier_name(self, name: str) -> str:
        """Normalize supplier name for matching."""
        if not name:
            return ""
        
        # Convert to lowercase, remove spaces, special chars
        normalized = ''.join(c.lower() for c in name if c.isalnum())
        return normalized
    
    def get_validation_rules(self, supplier_name: str = None) -> Dict[str, Any]:
        """
        Get validation rules for a supplier or default rules.
        
        Args:
            supplier_name: Name of the supplier (optional)
        
        Returns:
            Dictionary of validation rules
        """
        config = self.get_supplier_config(supplier_name) if supplier_name else self.config
        return config.get('validation_rules', {})
    
    def create_supplier_config_template(self, supplier_name: str) -> str:
        """
        Create a template configuration file for a new supplier.
        
        Args:
            supplier_name: Name of the supplier
        
        Returns:
            Path to the created template file
        """
        template = {
            'supplier_info': {
                'name': supplier_name,
                'contact': '',
                'notes': ''
            },
            'file_settings': {
                'expected_format': 'xlsx',  # xlsx, xls, csv, pdf
                'header_row': 1,
                'data_start_row': 2,
                'sheet_name': None  # None for first sheet
            },
            'column_mappings': {
                # Override default mappings here
                # Example:
                # 'sku': ['custom_sku_column', 'item_id'],
                # 'unit_price': ['price_column', 'cost']
            },
            'validation_rules': {
                # Override default validation rules here
                # Example:
                # 'price_range_check': {
                #     'enabled': True,
                #     'min_price': 1.00,
                #     'max_price': 50000.00
                # }
            },
            'data_transformations': {
                # Custom transformations for this supplier
                # Example:
                # 'price_multiplier': 1.0,
                # 'currency_conversion': None
            }
        }
        
        config_file = self.supplier_configs_dir / f"{supplier_name}.yaml"
        with open(config_file, 'w', encoding='utf-8') as file:
            yaml.dump(template, file, default_flow_style=False, indent=2)
        
        self.logger.info(f"Created supplier configuration template: {config_file}")
        return str(config_file)
    
    def _deep_merge(self, base_dict: Dict, update_dict: Dict) -> Dict:
        """
        Deep merge two dictionaries.
        
        Args:
            base_dict: Base dictionary
            update_dict: Dictionary to merge into base
        
        Returns:
            Merged dictionary
        """
        result = base_dict.copy()
        self.logger.debug(f"_deep_merge: Merging {update_dict.keys()} into {base_dict.keys()}")
        
        for key, value in update_dict.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                self.logger.debug(f"_deep_merge: Recursively merging key '{key}'")
                result[key] = self._deep_merge(result[key], value)
            else:
                self.logger.debug(f"_deep_merge: Setting key '{key}' to '{value}'")
                result[key] = value
        
        self.logger.debug(f"_deep_merge: Resulting dict keys: {result.keys()}")
        return result
    
    def validate_config(self) -> List[str]:
        """
        Validate the configuration.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Check required sections
        required_sections = ['master_schema', 'default_column_mappings', 'validation_rules']
        for section in required_sections:
            if section not in self.config:
                errors.append(f"Missing required configuration section: {section}")
        
        # Check master schema
        if 'master_schema' in self.config:
            schema = self.config['master_schema']
            if 'required_fields' not in schema:
                errors.append("Missing 'required_fields' in master_schema")
        
        # Check validation rules
        if 'validation_rules' in self.config:
            rules = self.config['validation_rules']
            if 'price_range_check' in rules and rules['price_range_check'].get('enabled'):
                price_check = rules['price_range_check']
                if 'min_price' not in price_check or 'max_price' not in price_check:
                    errors.append("Price range check enabled but min_price or max_price not specified")
        
        return errors
