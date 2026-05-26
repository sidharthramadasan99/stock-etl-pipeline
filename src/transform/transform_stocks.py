import pandas as pd
import os
import logging
from dotenv import load_dotenv

load_dotenv()

# -- Logging setup --
logging.basicConfig(
    filename="logs/transform.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)
logger = logging.getLogger(__name__)

# -- Configuration --
RAW_DIR       = "data/raw"
PROCESSED_DIR = "data/processed"

# -- Load all raw CSVs into a single DataFrame --
def load_raw_data(raw_dir):
    all_files = [
        os.path.join(raw_dir, f)
        for f in os.listdir(raw_dir)
        if f.endswith(".csv")
    ]

    if not all_files:
        raise FileNotFoundError(f"No CSV files found in {raw_dir}")

    df = pd.concat([pd.read_csv(f) for f in all_files], ignore_index=True)
    logger.info(f"Loaded {len(df)} rows from {len(all_files)} files")
    print(f"Loaded {len(df)} rows from {len(all_files)} files")
    return df

# -- Clean the data --
def clean_data(df):
    # Parse date column
    df["date"] = pd.to_datetime(df["date"])

    # Drop rows with nulls in critical columns
    before = len(df)
    df = df.dropna(subset=["date", "close", "ticker"])
    after = len(df)
    logger.info(f"Dropped {before - after} null rows. {after} rows remain.")

    # Round float columns
    for col in ["open", "high", "low", "close"]:
        df[col] = df[col].round(2)

    # Ensure volume is integer
    df["volume"] = df["volume"].astype("int64")

    # Sort by ticker and date — critical for window calculations
    df = df.sort_values(["ticker", "date"]).reset_index(drop=True)

    print(f"After cleaning: {len(df)} rows")
    return df

# -- Feature engineering --
def add_features(df):
    # Group by ticker so calculations don't bleed across stocks
    groups = []

    for ticker, group in df.groupby("ticker"):
        group = group.copy()

        # Daily return %
        group["daily_return_pct"] = (
            (group["close"] - group["close"].shift(1)) /
            group["close"].shift(1) * 100
        ).round(4)

        # 7-day moving average
        group["ma_7"] = group["close"].rolling(window=7).mean().round(2)

        # 30-day moving average
        group["ma_30"] = group["close"].rolling(window=30).mean().round(2)

        # Daily price range
        group["daily_range"] = (group["high"] - group["low"]).round(2)

        groups.append(group)

    df = pd.concat(groups, ignore_index=True)
    logger.info("Feature engineering complete: daily_return_pct, ma_7, ma_30, daily_range added")
    print("Feature engineering complete")
    return df

# -- Aggregate summary per ticker --
def create_summary(df):
    summary = df.groupby("ticker").agg(
        from_date=("date", "min"),
        to_date=("date", "max"),
        total_trading_days=("date", "count"),
        avg_close=("close", lambda x: round(x.mean(), 2)),
        all_time_high=("close", "max"),
        all_time_low=("close", "min"),
        avg_daily_volume=("volume", lambda x: round(x.mean(), 0)),
        avg_daily_return_pct=("daily_return_pct", lambda x: round(x.mean(), 4))
    ).reset_index()

    logger.info("Ticker summary created")
    return summary

# -- Save outputs --
def save_outputs(df, summary, output_dir):
    os.makedirs(output_dir, exist_ok=True)

    # Save enriched data as parquet (industry standard columnar format)
    enriched_path = os.path.join(output_dir, "enriched_stocks.parquet")
    df.to_parquet(enriched_path, index=False)
    logger.info(f"Enriched data saved to {enriched_path}")
    print(f"Enriched parquet saved to {enriched_path}")

    # Save summary as CSV for PostgreSQL loading
    summary_path = os.path.join(output_dir, "ticker_summary.csv")
    summary.to_csv(summary_path, index=False)
    logger.info(f"Summary saved to {summary_path}")
    print(f"Summary CSV saved to {summary_path}")

# -- Entry point --
if __name__ == "__main__":
    df      = load_raw_data(RAW_DIR)
    df      = clean_data(df)
    df      = add_features(df)
    summary = create_summary(df)

    print("\n-- Enriched Data Sample ----------------")
    print(df[["ticker", "date", "close", "daily_return_pct", "ma_7", "ma_30"]].head(10).to_string())

    print("\n-- Ticker Summary ----------------------")
    print(summary.to_string())

    save_outputs(df, summary, PROCESSED_DIR)
    print("\nTransformation complete. Check logs/transform.log for details.")