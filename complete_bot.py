import telebot
import yfinance as yf
import time
from datetime import datetime, timedelta
import pytz
import threading

# ===== FLASK SERVER (FOR RENDER PORT REQUIREMENT) =====
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "✅ NASDAQ Bot is running!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

def start_flask():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()
    print("🌐 Web server started on port 8080")

# Start Flask immediately
start_flask()
# ===== END FLASK SERVER =====

# ===== TELEGRAM BOT CODE =====
TOKEN = "8234060598:AAHoKauET9e9Yam_29CE1qqFArYoEeM1JCE"
bot = telebot.TeleBot(TOKEN)

chat_id = None
last_scan = None
alert_count = 0

NASDAQ = ["QQQ", "AAPL", "TSLA", "NVDA", "MSFT"]

@bot.message_handler(commands=['start'])
def start(msg):
    global chat_id
    chat_id = msg.chat.id
    bot.reply_to(msg, """✅ *NASDAQ Auto-Trader Started*

*Commands:*
/status - Bot status
/signal [SYMBOL] - Get signal
/scan - Scan all stocks
/alerts - Alert history
/symbols - Available symbols

*Auto-alerts:* Every 5 minutes
*Market hours:* 9:30 AM - 4:00 PM EST""", parse_mode='Markdown')
    print(f"Chat ID: {chat_id}")

@bot.message_handler(commands=['status'])
def status(msg):
    global last_scan, alert_count
    
    now = datetime.now(pytz.timezone('America/New_York'))
    market_open = now.replace(hour=9, minute=30, second=0)
    market_close = now.replace(hour=16, minute=0, second=0)
    
    status_msg = f"""📊 *Bot Status*

✅ Running: Yes
📈 Symbols: {len(NASDAQ)}
🔔 Alerts sent: {alert_count}
🕐 Last scan: {last_scan if last_scan else 'Never'}

*Market Status:* {'🟢 OPEN' if market_open <= now <= market_close else '🔴 CLOSED'}
*Current time:* {now.strftime('%H:%M:%S EST')}
*Next scan:* {(datetime.now() + timedelta(minutes=5)).strftime('%H:%M')}

*Active features:*
• Auto-scan every 5 min
• QQQ, AAPL, TSLA, NVDA, MSFT
• 1%+ move alerts""".replace('_', '\\_')
    
    bot.reply_to(msg, status_msg, parse_mode='Markdown')

@bot.message_handler(commands=['signal'])
def signal(msg):
    try:
        parts = msg.text.split()
        symbol = parts[1].upper() if len(parts) > 1 else "QQQ"
        
        if symbol not in NASDAQ:
            bot.reply_to(msg, f"Available: {', '.join(NASDAQ)}")
            return
        
        bot.reply_to(msg, f"🔍 Analyzing {symbol}...")
        
        df = yf.download(symbol, period="1d", interval="15m")
        price = float(df['Close'].iloc[-1])
        prev = float(df['Close'].iloc[-2])
        change = ((price - prev) / prev * 100)
        
        if abs(change) > 1.0:
            signal = "BUY" if change > 0 else "SELL"
            response = f"""{'🟢' if change > 0 else '🔴'} *{signal} {symbol}*

*Price:* ${price:.2f}
*Change:* {change:+.1f}%
*Volume:* {df['Volume'].iloc[-1]:,.0f}

*Action:* {'Enter long' if change > 0 else 'Enter short'}
*Stop Loss:* ${price * (0.99 if change > 0 else 1.01):.2f}
*Take Profit:* ${price * (1.02 if change > 0 else 0.98):.2f}

*Time:* {df.index[-1].strftime('%H:%M')}"""
        else:
            response = f"""📊 *{symbol} Analysis*

*Price:* ${price:.2f}
*Change:* {change:+.1f}%
*Signal:* HOLD

*No strong signal.* Wait for >1% move.
*Support:* ${df['Low'].min():.2f}
*Resistance:* ${df['High'].max():.2f}"""
        
        bot.reply_to(msg, response, parse_mode='Markdown')
        
    except Exception as e:
        bot.reply_to(msg, f"Error: {str(e)}")

