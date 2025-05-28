# Supplier Price List Consolidation Tool

A Python application that automates the consolidation of supplier price lists from various file formats (.xls, .xlsx, .csv, .pdf) into a single, standardized master price list Excel file.

## Features

- **Multi-format Support**: Processes CSV, XLS, XLSX, and PDF files
- **Intelligent Column Mapping**: Uses fuzzy matching to map diverse column names to standardized schema
- **Data Validation**: Comprehensive validation with outlier detection using IQR method
- **Excel Output**: Generates multi-sheet workbook with directory navigation and hyperlinks
- **Configurable**: Flexible configuration system for supplier-specific mappings
- **Robust Error Handling**: Detailed logging and error reporting
- **Local Processing**: Runs entirely offline on local machine

## Quick Start

### Prerequisites

- Python 3.11 or higher
- Windows 10/11 (tested environment)

### Installation

1. Clone or download the project to your local machine
2. Open a command prompt in the project directory
3. Create and activate a virtual environment:
   ```cmd
   python -m venv venv
   venv\Scripts\activate
   ```
4. Install dependencies:
   ```cmd
   pip install -r requirements.txt
   ```

### Basic Usage

1. Place your supplier files in the `supplier_data` directory
2. Run the consolidation:
   ```cmd
   python src/main.py supplier_data -o output/master_price_list.xlsx
   ```
3. Find your consolidated Excel file in the `output` directory

## File Structure

```
Pricelist Operater/
├── src/                    # Source code
│   ├── main.py            # Main application entry point
│   ├── config_manager.py  # Configuration management
│   ├── file_parsers.py    # File parsing for different formats
│   ├── column_mapper.py   # Column mapping engine
│   ├── data_validator.py  # Data validation engine
│   └── excel_generator.py # Excel output generation
├── config/                # Configuration files
│   ├── default_config.yaml # Default configuration
│   └── suppliers/         # Supplier-specific configurations
├── supplier_data/         # Input supplier files
├── output/               # Generated output files
├── logs/                 # Application logs
├── tests/                # Unit tests
└── docs/                 # Documentation
```

## Configuration

### Default Configuration

The application uses `config/default_config.yaml` for default settings including:

- **Master Schema**: Defines required and optional fields
- **Column Mappings**: Default mappings for common column names
- **Validation Rules**: Data validation settings
- **Output Settings**: Excel formatting and styling options

### Supplier-Specific Configuration

Create supplier-specific configurations in `config/suppliers/` to override defaults:

```cmd
python src/main.py --create-config "Supplier Name"
```

This creates a template configuration file that you can customize for specific suppliers.

## Command Line Options

```cmd
python src/main.py [OPTIONS] INPUT_DIRECTORY

Arguments:
  INPUT_DIRECTORY    Directory containing supplier files

Options:
  -o, --output PATH           Output Excel file path
  -c, --config PATH          Configuration directory (default: config)
  --create-config NAME       Create configuration template for supplier
  --single-file PATH         Process a single file instead of directory
  --supplier-name NAME       Supplier name for single file processing
  -h, --help                 Show help message
```

## Examples

### Process All Files in Directory
```cmd
python src/main.py supplier_data -o output/consolidated_prices.xlsx
```

### Process Single File
```cmd
python src/main.py --single-file "supplier_data/supplier1.xlsx" --supplier-name "Supplier 1"
```

### Create Supplier Configuration
```cmd
python src/main.py --create-config "New Supplier"
```

## Output Format

The generated Excel file contains:

1. **Directory Sheet**: Overview with links to all supplier sheets
   - Supplier names and product counts
   - Validation status (OK/WARNINGS/ERRORS)
   - Hyperlinks to individual supplier sheets

2. **Individual Supplier Sheets**: One sheet per supplier
   - Standardized column headers
   - Formatted data with currency formatting for prices
   - Validation flags highlighting problematic rows
   - Back-to-directory navigation links

3. **Processing Metadata**: Timestamps and processing statistics

## Data Validation

The application performs comprehensive validation:

- **Required Field Validation**: Ensures critical fields are present
- **Data Type Validation**: Validates numeric fields
- **Price Range Validation**: Configurable min/max price limits
- **Outlier Detection**: Uses IQR method to identify price anomalies
- **Duplicate Detection**: Identifies duplicate SKUs
- **Data Completeness**: Reports on missing data

## Column Mapping

The intelligent column mapping system:

- Uses fuzzy string matching to map columns
- Supports exact matches and partial matches
- Provides confidence scores for mappings
- Handles common variations in column names
- Allows supplier-specific overrides

### Common Column Mappings

| Standard Field | Common Variations |
|---------------|-------------------|
| sku | "SKU", "Product Code", "Part Number", "Item Code" |
| product_name | "Product Name", "Description", "Item Description" |
| unit_price | "Unit Price", "List Price", "Price", "Cost" |
| supplier_name | "Supplier", "Vendor", "Manufacturer" |

## Troubleshooting

### Common Issues

1. **Missing Required Fields**: Check column names in your files and update mappings
2. **File Format Issues**: Ensure files are in supported formats (CSV, XLS, XLSX, PDF)
3. **Encoding Problems**: The application auto-detects encoding but may need manual configuration
4. **Large Files**: Processing may be slow for very large files; consider splitting them

### Logs

Check `logs/consolidator.log` for detailed processing information and error messages.

### Configuration Validation

The application validates configuration on startup and reports any issues.

## Advanced Configuration

### Custom Column Mappings

Edit supplier configuration files to add custom mappings:

```yaml
column_mappings:
  sku:
    - "custom_sku_column"
    - "item_id"
  unit_price:
    - "price_column"
    - "cost_per_unit"
```

### Validation Rules

Customize validation rules per supplier:

```yaml
validation_rules:
  price_range_check:
    enabled: true
    min_price: 1.00
    max_price: 50000.00
  iqr_outlier_detection:
    enabled: true
    multiplier: 1.5
```

## Performance

- **Medium-powered PC**: Tested on 4-core CPU, 16GB RAM
- **Processing Speed**: ~2-3 files per second (varies by file size)
- **Memory Usage**: Efficient processing of large datasets
- **File Size Limits**: Configurable maximum file size (default: 100MB)

## Support

For issues or questions:

1. Check the logs in `logs/consolidator.log`
2. Review configuration files for errors
3. Ensure all dependencies are installed correctly
4. Verify file formats are supported

## License

This project is developed for internal use. All rights reserved.
