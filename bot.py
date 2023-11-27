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
from schedule import every, repeat, run_pending

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
            if self.cursor.execute('SELECT count(*) FROM users WHERE ID = ?', (id,)).fetchone()[0] >= 1:
                return True

    def add_user(self, id, first_name, last_name, username, tel, lang, bot):
        with self.connection:
            try:
                self.cursor.execute("INSERT INTO users (ID, First_name, Last_name, Username, Telephone, Lang, bot, lastpic) VALUES (?, ?, ?, ?, ?, ?, ?, 0);",
                                    (id, first_name, last_name, username, tel, lang, bot))
            except sqlite3.DatabaseError as error:
                print("Error add_user:", error)

    def random(self):
        with self.connection:
            return self.cursor.execute('SELECT * FROM goddesses ORDER BY RANDOM() LIMIT 1;')

    def all_reg_users(self):
        with self.connection:
            return self.connection.execute('SELECT ID FROM users').fetchall()

    def user_last_pic(self, userid):
        with self.connection:
            return self.cursor.execute('SELECT lastpic FROM users WHERE id = ?', (userid,)).fetchone()[0]

    def check_utc_in_buffer(self, utc):
        with self.connection:
            return self.cursor.execute('SELECT ID FROM goddesses WHERE utc = ?', (utc,)).fetchone()[0]

    def update_last_pic(self, id_from_buffer, userid):
        with self.connection:
            self.cursor.execute('UPDATE users SET lastpic = ? WHERE ID = ?',(id_from_buffer,userid))

# =============================SQL END

def read_js(req):
    data = None
    try:
        data = json.loads(req.text)
    except ValueError:
        print('error in js')
    return data


def check_user_last_pic(utc, userid):
    db_worker = SQLighter(config.database_name)
    last_id = db_worker.user_last_pic(userid)
    id_from_buffer = db_worker.check_utc_in_buffer(utc)
    if last_id < id_from_buffer:
        db_worker.update_last_pic(id_from_buffer, userid)
        posted = 1
    else:
        posted = 0
    db_worker.close()
    return posted


def check_and_add_bd(name, url, utc):
    db_worker = SQLighter(config.database_name)
    if db_worker.checkboobs(utc):
        in_db = 1
    else:
        db_worker.addboobs(name, url, utc)
        db_worker.close()
        print("Added - ", name)
        in_db = 0
    return in_db


def del_amp(text):
    text = text.replace("amp;", "")
    return text


def get_picture(url):
    data_all = []
    all_picture = []
    name = 'No name'
    while len(data_all) < 25:
        time.sleep(2)
        req = requests.get(url, headers={'User-Agent': UserAgent().chrome})
        json_data = read_js(req)
        try:
            if json_data['data']['children'] is not None:
                data_all += json_data['data']['children']
        except KeyError:
            pass
    for k in data_all:
        try:  # перевірка на відео
            if k['data']['preview']['reddit_video_preview']['is_gif']:
                name = del_amp(k['data']['title'])
                url = del_amp(k['data']['preview']['reddit_video_preview']['fallback_url'])
                time_create = k['data']['created_utc']
                check_and_add_bd(name, url, time_create)
                all_picture.append(['v',name,url,time_create])
                # if check_and_add(name, url, time_create, message) == 0:
                #     try:
                #         bot.send_video(message, url)
                #     except Exception:
                #         print("Error parsing video")
        except KeyError:
            try:
                if k['data']['preview']:
                    id = del_amp(k['data']['id'])
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
                    check_and_add_bd(name, url, time_create)
                    all_picture.append(['f',name, url, time_create, id])
                    # if check_and_add(name, url, time_create, message) == 0:
                    #     bot.send_photo(message, url, caption=name)
                else:
                    print('======= ', name)
            except KeyError:
                pass

        try:  # перевірка на галерею (не більше 10)
            if k['data']['is_gallery']:
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
                check_and_add_bd(name, url, time_create)
                all_picture.append(['g', name, images, time_create])
                # if check_and_add(name, url, time_create, message) == 0:
                #     try:
                #         bot.send_media_group(message, images)
                #     except telebot.apihelper.ApiException as e:
                #         if e.result.status_code == 403:
                #             print('Користувач забанив бота')
                #         elif e.result.status_code == 400:
                #             print('Не вийшло загрузить медіа')
        except KeyError:
            pass
    return all_picture

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
                     "/help - для допомоги\n")

@bot.message_handler(commands=['random'])
def rand(message):
    db_worker = SQLighter(config.database_name)
    r = db_worker.random().fetchall()
    #print(r[0][2]) 111
    try:
        bot.send_photo(message.chat.id, r[0][2], r[0][1])
    except:
        pass

@bot.message_handler(commands=['start'])
def start(message):

    db_worker = SQLighter(config.database_name)
    if db_worker.check_user(message.from_user.id):
        try:
            bot.send_message(message.chat.id, "Бот запущено")
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

