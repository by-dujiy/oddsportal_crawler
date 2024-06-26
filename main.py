from crawler import aprove_cookie, driver
from crawler import scraping_data
from db import Model, engine


def refresh_db():
    Model.metadata.drop_all(engine)
    Model.metadata.create_all(engine)


if __name__ == '__main__':
    refresh_db()
    aprove_cookie()
    scraping_data()
    driver.quit()
