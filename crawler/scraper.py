from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver import ActionChains
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from .utility import get_from_settings
from db import add_event_data
from time import sleep
from datetime import datetime
import pathlib
import os
import random
import logging


logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
    )

MAIN_URL = "https://www.oddsportal.com/"
CURRENT_YEAR = datetime.now().year


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


def elem_weiter(xpath_selector: str):
    result = WebDriverWait(driver, timeout=20).until(
        EC.presence_of_element_located((
            By.XPATH,
            xpath_selector
        ))
    )
    if result is None:
        raise NoSuchElementException
    return result


def subelem_weiter(toltip_elem, xpath_selector):
    result = WebDriverWait(toltip_elem, timeout=20).until(
        EC.presence_of_element_located((By.XPATH, xpath_selector))
    )
    if result is None:
        raise NoSuchElementException
    return result


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
    return [event.find('a', class_='w-full').get('href') for event in events]


def scraping_eventrow(first_year: int = 2024, last_year: int = 2024):
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


def get_event_data():
    data_frame = elem_weiter("//main/div[3]/div[2]/div[1]/div[2]")
    date = subelem_weiter(data_frame, "./div[1]/p[2]").text
    # catching exception if event was canceled
    try:
        res = data_frame.find_element(By.XPATH,
                                      "./div[3]/div[2]/strong").text
    except NoSuchElementException:
        res = 'canceled!'
    finally:
        fin_res = res
    teams = driver.find_elements(
                                 By.XPATH,
                                 "//span[contains(@class, 'truncate')]")
    team_1 = teams[0].text
    team_2 = teams[1].text
    logging.info(f"scraping... {date} {team_1} {fin_res} {team_2}")
    return {'date': date,
            'fin_res': fin_res,
            'team_1': team_1,
            'team_2': team_2}


def get_home_away_data():
    driver.implicitly_wait(10)
    bookmakers = driver.find_elements(
        By.XPATH,
        "//div[contains(@class, 'border-black-borders flex h-9 border-b')]"
    )
    logging.info(f"home/away bookmakers count {len(bookmakers)}")
    pinnacle_elem = next((elem for elem in bookmakers if elem.find_element(
        By.XPATH, "./div/a[2]/p").text == 'Pinnacle'), None)
    if pinnacle_elem is None:
        raise NoSuchElementException

    ha_t1_clos_odd_elem = subelem_weiter(
        pinnacle_elem,
        "./div[2]//p[contains(@class, 'height-content')]")
    ActionChains(driver).move_to_element(ha_t1_clos_odd_elem).perform()
    t1_ha_clos = ha_t1_clos_odd_elem.text
    ha_t1_tooltip = elem_weiter("//div[contains(@class, 'tooltip')]")
    ha_ts = subelem_weiter(ha_t1_tooltip,
                           "./div/div/div[2]/div[1]").text
    t1_ha_open = subelem_weiter(ha_t1_tooltip,
                                "./div/div/div[2]/div[2]").text
    t2_ha_clos_elem = subelem_weiter(
        pinnacle_elem,
        "./div[3]//p[contains(@class, 'height-content')]")
    t2_ha_clos = t2_ha_clos_elem.text
    ActionChains(driver).move_to_element(t2_ha_clos_elem).perform()
    ha_t2_tooltip = elem_weiter("//div[contains(@class, 'tooltip')]")
    t2_ha_open = subelem_weiter(ha_t2_tooltip,
                                "./div/div/div[2]/div[2]").text

    return {'ha_ts': ha_ts,
            't1_ha_clos': float(t1_ha_clos),
            't1_ha_open': float(t1_ha_open),
            't2_ha_clos': float(t2_ha_clos),
            't2_ha_open': float(t2_ha_open)}


