import subprocess
import os
from pathlib import Path
from dagster import op, graph, ScheduleDefinition, Definitions, RetryPolicy

# Paths to your existing scripts
BASE_DIR = Path(__file__).resolve().parent
SCRAPER_PATH = BASE_DIR / "scripts/telegram.py"
LOADER_PATH = BASE_DIR / "scripts/load_raw_to_pg.py"
DBT_PROJECT_DIR = BASE_DIR / "medical_warehouse"
YOLO_SCRIPT_PATH = BASE_DIR / "src/yolo_detection.py"

# Standard Retry Policy for production stability
standard_retry = RetryPolicy(max_retries=3, delay=60) # 3 retries, 1 min apart

@op(
    description="Step 1: Scrape medical messages and images from Telegram.",
    retry_policy=standard_retry
)
def scrape_telegram_data():
    """Executes the Telegram scraper script."""
    result = subprocess.run(["python", str(SCRAPER_PATH)], check=True, capture_output=True)
    return "Scraping complete"

@op(
    description="Step 2: Load raw JSON/CSV data into the 'raw' schema in Postgres.",
    retry_policy=standard_retry
)
def load_raw_to_postgres(upstream_status: str):
    """Executes the script that populates raw.fct_messages."""
    subprocess.run(["python", str(LOADER_PATH)], check=True)
    return "Loading complete"

@op(
    description="Step 3: Run dbt models to transform raw data into the Gold layer.",
    retry_policy=standard_retry
)
def run_dbt_transformations(upstream_status: str):
    """Executes dbt run to build analytical marts (fct_messages, dim_channels)."""
    # Note: Ensure dbt is in your path or virtualenv
    subprocess.run(["dbt", "run", "--project-dir", str(DBT_PROJECT_DIR)], check=True)
    return "Transformations complete"

@op(
    description="Step 4: Run YOLOv8 object detection on images and store results.",
    retry_policy=standard_retry
)
def run_yolo_enrichment(upstream_status: str):
    """Enriches data by detecting medical objects in images."""
    subprocess.run(["python", str(YOLO_SCRIPT_PATH)], check=True)
    return "YOLO enrichment complete"

@graph
def medical_warehouse_pipeline():
    """Full Pipeline: Scrape → Load → dbt → YOLO."""
    # We pass the status string to ensure sequential execution
    scraped = scrape_telegram_data()
    loaded = load_raw_to_postgres(scraped)
    transformed = run_dbt_transformations(loaded)
    run_yolo_enrichment(transformed)

# Create the job from the graph
medical_job = medical_warehouse_pipeline.to_job(name="medical_warehouse_job")

# Schedule it to run daily at 2 AM
daily_medical_schedule = ScheduleDefinition(
    job=medical_job,
    cron_schedule="0 2 * * *", # Daily at 02:00
)

# Register everything in the Dagster instance
defs = Definitions(
    jobs=[medical_job],
    schedules=[daily_medical_schedule],
)