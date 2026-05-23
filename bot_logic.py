import yfinance as yf
import pandas as pd
import numpy as np

def calculate_technical_indicators(df):
    # RSI (14)
    delta = df['Close'].diff(1)
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))

    # MACD (12, 26, 9)
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()
    
    # Bollinger Bands (20, 2)
    df['SMA_20'] = df['Close'].rolling(window=20).mean()
    df['STD_20'] = df['Close'].rolling(window=20).std()
    df['Upper_Band'] = df['SMA_20'] + (df['STD_20'] * 2)
    df['Lower_Band'] = df['SMA_20'] - (df['STD_20'] * 2)

    return df

def get_portfolio_from_sheet(url):
    try:
        df = pd.read_csv(url)
        portfolio = []
        for index, row in df.iterrows():
            if pd.isna(row.iloc[0]): continue
            ticker = str(row.iloc[0]).strip().upper()
            if ticker:
                portfolio.append(ticker)
        return portfolio
    except Exception as e:
        print(f"Error reading sheet: {e}")
        return []

def get_market_gain(url):
    try:
        df = pd.read_csv(url)
        for index, row in df.iterrows():
            if len(row) >= 12:
                if str(row.iloc[10]).strip() == "Ganancia del Mercado:":
                    return str(row.iloc[11]).strip()
        return "N/A"
    except Exception as e:
        print(f"Error reading market gain: {e}")
        return "N/A"

