"""
Unit tests for ConfigManager module.
"""

import unittest
import tempfile
import shutil
import os
from pathlib import Path
import yaml

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from config_manager import ConfigManager


class TestConfigManager(unittest.TestCase):
    """Test cases for ConfigManager class."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.test_dir) / "config"
        self.config_dir.mkdir()
        
        # Create test configuration
        self.test_config = {
            'master_schema': {
                'required_fields': ['sku', 'product_name', 'unit_price'],
                'optional_fields': ['description']
            },
            'default_column_mappings': {
                'sku': ['sku', 'product code'],
                'product_name': ['product name', 'description']
            },
            'validation_rules': {
                'required_field_check': True,
                'price_range_check': {
                    'enabled': True,
                    'min_price': 0.01,
                    'max_price': 10000.00
                }
            }
        }
        
        # Save test configuration
        config_file = self.config_dir / "default_config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(self.test_config, f)
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir)
    
    def test_load_config(self):
        """Test loading configuration."""
        config_manager = ConfigManager(str(self.config_dir))
        config = config_manager.get_config()
        
        self.assertEqual(config['master_schema']['required_fields'], 
                        ['sku', 'product_name', 'unit_price'])
        self.assertTrue(config['validation_rules']['required_field_check'])
    
    def test_validate_config_valid(self):
        """Test configuration validation with valid config."""
        config_manager = ConfigManager(str(self.config_dir))
        config = config_manager.get_config()
        
        errors = config_manager.validate_config(config)
        self.assertEqual(len(errors), 0)
    
    def test_validate_config_invalid(self):
        """Test configuration validation with invalid config."""
        config_manager = ConfigManager(str(self.config_dir))
        
        # Invalid config - missing required sections
        invalid_config = {'invalid': 'config'}
        
        errors = config_manager.validate_config(invalid_config)
        self.assertGreater(len(errors), 0)
    
    def test_create_supplier_config(self):
        """Test creating supplier-specific configuration."""
        config_manager = ConfigManager(str(self.config_dir))
        
        supplier_config = {
            'supplier_name': 'Test Supplier',
            'column_mappings': {
                'sku': ['item_code'],
                'product_name': ['item_name']
            }
        }
        
        config_manager.create_supplier_config('Test Supplier', supplier_config)
        
        # Verify file was created
        supplier_file = self.config_dir / "suppliers" / "Test Supplier.yaml"
        self.assertTrue(supplier_file.exists())
        
        # Verify content
        loaded_config = config_manager.get_supplier_config('Test Supplier')
        self.assertEqual(loaded_config['supplier_name'], 'Test Supplier')
        self.assertEqual(loaded_config['column_mappings']['sku'], ['item_code'])
    
    def test_list_supplier_configs(self):
        """Test listing supplier configurations."""
        config_manager = ConfigManager(str(self.config_dir))
        
        # Create test supplier configs
        suppliers = ['Supplier A', 'Supplier B', 'Supplier C']
        for supplier in suppliers:
            config_manager.create_supplier_config(supplier, {'supplier_name': supplier})
        
        listed_suppliers = config_manager.list_supplier_configs()
        self.assertEqual(set(listed_suppliers), set(suppliers))
    
    def test_get_effective_config(self):
        """Test getting effective configuration with supplier overrides."""
        config_manager = ConfigManager(str(self.config_dir))
        
        # Create supplier with overrides
        supplier_config = {
            'supplier_name': 'Test Supplier',
            'column_mappings': {
                'sku': ['custom_sku'],
                'unit_price': ['custom_price']
            },
            'validation_overrides': {
                'price_range_check': {
                    'enabled': True,
                    'min_price': 1.00,
                    'max_price': 5000.00
                }
            }
        }
        
        config_manager.create_supplier_config('Test Supplier', supplier_config)
        
        effective_config = config_manager.get_effective_config('Test Supplier')
        
        # Check that supplier overrides are applied
        self.assertEqual(effective_config['column_mappings']['sku'], ['custom_sku'])
        self.assertEqual(effective_config['validation_rules']['price_range_check']['max_price'], 5000.00)
        
        # Check that default values are preserved
        self.assertEqual(effective_config['master_schema']['required_fields'], 
                        ['sku', 'product_name', 'unit_price'])


if __name__ == '__main__':
    unittest.main()
