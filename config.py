import os
# -*- coding: utf-8 -*-

#for telegramm
token = os.environ.get('BOT_TOKEN', '')

#for fortnitetracker
header = {"TRN-Api-Key": os.environ.get('FORT_TRECKER', '')}
platform = "pc"
urlbase = "https://api.fortnitetracker.com/v1/profile/" + platform + "/"

#for mlab
mongourl = os.environ.get('MONGODB', '')
 
class AboutSelf:
    email   = "name@yandex.ru"
    mtel    = "+79995361024"
    name    = "Roman"
    chat_id = "337968852"
    vk      = "https://vk.com/holymanych"

    def getHelloMsg():
        return "I am here"

# FORTNITE
class FortniteParam:
    lowest_winrate = 10.0
