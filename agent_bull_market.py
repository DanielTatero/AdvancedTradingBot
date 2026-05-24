import pandas as pd
import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import requests
import xml.etree.ElementTree as ET
import yfinance as yf

# --- CONFIGURACIÓN ---
EMAIL_ADDRESS = os.environ.get("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD") 
RECIPIENT_EMAIL = "Danielcharras07@gmail.com, macarenarodriguez22@gmail.com"

# Coloca aquí el link de tu Google Sheet publicado como CSV
GOOGLE_SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTgzLERS_DHab2QVnkbaJ5ai41K6IHHyBGb7ZkOZpXVMhuYLfnw7UEBL8MRihA7LX3BdZ8Dat4JjzEf/pub?gid=685213890&single=true&output=csv"

# Lista de oportunidades enfocada en empresas solidas del mercado USA y tecnológicas de alto beta
CANDIDATES = ['PLTR', 'CRWD', 'SNOW', 'UBER', 'SHOP', 'COIN', 'NU', 'SQ', 'AMD', 'TSLA', 'GOOGL', 'AMZN', 'META', 'NFLX', 'CRM', 'AAPL', 'MSFT', 'NVDA', 'MSTR', 'HOOD', 'ROKU', 'PATH', 'DDOG', 'NET', 'ZS', 'MDB', 'SMCI', 'ARM']

