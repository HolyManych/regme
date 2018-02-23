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


@bot.message_handler(commands=['start', "help"])
def start(message):
    bot.send_message(message.chat.id, "Чтобы добавиться в подборку игроков, воспользуйся командой /addme")
    bot.send_message(message.chat.id, "Чтобы проверить свое место в списке зарегистрировавшихся участников используй /checkme")


@bot.message_handler(commands=['addme'])
def addme(message):
    sent = bot.send_message(message.chat.id, 'Напиши свой ник в Fortnite без кавычек, скобок и прочего')
    bot.register_next_step_handler(sent, check)


def check(message):
    lock = threading.Lock()
    name = message.text
    bot.send_message(message.chat.id, "Проверяю, подожди")
    lock.acquire()
    try:
        r = requests.get(config.urlbase + name, headers=config.header)
        data = json.loads(r.text)
        if "stats" in data:
            bot.send_message(message.chat.id, "Ваш WinRate" + " - " + str(data['stats']['p2']["winRatio"]["value"]))
        else:
            bot.send_message(message.chat.id, "Не удалось найти такой ник")
    except Exception as e:
        bot.send_message(message.chat.id, "Что-то пошло не так, попробуйте позже")
    time.sleep(2)
    lock.release()


@bot.message_handler(commands=['chatid'])
def chatid(message):
    bot.send_message(message.chat.id, "Its your chatid: " + str(message.chat.id))


@bot.message_handler(commands=['checkme'])
def checkme(message):
    users = db.users_telegram
    #isAdm = db.admins.find({"chat_id": chat_id}).count() == 1
    isFind = users.find({"chat_id": message.chat.id}).count() == 1
    if isFind:
        for i, user in enumerate(users.find().sort('wr', pymongo.DESCENDING):
            if user["chat_id"] == message.chat.id:
                bot.send_message(message.chat.id, "Твое место в списке - " + str(i+1))
                return
    else:
        bot.send_message(message.chat.id, "Тебя нет в списке. Воспользуйся командой /addme")


@bot.message_handler(commands=['key'])
def any_msg(message):
    keyboard = types.InlineKeyboardMarkup()
    yesButton = types.InlineKeyboardButton(text="Да", callback_data="yes")
    noButton = types.InlineKeyboardButton(text="Нет", callback_data="no")
    keyboard.add(yesButton, noButton)
    #keyboard.add(noButton)
    bot.send_message(message.chat.id, str(message.message_id) + "Будешь завтра учавствовать?", reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    # Если сообщение из чата с ботом
    if call.message:
        if call.data == "yes":
            #TODO
            #set status YES
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="Увидемся завтра в игре")
        else:
            #TODO
            #set status NO
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="Хорошо, я напишу тебе, когда будет следующая игра")


def checkAdmin(chat_id):
    return db.admins.find({"chat_id": chat_id}).count() == 1


@server.route("/" + config.token, methods=['POST'])
def getMessage():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "POST", 200


@server.route("/")
def webhook():
    bot.remove_webhook()
    bot.set_webhook(url="https://fortnite-regme.herokuapp.com/" + config.token)
    return "CONNECTED", 200

bot.send_message(337968852, "iam ready")
server.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))


if __name__ == '__main__':
    client = pymongo.MongoClient(config.mongourl, connectTimeoutMS=30000)
    db = client.get_database("fortnite_regme")
    bot = telebot.TeleBot(config.token)
    server = Flask(__name__)
    bot.send_message(337968852, "iam ready")
    server.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
