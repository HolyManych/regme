import config
import random
import telebot
import requests
import googlemaps
from lxml import html
from saver import Saver
from telebot import types

bot = telebot.TeleBot(config.token)
gmaps = googlemaps.Client(key=config.goole_api)
places = []
userPool = {}
db = Saver('local.db')



class UserCtx:
    def __init__(self, userName):
        self.mode = 1
        self.addresses = list()
        #self.cur = db.getUserCursor(userName)

    #def getCursor(self):
    #    return self.cur

    def setMode(self, mode):
        self.mode = mode

    def getMode(self):
        return self.mode

    def addAddress(self, addr):
        self.addresses.append(addr)

    def resetAddresses(self):
        self.addresses.clear()

    def getAddresses(self):
        return self.addresses



class Place:
    def __init__(self, name, address):
        self.name = name
        self.address = address
        self.marks = list()

    def __str__(self):
        return self.name + " Адрес: " + self.address

    def addMark(self, mark):
        self.marks.append(mark)

    def getAvrMark(self):
        sum_ = sum(self.marks)
        return sum_/len(self.marks)



@bot.message_handler(commands=['start'])
def send_welcome(message):
    ctx = UserCtx(message.chat.id)
    userPool[message.chat.id] = ctx

    # test
    #name = message.from_user.username
    #bot.send_message(message.chat.id, 'Name: ' + str(name))
    #print(db.getPlaceList())
    #cur = ctx.getCursor()
    # end test


    fname = message.from_user.first_name
    bot.send_message(message.chat.id, 'Привет,  ' + str(fname))
    bot.send_message(message.chat.id, "Не знаешь куда сходить в Санкт-Петербурге? Тогда Ты обратился по адресу! Я помогу Тебе решить эту проблему!")
    markup = types.ReplyKeyboardMarkup()
    markup.add('Выбрать одно место', 'Выбрать 5 мест', 'Оценить место')
    markup.one_time_keyboard = True
    sent = bot.send_message(message.chat.id, 'Что выберете?', reply_markup = markup)
    bot.register_next_step_handler(sent, startAnswer)


def startAnswer(message):
    mode = 0
    ctx = userPool[message.chat.id]
    if message.text == 'Выбрать одно место':
        mode = 1
    elif message.text == 'Выбрать 5 мест':
        mode = 5
    elif message.text == 'Оценить место':
        set_mark_for_place_prepare(message)
        return
    ctx.setMode(mode)
    send_location_request(message)


@bot.message_handler(commands=['setmark'])
def set_mark_for_place_prepare(message):
    req = bot.send_message(message.chat.id, 'Введите имя места, которое хотите оценить')
    bot.register_next_step_handler(req, set_mark_for_place_repeater)


def set_mark_for_place_repeater(message):
    ctx = userPool[message.chat.id]
    print("set_mark> [{}] {}".format(message.chat.id, str(message.text)))
    if str(message.text).lower().strip() == 'stop':
        send_welcome(message)
        return
    for place in places:
        if str(place.name).lower().strip() == str(message.text).lower().strip():
            ctx.resetAddresses()
            ctx.addAddress(place)
            keys = types.ReplyKeyboardMarkup()
            for i in range(5):
                keys.add(str(i+1))
            keys.one_time_keyboard = True
            sent = bot.send_message(message.chat.id, 'Выберете оценку', reply_markup = keys)
            bot.register_next_step_handler(sent, answer)
            return
    req = bot.send_message(message.chat.id, 'Место не найдено. Попробуйте снова или введите stop')
    bot.register_next_step_handler(req, set_mark_for_place_repeater)



def answer(message):
    ctx = userPool[message.chat.id]
    mark = int(message.text)
    for place in places:
        if ctx.getAddresses()[0].name == place.name:
            place.addMark(mark)
            break
    send_welcome(message)


"""
@bot.message_handler(commands=['help'])
def send_help(message):
    bot.reply_to(message, "/suggestone Бот предложит Вам куда пойти \n/suggestfew Бот предложит несколько мест на выбор \nВы, также, можете ввести интересующее Вас место, например: Музей")
"""

