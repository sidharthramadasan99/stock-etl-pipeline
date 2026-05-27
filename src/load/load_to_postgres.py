import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
import os
import logging
from dotenv import load_dotenv

load_dotenv()

# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    filename="logs/load.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)
logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────────
PROCESSED_DIR = "data/processed"

# ── Connect to PostgreSQL ─────────────────────────────────────────────────────
def get_connection():
    db_config = {
        "host":     os.getenv("DB_HOST",     "localhost"),
        "port":     os.getenv("DB_PORT",     "5432"),
        "dbname":   os.getenv("DB_NAME",     "stockdb"),
        "user":     os.getenv("DB_USER",     "postgres"),
        "password": os.getenv("DB_PASSWORD", "postgres123")
    }
    try:
        conn = psycopg2.connect(**db_config)
        logger.info("Database connection established")
        print("Connected to PostgreSQL", flush=True)
        return conn
    except Exception as e:
        logger.error(f"Connection failed: {e}")
        raise

# -- Load enriched_stocks --
def load_enriched_stocks(conn):
    filepath = os.path.join(PROCESSED_DIR, "enriched_stocks.parquet")
    df = pd.read_parquet(filepath)

    # Replace NaN with None so psycopg2 inserts NULL correctly
    df = df.where(pd.notnull(df), None)

    # Convert date to plain Python data object
    df["date"] = pd.to_datetime(df["date"]).dt.date

    rows = [
        (
            row["ticker"],
            row["date"],
            row["open"],
            row["high"],
            row["low"],
            row["close"],
            row["volume"],
            row["daily_return_pct"],
            row["ma_7"],
            row["ma_30"],
            row["daily_range"]
        )
        for _, row in df.iterrows()
    ]

    sql = """
        INSERT INTO enriched_stocks
            (ticker, date, open, high, low, close, volume, daily_return_pct, ma_7, ma_30, daily_range)
        VALUES %s
        ON CONFLICT (ticker, date) DO UPDATE SET
            close            = EXCLUDED.close,
            daily_return_pct = EXCLUDED.daily_return_pct,
            ma_7             = EXCLUDED.ma_7,
            ma_30            = EXCLUDED.ma_30,
            daily_range      = EXCLUDED.daily_range;
    """

    with conn.cursor() as cur:
        execute_values(cur, sql, rows, page_size=500)
    conn.commit()

    logger.info(f"Loaded {len(rows)} rows into enriched_stocks")
    print(f"Loaded {len(rows)} rows into enriched_stocks")

# -- Load ticker summary --
def load_ticker_summary(conn):
    filepath = os.path.join(PROCESSED_DIR, "ticker_summary.csv")
    df = pd.read_csv(filepath)

    df = df.where(pd.notnull(df), None)
    df["from_date"] = pd.to_datetime(df["from_date"]).dt.date
    df["to_date"] = pd.to_datetime(df["to_date"]).dt.date

    rows = [
        (
            row["ticker"],
            row["from_date"],
            row["to_date"],
            row["total_trading_days"],
            row["avg_close"],
            row["all_time_high"],
            row["all_time_low"],
            row["avg_daily_volume"],
            row["avg_daily_return_pct"]
        )
        for _, row in df.iterrows()
    ]

    sql = """
        INSERT INTO ticker_summary
            (ticker, from_date, to_date, total_trading_days, avg_close, all_time_high, all_time_low, avg_daily_volume, avg_daily_return_pct)
        VALUES %s
        ON CONFLICT (ticker) DO UPDATE SET
            to_date              = EXCLUDED.to_date ,
            total_trading_days   = EXCLUDED.total_trading_days ,
            avg_close            = EXCLUDED.avg_close ,
            all_time_high        = EXCLUDED.all_time_high ,
            all_time_low         = EXCLUDED.all_time_low ,
            avg_daily_volume     = EXCLUDED.avg_daily_volume ,
            avg_daily_return_pct = EXCLUDED.avg_daily_return_pct;
    """

    with conn.cursor() as cur:
        execute_values(cur, sql, rows)
    conn.commit()

    logger.info(f"Loaded {len(rows)} rows into ticker_summary")
    print(f"Loaded {len(rows)} rows into ticker_summary")

# -- Verify row counts --
def verify_load(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM enriched_stocks;")
        enriched_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM ticker_summary;")
        summary_count = cur.fetchone()[0]
    
    print(f"\nVerification:")
    print(f" enriched_stocks : {enriched_count} rows")
    print(f" ticker_summary  : {summary_count} rows")
    logger.info(f"Verification: enriched_stocks={enriched_count}, ticker_summary={summary_count}")

# -- Entry point --
if __name__ == "__main__":
    conn = get_connection()
    try:
        load_enriched_stocks(conn)
        load_ticker_summary(conn)
        verify_load(conn)
        print("\nLoad complete. Check logs/load.log for details.")
    finally:
        conn.close()
        print("Connection closed.")