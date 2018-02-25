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

#TODO: write command to FatherBot
# addme
# delme
# checkme
#

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
    FIRST = 1



db = DataBase
bot = telebot.TeleBot(config.token)
server = Flask(__name__)
lock1 = threading.Lock()


@bot.message_handler(commands=["start", "help"])
def start_help(message):
    # Available commands:
    #   start
    #   help
    #   addme
    #   chatid
    #   checkme
    #   status
    #   getcount
    #   delme
    func_list = [
        {name: "start",    mode: "start", descr: ""},
        {name: "help",     mode: "all", descr: ""},
        {name: "addme",    mode: "start", descr: ""},
        {name: "chatid",   mode: "start", descr: ""},
        {name: "checkme",  mode: "start", descr: ""},
        {name: "status",   mode: "start", descr: ""},
        {name: "getcount", mode: "start", descr: ""},
        {name: "delme",    mode: "start", descr: ""},
    ]
    #TODO: differnt help for admin and user
    #TODO для админов расширенную функцию
    send_id = message.chat.id
    bot.send_message(send_id, "Чтобы добавиться в подборку игроков, воспользуйся командой /add")
    bot.send_message(send_id, "Чтобы проверить свое место в списке зарегистрировавшихся участников используй /check")
    bot.send_message(send_id, "Чтобы удалить себя из списка, воспользуйся командой /del")

@bot.message_handler(commands=["addme"])
def addme(message):
    if not db.checkChatId(message.chat.id):
        sent = bot.send_message(message.chat.id, 'Напиши свой ник в Fortnite без кавычек, скобок и прочего')
        bot.register_next_step_handler(sent, check)
    else:
        bot.send_message(message.chat.id, "Ты уже присутствуешь в списке")
        bot.send_message(message.chat.id, "Ты можешь удалить себя из списка с помошью команды /del")

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
            #TODO:
            # from datetime import datetime
            # cur_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
            # string: "2018-02-25 18:07:48.029587"
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
    users = db.getUsers
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
    users = db.getUsers
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
    users = db.getUsers
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
