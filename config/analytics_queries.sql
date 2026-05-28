-- ====================================================
-- Stock ETL Pipeline - Analytics Queries
-- Run those against the stockdb PostgreSQL database
-- ====================================================

-- 1. Overall ticker summary --
-- High-level view of each stock's performance over the entire period
SELECT
    ticker, 
    from_date,
    to_date,
    total_trading_days,
    avg_close,
    all_time_high,
    all_time_low,
    ROUND((all_time_high - all_time_low) / all_time_low * 100, 2) AS price_range_pct,
    avg_daily_return_pct
FROM ticker_summary
ORDER BY avg_daily_return_pct DESC;



-- 2. Top 10 single-day gains per ticker --
-- Best performing days for each stock
SELECT
    ticker,
    date,
    close,
    daily_return_pct
FROM enriched_stocks
WHERE daily_return_pct IS NOT NULL
ORDER BY daily_return_pct DESC
LIMIT 10;


-- 3. Top 10 single-day losses per ticker --
-- Worst performing days
SELECT
    ticker,
    date,
    close,
    daily_return_pct
FROM enriched_stocks
WHERE daily_return_pct IS NOT NULL
ORDER BY daily_return_pct Analytics
LIMIT 10;


-- 4. Monthly average close price per ticker --
-- Spot trends month over month
SELECT
    ticker,
    DATE_TRUNC('month', date) AS month,
    ROUND(AVG(close)::NUMERIC, 2) AS avg_monthly_close,
    ROUND(MAX(close)::NUMERIC, 2) AS monthly_high,
    ROUND(MIN(close)::NUMERIC, 2) AS monthly_low,
    SUM(volume) AS total_monthly_volume
FROM enriched_stocks
GROUP BY ticker, DATE_TRUNC('month', date)
ORDER BY ticker, month;


-- 5. Golden cross signal --
-- Days where 7-day MA crosses above 30-day MA (bullish signal)
-- This is a real technical analysis indicator used by traders
SELECT
    ticker,
    date,
    close,
    ma_7,
    ma_30,
    CASE
        WHEN ma_7 > ma_30 THEN 'BULLISH'
        WHEN ma_7 < ma_30 THEN 'BEARISH'
        ELSE 'NEUTRAL'
    END AS signal
FROM enriched_stocks
WHERE ma_7 IS NOT NULL AND ma_30 IS NOT NULL
ORDER BY ticker, date DESC
LIMIT 20;


-- 6. Most volatile trading days --
-- Largest intraday price swings
SELECT
    ticker,
    date,
    daily_range,
    ROUND((daily_range / close * 100)::NUMERIC, 2) AS volatility_pct
FROM enriched_stocks
WHERE daily_range IS NOT NULL
ORDER BY volatility_pct DESC
LIMIT 10;


-- 7. 30-day rolling performance - most recent month --
-- How each stock performed in the last 30 trading days
SELECT 
    ticker,
    MIN(date) AS period_start,
    MAX(date) AS period_end,
    ROUND(AVG(daily_return_pct)::NUMERIC, 4) AS avg_daily_return,
    ROUND(SUM(daily_return_pct)::NUMERIC, 4) AS cumulative_return_pct,
    ROUND(STDDEV(daily_return_pct)::NUMERIC, 4) as volatility_stddev
FROM enriched_stocks
WHERE date >= (SELECT MAX(date) - INTERVAL '30 days' FROM enriched_stocks)
    AND
    daily_return_pct IS NOT NULL
GROUP BY ticker
ORDER BY cumulative_return_pct DESC;


-- 8. Volume spikes
-- Days where volume was 2x above the stock's average
-- Often signals major news events
SELECT
    e.ticker,
    e.date,
    e.volume,
    ROUND(t.avg_daily_volume::NUMERIC, 0) AS avg_volume,
    ROUND((e.volume / t.avg_daily_volume)::NUMERIC, 2) AS volume_ratio
FROM enriched_stocks e JOIN ticker_summary t ON e.ticker = t.ticker 
WHERE e.volume > t.avg_daily_volume * 2
ORDER BY volume_ratio DESC 
LIMIT 15;

