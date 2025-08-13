import unittest
from pathlib import Path
import shutil
import pandas as pd
import sys
import os

# Add src directory to Python path to allow direct import of src modules
# This is a common way to handle imports in tests when tests are outside the main package
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))

from main import PriceListConsolidator
from config_manager import ConfigManager

class TestIntermediateCSVCreation(unittest.TestCase):

    def setUp(self):
        self.test_dir = Path(__file__).resolve().parent
        self.temp_config_dir = self.test_dir / "temp_test_config"
        self.temp_suppliers_config_dir = self.temp_config_dir / "suppliers"
        self.temp_input_dir = self.test_dir / "temp_test_input"
        self.temp_output_dir = self.test_dir / "temp_test_output" # This will be the parent for "standardized_csvs"
        self.intermediate_csv_dir = self.temp_output_dir / "standardized_csvs"

        # Clean up and create directories
        for d in [self.temp_config_dir, self.temp_suppliers_config_dir,
                    self.temp_input_dir, self.temp_output_dir, self.intermediate_csv_dir]:
            if d.exists():
                shutil.rmtree(d)
            d.mkdir(parents=True, exist_ok=True)

        # Create dummy default_config.yaml
        self.default_config_content = """
output_options:
  save_intermediate_standardized_csvs: true
logging:
  level: ERROR # Keep logging minimal for tests
  log_directory: "logs"
  console_output: false
  file_rotation: false
master_schema:
  required_fields:
    - SKU
  optional_fields:
    - Price
default_column_mappings: # This is what ConfigManager's validate_config expects
  SKU: # Ensure SKU is here
    - "sku"
    - "product_code" # Example alternative
  Price: # Ensure Price is here
    - "price"
    - "unit_price" # Example alternative
# The following 'column_mappings' is used by the test to define actual test mappings for OurSKU -> SKU
# This might be slightly confusing, but it reflects that 'default_column_mappings' is for validation
# and the actual supplier-level or other override mappings drive the transformation.
# For the purpose of this test, the key is that 'default_column_mappings' exists.
column_mappings: # This section seems to be what the ConfigManager *uses* for mapping logic,
                 # despite validate_config checking for default_column_mappings.
                 # Keeping this as is from previous structure that worked for mapping.
  SKU:
    - "OurSKU" # This is the actual mapping the test relies on for input data
    - "sku"
  Price:
    - "Price" # This is the actual mapping the test relies on for input data
    - "price"
validation_rules: # Added to satisfy validation
  required_field_check: true
  price_range_check:
    enabled: false # Keep simple for this test
  iqr_outlier_detection:
    enabled: false # Keep simple for this test
  duplicate_sku_check: true
  data_type_validation: true
# Minimal supplier config structure if needed by ConfigManager initialization
# suppliers: {}
error_handling:
  continue_on_file_error: true
  max_errors_per_file: 100
file_processing:
  skip_empty_rows: true
# Provide minimal output settings to avoid errors if generate_master_excel is called
output:
  directory_sheet_name: "Directory"
  include_processing_metadata: false
  header_style:
    bold: true
    background_color: "E6E6FA"
"""
        with open(self.temp_config_dir / "default_config.yaml", "w") as f:
            f.write(self.default_config_content)

        # Create dummy TestSupplier.yaml
        self.supplier_config_content = """
file_settings:
  format: csv
column_mapping: # This section is for supplier-specific mappings
  mappings:
    OurSKU: SKU
    Price: Price # Map the input 'Price' column to the standard field 'Price'
  custom_columns: {}
"""
        with open(self.temp_suppliers_config_dir / "TestSupplier.yaml", "w") as f:
            f.write(self.supplier_config_content)

        # Create sample input CSV
        self.sample_csv_content = """OurSKU,Price
ITEM001,10.99
ITEM002,20.50
"""
        with open(self.temp_input_dir / "TestSupplier_Pricelist.csv", "w") as f:
            f.write(self.sample_csv_content)

    def tearDown(self):
        for d in [self.temp_config_dir, self.temp_input_dir, self.temp_output_dir]:
            if d.exists():
                shutil.rmtree(d, ignore_errors=True)

        # Also remove the root 'output' and 'logs' directory if created by the application
        # These are default output locations if not overridden or if other parts of the code write there
        project_root_output_dir = project_root / "output"
        if project_root_output_dir.exists():
            shutil.rmtree(project_root_output_dir, ignore_errors=True)

        project_root_logs_dir = project_root / "logs"
        if project_root_logs_dir.exists():
            shutil.rmtree(project_root_logs_dir, ignore_errors=True)


    def test_intermediate_csv_creation(self):
        # Initialize PriceListConsolidator
        # The PriceListConsolidator's __init__ sets up logging based on config.
        # It expects self.config_manager.get_config() to work early.
        # To avoid issues with default log dir creation if tests run in restricted env,
        # ensure config is loaded with non-problematic log settings.

        # The ConfigManager will load default_config.yaml from temp_config_dir
        # The PriceListConsolidator will use this config for its operations.
        consolidator = PriceListConsolidator(config_dir=str(self.temp_config_dir), log_level="ERROR")

        # Call process_supplier_files
        # The output_path for the main Excel file is given to temp_output_dir.
        # Intermediate CSVs should also go into a sub-directory of temp_output_dir.
        master_excel_path = self.temp_output_dir / "MasterTest.xlsx"
        consolidator.process_supplier_files(
            input_directory=str(self.temp_input_dir),
            output_path=str(master_excel_path)
        )

        # Assertions
        # Supplier name extraction: "TestSupplier_Pricelist.csv" -> "Testsupplier" (because "Pricelist" is a removable word)
        # Sanitized name: "Testsupplier"
        expected_csv_filename = "Testsupplier_standardized.csv" # Corrected filename
        # The intermediate CSV is saved to "output/standardized_csvs" relative to project root by main.py
        expected_csv_path = project_root / "output" / "standardized_csvs" / expected_csv_filename

        self.assertTrue(expected_csv_path.exists(), f"Intermediate CSV file not found at {expected_csv_path}")

        # Read created CSV and compare
        created_df = pd.read_csv(expected_csv_path)

        # Expected DataFrame based on mappings
        # 'OurSKU' maps to 'SKU', 'Price' maps to 'Price'
        # The ColumnMapper also adds a 'supplier_name' column.
        expected_data = {
            'SKU': ['ITEM001', 'ITEM002'],
            'Price': [10.99, 20.50],
            'supplier_name': ['Testsupplier', 'Testsupplier'] # Added expected supplier_name
        }
        expected_df = pd.DataFrame(expected_data)

        # Ensure Price column is float if it exists in created_df, as it is in expected_df
        if 'Price' in created_df.columns:
            created_df['Price'] = created_df['Price'].astype(float)

        # Ensure the columns are in the same order for comparison
        # The intermediate CSV columns order might depend on how mapped_df is constructed.
        # Typically, it's good practice to sort columns before comparison if order isn't guaranteed.
        # However, let's first try with the assumed order [SKU, Price, supplier_name] or whatever pandas outputs.
        # If column order is an issue, we'll adjust.
        # For now, ensure expected_df has columns in a defined order.
        expected_df = expected_df[['SKU', 'Price', 'supplier_name']]


        pd.testing.assert_frame_equal(created_df, expected_df, check_dtype=True)

if __name__ == "__main__":
    unittest.main()
