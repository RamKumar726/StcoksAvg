# 200-Week Stock Average

A clean Flask web app that calculates the 200-week moving average for any stock ticker and displays a buy/sell recommendation with a daily price chart.

## Features
- Enter any ticker symbol (AAPL, TSLA, etc.)
- Shows 200-week average price in ₹ (Rupees)
- Displays buy/sell recommendation (green = buy, red = avoid)
- Shows daily price chart for the past year
- Mobile-friendly responsive UI

## Local Development

### Prerequisites
- Python 3.9+
- pip

### Setup

1. **Clone or download the project:**
   ```bash
   cd StcoksAvg
   ```

2. **Create a virtual environment:**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the app:**
   ```bash
   python app.py
   ```

5. **Open in browser:**
   ```
   http://localhost:5000
   ```

## Production Deployment (Render.com)

### Method 1: Deploy via GitHub (Recommended)

1. **Push your code to GitHub:**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/YOUR_USERNAME/StcoksAvg.git
   git branch -M main
   git push -u origin main
   ```

2. **Create a Render account:**
   - Go to https://render.com
   - Sign up with GitHub

3. **Create a new Web Service:**
   - Click "New +" → "Web Service"
   - Connect your GitHub repo (StcoksAvg)
   - Fill in:
     - **Name:** `stocks-avg` (any name)
     - **Environment:** `Docker`
     - **Plan:** Free (or Starter)
     - **Auto-Deploy:** Enable

4. **Set Environment Variables:**
   - In Render dashboard, go to your service
   - Click "Environment" (or "Settings")
   - Add variable:
     ```
     SECRET_KEY: your-very-secret-random-string-here
     ```
     (e.g., `SECRET_KEY: 8f42a6c1b9d7e3f4k2m5n9p1q8x2y5z0`)

5. **Deploy:**
   - Render auto-deploys when you push to GitHub
   - Wait ~3-5 minutes for the build to complete
   - Your URL appears in the dashboard (e.g., `https://stocks-avg.onrender.com`)

### Method 2: Deploy via Docker (Locally Tested)

```powershell
# Build Docker image
docker build -t stocks-avg .

# Run locally to test
docker run -e SECRET_KEY="test-key" -p 8000:8000 stocks-avg

# Visit http://localhost:8000
```

Then push the Docker image to Docker Hub or use Render's Docker registry.

## File Structure

```
StcoksAvg/
├── app.py                    # Flask main app
├── stock_info.py             # Functions to fetch stock data & calculate average
├── requirements.txt          # Python dependencies
├── Dockerfile                # Docker configuration
├── .gitignore                # Git ignore rules
├── README.md                 # This file
├── templates/
│   ├── base.html            # Base template (navbar, flash messages)
│   ├── index.html           # Home page (form)
│   └── result.html          # Results page (stats + chart)
└── static/
    └── style.css            # Custom CSS
```

## Technologies Used

- **Flask** - Python web framework
- **yfinance** - Stock data fetching
- **pandas** - Data processing
- **Chart.js** - Interactive price charts
- **Bootstrap 5** - Responsive UI

## Notes

- Data is fetched real-time from Yahoo Finance
- Charts display the past 1 year of daily close prices
- Free Render tier may have ~15-minute cold starts; upgrade to Starter ($7/month) for always-on
- Recommended: Add caching (Redis) in the future to reduce API calls

## Support

If you encounter issues:
1. Check Flask logs in Render dashboard
2. Verify `SECRET_KEY` is set in environment variables
3. Ensure `requirements.txt` includes all needed packages

Enjoy! 📈
