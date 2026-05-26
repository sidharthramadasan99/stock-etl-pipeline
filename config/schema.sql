-- Stock ETL Pipeline - Database Schema
-- Run thsi to recreate the database from scratch

CREATE DATABASE stockdb;
\c stockdb

CREATE TABLE enriched_stocks (
    id          SERIAL PRIMARY KEY,
    ticker      VARCHAR(20)    NOT NULL,
    date        DATE           NOT NULL,
    open        NUMERIC(12,2),
    high        NUMERIC(12,2),
    low         NUMERIC(12,2),
    close       NUMERIC(12,2)  NOT NULL,
    volume      BIGINT,
    daily_return_pct  NUMERIC(10,4),
    ma_7        NUMERIC(12,2),
    ma_30       NUMERIC(12,2),
    daily_range NUMERIC(12,2),
    UNIQUE(ticker, date)
);

CREATE TABLE ticker_summary (
    id                   SERIAL PRIMARY KEY,
    ticker               VARCHAR(20)   NOT NULL UNIQUE,
    from_date            DATE,
    to_date              DATE,
    total_trading_days   INTEGER,
    avg_close            NUMERIC(12,2),
    all_time_high        NUMERIC(12,2),
    all_time_low         NUMERIC(12,2),
    avg_daily_volume     NUMERIC(20,2),
    avg_daily_return_pct NUMERIC(10,4)
);

CREATE INDEX idx_enriched_ticker ON enriched_stocks(ticker);
CREATE INDEX idx_enriched_date   ON enriched_stocks(date);