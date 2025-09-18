"""
Web UI for Supplier Price List Consolidation Tool
Provides a local web interface using FastAPI and Jinja2.
"""

import os
import tempfile
import shutil
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Form
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

from main import PriceListConsolidator
from cli import create_enhanced_parser
from logger import get_logger

# Create templates directory if it doesn't exist
templates_dir = Path(__file__).parent.parent / "templates"
templates_dir.mkdir(exist_ok=True)

# Create static directory for CSS/JS if needed
static_dir = Path(__file__).parent.parent / "static"
static_dir.mkdir(exist_ok=True)

app = FastAPI(title="Supplier Price List Consolidator", description="Local web interface for consolidating supplier price lists")

# Mount static files
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Setup Jinja2 templates
templates = Jinja2Templates(directory=str(templates_dir))

# Global consolidator instance
consolidator = None
logger = get_logger()

def get_consolidator(config_dir: str = "config") -> PriceListConsolidator:
    """Get or create consolidator instance."""
    global consolidator
    if consolidator is None:
        consolidator = PriceListConsolidator(config_dir)
    return consolidator

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page with file upload form."""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "title": "Supplier Price List Consolidator"
    })

@app.post("/upload")
async def upload_files(
    request: Request,
    files: List[UploadFile] = File(...),
    output_filename: str = Form("")
):
    """Handle file uploads and processing."""
    if not files:
        return templates.TemplateResponse("result.html", {
            "request": request,
            "success": False,
            "error": "No files uploaded."
        })

    # Create temp directory for uploaded files
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
        uploaded_paths = []

        # Save uploaded files
        for file in files:
            file_path = Path(temp_dir) / file.filename
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            uploaded_paths.append(str(file_path))

        try:
            # Get consolidator
            cons = get_consolidator()

            # Set default output filename if not provided
            if not output_filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_filename = f"Master_Price_List_{timestamp}.xlsx"

            # Ensure output directory exists
            output_dir = Path("output")
            output_dir.mkdir(exist_ok=True)
            output_path = output_dir / output_filename

            # Process files
            logger.info(f"Processing {len(uploaded_paths)} uploaded files")
            try:
                excel_path = cons.process_supplier_files(temp_dir, str(output_path))

                return templates.TemplateResponse("result.html", {
                    "request": request,
                    "success": True,
                    "filename": output_filename,
                    "processed_files": len(uploaded_paths),
                    "total_records": cons.performance_stats['total_records']
                })
            except Exception as e:
                logger.error(f"Processing failed: {e}")
                return templates.TemplateResponse("result.html", {
                    "request": request,
                    "success": False,
                    "error": str(e)
                })

        except Exception as e:
            logger.error(f"Upload processing error: {e}")
            return templates.TemplateResponse("result.html", {
                "request": request,
                "success": False,
                "error": f"Processing error: {str(e)}"
            })

@app.get("/download/{filename}")
async def download_file(filename: str):
    """Download the generated Excel file."""
    # Find the file in output directory
    output_dir = Path("output")
    file_path = output_dir / filename

    if file_path.exists():
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    else:
        raise HTTPException(status_code=404, detail="File not found")

@app.get("/config")
async def config_page(request: Request):
    """Configuration management page."""
    cons = get_consolidator()
    suppliers = cons.config_manager.list_supplier_configs()

    return templates.TemplateResponse("config.html", {
        "request": request,
        "suppliers": suppliers
    })

@app.post("/config/create")
async def create_config(request: Request):
    """Create new supplier configuration."""
    # Temporarily disabled due to Form dependency
    return templates.TemplateResponse("config_result.html", {
        "request": request,
        "success": False,
        "error": "Configuration creation temporarily disabled."
    })

@app.get("/status")
async def status_page(request: Request):
    """System status and logs page."""
    cons = get_consolidator()

    # Get recent logs (simplified)
    log_files = list(Path("logs").glob("*.log")) if Path("logs").exists() else []

    return templates.TemplateResponse("status.html", {
        "request": request,
        "performance_stats": cons.performance_stats,
        "log_files": [f.name for f in log_files[-5:]]  # Last 5 logs
    })

def create_templates():
    """Create basic HTML templates if they don't exist."""

    # Index template
    index_html = """
<!DOCTYPE html>
<html>
<head>
    <title>{{ title }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .upload-form { border: 1px solid #ccc; padding: 20px; border-radius: 5px; }
        .form-group { margin: 10px 0; }
        label { display: block; margin-bottom: 5px; }
        input[type="file"] { margin: 10px 0; }
        button { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; }
        button:hover { background: #0056b3; }
    </style>
</head>
<body>
    <h1>{{ title }}</h1>
    <p>Upload supplier price list files (.csv, .xls, .xlsx, .pdf) for consolidation.</p>

    <div class="upload-form">
        <form action="/upload" method="post" enctype="multipart/form-data">
            <div class="form-group">
                <label for="files">Select Files:</label>
                <input type="file" id="files" name="files" multiple required>
            </div>
            <div class="form-group">
                <label for="output_filename">Output Filename (optional):</label>
                <input type="text" id="output_filename" name="output_filename" placeholder="Master_Price_List.xlsx">
            </div>
            <button type="submit">Process Files</button>
        </form>
    </div>

    <div style="margin-top: 20px;">
        <a href="/config">Manage Configurations</a> |
        <a href="/status">View Status</a>
    </div>
</body>
</html>
"""

    # Result template
    result_html = """
<!DOCTYPE html>
<html>
<head>
    <title>Processing Result</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .success { color: green; }
        .error { color: red; }
        .result-box { border: 1px solid #ccc; padding: 20px; border-radius: 5px; margin: 20px 0; }
    </style>
</head>
<body>
    <h1>Processing Result</h1>

    {% if success %}
    <div class="result-box success">
        <h2>Success!</h2>
        <p>Processed {{ processed_files }} files with {{ total_records }} total records.</p>
        <p><a href="/download/{{ filename }}" target="_blank">Download {{ filename }}</a></p>
    </div>
    {% else %}
    <div class="result-box error">
        <h2>Error</h2>
        <p>{{ error }}</p>
    </div>
    {% endif %}

    <p><a href="/">Back to Upload</a></p>
</body>
</html>
"""

    # Config template
    config_html = """
<!DOCTYPE html>
<html>
<head>
    <title>Configuration Management</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .supplier-list { margin: 20px 0; }
        .supplier-item { border: 1px solid #ccc; padding: 10px; margin: 5px 0; border-radius: 3px; }
    </style>
</head>
<body>
    <h1>Configuration Management</h1>

    <h2>Existing Suppliers</h2>
    <div class="supplier-list">
        {% for supplier in suppliers %}
        <div class="supplier-item">{{ supplier }}</div>
        {% endfor %}
    </div>

    <h2>Create New Supplier Config</h2>
    <form action="/config/create" method="post">
        <div style="margin: 10px 0;">
            <label for="supplier_name">Supplier Name:</label><br>
            <input type="text" id="supplier_name" name="supplier_name" required>
        </div>
        <button type="submit">Create Configuration</button>
    </form>

    <p><a href="/">Back to Home</a></p>
</body>
</html>
"""

    # Config result template
    config_result_html = """
<!DOCTYPE html>
<html>
<head>
    <title>Configuration Result</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .success { color: green; }
        .error { color: red; }
    </style>
</head>
<body>
    <h1>Configuration Result</h1>

    {% if success %}
    <div class="success">
        <h2>Success!</h2>
        <p>{{ message }}</p>
        <p>Supplier: {{ supplier_name }}</p>
    </div>
    {% else %}
    <div class="error">
        <h2>Error</h2>
        <p>{{ error }}</p>
    </div>
    {% endif %}

    <p><a href="/config">Back to Configuration</a></p>
</body>
</html>
"""

    # Status template
    status_html = """
<!DOCTYPE html>
<html>
<head>
    <title>System Status</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .stats { border: 1px solid #ccc; padding: 20px; border-radius: 5px; margin: 20px 0; }
        .stat-item { margin: 5px 0; }
    </style>
</head>
<body>
    <h1>System Status</h1>

    <div class="stats">
        <h2>Performance Statistics</h2>
        <div class="stat-item">Files Processed: {{ performance_stats.files_processed }}</div>
        <div class="stat-item">Total Records: {{ performance_stats.total_records }}</div>
        <div class="stat-item">Processing Time: {{ "%.2f"|format(performance_stats.processing_time) }}s</div>
        <div class="stat-item">Errors: {{ performance_stats.errors }}</div>
        <div class="stat-item">Warnings: {{ performance_stats.warnings }}</div>
    </div>

    <h2>Recent Logs</h2>
    <ul>
        {% for log in log_files %}
        <li>{{ log }}</li>
        {% endfor %}
    </ul>

    <p><a href="/">Back to Home</a></p>
</body>
</html>
"""

    # Write templates
    (templates_dir / "index.html").write_text(index_html)
    (templates_dir / "result.html").write_text(result_html)
    (templates_dir / "config.html").write_text(config_html)
    (templates_dir / "config_result.html").write_text(config_result_html)
    (templates_dir / "status.html").write_text(status_html)

def run_web_ui(host: str = "127.0.0.1", port: int = 8000, config_dir: str = "config"):
    """Run the web UI server."""
    # Create templates if they don't exist
    create_templates()

    # Initialize consolidator
    get_consolidator(config_dir)

    logger.info(f"Starting web UI on http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    run_web_ui()