def analyze_stock(ticker, is_candidate=False):
    try:
        # Fetch 6 months of data
        stock = yf.Ticker(ticker)
        df = stock.history(period="6mo")
        
        if df.empty or len(df) < 30:
            return None
            
        df = calculate_technical_indicators(df)
        
        info = stock.info
        exchange = info.get('exchange', '')
        market_cap = info.get('marketCap', 0)
        recommendation = info.get('recommendationKey', 'none').lower()
        target_mean = info.get('targetMeanPrice', 0)
        trailing_pe = info.get('trailingPE', 0)
        forward_pe = info.get('forwardPE', 0)
        beta = info.get('beta', 1.0)
        short_name = info.get('shortName', ticker)
        country = info.get('country', '')

        current_price = df['Close'].iloc[-1]
        
        upside = 0
        if target_mean and current_price > 0:
            upside = (target_mean / current_price) - 1
            
        if is_candidate:
            # 1. Cotiza en NYSE o NASDAQ
            if exchange not in ['NYQ', 'NMS', 'NYSE', 'NASDAQ']:
                return None
            # 2. Capitalizacion minima: USD 2.000 millones (Acepta Mid-Caps de crecimiento)
            if market_cap < 2_000_000_000:
                return None
            # 3. Consenso de analistas: minimo "Buy" o "Hold" (damos mas margen para rebotes técnicos)
            if recommendation not in ['buy', 'strong_buy', 'hold']:
                return None
            # 4. Upside minimo: 12% (Más realista para trades de corto/mediano plazo)
            if upside < 0.12:
                return None
            # 5. NO incluir acciones argentinas
            if country == 'Argentina' or ticker in ['GGAL', 'YPF', 'PAMP', 'BMA', 'CEPU', 'TGS', 'LOMA', 'SUPV']:
                return None
            # 6. NO incluir acciones sin earnings positivos consistentes (calidad aceptable)
            if not (trailing_pe > 0 or forward_pe > 0):
                return None
            # 8. Volatilidad aceptable: beta menor a 3.0 (Permite acciones "picantes" de alto beta)
            if beta >= 3.0:
                return None

        current_rsi = df['RSI'].iloc[-1]
        current_macd = df['MACD'].iloc[-1]
        current_signal = df['Signal_Line'].iloc[-1]
        upper_band = df['Upper_Band'].iloc[-1]
        lower_band = df['Lower_Band'].iloc[-1]
        
        # Determine signals
        signals = []
        if current_rsi < 30: signals.append("RSI en Sobreventa (<30)")
        elif current_rsi > 70: signals.append("RSI en Sobrecompra (>70)")
            
        if current_macd > current_signal: signals.append("MACD Alcista")
        else: signals.append("MACD Bajista")
            
        if current_price < lower_band: signals.append("Precio bajo BB Inferior (Rebote)")
        elif current_price > upper_band: signals.append("Precio sobre BB Superior (Corrección)")
            
        # Precios sugeridos
        entrada_sugerida = round(lower_band, 2) if current_price > lower_band else round(current_price, 2)
        take_profit = round(target_mean, 2) if target_mean else (round(upper_band, 2) if not pd.isna(upper_band) else "N/A")
        stop_loss = round(entrada_sugerida * 0.92, 2) # Ajustado a -8% para trades cortos y picantes

        analysis_text = f"<h4>{ticker} - {short_name}</h4>"
        analysis_text += f"<ul>"
        analysis_text += f"<li><strong>Precio actual:</strong> ${round(current_price, 2)} | <strong>Entrada sugerida:</strong> ${entrada_sugerida}</li>"
        analysis_text += f"<li><strong>Take Profit:</strong> ${take_profit} (Objetivo de ganancia o media de analistas)</li>"
        analysis_text += f"<li><strong>Stop Loss CORTITO:</strong> ${stop_loss} (-8% del precio de entrada para cortar pérdidas rápido)</li>"
        analysis_text += f"<li><strong>Por qué encaja:</strong> Trade dinámico. Beta de {round(beta, 2)} (volatilidad a favor), Upside {round(upside*100, 1)}%. Calidad aceptable (PE positivo, Market Cap ${market_cap/1e9:.1f}B). Ideal para sumar capital al portfolio principal.</li>"
        analysis_text += f"<li><strong>Riesgo:</strong> Al ser un trade más 'picante', respetá el Stop Loss a rajatabla.</li>"
        analysis_text += f"<li><strong>Tiempo estimado:</strong> Corto/Mediano plazo (1 a 6 meses).</li>"
        analysis_text += f"</ul>"
        
        return {
            "ticker": ticker,
            "price": round(current_price, 2),
            "entry_price": entrada_sugerida,
            "take_profit": take_profit,
            "stop_loss": stop_loss,
            "rsi": round(current_rsi, 2) if not pd.isna(current_rsi) else "N/A",
            "macd": round(current_macd, 2) if not pd.isna(current_macd) else "N/A",
            "signal_line": round(current_signal, 2) if not pd.isna(current_signal) else "N/A",
            "upper_band": round(upper_band, 2) if not pd.isna(upper_band) else "N/A",
            "lower_band": round(lower_band, 2) if not pd.isna(lower_band) else "N/A",
            "signals": signals,
            "analysis_text": analysis_text,
            "upside": upside
        }
    except Exception as e:
        print(f"Error analyzing {ticker}: {e}")
        return None

def get_portfolio_status(portfolio_tickers):
    results = []
    for ticker in portfolio_tickers:
        data = analyze_stock(ticker)
        if data:
            results.append(data)
    return results

def get_market_opportunities(candidates):
    opportunities = []
    for ticker in candidates:
        data = analyze_stock(ticker, is_candidate=True)
        if data:
            # Score by technicals + fundamental upside
            score = 0
            if data['rsi'] != "N/A" and data['rsi'] < 45: score += 1
            if data['macd'] != "N/A" and data['signal_line'] != "N/A" and data['macd'] > data['signal_line']: score += 1
            if data['lower_band'] != "N/A" and data['price'] < data['lower_band'] * 1.05: score += 1
            
            data['score'] = score + (data['upside'] * 10) # Weighted by upside
            if score >= 1: # Require at least 1 technical signal + all fundamentals
                opportunities.append(data)
                
    # Sort by score descending and return only top 3 to prioritize quality over quantity
    opportunities.sort(key=lambda x: x['score'], reverse=True)
    return opportunities[:3]
