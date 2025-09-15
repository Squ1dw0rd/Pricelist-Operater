"""
Enhanced Command Line Interface for Supplier Price List Consolidation Tool
Provides interactive configuration, dry-run mode, and advanced CLI features.
"""

import argparse
import sys
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
import yaml
import json
from datetime import datetime

from config_manager import ConfigManager
from logger import setup_logging, get_logger


class InteractiveCLI:
    """Interactive command line interface for configuration and operation."""
    
    def __init__(self):
        self.config_manager = None
        self.logger = None
    
    def run_interactive_mode(self, config_dir: str = "config"):
        """Run interactive configuration mode."""
        print("=== Supplier Price List Consolidation Tool ===")
        print("Interactive Configuration Mode\n")
        
        # Load existing configuration
        self.config_manager = ConfigManager(config_dir)
        config = self.config_manager.get_config()
        
        # Setup basic logging for interactive mode
        self.logger = get_logger()
        
        while True:
            print("\nMain Menu:")
            print("1. Configure supplier mappings")
            print("2. Configure validation rules")
            print("3. Configure output settings")
            print("4. Test configuration")
            print("5. Run consolidation")
            print("6. View logs")
            print("7. Exit")
            
            choice = input("\nSelect option (1-7): ").strip()
            
            if choice == "1":
                self._configure_supplier_mappings()
            elif choice == "2":
                self._configure_validation_rules()
            elif choice == "3":
                self._configure_output_settings()
            elif choice == "4":
                self._test_configuration()
            elif choice == "5":
                self._run_consolidation()
            elif choice == "6":
                self._view_logs()
            elif choice == "7":
                print("Goodbye!")
                break
            else:
                print("Invalid option. Please try again.")
    
    def _configure_supplier_mappings(self):
        """Interactive supplier mapping configuration."""
        print("\n=== Supplier Mapping Configuration ===")
        
        # List existing supplier configurations
        supplier_configs = self.config_manager.list_supplier_configs()
        
        if supplier_configs:
            print("\nExisting supplier configurations:")
            for i, supplier in enumerate(supplier_configs, 1):
                print(f"{i}. {supplier}")
            print(f"{len(supplier_configs) + 1}. Create new supplier configuration")
        else:
            print("No existing supplier configurations found.")
        
        print(f"{len(supplier_configs) + 2}. Back to main menu")
        
        try:
            choice = int(input("\nSelect option: ").strip())
            
            if choice <= len(supplier_configs):
                supplier_name = supplier_configs[choice - 1]
                self._edit_supplier_config(supplier_name)
            elif choice == len(supplier_configs) + 1:
                self._create_supplier_config()
            elif choice == len(supplier_configs) + 2:
                return
            else:
                print("Invalid option.")
        except ValueError:
            print("Please enter a valid number.")
    
    def _create_supplier_config(self):
        """Create new supplier configuration."""
        print("\n=== Create New Supplier Configuration ===")
        
        supplier_name = input("Enter supplier name: ").strip()
        if not supplier_name:
            print("Supplier name cannot be empty.")
            return
        
        # Create basic configuration template
        config_template = {
            'supplier_name': supplier_name,
            'column_mappings': {},
            'validation_overrides': {},
            'file_processing_overrides': {}
        }
        
        # Interactive column mapping
        print(f"\nConfiguring column mappings for {supplier_name}")
        print("Enter the column names from the supplier's files for each standard field.")
        print("Press Enter to skip a field.\n")
        
        standard_fields = ['sku', 'product_name', 'unit_price', 'supplier_name', 'description']
        
        for field in standard_fields:
            columns = []
            print(f"\n{field.replace('_', ' ').title()}:")
            
            while True:
                column = input(f"  Column name (or Enter to finish): ").strip()
                if not column:
                    break
                columns.append(column)
            
            if columns:
                config_template['column_mappings'][field] = columns
        
        # Save configuration
        try:
            self.config_manager.create_supplier_config(supplier_name, config_template)
            print(f"\nSupplier configuration for '{supplier_name}' created successfully!")
        except Exception as e:
            print(f"Error creating configuration: {e}")
    
    def _edit_supplier_config(self, supplier_name: str):
        """Edit existing supplier configuration."""
        print(f"\n=== Edit Configuration: {supplier_name} ===")
        
        try:
            config = self.config_manager.get_supplier_config(supplier_name)
            
            print("\nCurrent column mappings:")
            for field, columns in config.get('column_mappings', {}).items():
                print(f"  {field}: {columns}")
            
            print("\nOptions:")
            print("1. Add column mapping")
            print("2. Remove column mapping")
            print("3. View full configuration")
            print("4. Back to supplier menu")
            
            choice = input("\nSelect option: ").strip()
            
            if choice == "1":
                self._add_column_mapping(supplier_name, config)
            elif choice == "2":
                self._remove_column_mapping(supplier_name, config)
            elif choice == "3":
                print(f"\nFull configuration:\n{yaml.dump(config, default_flow_style=False)}")
            elif choice == "4":
                return
            
        except Exception as e:
            print(f"Error loading configuration: {e}")
    
    def _add_column_mapping(self, supplier_name: str, config: Dict[str, Any]):
        """Add column mapping to supplier configuration."""
        field = input("Enter standard field name: ").strip()
        column = input("Enter supplier column name: ").strip()
        
        if field and column:
            if 'column_mappings' not in config:
                config['column_mappings'] = {}
            if field not in config['column_mappings']:
                config['column_mappings'][field] = []
            
            config['column_mappings'][field].append(column)
            
            try:
                self.config_manager.save_supplier_config(supplier_name, config)
                print(f"Added mapping: {field} -> {column}")
            except Exception as e:
                print(f"Error saving configuration: {e}")
    
    def _remove_column_mapping(self, supplier_name: str, config: Dict[str, Any]):
        """Remove column mapping from supplier configuration."""
        mappings = config.get('column_mappings', {})
        
        if not mappings:
            print("No column mappings found.")
            return
        
        print("\nCurrent mappings:")
        all_mappings = []
        for field, columns in mappings.items():
            for column in columns:
                all_mappings.append((field, column))
                print(f"{len(all_mappings)}. {field} -> {column}")
        
        try:
            choice = int(input("\nSelect mapping to remove (number): ").strip())
            if 1 <= choice <= len(all_mappings):
                field, column = all_mappings[choice - 1]
                config['column_mappings'][field].remove(column)
                
                # Remove field if no columns left
                if not config['column_mappings'][field]:
                    del config['column_mappings'][field]
                
                self.config_manager.save_supplier_config(supplier_name, config)
                print(f"Removed mapping: {field} -> {column}")
            else:
                print("Invalid selection.")
        except (ValueError, Exception) as e:
            print(f"Error: {e}")
    
    def _configure_validation_rules(self):
        """Configure validation rules."""
        print("\n=== Validation Rules Configuration ===")
        
        config = self.config_manager.get_config()
        validation_rules = config.get('validation_rules', {})
        
        print("\nCurrent validation rules:")
        for rule, setting in validation_rules.items():
            if isinstance(setting, dict):
                print(f"  {rule}: {setting}")
            else:
                print(f"  {rule}: {setting}")
        
        print("\nOptions:")
        print("1. Toggle required field check")
        print("2. Configure price range check")
        print("3. Configure IQR outlier detection")
        print("4. Toggle duplicate SKU check")
        print("5. Back to main menu")
        
        choice = input("\nSelect option: ").strip()
        
        if choice == "1":
            current = validation_rules.get('required_field_check', True)
            validation_rules['required_field_check'] = not current
            print(f"Required field check: {'Enabled' if not current else 'Disabled'}")
        
        elif choice == "2":
            self._configure_price_range(validation_rules)
        
        elif choice == "3":
            self._configure_iqr_detection(validation_rules)
        
        elif choice == "4":
            current = validation_rules.get('duplicate_sku_check', True)
            validation_rules['duplicate_sku_check'] = not current
            print(f"Duplicate SKU check: {'Enabled' if not current else 'Disabled'}")
        
        elif choice == "5":
            return
        
        # Save updated configuration
        try:
            config['validation_rules'] = validation_rules
            self.config_manager.save_config(config)
            print("Configuration saved successfully!")
        except Exception as e:
            print(f"Error saving configuration: {e}")
    
    def _configure_price_range(self, validation_rules: Dict[str, Any]):
        """Configure price range validation."""
        price_range = validation_rules.get('price_range_check', {})
        
        print(f"\nCurrent price range: ${price_range.get('min_price', 0.01)} - ${price_range.get('max_price', 100000)}")
        
        try:
            min_price = float(input("Enter minimum price: ").strip())
            max_price = float(input("Enter maximum price: ").strip())
            
            if min_price >= max_price:
                print("Minimum price must be less than maximum price.")
                return
            
            validation_rules['price_range_check'] = {
                'enabled': True,
                'min_price': min_price,
                'max_price': max_price
            }
            
            print(f"Price range updated: ${min_price} - ${max_price}")
            
        except ValueError:
            print("Please enter valid numbers.")
    
    def _configure_iqr_detection(self, validation_rules: Dict[str, Any]):
        """Configure IQR outlier detection."""
        iqr_config = validation_rules.get('iqr_outlier_detection', {})
        
        print(f"\nCurrent IQR multiplier: {iqr_config.get('multiplier', 1.5)}")
        
        try:
            multiplier = float(input("Enter IQR multiplier (1.5 is standard): ").strip())
            
            if multiplier <= 0:
                print("Multiplier must be positive.")
                return
            
            validation_rules['iqr_outlier_detection'] = {
                'enabled': True,
                'multiplier': multiplier
            }
            
            print(f"IQR multiplier updated: {multiplier}")
            
        except ValueError:
            print("Please enter a valid number.")
    
    def _configure_output_settings(self):
        """Configure output settings."""
        print("\n=== Output Settings Configuration ===")
        
        config = self.config_manager.get_config()
        output_settings = config.get('output', {})
        
        print("\nCurrent output settings:")
        for setting, value in output_settings.items():
            print(f"  {setting}: {value}")
        
        print("\nOptions:")
        print("1. Change directory sheet name")
        print("2. Toggle processing metadata")
        print("3. Change hyperlink color")
        print("4. Back to main menu")
        
        choice = input("\nSelect option: ").strip()
        
        if choice == "1":
            name = input("Enter directory sheet name: ").strip()
            if name:
                output_settings['directory_sheet_name'] = name
                print(f"Directory sheet name updated: {name}")
        
        elif choice == "2":
            current = output_settings.get('include_processing_metadata', True)
            output_settings['include_processing_metadata'] = not current
            print(f"Processing metadata: {'Enabled' if not current else 'Disabled'}")
        
        elif choice == "3":
            color = input("Enter hyperlink color (hex code): ").strip()
            if color:
                output_settings['hyperlink_color'] = color
                print(f"Hyperlink color updated: {color}")
        
        elif choice == "4":
            return
        
        # Save updated configuration
        try:
            config['output'] = output_settings
            self.config_manager.save_config(config)
            print("Configuration saved successfully!")
        except Exception as e:
            print(f"Error saving configuration: {e}")
    
    def _test_configuration(self):
        """Test current configuration."""
        print("\n=== Configuration Test ===")
        
        try:
            config = self.config_manager.get_config()
            
            # Validate configuration
            errors = self.config_manager.validate_config(config)
            
            if errors:
                print("Configuration errors found:")
                for error in errors:
                    print(f"  - {error}")
            else:
                print("Configuration is valid!")
            
            # Show summary
            print(f"\nConfiguration Summary:")
            print(f"  Required fields: {len(config.get('master_schema', {}).get('required_fields', []))}")
            print(f"  Optional fields: {len(config.get('master_schema', {}).get('optional_fields', []))}")
            print(f"  Default mappings: {len(config.get('default_column_mappings', {}))}")
            print(f"  Validation rules: {len(config.get('validation_rules', {}))}")
            
            supplier_configs = self.config_manager.list_supplier_configs()
            print(f"  Supplier configurations: {len(supplier_configs)}")
            
        except Exception as e:
            print(f"Error testing configuration: {e}")
    
    def _run_consolidation(self):
        """Run consolidation from interactive mode."""
        print("\n=== Run Consolidation ===")
        
        input_dir = input("Enter input directory path: ").strip()
        if not input_dir or not os.path.exists(input_dir):
            print("Invalid input directory.")
            return
        
        output_file = input("Enter output file path: ").strip()
        if not output_file:
            print("Output file path cannot be empty.")
            return
        
        dry_run = input("Run in dry-run mode? (y/n): ").strip().lower() == 'y'
        
        print(f"\nStarting consolidation...")
        print(f"Input: {input_dir}")
        print(f"Output: {output_file}")
        print(f"Dry run: {dry_run}")
        
        # Import and run main consolidation
        try:
            from main import run_consolidation
            
            args = type('Args', (), {
                'input_directory': input_dir,
                'output': output_file,
                'config': 'config',
                'dry_run': dry_run,
                'verbose': True
            })()
            
            run_consolidation(args)
            
        except Exception as e:
            print(f"Error running consolidation: {e}")
    
    def _view_logs(self):
        """View recent logs."""
        print("\n=== View Logs ===")
        
        log_dir = Path("logs")
        if not log_dir.exists():
            print("No logs directory found.")
            return
        
        log_files = list(log_dir.glob("*.log"))
        if not log_files:
            print("No log files found.")
            return
        
        print("Available log files:")
        for i, log_file in enumerate(log_files, 1):
            print(f"{i}. {log_file.name}")
        
        try:
            choice = int(input("\nSelect log file to view: ").strip())
            if 1 <= choice <= len(log_files):
                log_file = log_files[choice - 1]
                
                # Show last 50 lines
                with open(log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    
                print(f"\nLast 50 lines of {log_file.name}:")
                print("-" * 80)
                for line in lines[-50:]:
                    print(line.rstrip())
                print("-" * 80)
            else:
                print("Invalid selection.")
        except (ValueError, Exception) as e:
            print(f"Error: {e}")


def create_enhanced_parser() -> argparse.ArgumentParser:
    """Create enhanced argument parser with all CLI options."""
    parser = argparse.ArgumentParser(
        description="Supplier Price List Consolidation Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic consolidation
  python main.py supplier_data -o output/master_list.xlsx
  
  # Interactive mode
  python main.py --interactive
  
  # Dry run mode
  python main.py supplier_data -o output/test.xlsx --dry-run
  
  # Single file processing
  python main.py --single-file data/supplier1.xlsx --supplier-name "Supplier 1"
  
  # Create supplier configuration
  python main.py --create-config "New Supplier"
  
  # Verbose output with debug logging
  python main.py supplier_data -o output/master.xlsx --verbose --log-level DEBUG
        """
    )
    
    # Main arguments
    parser.add_argument(
        'input_directory',
        nargs='?',
        help='Directory containing supplier files'
    )
    
    parser.add_argument(
        '-o', '--output',
        help='Output Excel file path'
    )
    
    # Configuration options
    parser.add_argument(
        '-c', '--config',
        default='config',
        help='Configuration directory (default: config)'
    )
    
    # Processing modes
    parser.add_argument(
        '--interactive',
        action='store_true',
        help='Run in interactive configuration mode'
    )
    
    parser.add_argument(
        '--web-ui',
        action='store_true',
        help='Launch web-based user interface'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run without generating output files'
    )
    
    parser.add_argument(
        '--single-file',
        help='Process a single file instead of directory'
    )
    
    parser.add_argument(
        '--supplier-name',
        help='Supplier name for single file processing'
    )
    
    # Configuration management
    parser.add_argument(
        '--create-config',
        metavar='SUPPLIER_NAME',
        help='Create configuration template for supplier'
    )
    
    parser.add_argument(
        '--validate-config',
        action='store_true',
        help='Validate configuration and exit'
    )
    
    parser.add_argument(
        '--list-configs',
        action='store_true',
        help='List available supplier configurations'
    )
    
    # Output options
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Suppress non-error output'
    )
    
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Set logging level'
    )
    
    parser.add_argument(
        '--no-progress',
        action='store_true',
        help='Disable progress bars'
    )
    
    # Advanced options
    parser.add_argument(
        '--max-errors',
        type=int,
        default=100,
        help='Maximum errors per file before stopping'
    )
    
    parser.add_argument(
        '--batch-size',
        type=int,
        default=1000,
        help='Batch size for processing large files'
    )
    
    parser.add_argument(
        '--memory-limit',
        type=int,
        default=2048,
        help='Memory limit in MB'
    )
    
    return parser


def validate_args(args) -> List[str]:
    """Validate command line arguments."""
    errors = []
    
    # Check for required arguments based on mode
    if not args.interactive and not args.create_config and not args.validate_config and not args.list_configs and not args.web_ui:
        if not args.input_directory:
            errors.append("Input directory is required when not in interactive mode")
        elif not os.path.exists(args.input_directory):
            errors.append(f"Input directory does not exist: {args.input_directory}")

        if not args.output and not args.dry_run:
            errors.append("Output file is required when not in dry-run mode")
    
    # Single file processing validation
    if args.single_file:
        if not os.path.exists(args.single_file):
            errors.append(f"Single file does not exist: {args.single_file}")
        if not args.supplier_name:
            errors.append("Supplier name is required for single file processing")
    
    # Conflicting options
    if args.verbose and args.quiet:
        errors.append("Cannot use both --verbose and --quiet options")
    
    return errors


def print_help_and_examples():
    """Print detailed help and examples."""
    print("""
Supplier Price List Consolidation Tool - Enhanced CLI

BASIC USAGE:
  python main.py <input_directory> -o <output_file>

MODES:
  Interactive Mode:     python main.py --interactive
  Dry Run Mode:         python main.py input_dir -o output.xlsx --dry-run
  Single File:          python main.py --single-file file.xlsx --supplier-name "Supplier"

CONFIGURATION:
  Create Config:        python main.py --create-config "Supplier Name"
  Validate Config:      python main.py --validate-config
  List Configs:         python main.py --list-configs

EXAMPLES:
  # Process all files in supplier_data directory
  python main.py supplier_data -o output/consolidated.xlsx
  
  # Interactive configuration and processing
  python main.py --interactive
  
  # Test configuration without generating output
  python main.py supplier_data -o test.xlsx --dry-run --verbose
  
  # Process single file with custom supplier name
  python main.py --single-file "data/new_supplier.xlsx" --supplier-name "New Supplier"
  
  # Create configuration for new supplier
  python main.py --create-config "ACME Tools"
  
  # Debug mode with detailed logging
  python main.py supplier_data -o output.xlsx --log-level DEBUG --verbose

For more information, use: python main.py --help
    """)
