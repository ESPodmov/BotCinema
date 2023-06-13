import json
import time

from pymongo import MongoClient
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from config import MONGOKEY

dictionary = {"ids": {}}
service = Service("../geckodriver.exe")
options = webdriver.FirefoxOptions()
options.add_argument('--headless')
browser = webdriver.Firefox(options=options, service=service)
client = MongoClient(MONGOKEY)
db = client.mulitcinema

yt_base = "https://www.youtube.com"
search_yt_base = "https://www.youtube.com/results?search_query="

movie_collection = list(db.movie_collection.find())
try:
    for movie in movie_collection:
        movie_name = str(movie['name'])
        movie_id = movie["_id"]
        key_words = [movie_name, "трейлер"]
        url = search_yt_base + key_words[0].replace(" ", "+") + "+" + key_words[1]
        print(url)
        browser.get(url)
        time.sleep(1.5)
        content = browser.page_source
        soup = BeautifulSoup(content, 'html.parser')
        data = soup.findAll("a", {"id": "video-title"})
        flag = False
        for elem in data:
            title = str(elem.get('title')).lower()
            if all(word.lower() in title for word in key_words):
                dictionary["ids"][movie_id] = {}
                dictionary["ids"][movie_id]["name"] = movie_name
                dictionary["ids"][movie_id]["link"] = yt_base + elem.get('href')
                print(dictionary["ids"][movie_id]["link"])
                flag = True
                break
        if not flag:
            dictionary["ids"][movie_id] = {}
            dictionary["ids"][movie_id]["name"] = movie_name
            dictionary["ids"][movie_id]["link"] = "VOID"
            print(dictionary["ids"][movie_id]["link"])

    with open("trailers/trailers.json", 'w', encoding="utf-8") as file:
        json.dump(dictionary, file, ensure_ascii=False)
except Exception:
    with open("trailers/trailers.json", 'w', encoding="utf-8") as file:
        json.dump(dictionary, file, ensure_ascii=False)

