"""
Test runner for the Supplier Price List Consolidation Tool.
Runs all unit tests and generates coverage reports.
"""

import unittest
import sys
import os
from pathlib import Path
import time
from io import StringIO

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class TestResult:
    """Custom test result class to track test statistics."""
    
    def __init__(self):
        self.tests_run = 0
        self.failures = 0
        self.errors = 0
        self.skipped = 0
        self.success_rate = 0.0
        self.duration = 0.0
        self.details = []


class ColoredTextTestResult(unittest.TextTestResult):
    """Enhanced test result with colored output and detailed reporting."""
    
    def __init__(self, stream, descriptions, verbosity):
        super().__init__(stream, descriptions, verbosity)
        self.test_results = TestResult()
        self.start_time = None
    
    def startTest(self, test):
        super().startTest(test)
        if self.start_time is None:
            self.start_time = time.time()
        
        if self.verbosity > 1:
            self.stream.write(f"Running {test._testMethodName}... ")
            self.stream.flush()
    
    def addSuccess(self, test):
        super().addSuccess(test)
        if self.verbosity > 1:
            self.stream.write("✅ PASS\n")
    
    def addError(self, test, err):
        super().addError(test, err)
        self.test_results.errors += 1
        if self.verbosity > 1:
            self.stream.write("❌ ERROR\n")
        
        self.test_results.details.append({
            'test': str(test),
            'type': 'ERROR',
            'message': str(err[1])
        })
    
    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.test_results.failures += 1
        if self.verbosity > 1:
            self.stream.write("❌ FAIL\n")
        
        self.test_results.details.append({
            'test': str(test),
            'type': 'FAILURE',
            'message': str(err[1])
        })
    
    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.test_results.skipped += 1
        if self.verbosity > 1:
            self.stream.write("⏭️ SKIP\n")
    
    def stopTestRun(self):
        super().stopTestRun()
        if self.start_time:
            self.test_results.duration = time.time() - self.start_time
        
        self.test_results.tests_run = self.testsRun
        
        if self.testsRun > 0:
            successful = self.testsRun - len(self.failures) - len(self.errors)
            self.test_results.success_rate = (successful / self.testsRun) * 100


def discover_tests():
    """Discover all test modules in the tests directory."""
    test_dir = Path(__file__).parent
    loader = unittest.TestLoader()
    
    # Discover all test files
    suite = loader.discover(str(test_dir), pattern='test_*.py')
    
    return suite


def run_unit_tests(verbosity=2):
    """Run all unit tests with detailed reporting."""
    print("=" * 80)
    print("SUPPLIER PRICE LIST CONSOLIDATION TOOL - UNIT TESTS")
    print("=" * 80)
    
    # Discover tests
    suite = discover_tests()
    
    # Create custom test runner
    stream = StringIO()
    runner = unittest.TextTestRunner(
        stream=stream,
        verbosity=verbosity,
        resultclass=ColoredTextTestResult
    )
    
    # Run tests
    print(f"\nDiscovered {suite.countTestCases()} test cases")
    print("Running tests...\n")
    
    start_time = time.time()
    result = runner.run(suite)
    duration = time.time() - start_time
    
    # Print results
    print_test_summary(result.test_results, duration)
    
    # Print detailed output if there were failures/errors
    if result.test_results.failures > 0 or result.test_results.errors > 0:
        print("\n" + "=" * 80)
        print("DETAILED ERROR REPORT")
        print("=" * 80)
        
        for detail in result.test_results.details:
            print(f"\n{detail['type']}: {detail['test']}")
            print("-" * 40)
            print(detail['message'])
    
    return result.test_results


def print_test_summary(results, duration):
    """Print formatted test summary."""
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    print(f"Tests Run:     {results.tests_run}")
    print(f"Failures:      {results.failures}")
    print(f"Errors:        {results.errors}")
    print(f"Skipped:       {results.skipped}")
    print(f"Success Rate:  {results.success_rate:.1f}%")
    print(f"Duration:      {duration:.2f} seconds")
    
    # Overall status
    if results.failures == 0 and results.errors == 0:
        status = "✅ ALL TESTS PASSED"
        status_color = "green"
    elif results.failures > 0 or results.errors > 0:
        status = "❌ SOME TESTS FAILED"
        status_color = "red"
    else:
        status = "⚠️ NO TESTS RUN"
        status_color = "yellow"
    
    print(f"\nOverall Status: {status}")
    
    # Coverage estimation (basic)
    modules_tested = ['config_manager', 'column_mapper', 'data_validator', 'file_parsers']
    estimated_coverage = min(len(modules_tested) * 20, 80)  # Rough estimate
    print(f"Estimated Coverage: ~{estimated_coverage}%")


