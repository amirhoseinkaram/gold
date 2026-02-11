import os
import requests
import yfinance as yf
import asyncio
import re
from bs4 import BeautifulSoup

# دریافت توکن‌ها از محیط گیت‌هاب
TOKEN = os.getenv("TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

# --- تابع تبدیل اعداد فارسی به انگلیسی ---
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

# --- دریافت قیمت دلار و یورو از الان‌چند ---
def get_alanchand_prices():
    url = "https://alanchand.com/currencies-price"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    prices = {'usd': None, 'eur': None}
    try:
        # تایم‌اوت رو ۱۵ ثانیه گذاشتم که اگر سایت کند بود ارور نده
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. استخراج دلار
        dollar_row = soup.find('tr', attrs={'title': 'قیمت دلار آمریکا'})
        if dollar_row:
            price_tag = dollar_row.find('td', class_='sellPrice')
            if price_tag:
                prices['usd'] = clean_number(price_tag.get_text(strip=True))

        # 2. استخراج یورو
        euro_row = soup.find('tr', attrs={'title': 'قیمت یورو'})
        if euro_row:
            price_tag = euro_row.find('td', class_='sellPrice')
            if price_tag:
                prices['eur'] = clean_number(price_tag.get_text(strip=True))
    except Exception as e:
        print(f"⚠️ Error fetching alanchand data: {e}")
    return prices

# --- دریافت تتر (روش اصلاح شده شما: والکس -> تترلند) ---
def get_usdt_price():
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    # تلاش اول: والکس
    try:
        url = "https://api.wallex.ir/v1/markets"
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            price = data['result']['symbols']['USDTTMN']['stats']['lastPrice']
            return int(float(price)), "Wallex"
    except:
        pass
    
    # تلاش دوم: تترلند
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

# --- دریافت انس طلا (Yahoo Finance) ---
def get_gold_price():
    try:
        ticker = yf.Ticker("GC=F")
        price = ticker.fast_info['last_price']
        return round(price, 2)
    except:
        return None

# --- محاسبه قیمت طلای ۱۸ عیار ---
def calculate_18k(ounce, dollar_price):
    # فرمول: (انس / 31.1035) * دلار * 0.75
    if ounce and dollar_price:
        try:
            return int((ounce / 31.1035) * dollar_price * 0.75)
        except:
            return None
    return None

# --- تابع ارسال پیام به تلگرام (سبک و سریع با requests) ---
def send_telegram_message(msg):
    if not TOKEN or not CHANNEL_ID:
        print("🛑 No Token/Channel ID found.")
        return

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        'chat_id': CHANNEL_ID,
        'text': msg,
        'parse_mode': 'Markdown' # برای بولد کردن با *ستاره*
    }
    
    try:
        # تایم‌اوت ۳۰ ثانیه برای جلوگیری از ارور Timed out
        response = requests.post(url, data=payload, timeout=30)
        
        if response.status_code == 200:
            print("✅ Sent to Telegram successfully!")
        else:
            print(f"❌ Telegram Error: {response.text}")
    except Exception as e:
        print(f"❌ Telegram Connection Error: {e}")

async def send_update():
    print("⏳ دریافت قیمت‌ها...")
    
    gold = get_gold_price()
    
    # اینجا چون تتر خروجی تاپل (قیمت، منبع) میده، بازش میکنیم
    usdt_data = get_usdt_price()
    usdt = usdt_data[0] if usdt_data else None
    # usdt_source = usdt_data[1] if usdt_data else None # اگه خواستی منبع رو چاپ کنی
    
    fiat_prices = get_alanchand_prices()
    dollar = fiat_prices['usd']
    euro = fiat_prices['eur']
    
    # محاسبه طلا (فقط با دلار آمریکا)
    gold_18k = calculate_18k(gold, dollar)
    
    # --- ساخت پیام ---
    # نکته: در حالت Markdown معمولی تلگرام، بولد کردن با *متن* انجام میشه نه **متن**
    msg = "💎 *گزارش لحظه‌ای بازار*\n\n"
    
    if gold: msg += f"🏆 *انس طلا:* `{gold:,}$`\n\n"
    if dollar: msg += f"💵 *دلار آمریکا:* `{dollar:,} تومان`\n\n"
    if euro: msg += f"💶 *یورو:* `{euro:,} تومان`\n\n"
    if usdt: msg += f"🇺🇸 *تتر:* `{usdt:,} تومان`\n\n"
    if gold_18k: msg += f"✨ *طلای ۱۸:* `{gold_18k:,} تومان`\n   └ 🧮 (محاسبه با دلار - بدون اجرت)\n\n"
    
    msg += "🆔 @goldpricerls"

    # --- لاجیک ارسال یا تست ---
    if not TOKEN or not CHANNEL_ID:
        print("\n" + "="*40 + "\n🛑 LOCAL TEST OUTPUT\n" + "-" * 20)
        print(msg)
        print("="*40 + "\n")
    elif gold or usdt or dollar:
        send_telegram_message(msg)
    else:
        print("❌ All sources failed.")

if __name__ == '__main__':
    asyncio.run(send_update())
