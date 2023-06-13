import json

import pymongo
from pymongo import MongoClient
from config import MONGOKEY


client = MongoClient(MONGOKEY)
db = client.mulitcinema


db.movie_collection.create_index([("name", pymongo.TEXT)])
#
with open("trailers/trailers.json", encoding="utf-8") as f:
    trailers_data = json.load(f)

trailers_data = trailers_data["ids"]

for elem in trailers_data:
    print(str(trailers_data[str(elem)]["name"]))
    db.movie_collection.update_one({"_id": int(elem)}, {"$set": {"trailer": trailers_data[str(elem)]["link"]}})
