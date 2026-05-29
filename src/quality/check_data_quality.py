import pandas as pd
import psycopg2
import os
import logging
from dotenv import load_dotenv
from datetime import datetime, timedelta 

load_dotenv()

# -- Logging setup --
logging.basicConfig(
    filename="logs/quality.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)
logger = logging.getLogger(__name__)

# -- Database connection --
def get_connection():
    return psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432"),
            dbname=os.getenv("DB_NAME", "stockdb"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", "postgres123")
    )

# -- Individual checks -- 
def check_row_counts(cur, results):
    """Ensure both tables have data."""
    cur.execute("SELECT COUNT(*) FROM enriched_stocks;")
    enriched_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM ticker_summary;")
    summary_count = cur.fetchone()[0]

    passed = enriched_count > 0 and summary_count == 5
    results.append({
        "check": "Row Count",
        "passed": passed,
        "detail": f"enriched_stocks={enriched_count}, ticker_summary={summary_count}"
    })

def check_null_critical_columns(cur, results):
    """No nulls allowed in ticker, date, or close."""
    cur.execute("""
                SELECT COUNT(*) FROM enriched_stocks
                WHERE ticker IS NULL OR date IS NULL OR close IS NULL;
                """)
    null_count = cur.fetchone()[0]

    passed = null_count == 0
    results.append({
        "check": "Null Critical Columns",
        "passed": passed,
        "detail": f"{null_count} rows with nulls in ticker/date/close"
    })

def check_duplicate_rows(cur, results):
    """No duplicate (ticker, date) combinations"""
    cur.execute("""
                SELECT COUNT(*) FROM (
                    SELECT ticker, date, COUNT(*)
                    FROM enriched_stocks
                    GROUP BY ticker, date
                    HAVING COUNT(*) > 1
                ) duplicates;
                """)
    dup_count = cur.fetchone()[0]

    passed = dup_count == 0
    results.append({
        "check": "Dulicate Rows",
        "passed": passed,
        "detail": f"{dup_count} duplicate (ticker, date) pairs found"
    })


def check_price_sanity(cur, results):
    """Close price must be positive. No negative or zero prices."""
    cur.execute("""
                SELECT COUNT(*) FROM enriched_stocks
                WHERE close <= 0;
                """)
    bad_price_count = cur.fetchone()[0]

    passed = bad_price_count == 0
    results.append({
        "check": "Price Sanity",
        "passed": passed,
        "detail": f"{bad_price_count} rows with close price <= 0"
    })


def check_all_tickers_present(cur, results):
    """All 5 expected tickers must be present."""
    expected_tickers = {
        "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "WIPRO.NS"
    }

    cur.execute("SELECT DISTINCT ticker FROM enriched_stocks;")
    actual_tickers = {row[0] for row in cur.fetchall()}

    missing = expected_tickers - actual_tickers
    passed = len(missing) == 0
    results.append({
        "check": "All Tickers Present",
        "passed": passed,
        "detail": f"Missing tickers: {missing}" if missing else "All 5 tickers present"
    })


def check_data_range(cur, results):
    """Data must start from 2023 and be recent (within last 7 days)."""
    cur.execute("SELECT MIN(date), MAX(date) FROM enriched_stocks;")
    min_date, max_date = cur.fetchone()

    expected_min = datetime(2023, 1, 1).date()
    expected_max = datetime.today().date() - timedelta(days=7)

    passed = min_date <= expected_min or max_date >= expected_max
    results.append({
        "check": "Date Range",
        "passed": passed,
        "detail": f"Date from {min_date} to {max_date}"
    })



def check_moving_averages_populated(cur, results):
    """MA columns should not be all null - most rows should have values."""
    cur.execute("""
                SELECT
                    COUNT(*) AS total,
                    COUNT(ma_7) AS ma7_populated,
                    COUNT(ma_30) AS ma30_populated
                FROM enriched_stocks;
                """)
    total, ma7, ma30 = cur.fetchone()

    ma7_pct = round(ma7 / total * 100, 1)
    ma30_pct = round(ma30 / total * 100, 1)

    passed = ma7_pct > 90 and ma30_pct > 90
    results.append({
        "check": "Moving Averages Populated",
        "passed": passed,
        "detail": f"ma_7={ma7_pct}% populated, ma_30={ma30_pct}% populated"
    })


# -- Print results --
def print_results(results):
    print(f"\n{'='*60}")
    print(f"  DATA QUALITY REPORT - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")

    passed_count = sum(1 for r in results if r["passed"])
    total_count = len(results)

    for r in results:
        status = "PASS" if r["passed"] else "FAIL"
        icon = "✓" if r["passed"] else "✗"
        print(f"  {icon} [{status}] {r['check']:<30} {r['detail']}")
        logger.info(f"{status} | {r['check']} | {r['detail']}")
    
    print(f"{'='*60}")
    print(f"  Result: {passed_count}/{total_count} checks passed")
    print(f"{'='*60}\n")

    if passed_count < total_count:
        logger.warning(f"Data quality issues found: {total_count - passed_count} checks failed")
    else:
        logger.info("All data quality checks passed")

# --Entry point--
if __name__ == "__main__":
    conn = get_connection()
    cur = conn.cursor()
    results = []


    check_row_counts(cur, results)
    check_null_critical_columns(cur, results)
    check_duplicate_rows(cur, results)
    check_price_sanity(cur, results)
    check_all_tickers_present(cur, results)
    check_data_range(cur, results)
    check_moving_averages_populated(cur, results)

    print_results(results)

    cur.close()
    conn.close()