import pymongo
import config

def pushRECORD(chat_id, nick, isadm):
    record = {
    "chat_id": chat_id,
    "fortnite_name": nick,
    "isadmin": isadm
    }
    user_records.insert_one(record)


client = pymongo.MongoClient(config.mongourl, connectTimeoutMS=30000)
db = client.get_database("fortnite_regme")
user_records = db.users_telegram

#pushRECORD(50, "vvildvvolf", 1)

for men in user_records.find():
    print(men)


print("Thats all")
