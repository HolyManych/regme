import os
import re
import time
import json
import config # custom
import random
import telebot
import pymongo
import requests
import threading
from enum import Enum
from lxml import html
from telebot import types
from datetime import datetime
from flask import Flask, request


class DataBase:
    def __init__(self):
        client = pymongo.MongoClient(config.mongourl, connectTimeoutMS=30000)
        self.dbf = client.get_database("fortnite_regme")

    def pushPlayer(self, chatid, nick, wr):
        record = {
            "_id": chatid,
            "fortnite_name": nick,
            "wr": wr,
            "status": 0
        }
        self.dbf.users_telegram.insert_one(record)

    def getUsers(self):
        return self.dbf.users_telegram

    def checkAdmin(self, chat_id):
        return self.dbf.admins.find({"_id": chat_id}).count() == 1

    def checkPlayer(self, nick):
        return self.dbf.users_telegram.find({"fortnite_name": nick}).count() == 1

    def checkChatId(self, chatid):
        return self.dbf.users_telegram.find({"_id": chatid}).count() == 1

    def setStatus(self, chatid):
        self.dbf.users_telegram.update({"_id": chatid}, {"$set":{"status":1 }})



class OutMode(Enum):
    ADMIN  = 1
    ALL    = 2
    IGNORE = 3


db = DataBase()
bot = telebot.TeleBot(config.token)
server = Flask(__name__)
lock1 = threading.Lock()


@bot.message_handler(commands=["start", "help"])
def start_help(message):
    func_list = [
        {name: "start",    mode: OutMode.IGNORE, descr: "no description"},
        {name: "help",     mode: OutMode.ALL,    descr: "вывести все доступные команды"},
        {name: "addme",    mode: OutMode.ALL,    descr: "добавиться в подборку игроков"},
        {name: "chatid",   mode: OutMode.ALL,    descr: "узнать свой chat-id"},
        {name: "checkme",  mode: OutMode.ALL,    descr: "проверить свое место в списке зарегистрировавшихся участников"},
        {name: "status",   mode: OutMode.ADMIN,  descr: "no description"},
        {name: "getcount", mode: OutMode.ALL,    descr: "узнать количество зарегистрировавшихся"},
        {name: "delme",    mode: OutMode.ALL,    descr: "удалить себя из списка"},
    ]
    chat_id = message.chat.id
    isAdm = db.checkAdmin(chat_id)
    for func in func_list:
        if OutMode.IGNORE == func.mode: continue
        if OutMode.ADMIN == func.mode and not isAdm: continue
        bot.send_message(chat_id, "/{} -- {}".format(func.name, func.descr))

"""
2018-02-25T16:57:48.896211+00:00 app[web.1]:  * Running on http://0.0.0.0:52838/ (Press CTRL+C to quit)
2018-02-25T16:57:52.447121+00:00 app[web.1]: 10.99.40.4 - - [25/Feb/2018 16:57:52] "POST /468930047:AAFMt1a45Wl7W9NbjK5E_zlnJ6VAA0nZ-vE HTTP/1.1" 200 -
2018-02-25T16:57:52.447953+00:00 app[web.1]: addme>> chat_id = 337968852
2018-02-25T16:57:52.449127+00:00 app[web.1]: 2018-02-25 16:57:52,448 (util.py:64 WorkerThread1) ERROR - TeleBot: "TypeError occurred, args=("checkChatId() missing 1 required positional argument: 'chatid'",)
2018-02-25T16:57:52.449131+00:00 app[web.1]: Traceback (most recent call last):
2018-02-25T16:57:52.449134+00:00 app[web.1]:   File "/app/.heroku/python/lib/python3.6/site-packages/telebot/util.py", line 58, in run
2018-02-25T16:57:52.449136+00:00 app[web.1]:     task(*args, **kwargs)
2018-02-25T16:57:52.449137+00:00 app[web.1]:   File "bot.py", line 98, in addme
2018-02-25T16:57:52.449139+00:00 app[web.1]:     if not db.checkChatId(chat_id):
2018-02-25T16:57:52.449141+00:00 app[web.1]: TypeError: checkChatId() missing 1 required positional argument: 'chatid'
2018-02-25T16:57:52.449732+00:00 app[web.1]: "
"""


@bot.message_handler(commands=["addme"])
def addme(message):
    chat_id = message.chat.id
    print("addme>> chat_id =", chat_id)
    if not db.checkChatId(chat_id):
        sent = bot.send_message(chat_id, 'Напиши свой ник в Fortnite без кавычек, скобок и прочего')
        bot.register_next_step_handler(sent, check)
    else:
        bot.send_message(chat_id, "Ты уже присутствуешь в списке")
        bot.send_message(chat_id, "Ты можешь удалить себя из списка с помошью команды /del")

