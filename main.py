from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import os

def get_tehran_time():
    tehran_tz = pytz.timezone('Asia/Tehran')
    return datetime.now(tehran_tz).strftime("%Y-%m-%d %H:%M:%S")

class CarPriceBot:
    def __init__(self, token):
        self.token = token
        self.app = ApplicationBuilder().token(token).build()
        self.setup_handlers()
        
    def setup_handlers(self):
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("prices", self.show_prices))
        self.app.add_handler(CommandHandler("help", self.help))
        self.app.add_handler(CallbackQueryHandler(self.button_handler))
    
    def get_car_prices(self):
        try:
            print("در حال دریافت اطلاعات...")
            url = "https://mashinbank.com/%D9%82%DB%8C%D9%85%D8%AA-%D8%AE%D9%88%D8%AF%D8%B1%D9%88"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'fa-IR,fa;q=0.9,en-US;q=0.8,en;q=0.7',
                'Connection': 'keep-alive',
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            cars_data = []
            car_items = soup.select('.car-price-list .car-price-item')
            
            for item in car_items:
                try:
                    title = item.select_one('.car-name').text.strip()
                    price = item.select_one('.car-price').text.strip()
                    year = item.select_one('.car-year').text.strip() if item.select_one('.car-year') else '1402'
                    
                    cars_data.append({
                        'title': title,
                        'year': year,
                        'price': price,
                        'update_time': get_tehran_time()
                    })
                except Exception as e:
                    print(f"خطا در پردازش خودرو: {e}")
                    continue
            
            return cars_data
            
        except Exception as e:
            print(f"خطای کلی: {e}")
            return []

    def create_keyboard(self, current_page: int, total_pages: int):
        keyboard = []
        row = []
        
        if current_page > 0:
            row.append(InlineKeyboardButton("⬅️ قبلی", callback_data=f"page_{current_page-1}"))
        
        if current_page < total_pages - 1:
            row.append(InlineKeyboardButton("بعدی ➡️", callback_data=f"page_{current_page+1}"))
        
        if row:
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton("🔄 بروزرسانی", callback_data="refresh")])
        return InlineKeyboardMarkup(keyboard)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "🚗 به ربات قیمت خودرو خوش آمدید!\n\n"
            "این ربات قیمت‌های به‌روز خودرو را از سایت mashinbank.com دریافت می‌کند.\n\n"
            "برای دیدن لیست قیمت‌ها از دستور /prices استفاده کنید."
        )

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "راهنمای استفاده از ربات:\n\n"
            "🔹 /start - شروع کار با ربات\n"
            "🔹 /prices - نمایش لیست قیمت خودروها\n"
            "🔹 /help - نمایش این راهنما\n\n"
            "〽️ نکات:\n"
            "• قیمت‌ها به صورت لحظه‌ای به‌روز می‌شوند\n"
            "• برای مشاهده قیمت‌های جدید روی دکمه 🔄 بروزرسانی کلیک کنید"
        )

    async def show_prices(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        message = await update.message.reply_text("در حال دریافت اطلاعات... لطفاً صبر کنید.")
        
        cars_data = self.get_car_prices()
        if not cars_data:
            await message.edit_text(
                "⚠️ متأسفانه در دریافت اطلاعات مشکلی پیش آمده است.\n"
                "لطفاً چند دقیقه دیگر مجدداً تلاش کنید."
            )
            return
        
        context.user_data['cars_data'] = cars_data
        
        items_per_page = 5
        total_pages = (len(cars_data) + items_per_page - 1) // items_per_page
        
        content = []
        for car in cars_data[:items_per_page]:
            content.append(
                f"🚗 {car['title']}\n"
                f"📅 مدل {car['year']}\n"
                f"💰 قیمت: {car['price']}\n"
                f"🕒 {car['update_time']}\n"
                f"{'─' * 30}\n"
            )
        
        await message.edit_text(
            f"📊 لیست قیمت خودروها\n\n{''.join(content)}\n"
            f"📄 صفحه 1 از {total_pages}\n"
            f"🌐 منبع: mashinbank.com",
            reply_markup=self.create_keyboard(0, total_pages)
        )

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        if query.data == "refresh":
            await query.message.edit_text("در حال بروزرسانی اطلاعات... لطفاً صبر کنید.")
            cars_data = self.get_car_prices()
            if not cars_data:
                await query.message.edit_text(
                    "⚠️ متأسفانه در دریافت اطلاعات مشکلی پیش آمده است.\n"
                    "لطفاً چند دقیقه دیگر مجدداً تلاش کنید."
                )
                return
            
            context.user_data['cars_data'] = cars_data
            page = 0
        else:
            page = int(query.data.split('_')[1])
            cars_data = context.user_data.get('cars_data', [])
        
        items_per_page = 5
        total_pages = (len(cars_data) + items_per_page - 1) // items_per_page
        start_idx = page * items_per_page
        end_idx = start_idx + items_per_page
        
        content = []
        for car in cars_data[start_idx:end_idx]:
            content.append(
                f"🚗 {car['title']}\n"
                f"📅 مدل {car['year']}\n"
                f"💰 قیمت: {car['price']}\n"
                f"🕒 {car['update_time']}\n"
                f"{'─' * 30}\n"
            )
        
        await query.message.edit_text(
            f"📊 لیست قیمت خودروها\n\n{''.join(content)}\n"
            f"📄 صفحه {page + 1} از {total_pages}\n"
            f"🌐 منبع: mashinbank.com",
            reply_markup=self.create_keyboard(page, total_pages)
        )

    def run(self):
        print("Bot is starting...")
        self.app.run_polling()

if __name__ == '__main__':
    TOKEN = os.environ.get('BOT_TOKEN', '7984845167:AAGBD1cPGcx-IXUQ1Py5O1_R7Cy6o-7JEDc')
    bot = CarPriceBot(TOKEN)
    bot.run()
