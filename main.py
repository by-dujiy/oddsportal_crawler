from crawler import aprove_cookie, scraping_eventrow, driver
from db import Model, engine


def run_crawler():
    # refresh db
    Model.metadata.drop_all(engine)
    Model.metadata.create_all(engine)

    aprove_cookie()
    scraping_eventrow()
    driver.quit()


if __name__ == '__main__':
    run_crawler()
