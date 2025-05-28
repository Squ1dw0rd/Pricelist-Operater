# Quick Start Guide - Supplier Price List Consolidation Tool

## Prerequisites

1. **Python 3.11+** installed on your system
2. **VS Code** (already set up)
3. **Command prompt/terminal** access

## Setup Instructions

### 1. Install Dependencies

Open a command prompt in the project directory and run:

```bash
pip install -r requirements.txt
```

### 2. Verify Installation

Test that all dependencies are installed:

```bash
python tests/test_runner.py
```

This will run the test suite and check all dependencies.

## Running the Application

### Option 1: Basic Usage (Process All Files in supplier_data/)

```bash
python src/main.py supplier_data -o output/master_list.xlsx
```


- Process all files in the `supplier_data/` directory
- Generate a master Excel file in `output/`
- Create logs in `logs/`
- Generate a summary report

### Option 2: Interactive Mode (Recommended for First Time)

```bash
python src/main.py --interactive
```

This will:

- Guide you through the configuration
- Let you select files to process
- Show you all available options

### Option 3: Dry Run (Test Without Generating Output)

```bash
python src/main.py supplier_data --dry-run
```

This will:

- Process all files but not generate Excel output
- Show you what would be processed
- Validate your configuration

### Option 4: Single File Testing

```bash
python src/main.py --single-file "supplier_data/Narex 2025.csv"
```

### Option 5: Get Help

```bash
python src/main.py --help
```

## Expected Output

When you run the application, you should see:

1. **Console Output**: Progress bars, status messages, and results
2. **Excel File**: Generated in `output/Master_Price_List_YYYYMMDD_HHMMSS.xlsx`
3. **Log Files**: Detailed logs in `logs/` directory
4. **Summary Report**: Text file with processing statistics

## Quick Test Commands

### 1. Test Dependencies

```bash
python tests/test_runner.py
```

### 2. Test Configuration

```bash
python src/main.py --validate-config
```

### 3. Test Single File

```bash
python src/main.py --single-file "supplier_data/Narex 2025.csv" --supplier-name "Narex"
```

### 4. Test All Files (Dry Run)

```bash
python src/main.py supplier_data --dry-run --log-level DEBUG
```

### 5. Full Processing

```bash
python src/main.py supplier_data --output "output/my_test_output.xlsx"
```

## Troubleshooting

### If you get "Module not found" errors

```bash
# Make sure you're in the project directory
cd "c:/Users/Luke/Pricelist Operater"

# Install dependencies
pip install -r requirements.txt
```

### If you get permission errors

```bash
# Run as administrator or check file permissions
```

### If processing fails

```bash
# Check the logs in the logs/ directory
# Run with debug logging:
python src/main.py supplier_data --log-level DEBUG
```

## What to Look For

### ✅ Success Indicators

- Progress bars complete without errors
- Excel file generated in output/
- Summary shows processed products
- Log files created without critical errors

### ⚠️ Expected Warnings

- Column mapping warnings (normal for diverse file formats)
- Validation warnings for data quality issues
- PDF parsing issues (known limitation)

### ❌ Error Indicators

- Application crashes
- No output files generated
- Critical errors in logs
- Missing dependencies

## File Locations

- **Input Files**: `supplier_data/` (15 test files included)
- **Output Files**: `output/` (Excel files and reports)
- **Log Files**: `logs/` (detailed processing logs)
- **Configuration**: `config/` (YAML configuration files)

## Next Steps After Testing

1. **Review the generated Excel file** - Check the Directory sheet and individual supplier sheets
2. **Check the logs** - Look for any issues or warnings
3. **Review the summary report** - Understand what was processed
4. **Test with your own files** - Add files to `supplier_data/` and rerun
5. **Customize configuration** - Modify `config/default_config.yaml` as needed

## Getting Help

- Run `python src/main.py --help` for all command options
- Check `docs/README.md` for detailed documentation
- Review log files in `logs/` for troubleshooting
- Use `--interactive` mode for guided setup
