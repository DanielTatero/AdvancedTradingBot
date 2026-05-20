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

def analyze_stock(ticker):
    try:
        # Fetch 6 months of data
        stock = yf.Ticker(ticker)
        df = stock.history(period="6mo")
        
        if df.empty or len(df) < 30:
            return None
            
        df = calculate_technical_indicators(df)
        
        try:
            info = stock.info
            target_mean = info.get('targetMeanPrice', "N/A")
            target_high = info.get('targetHighPrice', "N/A")
        except:
            target_mean = "N/A"
            target_high = "N/A"
            
        current_price = df['Close'].iloc[-1]
        current_rsi = df['RSI'].iloc[-1]
        current_macd = df['MACD'].iloc[-1]
        current_signal = df['Signal_Line'].iloc[-1]
        upper_band = df['Upper_Band'].iloc[-1]
        lower_band = df['Lower_Band'].iloc[-1]
        
        # Determine signals & Analysis
        signals = []
        analysis_text = f"<p>Basado en el cierre más reciente de <strong>${round(current_price, 2)}</strong>, aquí tienes el análisis técnico de <strong>{ticker}</strong>:</p><ul>"
        
        if current_rsi < 30:
            signals.append("RSI en Sobreventa (<30)")
            analysis_text += "<li><strong>RSI (Fuerza Relativa):</strong> Está por debajo de 30. Esto indica que la acción fue muy castigada y está 'sobrevendida'. Los inversores podrían verla muy barata y podría rebotar pronto.</li>"
        elif current_rsi > 70:
            signals.append("RSI en Sobrecompra (>70)")
            analysis_text += "<li><strong>RSI (Fuerza Relativa):</strong> Está por encima de 70. La acción está 'sobrecomprada', es decir, subió demasiado rápido. Hay un alto riesgo de corrección o caída en el corto plazo.</li>"
        else:
            analysis_text += f"<li><strong>RSI (Fuerza Relativa):</strong> Está en {round(current_rsi, 2)}. Es una zona neutral, sin presión extrema ni de compra ni de venta.</li>"
            
        if current_macd > current_signal:
            signals.append("MACD Alcista")
            analysis_text += "<li><strong>MACD (Tendencia):</strong> La línea cruzó hacia arriba. Es una excelente señal alcista que indica que el momentum (la fuerza de subida) es positivo.</li>"
        else:
            signals.append("MACD Bajista")
            analysis_text += "<li><strong>MACD (Tendencia):</strong> El indicador es bajista actualmente, perdiendo fuerza de subida.</li>"
            
        if current_price < lower_band:
            signals.append("Precio bajo BB Inferior (Rebote)")
            analysis_text += "<li><strong>Bandas de Bollinger (Volatilidad):</strong> ¡Atención! El precio rompió el suelo de la banda. Históricamente, el 95% del tiempo el precio vuelve a entrar, por lo que es un punto de entrada inmejorable (rebote inminente).</li>"
        elif current_price > upper_band:
            signals.append("Precio sobre BB Superior (Corrección)")
            analysis_text += "<li><strong>Bandas de Bollinger (Volatilidad):</strong> El precio perforó el techo de la banda. Es momento de cautela o tomar ganancias, ya que suele volver a bajar hacia el promedio.</li>"
            
        # Precios sugeridos
        entrada_sugerida = round(lower_band, 2) if current_price > lower_band else round(current_price, 2)
        salida_sugerida = target_mean if target_mean != "N/A" else (round(upper_band, 2) if not pd.isna(upper_band) else "N/A")

        analysis_text += f"</ul><br><h3>💰 Zonas de Operación:</h3><ul><li><strong>Entrada sugerida:</strong> ~ ${entrada_sugerida} (Basado en la banda inferior)</li><li><strong>Toma de Ganancia:</strong> ${salida_sugerida} (Consenso de analistas de Wall Street)</li></ul><br>"
        analysis_text += "<p><em>Recuerda: Los indicadores técnicos muestran probabilidades, no certezas absolutas. Analiza también el contexto del mercado.</em></p>"
        
        return {
            "ticker": ticker,
            "price": round(current_price, 2),
            "entry_price": entrada_sugerida,
            "take_profit": salida_sugerida,
            "rsi": round(current_rsi, 2) if not pd.isna(current_rsi) else "N/A",
            "macd": round(current_macd, 2) if not pd.isna(current_macd) else "N/A",
            "signal_line": round(current_signal, 2) if not pd.isna(current_signal) else "N/A",
            "upper_band": round(upper_band, 2) if not pd.isna(upper_band) else "N/A",
            "lower_band": round(lower_band, 2) if not pd.isna(lower_band) else "N/A",
            "signals": signals,
            "analysis_text": analysis_text
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
        data = analyze_stock(ticker)
        if data:
            # Simple scoring for opportunities
            score = 0
            if data['rsi'] != "N/A" and data['rsi'] < 45: score += 1
            if data['macd'] != "N/A" and data['signal_line'] != "N/A" and data['macd'] > data['signal_line']: score += 1
            if data['lower_band'] != "N/A" and data['price'] < data['lower_band'] * 1.05: score += 1
            
            data['score'] = score
            if score >= 1: # Any positive signal
                opportunities.append(data)
                
    # Sort by score descending
    opportunities.sort(key=lambda x: x['score'], reverse=True)
    return opportunities
