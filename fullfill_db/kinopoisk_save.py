from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Создание экземпляра драйвера Chrome
driver = webdriver.Firefox()

page = 1
# Загрузка веб-страницы
while page <= 20:
    driver.get(f"https://www.kinopoisk.ru/lists/movies/popular-films/?page={page}")

    # Ожидание полной загрузки страницы (10 секунд таймаут)
    wait = WebDriverWait(driver, 10)
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

    # Получение содержимого HTML
    html_content = driver.page_source

    # Сохранение содержимого HTML в файл
    with open(f"./pages_kp/page_{page}.html", "w", encoding="utf-8") as file:
        file.write(html_content)
    page += 1

# Закрытие браузера
driver.quit()