@bot.message_handler(commands=['suggestone'])
def send_location_request(message):
    keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    keyboard.one_time_keyboard = True
    button_geo = types.KeyboardButton(text="Отправить местоположение", request_location=True)
    keyboard.add(button_geo)
    bot.send_message(message.chat.id, "Поделись местоположением, жалкий Человечишка!", reply_markup=keyboard)



@bot.message_handler(content_types=['location'])
def work_with_geo(message):
    city = 'Санкт-Петербург'
    lat = message.location.latitude
    lng = message.location.longitude
    loc = str(lat)+','+str(lng)
    ctx = userPool[message.chat.id]
    ctx.resetAddresses()
    mode = ctx.getMode()
    res = list()
    msg = ''
    while len(res) != mode:
        rand = random.choice(places)
        if rand in res: continue
        res.append(rand)
    for i, place in enumerate(res):
        addr = "{0}, {1}".format(city, place.address)
        geo = gmaps.distance_matrix(loc, addr, mode = "transit", language = 'ru')
        if geo['rows'][0]['elements'][0]['status'] == 'OK':
            dist = geo['rows'][0]['elements'][0]['distance']['text']
            time = geo['rows'][0]['elements'][0]['duration']['text']
            msg += "{}) {}\nАдрес: {}\nРасстояние: {}\nВремя в пути: {}\nСредняя оценка: {}\n\n".format(i + 1, place.name, addr, dist, time, place.getAvrMark())
            ctx.addAddress(addr)
        else:
            msg += "{}) {}\nАдрес: {}\nНе найти маршрут\nСредняя оценка: {}\n\n".format(i + 1, place.name, addr, place.getAvrMark())

    bot.send_message(message.chat.id, msg)
    keyboard = types.ReplyKeyboardMarkup()
    keyboard.add('Да', 'Нет')
    keyboard.one_time_keyboard = True
    req = bot.send_message(message.chat.id, 'Хотите получить геопозицию места', reply_markup = keyboard)
    bot.register_next_step_handler(req, question_after_top_place)


def question_after_top_place(message):
    ctx = userPool[message.chat.id]
    if message.text == 'Да':
        keys = types.ReplyKeyboardMarkup()
        keys.one_time_keyboard = True
        for i in range(1, len(ctx.getAddresses()) + 1):
            keys.add(str(i))
        keys.one_time_keyboard = True
        req = bot.send_message(message.chat.id, 'Получить локацию места:', reply_markup = keys)
        bot.register_next_step_handler(req, get_coord_after_top_place)
    else:
        ctx.setMode(0)
        ctx.resetAddresses()
        send_welcome(message)


def get_coord_after_top_place(message):
    ctx = userPool[message.chat.id]
    addr = ctx.getAddresses()[int(message.text) - 1]
    loc = gmaps.geocode(addr)
    lat = loc[0]['geometry']['location']['lat']
    lng = loc[0]['geometry']['location']['lng']
    bot.send_location(message.chat.id, lat, lng)
    ctx.resetAddresses()
    send_welcome(message)

@bot.message_handler(content_types=["text"])
def sayHello(message):
    send_welcome(message)



"""
@bot.message_handler(content_types=["text"])
def sayHello(message):
    foundPlaces = []
    for place in places:
        if place.name.find(message.text) != -1:
            #foundPlaces.append(str(place))
            foundPlaces.append(place)
    if len(foundPlaces) == 0:
        bot.send_message(message.chat.id, "Ничего не найдено!")
    else:
        cn = 1
        for pl in foundPlaces:
            bot.send_message(message.chat.id, str(cn) + ')' + pl.name)
            cn += 1
        #bot.send_message(message.chat.id, '\n'.join(foundPlaces))
"""


if __name__ == '__main__':
    response = requests.get(config.url)
    document = html.fromstring(response.text)
    names = document.xpath('//h2//b/text()')
    address = document.xpath("//a[@class='media-preview_description']/text()")
    for i in range(0, len(names)):
        placeName, placeAddr = names[i], address[i]
        places.append(Place(placeName, placeAddr))


        #for local DB
        try:
            db.createPlace(placeName, placeAddr)
        except Exception as e:
            # ignore creating places
            pass
    for place in places:
        for i in range(10):
            user = 'User' + str(i)
            place.addMark(db.getMark(user, place.name))
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        print("main>", e)
        exit(1)
