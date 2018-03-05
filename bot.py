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
from lxml import html
from telebot import types
from datetime import datetime
from flask import Flask, request

##############################################################################
# DataBase class
##############################################################################
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

    def pushAdmin(self, chatid):
        self.dbf.admins.insert_one({"_id": chatid})

    def getUsers(self):
        return self.dbf.users_telegram

    def checkAdmin(self, chat_id):
        return self.dbf.admins.find({"_id": chat_id}).count() == 1

    def checkPlayer(self, nick):
        return self.dbf.users_telegram.find({"fortnite_name": nick}).count() == 1

    def checkChatId(self, chatid):
        return self.dbf.users_telegram.find({"_id": chatid}).count() == 1

    def setStatus(self, chatid, status):
        self.dbf.users_telegram.update({"_id": chatid}, {"$set":{"status":status }})


##############################################################################
# Command class
##############################################################################
class Cmd:
    class Id:
        start      = 1
        help       = 2
        checkme    = 3
        chatid     = 4
        addme      = 5
        delme      = 6
        status     = 7
        getcount   = 8
        reset      = 9
        addadmin   = 10

    class Mode:
        ANY    = 0
        ADMIN  = 1
        IGNORE = 2

    def __init__(self, name, mode, description):
        self.name = name
        self.mode = mode
        self.descr = description

##############################################################################
# global variables
##############################################################################
cmds = {
    Cmd.Id.start:    Cmd("start",    Cmd.Mode.IGNORE,"Старт"),
    Cmd.Id.help:     Cmd("help",     Cmd.Mode.ANY,   "Вывод всех команд"),
    Cmd.Id.checkme:  Cmd("checkme",  Cmd.Mode.ANY,   "Показывает место в подборе"),
    Cmd.Id.chatid:   Cmd("chatid",   Cmd.Mode.ANY,   "Вывести номер пользователя"),
    Cmd.Id.addme:    Cmd("addme",    Cmd.Mode.ANY,   "Добавиться в очередь подбора"),
    Cmd.Id.delme:    Cmd("delme",    Cmd.Mode.ANY,   "Удалиться из очереди"),
    Cmd.Id.status:   Cmd("status",   Cmd.Mode.ADMIN, "developing..."),
    Cmd.Id.getcount: Cmd("getcount", Cmd.Mode.ANY,   "Количество игроков"),
    Cmd.Id.reset:    Cmd("reset",    Cmd.Mode.ADMIN, "Сбросить статус игроков после игры"),
    Cmd.Id.addadmin: Cmd("addadmin", Cmd.Mode.ADMIN, "Добавление админа"),
}

db = DataBase()
bot = telebot.TeleBot(config.token)
server = Flask(__name__)
lock1 = threading.Lock()

##############################################################################
# handlers
##############################################################################
@bot.message_handler(commands=[cmds[Cmd.Id.start].name, cmds[Cmd.Id.help].name])
def start_help(message):
    chat_id = message.chat.id
    isAdmin = db.checkAdmin(chat_id)
    for val in sorted(cmds.values(), key=lambda cmd: cmd.name):
        if val.mode == Cmd.Mode.IGNORE: continue
        if val.mode == Cmd.Mode.ADMIN and not isAdmin: continue
        bot.send_message(chat_id, "/{0} -- {1}".format(val.name, val.descr))


@bot.message_handler(commands=[cmds[Cmd.Id.addme].name])
def addme(message):
    chat_id = message.chat.id
    if not db.checkChatId(chat_id):
        sent = bot.send_message(chat_id, 'Напиши свой ник в Fortnite без кавычек, скобок и прочего')
        bot.register_next_step_handler(sent, check)
    else:
        bot.send_message(chat_id, "Ты уже присутствуешь в списке")
        bot.send_message(chat_id, "Ты можешь удалить себя из списка с помошью команды /{}".format(cmds[Cmd.Id.delme].name))

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
                    wr = float(data["stats"]["p2"]["winRatio"]["value"])
                    bot.send_message(message.chat.id, "Твой WinRate" + " - " + str(wr))
                    if wr < config.FortniteParam.lowest_winrate:
                        bot.send_message(message.chat.id, "Твой WinRate слишком низок, но я все равно помещу тебя в конец списка")
                    else:
                        bot.send_message(message.chat.id, "Ты помещен(а) в список")
                    db.pushPlayer(message.chat.id, name, wr)
            else:
                bot.send_message(message.chat.id, "Не удалось найти такой ник")
        except Exception as e:
            print("DEBUG: check: Exception:" + str(e))
            bot.send_message(message.chat.id, "Что-то пошло не так, попробуй позже")
        time.sleep(2)
        lock.release()
    else:
        bot.send_message(message.chat.id, "Такой ник уже есть среди участников. Если ты точно ввел(а) свой ник, то напиши ему:")
        bot.send_contact(message.chat.id, config.AboutSelf.mtel, config.AboutSelf.name)


