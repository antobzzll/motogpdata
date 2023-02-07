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


def list_seasons():
    handler = _Handler()
    return handler._seasons


class Season(_Handler):
    def __init__(self, season: int = 0, category: str = "MotoGP", verbose : bool = False):
        
        super().__init__()
        self._verbose = verbose
        
        # season validation
        if not season:  # chose the last season if variable is empty
            selected_season = self._seasons_list[0]
            self.selected_season_id = selected_season['id']
            self.selected_season_year = selected_season['year']
        else:
            # seasons_list_df = pd.json_normalize(self._seasons_list)
            # self.seasons = seasons_list_df['year'].to_list()
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
            print(f"Loaded {self.selected_cat_name} season {self.selected_season_year} ({self.selected_season_id})")
            print(av_cat_message)
            print(f"Available events:", self.events_list)
        
        # riders
        self.riders = self._riders()


    def _riders(self):
        riders_url = f"{self._api_base_url}/riders-api/season/{self.selected_season_year}/riders?category={self.selected_cat_id}"
        riders = self._req.get(riders_url)
        riders_df = pd.json_normalize(riders.json())
        
        return riders_df
    
    
    def _results(self, 
                 event: str, 
                 session: str = 'RAC', 
                 s_num: int = 0,
                 include_session : bool = False
                 ):
        
        self.selected_event_id = self.events.loc[self.events['short_name'] == event, 'id'].item()
        if self._verbose:
            print(f"\t* {event} ({self.selected_event_id}) ... ", end='')

        # category
        categories_list_url = f"{self._base_url}/results-front/be/results-api/event/{self.selected_event_id}/categories"
        categories_list = self._req.get(categories_list_url).json()
        categories_list_df = pd.json_normalize(categories_list)
        selected_cat_id = categories_list_df.loc[categories_list_df['name'] == f"{self.selected_cat_name}™", 'id'].item()

        # session
        sessions_list_url = f"{self._base_url}/results-front/be/results-api/event/{self.selected_event_id}/category/{selected_cat_id}/sessions"
        sessions_list = self._req.get(sessions_list_url).json()
        sessions_list_df = pd.json_normalize(sessions_list)
        sessions_list_df['number'] = sessions_list_df['number'].fillna(0)
        self.sessions = sessions_list_df
        selected_session_id = sessions_list_df.loc[
            (sessions_list_df['type'] == session) & (sessions_list_df['number'] == s_num), 'id'].item()

        # classification
        classification_list_url = f"{self._base_url}/results-front/be/results-api/session/{selected_session_id}/classifications"
        classification = self._req.get(classification_list_url).json()
        classification_df = pd.json_normalize(classification['classification'])
        classification_df['event_id'] = self.selected_event_id
        classification_df['event_name'] = event

        if self._verbose:
            print("Ok.")
        return classification_df


    def results(self, event: str = 'all', session: str = 'RAC', s_num: int = 0):
        event = event.upper()

        if event not in self.events_list and event != 'ALL':
            raise ValueError(
                f"Invalid event name. Available events for season "
                f"{self.selected_season_year}: {self.events_list}"
            )

        if event == 'ALL':
            if self._verbose:
                print(
                    f"Retrieving results for all events in season {self.selected_season_year}:")
            all_dfs = []
            for ev in self.events_list:
                all_dfs.append(self._results(ev, session=session, s_num=s_num))
            if self._verbose:
                print("Dataframe concatenated.")
            return pd.concat(all_dfs)
        else:
            if self._verbose:
                print(
                    f"Retrieving results for event {event} in season {self.selected_season_year}:")
            return self._results(event, session=session, s_num=s_num)


def season_range_results(
    season_start : int,
    season_end : int,
    category : str = 'MotoGP',
    session : str = 'RAC',
    s_num : int = 0,
    verbose : bool = False,
    include_session : bool = False
    ):
    
    dataframes = []
    for season in range(season_start, season_end+1):
        
        if verbose:
            print(season, end='')
            
        s = Season(season=season, category=category)
        dataframes.append(s.results(session=session, s_num=s_num))
        
        if verbose:
            print(" - OK")
            
    df = pd.concat(dataframes)
    
    return df

class Event:
    def __init__(self, season_obj : object, short_name : str):
        season_obj.selected_event_id = season_obj.events.loc[season_obj.events['short_name'] == short_name, 'id'].item()
        if season_obj._verbose:
            print(f"\t* {short_name} ({season_obj.selected_event_id}) ... ", end='')

        # category
        categories_list_url = f"{season_obj._base_url}/results-front/be/results-api/event/{season_obj.selected_event_id}/categories"
        categories_list = season_obj._req.get(categories_list_url).json()
        categories_list_df = pd.json_normalize(categories_list)
        selected_cat_id = categories_list_df.loc[categories_list_df['name'] == f"{season_obj.selected_cat_name}™", 'id'].item()

        # session
        sessions_list_url = f"{season_obj._base_url}/results-front/be/results-api/event/{season_obj.selected_event_id}/category/{selected_cat_id}/sessions"
        sessions_list = season_obj._req.get(sessions_list_url).json()
        sessions_list_df = pd.json_normalize(sessions_list)
        sessions_list_df['number'] = sessions_list_df['number'].fillna(0)
        self.sessions = sessions_list_df
        # selected_session_id = sessions_list_df.loc[
        #     (sessions_list_df['type'] == session) & (sessions_list_df['number'] == s_num), 'id'].item()