@bot.message_handler(commands=['test1'])
def goddesses(message):
    url = 'https://www.reddit.com/r/goddesses_2/new/.json'
    v_all_users = all_users()
    new_pic = get_picture(url)
    #print(new_pic)
    for v in v_all_users:
        print(v[0],"===========================Тест Богині 2")
        for p in new_pic:
            if p[0] == 'v':
                if check_user_last_pic(p[3],v[0])==1:
                    try:
                        print(v[0], p[0], p[1])
                        bot.send_video(v[0], p[2])
                    except telebot.apihelper.ApiException as e:
                        if e.result.status_code == 403:
                            print('Користувач забанив бота')
                        elif e.result.status_code == 400:
                            print('Не вийшло загрузить медіа')
            if p[0] == 'f':
                if check_user_last_pic(p[3], v[0])==1:
                    try:
                        print(v[0], p[0], p[1])
                        capt = str("[" + p[1] + "](redd.it/" + p[4]+ ")")
                        bot.send_photo(v[0], p[2], caption=capt, parse_mode='MarkdownV2')
                    except telebot.apihelper.ApiException as e:
                        if e.result.status_code == 403:
                            print('Користувач забанив бота')
                        elif e.result.status_code == 400:
                            print('Не вийшло загрузить медіа')
            if p[0] == 'g':
                if check_user_last_pic(p[3], v[0])==1:
                    try:
                        print(v[0], p[0], p[1])
                        bot.send_media_group(v[0], p[2])
                    except telebot.apihelper.ApiException as e:
                        if e.result.status_code == 403:
                            print('Користувач забанив бота')
                        elif e.result.status_code == 400:
                            print('Не вийшло загрузить медіа')

@bot.message_handler(commands=['test2'])
def goddesses(message):
    url = 'https://www.reddit.com/r/FitNakedGirls/new/.json'
    v_all_users = all_users()
    new_pic = get_picture(url)
    #print(new_pic)
    for v in v_all_users:
        print(v[0],"===========================Test FitNakedGirls")
        for p in new_pic:
            if p[0] == 'v':
                if check_user_last_pic(p[3],v[0])==1:
                    try:
                        print(v[0], p[0], p[1])
                        bot.send_video(v[0], p[2])
                    except telebot.apihelper.ApiException as e:
                        if e.result.status_code == 403:
                            print('Користувач забанив бота')
                        elif e.result.status_code == 400:
                            print('Не вийшло загрузить медіа')
            if p[0] == 'f':
                if check_user_last_pic(p[3], v[0])==1:
                    try:
                        print(v[0], p[0], p[1])
                        capt = str("[" + p[1] + "](redd.it/" + p[4]+ ")")
                        bot.send_photo(v[0], p[2], caption=capt, parse_mode='MarkdownV2')
                    except telebot.apihelper.ApiException as e:
                        if e.result.status_code == 403:
                            print('Користувач забанив бота')
                        elif e.result.status_code == 400:
                            print('Не вийшло загрузить медіа')
            if p[0] == 'g':
                if check_user_last_pic(p[3], v[0])==1:
                    try:
                        print(v[0], p[0], p[1])
                        bot.send_media_group(v[0], p[2])
                    except telebot.apihelper.ApiException as e:
                        if e.result.status_code == 403:
                            print('Користувач забанив бота')
                        elif e.result.status_code == 400:
                            print('Не вийшло загрузить медіа')

# @repeat(every().hour.at(":32"))
def post(url):
    v_all_users = all_users()
    new_pic = get_picture(url)
    #print(new_pic)
    for v in v_all_users:
        print(v[0],"===========================GODDESSES")
        for p in new_pic:
            if p[0] == 'v':
                if check_user_last_pic(p[3],v[0])==1:
                    try:
                        print(v[0], p[0], p[1])
                        bot.send_video(v[0], p[2])
                    except telebot.apihelper.ApiException as e:
                        if e.result.status_code == 403:
                            print('Користувач забанив бота')
                        elif e.result.status_code == 400:
                            print('Не вийшло загрузить медіа')
            if p[0] == 'f':
                if check_user_last_pic(p[3], v[0])==1:
                    try:
                        print(v[0], p[0], p[1])
                        capt = str("[" + p[1] + "](redd.it/" + p[4]+ ")")
                        bot.send_photo(v[0], p[2], caption=capt, parse_mode='MarkdownV2')
                    except telebot.apihelper.ApiException as e:
                        if e.result.status_code == 403:
                            print('Користувач забанив бота')
                        elif e.result.status_code == 400:
                            print('Не вийшло загрузить медіа')
            if p[0] == 'g':
                if check_user_last_pic(p[3], v[0])==1:
                    try:
                        print(v[0], p[0], p[1])
                        bot.send_media_group(v[0], p[2])
                    except telebot.apihelper.ApiException as e:
                        if e.result.status_code == 403:
                            print('Користувач забанив бота')
                        elif e.result.status_code == 400:
                            print('Не вийшло загрузить медіа')



@bot.message_handler(content_types=['contact'])
def contact(message):
    if message.from_user.id == message.contact.user_id:
        print(message.contact)
        print(message.from_user)
        #db_worker = SQLighter(config.database_name)
        #db_worker.add_user(message.contact.user_id, message.contact.first_name, message.contact.last_name,
        #                   message.from_user.username, message.contact.phone_number, message.from_user.language_code,
        #                   message.from_user.is_bot)
        #db_worker.close()
        #keyboard = types.ReplyKeyboardRemove()
        #bot.send_message(message.chat.id, "Зарєстровано! Зачекай, поки адмін додасть тебе до дозволених людей!", reply_markup=keyboard)
    else:
        bot.send_message(message.chat.id, 'Ділитися треба лише СВОЇМИ контактами')

def runBot():
    bot.polling(none_stop=True)

def runScheluders():
    schedule.every().hour.at(":00").do(post, url='https://www.reddit.com/r/adorableporn/new/.json')
    schedule.every().hour.at(":20").do(post, url='https://www.reddit.com/r/goddesses_2/new/.json')
    schedule.every().hour.at(":40").do(post, url='https://www.reddit.com/r/TooCuteForPorn/new/.json')
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == '__main__':
    t1 = threading.Thread(target=runBot)
    t2 = threading.Thread(target=runScheluders)
    t1.start()
    t2.start()
