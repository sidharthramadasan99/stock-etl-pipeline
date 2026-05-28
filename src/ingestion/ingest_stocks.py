import yfinance as yf
import pandas as pd
import os
import logging
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --Logging setup--
logging.basicConfig(
    filename="logs/ingestion.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --Configuration--
TICKERS = ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "WIPRO.NS"]
START_DATE = "2023-01-01"
END_DATE = datetime.today().strftime("%Y-%m-%d")
RAW_DIR = "data/raw"

# --Main ingestion function--
def ingest_stock_data(tickers, start, end, output_dir):
    os.makedirs(output_dir, exist_ok=True)

    # Remove old CSV files before downloading fresh data
    for old_file in os.listdir(output_dir):
        if old_file.endswith(".csv"):
            os.remove(os.path.join(output_dir, old_file))
    logger.info("Cleared old CSV files from data/raw/")

    for ticker in tickers:
        logger.info(f"Starting dowload for {tickers}")
        print(f"Downloading {ticker}...")

        try:
            df = yf.download(
                ticker,
                start=start,
                end=end,
                auto_adjust=True,
                progress=False
            )

            if df.empty:
                logger.warning(f"No data returned for {ticker}. Skipping.")
                print(f" WARNING: No data for {ticker}. Skipping.")
                continue

            # Flatten MultiIndex columns if present
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            # Reset index so Data becomes a regular column
            df.reset_index(inplace=True)

            # Add a column to track which ticker this row belongs to
            df["ticker"] = ticker

            # Rename columns to lowercase with underscores
            df.columns = [col.lower().replace(" ", "_") for col in df.columns]

            # Save as CSV in data/raw/
            filename = f"{ticker.replace('.', '_')}_{END_DATE}.csv"
            filepath = os.path.join(output_dir, filename)
            df.to_csv(filepath, index=False)

            logger.info(f"Saved {len(df)} rows for {ticker} -> {filepath}")
            print(f" SUCCESS: {len(df)} rows saved to {filepath}")
        
        except Exception as e:
            logger.error(f"Failed to download {ticker}: {e}")
            print(f"  ERROR: Failed to download {ticker}: {e}")
        
    print("\nIngestion complete. Check logs/ingestion.log for details.")

# --Entry point--
if __name__ == "__main__":
    ingest_stock_data(TICKERS, START_DATE, END_DATE, RAW_DIR)