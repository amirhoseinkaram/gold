import os
import requests
import yfinance as yf
import asyncio
from telegram import Bot


TOKEN = os.getenv("TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")


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
        data = requests.get(url, headers=headers, timeout=5).json()
        price = data['result']['symbols']['USDTTMN']['stats']['lastPrice']
        return int(float(price)), "Wallex"
    except:
        pass
    try:
        url = "https://api.tetherland.com/currencies"
        data = requests.get(url, headers=headers, timeout=5).json()
        price = data['data']['currencies']['USDT']['price']
        return int(float(price)), "TetherLand"
    except:
        pass
    return None, None

def calculate_18k(ounce, usdt):
    if ounce and usdt:
        try:
            return int((ounce / 31.1035) * usdt * 0.75)
        except:
            return None
    return None

async def send_update():
    if not TOKEN:
        print("Error: No TOKEN provided")
        return

    gold, gold_src = get_gold_price()
    usdt, usdt_src = get_usdt_price()
    gold_18k = calculate_18k(gold, usdt)
    
    msg = "💎 **گزارش لحظه‌ای بازار**\n\n"
    if gold: msg += f"🏆 **انس طلا:** `{gold:,}$`\n   └ 🔗 منبع: _{gold_src}_\n\n"
    if usdt: msg += f"🇺🇸 **تتر:** `{usdt:,} ت`\n   └ 🔗 منبع: _{usdt_src}_\n\n"
    if gold_18k: msg += f"✨ **طلای ۱۸:** `{gold_18k:,} ت`\n   └ 🧮 (هر گرم - بدون اجرت)\n\n"
    
    msg += "🆔 @gold_price_rls "

    if gold or usdt:
        bot = Bot(token=TOKEN)
        await bot.send_message(chat_id=CHANNEL_ID, text=msg, parse_mode='Markdown')
        print("✅ Message sent!")
    else:
        print("❌ Failed to fetch prices.")

if __name__ == '__main__':
    asyncio.run(send_update())