@bot.message_handler(commands=[cmds[Cmd.Id.chatid].name])
def chatid(message):
    bot.send_message(message.chat.id, "Its your chatid: " + str(message.chat.id))


@bot.message_handler(commands=[cmds[Cmd.Id.checkme].name])
def checkme(message):
    users = db.getUsers()
    #isAdm = db.admins.find({"chat_id": chat_id}).count() == 1
    if db.checkChatId(message.chat.id):
        for i, user in enumerate(users.find().sort('wr', pymongo.DESCENDING)):
            if user["_id"] == message.chat.id:
                bot.send_message(message.chat.id, "Твое место в списке - " + str(i+1))
                return
    else:
        bot.send_message(message.chat.id, "Тебя нет в списке. Воспользуйся командой /{}".format(cmds[Cmd.Id.addme].name))


@bot.message_handler(commands=[cmds[Cmd.Id.status].name])
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
    #db.dbf.users_telegram.update({}, {"$set":{"status":0 }}, multi=True)
    for user in users.find().sort("wr", pymongo.DESCENDING).limit(99):
        #players.append(user["_id"])
        bot.send_message(user["_id"], "Будешь завтра учавствовать в турнире?", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    # Если сообщение из чата с ботом
    if call.message:
        if call.data == "yes":
            db.setStatus(call.message.chat.id, 1)
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="Увидемся завтра в игре. Перед игрой я тебе скину ключ")
        else:
            #TODO Надо отправлять новые приглашения
            db.setStatus(call.message.chat.id, -1)
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="Хорошо, я напишу тебе, когда будет следующая игра")

@bot.message_handler(commands=[cmds[Cmd.Id.getcount].name])
def getcount(message):
    users = db.getUsers()
    count = users.count()
    bot.send_message(message.chat.id, "Всего игроков в списке " + str(count))

@bot.message_handler(commands=[cmds[Cmd.Id.delme].name])
def delme(message):
    try:
        db.dbf.users_telegram.remove({"_id": message.chat.id})
        bot.send_message(message.chat.id, "Тебя больше нет в списке")
    except Exception as e:
        bot.send_message(message.chat.id, "Что-то пошло не так")
        print("Error on deleting", e)

@bot.message_handler(commands=[cmds[Cmd.Id.reset].name])
def reset(message):
    if not db.checkAdmin(message.chat.id):
        bot.send_message(message.chat.id, "Ты не администратор")
        return
    db.dbf.users_telegram.update({}, {"$set":{"status":0 }}, multi=True)
    bot.send_message(message.chat.id, "Успешно")

@bot.message_handler(commands=[cmds[Cmd.Id.addadmin].name])
def addadmin(message):
    if message.chat.id != int(config.AboutSelf.chat_id):
        bot.send_message(message.chat.id, "Ты не имеешь привелегий на эту команду")
        return
    textMes = message.text
    textMes = textMes.strip()
    pattern = "[\/][a-z]*[ ](.*)"
    result = re.findall(pattern, textMes)
    if len(result) == 0:
        bot.send_message(message.chat.id, "Команда введена неправильно. Введи в формате /addadmin #########")
        return
    res = result[0]
    if res.isdigit():
        try:
            isAdm = db.checkAdmin(res)
            if not isAdm:
                db.pushAdmin(res)
                bot.send_message(message.chat.id, "Добавлен")
            else:
                bot.send_message(message.chat.id, "Уже есть в списке администраторов")
        except Exception as e:
            print(e)
            bot.send_message(message.chat.id, "Что-то пошло не так")
    else:
        bot.send_message(message.chat.id, "Команда введена неправильно. Введи в формате /addadmin #########")




##############################################################################
# testing
##############################################################################
@bot.message_handler(commands=["threadtest"])
def threadtest(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "Hi before lock")
    #блокировка
    lock1.acquire()
    cur_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
    bot.send_message(chat_id, "Last request in [{0}]".format(cur_time))
    bot.send_message(chat_id, "Hi from lock")
    delay, every = 30, 5
    while delay > 0:
        bot.send_message(chat_id, "I am alive. Wait {} sec".format(delay))
        delay -= every
        time.sleep(every)
    lock1.release()
    bot.send_message(chat_id, "Hi after lock")

@bot.message_handler(commands=["updatetest"])
def threadtest(message):
    users = db.getUsers()
    users.find().sort("wr", pymongo.DESCENDING).limit(99)



##############################################################################
# webhooks
##############################################################################
@server.route("/" + config.token, methods=["POST"])
def getMessage():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return ("POST", 200)

@server.route("/")
def webhook():
    bot.remove_webhook()
    bot.set_webhook(url="https://fortnite-regme.herokuapp.com/" + config.token)
    return ("CONNECTED", 200)

##############################################################################
# main execution
##############################################################################
bot.send_message(config.AboutSelf.chat_id, config.AboutSelf.getHelloMsg())
server.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
