from pymongo import MongoClient
from pymongo.server_api import ServerApi
from config import TOKEN, MONGOKEY

client = MongoClient(MONGOKEY, server_api=ServerApi('1'))

# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)