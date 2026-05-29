import subprocess
import sys
import time
import logging
from datetime import datetime

# -- Logging setup --
logging.basicConfig(
    filename="logs/pipeline.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)
logger = logging.getLogger(__name__)

# -- Pipeline stages --
STAGES = [
    {
        "name":        "Ingestion",
        "script":      "src/ingestion/ingest_stocks.py",
        "description": "Fetching stock data from Yahoo Finance"
    },
    {
        "name":        "Transformation",
        "script":      "src/transform/transform_stocks.py",
        "description": "Cleaning data and engineering features"
    },
    {
        "name":        "Load",
        "script":      "src/load/load_to_postgres.py",
        "description": "Loading transformed data into PostgreSQL"
    },
    {
        "name":        "Quality Checks",
        "script":      "src/quality/check_data_quality.py",
        "description": "Validating data integrity in PostgreSQL"
    }
]

# -- Run a single stage --
def run_stage(stage):
    print(f"\n{'='*60}")
    print(f"  STAGE: {stage['name']}")
    print(f"  {stage['description']}")
    print(f"{'='*60}")

    start_time = time.time()
    logger.info(f"Starting stage: {stage['name']}")

    result = subprocess.run(
        [sys.executable, stage['script']],
        capture_output=False
    )

    elapsed = round(time.time() - start_time, 2)

    if result.returncode == 0:
        logger.info(f"Stage {stage['name']} completed in {elapsed}s")
        print(f"\n  ✓ {stage['name']} completed in {elapsed}s")
        return True
    else:
        logger.error(f"Stage {stage['name']} failed after {elapsed}s")
        print(f"\n  ✗ {stage['name']} FAILED after {elapsed}s")
        return False

# -- Run the full pipeline --
def run_pipeline():
    print(f"\n{'#'*60}")
    print(f"  STOCK ETL PIPELINE")
    print(f"  Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#'*60}")

    logger.info("Pipeline started")
    pipeline_start = time.time()

    results = {}

    for stage in STAGES:
        success = run_stage(stage)
        results[stage['name']] = success
        
        if not success:
            print(f"\n  Pipeline halted at stage: {stage['name']}")
            print(f"  Fix the error above and rerun pipeline.py")
            logger.error(f"Pipeline halted at stage: {stage['name']}")
            sys.exit(1)
        
        total_time = round(time.time() - pipeline_start, 2)

        print(f"\n{'#'*60}")
        print(f"  PIPELINE COMPLETE")
        print(f" Total time: {total_time}s")
        print(f" Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"\n Summary:")
        for stage_name, success in results.items():
            status = "SUCCESS" if success else "FAILED"
            print(f"    {stage_name:<20} {status}")
        print(f"{'#'*60}\n")

        logger.info(f"Pipeline completed successfully in {total_time}s")


# --Entry point--
if __name__ == "__main__":
    run_pipeline()