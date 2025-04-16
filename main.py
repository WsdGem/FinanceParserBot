import telebot
from dotenv import load_dotenv
import os
from pdfminer.high_level import extract_text
import re
import gspread
from oauth2client.service_account import ServiceAccountCredentials

load_dotenv()

# Инициализация бота
TOKEN = os.getenv("TELEGRAM_API_KEY")
bot = telebot.TeleBot(TOKEN)



# Настройка Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("D:/Project/FinanceParserBot-main/financeparserbot-a1f01b2f9806.json", scope)
client = gspread.authorize(creds)
sheet = client.open("PDF Data").sheet1

print("Бот запущен")

def extract_field(pattern, text, default=""):
    match = re.search(pattern, text, re.MULTILINE)
    return match.group(1).strip() if match else default

def extract_payer(text):
    match = re.search(r"((?:ООО|ИП|ПАО|АО|Общество с ограниченной ответственностью|ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ|ФИЛИАЛ)\s+[\w\s\"«»\-]+)\s*Плательщик", text)
    return match.group(1).strip() if match else ""

def extract_recipient(text):
    match = re.search(r"((?:ООО|ИП|ПАО|АО|Общество с ограниченной ответственностью|ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ|ФИЛИАЛ)\s+[\w\s\"«»\-]+)\s*Получатель", text)
    return match.group(1).strip() if match else ""

def parse_pdf(pdf_path):
    print(f"Обработка PDF: {pdf_path}")
    text = extract_text(pdf_path)
    
    data = {
        "Плательщик": extract_payer(text),
        "Получатель": extract_recipient(text),
        "Дата": extract_field(r"(\d{2}\.\d{2}\.\d{4})", text),
        "ИНН плательщика": extract_field(r"ИНН\s*(\d{10})", text),
        "ИНН получателя": extract_field(r"ИНН\s*(\d{10})", text, default=""),
        "Сумма": extract_field(r"Сумма\s*(\d+-\d{2})", text),
        "Статус платежа": extract_field(r"(ИСПОЛНЕНО|Исполнен|ПРОВЕДЕНО)", text)
    }
    print("Данные извлечены:", data)
    return text, data

def ensure_headers():
    headers = ["Плательщик", "Получатель", "Дата", "ИНН плательщика", "ИНН получателя", "Сумма", "Статус платежа"]
    existing_headers = sheet.row_values(1)
    if existing_headers != headers:
        sheet.insert_row(headers, 1)

def save_to_google_sheets(data):
    ensure_headers()
    sheet.append_row(list(data.values()))

@bot.message_handler(content_types=['document'])
def handle_document(message):
    print("Получен документ от пользователя")
    file_info = bot.get_file(message.document.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    
    with open("uploaded_file.pdf", "wb") as file:
        file.write(downloaded_file)
    print("Файл загружен")
    
    text, data = parse_pdf("uploaded_file.pdf")
    save_to_google_sheets(data)
    bot.reply_to(message, "Данные успешно добавлены в Google Таблицу.")

@bot.message_handler(commands=['all'])
def send_full_text(message):
    try:
        print("Запрошен полный текст PDF")
        with open("uploaded_file.pdf", "rb") as file:
            text = extract_text("uploaded_file.pdf")
        
        if len(text) > 4096:
            for chunk in [text[i:i+4096] for i in range(0, len(text), 4096)]:
                bot.send_message(message.chat.id, chunk)
        else:
            bot.send_message(message.chat.id, text)
        print("Полный текст отправлен пользователю")
    except Exception as e:
        bot.reply_to(message, "Нет загруженного PDF-файла или ошибка при обработке.")
        print("Ошибка при обработке PDF:", e)

bot.polling()