def calculate_rsi(data, window=14):
    diff = data.diff(1).dropna()
    gain = (diff.where(diff > 0, 0)).rolling(window=window).mean()
    loss = (-diff.where(diff < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def get_historical_data(ticker, period="1mo"):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period)
        if df.empty:
            return pd.DataFrame()
        return df
    except Exception as e:
        print(f"Error descargando {ticker}: {e}")
        return pd.DataFrame()

def get_market_news():
    # Busca noticias en español sobre el S&P 500 de los últimos 7 días
    url = "https://news.google.com/rss/search?q=S%26P+500+mercado+acciones+EEUU+when:7d&hl=es-419&gl=AR&ceid=AR:es-419"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    news_items = []
    try:
        response = requests.get(url, headers=headers, timeout=10)
        root = ET.fromstring(response.text)
        for item in root.findall('.//item')[:2]: # Tomamos las 2 más relevantes
            title = item.find('title').text
            link = item.find('link').text
            # Limpiamos el nombre del diario al final del título
            clean_title = title.rsplit(' - ', 1)[0] if ' - ' in title else title
            news_items.append({'title': clean_title, 'link': link})
    except Exception as e:
        print(f"Error obteniendo noticias: {e}")
    
    return news_items

def get_portfolio_from_sheet():
    # Si no configuraste el link, usa este portafolio por defecto
    default_portfolio = [{'ticker': t, 'purchase_price': None, 'total_gain_usd': None} for t in ['NVDA', 'SPY', 'PG', 'KO', 'CVX', 'O', 'DIA', 'SCHD', 'MSFT', 'BBD']]
    
    if not GOOGLE_SHEET_CSV_URL or "tu_link_aqui" in GOOGLE_SHEET_CSV_URL:
        return default_portfolio
        
    try:
        df = pd.read_csv(GOOGLE_SHEET_CSV_URL)
        portfolio = []
        for index, row in df.iterrows():
            if pd.isna(row.iloc[0]):
                continue
            ticker = str(row.iloc[0]).strip().upper()
            if not ticker:
                continue
                
            purchase_price = None
            if len(df.columns) > 2 and not pd.isna(row.iloc[2]):
                try:
                    val = str(row.iloc[2]).replace('$', '').strip()
                    if ',' in val and '.' in val:
                        if val.rfind('.') < val.rfind(','):
                            val = val.replace('.', '').replace(',', '.')
                        else:
                            val = val.replace(',', '')
                    elif ',' in val:
                        val = val.replace(',', '.')
                    purchase_price = float(val)
                except ValueError:
                    pass

            total_gain_usd = None
            if len(df.columns) > 7 and not pd.isna(row.iloc[7]):
                try:
                    val = str(row.iloc[7]).replace('$', '').strip()
                    if ',' in val and '.' in val:
                        if val.rfind('.') < val.rfind(','):
                            val = val.replace('.', '').replace(',', '.')
                        else:
                            val = val.replace(',', '')
                    elif ',' in val:
                        val = val.replace(',', '.')
                    total_gain_usd = float(val)
                except ValueError:
                    pass
                    
            portfolio.append({'ticker': ticker, 'purchase_price': purchase_price, 'total_gain_usd': total_gain_usd})
            
        return portfolio if portfolio else default_portfolio
    except Exception as e:
        print(f"[!] Error leyendo Google Sheet: {e}")
        return default_portfolio

def analyze_portfolio():
    results = []
    
    # Obtenemos tu cartera actualizada del Drive
    portfolio_items = get_portfolio_from_sheet()
    
    for item in portfolio_items:
        ticker = item['ticker']
        total_gain_usd = item['total_gain_usd']
        purchase_price = item.get('purchase_price')
        try:
            # Usamos nuestro propio cliente directo a la API de Yahoo
            df = get_historical_data(ticker, period="1mo")
            
            if df.empty or len(df) < 5:
                print(f"[!] Datos insuficientes para {ticker}")
                continue
            
            current_price = df['Close'].iloc[-1]
            
            # Buscar el precio de hace una semana (aprox 5 días hábiles atrás)
            idx_1w = -6 if len(df) >= 6 else 0
            price_1w_ago = df['Close'].iloc[idx_1w]
            
            # Buscar el precio de hace un mes (el primero del dataframe)
            price_1m_ago = df['Close'].iloc[0]
            
            weekly_change = ((current_price - price_1w_ago) / price_1w_ago) * 100
            monthly_change = ((current_price - price_1m_ago) / price_1m_ago) * 100
                
            if weekly_change > 0.5:
                trend = '📈 Alcista'
            elif weekly_change < -0.5:
                trend = '📉 Bajista'
            else:
                trend = '➡️ Lateral'
                
            results.append({
                'ticker': ticker,
                'price': purchase_price if purchase_price is not None else current_price,
                'weekly': weekly_change,
                'monthly': monthly_change,
                'total_gain': total_gain_usd,
                'trend': trend
            })
        except Exception as e:
            print(f"[Error] Analizando {ticker}: {e}")
            results.append({'error': str(e), 'ticker': ticker})
            
    return results

def find_opportunities():
    opportunities = []
    
    for ticker in CANDIDATES:
        try:
            df = get_historical_data(ticker, period="1y")
            if df.empty or len(df) < 50: 
                continue
            
            current_price = df['Close'].iloc[-1]
            
            stock = yf.Ticker(ticker)
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
            
            upside = 0
            if target_mean and current_price > 0:
                upside = (target_mean / current_price) - 1

            # Criterios obligatorios (relajados para swing corto/picante)
            if exchange not in ['NYQ', 'NMS', 'NYSE', 'NASDAQ']: continue
            if market_cap < 2_000_000_000: continue
            if recommendation not in ['buy', 'strong_buy', 'hold']: continue
            if upside < 0.12: continue
            if country == 'Argentina' or ticker in ['GGAL', 'YPF', 'PAMP', 'BMA', 'CEPU', 'TGS', 'LOMA', 'SUPV']: continue
            if not (trailing_pe > 0 or forward_pe > 0): continue
            if beta >= 3.0: continue

            df['SMA_20'] = df['Close'].rolling(window=20).mean()
            df['STD_20'] = df['Close'].rolling(window=20).std()
            lower_band = df['SMA_20'].iloc[-1] - (df['STD_20'].iloc[-1] * 2)
            
            entrada_sugerida = round(lower_band, 2) if current_price > lower_band else round(current_price, 2)
            take_profit = round(target_mean, 2)
            stop_loss = round(entrada_sugerida * 0.92, 2)
            
            opportunities.append({
                'ticker': ticker,
                'name': short_name,
                'price': round(current_price, 2),
                'entry_price': entrada_sugerida,
                'take_profit': take_profit,
                'stop_loss': stop_loss,
                'market_cap': market_cap,
                'beta': round(beta, 2),
                'upside': round(upside * 100, 1),
                'recommendation': recommendation
            })
            
        except Exception as e:
            print(f"Error analizando oportunidad {ticker}: {e}")
            continue
            
    # Priority based on upside
    opportunities.sort(key=lambda x: x['upside'], reverse=True)
    return opportunities[:3]

def generate_html_email(portfolio_data, opportunities, date_str, news_data):
    valid_data = [d for d in portfolio_data if "error" not in d]
    
    if valid_data:
        best_stock = max(valid_data, key=lambda x: x['weekly'])
        worst_stock = min(valid_data, key=lambda x: x['weekly'])
    else:
        best_stock = {'ticker': 'N/A', 'weekly': 0}
        worst_stock = {'ticker': 'N/A', 'weekly': 0}

    table_rows = ""
    error_messages = []
    
    for data in portfolio_data:
        if "error" in data:
            error_messages.append(f"{data['ticker']}: {data['error']}")
            continue
            
        weekly_color = "#16a34a" if data["weekly"] > 0 else "#dc2626"
        monthly_color = "#16a34a" if data["monthly"] > 0 else "#dc2626"
        
        total_gain_html = "-"
        if data.get("total_gain") is not None:
            gain_color = "#16a34a" if data["total_gain"] > 0 else "#dc2626"
            sign = "+" if data["total_gain"] > 0 else "-"
            total_gain_html = f'<span style="color: {gain_color}; font-weight: bold;">{sign}${abs(data["total_gain"]):.2f}</span>'
            
        table_rows += f'''
        <tr style="border-bottom: 1px solid #e5e7eb;">
            <td style="padding: 12px 16px; font-weight: bold; color: #1f2937;">{data["ticker"]}</td>
            <td style="padding: 12px 16px; color: #4b5563;">${data["price"]:.2f}</td>
            <td style="padding: 12px 16px; text-align: center;">{total_gain_html}</td>
            <td style="padding: 12px 16px; font-weight: bold; color: {weekly_color};">{data["weekly"]:+.2f}%</td>
            <td style="padding: 12px 16px; font-weight: bold; color: {monthly_color};">{data["monthly"]:+.2f}%</td>
            <td style="padding: 12px 16px; color: #4b5563;">{data["trend"]}</td>
        </tr>
        '''

    if not table_rows:
        error_details = "<br>".join(error_messages) if error_messages else "Datos insuficientes devueltos por Yahoo Finance."
        table_rows = f'<tr><td colspan="6" style="padding: 20px; text-align: center; color: #dc2626;">⚠️ No se pudieron cargar los datos.<br><small>{error_details}</small></td></tr>'

    news_html = ""
    if news_data:
        news_list = "".join([f'<li style="margin-bottom: 8px;"><a href="{news["link"]}" style="color: #2563eb; text-decoration: none; font-weight: 500;">{news["title"]}</a></li>' for news in news_data])
        news_html = f'''
        <!-- News Section -->
        <h2 style="font-size: 18px; color: #111827; border-bottom: 2px solid #e5e7eb; padding-bottom: 10px; margin-top: 40px;">📰 Radar Macro (S&P 500)</h2>
        <div style="background-color: #fffbeb; border: 1px solid #fef3c7; border-radius: 8px; padding: 15px; margin-top: 15px;">
            <p style="margin: 0 0 10px 0; font-size: 14px; color: #92400e;"><strong>Titulares de la semana que impactan en el SPY:</strong></p>
            <ul style="margin: 0; padding-left: 20px; font-size: 14px; color: #374151; line-height: 1.5;">
                {news_list}
            </ul>
        </div>
        '''

    opps_html = ""
    if opportunities:
        for opp in opportunities:
            opps_html += f'''
                <div style="background-color: #eff6ff; border-left: 4px solid #3b82f6; padding: 20px; border-radius: 0 8px 8px 0; margin-top: 15px;">
                    <h3 style="margin: 0 0 10px 0; color: #1e3a8a; font-size: 20px;">{opp['ticker']} <span style="font-weight: normal; font-size: 16px; color: #60a5fa;">| {opp['name']}</span></h3>
                    
                    <div style="display: flex; margin-bottom: 15px; gap: 20px; flex-wrap: wrap;">
                        <div>
                            <span style="font-size: 12px; color: #6b7280; text-transform: uppercase; font-weight: bold;">Precio Actual</span><br>
                            <span style="font-size: 18px; font-weight: bold; color: #1f2937;">${opp['price']:.2f}</span>
                        </div>
                        <div>
                            <span style="font-size: 12px; color: #6b7280; text-transform: uppercase; font-weight: bold;">Entrada Sugerida</span><br>
                            <span style="font-size: 16px; color: #374151;">${opp['entry_price']:.2f}</span>
                        </div>
                        <div>
                            <span style="font-size: 12px; color: #6b7280; text-transform: uppercase; font-weight: bold;">Take Profit</span><br>
                            <span style="font-size: 16px; color: #16a34a;">${opp['take_profit']:.2f}</span>
                        </div>
                        <div>
                            <span style="font-size: 12px; color: #6b7280; text-transform: uppercase; font-weight: bold;">Stop Loss</span><br>
                            <span style="font-size: 16px; color: #dc2626;">${opp['stop_loss']:.2f}</span>
                        </div>
                    </div>

                    <p style="margin: 0 0 5px 0; font-size: 14px; color: #1f2937;"><strong>¿Por qué encaja para este trade dinámico?</strong></p>
                    <ul style="margin: 0 0 10px 0; padding-left: 20px; font-size: 14px; color: #374151; line-height: 1.6;">
                        <li>Calidad aceptable: Capitalización > $2B, PE Positivo y Beta de {opp['beta']} (buena volatilidad a favor).</li>
                        <li>Upside proyectado del {opp['upside']}%. Ideal para engordar la cuenta y luego pasarlo a tu cartera de largo plazo.</li>
                        <li><strong>Riesgo:</strong> Al ser un trade más corto y agresivo, respetá el Stop Loss a rajatabla.</li>
                        <li><strong>Tiempo estimado:</strong> Corto/Mediano plazo (1 a 6 meses).</li>
                    </ul>
                </div>
            '''
    else:
        opps_html = "<p style='color: #6b7280; font-size: 14px; margin-top: 15px;'>No se encontraron oportunidades técnicas hoy en empresas de calidad aceptable. Priorizamos cuidar el capital hasta que el mercado dé una señal más clara.</p>"

    html = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
    </head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f3f4f6; padding: 20px; margin: 0;">
        <div style="max-width: 650px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
            
            <!-- Header -->
            <div style="background-color: #111827; padding: 30px 20px; text-align: center;">
                <h1 style="color: #ffffff; margin: 0; font-size: 24px; font-weight: 800; letter-spacing: 1px;">BULL MARKET WEEKLY</h1>
                <p style="color: #9ca3af; margin: 10px 0 0 0; font-size: 14px;">Reporte Ejecutivo del Cierre Semanal</p>
            </div>

            <!-- Content -->
            <div style="padding: 30px;">
                <p style="font-size: 16px; color: #374151; margin-top: 0;">Hola Daniel,</p>
                <p style="font-size: 16px; color: #374151; line-height: 1.5;">El mercado ha cerrado. Aquí tienes el análisis de rendimiento de tu portafolio y las oportunidades destacadas para la próxima semana alineadas con tu perfil.</p>
                
                <!-- Portfolio Section -->
                <h2 style="font-size: 18px; color: #111827; border-bottom: 2px solid #e5e7eb; padding-bottom: 10px; margin-top: 30px;">📋 Tu Portafolio</h2>
                <div style="border-radius: 8px; overflow: hidden; border: 1px solid #e5e7eb; margin-top: 15px;">
                    <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 14px;">
                        <thead style="background-color: #f9fafb;">
                            <tr>
                                <th style="padding: 12px 16px; color: #6b7280; font-weight: 600;">Ticker</th>
                                <th style="padding: 12px 16px; color: #6b7280; font-weight: 600;">Costo Unit.</th>
                                <th style="padding: 12px 16px; color: #6b7280; font-weight: 600; text-align: center;">Ganancia (USD)</th>
                                <th style="padding: 12px 16px; color: #6b7280; font-weight: 600;">Semana</th>
                                <th style="padding: 12px 16px; color: #6b7280; font-weight: 600;">Mes</th>
                                <th style="padding: 12px 16px; color: #6b7280; font-weight: 600;">Tendencia</th>
                            </tr>
                        </thead>
                        <tbody>
                            {table_rows}
                        </tbody>
                    </table>
                </div>

                <div style="background-color: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 15px; margin-top: 20px;">
                    <p style="margin: 0 0 8px 0; font-size: 14px; color: #166534;">🏆 <strong>Mejor desempeño:</strong> {best_stock['ticker']} con <strong>{best_stock['weekly']:+.2f}%</strong></p>
                    <p style="margin: 0 0 8px 0; font-size: 14px; color: #991b1b;">⚠️ <strong>Mayor caída:</strong> {worst_stock['ticker']} con <strong>{worst_stock['weekly']:+.2f}%</strong></p>
                    <p style="margin: 0; font-size: 14px; color: #1f2937;">💰 <strong>Atención:</strong> O, SCHD y KO pagan dividendos pronto. Revisar calendario ex-div.</p>
                </div>

                <!-- Opportunity Section -->
                <h2 style="font-size: 18px; color: #111827; border-bottom: 2px solid #e5e7eb; padding-bottom: 10px; margin-top: 40px;">🚀 Acciones Recomendadas (Swing de Corto/Mediano Plazo)</h2>
                
                {opps_html}

                {news_html}

                <!-- Footer -->
                <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #e5e7eb; text-align: center;">
                    <p style="font-size: 12px; color: #9ca3af; margin: 0;">
                        ⚠️ Esto no es asesoramiento financiero. Siempre realiza tu propia investigación antes de operar.
                    </p>
                    <p style="font-size: 12px; color: #6b7280; margin-top: 10px; font-weight: bold;">
                        Generado automáticamente por tu Agente Bull Market 🤖
                    </p>
                </div>
            </div>
        </div>
    </body>
    </html>
    '''
    return html

def send_email(subject, html_content):
    if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        print("[!] Advertencia: Credenciales no configuradas. El email no se enviará.")
        return

    msg = MIMEMultipart("alternative")
    msg['Subject'] = subject
    msg['From'] = f"Bull Market Agent <{EMAIL_ADDRESS}>"
    
    # Soporte para múltiples destinatarios separados por comas
    recipients = [email.strip() for email in RECIPIENT_EMAIL.split(',')]
    msg['To'] = ", ".join(recipients)

    part = MIMEText(html_content, 'html')
    msg.attach(part)

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.sendmail(EMAIL_ADDRESS, recipients, msg.as_string())
        server.quit()
        print(f"[OK] Email enviado con éxito a {len(recipients)} destinatario(s)")
    except Exception as e:
        print(f"[Error] Enviando email: {e}")

if __name__ == "__main__":
    print("Iniciando análisis...")
    portfolio_data = analyze_portfolio()
    opportunities = find_opportunities()
    news_data = get_market_news()
    date_str = datetime.datetime.now().strftime('%d/%m/%Y')
    subject = f"📈 Bull Market Weekly — Cierre {date_str}"
    html_content = generate_html_email(portfolio_data, opportunities, date_str, news_data)
    
    with open("reporte_prueba.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    print("[OK] Reporte guardado localmente como 'reporte_prueba.html' para que puedas probarlo.")
        
    send_email(subject, html_content)
    print("Ejecución finalizada.")
