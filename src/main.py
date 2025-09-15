"""
Enhanced Main Application for Supplier Price List Consolidation Tool
Integrates enhanced logging, CLI, error handling, and testing capabilities.
"""

import argparse
import os
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from tqdm import tqdm
import time
import sys

def safe_print(message):
    """Safely print message handling Unicode encoding issues."""
    try:
        print(message)
    except UnicodeEncodeError:
        # Fallback for non-UTF8 consoles
        ascii_msg = message.encode('ascii', 'replace').decode('ascii')
        print(ascii_msg)

# Import our modules
from config_manager import ConfigManager
from file_parsers import parse_file, FileParserFactory
from column_mapper import create_column_mapper
from data_validator import validate_data, create_validation_report
from excel_generator import generate_master_excel
from logger import setup_logging, ContextualLogger, get_logger
from cli import InteractiveCLI, create_enhanced_parser, validate_args, print_help_and_examples


class PriceListConsolidator:
    """Enhanced main application class for consolidating supplier price lists."""
    
    def __init__(self, config_dir: str = "config", log_level: str = "INFO"):
        # 1. Initialize ConfigManager first.
        # It does not take a logger in its own __init__, but uses global logging.
        # We will set its instance logger later.
        self.config_manager = ConfigManager(config_dir)

        # 2. Get the base configuration from ConfigManager.
        self.config = self.config_manager.get_config()
        
        # Handle cases where default_config.yaml might be missing or malformed.
        if not self.config:
            # Fallback to a very basic config for logging if everything else fails
            self.config = {'logging': {'level': 'ERROR', 'format': '%(asctime)s - %(levelname)s - %(message)s'}}
            # Use standard logging to output a critical error if config is missing
            import logging # Ensure logging is imported if not already at module level for this fallback
            logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')
            logging.error("CRITICAL: Default configuration (default_config.yaml) failed to load or is empty. " +
                          "PriceListConsolidator will use a minimal fallback configuration for logging. " +
                          "Please ensure 'default_config.yaml' is present and correct in the config directory.")
            # Depending on desired robustness, might raise an error here.
            # For now, we'll let setup_logging use this minimal config.

        # 3. Override log level from the log_level parameter.
        # Ensure 'logging' key exists in self.config, initialize if not.
        if 'logging' not in self.config:
            self.config['logging'] = {} # Should not happen if default_config.yaml is present
        self.config['logging']['level'] = log_level.upper() # Ensure level is uppercase

        # 4. Setup the application's logging system using the (potentially modified) config.
        self.logger_system = setup_logging(self.config)
        self.logger = self.logger_system.get_logger()

        # 5. Assign the created application logger to the ConfigManager instance.
        # This allows ConfigManager's internal methods (like get_supplier_config)
        # to use the application-configured logger via 'self.config_manager.logger'.
        self.config_manager.logger = self.logger
        
        # Now ConfigManager can use its self.logger for its own logging needs.
        # Example: self.config_manager._load_supplier_configs() might use self.config_manager.logger internally.
        # If ConfigManager's methods were called before this point and tried to use self.logger,
        # they would have failed or used a different logger.

        # Log session start (can now use the fully configured logger)
        self.logger_system.log_session_start(self.config)
        
        # Validate overall configuration (ConfigManager can use its assigned logger for this)
        # Ensure validate_config is called after config_manager.logger is set, if it uses the logger.
        config_errors = self.config_manager.validate_config()
        if config_errors:
            for error in config_errors:
                self.logger.error(f"Configuration error: {error}")
            # The original code raised a ValueError here.
            raise ValueError(f"Invalid configuration. Errors: {'; '.join(config_errors)}")
        
        self.logger.info("Price List Consolidator initialized successfully.")
        
        self.performance_stats = {
            'files_processed': 0,
            'total_records': 0,
            'processing_time': 0.0,
            'errors': 0,
            'warnings': 0
        }
    
    def process_supplier_files(self, input_directory: str, output_path: str = None, 
                             dry_run: bool = False) -> str:
        """
        Process all supplier files in a directory with enhanced error handling.
        
        Args:
            input_directory: Directory containing supplier files
            output_path: Optional output path for the Excel file
            dry_run: If True, process files but don't generate output
        
        Returns:
            Path to the generated Excel file (or None if dry_run)
        """
        start_time = time.time()
        
        with ContextualLogger(self.logger, f"Processing directory: {input_directory}"):
            input_dir = Path(input_directory)
            if not input_dir.exists():
                raise FileNotFoundError(f"Input directory not found: {input_directory}")
            
            # Find all supported files
            supported_formats = FileParserFactory.get_supported_formats()
            supplier_files = []
            
            for format_ext in supported_formats:
                supplier_files.extend(input_dir.glob(f"*{format_ext}"))
            
            if not supplier_files:
                raise ValueError(f"No supported files found in {input_directory}")
            
            self.logger.info(f"Found {len(supplier_files)} supplier files to process")
            
            # Process each file with enhanced error handling
            supplier_data = {}
            validation_reports = {}
            processing_errors = []
            
            error_handling_config = self.config.get('error_handling', {})
            max_errors_per_file = error_handling_config.get('max_errors_per_file', 100)
            continue_on_error = error_handling_config.get('continue_on_file_error', True)
            
            progress_bar = tqdm(supplier_files, desc="Processing files", 
                              disable=self.config.get('ui', {}).get('progress_bars', True) == False)
            
            for file_path in progress_bar:
                try:
                    supplier_name = self._extract_supplier_name(file_path)
                    progress_bar.set_description(f"Processing {supplier_name}")
                    
                    # Log file processing start
                    file_size = file_path.stat().st_size
                    self.logger_system.log_file_processing_start(str(file_path), file_size)
                    
                    # Process single file with error handling
                    result = self._process_single_file_safe(file_path, supplier_name, max_errors_per_file)
                    
                    if result['success']:
                        supplier_data[supplier_name] = result['mapped_data']
                        validation_reports[supplier_name] = result['validation_result']
                        
                        # Log successful processing
                        errors = result['validation_result'].get_summary()['error_count']
                        warnings = result['validation_result'].get_summary()['warning_count']
                        
                        self.logger_system.log_file_processing_end(
                            str(file_path), len(result['mapped_data']), errors, warnings
                        )
                        
                        # Update performance stats
                        self.performance_stats['files_processed'] += 1
                        self.performance_stats['total_records'] += len(result['mapped_data'])
                        self.performance_stats['errors'] += errors
                        self.performance_stats['warnings'] += warnings
                        
                    else:
                        processing_errors.append({
                            'file': str(file_path),
                            'supplier': supplier_name,
                            'error': result['error']
                        })
                        
                        self.logger_system.log_file_processing_end(str(file_path), 0, 1, 0)
                        self.performance_stats['errors'] += 1
                        
                        if not continue_on_error:
                            raise Exception(f"Processing stopped due to error in {file_path.name}: {result['error']}")
                
                except Exception as e:
                    error_msg = f"Critical error processing {file_path.name}: {e}"
                    self.logger.error(error_msg)
                    processing_errors.append({
                        'file': str(file_path),
                        'supplier': supplier_name if 'supplier_name' in locals() else 'Unknown',
                        'error': str(e)
                    })
                    
                    if not continue_on_error:
                        raise
            
            progress_bar.close()
            
            # Check if any files were successfully processed
            if not supplier_data:
                error_summary = "\n".join([f"  - {err['file']}: {err['error']}" for err in processing_errors])
                raise ValueError(f"No files were successfully processed. Errors:\n{error_summary}")
            
            # Log processing summary
            processing_time = time.time() - start_time
            self.performance_stats['processing_time'] = processing_time
            
            self.logger.info(f"Processing completed: {len(supplier_data)} suppliers, "
                           f"{self.performance_stats['total_records']} total records, "
                           f"{processing_time:.2f}s")
            
            # Log memory usage
            self.logger_system.log_memory_usage("file processing")
            
            if dry_run:
                self.logger.info("DRY RUN MODE: Skipping Excel generation")
                self._log_dry_run_summary(supplier_data, validation_reports, processing_errors)
                return None
            
            # Generate output path if not provided
            if output_path is None:
                output_dir = Path("output")
                output_dir.mkdir(exist_ok=True)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_path = output_dir / f"Master_Price_List_{timestamp}.xlsx"
            
            # Generate Excel output with performance tracking
            with ContextualLogger(self.logger, "Excel generation"):
                excel_path = generate_master_excel(supplier_data, str(output_path), 
                                                 self.config, validation_reports)
            
            # Generate enhanced summary report
            self._generate_enhanced_summary_report(supplier_data, validation_reports, 
                                                 processing_errors, excel_path)
            
            self.logger.info(f"Consolidation completed successfully. Output: {excel_path}")
            
            # Log session end
            self.logger_system.log_session_end()
            
            return excel_path
    
    def _process_single_file_safe(self, file_path: Path, supplier_name: str, 
                                max_errors: int) -> Dict[str, Any]:
        """
        Safely process a single file with comprehensive error handling.
        
        Args:
            file_path: Path to the supplier file
            supplier_name: Name of the supplier
            max_errors: Maximum errors allowed before stopping
        
        Returns:
            Dictionary with processing results
        """
        try:
            with ContextualLogger(self.logger, f"Processing {supplier_name}", logging.DEBUG):
                # Parse file
                raw_df = parse_file(str(file_path), self.config, supplier_name)
                self.logger.debug(f"Parsed {len(raw_df)} rows from {file_path.name}")
                
                if raw_df.empty:
                    return {
                        'success': False,
                        'error': 'File contains no data or could not be parsed'
                    }
                
                # Map columns
                # Get supplier-specific configuration
                try:
                    supplier_specific_config = self.config_manager.get_supplier_config(supplier_name)
                except Exception as config_err:
                    self.logger.warning(f"Could not load supplier config for {supplier_name}: {config_err}, using default config")
                    supplier_specific_config = self.config
                
                mapper = create_column_mapper(supplier_specific_config, supplier_name, self.config_manager, self.logger)
                mapped_df, mapping_report = mapper.map_columns(raw_df.columns.tolist())
                
                # Log mapping results
                self.logger_system.log_column_mapping(
                    supplier_name, 
                    mapping_report['mapped_fields'],
                    mapping_report['unmapped_columns']
                )

                # Check configuration and save intermediate CSV
                save_csv_flag = self.config.get('output_options', {}).get('save_intermediate_standardized_csvs', False)
                if save_csv_flag and not mapped_df.empty: # Also ensure mapped_df is not empty
                    try:
                        csv_output_dir = Path("output") / "standardized_csvs"
                        csv_output_dir.mkdir(parents=True, exist_ok=True)

                        # Sanitize supplier_name for filename
                        safe_supplier_name = "".join(c if c.isalnum() or c in ['_', '-'] else '_' for c in supplier_name)
                        # Replace multiple underscores with one, and remove leading/trailing
                        safe_supplier_name = '_'.join(filter(None, safe_supplier_name.split('_')))

                        csv_filename = f"{safe_supplier_name}_standardized.csv"
                        full_csv_path = csv_output_dir / csv_filename

                        mapped_df.to_csv(full_csv_path, index=False, encoding='utf-8')
                        self.logger.info(f"Saved standardized data for {supplier_name} to {full_csv_path}")
                    except Exception as e_csv:
                        self.logger.error(f"Failed to save intermediate CSV for {supplier_name}: {e_csv}")
                
                # Check for missing required fields
                if mapping_report['missing_required_fields']:
                    missing_fields = ', '.join(mapping_report['missing_required_fields'])
                    return {
                        'success': False,
                        'error': f'Missing required fields: {missing_fields}'
                    }
                
                # Validate data
                validation_result = validate_data(mapped_df, self.config, supplier_name)
                
                # Log validation results
                self.logger_system.log_validation_summary(supplier_name, validation_result)
                
                # Check if errors exceed threshold
                if validation_result.get_summary()['error_count'] > max_errors:
                    return {
                        'success': False,
                        'error': f'Too many validation errors: {validation_result.get_summary()["error_count"]} > {max_errors}'
                    }
                
                return {
                    'supplier_name': supplier_name,
                    'raw_data': raw_df,
                    'mapped_data': mapped_df,
                    'mapping_report': mapping_report,
                    'validation_result': validation_result,
                    'success': True
                }
        
        except Exception as e:
            self.logger.error(f"Error processing {file_path.name}: {e}")
            return {
                'supplier_name': supplier_name,
                'error': str(e),
                'success': False
            }
    
    def _extract_supplier_name(self, file_path: Path) -> str:
        """Extract supplier name from file path with enhanced logic."""
        # Remove file extension and clean up the name
        name = file_path.stem
        
        # Remove common prefixes/suffixes and years
        words_to_remove = {
            'price', 'list', 'pricelist', 'pricesheet', 'catalog', 'catalogue',
            '2024', '2025', '2026', 'updated', 'new', 'latest', 'current'
        }
        
        # Split and clean
        name_parts = []
        for part in name.replace('_', ' ').replace('-', ' ').split():
            clean_part = ''.join(c for c in part if c.isalnum())
            if clean_part.lower() not in words_to_remove and len(clean_part) > 1:
                # Skip pure numbers unless they're part codes
                if not (clean_part.isdigit() and len(clean_part) == 4):
                    name_parts.append(clean_part.title())
        
        if name_parts:
            return ' '.join(name_parts)
        else:
            # Fallback to original filename
            return file_path.stem.replace('_', ' ').title()
    
    def _log_dry_run_summary(self, supplier_data: Dict, validation_reports: Dict, 
                           processing_errors: List[Dict]):
        """Log summary for dry run mode."""
        self.logger.info("=== DRY RUN SUMMARY ===")
        self.logger.info(f"Successfully processed: {len(supplier_data)} suppliers")
        self.logger.info(f"Processing errors: {len(processing_errors)}")
        
        total_records = sum(len(df) for df in supplier_data.values())
        total_errors = sum(report.get_summary()['error_count'] for report in validation_reports.values())
        total_warnings = sum(report.get_summary()['warning_count'] for report in validation_reports.values())
        
        self.logger.info(f"Total records: {total_records}")
        self.logger.info(f"Total validation errors: {total_errors}")
        self.logger.info(f"Total validation warnings: {total_warnings}")
        
        if processing_errors:
            self.logger.warning("Files with processing errors:")
            for error in processing_errors:
                self.logger.warning(f"  - {error['file']}: {error['error']}")
    
    def _generate_enhanced_summary_report(self, supplier_data: Dict, validation_reports: Dict,
                                        processing_errors: List[Dict], excel_path: str):
        """Generate enhanced summary report with detailed statistics."""
        report_lines = []
        report_lines.append("SUPPLIER PRICE LIST CONSOLIDATION SUMMARY")
        report_lines.append("=" * 50)
        report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"Output File: {excel_path}")
        report_lines.append("")
        
        # Performance statistics
        report_lines.append("PERFORMANCE STATISTICS:")
        report_lines.append(f"  Processing Time: {self.performance_stats['processing_time']:.2f} seconds")
        if self.performance_stats['total_records'] > 0:
            rate = self.performance_stats['total_records'] / self.performance_stats['processing_time']
            report_lines.append(f"  Processing Rate: {rate:.1f} records/second")
        report_lines.append("")
        
        # Overall statistics
        total_suppliers = len(supplier_data)
        total_products = sum(len(df) for df in supplier_data.values())
        total_errors = sum(report.get_summary()['error_count'] for report in validation_reports.values())
        total_warnings = sum(report.get_summary()['warning_count'] for report in validation_reports.values())
        
        report_lines.append(f"Total Suppliers: {total_suppliers}")
        report_lines.append(f"Total Products: {total_products}")
        report_lines.append(f"Total Validation Errors: {total_errors}")
        report_lines.append(f"Total Validation Warnings: {total_warnings}")
        report_lines.append("")
        
        # Processing errors
        if processing_errors:
            report_lines.append("PROCESSING ERRORS:")
            for error in processing_errors:
                report_lines.append(f"  {error['supplier']}: {error['error']}")
            report_lines.append("")
        
        # Per-supplier summary
        report_lines.append("SUPPLIER DETAILS:")
        for supplier_name, df in supplier_data.items():
            validation_summary = validation_reports[supplier_name].get_summary()
            report_lines.append(f"  {supplier_name}:")
            report_lines.append(f"    Products: {len(df)}")
            report_lines.append(f"    Errors: {validation_summary['error_count']}")
            report_lines.append(f"    Warnings: {validation_summary['warning_count']}")
            report_lines.append("")
        
        # Save summary report
        summary_path = Path(excel_path).parent / "consolidation_summary.txt"
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_lines))
        
        self.logger.info(f"Summary report saved to: {summary_path}")
    
    def create_supplier_config(self, supplier_name: str) -> str:
        """Create a configuration template for a new supplier."""
        return self.config_manager.create_supplier_config_template(supplier_name)


