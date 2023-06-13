from aiogram.types import ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, \
    InlineKeyboardButton

confirmation_button = InlineKeyboardButton("Да", callback_data="confirm")
refusing_button = InlineKeyboardButton("Нет", callback_data="refuse")
inline_kb_confirm = InlineKeyboardMarkup(row_width=2).row(confirmation_button, refusing_button)

name_button = InlineKeyboardButton("Название", callback_data="*name")
genre_button = InlineKeyboardButton("Жанр", callback_data="*genre")
year_button = InlineKeyboardButton("Год", callback_data="*year")
vector_button = InlineKeyboardButton("Направление", callback_data="*vector")
rate_button = InlineKeyboardButton("Рейтинг", callback_data="*rate")
link_button = InlineKeyboardButton("Ссылка", callback_data="*link")
description_button = InlineKeyboardButton("Описание", callback_data="*description")
country_button = InlineKeyboardButton("Страна", callback_data="*country")
trailer_button = InlineKeyboardButton("Трейлер", callback_data="*trailer")
picture_button = InlineKeyboardButton("Обложка", callback_data="*picture_id")
stop_changing = InlineKeyboardButton("Закончить редактирование", callback_data="*stop_updating")
inline_kb_change = InlineKeyboardMarkup(row_width=2).row(name_button, genre_button).row(year_button, vector_button).row(
    rate_button, link_button).row(description_button, country_button).row(trailer_button, picture_button).add(
    stop_changing)

reply_genre_button = KeyboardButton("Жанр🥸")
reply_year_button = KeyboardButton("Год✨")
reply_country_button = KeyboardButton("Страна🏳")
reply_vector_button = KeyboardButton("Направление🎟")
reply_rate_button = KeyboardButton("Рейтинг⭐")
reply_cancel_button = KeyboardButton("Отмена❌")
reply_confirm_button = KeyboardButton("Выбрать фильм✔")

reply_keyboard_select_movie = ReplyKeyboardMarkup(resize_keyboard=True).row(reply_genre_button, reply_year_button,
                                                                            reply_country_button).row(
    reply_vector_button,
    reply_rate_button).row(
    reply_cancel_button, reply_confirm_button)

select_movie_button = KeyboardButton("Подобрать фильм✔")
random_movie_button = KeyboardButton("Случайный фильм🎲")

start_reply_keyboard = ReplyKeyboardMarkup(resize_keyboard=True).row(select_movie_button, random_movie_button)
delete_reply_keyboard = ReplyKeyboardRemove()

reply_keyboards_list = [delete_reply_keyboard, start_reply_keyboard]

new_films_btn = InlineKeyboardButton("Новые", callback_data="s?n")
old_films_btn = InlineKeyboardButton("Старые", callback_data="s?o")
best_films_btn = InlineKeyboardButton("Высокий рейтинг", callback_data="s?b")
worst_films_btn = InlineKeyboardButton("Низкий рейтинг", callback_data="s?w")
random_movie_inline_btn = InlineKeyboardButton("Случайный фильм", callback_data="s?rnd")
cancel_sorting_btn = InlineKeyboardButton("Отмена", callback_data="s?c")
sorting_keyboard = InlineKeyboardMarkup().row(new_films_btn, old_films_btn, random_movie_inline_btn).row(best_films_btn,
                                                                                                         worst_films_btn).add(
    cancel_sorting_btn)

prev_btn = InlineKeyboardButton("<<", callback_data="$m<<")
next_btn = InlineKeyboardButton(">>", callback_data="$m>>")
delete_movie_btn = InlineKeyboardButton("Удалить", callback_data="$mDelete")
description_for_full_movie_list_btn = InlineKeyboardButton("Описание", callback_data="$mfDescription")
full_info_for_movie_list_btn = InlineKeyboardButton("Подробная информация", callback_data="$mfData")
description_for_movie_btn = InlineKeyboardButton("Описание", callback_data="$mDescription")
full_info_for_one_movie_btn = InlineKeyboardButton("Подробно", callback_data="$mData")
delete_for_one_movie_btn = InlineKeyboardButton('Удалить', callback_data='$moDelete')

full_movie_inline_keyboard = InlineKeyboardMarkup().add(description_for_full_movie_list_btn).row(prev_btn,
                                                                                                 delete_movie_btn,
                                                                                                 next_btn)
one_movie_inline_keyboard = InlineKeyboardMarkup().row(description_for_movie_btn, delete_movie_btn)

full_movie_replace_description_keyboard = InlineKeyboardMarkup().add(full_info_for_movie_list_btn).row(prev_btn,
                                                                                                       delete_movie_btn,
                                                                                                       next_btn)
one_movie_replace_description_keyboard = InlineKeyboardMarkup().row(full_info_for_one_movie_btn, delete_movie_btn)

one_movie_description_keyboard = InlineKeyboardMarkup().row(description_for_movie_btn, delete_for_one_movie_btn)
one_movie_full_info_keyboard = InlineKeyboardMarkup().row(full_info_for_one_movie_btn, delete_for_one_movie_btn)


def create_keyboard(items, front_marker, items_in_row):
    inline_kb = InlineKeyboardMarkup(row_width=items_in_row)
    for elem in items:
        for key in elem:
            callback_data = str(front_marker) + str(elem[key])
            current_btn = InlineKeyboardButton(str(key), callback_data=callback_data)
            inline_kb.insert(current_btn)
    return inline_kb


def join_keyboards(kb_list):
    resulting_kb = InlineKeyboardMarkup()
    for elem in kb_list:
        resulting_kb.add(elem)
    return resulting_kb
