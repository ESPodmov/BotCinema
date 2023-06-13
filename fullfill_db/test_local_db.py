import asyncio
import json

from pymongo import MongoClient
from aiogram import Bot, types
from config import TOKEN, MONGOKEY
from aiogram.dispatcher import Dispatcher, FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils import executor
import requests
from kinopoisk_api import KP
from aiogram.types import ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, \
    InlineKeyboardButton

kinopoisk = KP(token='3c4f094f-b98a-42e0-b39f-1f9ea363f7be')
bot = Bot(token=TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())
client = MongoClient(MONGOKEY)
db = client.mulitcinema
with open('movie_list/other/movies_id_main.json') as f:
    movie_ids = json.load(f)
    movie_ids = movie_ids['data']


class MovieAdder:
    def __init__(self, name, genre, year, vector, rate, link, description, country, number, trailer, picture,
                 poster_preview):
        self.name = name
        self.genre = genre
        self.year = year
        self.vector = vector
        self.rate = rate
        self.link = link
        self.description = description
        self.country = country
        self.number = number
        self.trailer = trailer
        self.picture = picture
        self.poster_preview = poster_preview


control_dict = {}
not_used_movies = {'data': []}
count_control = {"data": 1}
callback_control = {'data': ""}
no_photos = {'data': []}


async def process_movie(user_id):
    for elem in movie_ids:
        movie = kinopoisk.get_film(int(elem)).__dict__
        rate = movie['kp_rate']
        if rate is not None and str(rate) != "0":
            rate = str(round(float(rate), 1))
            description = movie['description']
            if description is not None:
                description = description.replace('\xa0', " ")
                name_list = list(db.movie_collection.distinct("name"))
                name = movie['ru_name']
                if name not in name_list:
                    genre = movie["genres"]
                    year = movie['year']
                    country = movie['countries']
                    vector = ""
                    trailer = ""
                    link = ""
                    poster_link = requests.get(movie['poster'], allow_redirects=True).url
                    collection = db.movie_collection.find()
                    size = 0
                    for e in collection:
                        size = size + 1
                    if size == 0:
                        movie_number = 1
                    else:
                        movie_number = int(
                            db.movie_collection.find().sort("_id", -1).limit(1)[0]["_id"]) + 1
                    try:
                        photo = await bot.send_photo(user_id, photo=poster_link)
                    except Exception as e:
                        try:
                            poster_link = requests.get(movie['poster_preview'], allow_redirects=True).url
                            photo = await bot.send_photo(user_id, photo=poster_link)
                        except Exception as second_exception:
                            no_photos['data'].append(int(elem))
                            continue
                    photo_id = photo["photo"][-1]["file_id"]
                    inserted_movie_data = {'_id': movie_number, 'name': name, 'genre': genre,
                                           'year': year, 'vector': vector, 'rate': rate,
                                           'link': link, 'description': description,
                                           'country': country, 'trailer': trailer,
                                           'picture_id': photo_id}
                    db.movie_collection.insert_one(inserted_movie_data)
                    print(str(movie_ids.index(elem) + 1) + ": added")
                else:
                    movie_data = db.movie_collection.find({"name": name}).limit(1)[0]
                    print(movie_data['name'] + "(" + str(movie_data["_id"]) + ")" + " already added")
            else:
                not_used_movies['data'].append(int(elem))
                print(str(movie_ids.index(elem) + 1) + ": empty")

        else:
            not_used_movies['data'].append(int(elem))
            print(str(movie_ids.index(elem) + 1) + ": empty")

    await bot.send_message(user_id, "Список фильмов закончился")
    with open('./movie_list/missed_movies.json', 'w') as file:
        json.dump(not_used_movies, file)
    with open('./movie_list/movies_without_photo.json', 'w') as file:
        json.dump(no_photos, file)


@dp.message_handler(commands=["start"])
async def start_est_handler(message: types.Message):
    await process_movie(message.from_user.id)


@dp.callback_query_handler()
async def callback_handler(callback: types.CallbackQuery):
    data = callback.data
    if callback_control['data'] != data:
        callback_control['data'] = data
        if data[:2] == "no":
            empty_btn = InlineKeyboardButton("Пустая", callback_data="empty%d" % count_control['data'])
            not_empty_btn = InlineKeyboardButton("Есть", callback_data="have%d" % count_control['data'])
            delete_btn = InlineKeyboardButton("Удалить", callback_data="delete%d" % count_control['data'])
            keyboard = InlineKeyboardMarkup().row(not_empty_btn, empty_btn, delete_btn)
            photo = await bot.send_photo(callback.from_user.id, control_dict[callback.from_user.id].poster_preview,
                                         reply_markup=keyboard)
            photo_id = photo["photo"][-1]["file_id"]
            control_dict[callback.from_user.id].picture = photo_id
            return
        if "delete" not in data:
            if "have" in data or "yes" in data:
                movie_data = control_dict[callback.from_user.id]
                inserted_movie_data = {'_id': movie_data.number, 'name': movie_data.name, 'genre': movie_data.genre,
                                       'year': movie_data.year, 'vector': movie_data.vector, 'rate': movie_data.rate,
                                       'link': movie_data.link, 'description': movie_data.description,
                                       'country': movie_data.country, 'trailer': movie_data.trailer,
                                       'picture_id': movie_data.picture}
                db.movie_collection.insert_one(inserted_movie_data)
                print(str(count_control['data']) + ": added")
            elif "empty" in data:
                print(str(count_control['data']) + ": added without photos")
                no_photos['data'].append(int(movie_ids[count_control['data'] - 1]))
        else:
            print(str(count_control['data']) + ": deleted")
        count_control['data'] += 1
        if count_control['data'] <= len(movie_ids):
            await process_movie(callback.from_user.id)
        else:
            await bot.send_message(callback.from_user.id, "Список фильмов закончился")
            with open('./movie_list/missed_movies.json', 'w') as file:
                json.dump(not_used_movies, file)
            with open('./movie_list/movies_without_photo.json', 'w') as file:
                json.dump(not_used_movies, file)


@dp.message_handler(commands=["delete"])
async def delete_all_movies(message: types.Message):
    movies = list(db.movie_collection.find({}))
    for elem in movies:
        db.movie_collection.delete_one({'_id': elem['_id']})


@dp.message_handler(commands=["end"])
async def delete_all_movies(message: types.Message):
    with open('./movie_list/missed_movies.json', 'w') as file:
        json.dump(not_used_movies, file)
    with open('./movie_list/movies_without_photo.json', 'w') as file:
        json.dump(no_photos, file)
    await bot.send_message(message.from_user.id, "Работа принудительно закончена, все файлы сохранены")


# @dp.message_handler(commands=["photo"])
# async def delete_all_movies(message: types.Message):
#     await bot.send_photo(message.from_user.id,
#                          photo='https://kinopoiskapiunofficial.tech/images/posters/kp_small/1115098.jpg')
#     await bot.send_photo(message.from_user.id,
#                          photo='https://avatars.mds.yandex.net/get-kinopoisk-image/4303601/33a1b1e1-241d-4908-a0ea-f16950f539c6/x1000')


if __name__ == '__main__':
    executor.start_polling(dp)
