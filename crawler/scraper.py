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


def scraping_event_data(event_url):
    driver.get(MAIN_URL+event_url[1:])
    driver.implicitly_wait(10)
    data_frame = elem_weiter("//main/div[3]/div[2]/div[1]/div[2]")
    date = data_frame.find_element(By.XPATH, "./div[1]/p[2]").text
    # catching exception if event was canceled
    try:
        res = data_frame.find_element(By.XPATH,
                                      "./div[3]/div[2]/strong").text
    except NoSuchElementException:
        res = 'canceled!'
    finally:
        fin_res = res

    teams = driver.find_elements(By.XPATH,
                                 "//span[contains(@class, 'truncate')]")
    team_1 = teams[0].text
    team_2 = teams[1].text
    logging.info(f"crawling {date} {team_1} - {team_2}")
    # scraping home/away partition
    # find particular bookbaker
    while True:
        bookmakers = driver.find_elements(
            By.XPATH,
            "//div[contains(@class, 'border-black-borders flex h-9 border-b')]"
            )
        pinnacle_elem = next((
            elem for elem in bookmakers if elem.find_element(
                By.XPATH,
                "./div/a[2]/p").text == 'Pinnacle'), None)
        if pinnacle_elem is not None:
            break
        else:
            logging.info("pinnacle elem not found, try again!")
            driver.refresh()
            driver.implicitly_wait(10)

    ha_t1_clos_odd_elem = pinnacle_elem.find_element(
        By.XPATH, "./div[2]//p[contains(@class, 'height-content')]")
    ActionChains(driver).move_to_element(ha_t1_clos_odd_elem).perform()
    t1_ha_clos = ha_t1_clos_odd_elem.text

    ha_t1_tooltip = elem_weiter("//div[contains(@class, 'tooltip')]")
    ha_ts = ha_t1_tooltip.find_element(
        By.XPATH, "./div/div/div[2]/div[1]").text
    t1_ha_open = ha_t1_tooltip.find_element(
        By.XPATH, "./div/div/div[2]/div[2]").text
    # team 2 tooltip processing
    t2_ha_clos_elem = pinnacle_elem.find_element(
        By.XPATH, "./div[3]//p[contains(@class, 'height-content')]")
    t2_ha_clos = t2_ha_clos_elem.text
    ActionChains(driver).move_to_element(t2_ha_clos_elem).perform()
    ha_t2_tooltip = elem_weiter("//div[contains(@class, 'tooltip')]")

    t2_ha_open = ha_t2_tooltip.find_element(
        By.XPATH, "./div/div/div[2]/div[2]").text

    for item in driver.find_elements(By.XPATH,
                                     "//li[contains(@class, 'odds-item')]"):
        if item.find_element(By.XPATH, "./span/div").text == "Asian Handicap":
            item.click()

    if float(t1_ha_clos) < float(t1_ha_open):
        target = "Asian Handicap +1.5"
    else:
        target = "Asian Handicap -1.5"

    logging.info(f"processing {target}")

    driver.implicitly_wait(10)
    odds_items = driver.find_elements(
        By.XPATH, "//li[contains(@class, 'odds-item')]")

    for item in odds_items:
        if item.find_element(By.XPATH, "./span/div").text == "Asian Handicap":
            item.click()
            sleep(1)

    while True:
        handicaps = driver.find_elements(
            By.XPATH,
            "//div[@class='relative flex flex-col']"
            )
        target_hc = next((elem for elem in handicaps if elem.find_element(
            By.XPATH,
            "./div/div[2]/p[1]").text == target
        ), None)
        if target_hc is not None:
            target_hc.click()
            break
        else:
            logging.info("target handicap not found, try again!")
            driver.refresh()
            driver.implicitly_wait(10)

    while True:
        bet_elements = driver.find_elements(
            By.XPATH,
            "//div[contains(@class, ' border-black-borders border-b')]"
        )
        pinnacle_elem = next((
            elem for elem in bet_elements if elem.find_element(
                By.XPATH,
                "./div[1]/a[2]/p").text == 'Pinnacle'), None)
        if pinnacle_elem is not None:
            break
        else:
            logging.info("pinnacle elem not found, try again!")
            driver.refresh()
            driver.implicitly_wait(10)

    odd_score = WebDriverWait(pinnacle_elem, timeout=20).until(
        EC.presence_of_element_located((
            By.XPATH,
            "./div[3]//p[contains(@class, 'height-content')]"
        ))
    )
    ActionChains(driver).move_to_element(odd_score).perform()
    odd_toltip = elem_weiter("//div[contains(@class, 'tooltip')]")
    handicap_ts = odd_toltip.find_element(
                By.XPATH, "./div/div/div[2]/div[1]").text
    t1_handicap_open = odd_toltip.find_element(
                By.XPATH, "./div/div/div[2]/div[2]").text
    t1_handicap_clos = odd_toltip.find_element(
                By.XPATH, "./div/div/div[1]/div[2]/div").text

    odd_score_t2 = pinnacle_elem.find_element(
                By.XPATH,
                "./div[4]//p[contains(@class, 'height-content')]"
                )
    ActionChains(driver).move_to_element(odd_score_t2).perform()
    odd_toltip_t2 = elem_weiter("//div[contains(@class, 'tooltip')]")

    t2_handicap_open = odd_toltip_t2.find_element(
                By.XPATH, "./div/div/div[2]/div[2]").text
    t2_handicap_clos = odd_toltip_t2.find_element(
                By.XPATH, "./div/div/div[1]/div[2]/div").text

    add_event_data(date=date,
                   team_1=team_1,
                   team_2=team_2,
                   fin_res=fin_res,
                   ha_ts=ha_ts,
                   t1_ha_open=t1_ha_open,
                   t2_ha_open=t2_ha_open,
                   t1_ha_clos=t1_ha_clos,
                   t2_ha_clos=t2_ha_clos,
                   handicap_ts=handicap_ts,
                   t1_handicap_open=t1_handicap_open,
                   t2_handicap_open=t2_handicap_open,
                   t1_handicap_clos=t1_handicap_clos,
                   t2_handicap_clos=t2_handicap_clos)
    logging.info((f"added event: {date}. {team_1} - {fin_res} - {team_2}\n"
                  f"-- {ha_ts}: {t1_ha_open}, {t1_ha_clos}\n"
                  f"\t\t  {t2_ha_open}, {t2_ha_clos}\n"
                  f"-- {handicap_ts}: {t1_handicap_open}, {t1_handicap_clos}\n"
                  f"\t\t  {t2_handicap_open}, {t2_handicap_clos}"))


def scraping_data(first_year: int = 2016, last_year: int = 2024):
    for year in range(first_year, last_year+1):
        logging.info(f"year {year}")
        max_pagination = get_pagination(driver, year)
        for p in range(1, int(max_pagination)+1):
            logging.info(f"-- page: {p}")
            event_urls = scraping_urls(driver, year, p)
            for url in event_urls:
                scraping_event_data(url)
