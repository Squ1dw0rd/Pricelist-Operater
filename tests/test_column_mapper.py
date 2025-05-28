"""
Unit tests for ColumnMapper module.
"""

import unittest
import pandas as pd
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from column_mapper import ColumnMapper


class TestColumnMapper(unittest.TestCase):
    """Test cases for ColumnMapper class."""
    
    def setUp(self):
        """Set up test environment."""
        self.config = {
            'master_schema': {
                'required_fields': ['sku', 'product_name', 'unit_price'],
                'optional_fields': ['description', 'category']
            },
            'default_column_mappings': {
                'sku': ['sku', 'product code', 'item code'],
                'product_name': ['product name', 'description', 'name'],
                'unit_price': ['unit price', 'price', 'cost'],
                'description': ['description', 'long description'],
                'category': ['category', 'type']
            }
        }
        
        self.mapper = ColumnMapper(self.config)
    
    def test_exact_match_mapping(self):
        """Test exact column name matching."""
        columns = ['SKU', 'Product Name', 'Unit Price', 'Description']
        
        mappings, unmapped = self.mapper.map_columns(columns)
        
        self.assertEqual(mappings['sku'], 'SKU')
        self.assertEqual(mappings['product_name'], 'Product Name')
        self.assertEqual(mappings['unit_price'], 'Unit Price')
        self.assertEqual(mappings['description'], 'Description')
        self.assertEqual(len(unmapped), 0)
    
    def test_fuzzy_match_mapping(self):
        """Test fuzzy column name matching."""
        columns = ['Product_Code', 'Item_Name', 'List_Price', 'Item_Description']
        
        mappings, unmapped = self.mapper.map_columns(columns)
        
        # Should find fuzzy matches
        self.assertIn('sku', mappings)
        self.assertIn('product_name', mappings)
        self.assertIn('unit_price', mappings)
        self.assertIn('description', mappings)
    
    def test_case_insensitive_mapping(self):
        """Test case-insensitive column matching."""
        columns = ['PRODUCT CODE', 'product name', 'Unit_Price', 'DESCRIPTION']
        
        mappings, unmapped = self.mapper.map_columns(columns)
        
        self.assertEqual(mappings['sku'], 'PRODUCT CODE')
        self.assertEqual(mappings['product_name'], 'product name')
        self.assertEqual(mappings['unit_price'], 'Unit_Price')
        self.assertEqual(mappings['description'], 'DESCRIPTION')
    
    def test_partial_mapping(self):
        """Test mapping with some unmapped columns."""
        columns = ['SKU', 'Product Name', 'Unknown Column', 'Random Field']
        
        mappings, unmapped = self.mapper.map_columns(columns)
        
        self.assertEqual(mappings['sku'], 'SKU')
        self.assertEqual(mappings['product_name'], 'Product Name')
        self.assertIn('Unknown Column', unmapped)
        self.assertIn('Random Field', unmapped)
    
    def test_supplier_specific_mapping(self):
        """Test supplier-specific column mappings."""
        supplier_mappings = {
            'sku': ['custom_sku', 'item_id'],
            'unit_price': ['net_price', 'selling_price']
        }
        
        columns = ['custom_sku', 'Product Name', 'net_price']
        
        mappings, unmapped = self.mapper.map_columns(columns, supplier_mappings)
        
        self.assertEqual(mappings['sku'], 'custom_sku')
        self.assertEqual(mappings['product_name'], 'Product Name')
        self.assertEqual(mappings['unit_price'], 'net_price')
    
    def test_transform_data(self):
        """Test data transformation with column mapping."""
        # Create test DataFrame
        data = pd.DataFrame({
            'Product Code': ['A001', 'A002', 'A003'],
            'Item Name': ['Product 1', 'Product 2', 'Product 3'],
            'List Price': [10.50, 25.00, 15.75],
            'Extra Column': ['Extra 1', 'Extra 2', 'Extra 3']
        })
        
        mappings = {
            'sku': 'Product Code',
            'product_name': 'Item Name',
            'unit_price': 'List Price'
        }
        
        transformed_data = self.mapper.transform_data(data, mappings, 'Test Supplier')
        
        # Check transformed columns
        self.assertIn('sku', transformed_data.columns)
        self.assertIn('product_name', transformed_data.columns)
        self.assertIn('unit_price', transformed_data.columns)
        self.assertIn('supplier_name', transformed_data.columns)
        
        # Check data values
        self.assertEqual(transformed_data['sku'].iloc[0], 'A001')
        self.assertEqual(transformed_data['product_name'].iloc[0], 'Product 1')
        self.assertEqual(transformed_data['unit_price'].iloc[0], 10.50)
        self.assertEqual(transformed_data['supplier_name'].iloc[0], 'Test Supplier')
    
    def test_data_type_conversion(self):
        """Test automatic data type conversion."""
        # Create test DataFrame with mixed types
        data = pd.DataFrame({
            'SKU': ['A001', 'A002', 'A003'],
            'Product Name': ['Product 1', 'Product 2', 'Product 3'],
            'Unit Price': ['10.50', '25.00', '15.75'],  # String prices
            'Quantity': ['100', '200', '150']  # String numbers
        })
        
        mappings = {
            'sku': 'SKU',
            'product_name': 'Product Name',
            'unit_price': 'Unit Price'
        }
        
        transformed_data = self.mapper.transform_data(data, mappings, 'Test Supplier')
        
        # Check that prices were converted to float
        self.assertEqual(transformed_data['unit_price'].dtype, 'float64')
        self.assertEqual(transformed_data['unit_price'].iloc[0], 10.50)
    
    def test_missing_required_fields(self):
        """Test handling of missing required fields."""
        columns = ['Product Name', 'Description']  # Missing SKU and unit_price
        
        mappings, unmapped = self.mapper.map_columns(columns)
        
        missing_required = self.mapper.get_missing_required_fields(mappings)
        
        self.assertIn('sku', missing_required)
        self.assertIn('unit_price', missing_required)
        self.assertNotIn('product_name', missing_required)
    
    def test_confidence_scores(self):
        """Test mapping confidence scores."""
        columns = ['SKU', 'Product_Name_Fuzzy', 'Price_Approximate']
        
        mappings, unmapped, confidence = self.mapper.map_columns_with_confidence(columns)
        
        # Exact match should have high confidence
        self.assertGreater(confidence.get('sku', 0), 0.9)
        
        # Fuzzy matches should have lower confidence
        self.assertLess(confidence.get('product_name', 1.0), 0.9)
        self.assertLess(confidence.get('unit_price', 1.0), 0.9)
    
    def test_empty_dataframe(self):
        """Test handling of empty DataFrame."""
        empty_data = pd.DataFrame()
        
        mappings = {'sku': 'SKU', 'product_name': 'Product Name'}
        
        transformed_data = self.mapper.transform_data(empty_data, mappings, 'Test Supplier')
        
        # Should return empty DataFrame with correct columns
        self.assertTrue(transformed_data.empty)
        self.assertIn('supplier_name', transformed_data.columns)


if __name__ == '__main__':
    unittest.main()
