import logging
import requests
import yfinance as yf
import os  
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler



TOKEN = os.getenv("TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
CHECK_INTERVAL = 600


logging.basicConfig(level=logging.INFO)


app = Flask('')

@app.route('/')
def home():
    return "I am alive! Robot is running..."

def run_http():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_http)
    t.start()


def get_gold_price():
    try:
        ticker = yf.Ticker("GC=F")
        price = ticker.fast_info['last_price']
        return round(price, 2), "Yahoo Finance"
    except:
        return None, None

def get_usdt_price():
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        url = "https://api.wallex.ir/v1/markets"
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            price = data['result']['symbols']['USDTTMN']['stats']['lastPrice']
            return int(float(price)), "Wallex"
    except:
        pass
    try:
        url = "https://api.tetherland.com/currencies"
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            price = data['data']['currencies']['USDT']['price']
            return int(float(price)), "TetherLand"
    except:
        pass
    return None, None

def calculate_18k(ounce, usdt):
    if ounce and usdt:
        try:
            gram_24k_usd = ounce / 31.1035
            gram_24k_toman = gram_24k_usd * usdt
            gram_18k = gram_24k_toman * 0.75
            return int(gram_18k)
        except:
            return None
    return None

def create_message():
    gold, gold_source = get_gold_price()
    usdt, usdt_source = get_usdt_price()
    gold_18k = calculate_18k(gold, usdt)
    
    msg = "💎 **گزارش لحظه‌ای بازار**\n\n"
    if gold:
        msg += f"🏆 **انس طلا:** `{gold:,}$`\n   └ 🔗 منبع: _{gold_source}_\n\n"
    else:
        msg += "🏆 انس طلا: ❌ خطا\n\n"
    if usdt:
        msg += f"🇺🇸 **تتر (USDT):** `{usdt:,} ت`\n   └ 🔗 منبع: _{usdt_source}_\n\n"
    else:
        msg += "🇺🇸 تتر: ❌ خطا\n\n"
    if gold_18k:
        msg += f"✨ **طلای ۱۸ عیار:** `{gold_18k:,} ت`\n   └ 🧮 (هر گرم - بدون اجرت)\n\n"
    
    msg += f"🆔 {CHANNEL_ID}"
    
    if gold or usdt:
        return msg
    return None


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    welcome_text = (
        f"سلام {user.first_name} عزیز! 👋\n\n"
        "🤖 من ربات هوشمند اعلام نرخ طلا و ارز هستم.\n"
        f"⏰ بروزرسانی خودکار هر ۱۰ دقیقه در کانال:\n{CHANNEL_ID}"
    )
    await update.message.reply_text(welcome_text)

async def manual_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    wait_msg = await update.message.reply_text("⏳ ...")
    text = create_message()
    if text:
        await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=wait_msg.message_id, text=text, parse_mode='Markdown')
    else:
        await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=wait_msg.message_id, text="❌ خطا")

async def auto_post(context: ContextTypes.DEFAULT_TYPE):
    text = create_message()
    if text:
        try:
            await context.bot.send_message(chat_id=CHANNEL_ID, text=text, parse_mode='Markdown')
        except Exception as e:
            print(f"TeleErr: {e}")

if __name__ == '__main__':
    keep_alive()
    
    if not TOKEN or not CHANNEL_ID:
        print("Error: TOKEN or CHANNEL_ID is missing!")
    else:
        app_bot = ApplicationBuilder().token(TOKEN).build()
        app_bot.add_handler(CommandHandler('start', start_command))
        app_bot.add_handler(CommandHandler('price', manual_price))
        job_queue = app_bot.job_queue
        job_queue.run_repeating(auto_post, interval=CHECK_INTERVAL, first=10)
        app_bot.run_polling()