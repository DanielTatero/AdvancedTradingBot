from flask import Flask, jsonify, render_template
from bot_logic import get_portfolio_status, get_market_opportunities, get_portfolio_from_sheet

app = Flask(__name__)

GOOGLE_SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTgzLERS_DHab2QVnkbaJ5ai41K6IHHyBGb7ZkOZpXVMhuYLfnw7UEBL8MRihA7LX3BdZ8Dat4JjzEf/pub?gid=685213890&single=true&output=csv"
CANDIDATES = ['PLTR', 'CRWD', 'SNOW', 'UBER', 'SHOP', 'COIN', 'NU', 'SQ', 'AMD', 'TSLA', 'GOOGL', 'AMZN', 'META', 'NFLX', 'CRM']

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/portfolio')
def api_portfolio():
    tickers = get_portfolio_from_sheet(GOOGLE_SHEET_CSV_URL)
    if not tickers:
        tickers = ['SPY', 'QQQ', 'AAPL'] # Fallback por si falla el sheet
    
    from bot_logic import get_market_gain
    market_gain = get_market_gain(GOOGLE_SHEET_CSV_URL)
    data = get_portfolio_status(tickers)
    
    return jsonify({
        "market_gain": market_gain,
        "portfolio": data
    })

@app.route('/api/opportunities')
def api_opportunities():
    data = get_market_opportunities(CANDIDATES)
    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
