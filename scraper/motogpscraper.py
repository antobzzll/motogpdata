from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import re
import time
import pandas as pd
import tydier as ty
from datetime import datetime as dt

options = Options()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')

# settings for data storage
CSV_PATH = "../data/csv/"
YEAR = dt.today().year
save_as_arg_erro = "Unvalid `save_as` argument. Options are:" \
    "`csv`"


# class _SeleniumWebDriver:
#     def __init__(self):
        # self.driver = webdriver.Chrome(
        #     service=Service(ChromeDriverManager().install()),
        #     options=options)
        # self.driver = webdriver.Chrome(/usr/bin/chromedriver)


class CurrentRiders():
    def __init__(self, save_as: str = 'csv',
                 verbose: bool = True):
        self.verbose = verbose
        self.driver = webdriver.Chrome("/usr/bin/chromedriver")
        
        if self.verbose:
            print(
                f"[motogpscraper] Retrieving riders and teams for current season: ", end='')

        url = "https://www.motogp.com/en/teams/MotoGP"
        self.url = url
        if self.verbose:
            print(f"Connecting to: {url}", end='')
        self.driver.get(self.url)
        if self.verbose:
            print(" OK")
            print(f"[motogpscraper] {self.driver.title}")

        team_boxes = self.driver.find_elements(By.CLASS_NAME, "card-body")

        riders_team_ls = []
        names = []
        surnames = []
        riders_n_s = []
        countries = []
        for team_box in team_boxes[2:]:
            # print(team_box.get_attribute('innerHTML'))
            # print()
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
            
        self.driver.close()
        
        # retrieve rider country
        if verbose:
            print("[motogpscraper] Retrieving countries")
        for name, surname in zip(names, surnames):
            self.driver = webdriver.Chrome("/usr/bin/chromedriver")
            url = f"https://www.motogp.com/en/riders/profile/{name}+{surname}"
            self.driver.get(url)
            page_content = self.driver.page_source
            time.sleep(5)
            soup = BeautifulSoup(page_content)
            country = soup.find("p", "card-text c-rider-country").get_text()
            # country = self.driver.find_element(By.CLASS_NAME, "card-text c-rider-country")
            # country = country.get_attribute('innerHTML')
            self.driver.close()
            countries.append(country)
            print(country)
            time.sleep(30)
        
        df = pd.DataFrame({'rider_name': riders_n_s, 
                           'team': riders_team_ls,
                           'country': countries})
        df['team'] = df['team'].astype(str).str.replace("™", "")

        
        
        if len(df.index) == 0:
            print("[!][motogpscraper] Unable to download data. Please retry.")
            self._closeconn()
        else:
            # saving
            if save_as == 'csv':
                path_file = f"{CSV_PATH}motogp_{YEAR}_Riders.csv"
                df.to_csv(path_file)
                if self.verbose:
                    print(
                        f"[motogpscraper] Riders data for season {YEAR} saved to: {path_file}")
                self._closeconn()
            else:
                self._closeconn()
                raise ValueError(save_as_arg_erro)

    def _closeconn(self):
        if self.verbose:
            print("[motogpscraper] Closing connection")
        self.driver.close()


class RaceData():
    def __init__(self, GP: str, YEAR: str | int, verbose: bool = True):
        self.driver = webdriver.Chrome("/usr/bin/chromedriver")
        self.GP = str(GP).upper()
        self.YEAR = str(YEAR)
        self.verbose = verbose

        if self.verbose:
            print(f"[motogpscraper] Scraping {self.GP} {self.YEAR}: ", end='')

        url = f"https://www.motogp.com/en/gp-results/{self.YEAR}/{self.GP}/MotoGP/RAC/Classification"
        self.url = url
        if self.verbose:
            print(f"Connecting to: {url}", end='')
        self.driver.get(self.url)
        if self.verbose:
            print(" OK")
            print(f"[motogpscraper] {self.driver.title}")

    @staticmethod
    def _clean_class_table(df: pd.DataFrame):
        # cleaning columns
        df.columns = ty.clean_col_names(df.columns)

        df['rider_number'] = df['rider'].str.slice(0, 2)
        df['rider_number'] = df['rider_number'].str.replace(" ", "")
        df['rider_number'].loc[df['rider_number'] == 'No'] = 0
        df['rider_number'] = df['rider_number'].astype(int)

        df['rider_name'] = df['rider'].str.split(" ", expand=True)[1]

        def _split_upper(x):
            return ' '.join(re.findall('[a-zA-Z][^A-Z]*', x))
        df['rider_name'] = df['rider_name'].apply(_split_upper)

        def _team(x):
            return ' '.join(x.split(" ")[2:])
        df['team'] = df['rider'].apply(_team)

        df = df.drop(columns=['unnamed_10',
                              'unnamed_11',
                              'rider'])

        # separating Non-classified riders
        nc_index = int(
            df.loc[df['pos'] == 'Non-classified riders'].iloc[0].name)
        # retrievies the index of the first 'Non-classified riders' encounter
        nc_df = df.iloc[nc_index+1:]
        nc_df['pos'] = 0
        nc_df['points'] = 0
        # print(df)

        # return df[['pos', 'points', 'rider_number', 'rider_name', 'team']]
        return df

    def class_table(self, save_as: str = 'csv'):
        # retrive GP classification table
        gp_table = self.driver.find_element(
            "xpath",
            "/html/body/div/div/div/div/main/div/div/div/div[3]/div/div[2]/div[4]/div/div/div")
        gp_table_html = gp_table.get_attribute('innerHTML')

        # to pandas.df
        df = pd.read_html(gp_table_html)

        # cleaning and validation
        df = self._clean_class_table(df[0])

        # saving
        if save_as == 'csv':
            path_file = f"{CSV_PATH}motogp_{self.YEAR}_{self.GP}.csv"
            df.to_csv(path_file)
            if self.verbose:
                print(f"[motogpscraper] Race results saved to: {path_file}")
            self._closeconn()
        else:
            self._closeconn()
            raise ValueError(save_as_arg_erro)

    def _closeconn(self):
        if self.verbose:
            print("[motogpscraper] Closing connection")
        self.driver.close()
