import os
import time
import json
import config
import random
import telebot
import pymongo
import requests
import threading
from lxml import html
from telebot import types
from flask import Flask, request


client = pymongo.MongoClient(config.mongourl, connectTimeoutMS=30000)
db = client.get_database("fortnite_regme")
bot = telebot.TeleBot(config.token)
server = Flask(__name__)

def pushPlayer(chatid, nick, wr):
    record = {
    "_id": chatid,
    "fortnite_name": nick,
    "wr": wr,
    "status": 0
    }
    db.users_telegram.insert_one(record)

def checkAdmin(chat_id):
    return db.admins.find({"_id": chat_id}).count() == 1

def checkPlayer(nick):
    return db.users_telegram.find({"fortnite_name": nick}).count() == 1

def checkChatId(chatid):
    return db.users_telegram.find({"_id": chatid}).count() == 1

def setStatus(chatid):
    db.users_telegram.update({"_id": chatid}, {"$set":{"status":1 }})

@bot.message_handler(commands=["start", "help"])
def start(message):
    bot.send_message(message.chat.id, "Чтобы добавиться в подборку игроков, воспользуйся командой /add")
    bot.send_message(message.chat.id, "Чтобы проверить свое место в списке зарегистрировавшихся участников используй /check")
    bot.send_message(message.chat.id, "Если твой WinRate изменился, то воспользуйся командой /update")
    bot.send_message(message.chat.id, "Чтобы удалить себя из списка, воспользуйся командой /del")

@bot.message_handler(commands=["add"])
def addme(message):
    if not checkChatId(message.chat.id):
        sent = bot.send_message(message.chat.id, 'Напиши свой ник в Fortnite без кавычек, скобок и прочего')
        bot.register_next_step_handler(sent, check)
    else:
        bot.send_message(message.chat.id, "Ты уже присутствуешь в списке")
        bot.send_message(message.chat.id, "Ты можешь удалить себя из списка с помошью команды /delme")

def check(message):
    lock = threading.Lock()
    name = message.text
    name = name.lower()
    name = name.strip()
    bot.send_message(message.chat.id, "Проверяю, подожди. Это может занять некоторое время.  ⌛")
    if not checkPlayer(name):
        lock.acquire()
        try:
            #DEBUG Проверка на частоту запросов
            print("Last request in", time.time())
            r = requests.get(config.urlbase + name, headers=config.header)
            data = json.loads(r.text)
            if "stats" in data:
                wr = data['stats']['p2']["winRatio"]["value"]
                bot.send_message(message.chat.id, "Твой WinRate" + " - " + str(wr))
                if float(wr) < 10:
                    bot.send_message(message.chat.id, "Твой WinRate слишком низок, но я все равно помещу тебя в конец списка")
                else:
                    bot.send_message(message.chat.id, "Ты помещен(а) в список")
                pushPlayer(message.chat.id, name, wr)
            else:
                bot.send_message(message.chat.id, "Не удалось найти такой ник")
        except Exception as e:
            print(e)
            bot.send_message(message.chat.id, "Что-то пошло не так, попробуй позже")
        time.sleep(2)
        lock.release()
    else:
        bot.send_message(message.chat.id, "Такой ник уже есть среди участников. Если ты точно ввел(а) свой ник, то напиши ему:")
        bot.send_contact(message.chat.id, "+79995361024", "Roman")

@bot.message_handler(commands=["chatid"])
def chatid(message):
    bot.send_message(message.chat.id, "Its your chatid: " + str(message.chat.id))

@bot.message_handler(commands=["check"])
def checkme(message):
    users = db.users_telegram
    #isAdm = db.admins.find({"chat_id": chat_id}).count() == 1
    if checkChatId(message.chat.id):
        for i, user in enumerate(users.find().sort('wr', pymongo.DESCENDING)):
            if user["_id"] == message.chat.id:
                bot.send_message(message.chat.id, "Твое место в списке - " + str(i+1))
                return
    else:
        bot.send_message(message.chat.id, "Тебя нет в списке. Воспользуйся командой /addme")

@bot.message_handler(commands=["status"])
def any_msg(message):
    if not checkAdmin(message.chat.id):
        bot.send_message(message.chat.id, "Ты не администратор")
        return
    keyboard = types.InlineKeyboardMarkup()
    yesButton = types.InlineKeyboardButton(text="✅  Да, порву всех  ☠", callback_data="yes")
    noButton = types.InlineKeyboardButton(text="✖  Нет, у меня лапки  ", callback_data="no")
    keyboard.add(yesButton)
    keyboard.add(noButton)
    #players = []
    users = db.users_telegram
    for user in users.find().sort("wr", pymongo.DESCENDING).limit(99):
        #players.append(user["_id"])
        bot.send_message(user["_id"], "Будешь завтра учавствовать в турнире?", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    # Если сообщение из чата с ботом
    if call.message:
        if call.data == "yes":
            setStatus(call.message.chat.id)
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="Увидемся завтра в игре. Перед игрой я тебе скину ключ")
        else:
            #TODO Надо отправлять новые приглашения
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="Хорошо, я напишу тебе, когда будет следующая игра")

@bot.message_handler(commands=["getcount"])
def getcount(message):
    count = db.users_telegram.count()
    bot.send_message(message.chat.id, "Всего игроков в списке " + str(count))

@bot.message_handler(commands=["del"])
def delme(message):
    try:
        db.users_telegram.remove({"_id": message.chat.id})
        bot.send_message(message.chat.id, "Тебя больше нет в списке")
    except Exception as e:
        bot.send_message(message.chat.id, "Что-то пошло не так")
        print("Error on deleting", e)

@server.route("/" + config.token, methods=["POST"])
def getMessage():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "POST", 200

@server.route("/")
def webhook():
    bot.remove_webhook()
    bot.set_webhook(url="https://fortnite-regme.herokuapp.com/" + config.token)
    return "CONNECTED", 200


bot.send_message(337968852, "iam ready")
server.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