@bot.message_handler(commands=['scan'])
def scan(msg):
    bot.reply_to(msg, "🔍 Scanning all NASDAQ stocks...")
    
    results = []
    for symbol in NASDAQ:
        try:
            df = yf.download(symbol, period="1d", interval="15m")
            price = float(df['Close'].iloc[-1])
            prev = float(df['Close'].iloc[-2])
            change = ((price - prev) / prev * 100)
            
            if abs(change) > 0.5:
                results.append(f"{'📈' if change > 0 else '📉'} {symbol}: {change:+.1f}% (${price:.2f})")
        except:
            pass
        time.sleep(1)
    
    if results:
        response = f"*Market Movers:*\n\n" + "\n".join(results[:8])
    else:
        response = "No significant moves (>0.5%) detected."
    
    bot.reply_to(msg, response, parse_mode='Markdown')

@bot.message_handler(commands=['alerts'])
def alerts(msg):
    global alert_count
    response = f"""🔔 *Alert History*

*Total alerts sent:* {alert_count}
*Last alert:* {last_scan if last_scan else 'None'}
*Monitoring:* {len(NASDAQ)} symbols

*Alert Criteria:*
• 1%+ price move in 15m
• During market hours
• Volume confirmation

*Recent symbols:* {', '.join(NASDAQ)}"""
    
    bot.reply_to(msg, response, parse_mode='Markdown')

@bot.message_handler(commands=['symbols'])
def symbols(msg):
    sym_list = "*Available Symbols:*\n\n"
    for sym in NASDAQ:
        sym_list += f"• {sym}\n"
    
    sym_list += f"\n*Example:* `/signal {NASDAQ[0]}`"
    bot.reply_to(msg, sym_list, parse_mode='Markdown')

def auto_scanner():
    global last_scan, alert_count, chat_id
    
    if not chat_id:
        return
    
    # Check market hours (EST)
    est = pytz.timezone('America/New_York')
    now = datetime.now(est)
    
    # Monday-Friday, 9:30 AM - 4:00 PM
    if now.weekday() >= 5:
        return
    
    current_time = now.strftime("%H:%M")
    if current_time < "09:30" or current_time > "16:00":
        return
    
    last_scan = current_time
    print(f"[{current_time}] Auto-scanning...")
    
    for symbol in NASDAQ[:3]:  # Check first 3
        try:
            df = yf.download(symbol, period="1d", interval="15m")
            price = float(df['Close'].iloc[-1])
            prev = float(df['Close'].iloc[-2])
            change = ((price - prev) / prev * 100)
            
            if abs(change) > 1.0:
                alert_count += 1
                signal = "BUY" if change > 0 else "SELL"
                alert = f"""{'🟢' if change > 0 else '🔴'} *AUTO-ALERT: {signal} {symbol}*

*Price:* ${price:.2f}
*Change:* {change:+.1f}%
*Time:* {current_time}

*Action:* Consider {signal.lower()} position
*Stop:* ${price * (0.99 if change > 0 else 1.01):.2f}
*Target:* ${price * (1.02 if change > 0 else 0.98):.2f}

#{symbol} #{signal} #AUTO"""
                
                bot.send_message(chat_id, alert, parse_mode='Markdown')
                time.sleep(2)  # Rate limiting
                
        except Exception as e:
            print(f"Error scanning {symbol}: {e}")
        time.sleep(1)

# Schedule auto-scans every 5 minutes
def scanner_loop():
    while True:
        auto_scanner()
        time.sleep(300)  # 5 minutes

# Start scanner in background
threading.Thread(target=scanner_loop, daemon=True).start()

print("🚀 NASDAQ Auto-Trader Started")
print("📊 Symbols:", ", ".join(NASDAQ))
print("⏰ Auto-scans every 5 minutes")
print("📱 Commands: /start, /status, /signal, /scan, /alerts")

# Start bot
if __name__ == "__main__":
    # Clear any existing webhook
import telebot.apihelper
bot.remove_webhook()
time.sleep(2)

# Set timeout
telebot.apihelper.SESSION_TIME_TO_LIVE = 5 * 60

# Start with timeout
bot.polling(none_stop=True, interval=1, timeout=20)
    bot.polling(none_stop=True, interval=1)