def check(message):

    bot.send_message(message.chat.id, "Проверяю, подожди. Это может занять некоторое время.  ⌛")
    lock = threading.Lock()
    name = message.text
    name = name.lower()
    name = name.strip()
    if not db.checkPlayer(name):
        lock.acquire()
        try:
            #DEBUG Проверка на частоту запросов
            #TODO запись этого в db.logs
            cur_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
            print("Last request in [{0}]".format(cur_time))
            r = requests.get(config.urlbase + name, headers=config.header)
            data = json.loads(r.text)
            if "stats" in data:
                if "winRatio" not in data["stats"]["p2"]:
                    bot.send_message(message.chat.id, "У тебя нет побед. Возвращайся, когда выиграешь.")
                else:
                    wr = data["stats"]["p2"]["winRatio"]["value"]
                    bot.send_message(message.chat.id, "Твой WinRate" + " - " + str(wr))
                    #TODO: get 10 from config.lowest_winrate
                    if float(wr) < config.FortniteParam.lowest_winrate:
                        bot.send_message(message.chat.id, "Твой WinRate слишком низок, но я все равно помещу тебя в конец списка")
                    else:
                        bot.send_message(message.chat.id, "Ты помещен(а) в список")
                    db.pushPlayer(message.chat.id, name, wr)
            else:
                bot.send_message(message.chat.id, "Не удалось найти такой ник")
        except Exception as e:
            print("check>> Exception:" + str(e))
            bot.send_message(message.chat.id, "Что-то пошло не так, попробуй позже")
        time.sleep(2)
        lock.release()
    else:
        bot.send_message(message.chat.id, "Такой ник уже есть среди участников. Если ты точно ввел(а) свой ник, то напиши ему:")
        bot.send_contact(message.chat.id, "+79995361024", "Roman")

@bot.message_handler(commands=["chatid"])
def chatid(message):
    bot.send_message(message.chat.id, "Its your chatid: " + str(message.chat.id))

@bot.message_handler(commands=["checkme"])
def checkme(message):
    users = db.getUsers()
    #isAdm = db.admins.find({"chat_id": chat_id}).count() == 1
    if db.checkChatId(message.chat.id):
        for i, user in enumerate(users.find().sort('wr', pymongo.DESCENDING)):
            if user["_id"] == message.chat.id:
                bot.send_message(message.chat.id, "Твое место в списке - " + str(i+1))
                return
    else:
        bot.send_message(message.chat.id, "Тебя нет в списке. Воспользуйся командой /add")


@bot.message_handler(commands=["status"])
def any_msg(message):
    #TODO: check duplicate answer yes/no
    if not db.checkAdmin(message.chat.id):
        bot.send_message(message.chat.id, "Ты не администратор")
        return
    keyboard = types.InlineKeyboardMarkup()
    yesButton = types.InlineKeyboardButton(text="✅  Да, порву всех  ☠", callback_data="yes")
    noButton = types.InlineKeyboardButton(text="✖  Нет, у меня лапки  ", callback_data="no")
    keyboard.add(yesButton)
    keyboard.add(noButton)
    #players = []
    users = db.getUsers()
    for user in users.find().sort("wr", pymongo.DESCENDING).limit(99):
        #players.append(user["_id"])
        bot.send_message(user["_id"], "Будешь завтра учавствовать в турнире?", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    # Если сообщение из чата с ботом
    if call.message:
        if call.data == "yes":
            db.setStatus(call.message.chat.id)
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="Увидемся завтра в игре. Перед игрой я тебе скину ключ")
        else:
            #TODO Надо отправлять новые приглашения
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="Хорошо, я напишу тебе, когда будет следующая игра")

@bot.message_handler(commands=["getcount"])
def getcount(message):
    users = db.getUsers()
    count = users.count()
    bot.send_message(message.chat.id, "Всего игроков в списке " + str(count))

@bot.message_handler(commands=["delme"])
def delme(message):
    try:
        db.dbf.users_telegram.remove({"_id": message.chat.id})
        bot.send_message(message.chat.id, "Тебя больше нет в списке")
    except Exception as e:
        bot.send_message(message.chat.id, "Что-то пошло не так")
        print("Error on deleting", e)
"""
@bot.message_handler(commands=["reset"])
def reset(message):
    if not checkAdmin(message.chat.id):
        bot.send_message(message.chat.id, "Ты не администратор")
        return
"""


@bot.message_handler(commands=["threadtest"])
def threadtest(message):
    bot.send_message(message.chat.id, "Hi before lock")
    #блокировка
    lock1.acquire()
    cur_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
    bot.send_message(message.chat.id, "Last request in [{0}]".format(cur_time))
    bot.send_message(message.chat.id, "Hi from lock")
    time.sleep(30)
    lock1.release()
    bot.send_message(message.chat.id, "Hi after lock")


@server.route("/" + config.token, methods=["POST"])
def getMessage():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return ("POST", 200)

@server.route("/")
def webhook():
    bot.remove_webhook()
    bot.set_webhook(url="https://fortnite-regme.herokuapp.com/" + config.token)
    return ("CONNECTED", 200)


bot.send_message(config.AboutSelf.chat_id, config.AboutSelf.getHelloMsg())
server.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
