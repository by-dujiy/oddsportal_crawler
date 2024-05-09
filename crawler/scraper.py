from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver import ActionChains
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from .utility import get_from_settings
from db import EventRow, Session
from time import sleep
from datetime import datetime
import pathlib
import os
import random
import logging


MAIN_URL = "https://www.oddsportal.com/"
CURRENT_YEAR = datetime.now().year

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
    )

current_path = pathlib.Path(os.getcwd())
driver_path = current_path / 'chromedriver' / 'chromedriver.exe'

user_agent = get_from_settings('user_agents')

chrome_options = Options()
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


def get_pagination(driver, year: int) -> int:
    logging.info(f"current year - {CURRENT_YEAR}")
    if year == CURRENT_YEAR:
        driver.get(f"{MAIN_URL}baseball/usa/mlb/results/")
    else:
        driver.get(f"{MAIN_URL}baseball/usa/mlb-{year}/results/")
    sleep(1)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
    sleep(3)
    pagination = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((
            By.XPATH,
            "//div[contains(@class, 'pagination')]"))
    )
    soup = BeautifulSoup(driver.page_source, "lxml")
    pagination = soup.find_all('a', attrs={'data-number': True})
    return int(pagination[-1].text)


def scraping_urls(driver, year, page):
    if year == CURRENT_YEAR:
        driver.get(f"{MAIN_URL}baseball/usa/mlb/results/#/page/{page}/")
    else:
        driver.get(f"{MAIN_URL}baseball/usa/mlb-{year}/results/#/page/{page}/")
    sleep(1)
    driver.refresh()
    sleep(4)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
    sleep(1)
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
    with Session() as session:
        with session.begin():
            for n, event in enumerate(events, 1):
                event_id = event.get('id')
                url = event.find('a', class_='w-full').get('href')
                logging.info(f"---- row {n}, url: {url}, id: {event_id}")
                row = EventRow(event_id=event_id, event_url=url)
                session.add(row)
                logging.info(f"added {row}")


def scraping_eventrow(first_year: int = 2016, last_year: int = 2024):
    """
    Composite function for scraping event rows
    Scraping even url's from pages and save in db
    """
    for year in range(first_year, last_year+1):
        logging.info(f"year {year}")
        max_pagination = get_pagination(driver, year)
        for p in range(1, int(max_pagination)+1):
            logging.info(f"-- page: {p}")
            scraping_urls(driver, year, p)


def scraping_event_data(event_url):
    driver.get(MAIN_URL+event_url[1:])
    data_frame = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((
            By.XPATH,
            "//main/div[3]/div[2]/div[1]/div[2]"))
    )
    event_date = data_frame.find_element(By.XPATH, "./div[1]/p[2]").text
    # catching exception if event was canceled
    try:
        res = data_frame.find_element(By.XPATH,
                                      "./div[3]/div[2]/strong").text
    except NoSuchElementException:
        res = 'canceled!'
    finally:
        final_res = res

    teams = driver.find_elements(By.XPATH,
                                 "//span[contains(@class, 'truncate')]")

    # scraping home/away partition
    # find particular bookbaker
    bookmakers = driver.find_elements(
        By.XPATH,
        "//div[contains(@class, 'border-black-borders flex h-9 border-b')]")
    for elem in bookmakers:
        if elem.find_element(By.XPATH, "./div/a[2]/p").text == 'Pinnacle':
            pinnacle_elem = elem
            break
    # processing particular bookmeker and tooltips
    # team 1 processing
    ha_t1_clos_odd_elem = pinnacle_elem.find_element(
        By.XPATH, "./div[2]//p[@class='height-content']")
    print("ha t1 closing odds:", ha_t1_clos_odd_elem.text)
    ActionChains(driver).move_to_element(ha_t1_clos_odd_elem).perform()
    ha_t1_tooltip = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((
            By.XPATH,
            "//div[contains(@class, 'tooltip')]"
        ))
    )
    ha_open_ts = ha_t1_tooltip.find_element(
        By.XPATH, "./div/div/div[2]/div[1]").text
    ha_t1_open_odd = ha_t1_tooltip.find_element(
        By.XPATH, "./div/div/div[2]/div[2]").text

    # team 2 tooltip processing
    ha_t2_clos_odd_elem = pinnacle_elem.find_element(
        By.XPATH, "./div[3]//p[@class='height-content']")
    ActionChains(driver).move_to_element(ha_t2_clos_odd_elem).perform()
    ha_t2_tooltip = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((
            By.XPATH,
            "//div[contains(@class, 'tooltip')]"
        ))
    )
    ha_t2_open_odd = ha_t2_tooltip.find_element(
        By.XPATH, "./div/div/div[2]/div[2]").text
