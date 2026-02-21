import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import requests
from io import StringIO


def get_200_week_average(ticker: str) -> dict:
    ticker = ticker.strip().upper()
    # For NSE stocks (already have .NS), use directly; otherwise normalize
    if not any(x in ticker for x in [".", "=", "^", "-"]):
        ticker = ticker + ".NS"  # Assume NSE for stock list calls
    end_date = datetime.today()
    start_date = end_date - timedelta(weeks=220)

    # Try to fetch weekly data; yf.download with interval '1wk' returns one row per week.
    df = yf.download(
        ticker,
        start=start_date.strftime("%Y-%m-%d"),
        end=end_date.strftime("%Y-%m-%d"),
        interval="1wk",
        progress=False,
        auto_adjust=True,
    )

    if df is None or df.empty:
        # fallback to ticker.history
        tk = yf.Ticker(ticker)
        df = tk.history(start=start_date.strftime("%Y-%m-%d"), end=end_date.strftime("%Y-%m-%d"), interval="1wk", auto_adjust=True)

    if df is None or df.empty:
        raise ValueError("No weekly data found for ticker")

    # Determine the price column: prefer 'Adj Close', then 'Close'. Handle MultiIndex columns.
    col_candidates = []
    cols = list(df.columns)
    for c in cols:
        name = c
        if isinstance(c, tuple):
            name = c[-1]
        name = str(name)
        if name in ("Adj Close", "Close") or "Close" in name:
            col_candidates.append(c)

    if not col_candidates:
        # fallback: try taking the first numeric column
        numeric_cols = [c for c in cols if pd.api.types.is_numeric_dtype(df[c].dtype)]
        if not numeric_cols:
            raise ValueError("No numeric price column found in data")
        col = numeric_cols[0]
    else:
        # prefer Adj Close if present
        adj = [c for c in col_candidates if (isinstance(c, str) and c == "Adj Close") or (isinstance(c, tuple) and c[-1] == "Adj Close")]
        col = adj[0] if adj else col_candidates[0]

    series = df[col]
    # If selecting a column produced a DataFrame (multi columns), pick first column
    if isinstance(series, pd.DataFrame):
        series = series.iloc[:, 0]

    # Coerce to numeric and drop NA
    series = pd.to_numeric(series, errors="coerce").dropna()

    weeks_available = len(series)
    last_200 = series.tail(200)
    avg_200 = float(last_200.mean()) if not last_200.empty else None

    latest_price = float(series.iloc[-1]) if weeks_available > 0 else None
    # compute difference and recommendation
    if avg_200 is None or latest_price is None:
        rec_type = "neutral"
        rec_text = "Insufficient data to form a recommendation"
        diff_pct = None
    else:
        diff_pct = (latest_price - avg_200) / avg_200 * 100 if avg_200 != 0 else None
        if latest_price < avg_200:
            rec_type = "buy"
            rec_text = "Good to buy — price is below the 200-week average"
        elif latest_price > avg_200:
            rec_type = "avoid"
            rec_text = "Do not buy — price is above the 200-week average"
        else:
            rec_type = "neutral"
            rec_text = "Price equals the 200-week average"

    return {
        "ticker": ticker,
        "weeks_available": weeks_available,
        "weeks_used": min(weeks_available, 200),
        "avg_200_week": avg_200,
        "latest_price": latest_price,
        "diff_pct": float(diff_pct) if diff_pct is not None else None,
        "rec_type": rec_type,
        "rec_text": rec_text,
    }


def get_daily_series(ticker: str, period: str = "1y") -> dict:
    """Return daily close series (dates and closes) for the given period.

    Returns dict with keys `dates` (list of yyyy-mm-dd) and `closes` (list of floats).
    """ 
    ticker = ticker.strip().upper()
    ticker = normalize_ticker(ticker)
    df = yf.download(
        ticker,
        period=period,
        interval="1d",
        progress=False,
        auto_adjust=True,
    )

    if df is None or df.empty:
        tk = yf.Ticker(ticker)
        df = tk.history(period=period, interval="1d", auto_adjust=True)

    if df is None or df.empty:
        return {"dates": [], "closes": []}

    # pick Close or Adj Close
    col = None
    for c in df.columns:
        name = c if not isinstance(c, tuple) else c[-1]
        if name == "Close":
            col = c
            break
        if name == "Adj Close":
            col = c
    if col is None:
        # fallback to first numeric column
        numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c].dtype)]
        if not numeric_cols:
            return {"dates": [], "closes": []}
        col = numeric_cols[0]

    series = df[col]
    if isinstance(series, pd.DataFrame):
        series = series.iloc[:, 0]

    series = pd.to_numeric(series, errors="coerce").dropna()
    dates = [d.strftime("%Y-%m-%d") for d in series.index]
    closes = [float(v) for v in series.values]
    return {"dates": dates, "closes": closes}