def run_consolidation(args):
    """Run the consolidation process with the given arguments."""
    try:
        # Initialize consolidator with enhanced logging
        log_level = getattr(args, 'log_level', 'INFO')
        consolidator = PriceListConsolidator(args.config, log_level)
        
        # Process files
        if hasattr(args, 'single_file') and args.single_file:
            # Single file processing
            result = consolidator._process_single_file_safe(
                Path(args.single_file),
                args.supplier_name or "Unknown Supplier",
                100
            )
            
            if result['success']:
                safe_print(f"✅ Successfully processed {result['supplier_name']}")
                safe_print(f"   Records: {len(result['mapped_data'])}")
                validation_summary = result['validation_result'].get_summary()
                safe_print(f"   Validation: {validation_summary['error_count']} errors, {validation_summary['warning_count']} warnings")
            else:
                safe_print(f"❌ Error processing file: {result['error']}")
                return 1
        else:
            # Directory processing
            dry_run = getattr(args, 'dry_run', False)
            output_path = consolidator.process_supplier_files(
                args.input_directory,
                getattr(args, 'output', None),
                dry_run
            )
            
            if not dry_run:
                safe_print(f"✅ Consolidation completed successfully!")
                safe_print(f"📄 Output file: {output_path}")
            else:
                safe_print(f"✅ Dry run completed successfully!")
            
        return 0
        
    except Exception as e:
        safe_print(f"❌ Error: {e}")
        return 1


