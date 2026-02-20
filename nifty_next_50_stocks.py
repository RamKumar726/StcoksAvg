import yfinance as yf
import pandas as pd
from stock_info import get_200_week_average
from concurrent.futures import ThreadPoolExecutor, as_completed


# NIFTY Next 50 Stocks List
NIFTY_NEXT_50_STOCKS = [
    "ABB",
    "ADANIENSOL",
    "ADANIGREEN",
    "ADANIPOWER",
    "AMBUJACEM",
    "BAJAJHFL",
    "BAJAJHLDNG",
    "BANKBARODA",
    "BPCL",
    "BRITANNIA",
    "BOSCHLTD",
    "CANBK",
    "CGPOWER",
    "CHOLAFIN",
    "DIVISLAB",
    "DLF",
    "DMART",
    "ENRIN",
    "GAIL",
    "GODREJCP",
    "HAL",
    "HAVELLS",
    "HINDZINC",
    "HYUNDAI",
    "ICICIGI",
    "INDHOTEL",
    "IOC",
    "IRFC",
    "JINDALSTEL",
    "LICI",
    "LODHA",
    "LTIM",
    "MAZDOCK",
    "MOTHERSON",
    "NAUKRI",
    "PFC",
    "PIDILITIND",
    "PNB",
    "RECLTD",
    "SHREECEM",
    "SIEMENS",
    "SOLARINDS",
    "TATAPOWER",
    "TORNTPHARM",
    "TVSMOTOR",
    "UNITDSPR",
    "VBL",
    "VEDL",
    "ZYDUSLIFE"
]


def get_nifty_next_50_stocks_with_prices(search_query: str = "") -> list:
    """Fetch all NIFTY Next 50 stocks with their latest prices.
    
    If search_query is provided, filter stocks that start with the query (case-insensitive).
    
    Returns list of dicts: [{"symbol": "RELIANCE", "price": 2850.50, "status": "success"}, ...]
    """
    # Filter stocks by search query
    filtered_stocks = NIFTY_NEXT_50_STOCKS
    if search_query:
        search_query = search_query.strip().upper()
        filtered_stocks = [stock for stock in NIFTY_NEXT_50_STOCKS if stock.startswith(search_query)]
    
    results = []
    
    # Fetch prices in parallel using ThreadPoolExecutor
    def fetch_stock_data(symbol):
        try:
            # NIFTY Next 50 stocks are NSE stocks - always use .NS suffix
            nse_ticker = symbol + ".NS"
            
            # Fetch latest price using yfinance
            tk = yf.Ticker(nse_ticker)
            df = tk.history(period="5d", auto_adjust=True)
            
            if df is not None and not df.empty:
                # Get close price column
                col = None
                for c in df.columns:
                    name = c if not isinstance(c, tuple) else c[-1]
                    if name in ("Close", "Adj Close"):
                        col = c
                        if name == "Adj Close":
                            break
                
                if col is not None:
                    series = df[col]
                    if isinstance(series, pd.DataFrame):
                        series = series.iloc[:, 0]
                    
                    series = pd.to_numeric(series, errors="coerce").dropna()
                    if not series.empty:
                        latest_price = float(series.iloc[-1])
                        
                        # Fetch 200-week average (cached, so fast on repeat)
                        avg_200w = None
                        try:
                            avg_data = get_200_week_average(symbol)
                            if avg_data:
                                avg_200w = avg_data.get("avg_200_week")
                        except Exception:
                            pass  # If avg fetch fails, just leave as None
                        
                        return {
                            "symbol": symbol,
                            "price": latest_price,
                            "avg_200w": avg_200w,
                            "status": "success"
                        }
            
            # If we reach here, data fetch failed
            return {
                "symbol": symbol,
                "price": None,
                "avg_200w": None,
                "status": "no_data"
            }
        except Exception as e:
            return {
                "symbol": symbol,
                "price": None,
                "avg_200w": None,
                "status": f"error: {str(e)}"
            }
    
    # Use ThreadPoolExecutor to fetch multiple stocks in parallel
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(fetch_stock_data, symbol) for symbol in filtered_stocks]
        for future in as_completed(futures):
            results.append(future.result())
    
    return results