def get_moving_average(ticker: str, days: int) -> float:
    """Fetch moving average for given days. Uses yfinance built-in values when available."""
    ticker_clean = ticker.strip().upper()
    ticker_normalized = normalize_ticker(ticker_clean)
    
    try:
        # Try to get from yfinance info dict first (most reliable)
        tk = yf.Ticker(ticker_normalized)
        info = tk.info
        
        # Map days to yfinance info keys
        if days == 5:
            # yfinance doesn't have 5-day, calculate manually
            return _calculate_moving_average(ticker_normalized, days)
        elif days == 20:
            # yfinance doesn't have 20-day, calculate manually
            return _calculate_moving_average(ticker_normalized, days)
        elif days == 50:
            val = info.get("fiftyDayAverage")
            if val and isinstance(val, (int, float)):
                return float(val)
        elif days == 100:
            # yfinance doesn't have 100-day in standard info, calculate manually
            return _calculate_moving_average(ticker_normalized, days)
        elif days == 200:
            val = info.get("twoHundredDayAverage")
            if val and isinstance(val, (int, float)):
                return float(val)
        
        # Fallback: calculate manually if above didn't work
        return _calculate_moving_average(ticker_normalized, days)
    
    except Exception as e:
        # If anything fails, try manual calculation
        return _calculate_moving_average(ticker_normalized, days)


def _calculate_moving_average(ticker: str, days: int) -> float:
    """Helper function to manually calculate moving average from daily data."""
    try:
        # Use longer period for data retrieval
        if days >= 200:
            tk = yf.Ticker(ticker)
            df = tk.history(period="1y", auto_adjust=True)
        else:
            end_date = datetime.today()
            buffer_days = max(100, days + 50)
            start_date = end_date - timedelta(days=buffer_days)
            
            df = yf.download(
                ticker,
                start=start_date.strftime("%Y-%m-%d"),
                end=end_date.strftime("%Y-%m-%d"),
                interval="1d",
                progress=False,
                auto_adjust=True,
            )
            
            if df is None or df.empty:
                tk = yf.Ticker(ticker)
                df = tk.history(start=start_date.strftime("%Y-%m-%d"), end=end_date.strftime("%Y-%m-%d"), interval="1d", auto_adjust=True)
        
        if df is None or df.empty:
            return None
        
        # Get close price column
        col = None
        for c in df.columns:
            name = c if not isinstance(c, tuple) else c[-1]
            if name in ("Adj Close", "Close"):
                col = c
                if name == "Adj Close":
                    break
        
        if col is None:
            numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c].dtype)]
            if not numeric_cols:
                return None
            col = numeric_cols[0]
        
        series = df[col]
        if isinstance(series, pd.DataFrame):
            series = series.iloc[:, 0]
        
        series = pd.to_numeric(series, errors="coerce").dropna()
        
        if len(series) < days:
            return None
        
        last_days = series.tail(days)
        return float(last_days.mean()) if not last_days.empty else None
    except Exception:
        return None


