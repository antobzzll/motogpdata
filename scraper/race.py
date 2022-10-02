from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from tqdm import tqdm
import pandas as pd
from datetime import datetime as dt

CSV_PATH = "data/csv/"
YEAR = dt.today().year

options = Options()
# options.add_argument("start-maximized")
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')

webdriver_service = Service("/usr/bin/chromedriver")
driver = webdriver.Chrome(service=webdriver_service, options=options)
wait = WebDriverWait(driver, 60)


def race_info():
    pass


def race_results():
    pass


if __name__ == "__main__":
    print(race_info())
    print(race_results())