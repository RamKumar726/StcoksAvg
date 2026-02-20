import yfinance as yf
import pandas as pd
from stock_info import get_200_week_average
from concurrent.futures import ThreadPoolExecutor, as_completed


# FNO Stocks List
FNO_STOCKS = [
    "360ONE","ABB","ADANIENSOL","ADANIENT","ADANIGREEN","ADANIPORTS",
    "ABCAPITAL","ALKEM","AMBER","AMBUJACEM","ANGELONE","APLAPOLLO",
    "APOLLOHOSP","ASHOKLEY","ASIANPAINT","ASTRAL","AUBANK","AUROPHARMA",
    "DMART","AXISBANK","BAJAJ-AUTO","BAJFINANCE","BAJAJFINSV","BAJAJHLDNG",
    "BANDHANBNK","BANKBARODA","BANKINDIA","BDL","BEL","BHARATFORG",
    "BHEL","BPCL","BHARTIARTL","BIOCON","BLUESTARCO","BOSCHLTD",
    "BRITANNIA","BSE","CANBK","CDSL","CGPOWER","CHOLAFIN",
    "CIPLA","COALINDIA","COFORGE","COLPAL","CAMS","CONCOR",
    "CROMPTON","CUMMINSIND","DABUR","DALBHARAT","DELHIVERY","DIVISLAB",
    "DIXON","DLF","DRREDDY","EICHERMOT","EXIDEIND","FEDERALBNK",
    "FORTIS","NYKAA","GAIL","GLENMARK","GMRAIRPORT","GODREJCP",
    "GODREJPROP","GRASIM","HAVELLS","HCLTECH","HDFCAMC",
    "HDFCBANK","HDFCLIFE","HEROMOTOCO","HINDALCO","HAL",
    "HINDPETRO","HINDUNILVR","HINDZINC","POWERINDIA","HUDCO",
    "ICICIBANK","ICICIGI","ICICIPRULI","IDFCFIRSTB","INDIANB",
    "IEX","INDHOTEL","IOC","IRCTC","IRFC","IREDA",
    "INDUSTOWER","INDUSINDBK","NAUKRI","INFY","INOXWIND",
    "INDIGO","ITC","JINDALSTEL","JIOFIN","JSWENERGY","JSWSTEEL",
    "JUBLFOOD","KALYANKJIL","KAYNES","KEI","KFINTECH",
    "KOTAKBANK","KPITTECH","LTF","LT","LAURUSLABS",
    "LICHSGFIN","LICI","LTIM","LUPIN","LODHA",
    "M&M","MANAPPURAM","MANKIND","MARICO","MARUTI",
    "MFSL","MAXHEALTH","MAZDOCK","MPHASIS","MCX",
    "MUTHOOTFIN","NATIONALUM","NBCC","NESTLEIND","NHPC",
    "NMDC","NTPC","NUVAMA","OBEROIRLTY","ONGC",
    "OIL","PAYTM","OFSS","PIIND","PAGEIND",
    "PATANJALI","POLICYBZR","PERSISTENT","PETRONET","PGEL",
    "PHOENIXLTD","PIDILITIND","PPLPHARMA","PNBHOUSING","POLYCAB",
    "PFC","POWERGRID","PREMIERENE","PRESTIGE","PNB",
    "RVNL","RBLBANK","RECLTD","RELIANCE","SAMMAANCAP",
    "MOTHERSON","SBICARD","SBILIFE","SHREECEM","SHRIRAMFIN",
    "SIEMENS","SOLARINDS","SONACOMS","SRF","SBIN",
    "SAIL","SUNPHARMA","SUPREMEIND","SUZLON","SWIGGY",
    "SYNGENE","TCS","TATACONSUM","TATAELXSI","TMPV", "TMCV",
    "TATAPOWER","TATASTEEL","TATATECH","TECHM","TITAN",
    "TORNTPHARM","TORNTPOWER","TRENT","TIINDIA","TVSMOTOR",
    "ULTRACEMCO","UNIONBANK","UNITDSPR","UNOMINDA","UPL",
    "VBL","VEDL","IDEA","VOLTAS","WAAREEENER",
    "WIPRO","YESBANK","ETERNAL","ZYDUSLIFE"
]


def get_fno_stocks_with_prices(search_query: str = "") -> list:
    """Fetch all FNO stocks with their latest prices.
    
    If search_query is provided, filter stocks that start with the query (case-insensitive).
    
    Returns list of dicts: [{"symbol": "RELIANCE", "price": 2850.50, "status": "success"}, ...]
    """
    # Filter stocks by search query
    filtered_stocks = FNO_STOCKS
    if search_query:
        search_query = search_query.strip().upper()
        filtered_stocks = [stock for stock in FNO_STOCKS if stock.startswith(search_query)]
    
    results = []
    
    # Fetch prices in parallel using ThreadPoolExecutor
    def fetch_stock_data(symbol):
        try:
            # FNO stocks are NSE stocks - always use .NS suffix
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
                        # Try to fetch 200-week average (cached, so fast on repeat)
                        avg_200w = None
                        try:
                            avg_info = get_200_week_average(symbol)
                            avg_200w = avg_info.get("avg_200_week")
                        except Exception:
                            pass  # If avg fetch fails, just skip it

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
