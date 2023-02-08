import pandas as pd
import requests
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)


class _Handler:
    def __init__(self):
        self._req = requests.Session()
        self._base_url = 'https://www.motogp.com/api'
        self._api_base_url = 'https://api.motogp.com'

        # seasons list
        seasons_list_url = f"{self._base_url}/results-front/be/results-api/seasons?test=0"
        self._seasons_list = self._req.get(seasons_list_url, timeout=60).json()
        self._seasons_df = pd.json_normalize(self._seasons_list)
        self._seasons = self._seasons_df['year'].to_list()


class Season(_Handler):
    def __init__(self, season: int = 0, category: str = "MotoGP", verbose: bool = False):

        super().__init__()
        self._verbose = verbose

        # season validation
        if not season:  # chose the last season if variable is empty
            selected_season = self._seasons_list[0]
            self.selected_season_id = selected_season['id']
            self.selected_season_year = selected_season['year']
        else:
            try:
                self.selected_season_id = self._seasons_df.loc[
                    self._seasons_df['year'] == season, 'id'].item()
                self.selected_season_year = season
            except:
                raise ValueError("Invalid season year") from None

        # selected season category validation
        cat_list_url = f"{self._api_base_url}/riders-api/season/{self.selected_season_year}/categories"
        cat_list = self._req.get(cat_list_url, timeout=60).json()
        cat_list_df = pd.json_normalize(
            cat_list)[['id', 'name']].set_index('name')
        categories = cat_list_df.index.to_list()
        av_cat_message = f"Available categories in season {self.selected_season_year}: {categories}"
        # if self._verbose:
        #     print(av_cat_message)

        if category not in categories:
            raise ValueError(
                f"Invalid category. {av_cat_message}")
        else:
            self.selected_cat_name = category
            self.selected_cat_id = cat_list_df[
                cat_list_df.index == self.selected_cat_name]['id'].item()

        # list of events
        fevents_list_url = f"{self._base_url}/results-front/be/results-api/season/{self.selected_season_id}/events?finished=1"
        fevents_list = self._req.get(fevents_list_url).json()
        self.events = pd.json_normalize(fevents_list)
        self.events_list = self.events['short_name'].to_list()

        if self._verbose:
            print(
                f"Loaded {self.selected_cat_name} season {self.selected_season_year} ({self.selected_season_id})")
            print(av_cat_message)
            print(f"Available events:", self.events_list)

        # riders
        self.riders = self._riders()

    def _riders(self):
        riders_url = f"{self._api_base_url}/riders-api/season/{self.selected_season_year}/riders?category={self.selected_cat_id}"
        riders = self._req.get(riders_url)
        riders_df = pd.json_normalize(riders.json())

        return riders_df


class Event:
    def __init__(self, season_obj: object, short_name: str):
        season_obj.selected_event_id = season_obj.events.loc[season_obj.events['short_name'] == short_name, 'id'].item(
        )
        if season_obj._verbose:
            print(
                f"Loading event '{short_name}' ({season_obj.selected_event_id}) ... ", end='')

        self.season_obj = season_obj
        self.short_name = short_name

        # category
        categories_list_url = f"{season_obj._base_url}/results-front/be/results-api/event/{season_obj.selected_event_id}/categories"
        categories_list = season_obj._req.get(categories_list_url).json()
        categories_list_df = pd.json_normalize(categories_list)
        selected_cat_id = categories_list_df.loc[
            categories_list_df['name'] == f"{season_obj.selected_cat_name}™", 'id'].item()

        # session
        sessions_list_url = f"{season_obj._base_url}/results-front/be/results-api/event/{season_obj.selected_event_id}/category/{selected_cat_id}/sessions"
        sessions_list = season_obj._req.get(sessions_list_url).json()
        sessions_list_df = pd.json_normalize(sessions_list)
        sessions_list_df['number'] = sessions_list_df['number'].fillna(0)
        self.sessions = sessions_list_df

        if self.season_obj._verbose:
            print("Done.")

    def results(self,
                session: str = 'RAC',
                s_num: int = 0,
                include_session: bool = False):

        selected_session_id = self.sessions.loc[(self.sessions['type'] == session) & (self.sessions['number'] == s_num), 'id'].item()

        # classification
        classification_list_url = f"{self.season_obj._base_url}/results-front/be/results-api/session/{selected_session_id}/classifications"
        classification = self.season_obj._req.get(
            classification_list_url).json()
        classification_df = pd.json_normalize(classification['classification'])
        classification_df['event_id'] = self.season_obj.selected_event_id
        classification_df['event_name'] = self.short_name

        return classification_df
