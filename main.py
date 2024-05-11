from crawler import aprove_cookie, driver
from crawler import scraping_event_data, scraping_eventrow
from db import Model, engine


def refresh_db():
    Model.metadata.drop_all(engine)
    Model.metadata.create_all(engine)


def run_crawler():
    aprove_cookie()
    scraping_eventrow()
    driver.quit()


if __name__ == '__main__':
    run_crawler()
