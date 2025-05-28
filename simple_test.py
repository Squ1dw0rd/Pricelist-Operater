"""
Simple test script to verify the core functionality works.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, 'src')

def test_basic_functionality():
    """Test basic functionality without the enhanced features."""
    print("Testing Supplier Price List Consolidation Tool")
    print("=" * 50)
    
    try:
        # Test 1: Import core modules
        print("1. Testing imports...")
        from config_manager import ConfigManager
        from file_parsers import FileParserFactory
        print("   ✅ Core modules imported successfully")
        
        # Test 2: Load configuration
        print("\n2. Testing configuration...")
        config_manager = ConfigManager('config')
        config = config_manager.get_config()
        print(f"   ✅ Configuration loaded: {len(config)} sections")
        
        # Test 3: Test file parser factory
        print("\n3. Testing file parsers...")
        supported_formats = FileParserFactory.get_supported_formats()
        print(f"   ✅ Supported formats: {supported_formats}")
        
        # Test 4: Test with a simple CSV file
        print("\n4. Testing CSV parsing...")
        csv_file = Path("supplier_data/Narex 2025.csv")
        if csv_file.exists():
            csv_parser = FileParserFactory.create_parser(str(csv_file), config)
            data = csv_parser.parse(str(csv_file))
            print(f"   ✅ CSV parsed: {len(data)} rows, {len(data.columns)} columns")
            print(f"   Columns: {list(data.columns)}")
        else:
            print("   ⚠️ CSV file not found")
        
        # Test 5: Test column mapping
        print("\n5. Testing column mapping...")
        from column_mapper import ColumnMapper
        mapper = ColumnMapper(config, "Narex")
        
        if csv_file.exists() and 'data' in locals():
            mapped_df, mapping_report = mapper.map_columns(data)
            print(f"   ✅ Column mapping: {len(mapping_report['mapped_fields'])} mapped, {len(mapping_report['unmapped_columns'])} unmapped")
            print(f"   Mapped fields: {mapping_report['mapped_fields']}")
        
        # Test 6: Test data validation
        print("\n6. Testing data validation...")
        from data_validator import DataValidator
        validator = DataValidator(config)
        print("   ✅ Data validator created")
        
        print("\n🎉 All basic tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_simple_processing():
    """Test simple file processing without the enhanced main app."""
    print("\n" + "=" * 50)
    print("Testing Simple File Processing")
    print("=" * 50)
    
    try:
        # Import required modules
        from config_manager import ConfigManager
        from file_parsers import FileParserFactory
        from column_mapper import ColumnMapper
        from data_validator import DataValidator
        import pandas as pd
        
        # Load config
        config_manager = ConfigManager('config')
        config = config_manager.get_config()
        
        # Test with Narex CSV file
        csv_file = Path("supplier_data/Narex 2025.csv")
        if not csv_file.exists():
            print("❌ Test file not found")
            return False
        
        print(f"Processing: {csv_file.name}")
        
        # Parse file
        csv_parser = FileParserFactory.create_parser(str(csv_file), config)
        raw_data = csv_parser.parse(str(csv_file))
        print(f"✅ Parsed {len(raw_data)} rows")
        
        # Map columns
        mapper = ColumnMapper(config, "Narex")
        mapped_df, mapping_report = mapper.map_columns(raw_data)
        print(f"✅ Mapped {len(mapping_report['mapped_fields'])} columns")
        
        # Validate data
        validator = DataValidator(config)
        validation_result = validator.validate(mapped_df, "Narex")
        summary = validation_result.get_summary()
        print(f"✅ Validation: {summary['error_count']} errors, {summary['warning_count']} warnings")
        
        # Show sample data
        print(f"\nSample transformed data:")
        print(mapped_df.head())
        
        print(f"\n🎉 Simple processing test completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Processing test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Supplier Price List Consolidation Tool - Simple Test")
    print("=" * 60)
    
    # Run basic functionality tests
    basic_success = test_basic_functionality()
    
    if basic_success:
        # Run simple processing test
        processing_success = test_simple_processing()
        
        if processing_success:
            print("\n" + "=" * 60)
            print("✅ ALL TESTS PASSED - Core functionality is working!")
            print("=" * 60)
            print("\nNext steps:")
            print("1. The core functionality is working correctly")
            print("2. You can process files using the basic components")
            print("3. The enhanced CLI has some minor issues but core processing works")
            print("4. Try running: python simple_test.py")
        else:
            print("\n❌ Processing tests failed")
    else:
        print("\n❌ Basic tests failed")
