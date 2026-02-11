import os
import requests
import yfinance as yf
import asyncio
import re
from telegram import Bot
from bs4 import BeautifulSoup

TOKEN = os.getenv("TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

# --- Function to convert Persian numbers to English ---
def clean_number(text):
    if not text:
        return None
    persian_digits = '۰۱۲۳۴۵۶۷۸۹'
    arabic_digits = '٠١٢٣٤٥٦٧٨٩'
    english_digits = '0123456789'
    
    translation = text.maketrans(persian_digits + arabic_digits, english_digits * 2)
    text = text.translate(translation)
    text = re.sub(r'[^\d]', '', text)
    
    try:
        return int(text)
    except:
        return None

# --- Fetch USD and EUR 
def get_alanchand_prices():
    url = "https://alanchand.com/currencies-price"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    
    prices = {'usd': None, 'eur': None}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract USD
        dollar_row = soup.find('tr', attrs={'title': 'قیمت دلار آمریکا'})
        if dollar_row:
            price_tag = dollar_row.find('td', class_='sellPrice')
            if price_tag:
                prices['usd'] = clean_number(price_tag.get_text(strip=True))

        # Extract EUR
        euro_row = soup.find('tr', attrs={'title': 'قیمت یورو'})
        if euro_row:
            price_tag = euro_row.find('td', class_='sellPrice')
            if price_tag:
                prices['eur'] = clean_number(price_tag.get_text(strip=True))
                
    except Exception as e:
        print(f"⚠️ Error fetching alanchand data: {e}")
        
    return prices

# Fetch USDT price
def get_usdt_price():
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        
        url = "https://api.nobitex.ir/v2/orderbook/USDTIRT"
        data = requests.get(url, headers=headers, timeout=5).json()
        price = data['bids'][0][0] 
        return int(float(price) / 10) # Convert Rial to Toman
    except:
        return None

# --- Fetch global gold ounce price ---
def get_gold_price():
    try:
        ticker = yf.Ticker("GC=F")
        price = ticker.fast_info['last_price']
        return round(price, 2)
    except:
        return None

# --- Calculate 18K gold price ---
def calculate_18k(ounce, dollar_price):
   # (ounce / 31.1035) * dollar_price * 0.75
    if ounce and dollar_price:
        try:
            return int((ounce / 31.1035) * dollar_price * 0.75)
        except:
            return None
    return None

async def send_update():
    print("⏳ دریافت قیمت‌ها...")
    
    gold = get_gold_price()       # ounce
    usdt = get_usdt_price()       # USDT
    
    
    fiat_prices = get_alanchand_prices()
    dollar = fiat_prices['usd']
    euro = fiat_prices['eur']
    
    
    # If the dollar price cannot be retrieved, the gold price will not be calculated
    gold_18k = calculate_18k(gold, dollar)
    
    
    msg = "💎 **گزارش لحظه‌ای بازار**\n\n"
    
    if gold: 
        msg += f"🏆 **انس طلا:** `{gold:,}$`\n\n"
        
    if dollar: 
        msg += f"💵 **دلار آمریکا:** `{dollar:,} تومان`\n\n"
        
    if euro: 
        msg += f"💶 **یورو:** `{euro:,} تومان`\n\n"
        
    if usdt: 
        msg += f"🇺🇸 **تتر:** `{usdt:,} تومان`\n\n"
        
    if gold_18k: 
        msg += f"✨ **طلای ۱۸:** `{gold_18k:,} تومان`\n   └ 🧮 (محاسبه با دلار - بدون اجرت)\n\n"
    
    msg += "🆔 @goldpricerls"

  
    if not TOKEN or not CHANNEL_ID:
        print("\n" + "="*40)
        print("🛑 LOCAL TEST OUTPUT")
        print("-" * 20)
        print(msg)
        print("="*40 + "\n")
    elif gold or usdt or dollar:
        try:
            bot = Bot(token=TOKEN)
            await bot.send_message(chat_id=CHANNEL_ID, text=msg, parse_mode='Markdown')
            print("✅ Sent to Telegram.")
        except Exception as e:
            print(f"❌ Telegram Error: {e}")
    else:
        print("❌ All sources failed.")

if __name__ == '__main__':
    asyncio.run(send_update())
