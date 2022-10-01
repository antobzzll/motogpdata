from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
 
options = Options()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')

# settings for data storage
path = "../data/"


class MotoGPRaceData:
    def __init__(self, GP: str, YEAR: str | int, verbose: bool = True):
        self.GP = str(GP).upper()
        self.YEAR = str(YEAR)
        self.verbose = verbose
        
        if self.verbose:
            print("[motogpscraper] Initializing selenium webdriver")
            
        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), 
            options=options)
        
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
    
    
    def _info(self):
        pass
    
    
    def class_table(self, save: bool = True):
        # retrive GP classification table
        gp_table = self.driver.find_element(
            "xpath", 
            "/html/body/div/div/div/div/main/div/div/div/div[3]/div/div[2]/div[4]/div/div/div")
        gp_table_html = gp_table.get_attribute('innerHTML')

        # to pandas.DataFrame
        df = pd.read_html(gp_table_html)
        
        # cleaning and validation
        
        
        # saving
        if save:
            df[0].to_csv(f"{path}motogp_{self.YEAR}_{self.GP}.csv")
    
    def __del__(self):
        self.driver.close()