def get_all_averages(ticker: str) -> dict:
    """Fetch stock details with all moving averages (200 weeks, 50 days, 100 days, 20 days, 5 days)."""
    ticker = ticker.strip().upper()
    normalized_ticker = normalize_ticker(ticker)
    
    # Get latest price with better error handling
    try:
        df_daily = yf.download(
            normalized_ticker,
            period="10d",
            interval="1d",
            progress=False,
            auto_adjust=True,
        )
        
        if df_daily is None or df_daily.empty:
            tk = yf.Ticker(normalized_ticker)
            df_daily = tk.history(period="10d", interval="1d", auto_adjust=True)
        
        if df_daily is None or df_daily.empty:
            raise ValueError(f"No data found for ticker {ticker}")
        
        # Extract close column more robustly
        col = None
        for c in df_daily.columns:
            name = c if not isinstance(c, tuple) else c[-1]
            if name in ("Close", "Adj Close"):
                col = c
                if name == "Adj Close":  # Prefer Adj Close
                    break
        
        if col is None:
            numeric_cols = [c for c in df_daily.columns if pd.api.types.is_numeric_dtype(df_daily[c].dtype)]
            if not numeric_cols:
                raise ValueError("No numeric price column found")
            col = numeric_cols[0]
        
        series = df_daily[col]
        if isinstance(series, pd.DataFrame):
            series = series.iloc[:, 0]
        
        series = pd.to_numeric(series, errors="coerce").dropna()
        if series.empty:
            raise ValueError("No valid price data")
        
        latest_price = float(series.iloc[-1])
    except Exception as e:
        raise ValueError(f"Failed to fetch latest price: {e}")
    
    # Calculate all moving averages using normalized ticker
    try:
        avg_5d = get_moving_average(normalized_ticker, 5)
        avg_20d = get_moving_average(normalized_ticker, 20)
        avg_50d = get_moving_average(normalized_ticker, 50)
        avg_100d = get_moving_average(normalized_ticker, 100)
        avg_200d = get_moving_average(normalized_ticker, 200)
        
        # Get 200-week average
        result_200w = get_200_week_average(ticker)
        avg_200w = result_200w.get("avg_200_week")
        
        # Get 52-week high and low
        tk = yf.Ticker(normalized_ticker)
        try:
            info = tk.info
            week_52_high = info.get("fiftyTwoWeekHigh")
            week_52_low = info.get("fiftyTwoWeekLow")
            
            # Fallback: try alternative keys
            if not week_52_high:
                week_52_high = info.get("fiftyTwoWeek", {}).get("high")
            if not week_52_low:
                week_52_low = info.get("fiftyTwoWeek", {}).get("low")
            
            # Convert to float if valid
            if isinstance(week_52_high, (int, float)):
                week_52_high = float(week_52_high)
            else:
                week_52_high = None
                
            if isinstance(week_52_low, (int, float)):
                week_52_low = float(week_52_low)
            else:
                week_52_low = None
        except Exception:
            week_52_high = None
            week_52_low = None
    except Exception as e:
        raise ValueError(f"Failed to calculate averages: {e}")
    
    # Determine recommendation based on 200-week average
    if avg_200w is None or latest_price is None:
        rec_type = "neutral"
        rec_text = f"Latest price: ₹{latest_price:.2f}" if latest_price else "Insufficient data"
    else:
        if latest_price < avg_200w:
            rec_type = "buy"
            rec_text = "✓ Good to buy — price is below 200-week avg"
        elif latest_price > avg_200w:
            rec_type = "avoid"
            rec_text = "✗ Do not buy — price is above 200-week avg"
        else:
            rec_type = "neutral"
            rec_text = "Price equals 200-week avg"
    
    return {
        "ticker": normalized_ticker,
        "latest_price": latest_price,
        "avg_5d": avg_5d,
        "avg_20d": avg_20d,
        "avg_50d": avg_50d,
        "avg_100d": avg_100d,
        "avg_200d": avg_200d,
        "avg_200w": avg_200w,
        "week_52_high": week_52_high,
        "week_52_low": week_52_low,
        "rec_type": rec_type,
        "rec_text": rec_text,
    }


def normalize_ticker(ticker: str) -> str:
    """
    Normalize ticker input:
    - If already contains '.' or '=' or '^' → assume complete (indices/forex/etc)
    - If pure alphabetic and <=5 chars → assume US ticker
    - Otherwise try NSE (.NS)
    """

    ticker = ticker.strip().upper()

    # Already formatted (e.g., RELIANCE.NS, ^NSEI, BTC-USD)
    if any(x in ticker for x in [".", "=", "^", "-"]):
        return ticker

    # Try US first
    us_test = yf.Ticker(ticker).history(period="5d")
    if not us_test.empty:
        return ticker

    # Try NSE
    nse_ticker = ticker + ".NS"
    nse_test = yf.Ticker(nse_ticker).history(period="5d")
    if not nse_test.empty:
        return nse_ticker

    # If nothing works, return original
    return ticker


if __name__ == "__main__":
    # simple test
    print(get_200_week_average("AAPL"))


# Cache for NSE CSV (reuse for 1 hour)
_nse_cache = {"data": None, "timestamp": None}


def fetch_nse_csv() -> pd.DataFrame:
    """Fetch NSE equity list CSV and return DataFrame."""
    global _nse_cache
    import time
    
    now = time.time()
    # Reuse cache if less than 3600 seconds (1 hour) old
    if _nse_cache["data"] is not None and _nse_cache["timestamp"] is not None:
        if (now - _nse_cache["timestamp"]) < 3600:
            return _nse_cache["data"]
    
    url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        df = pd.read_csv(StringIO(response.text))
        # Cache the result
        _nse_cache["data"] = df
        _nse_cache["timestamp"] = now
        return df
    except Exception as e:
        raise ValueError(f"Failed to fetch NSE CSV: {e}")


def search_nse_stocks(prefix: str, limit: int = 20) -> list:
    """Search NSE stocks by ticker/name prefix.
    
    Returns list of dicts: [{"symbol": "RELIANCE", "name": "Reliance Industries Limited"}, ...]
    """
    if not prefix or len(prefix.strip()) == 0:
        return []
    
    try:
        df = fetch_nse_csv()
    except Exception:
        return []
    
    prefix = prefix.strip().upper()
    
    # Filter by SYMBOL (ticker) first, then by NAME
    filtered = df[
        (df["SYMBOL"].str.contains(prefix, case=False, na=False)) |
        (df["NAME OF COMPANY"].str.contains(prefix, case=False, na=False))
    ]
    
    # Return top `limit` results
    results = []
    for _, row in filtered.head(limit).iterrows():
        results.append({
            "symbol": row["SYMBOL"],
            "name": row["NAME OF COMPANY"]
        })
    return results
