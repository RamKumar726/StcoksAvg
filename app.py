from flask import Flask, render_template, request, flash
from stock_info import get_200_week_average
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


if __name__ == "__main__":
    app.run(debug=True)