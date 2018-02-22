import time
import json
import config
import requests

#https://fortnitetracker.com/


epic_nicknames = ["sorryhanzomain", "vanes130", "WBG Strafesh0t", "TiT_man"]

for name in epic_nicknames:
    r = requests.get(config.urlbase + name, headers=config.header)
    data = json.loads(r.text)
    print("WinRate for", name, "-", data['stats']['p2']["winRatio"]["value"], sep = '\t')
    time.sleep(2)