def main():
    """Enhanced main entry point with full CLI support."""
    # Create enhanced argument parser
    parser = create_enhanced_parser()
    
    # Parse arguments
    args = parser.parse_args()
    
    # Handle special cases
    if len(sys.argv) == 1:
        print_help_and_examples()
        return 0
    
    # Validate arguments
    validation_errors = validate_args(args)
    if validation_errors:
        safe_print("❌ Argument validation errors:")
        for error in validation_errors:
            safe_print(f"   - {error}")
        return 1
    
    # Handle interactive mode
    if getattr(args, 'interactive', False):
        cli = InteractiveCLI()
        cli.run_interactive_mode(args.config)
        return 0
    
    # Handle configuration operations
    if getattr(args, 'create_config', None):
        try:
            consolidator = PriceListConsolidator(args.config)
            config_path = consolidator.create_supplier_config(args.create_config)
            print(f"✅ Created supplier configuration template: {config_path}")
            return 0
        except Exception as e:
            safe_print(f"❌ Error creating configuration: {e}")
            return 1
    
    if getattr(args, 'validate_config', False):
        try:
            config_manager = ConfigManager(args.config)
            config = config_manager.get_config()
            errors = config_manager.validate_config(config)
            
            if errors:
                print("❌ Configuration validation errors:")
                for error in errors:
                    print(f"   - {error}")
                return 1
            else:
                print("✅ Configuration is valid!")
                return 0
        except Exception as e:
            safe_print(f"❌ Error validating configuration: {e}")
            return 1
    
    if getattr(args, 'list_configs', False):
        try:
            config_manager = ConfigManager(args.config)
            suppliers = config_manager.list_supplier_configs()
            
            if suppliers:
                print("📋 Available supplier configurations:")
                for supplier in suppliers:
                    print(f"   - {supplier}")
            else:
                print("📋 No supplier configurations found.")
            return 0
        except Exception as e:
            safe_print(f"❌ Error listing configurations: {e}")
            return 1
    if getattr(args, 'web_ui', False):
        try:
            from web_ui import run_web_ui
            run_web_ui(host="127.0.0.1", port=8000, config_dir=args.config)
            return 0
        except Exception as e:
            safe_print(f"❌ Error starting web UI: {e}")
            return 1
    
    # Run main consolidation
    return run_consolidation(args)


if __name__ == "__main__":
    sys.exit(main())
