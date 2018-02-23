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
    return db.users_telegram.find({"_id": nick}).count() == 1
#coll.update({"name": "Петр"}, {"surname": "Новосельцев", "age": 25})
def setStatus(chatid):
    users = db.users_telegram
    users.update({"_id": chatid}, {"status": 1})

@bot.message_handler(commands=["start", "help"])
def start(message):
    bot.send_message(message.chat.id, "Чтобы добавиться в подборку игроков, воспользуйся командой /addme")
    bot.send_message(message.chat.id, "Чтобы проверить свое место в списке зарегистрировавшихся участников используй /checkme")
    bot.send_message(message.chat.id, "Чтобы удалить себя из списка, воспользуйся командой /delme)

@bot.message_handler(commands=["addme"])
def addme(message):
    if not checkChatId(message.chat.id):
        sent = bot.send_message(message.chat.id, 'Напиши свой ник в Fortnite без кавычек, скобок и прочего')
        bot.register_next_step_handler(sent, check)
    else:
        bot.send_message(message.chat.id, "Ты уже присутствуешь в списке")
        bot.send_message(message.chat.id, "Ты можешь удалить себя с помошью команды /delme")

def check(message):
    lock = threading.Lock()
    name = message.text
    bot.send_message(message.chat.id, "Проверяю, подожди")
    if not checkPlayer(name):
        lock.acquire()
        try:
            r = requests.get(config.urlbase + name, headers=config.header)
            data = json.loads(r.text)
            wr = data['stats']['p2']["winRatio"]["value"]
            if "stats" in data:
                bot.send_message(message.chat.id, "Твой WinRate" + " - " + str(wr))
                if wr < 10:
                    bot.send_message(message.chat.id, "Твой WinRate слишком низок, но я все равно помещу тебя в список")
                else:
                    bot.send_message(message.chat.id, "Ты помещен в список")
                pushPlayer(message.chat.id, name, wr)
            else:
                bot.send_message(message.chat.id, "Не удалось найти такой ник")
        except Exception as e:
            bot.send_message(message.chat.id, "Что-то пошло не так, попробуйте позже")
        time.sleep(2)
        lock.release()
    else:
        bot.send_message(message.chat.id, "Такой ник уже есть среди участников. Если ты точно ввел свой ник, то напиши ему:")

@bot.message_handler(commands=["chatid"])
def chatid(message):
    bot.send_message(message.chat.id, "Its your chatid: " + str(message.chat.id))

@bot.message_handler(commands=["checkme"])
def checkme(message):
    users = db.users_telegram
    #isAdm = db.admins.find({"chat_id": chat_id}).count() == 1
    if checkChatId(message.chat.id):
        for i, user in enumerate(users.find().sort('wr', pymongo.DESCENDING)):
            if user["chat_id"] == message.chat.id:
                bot.send_message(message.chat.id, "Твое место в списке - " + str(i+1))
                return
    else:
        bot.send_message(message.chat.id, "Тебя нет в списке. Воспользуйся командой /addme")

@bot.message_handler(commands=["status"])
def any_msg(message):
    if checkAdmin(message.chat.id):
        keyboard = types.InlineKeyboardMarkup()
        yesButton = types.InlineKeyboardButton(text="Да", callback_data="yes")
        noButton = types.InlineKeyboardButton(text="Нет", callback_data="no")
        keyboard.add(yesButton, noButton)
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
            #TODO
            #set status YES
            setStatus(call.message.chat.id)
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="Увидемся завтра в игре. Перед игрой я тебе скину ключ")
        else:
            #TODO
            #set status NO
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="Хорошо, я напишу тебе, когда будет следующая игра")

@bot.message_handler(commands=["delme"])
def delme(message):
    db.users.remove({"_id": message.chat.id})

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
