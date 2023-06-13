import json
from bs4 import BeautifulSoup

movie_id_array = []
pages = 1
while pages <= 18:
    with open('./pages_kp/page_%d.html' % pages, encoding="utf-8") as file:
        data = file.read()
        soup = BeautifulSoup(data, features="html.parser")
        film_ids = soup.findAll('a', {'class': 'base-movie-main-info_link__YwtP1'})
        for elem in film_ids:
            mov_id = str(elem.get('href').split('/')[2])
            if mov_id not in movie_id_array:
                movie_id_array.append(mov_id)
        pages += 1

with open('./movie_list/movies_id_second.json', 'w') as file:
    json.dump({'data': movie_id_array}, file)
#
# from kinopoisk_api import KP
#
#
# kinopoisk = KP(token='3c4f094f-b98a-42e0-b39f-1f9ea363f7be')
#
# print(kinopoisk.about, kinopoisk.version)
#
#
# line_to_replace = ' '
#
#
#
# with open("./movie_list/movies_id.json") as file:
#     ids = json.load(file)['data']
#
# movie = kinopoisk.get_film(ids[144]).__dict__
# movie['description'] = movie['description'].replace('\xa0', " ")
# print(movie['description'])
#
# with open('./movie_list/error_movie.json', "w", encoding="utf-8") as file:
#     json.dump(movie, file, ensure_ascii=False)
# from kinopoisk_unofficial.kinopoisk_api_client import KinopoiskApiClient
from kinopoisk_unofficial.request.films.film_request import FilmRequest
# from kinopoisk_unofficial.request.films.film_video_request import FilmVideoRequest
#
# api_client = KinopoiskApiClient('3c4f094f-b98a-42e0-b39f-1f9ea363f7be')
# request = FilmVideoRequest(1392550)
# response = api_client.films.send_film_video_request(request).__dict__
# with open("./movie_list/new_kinopoisk_api/movie_sample.json", "w", encoding="utf-8") as file:
#     file.write(str(response))