def get_handicap_data(target_handicap):
    handicaps = driver.find_elements(
            By.XPATH,
            "//div[@class='relative flex flex-col']"
            )
    logging.info(f"handicaps count {len(handicaps)}")
    target_hc = next((elem for elem in handicaps if elem.find_element(
        By.XPATH, "./div/div[2]/p[1]").text == target_handicap), None)
    if target_hc is not None:
        target_hc.click()
        driver.implicitly_wait(10)
    else:
        logging.info(f"{target_handicap} handicap not found!")
        raise NoSuchElementException

    bet_elements = driver.find_elements(
        By.XPATH, "//div[contains(@class, ' border-black-borders border-b')]")
    pinnacle_elem = next((elem for elem in bet_elements if elem.find_element(
        By.XPATH, "./div[1]/a[2]/p").text == 'Pinnacle'), None)
    if pinnacle_elem is None:
        logging.info("handicaps pinnacle elem not found")
        raise NoSuchElementException

    odd_score = WebDriverWait(pinnacle_elem, timeout=20).until(
        EC.presence_of_element_located((
            By.XPATH,
            "./div[3]//p[contains(@class, 'height-content')]"
        ))
    )
    ActionChains(driver).move_to_element(odd_score).perform()
    odd_toltip = elem_weiter("//div[contains(@class, 'tooltip')]")
    handicap_ts = subelem_weiter(odd_toltip,
                                 "./div/div/div[2]/div[1]").text
    t1_handicap_open = subelem_weiter(odd_toltip,
                                      "./div/div/div[2]/div[2]").text
    t1_handicap_clos = subelem_weiter(odd_toltip,
                                      "./div/div/div[1]/div[2]/div").text
    odd_score_t2 = pinnacle_elem.find_element(
                By.XPATH,
                "./div[4]//p[contains(@class, 'height-content')]"
                )
    ActionChains(driver).move_to_element(odd_score_t2).perform()
    odd_toltip_t2 = elem_weiter("//div[contains(@class, 'tooltip')]")

    t2_handicap_open = subelem_weiter(
        odd_toltip_t2,
        "./div/div/div[2]/div[2]").text
    t2_handicap_clos = subelem_weiter(
        odd_toltip_t2,
        "./div/div/div[1]/div[2]/div").text
    return {'handicap_ts': handicap_ts,
            't1_handicap_open': t1_handicap_open,
            't1_handicap_clos': t1_handicap_clos,
            't2_handicap_open': t2_handicap_open,
            't2_handicap_clos': t2_handicap_clos}


def processing_event_data(event_url):
    while True:
        try:
            driver.get(MAIN_URL+event_url[1:])
            driver.implicitly_wait(10)
            event_data = get_event_data()
            if event_data['fin_res'] == 'canceled!':
                logging.info(
                    f"{event_data['team_1']} {event_data['team_1']} - "
                    f"{event_data['fin_res']}. processing next...")
                return None
            else:
                ha_data = get_home_away_data()
                odds_items = driver.find_elements(
                    By.XPATH, "//li[contains(@class, 'odds-item')]")
                for item in odds_items:
                    item_name = item.find_element(By.XPATH, "./span/div").text
                    if item_name == "Asian Handicap":
                        item.click()
                        driver.implicitly_wait(10)

                if ha_data['t1_ha_clos'] < ha_data['t1_ha_open']:
                    target = "Asian Handicap +1.5"
                else:
                    target = "Asian Handicap -1.5"
                logging.info(f"processing {target}")
                handicap_data = get_handicap_data(target)
                return {**event_data, **ha_data, **handicap_data}
        except (NoSuchElementException,
                TimeoutException,
                StaleElementReferenceException) as e:
            logging.info(f"{e} occur... try again")
            sleep(5)
            driver.refresh()
            sleep(5)
            continue


def scraping_data(first_year: int = 2016, last_year: int = 2024):
    for year in range(first_year, last_year+1):
        pagination = get_pagination(driver, year)
        for p in range(1, int(pagination)+1):
            event_urls = scraping_urls(driver, year, p)
            for url in event_urls:
                data = processing_event_data(url)
                if data:
                    add_event_data(**data)
                    logging.info(f"added {data}")
