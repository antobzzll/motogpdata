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


def riders_list():
    # riders list
    print("\nRetrieving riders names list... ")
    driver.get("https://www.motogp.com/en/teams/MotoGP")
    team_boxes = driver.find_elements(By.CLASS_NAME, "card-body")

    riders_team_ls = []
    names = []
    surnames = []
    riders_n_s = []
    for team_box in tqdm(team_boxes[2:]):
        rider_names = team_box.find_elements(
            By.CLASS_NAME, 'c-teams-rider-name')
        names_list = [name.get_attribute('innerHTML')
                      for name in rider_names]

        rider_surnames = team_box.find_elements(
            By.CLASS_NAME, 'c-teams-rider-surname')
        surnames_list = [surname.get_attribute(
            'innerHTML') for surname in rider_surnames]

        for name, surname in zip(names_list, surnames_list):
            names.append(name)
            surnames.append(surname)
            riders_n_s.append(f"{name} {surname}")

        nrows = len(names_list)
        riders_team = team_box.find_element(
            By.TAG_NAME, 'h5').get_attribute('innerHTML')

        repeated_team = [team for team in [riders_team]
                         for i in range(nrows)]
        riders_team_ls += repeated_team

    if names and surnames:
        print("Done.")

    # info extraction
    print("\nRetrieving riders information...")
    countries = []
    dobs = []
    attributes = []
    nicknames = []
    bikes = []
    for name, surname in tqdm(zip(names, surnames), total=len(names)):
        driver.get(
            f"https://www.motogp.com/en/riders/profile/{name}+{surname}")

        country = wait.until(EC.visibility_of_element_located(
            (By.CSS_SELECTOR, "p.card-text.c-rider-country"))).text
        countries.append(country.title())

        nickname = wait.until(EC.visibility_of_element_located(
            (By.CSS_SELECTOR, "h5.c-rider-nickname-text"))).text
        nicknames.append(nickname)

        bike = wait.until(EC.visibility_of_element_located(
            (By.CSS_SELECTOR, "p.card-text.c-rider-bike"))).text
        bikes.append(bike)

        dob = wait.until(EC.visibility_of_element_located(
            (By.CSS_SELECTOR, "p.card-text.c-rider-birth_date"))).text
        dobs.append(dob)

        # hw = wait.until(EC.visibility_of_element_located(
        #     (By.CSS_SELECTOR, "p.card-text.c-rider-attributes"))).text
        try:
            hw = driver.find_element(
                By.CSS_SELECTOR, "p.card-text.c-rider-attributes").text
            attributes.append(hw)
        except NoSuchElementException:
            attributes.append('')
    if countries and dobs and attributes and nicknames and bikes:
        print("Done.")

    # data collection in dataframe
    df = pd.DataFrame({
        'name': riders_n_s,
        'nickname': nicknames,
        'dob': dobs,
        'country': countries,
        'attributes': attributes,
        'team': riders_team_ls,
        'bike': bikes
    })

    df['team'] = df['team'].astype(str).str.replace('™', '')
    
    df['number'] = df['nickname'].astype(str).str.extract(r'(\d+)')
    
    df['dob'] = df['dob'].astype(str).str[-10:]
    df['dob'] = pd.to_datetime(df['dob'])
    
    hw = df['attributes'].astype(str).str.split("|", expand=True)
    df['height_cm'] = hw[0].str.extract(r'(\d+)')
    df['height_cm'] = df['height_cm'].astype('float64')
    df['weight_kg'] = hw[1].str.extract(r'(\d+)')
    df['weight_kg'] = df['weight_kg'].astype('float64')
    
    df['bike'] = df['bike'].astype(str).str.split(' : ', expand=True)[1]
    
    df.drop(columns=['attributes'])
    df = df[['name', 'nickname', 'number', 'dob', 'country', 'height_cm',
            'weight_kg', 'team', 'bike']]

    path_file = f"{CSV_PATH}motogp_{YEAR}_Riders.csv"
    df.to_csv(path_file)

    return df


if __name__ == "__main__":
    print(riders_list())
