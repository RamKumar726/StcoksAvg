from flask import Flask, render_template, request, flash, jsonify
from stock_info import get_200_week_average, search_nse_stocks, get_all_averages, get_daily_series
from fno_stocks import get_fno_stocks_with_prices
from nifty_stocks import get_nifty_stocks_with_prices
from nifty_next_50_stocks import get_nifty_next_50_stocks_with_prices
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-key-change-in-production")


@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        ticker = request.form.get("ticker", "").strip()
        if not ticker:
            flash("Please enter a ticker symbol.")
            return render_template("index.html")

        try:
            result = get_200_week_average(ticker)
            # also fetch daily series for charting (last 1 year)
            from stock_info import get_daily_series
            daily = get_daily_series(ticker, period="1y")
            result["daily_dates"] = daily.get("dates", [])
            result["daily_closes"] = daily.get("closes", [])
        except Exception as e:
            flash(f"Error fetching data for '{ticker}': {e}")
            return render_template("index.html")

        return render_template("result.html", result=result)

    return render_template("index.html")


@app.route("/api/search", methods=["GET"])
def search():
    """API endpoint to search NSE stocks by prefix."""
    prefix = request.args.get("q", "").strip()
    limit = request.args.get("limit", 20, type=int)
    
    if not prefix or len(prefix) < 1:
        return jsonify([])
    
    try:
        results = search_nse_stocks(prefix, limit=limit)
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/stock-details", methods=["GET"])
def stock_details():
    """API endpoint to fetch stock details (all moving averages, chart data, etc.)"""
    ticker = request.args.get("ticker", "").strip()
    
    if not ticker:
        return jsonify({"error": "Ticker is required"}), 400
    
    try:
        result = get_all_averages(ticker)
        # also fetch daily series for charting (last 1 year)
        daily = get_daily_series(ticker, period="1y")
        result["daily_dates"] = daily.get("dates", [])
        result["daily_closes"] = daily.get("closes", [])
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/fno-stocks", methods=["GET"])
def fno_stocks():
    """API endpoint to fetch FNO stocks with latest prices."""
    search_query = request.args.get("q", "").strip()
    
    try:
        results = get_fno_stocks_with_prices(search_query)
        return jsonify({"stocks": results})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/nifty-stocks", methods=["GET"])
def nifty_stocks():
    """API endpoint to fetch NIFTY50 stocks with latest prices."""
    search_query = request.args.get("q", "").strip()
    
    try:
        results = get_nifty_stocks_with_prices(search_query)
        return jsonify({"stocks": results})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/nifty-next-50-stocks", methods=["GET"])
def nifty_next_50_stocks():
    """API endpoint to fetch NIFTY Next 50 stocks with latest prices."""
    search_query = request.args.get("q", "").strip()
    
    try:
        results = get_nifty_next_50_stocks_with_prices(search_query)
        return jsonify({"stocks": results})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/fno", methods=["GET"])
def fno_page():
    """Render the FNO stocks page."""
    return render_template("fno.html")


@app.route("/nifty50", methods=["GET"])
def nifty50_page():
    """Render the NIFTY50 stocks page."""
    return render_template("nifty50.html")


@app.route("/nifty-next-50", methods=["GET"])
def nifty_next_50_page():
    """Render the NIFTY Next 50 stocks page."""
    return render_template("nifty_next_50.html")


@app.route("/stocks", methods=["GET"])
def stocks_page():
    """Render the stocks lists page (FNO, NIFTY50, NIFTY Next 50)."""
    return render_template("stocks.html")


if __name__ == "__main__":
    app.run(debug=True)