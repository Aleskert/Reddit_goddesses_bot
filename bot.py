# ==============================
#                   >pip list
# Package            Version
# ------------------ ---------
# certifi            2021.5.30
# charset-normalizer 2.0.4
# fake-useragent     0.1.11
# idna               3.2
# Pillow             8.3.2
# pip                21.2.4
# pyTelegramBotAPI   4.0.0
# requests           2.26.0
# schedule           1.1.0
# setuptools         57.4.0
# urllib3            1.26.6

import time  # бібліотека для роботи з часом
import json  # робота з json
import config  # import config.py
import sqlite3
import telebot  # import telebot library
import requests
import logging
from fake_useragent import UserAgent
from telebot import types
import threading
import schedule

# from PIL import Image

bot = telebot.TeleBot(config.token)  # create new bot


# =============================SQL START
class SQLighter:
    def __init__(self, database):
        self.connection = sqlite3.connect(database)
        self.cursor = self.connection.cursor()

    def close(self):
        self.connection.close()

    def addboobs(self, name, url, utc):
        with self.connection:
            try:
                self.cursor.execute("INSERT INTO goddesses (name, url, utc) VALUES (?, ?, ?);", (name, url, utc))
            except sqlite3.DatabaseError as error:
                print("Error:", error)

    def checkboobs(self, utc):
        with self.connection:
            isboobs = self.cursor.execute('SELECT count(*) FROM goddesses WHERE utc = ?', (utc,)).fetchone()[0]
            if isboobs > 0 :
                return True

    def check_user(self, id):
        with self.connection:
            if self.cursor.execute('SELECT count(*) FROM users WHERE ID = ?', (id,)).fetchone()[0] == 1:
                return True

    def add_user(self, id, first_name, last_name, username, tel, lang, bot):
        with self.connection:
            try:
                self.cursor.execute("INSERT INTO users (ID, First_name, Last_name, Username, Telephone, Lang, bot) VALUES (?, ?, ?, ?, ?, ?, ?);",
                                    (id, first_name, last_name, username, tel, lang, bot))
            except sqlite3.DatabaseError as error:
                print("Error add_user:", error)

    def all_reg_users(self):
        with self.connection:
            return self.connection.execute('SELECT ID FROM users').fetchall()

    def user_last_pic(self, userid):
        with self.connection:
            return self.cursor.execute('SELECT lastpic FROM users WHERE id = ?', (userid,)).fetchone()[0]

    def update_last_pic(self, utc, userid):
        with self.connection:
            self.cursor.execute('UPDATE users SET lastpic = ? WHERE ID = ?',(utc,userid))

# =============================SQL END

def read_js(req):
    data = None
    try:
        data = json.loads(req.text)
    except ValueError:
        print('error in js')
    return data


def check_and_add(name, url, utc, userid):
    db_worker = SQLighter(config.database_name)
    if db_worker.checkboobs(utc):
        if db_worker.user_last_pic(userid) < utc:
            print(" + ", end=" | ")
            print(name)
            db_worker.update_last_pic(utc, userid)
            posted = 0
        else:
            print("   ", end=" | ")
            print(name)
            posted = 1
        db_worker.close()
    else:
        db_worker.addboobs(name, url, utc)
        db_worker.close()
        posted = 0
        print(" + ", end=" | ")
        print(name)
    return posted


def del_amp(text):
    text = text.replace("amp;", "")
    return text


