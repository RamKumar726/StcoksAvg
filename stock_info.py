import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta


def get_200_week_average(ticker: str) -> dict:
    ticker = ticker.strip().upper()
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



if __name__ == "__main__":
    # simple test
    print(get_200_week_average("AAPL"))