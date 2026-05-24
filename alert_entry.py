import os
import smtplib
import datetime
import yfinance as yf
import pandas as pd
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- CONFIGURACION ---
EMAIL_ADDRESS  = os.environ.get("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
RECIPIENT_EMAIL = "Danielcharras07@gmail.com, macarenarodriguez22@gmail.com"

CANDIDATES = [
    'PLTR', 'CRWD', 'SNOW', 'UBER', 'SHOP', 'COIN', 'NU', 'SQ',
    'AMD', 'TSLA', 'GOOGL', 'AMZN', 'META', 'NFLX', 'CRM',
    'AAPL', 'MSFT', 'NVDA', 'MSTR', 'HOOD', 'ROKU', 'PATH',
    'DDOG', 'NET', 'ZS', 'MDB', 'SMCI', 'ARM'
]

# Tolerancia: si el precio actual esta dentro del X% del precio de entrada, se dispara la alerta
ENTRY_TOLERANCE = 0.03  # 3% de margen


def check_entries():
    alerts = []

    for ticker in CANDIDATES:
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period="6mo")

            if df.empty or len(df) < 30:
                continue

            info = stock.info
            exchange      = info.get('exchange', '')
            market_cap    = info.get('marketCap', 0)
            recommendation= info.get('recommendationKey', 'none').lower()
            target_mean   = info.get('targetMeanPrice', 0)
            trailing_pe   = info.get('trailingPE', 0)
            forward_pe    = info.get('forwardPE', 0)
            beta          = info.get('beta', 1.0)
            short_name    = info.get('shortName', ticker)
            country       = info.get('country', '')

            current_price = df['Close'].iloc[-1]

            upside = 0
            if target_mean and current_price > 0:
                upside = (target_mean / current_price) - 1

            # Filtros de calidad (picante pero con sustento)
            if exchange not in ['NYQ', 'NMS', 'NYSE', 'NASDAQ']: continue
            if market_cap < 2_000_000_000: continue
            if recommendation not in ['buy', 'strong_buy', 'hold']: continue
            if upside < 0.12: continue
            if country == 'Argentina': continue
            if not (trailing_pe > 0 or forward_pe > 0): continue
            if beta >= 3.0: continue

            # Calcular precio de entrada sugerida (Banda de Bollinger inferior)
            df['SMA_20'] = df['Close'].rolling(window=20).mean()
            df['STD_20'] = df['Close'].rolling(window=20).std()
            lower_band = df['SMA_20'].iloc[-1] - (df['STD_20'].iloc[-1] * 2)

            entry_price = round(lower_band, 2) if current_price > lower_band else round(current_price, 2)
            take_profit = round(target_mean, 2) if target_mean else None
            stop_loss   = round(entry_price * 0.92, 2)

            # DISPARO DE ALERTA: precio actual <= entrada + tolerancia del 3%
            trigger_price = entry_price * (1 + ENTRY_TOLERANCE)
            if current_price <= trigger_price:
                alerts.append({
                    'ticker':      ticker,
                    'name':        short_name,
                    'price':       round(current_price, 2),
                    'entry':       entry_price,
                    'take_profit': take_profit,
                    'stop_loss':   stop_loss,
                    'upside':      round(upside * 100, 1),
                    'beta':        round(beta, 2),
                })

        except Exception as e:
            print(f"[Error] {ticker}: {e}")
            continue

    return alerts


