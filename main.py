import time
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from telebot.types import KeyboardButton, ReplyKeyboardMarkup
import aiohttp
import asyncio
from bs4 import BeautifulSoup
import xlsxwriter
import sqlite3
import os
from config import API_Token

bot = telebot.TeleBot(API_Token)
button1 = InlineKeyboardButton(text="Laptop", callback_data="Laptop")
inline_keyboard = InlineKeyboardMarkup(row_width=1)
inline_keyboard.add(button1)

# data base
conn = sqlite3.connect("scrap_users.db")
cur = conn.cursor()

creat_table_query = """
CREATE TABLE IF NOT EXISTS scrap_users(
    id INTEGER PRIMARY KEY,
    first_name TEXT,
    last_name TEXT,
    phone_number TEXT
);
"""

cur.execute(creat_table_query)
conn.commit()
conn.close()

# get information
button2 = KeyboardButton(text="Send my info", request_contact=True)
button3 = KeyboardButton(text="Test")
keyword = ReplyKeyboardMarkup(one_time_keyboard=False, resize_keyboard=True, row_width=1)
keyword.add(button2, button3)

# button for just test
@bot.message_handler(func=lambda message: message.text == "Test")
def send_laptop(message):
    bot.send_message(message.chat.id,"In this bot we scrap the product from (newegg.com) " + "\n"
                                                                                "you can click on button and test the bot for once" + "\n"
                                                                                "if you want to scrap more product please click on button" + "\n"
                                                                                "(send my info)",
                                                                                reply_markup=inline_keyboard)


# start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(message.chat.id, "Welcome to scrap bot choose your options in keyword button", reply_markup=keyword)

# iformation of user
@bot.message_handler(content_types=["contact"])
def send_contact(message):
    contact = message.contact

    # delet the keyword
    bot.send_message(message.chat.id, "Thank you for sharing your info now you can scrap your product🎉", reply_markup= telebot.types.ReplyKeyboardRemove())

    # insert the data in database
    with sqlite3.connect("scrap_users.db") as conn:
        cur = conn.cursor()
        insert_data_query = """
        INSERT OR IGNORE INTO scrap_users(id, first_name, last_name, phone_number)
        VALUES (?, ?, ?, ?)
        """

        data = (message.contact.user_id,
            f"{message.contact.first_name}",
            f"{message.contact.last_name}",
            f"{message.contact.phone_number}")
        conn.execute(insert_data_query, data)


    # Explain the bot
    bot.send_message(message.chat.id, "Hello " + message.from_user.first_name + "\n"
                                                                                  "in this bot we scrap the product from (newegg.com) "
                                                                                  "what the name of product you want to scrape write it?" + "\n"
                                                                                  "for example: ",
                                                                                   reply_markup=inline_keyboard)
    
# Read data base
# fetch_data_query = """
# SELECT id, first_name, last_name, phone_number FROM scrap_users
# """

# rows = []
# with sqlite3.connect("scrap_users.db") as conn:
#     cur = conn.cursor()
#     cur.execute(fetch_data_query)
#     rows = cur.fetchall()
# for r in rows:
#     print(f"ID: {r[0]}, First Name: {r[1]}, Last Name: {r[2]}, Phone Number: {r[3]}")





# get the name of the product for search from user
search_list = {}

# get search name whit button laptop
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data == "Laptop":
        search_list[call.message.chat.id] = call.data
        bot.answer_callback_query(call.id, text="Laptop scrape start")
        bot.send_message(call.message.chat.id, "Scraping will start after /excel")
    else:
        bot.answer_callback_query(call.id, "write your product you want to scrap")


# get search name whit message of user
@bot.message_handler(func=lambda message: not message.text.startswith('/'))
def search_text(message):
    t = message.text.strip()
    if t:
        search_list[message.chat.id] = t
        bot.reply_to(message, f"The product you want to scrap is: {search_list[message.chat.id]}")
        bot.send_message(message.chat.id, "Laptop scrape start for take your Excel product please write (/excel) ")
    else:
        bot.answer_callback_query(message.id, "Please send a valid product name")


# All Variable
pages = 2

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

# Table
def get_spec(soup, label):
    rows = soup.select(".table-horizontal tr")
    for row in rows:
        th = row.find("th")
        td = row.find("td")
        if th and td and label.lower() in th.text.lower():
            return td.text.strip()
    return ""

# price
def get_price(soup):
    whole = soup.select_one(".price-current strong")
    fraction = soup.select_one(".price-current sup")
    if whole:
        price = whole.text
        if fraction:
            price += fraction.text
        return price.strip()
    return ""

# Product information
async def fetch_product(session, url, worksheet, row_number, lock, sem):
    async with sem:
        async with session.get(url, headers=headers) as response:
            html = await response.text()

    soup = BeautifulSoup(html, "html.parser")

    brand = get_spec(soup, "Brand")
    color = get_spec(soup, "Color")
    cpu = get_spec(soup, "CPU")
    memory = get_spec(soup, "Memory")
    ssd = get_spec(soup, "SSD")
    gpu = get_spec(soup, "Graphics")
    price = get_price(soup)

    async with lock:
        worksheet.write(row_number[0], 0, brand)
        worksheet.write(row_number[0], 1, color)
        worksheet.write(row_number[0], 2, price)
        worksheet.write(row_number[0], 3, cpu)
        worksheet.write(row_number[0], 4, memory)
        worksheet.write(row_number[0], 5, ssd)
        worksheet.write(row_number[0], 6, gpu)

        row_number[0] += 1

# Body
async def main(search, filename):
    sem = asyncio.Semaphore(5)
    lock = asyncio.Lock()
    row_number = [1]


    workbook = xlsxwriter.Workbook(filename)
    worksheet = workbook.add_worksheet()
    worksheet.write(row_number[0], 0, "brand")
    worksheet.write(row_number[0], 1, "color")
    worksheet.write(row_number[0], 2, "price")
    worksheet.write(row_number[0], 3, "cpu")
    worksheet.write(row_number[0], 4, "memory")
    worksheet.write(row_number[0], 5, "ssd")
    worksheet.write(row_number[0], 6, "gpu")


    async with aiohttp.ClientSession() as session:
        number_pages = 1
        while number_pages <= pages:
            url = f"https://www.newegg.com/p/pl?d={search}&page={number_pages}"
            async with session.get(url, headers=headers) as response:
                html = await response.text()

            soup = BeautifulSoup(html, "html.parser")
            links = soup.select("a.item-title")

            tasks = []
            for link in links:
                href = link.get("href")
                if href:
                    tasks.append(fetch_product(session, href, worksheet, row_number, lock, sem))

            await asyncio.gather(*tasks)
            number_pages += 1
    workbook.close()


# send the Excel file for user
@bot.message_handler(commands=["Excel", "excel"])
def send_excel(message):
    chat_id = message.chat.id

    if not search_list:
        bot.reply_to(message, "Please send a valid product name")
        return
    
    if chat_id not in search_list:
        bot.reply_to(message, "Please send a valid product name")

    product_name = search_list.pop(chat_id, None)
    # filename = f"newegg_{chat_id}.xlsx"
    filename = f"newegg.xlsx"


    # Run the scraper
    asyncio.run(main(product_name, filename))
    time.sleep(2)

    # Excel file
    try:
        with open(filename, "rb") as f:
            bot.send_document(message.chat.id, f)

    finally:
        os.remove(filename)

# Run the bot
bot.polling()