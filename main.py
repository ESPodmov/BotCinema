import datetime
import math
import re
import sys
import traceback

from aiogram.utils.exceptions import BadRequest
import pymongo
from aiogram import Bot, types
from aiogram.types import ContentTypes
from aiogram.dispatcher import Dispatcher, FSMContext
from aiogram.utils import executor
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from aiogram.dispatcher.filters.state import State, StatesGroup
import gridfs
import random
from aiogram_broadcaster import MessageBroadcaster
from aiogram.contrib.fsm_storage.memory import MemoryStorage

from config import TOKEN, MONGOKEY
import keyboars
from msg_dict import msg_dict

bot = Bot(token=TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

client = MongoClient(MONGOKEY, server_api=ServerApi('1'))
db = client.mulitcinema

fs = gridfs.GridFS(db)

admins_dict = {}
users_dict = {}
users_select_dict = {}
users_selected_movies = {}

msg_dict = msg_dict

punctuations = '''!()-[]{};:'"\,<>./?@#$%^&*_~'''


class MovieAdder:
    def __init__(self, name, genre, year, vector, rate, link, description, country, number, trailer):
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
        self.picture = None


class MovieUpdater:
    def __init__(self, id_of_movie):
        self.id = id_of_movie
        self.data = None
        self.param = None


class MovieSelector:
    def __init__(self):
        self.genre = None
        self.year = None
        self.vector = None
        self.rate = None
        self.country = None


class States(StatesGroup):
    DEFAULT_STATE = State()
    ENTER_STATE = State()
    GET_PICTURE = State()
    DELETE_STATE = State()
    CHANGE_STATE = State()
    CHOOSE_CHANGE_STATE = State()
    EDIT_PICTURE_STATE = State()
    SEND_MESSAGES = State()
    SORT_STATE = State()


def check_if_admin(message: types.Message):
    admin = False
    for elem in db.control.find({}):
        if message.from_user.id == elem["user_id"]:
            admin = True
    return admin


def check_user_exists(message: types.Message):
    admin = False
    for elem in db.users.find({}):
        if message.from_user.id == elem["user_id"]:
            admin = True
    return admin


def calculate_count_of_documents(docs):
    counter = 0
    for elem in docs:
        counter += 1
    return counter


def delete_movie_with_picture(document):
    db.movie_collection.delete_one({'_id': int(document["_id"])})


def read_from_array_in_db(movie: dict, param: str):
    result = ""
    for elem in movie[param]:
        if result == "":
            result += elem
        else:
            result += ", " + elem
    return result


def create_caption_for_users(movie):
    genre = read_from_array_in_db(movie, "genre")
    country = read_from_array_in_db(movie, "country")
    vector = read_from_array_in_db(movie, "vector")
    caption = f"<b>{movie['name']}</b>\nЖанр: {genre.lower()}\nГод: {movie['year']}\nСтрана: {country}"
    if movie['vector'] != "":
        caption += f"\nНаправление: {vector.lower()}"
    caption += f"\nРейтинг: {movie['rate']}"
    try:
        trailer = movie['trailer']
        if trailer != "":
            caption += f"\nТрейлер(<a href='{trailer}'>клик</a>)"
    except Exception:
        print("There is no trailer link")
    if movie["link"] != "":
        caption += f"\nСмотреть фильм(<a href='{movie['link']}'>клик</a>)"
    return caption


def create_description_for_users(movie):
    description = f"<b>{movie['name']}</b>\n{movie['description']}"
    return description


async def assign_new_param_admins_dict(callback: types.CallbackQuery, param, state: FSMContext):
    try:
        movie_to_update = admins_dict[callback.from_user.id]
        movie_to_update.param = param
        admins_dict[callback.from_user.id] = movie_to_update
    except KeyError:
        await bot.send_message(callback.from_user.id,
                               msg_dict["error_msg"]["error_sample"] + msg_dict["error_msg"]["updating_error"])
        await state.reset_state()
        return


async def assign_new_data_admins_dict(message: types.Message, data, state: FSMContext):
    try:
        movie_to_update = admins_dict[message.from_user.id]
        param = movie_to_update.param
        entered_data = data
        if param == "country" or param == "vector" or param == "genre":
            entered_data = data.split(",")
            if param != "country":
                for i in range(len(entered_data)):
                    if entered_data[i][0] == " ":
                        entered_data[i] = entered_data[i][1:].capitalize()
            else:
                for i in range(len(entered_data)):
                    if entered_data[i][0] == " ":
                        entered_data[i] = entered_data[i][1:]
        movie_to_update.data = entered_data
        admins_dict[message.from_user.id] = movie_to_update
    except KeyError:
        await bot.send_message(message.from_user.id,
                               msg_dict["error_msg"]["error_sample"] + msg_dict["error_msg"]["updating_error"])
        await state.reset_state()
        return


async def user_is_channel_member(user_id):
    channels = db.channels.find({})
    result = True
    for elem in channels:
        user_channel_status = await bot.get_chat_member(chat_id=elem["chat_id"], user_id=user_id)
        if user_channel_status["status"] != 'left' and user_channel_status["status"] != "kicked":
            result = result and True
        else:
            result = result and False
    return result


async def delete_all_useless_links(message: types.Message):
    users_data = db.users.find({})
    try:
        for user in users_data:
            links_data = user["invite"]
            if not isinstance(links_data, bool):
                time_now = datetime.datetime.now()
                if time_now > links_data["exp_time"]:
                    links_dict = links_data["groups"]
                    for key in links_dict:
                        try:
                            await bot.revoke_chat_invite_link(links_dict[key]["id"], str(links_dict[key]["link"]))
                        except BadRequest:
                            pass
        await bot.send_message(message.from_user.id, msg_dict["revoke_links"]["success"])
    except Exception as e:
        await bot.send_message(message.from_user.id, msg_dict["error_msg"]["error_sample"])
        pass


@dp.message_handler(commands=["revoke_links"])
async def revoke_links_handler(message: types.Message):
    if check_if_admin(message):
        await delete_all_useless_links(message)
    else:
        await bot.send_message(message.from_user.id, msg_dict["error_msg"]["unknown_command"])


async def create_invite_links():
    channels = db.channels.find({})
    result = {}
    for elem in channels:
        expire_date = datetime.datetime.now() + datetime.timedelta(hours=1)
        link = await bot.create_chat_invite_link(elem["chat_id"], expire_date=expire_date)
        result[elem["name"]] = {"link": link.invite_link, "id": elem["chat_id"]}
    return result


def get_permanent_links():
    channels = db.channels.find({})
    result = {}
    for elem in channels:
        result[elem["name"]] = elem["permanent"]
    return result


@dp.message_handler(state="*", commands=['add_new_movie_admin_pass'])
async def add_new_movie(message: types.Message):
    if check_if_admin(message):
        await message.reply(msg_dict["add_new_movie"]["start"])
        await States.ENTER_STATE.set()
    else:
        await message.reply(msg_dict["error_msg"]["unknown_command"])


@dp.message_handler(commands=['delete_film_admin_pass'])
async def delete_movie_check(message: types.Message):
    if check_if_admin(message):
        await message.reply(msg_dict["delete_movie"]["start"])
        await States.DELETE_STATE.set()
    else:
        await message.reply(msg_dict["error_msg"]["unknown_command"])


async def subscribe_funnel(user: types.User):
    if isinstance(db.users.find({"user_id": user.id}).limit(1)[0]["invite"], bool):
        channel_dict = await create_invite_links()
        keyboard = keyboars.InlineKeyboardMarkup()
        for elem in channel_dict:
            btn = keyboars.InlineKeyboardButton(str(elem), url=str(channel_dict[elem]["link"]))
            keyboard.add(btn)
        exp_time = datetime.datetime.now() + datetime.timedelta(hours=1)
        db.users.update_one({"user_id": user.id}, {"$set": {"invite": {"exp_time": exp_time, "groups": channel_dict}}})
        await bot.send_message(user.id, msg_dict["subscribe_msg"]["first_time"], reply_markup=keyboard,
                               parse_mode="HTML")
    else:
        channel_dict = get_permanent_links()
        keyboard = keyboars.InlineKeyboardMarkup()
        for elem in channel_dict:
            btn = keyboars.InlineKeyboardButton(str(elem), url=str(channel_dict[elem]))
            keyboard.add(btn)
        await bot.send_message(user.id, msg_dict["subscribe_msg"]["not_first_time"], reply_markup=keyboard,
                               parse_mode="HTML")


@dp.message_handler(commands=["start"])
async def start_handler(message: types.Message):
    await bot.send_message(message.from_user.id, msg_dict["start"]["first"])
    await bot.send_message(message.from_user.id, msg_dict["start"]["second"],
                           reply_markup=keyboars.reply_keyboards_list[1])
    if not check_user_exists(message):
        db.users.insert_one({"user_id": message.from_user.id, "keyboard": 1, "invite": False})
    if not await user_is_channel_member(message.from_user.id):
        await subscribe_funnel(message.from_user)


@dp.message_handler(commands=["get_links"])
async def get_links_handler(message: types.Message):
    await subscribe_funnel(message.from_user)


@dp.message_handler(commands=["help"])
async def help_command_handler(message: types.Message):
    message_text = msg_dict["help"]["main_commands"]
    if check_if_admin(message):
        additional_commands = msg_dict["help"]["additional_commands"]
        admins_line = message_text + additional_commands
        await bot.send_message(message.from_user.id, admins_line, parse_mode="HTML")
    else:
        await bot.send_message(message.from_user.id, message_text, parse_mode="HTML")


@dp.message_handler(commands=["update_movie_admin_pass"])
async def update_movie_check(message: types.Message):
    if check_if_admin(message):
        await message.reply(msg_dict["update_movie"]["start"])
        await States.CHANGE_STATE.set()
    else:
        await message.reply(msg_dict["error_msg"]["unknown_command"])


@dp.message_handler(commands=["delete_start_keyboard"])
async def delete_start_keyboard(message: types.Message):
    if not await user_is_channel_member(message.from_user.id):
        await bot.send_message(message.from_user.id, msg_dict["subscribe_msg"]["not_subscribed"])
    else:
        if db.users.find({"user_id": message.from_user.id}).limit(1)[0]["keyboard"] != 0:
            await bot.send_message(message.from_user.id, msg_dict["remove_keyboard"]["first"],
                                   reply_markup=keyboars.ReplyKeyboardRemove())
            db.users.update_one({"user_id": message.from_user.id}, {"$set": {"keyboard": 0}})


@dp.message_handler(commands=["add_start_keyboard"])
async def add_start_keyboard(message: types.Message):
    if not await user_is_channel_member(message.from_user.id):
        await bot.send_message(message.from_user.id, msg_dict["subscribe_msg"]["not_subscribed"])
    else:
        if db.users.find({"user_id": message.from_user.id}).limit(1)[0]["keyboard"] != 1:
            await bot.send_message(message.from_user.id, msg_dict["add_keyboard"]["first"],
                                   reply_markup=keyboars.reply_keyboards_list[1])
            db.users.update_one({"user_id": message.from_user.id}, {"$set": {"keyboard": 1}})


@dp.message_handler(commands=["stop"])
async def stop_handler(message: types.Message):
    await message.reply(msg_dict["stop"]["main"])
    db.users.delete_one({"user_id": message.from_user.id})


@dp.message_handler(commands=["send_message_to_users"])
async def send_message_to_user_handler(message: types.Message):
    if check_if_admin(message):
        await message.reply(msg_dict["send_message_to_users"]["main"])
        await States.SEND_MESSAGES.set()
    else:
        await message.reply(msg_dict["error_msg"]["unknown_command"])


@dp.message_handler(state=States.ENTER_STATE)
async def enter_movie(message: types.Message, state: FSMContext):
    if message.text.lower() == "stop":
        await state.reset_state()
        await message.reply("Отмена добавления")
    else:
        data = message.text.split(sep='&')
        if len(data) != 9:
            await message.reply(msg_dict["add_new_movie"]["wrong_data"])
        else:
            movie_name = data[0]
            name_list = list(db.movie_collection.distinct("name"))
            name_list = [str(elem).lower() for elem in name_list]
            if movie_name.lower() in name_list:
                movie_data = db.movie_collection.find({"name": movie_name}).limit(1)[0]
                await bot.send_message(message.from_user.id,
                                       msg_dict["add_new_movie"]["already_added"].format(name=movie_data["name"],
                                                                                         id=movie_data["_id"]))
            movie_genre = [elem.lower() for elem in data[1].replace(" ", "").split(",")]
            movie_year = int(data[2])
            movie_vector = data[3].split(",")
            for i in range(len(movie_vector)):
                if movie_vector[i][0] == " ":
                    movie_vector[i] = movie_vector[i][1:].capitalize()
                else:
                    movie_vector[i] = movie_vector[i].capitalize()
            movie_rate = data[4]
            movie_country = data[5].split(",")
            for i in range(len(movie_country)):
                if movie_country[i][0] == " ":
                    movie_country[i] = movie_country[i][1:]
            movie_link = data[6]
            trailer_link = data[7]
            movie_description = data[8]
            collection = db.movie_collection.find()
            size = 0
            for elem in collection:
                size = size + 1
            if size == 0:
                movie_number = 1
            else:
                movie_number = int(
                    db.movie_collection.find().sort("_id", -1).limit(1)[0]["_id"]) + 1  # под вопросом
            admins_dict[message.from_user.id] = MovieAdder(movie_name, movie_genre, movie_year, movie_vector,
                                                           movie_rate, movie_link, movie_description,
                                                           movie_country, movie_number, trailer_link)
            await bot.send_message(message.from_user.id, msg_dict["add_new_movie"]["send_photo_part"])
            await States.GET_PICTURE.set()


@dp.message_handler(state=States.GET_PICTURE, content_types=ContentTypes.ANY)
async def get_picture_handler(message: types.Message, state: FSMContext):
    if message.text:
        if message.text.lower() == "stop":
            await state.reset_state()
            await message.reply("Отмена добавления")
            try:
                admins_dict.pop(message.from_user.id)
            except Exception:
                print("Data have been deleted already")
        else:
            await bot.send_message(message.from_user.id, msg_dict["add_new_movie"]["wrong_data_picture_stage"])
    elif message.photo:
        try:
            current_movie = admins_dict[message.from_user.id]
        except KeyError:
            await bot.send_message(message.from_user.id,
                                   msg_dict["error_msg"]["error_sample"] + msg_dict["error_msg"]["adding_error_1"])
            await state.reset_state()
            return
        file = await bot.get_file(message.photo[-1].file_id)
        file_info = (await bot.download_file(file.file_path)).read()
        inserted_movie_data = {'_id': current_movie.number, 'name': current_movie.name, 'genre': current_movie.genre,
                               'year': current_movie.year, 'vector': current_movie.vector, 'rate': current_movie.rate,
                               'link': current_movie.link, 'description': current_movie.description,
                               'country': current_movie.country, 'trailer': current_movie.trailer}
        caption = "Всё верно?\n" + create_caption(inserted_movie_data)
        photo_id = await bot.send_photo(message.from_user.id, file_info, caption=caption,
                                        reply_markup=keyboars.inline_kb_confirm)
        # print(photo_id["photo"][-1]["file_id"])
        current_movie.picture = photo_id["photo"][-1]["file_id"]
        admins_dict[message.from_user.id] = current_movie
        inserted_movie_data["picture_id"] = current_movie.picture

        db.movie_collection.insert_one(inserted_movie_data)
    else:
        await bot.send_message(message.from_user.id, msg_dict["add_new_movie"]["wrong_data_picture_stage"])


@dp.callback_query_handler(lambda c: c.data == 'confirm', state=States.GET_PICTURE)
async def confirm_new_movie(callback: types.CallbackQuery, state: FSMContext):
    await state.reset_state()
    await bot.send_message(callback.from_user.id, msg_dict["add_new_movie"]["success"])
    await callback.message.delete()
    try:
        admins_dict.pop(callback.from_user.id)
    except KeyError:
        print(str(callback.from_user.id) + " (admin) data have been deleted")


@dp.callback_query_handler(lambda c: c.data == "refuse", state=States.GET_PICTURE)
async def refuse_new_movie(callback: types.CallbackQuery, state: FSMContext):
    try:
        added_movie = admins_dict[callback.from_user.id]
    except KeyError:
        await bot.send_message(callback.from_user.id,
                               msg_dict["error_msg"]["error_sample"] + msg_dict["error_msg"]["adding_error_2"])
        await state.reset_state()
        return
    if added_movie is not None:
        db.movie_collection.delete_one({'_id': int(added_movie.number)})
        await bot.send_message(callback.from_user.id, msg_dict["add_new_movie"]["reenter_data"])
        await callback.message.delete()
        await States.ENTER_STATE.set()
    else:
        await bot.send_message(callback.from_user.id,
                               "Что-то пошло не так, удалите введенный фильм вручную(/delete_film_admin_pass)")
    try:
        admins_dict.pop(callback.from_user.id)
    except KeyError:
        print(str(callback.from_user.id) + " (admin) data have been deleted")
    await States.ENTER_STATE.set()


@dp.message_handler(state=States.DELETE_STATE)
async def delete_movie_handler(message: types.Message, state: FSMContext):
    movie = message.text
    if movie.lower() == "stop":
        await message.reply("Удаление отменено")
        await state.reset_state()
    elif movie.isdigit():
        documents = list(db.movie_collection.find({'_id': int(movie)}))
        documents_count = calculate_count_of_documents(documents)
        if documents_count <= 0:
            await message.reply(msg_dict["delete_movie"]["wrong_number"])
        else:
            deleting_movie = db.movie_collection.find({'_id': int(movie)})[0]
            delete_movie_with_picture(deleting_movie)
            await message.reply(msg_dict["delete_movie"]["success"])
            await state.reset_state()
    else:
        documents = list(db.movie_collection.find({'name': movie}))
        documents_count = calculate_count_of_documents(documents)
        if documents_count <= 0:
            await message.reply(msg_dict["delete_movie"]["wrong_name"])
        else:
            deleting_movie = db.movie_collection.find({'name': movie})[0]
            delete_movie_with_picture(deleting_movie)
            await message.reply(msg_dict["delete_movie"]["success"])
            await state.reset_state()


@dp.message_handler(state=States.CHANGE_STATE)
async def update_movie_select(message: types.Message, state: FSMContext):
    movie = message.text
    if movie.lower() == "stop":
        await message.reply("Обновление отменено")
        await state.reset_state()
    elif movie.isdigit():
        documents = list(db.movie_collection.find({'_id': int(movie)}))
        documents_count = calculate_count_of_documents(documents)
        if documents_count <= 0:
            await message.reply(msg_dict["update_movie"]["wrong_number"])
        else:
            admins_dict[message.from_user.id] = MovieUpdater(int(movie))
            await bot.send_message(message.from_user.id, msg_dict["update_movie"]["select_param"],
                                   reply_markup=keyboars.inline_kb_change)
    else:
        documents = list(db.movie_collection.find({'name': movie}))
        documents_count = calculate_count_of_documents(documents)
        if documents_count <= 0:
            await message.reply(msg_dict["update_movie"]["wrong_name"])
        else:
            admins_dict[message.from_user.id] = MovieUpdater(int(documents[0]['_id']))
            await bot.send_message(message.from_user.id, msg_dict["update_movie"]["select_param"],
                                   reply_markup=keyboars.inline_kb_change)


@dp.callback_query_handler(lambda c: c.data[0] == "*", state=States.CHANGE_STATE)
async def update_processor(callback: types.CallbackQuery, state: FSMContext):
    param = callback.data[1:]
    if param == "stop_updating":
        await state.reset_state()
        await bot.send_message(callback.from_user.id, msg_dict["update_movie"]["success"])
        try:
            movie = db.movie_collection.find({"_id": admins_dict[callback.from_user.id].id}).limit(1)[0]
            caption = create_caption(movie)
            await bot.send_photo(callback.from_user.id, photo=movie["picture_id"], caption=caption)
        except KeyError:
            await bot.send_message(callback.from_user.id, msg_dict["update_movie"]["ok_but_check"])
    elif param != "picture_id":
        await assign_new_param_admins_dict(callback, param, state)
        await bot.send_message(callback.from_user.id,
                               "Enter new " + param + ", send stop if you want to cancel entering")
        await States.CHOOSE_CHANGE_STATE.set()
    else:
        await assign_new_param_admins_dict(callback, param, state)
        await bot.send_message(callback.from_user.id, msg_dict["update_movie"]["picture_state"])
        await States.EDIT_PICTURE_STATE.set()


@dp.message_handler(state=States.EDIT_PICTURE_STATE, content_types=ContentTypes.ANY)
async def edit_picture_handler(message: types.Message, state: FSMContext):
    if message.text.lower() == "stop":
        await States.CHANGE_STATE.set()
        await bot.send_message(message.from_user.id, msg_dict["update_movie"]["select_param"],
                               reply_markup=keyboars.inline_kb_change)
    else:
        file = await bot.get_file(message.photo[-1].file_id)
        if file is not None:
            try:
                movie_id = admins_dict[message.from_user.id].id
            except KeyError:
                await bot.send_message(message.from_user.id,
                                       msg_dict["error_msg"]["error_sample"] + msg_dict["error_msg"]["updating_error"])
                await state.reset_state()
                return
            new_picture_id = message["photo"][-1]["file_id"]
            await assign_new_data_admins_dict(message, new_picture_id, state)
            db.movie_collection.update_one({"_id": movie_id}, {"$set": {"picture_id": new_picture_id}})
            await bot.send_message(message.from_user.id, msg_dict["update_movie"]["picture_updated"])
            await States.CHANGE_STATE.set()
            await bot.send_message(message.from_user.id, msg_dict["update_movie"]["select_param"],
                                   reply_markup=keyboars.inline_kb_change)
        else:
            await bot.send_message(message.from_user.id, msg_dict["update_movie"]["picture_state_not_img_error"])


@dp.message_handler(state=States.CHOOSE_CHANGE_STATE)
async def update_info_controller(message: types.Message, state: FSMContext):
    if message.text.lower() == "stop":
        await States.CHANGE_STATE.set()
        await bot.send_message(message.from_user.id, msg_dict["update_movie"]["select_param"],
                               reply_markup=keyboars.inline_kb_change)
    else:
        try:
            await assign_new_data_admins_dict(message, message.text, state)
            updating_movie = admins_dict[message.from_user.id]
            movie_id = updating_movie.id
            if updating_movie.param == "name":
                list_of_names = db.movie_collection.distinct("name")
                list_of_names = [elem.lower() for elem in list_of_names]
                if str(updating_movie.data).lower() in list_of_names:
                    same_movie = \
                        db.movie_collection.find({"name": re.compile(updating_movie.data, re.IGNORECASE)}).limit(1)[0]
                    await bot.send_message(message.from_user.id,
                                           msg_dict["update_movie"]["already_added"].format(name=updating_movie.data,
                                                                                            id=same_movie['_id'],
                                                                                            this_id=movie_id))
            db.movie_collection.update_one({"_id": movie_id}, {"$set": {updating_movie.param: updating_movie.data}})
            await bot.send_message(message.from_user.id, updating_movie.param + " has been updated")
            await States.CHANGE_STATE.set()
            await bot.send_message(message.from_user.id, msg_dict["update_movie"]["select_param"],
                                   reply_markup=keyboars.inline_kb_change)
        except KeyError:
            await bot.send_message(message.from_user.id,
                                   msg_dict["error_msg"]["error_sample"] + msg_dict["error_msg"]["updating_error"])
            await state.reset_state()
            return


@dp.message_handler(state=States.SEND_MESSAGES, content_types=ContentTypes.ANY)
async def start_sending_message_handler(message: types.Message, state: FSMContext):
    if message.text != "stop":
        await state.reset_state()
        users = db.users.find({})
        users_id = []
        for item in users:
            users_id.append(item["user_id"])
        await MessageBroadcaster(users_id, message).run()
    else:
        await state.reset_state()
        await message.reply("Операция отменена")


async def select_movie_function(message: types.Message):
    if not await user_is_channel_member(message.from_user.id):
        await bot.send_message(message.from_user.id, msg_dict["subscribe_msg"]["not_subscribed"])
    else:
        await bot.send_message(message.from_user.id, msg_dict["select_movie"]["choose_param"],
                               reply_markup=keyboars.reply_keyboard_select_movie)
        users_dict[message.from_user.id] = MovieSelector()
        users_select_dict[message.from_user.id] = {}


async def check_selector_values(message: types.Message, exception, state: FSMContext):
    try:
        selector_state = users_dict[message.from_user.id]
    except KeyError:
        await state.reset_state()
        users_select_dict[message.from_user.id] = {}
        users_dict[message.from_user.id] = MovieSelector()
        return {}
    result = {}
    genre = selector_state.genre
    rate = selector_state.rate
    country = selector_state.country
    vector = selector_state.vector
    year = selector_state.year
    result["$match"] = {}
    if genre is not None and exception != "genre":
        result["$match"]["genre"] = genre
    if rate is not None and exception != "rate":
        rates = rate.split("-")
        result["$match"]["rate"] = {"$gte": rates[0], "$lte": rates[1]}
    if country is not None and exception != "country":
        result["$match"]["country"] = country
    if vector is not None and exception != "vector":
        result["$match"]["vector"] = vector
    if year is not None and exception != "year":
        if "-" in year:
            years = year.split("-")
            result["$match"]["year"] = {"$gte": int(years[0]), "$lte": int(years[1])}
        else:
            result["$match"]["year"] = int(year)
    return result


async def create_find_parameter(user_id, state: FSMContext):
    try:
        selector_state = users_dict[user_id]
    except KeyError:
        keyboard_state = db.users.find({"user_id": user_id}).limit(1)[0]["keyboard"]
        if keyboard_state == 1:
            reply_markup = keyboars.reply_keyboards_list[1]
        else:
            reply_markup = keyboars.reply_keyboards_list[0]
        await bot.send_message(user_id,
                               msg_dict["error_msg"]["choosing_movie_error"], reply_markup=reply_markup)
        await state.reset_state()
        return False
    result = {}
    genre = selector_state.genre
    rate = selector_state.rate
    country = selector_state.country
    vector = selector_state.vector
    year = selector_state.year
    if genre is not None:
        result["genre"] = {"$in": [genre]}
    if rate is not None:
        rates = rate.split("-")
        if rates[1] == "10.0":
            result["rate"] = {"$gte": rates[0], "$lte": '9.9'}
        result["rate"] = {"$gte": rates[0], "$lte": rates[1]}
    if country is not None:
        result["country"] = {"$in": [country]}
    if vector is not None:
        result["vector"] = {"$in": [vector]}
    if year is not None:
        if "-" in year:
            years = year.split("-")
            result["year"] = {"$gte": int(years[0]), "$lte": int(years[1])}
        else:
            result["year"] = int(year)
    return result


async def find_unique_items(line, parameters):
    if len(parameters) != 0:
        items = list(db.movie_collection.aggregate(
            [parameters, {"$unwind": "$" + line}, {"$group": {"_id": "$" + line, "count": {"$sum": 1}}},
             {"$sort": {"count": pymongo.DESCENDING}}, {"$group": {"_id": None, "set": {"$push": "$_id"}}}]))[0]
        items_list = items["set"]
    else:
        items = list(db.movie_collection.aggregate(
            [{"$unwind": "$" + line}, {"$group": {"_id": "$" + line, "count": {"$sum": 1}}},
             {"$sort": {"count": pymongo.DESCENDING}}, {"$group": {"_id": None, "set": {"$push": "$_id"}}}]))[0]
        items_list = items["set"]
    return items_list


def split_items(parameters):
    result = {}
    pages = 1
    while pages <= math.ceil(len(parameters) / 4):
        items_list = []
        counter = 0
        while counter < 4 and (counter + (pages - 1) * 4) < len(parameters):
            items_list.append(parameters[counter + (pages - 1) * 4])
            counter = counter + 1
        result[pages] = items_list
        pages = pages + 1
    result["current"] = 1
    return result


controls = ["<<", "Отмена", ">>"]
select_movie_controls = [{"<<": "<<"}, {"Удалить": "Удалить"}, {">>": ">>"}]
year_groups = ["2000-2010", "1990-1999", "1980-1989", "1-1979"]
rate_group = ["8.0-10.0", "7.0-7.9", "6.0-6.9", "1.0-5.9"]


def edit_year_list(items, current_year_group):
    length = len(current_year_group)
    resulting_items = items.copy()
    resulting_years = []
    for i in range(len(current_year_group)):
        current_years = str(current_year_group[length - i - 1])
        current_years_list = current_years.split("-")
        greatest_year = int(current_years_list[1])
        start_len = len(resulting_items)
        resulting_items = [item for item in resulting_items if int(item) > greatest_year]
        end_len = len(resulting_items)
        if end_len < start_len:
            resulting_years.insert(0, 1)
        else:
            resulting_years.insert(0, 0)
    length = len(resulting_years)
    resulting_items.sort(reverse=True)
    for i in range(len(resulting_items)):
        resulting_items[i] = {resulting_items[i]: resulting_items[i]}
    for i in range(len(resulting_years)):
        if resulting_years[i] == 1:
            if i == (length - 1):
                resulting_items.append({"до 1980": "1-1979"})
            else:
                resulting_items.append({year_groups[i]: year_groups[i]})
    return resulting_items


def edit_rate_list(items, current_rate_group):
    length = len(current_rate_group)
    resulting_items = items.copy()
    resulting_rate = []
    for i in range(len(current_rate_group)):
        current_rates = str(current_rate_group[length - i - 1])
        current_rate_list = current_rates.split("-")
        greatest_rate = float(current_rate_list[1])
        start_len = len(resulting_items)
        resulting_items = [item for item in resulting_items if float(item) > greatest_rate]
        end_len = len(resulting_items)
        if end_len < start_len:
            resulting_rate.insert(0, 1)
        else:
            resulting_rate.insert(0, 0)
    length = len(resulting_rate)
    for i in range(len(resulting_rate)):
        if resulting_rate[i] == 1:
            if i == (length - 1):
                resulting_items.append({"до 5.9": "1.0-5.9"})
            else:
                resulting_items.append({rate_group[i]: rate_group[i]})
    return resulting_items


def edit_to_dict(items, parameter):
    if parameter != "genre":
        for i in range(len(items)):
            items[i] = {items[i]: items[i]}
        return items
    else:
        for i in range(len(items)):
            items[i] = {items[i].capitalize(): items[i]}
        return items


async def send_select_inline_keyboard(message: types.Message, parameter, text, state: FSMContext):
    parameters = await check_selector_values(message, parameter, state)
    items = await find_unique_items(parameter, parameters)
    items = edit_to_dict(items, parameter)
    splitted_items = split_items(items)
    users_select_dict[message.from_user.id][parameter] = splitted_items
    front_marker = "$" + parameter[0]
    keyboard = create_keyboard_process(splitted_items, front_marker)
    await bot.send_message(message.from_user.id, text=str(text), reply_markup=keyboard)


def create_caption(movie):
    caption = f"Номер:{movie['_id']}\nНазвание:{movie['name']}\nЖанр:{movie['genre']}\n" \
              f"Год:{movie['year']}\nСтрана:{movie['country']}\nНаправление:{movie['vector']}\nРейтинг:{movie['rate']}\n" \
              f"Ссылка на просмотр:{movie['link']}\nТрейлер:{movie['trailer']}\nОписание:{movie['description']}"
    return caption


async def send_movie_list(user: types.User, movie):
    keyboard = keyboars.full_movie_inline_keyboard
    caption = create_caption_for_users(movie)
    await bot.send_photo(user.id, photo=movie["picture_id"], caption=caption, reply_markup=keyboard, parse_mode="HTML")


@dp.message_handler(commands=["select_movie"])
async def select_movie_handler(message: types.Message):
    await select_movie_function(message)


def create_keyboard(items, front_marker):
    keyboard_main = keyboars.create_keyboard(items, front_marker, items_in_row=2)
    add_controls_to_keyboard(keyboard_main, front_marker)
    return keyboard_main


async def check_and_edit_previous(callback: types.CallbackQuery, line, state: FSMContext):
    message = callback.message
    try:
        current_selecting_state = users_select_dict[callback.from_user.id]
    except KeyError:
        await callback.message.delete()
        await bot.send_message(callback.from_user.id,
                               msg_dict["error_msg"]["choosing_movie_error"],
                               reply_markup=keyboars.reply_keyboards_list[
                                   db.users.find({"user_id": message.from_user.id}).limit(1)[0]["keyboard"]])
        await state.reset_state()
        return
    current_state = current_selecting_state[line]["current"]
    if current_state == 1:
        current_state = len(list(current_selecting_state[line].keys())) - 1
    else:
        current_state = current_state - 1
    users_select_dict[callback.from_user.id][line]["current"] = current_state
    front_marker = "$" + line[0]
    keyboard = create_keyboard(current_selecting_state[line][current_state], front_marker)
    await message.edit_reply_markup(reply_markup=keyboard)


async def check_and_edit_next(callback: types.CallbackQuery, line, state):
    message = callback.message
    try:
        current_selecting_state = users_select_dict[callback.from_user.id]
    except KeyError:
        await callback.message.delete()
        await bot.send_message(callback.from_user.id,
                               msg_dict["error_msg"]["choosing_movie_error"],
                               reply_markup=keyboars.reply_keyboards_list[db.users.find(
                                   {"user_id": message.from_user.id}).limit(1)[0]["keyboard"]])
        await state.reset_state()
        return
    current_state = current_selecting_state[line]["current"]
    if current_state == len(list(current_selecting_state[line].keys())) - 1:
        current_state = 1
    else:
        current_state = current_state + 1
    users_select_dict[callback.from_user.id][line]["current"] = current_state
    front_marker = "$" + line[0]
    keyboard = create_keyboard(current_selecting_state[line][current_state], front_marker)
    await message.edit_reply_markup(reply_markup=keyboard)


@dp.callback_query_handler(lambda c: c.data[0] == "$")
async def select_movie_callback_handler(callback: types.CallbackQuery, state: FSMContext):
    callback_data = callback.data[1:]
    if "<<" in callback_data:
        if callback_data[0] == "g":
            await check_and_edit_previous(callback, "genre", state)
        if callback_data[0] == "y":
            await check_and_edit_previous(callback, "year", state)
        if callback_data[0] == "c":
            await check_and_edit_previous(callback, "country", state)
        if callback_data[0] == "v":
            await check_and_edit_previous(callback, "vector", state)
        if callback_data[0] == "r":
            await check_and_edit_previous(callback, "rate", state)
        if callback_data[0] == "m":
            try:
                current_movie_list_state = users_selected_movies[callback.from_user.id]
            except KeyError:
                await bot.send_message(callback.from_user.id,
                                       msg_dict["error_msg"]["choosing_movie_error"])
                await state.reset_state()
                return
            current_state = current_movie_list_state["current"]
            if current_state == 0:
                current_state = calculate_count_of_documents(current_movie_list_state["movies"]) - 1
            else:
                current_state = current_state - 1
            keyboard = keyboars.full_movie_inline_keyboard
            users_selected_movies[callback.from_user.id]["current"] = current_state
            caption = create_caption_for_users(current_movie_list_state["movies"][current_state])
            picture_id = current_movie_list_state["movies"][current_state]['picture_id']
            await callback.message.edit_media(
                media=types.InputMediaPhoto(media=picture_id, caption=caption, parse_mode="HTML"),
                reply_markup=keyboard)
    elif ">>" in callback_data:
        if callback_data[0] == "g":
            await check_and_edit_next(callback, "genre", state)
        if callback_data[0] == "y":
            await check_and_edit_next(callback, "year", state)
        if callback_data[0] == "c":
            await check_and_edit_next(callback, "country", state)
        if callback_data[0] == "v":
            await check_and_edit_next(callback, "vector", state)
        if callback_data[0] == "r":
            await check_and_edit_next(callback, "rate", state)
        if callback_data[0] == "m":
            try:
                current_movie_list_state = users_selected_movies[callback.from_user.id]
            except KeyError:
                await bot.send_message(callback.from_user.id,
                                       msg_dict["error_msg"]["choosing_movie_error"])
                await state.reset_state()
                return
            current_state = current_movie_list_state["current"]
            if current_state == calculate_count_of_documents(current_movie_list_state["movies"]) - 1:
                current_state = 0
            else:
                current_state = current_state + 1
            keyboard = keyboars.full_movie_inline_keyboard
            users_selected_movies[callback.from_user.id]["current"] = current_state
            caption = create_caption_for_users(current_movie_list_state["movies"][current_state])
            picture_id = current_movie_list_state["movies"][current_state]['picture_id']
            await callback.message.edit_media(
                media=types.InputMediaPhoto(media=picture_id, caption=caption, parse_mode="HTML"),
                reply_markup=keyboard)
    elif "Отмена" in callback_data:
        try:
            users_dict[callback.from_user.id]
        except KeyError:
            await state.reset_state()
            await callback.message.delete()
            return
        if callback_data[0] == "g":
            await bot.send_message(callback.from_user.id, msg_dict["select_movie"]["genre_cancel"])
        if callback_data[0] == "y":
            await bot.send_message(callback.from_user.id, msg_dict["select_movie"]["year_cancel"])
        if callback_data[0] == "c":
            await bot.send_message(callback.from_user.id, msg_dict["select_movie"]["country_cancel"])
        if callback_data[0] == "v":
            await bot.send_message(callback.from_user.id, msg_dict["select_movie"]["vector_cancel"])
        if callback_data[0] == "r":
            await bot.send_message(callback.from_user.id, msg_dict["select_movie"]["rate_cancel"])
        await callback.message.delete()
    elif "Delete" in callback_data:
        await callback.message.delete()
        try:
            users_selected_movies.pop(callback.from_user.id)
            if "o" not in callback_data:
                await bot.send_message(callback.from_user.id, msg_dict["select_movie"]["list_deleted"])
        except KeyError:
            await state.reset_state()
            return
    elif "Description" in callback_data:
        try:
            current_movie_list_state = users_selected_movies[callback.from_user.id]
            current_movie_num = current_movie_list_state["current"]
            description = create_description_for_users(current_movie_list_state["movies"][current_movie_num])
            if "f" in callback_data:
                reply_keyboard = keyboars.full_movie_replace_description_keyboard
            else:
                reply_keyboard = keyboars.one_movie_full_info_keyboard
            await callback.message.edit_caption(description, reply_markup=reply_keyboard, parse_mode="HTML")
        except KeyError as e:
            await bot.send_message(callback.from_user.id, msg_dict["error_msg"]["choosing_movie_error"])
            await callback.message.delete()
            print(e.with_traceback(sys.exc_info()[2]))
            return
    elif "Data" in callback_data:
        try:
            current_movie_list_state = users_selected_movies[callback.from_user.id]
            current_movie_num = current_movie_list_state["current"]
            caption = create_caption_for_users(current_movie_list_state["movies"][current_movie_num])
            if "f" in callback_data:
                reply_keyboard = keyboars.full_movie_inline_keyboard
            else:
                reply_keyboard = keyboars.one_movie_inline_keyboard
            await callback.message.edit_caption(caption, reply_markup=reply_keyboard, parse_mode="HTML")
        except KeyError:
            await bot.send_message(callback.from_user.id, msg_dict["error_msg"]["choosing_movie_error"])
            await callback.message.delete()
            return
    else:
        try:
            current_state = users_dict[callback.from_user.id]
        except KeyError:
            await bot.send_message(callback.from_user.id, msg_dict["error_msg"]["choosing_movie_error"])
            await state.reset_state()
            await callback.message.delete()
            return
        if callback_data[0] == "g":
            current_state.genre = callback_data[1:]
            users_dict[callback.from_user.id] = current_state
            await bot.send_message(callback.from_user.id, msg_dict["select_movie"]["genre_selected"])
        if callback_data[0] == "y":
            current_state.year = callback_data[1:]
            users_dict[callback.from_user.id] = current_state
            await bot.send_message(callback.from_user.id, msg_dict["select_movie"]["year_selected"])
        if callback_data[0] == "c":
            current_state.country = callback_data[1:]
            users_dict[callback.from_user.id] = current_state
            await bot.send_message(callback.from_user.id, msg_dict["select_movie"]["country_selected"])
        if callback_data[0] == "v":
            current_state.vector = callback_data[1:]
            users_dict[callback.from_user.id] = current_state
            await bot.send_message(callback.from_user.id, msg_dict["select_movie"]["vector_selected"])
        if callback_data[0] == "r":
            current_state.rate = callback_data[1:]
            users_dict[callback.from_user.id] = current_state
            await bot.send_message(callback.from_user.id, msg_dict["select_movie"]["rate_selected"])
        await callback.message.delete()


@dp.callback_query_handler(lambda c: c.data[0:2] == "s?")
async def select_sort_parameter(callback: types.CallbackQuery, state: FSMContext):
    callback_data = callback.data[2:]
    find_parameter = await create_find_parameter(callback.from_user.id, state)
    movies = None
    await callback.message.delete()
    try:
        users_dict.pop(callback.from_user.id)
        users_select_dict.pop(callback.from_user.id)
    except KeyError:
        print(str(callback.from_user.id) + " data have been deleted already")
    if callback_data != "rnd":
        if callback_data == "n":
            movies = list(db.movie_collection.find(find_parameter).sort("year", -1))
        elif callback_data == "o":
            movies = list(db.movie_collection.find(find_parameter).sort("year", 1))
        elif callback_data == "b":
            movies = list(db.movie_collection.find(find_parameter).sort("rate", -1))
        elif callback_data == "w":
            movies = list(db.movie_collection.find(find_parameter).sort("rate", 1))
        if movies is not None:
            movie = movies[0]
            movies_dictionary = {"current": 0, "movies": movies}
            users_selected_movies[callback.from_user.id] = movies_dictionary
            await send_movie_list(callback.from_user, movie)
        else:
            await bot.send_message(callback.from_user.id, msg_dict["error_msg"]["choosing_movie_error"])
    else:
        movie = random.choice(list(db.movie_collection.find(find_parameter)))
        await bot.send_photo(callback.from_user.id, photo=movie["picture_id"],
                             caption=create_caption_for_users(movie), parse_mode="HTML",
                             reply_markup=keyboars.one_movie_description_keyboard)
        movies_dictionary = {"current": 0, "movies": [movie]}
        users_selected_movies[callback.from_user.id] = movies_dictionary


async def random_movie(message: types.Message, search_param: dict):
    if not await user_is_channel_member(message.from_user.id):
        await bot.send_message(message.from_user.id, msg_dict["subscribe_msg"]["not_subscribed"])
    else:
        document = list(db.movie_collection.aggregate([{"$sample": {"size": 1}}]))
        movie = document[0]
        while movie is None:
            document = list(db.movie_collection.aggregate([{"$sample": {"size": 1}}]))
            movie = document[0]
        caption = create_caption_for_users(movie)
        movies_dictionary = {"current": 0, "movies": [movie]}
        users_selected_movies[message.from_user.id] = movies_dictionary
        await bot.send_photo(message.from_user.id, photo=movie["picture_id"], caption=caption, parse_mode="HTML",
                             reply_markup=keyboars.one_movie_description_keyboard)


def add_controls_to_keyboard(keyboard: types.InlineKeyboardMarkup, front_marker):
    prev_btn = keyboars.InlineKeyboardButton(controls[0], callback_data=(front_marker + controls[0]))
    cancel_btn = keyboars.InlineKeyboardButton(controls[1], callback_data=(front_marker + controls[1]))
    next_btn = keyboars.InlineKeyboardButton(controls[2], callback_data=(front_marker + controls[2]))
    keyboard.row(prev_btn, cancel_btn, next_btn)


def create_keyboard_process(items, front_marker):
    keyboard_main = keyboars.create_keyboard(items[1], front_marker, 2)
    if len(list(items.keys())) > 2:
        add_controls_to_keyboard(keyboard_main, front_marker)
    else:
        cancel_btn = keyboars.InlineKeyboardButton("Отмена", callback_data=(front_marker + "Отмена"))
        keyboard_main.row(cancel_btn)
    return keyboard_main


@dp.message_handler(commands=["random_movie"])
async def random_movie_handler(message: types.Message):
    await random_movie(message, {})


@dp.message_handler(content_types=ContentTypes.ANY)
async def simple_message_controller(message: types.Message, state: FSMContext):
    if not await user_is_channel_member(message.from_user.id):
        await bot.send_message(message.from_user.id, msg_dict["subscribe_msg"]["not_subscribed"])
    else:
        try:
            text = message.text
        except Exception:
            await message.reply(msg_dict["error_msg"]["unknown_msg"])
            return
        if text.isdigit():
            number = int(text)
            try:
                movie = db.movie_collection.find({"_id": number}).limit(1)[0]
            except IndexError:
                await bot.send_message(message.from_user.id, msg_dict["error_msg"]["no_such_film"])
                return
            users_selected_movies[message.from_user.id] = {"current": 0, "movies": [movie]}
            caption = create_caption_for_users(movie)
            await bot.send_photo(message.from_user.id, photo=movie["picture_id"], caption=caption, parse_mode="HTML",
                                 reply_markup=keyboars.one_movie_description_keyboard)
        elif text == "Подобрать фильм✔":
            await select_movie_function(message)
        elif text == "Случайный фильм🎲":
            await random_movie(message, {})
        elif text == "Жанр🥸":
            await send_select_inline_keyboard(message, "genre", "Выберите жанр фильма:", state)
        elif text == "Год✨":
            parameters = await check_selector_values(message, "year", state)
            items = await find_unique_items("year", parameters)
            edited_items = edit_year_list(items, year_groups)
            splitted_items = split_items(edited_items)
            users_select_dict[message.from_user.id]["year"] = splitted_items
            front_marker = "$y"
            keyboard = create_keyboard_process(splitted_items, front_marker)
            await bot.send_message(message.from_user.id, "Выберите год фильма:", reply_markup=keyboard)
        elif text == "Страна🏳":
            await send_select_inline_keyboard(message, "country", "Выберите страну, в которой был снят фильм:", state)
        elif text == "Направление🎟":
            await send_select_inline_keyboard(message, "vector", "Выберите направление фильма:", state)
        elif text == "Рейтинг⭐":
            parameters = await check_selector_values(message, "rate", state)
            items = await find_unique_items("rate", parameters)
            edited_items = edit_rate_list(items, rate_group)
            keyboard_main = keyboars.create_keyboard(edited_items, front_marker="$r", items_in_row=2)
            keyboard_main.row(keyboars.InlineKeyboardButton("Отмена", callback_data="$rОтмена"))
            await bot.send_message(message.from_user.id, "Выберите рейтинг фильма:", reply_markup=keyboard_main)
        elif text == "Отмена❌":
            try:
                users_dict.pop(message.from_user.id)
                users_select_dict.pop(message.from_user.id)
            except KeyError:
                print(str(message.from_user.id) + " data have been deleted already")
            await bot.send_message(message.from_user.id, msg_dict["select_movie"]["cancel"],
                                   reply_markup=keyboars.reply_keyboards_list[
                                       db.users.find({"user_id": message.from_user.id}).limit(1)[0]["keyboard"]])
        elif text == "Выбрать фильм✔":
            # users_selected_movies[message.from_user.id] = []
            find_parameter = await create_find_parameter(message.from_user.id, state)
            if not isinstance(find_parameter, bool):
                if len(find_parameter) >= 0:
                    if find_parameter == {}:
                        movies = list(db.movie_collection.aggregate([{"$sample": {"size": 10}}]))
                    else:
                        movies = list(db.movie_collection.find(find_parameter).sort("rate", -1))
                    movie = movies[0]
                    length = len(movies)
                    print(length)
                    if length <= 0:
                        await bot.send_message(message.from_user.id, msg_dict["select_movie"]["excusing"])
                    elif length > 1:
                        await bot.send_message(message.from_user.id, msg_dict["select_movie"]["selected_movies"],
                                               reply_markup=keyboars.reply_keyboards_list[db.users.find(
                                                   {"user_id": message.from_user.id}).limit(1)[0]["keyboard"]])
                        await bot.send_message(message.from_user.id, msg_dict["select_movie"]["sort_phrase"],
                                               reply_markup=keyboars.sorting_keyboard)
                    elif movie is not None:
                        users_selected_movies[message.from_user.id] = {"current": 0, "movies": movies}
                        await bot.send_message(message.from_user.id, msg_dict["select_movie"]["selected_movies"],
                                               reply_markup=keyboars.reply_keyboards_list[db.users.find(
                                                   {"user_id": message.from_user.id}).limit(1)[0]["keyboard"]])
                        await bot.send_photo(message.from_user.id, photo=movie["picture_id"],
                                             caption=create_caption_for_users(movie), parse_mode="HTML",
                                             reply_markup=keyboars.one_movie_description_keyboard)
                        try:
                            users_dict.pop(message.from_user.id)
                            users_select_dict.pop(message.from_user.id)
                        except KeyError:
                            print(str(message.from_user.id) + " data have been deleted already")
            else:
                await bot.send_message(message.from_user.id, msg_dict["select_movie"]["no_parameters_error"])
        elif text[1] == "/":
            await bot.send_message(message.from_user.id, msg_dict["error_msg"]["unknown_command"])
        else:
            try:
                name_without_punctuation = ""
                for char in text:
                    if char not in punctuations:
                        name_without_punctuation += char
                movie = db.movie_collection.find({"$text": {"$search": name_without_punctuation}},
                                                 {"score": {"$meta": "textScore"}}).sort(
                    "score", {"$meta": "textScore"}).limit(1)[0]
            except IndexError:
                await message.reply(msg_dict["error_msg"]["unknown_msg"])
                return
            users_selected_movies[message.from_user.id] = {"current": 0, "movies": [movie]}
            caption = create_caption_for_users(movie)
            await bot.send_photo(message.from_user.id, photo=movie["picture_id"], caption=caption, parse_mode="HTML",
                                 reply_markup=keyboars.one_movie_description_keyboard)


if __name__ == '__main__':
    executor.start_polling(dp)