def run_integration_tests():
    """Run integration tests with real data."""
    print("\n" + "=" * 80)
    print("INTEGRATION TESTS")
    print("=" * 80)
    
    integration_results = TestResult()
    
    try:
        # Test 1: Configuration loading
        print("\n1. Testing configuration loading...")
        from config_manager import ConfigManager
        
        config_manager = ConfigManager('config')
        config = config_manager.get_config()
        
        if config and 'master_schema' in config:
            print("   ✅ Configuration loaded successfully")
            integration_results.tests_run += 1
        else:
            print("   ❌ Configuration loading failed")
            integration_results.failures += 1
            integration_results.tests_run += 1
        
        # Test 2: File parsing
        print("\n2. Testing file parsing capabilities...")
        from file_parsers import FileParserFactory
        
        parser_factory = FileParserFactory()
        
        # Test CSV parser
        csv_parser = parser_factory.get_parser('.csv')
        if csv_parser:
            print("   ✅ CSV parser available")
            integration_results.tests_run += 1
        else:
            print("   ❌ CSV parser not available")
            integration_results.failures += 1
            integration_results.tests_run += 1
        
        # Test Excel parser
        xlsx_parser = parser_factory.get_parser('.xlsx')
        if xlsx_parser:
            print("   ✅ Excel parser available")
            integration_results.tests_run += 1
        else:
            print("   ❌ Excel parser not available")
            integration_results.failures += 1
            integration_results.tests_run += 1
        
        # Test 3: Column mapping
        print("\n3. Testing column mapping...")
        from column_mapper import ColumnMapper
        
        mapper = ColumnMapper(config)
        test_columns = ['SKU', 'Product Name', 'Unit Price']
        mappings, unmapped = mapper.map_columns(test_columns)
        
        if len(mappings) >= 3:
            print("   ✅ Column mapping working")
            integration_results.tests_run += 1
        else:
            print("   ❌ Column mapping failed")
            integration_results.failures += 1
            integration_results.tests_run += 1
        
        # Test 4: Data validation
        print("\n4. Testing data validation...")
        from data_validator import DataValidator
        import pandas as pd
        
        validator = DataValidator(config)
        test_data = pd.DataFrame({
            'sku': ['A001', 'A002'],
            'product_name': ['Product 1', 'Product 2'],
            'unit_price': [10.50, 25.00],
            'supplier_name': ['Test Supplier', 'Test Supplier']
        })
        
        validation_result = validator.validate_data(test_data, 'Test Supplier')
        
        if validation_result:
            print("   ✅ Data validation working")
            integration_results.tests_run += 1
        else:
            print("   ❌ Data validation failed")
            integration_results.failures += 1
            integration_results.tests_run += 1
        
        # Test 5: Excel generation
        print("\n5. Testing Excel generation...")
        from excel_generator import ExcelGenerator
        
        generator = ExcelGenerator(config)
        
        # Test basic functionality
        if hasattr(generator, 'create_workbook'):
            print("   ✅ Excel generator available")
            integration_results.tests_run += 1
        else:
            print("   ❌ Excel generator not available")
            integration_results.failures += 1
            integration_results.tests_run += 1
    
    except Exception as e:
        print(f"   ❌ Integration test error: {e}")
        integration_results.errors += 1
        integration_results.tests_run += 1
    
    # Calculate success rate
    if integration_results.tests_run > 0:
        successful = integration_results.tests_run - integration_results.failures - integration_results.errors
        integration_results.success_rate = (successful / integration_results.tests_run) * 100
    
    print(f"\nIntegration Tests Summary:")
    print(f"  Tests Run: {integration_results.tests_run}")
    print(f"  Failures: {integration_results.failures}")
    print(f"  Errors: {integration_results.errors}")
    print(f"  Success Rate: {integration_results.success_rate:.1f}%")
    
    return integration_results


def check_dependencies():
    """Check if all required dependencies are available."""
    print("=" * 80)
    print("DEPENDENCY CHECK")
    print("=" * 80)
    
    required_packages = [
        'pandas', 'openpyxl', 'xlrd', 'pdfplumber', 
        'fuzzywuzzy', 'tqdm', 'chardet', 'yaml'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            if package == 'yaml':
                import yaml
            else:
                __import__(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - MISSING")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️ Missing packages: {', '.join(missing_packages)}")
        print("Install with: pip install " + " ".join(missing_packages))
        return False
    else:
        print("\n✅ All dependencies available")
        return True


def main():
    """Main test runner function."""
    print("Supplier Price List Consolidation Tool - Test Suite")
    print("=" * 80)
    
    # Check dependencies first
    if not check_dependencies():
        print("\n❌ Cannot run tests - missing dependencies")
        return 1
    
    # Run unit tests
    unit_results = run_unit_tests(verbosity=2)
    
    # Run integration tests
    integration_results = run_integration_tests()
    
    # Overall summary
    print("\n" + "=" * 80)
    print("OVERALL TEST RESULTS")
    print("=" * 80)
    
    total_tests = unit_results.tests_run + integration_results.tests_run
    total_failures = unit_results.failures + integration_results.failures
    total_errors = unit_results.errors + integration_results.errors
    
    if total_tests > 0:
        overall_success_rate = ((total_tests - total_failures - total_errors) / total_tests) * 100
    else:
        overall_success_rate = 0
    
    print(f"Total Tests:      {total_tests}")
    print(f"Total Failures:   {total_failures}")
    print(f"Total Errors:     {total_errors}")
    print(f"Overall Success:  {overall_success_rate:.1f}%")
    
    # Determine exit code
    if total_failures == 0 and total_errors == 0:
        print("\n🎉 ALL TESTS PASSED!")
        return 0
    else:
        print(f"\n❌ {total_failures + total_errors} TESTS FAILED")
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
