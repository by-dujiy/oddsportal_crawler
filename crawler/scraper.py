from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from time import sleep
from .utility import get_from_settings
import pathlib
import os
import random
import logging


MAIN_URL = "https://www.oddsportal.com/"
LINK_LIST = []

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
    )

current_path = pathlib.Path(os.getcwd())
driver_path = current_path / 'chromedriver' / 'chromedriver.exe'

user_agent = get_from_settings('user_agents')

chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument(f"user-agent={random.choice(user_agent)}")

driver = webdriver.Chrome(
    service=Service(driver_path),
    options=chrome_options
    )
driver.maximize_window()


def aprove_cookie():
    driver.get(MAIN_URL)
    sleep(2)
    cookie_button = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((
            By.XPATH,
            "//button[@id='onetrust-accept-btn-handler']"))
    )
    cookie_button.click()


def get_pagination(driver, year):
    driver.get(f"{MAIN_URL}baseball/usa/mlb-{year}/results/")
    sleep(1)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
    pagination = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((
            By.XPATH,
            "//div[contains(@class, 'pagination')]"))
    )
    pag_list = pagination.find_elements(By.XPATH, "//a[@data-number]")
    return pag_list[-1].get_attribute('data-number')


def scraping_urls(driver, year, page):
    driver.get(f"{MAIN_URL}baseball/usa/mlb-{year}/results/#/page/{page}/")
    sleep(2)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
    sleep(0.5)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
    footer = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((
            By.XPATH,
            "//footer[contains(@class, 'flex')]"
        ))
    )
    ActionChains(driver).scroll_to_element(footer).perform()
    soup = BeautifulSoup(driver.page_source, "lxml")
    events = soup.find_all('div', class_='eventRow')
    for n, event in enumerate(events, 1):
        url_link = event.find('a').get('href')
        logging.info(f"---- row {n}, url: {url_link}")
        LINK_LIST.append(url_link)


def scraping_eventrow():
    for year in range(2016, 2025):
        logging.info(f"year {year}")
        max_pagination = get_pagination(driver, year)
        for p in range(1, int(max_pagination)+1):
            logging.info(f"-- page: {p}")
            scraping_urls(driver, year, p)


def run_crawler():
    aprove_cookie()
    scraping_eventrow()
    driver.guit()