def build_email(alerts):
    date_str = datetime.datetime.now().strftime('%d/%m/%Y %H:%M')

    cards_html = ""
    for a in alerts:
        tp_str = f"${a['take_profit']:.2f}" if a['take_profit'] else "N/A"
        cards_html += f"""
        <div style="background:#eff6ff; border-left:4px solid #3b82f6; padding:20px;
                    border-radius:0 8px 8px 0; margin-bottom:20px;">
            <h3 style="margin:0 0 12px 0; color:#1e3a8a; font-size:20px;">
                {a['ticker']}
                <span style="font-weight:normal; font-size:15px; color:#60a5fa;">
                    | {a['name']}
                </span>
            </h3>
            <table style="width:100%; font-size:14px; border-collapse:collapse;">
                <tr>
                    <td style="padding:5px 10px 5px 0; color:#6b7280;">Precio Actual</td>
                    <td style="padding:5px; font-weight:bold; color:#111827;">${a['price']:.2f}</td>
                    <td style="padding:5px 10px 5px 0; color:#6b7280;">Entrada Sugerida</td>
                    <td style="padding:5px; font-weight:bold; color:#16a34a;">${a['entry']:.2f}</td>
                </tr>
                <tr>
                    <td style="padding:5px 10px 5px 0; color:#6b7280;">Take Profit</td>
                    <td style="padding:5px; font-weight:bold; color:#2563eb;">{tp_str}</td>
                    <td style="padding:5px 10px 5px 0; color:#6b7280;">Stop Loss (-8%)</td>
                    <td style="padding:5px; font-weight:bold; color:#dc2626;">${a['stop_loss']:.2f}</td>
                </tr>
                <tr>
                    <td style="padding:5px 10px 5px 0; color:#6b7280;">Upside proyectado</td>
                    <td style="padding:5px; font-weight:bold; color:#7c3aed;">{a['upside']}%</td>
                    <td style="padding:5px 10px 5px 0; color:#6b7280;">Beta</td>
                    <td style="padding:5px; color:#374151;">{a['beta']}</td>
                </tr>
            </table>
            <p style="margin:12px 0 0 0; font-size:13px; color:#374151;">
                <strong>Tiempo estimado:</strong> 1 a 6 meses &nbsp;|&nbsp;
                <strong>Respeta el Stop Loss a rajatabla.</strong>
            </p>
        </div>
        """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
                 background:#f3f4f6; padding:20px; margin:0;">
        <div style="max-width:650px; margin:0 auto; background:#fff;
                    border-radius:12px; overflow:hidden;
                    box-shadow:0 4px 6px -1px rgba(0,0,0,.1);">

            <!-- Header -->
            <div style="background:#111827; padding:25px 20px; text-align:center;">
                <h1 style="color:#facc15; margin:0; font-size:22px; font-weight:800;
                            letter-spacing:1px;">
                    ALERTA DE ENTRADA
                </h1>
                <p style="color:#9ca3af; margin:8px 0 0 0; font-size:13px;">
                    {date_str} — Punto de compra detectado
                </p>
            </div>

            <!-- Body -->
            <div style="padding:30px;">
                <p style="font-size:16px; color:#374151; margin-top:0;">
                    Hola Daniel,
                </p>
                <p style="font-size:15px; color:#374151; line-height:1.6;">
                    El bot detectó que las siguientes acciones <strong>están en zona de entrada</strong>
                    (precio actual dentro del 3% del punto de compra sugerido).
                    Este es el momento que esperabas para evaluar la compra.
                </p>

                {cards_html}

                <div style="background:#fef3c7; border:1px solid #fde68a; border-radius:8px;
                            padding:15px; margin-top:10px;">
                    <p style="margin:0; font-size:13px; color:#92400e;">
                        ⚠️ <strong>Recordatorio:</strong> Esto no es asesoramiento financiero.
                        Siempre analizá el contexto macro antes de operar y respetá el Stop Loss.
                    </p>
                </div>
            </div>

            <!-- Footer -->
            <div style="padding:15px 30px; border-top:1px solid #e5e7eb; text-align:center;">
                <p style="font-size:12px; color:#9ca3af; margin:0;">
                    Generado automáticamente por tu Agente Bull Market 🤖
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    return html


def send_alert_email(html_content, num_alerts):
    if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        print("[!] Credenciales no configuradas, no se envía email.")
        return

    subject = f"🚨 ALERTA DE ENTRADA — {num_alerts} accion(es) en punto de compra"
    msg = MIMEMultipart("alternative")
    msg['Subject'] = subject
    msg['From']    = f"Bull Market Alert <{EMAIL_ADDRESS}>"
    recipients     = [e.strip() for e in RECIPIENT_EMAIL.split(',')]
    msg['To']      = ", ".join(recipients)
    msg.attach(MIMEText(html_content, 'html'))

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.sendmail(EMAIL_ADDRESS, recipients, msg.as_string())
        server.quit()
        print(f"[OK] Alerta enviada a {len(recipients)} destinatario(s).")
    except Exception as e:
        print(f"[Error] Enviando alerta: {e}")


if __name__ == "__main__":
    print("Escaneando precios de entrada...")
    alerts = check_entries()

    if alerts:
        print(f"[!] {len(alerts)} alerta(s) detectada(s): {[a['ticker'] for a in alerts]}")
        html = build_email(alerts)
        # Guardar copia local para revisar
        with open("alerta_entrada.html", "w", encoding="utf-8") as f:
            f.write(html)
        send_alert_email(html, len(alerts))
    else:
        print("[OK] Ninguna accion en zona de entrada hoy. No se envia email.")
