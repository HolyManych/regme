# -*- coding: utf-8 -*-

#for telegramm
token = '468930047:AAFMt1a45Wl7W9NbjK5E_zlnJ6VAA0nZ-vE'

#for fortnitetracker
header = {"TRN-Api-Key": "51c30244-9117-41db-8f25-9041b222dc43"}
platform = "pc"
urlbase = "https://api.fortnitetracker.com/v1/profile/" + platform + "/"

#for mlab
mongourl = "mongodb://adm:adm@ds243418.mlab.com:43418/fortnite_regme"

class AboutSelf:
    email   = "name@yandex.ru"
    mtel    = "+79995361024"
    name    = "Roman"
    chat_id = "337968852"
    vk      = "https://vk.com/holymanych"

    def getHelloMsg():
        return "I am ready"

# FORTNITE
class FortniteParam:
    lowest_winrate = 10.0