def get_picture(url, message):
    data_all = []
    name = 'No name'
    while len(data_all) < 25:
        time.sleep(2)
        req = requests.get(url, headers={'User-Agent': UserAgent().chrome})
        json_data = read_js(req)
        data_all += json_data['data']['children']
    for k in data_all:
        try:  # перевірка на відео
            if k['data']['preview']['reddit_video_preview']['is_gif']:
                print("Video  ", end=" | ")
                name = del_amp(k['data']['title'])
                url = del_amp(k['data']['preview']['reddit_video_preview']['fallback_url'])
                time_create = k['data']['created_utc']
                if check_and_add(name, url, time_create, message) == 0:
                    try:
                        bot.send_video(message, url)
                    except Exception:
                        print("Error parsing video")
        except KeyError:
            try:
                if k['data']['preview']:
                    print("Images ", end=" | ")
                    name = del_amp(k['data']['title'])
                    time_create = k['data']['created_utc']
                    try:  # пробуємо запостити 3 резолюцію
                        url = del_amp(k['data']['preview']['images'][0]['resolutions'][3]['url'])
                    except IndexError:
                        try:  # пробуємо запостити 2 резолюцію
                            url = del_amp(k['data']['preview']['images'][0]['resolutions'][2]['url'])
                        except IndexError:
                            try:  # пробуємо запостити 1 резолюцію
                                url = del_amp(k['data']['preview']['images'][0]['resolutions'][1]['url'])
                            except Exception:
                                print("Ніхуя не вдалося, певно відсутні дані")
                    if check_and_add(name, url, time_create, message) == 0:
                        bot.send_photo(message, url, caption=name)
                else:
                    print('======= ', name)
            except KeyError:
                pass

        try:  # перевірка на галерею (не більше 10)
            if k['data']['is_gallery']:
                print("Gallery", end=" | ")
                images = []
                sql_url = ""
                i = 0
                for l in k['data']['media_metadata']:
                    i += 1
                    if i > 10:  # Не більше 10 картинок в галереї
                        break
                    url = del_amp(k['data']['media_metadata'][l]['s']['u'])
                    name = del_amp(k['data']['title'])
                    images += [types.InputMediaPhoto(url, name)]
                    sql_url += str(url) + ','
                time_create = k['data']['created_utc']
                if check_and_add(name, url, time_create, message) == 0:
                    try:
                        bot.send_media_group(message, images)
                    except telebot.apihelper.ApiException as e:
                        if e.result.status_code == 403:
                            print('Користувач забанив бота')
                        elif e.result.status_code == 400:
                            print('Не вийшло загрузить медіа')
        except KeyError:
            pass

def all_users():
    db_worker = SQLighter(config.database_name)
    v_all_users = db_worker.all_reg_users()
    db_worker.close()
    return v_all_users

@bot.message_handler(content_types=['document', 'audio'])
def handle_docs_audio(message):
    bot.send_message(message.chat.id, "Файли бот не сприймає")


@bot.message_handler(commands=['help'])
def open_help(message):
    bot.send_message(message.chat.id,
                     "/start - для початку роботи надішліть команду\n"
                     "/help - для допомоги\n"
                     "/goddesses - бот парсить богинь\n"
                     "/nsfw - бот парсить еротику")


@bot.message_handler(commands=['start'])
def start(message):

    db_worker = SQLighter(config.database_name)
    if db_worker.check_user(message.from_user.id):
        try:
            bot.send_message(message.chat.id, "Бот запущено")
            # get_picture(url, message)
        except telebot.apihelper.ApiException as e:
            if e.result.status_code == 403:
                print('Користувач забанив бота')
            elif e.result.status_code == 400:
                print('Не вийшло загрузить медіа')
    else:
        keyboard = types.ReplyKeyboardMarkup(row_width=1, one_time_keyboard=True, resize_keyboard=True)
        button_phone = types.KeyboardButton(request_contact=True, text="Надіслати свої дані")
        keyboard.add(button_phone)
        bot.send_message(message.chat.id, 'Ти не зареєстрований. Зареєструйся!', reply_markup=keyboard)
    db_worker.close()

# @bot.message_handler(commands=['goddesses'])
def goddesses():
    url = 'https://www.reddit.com/r/goddesses/new/.json'
    v_all_users = all_users()
    for v in v_all_users:
        print(v[0],"===========================GODDESSES")
        get_picture(url, v[0])

def nsfw():
    url = 'https://www.reddit.com/r/nsfw/new/.json'
    v_all_users = all_users()
    for v in v_all_users:
        print(v[0], "===========================NSFW")
        get_picture(url, v[0])


@bot.message_handler(content_types=['contact'])
def contact(message):
    if message.from_user.id == message.contact.user_id:
        print(message.contact)
        print(message.from_user)
        db_worker = SQLighter(config.database_name)
        db_worker.add_user(message.contact.user_id, message.contact.first_name, message.contact.last_name,
                           message.from_user.username, message.contact.phone_number, message.from_user.language_code,
                           message.from_user.is_bot)
        db_worker.close()
        keyboard = types.ReplyKeyboardRemove()
        bot.send_message(message.chat.id, "Зарєстровано! Зачекай, поки адмін додасть тебе до дозволених людей!", reply_markup=keyboard)
    else:
        bot.send_message(message.chat.id, 'Ділитися треба лише СВОЇМИ контактами')

def runBot():
    bot.polling(none_stop=True)

def runScheluders():
    schedule.every().hour.at(":26").do(goddesses)
    schedule.every().hour.at(":42").do(nsfw)
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == '__main__':
    t1 = threading.Thread(target=runBot)
    t2 = threading.Thread(target=runScheluders)
    t1.start()
    t2.start()
