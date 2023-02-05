import pandas as pd
import requests


class MotoGPData:
    """Class to retrieve data from motogp.com API
    """

    def __init__(self, verbose: bool = False):
        """
        The method creates a requests session, sets the base URL for the API, 
        and then uses the requests session to get a list of seasons from the 
        API and stores it in self._seasons_list. It then normalizes this list 
        into a pandas dataframe and stores it in self.seasons as a list of years.

        Args:
            verbose (bool, optional): verbose level. Defaults to False.
        """
        self._verbose = verbose
        self._req = requests.Session()
        self._base_url = 'https://www.motogp.com/api'
        self._api_base_url = 'https://api.motogp.com'
        
        # seasons list
        seasons_list_url = f"{self._base_url}/results-front/be/results-api/seasons?test=0"
        self._seasons_list = self._req.get(seasons_list_url, timeout=60).json()
        seasons_list_df = pd.json_normalize(self._seasons_list)
        self.seasons = seasons_list_df['year'].to_list()

    def load_season(self, season: int = 0, category: str = "MotoGP"):
        # season validation
        if not season:  # chose the last season if variable is empty
            selected_season = self._seasons_list[0]
            self.selected_season_id = selected_season['id']
            self.selected_season_year = selected_season['year']
        else:
            seasons_list_df = pd.json_normalize(self._seasons_list)
            self.seasons = seasons_list_df['year'].to_list()
            try:
                self.selected_season_id = seasons_list_df.loc[
                    seasons_list_df['year'] == season, 'id'].item()
                self.selected_season_year = season
            except:
                raise ValueError("Invalid season year") from None

        # selected season categories ids
        cat_list_url = f"{self._api_base_url}/riders-api/season/{self.selected_season_year}/categories"
        cat_list = self._req.get(cat_list_url, timeout=60).json()
        cat_list_df = pd.json_normalize(
            cat_list)[['id', 'name']].set_index('name')
        categories = cat_list_df.index.to_list()
        av_cat_message = f"Available categories: {categories}"
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
        self._fevents_list_url = f"{self._base_url}/results-front/be/results-api/season/{self.selected_season_id}/events?finished=1"
        self._fevents_list = self._req.get(self._fevents_list_url).json()
        self._fevents_list_df = pd.json_normalize(self._fevents_list)
        self.events = self._fevents_list_df['short_name'].to_list()

        if self._verbose:
            print(
                f"Loaded {self.selected_cat_name} season {self.selected_season_year} ({self.selected_season_id})")
            print(av_cat_message)
            print(f"Available events:", self.events)

    def riders(self):
        """
        This function retrieves a list of riders from the MotoGP API for 
        the selected season year and category ID.

        Returns:
            pandas.DataFrame: dataframe with riders data
        """
        if self._verbose:
            print("Riders:")
        riders_url = f"{self._api_base_url}/riders-api/season/{self.selected_season_year}/riders?category={self.selected_cat_id}"
        riders = self._req.get(riders_url)
        riders_df = pd.json_normalize(riders.json())
        
        return riders_df

    def _get_results(self, event: str, session: str = 'RAC', s_num: int = 0):
        """
        Function that gets the results of a MotoGP event.
        It takes in an event name as an argument and uses it to get 
        the event ID from the fevents_list_df dataframe. It then uses the
        event ID to get the category ID from the categories_list dataframe 
        and uses that to get the session ID from the sessions_list dataframe.
        Finally, it uses the session ID to get a classification from the 
        classification_list and returns a classification dataframe with 
        additional columns for event ID and event name.

        Args:
            _event ([type]): [description]

        Returns:
            [type]: [description]
        """
        selected_event_id = self._fevents_list_df.loc[
            self._fevents_list_df['short_name'] == event, 'id'].item()
        if self._verbose:
            print(f"\t* {event} ({selected_event_id}) ... ", end='')

        # category
        categories_list_url = f"{self._base_url}/results-front/be/results-api/event/{selected_event_id}/categories"
        categories_list = self._req.get(categories_list_url).json()
        categories_list_df = pd.json_normalize(categories_list)
        selected_cat_id = categories_list_df.loc[categories_list_df['name']
                                                 == f"{self.selected_cat_name}™", 'id'].item()

        # session
        sessions_list_url = f"{self._base_url}/results-front/be/results-api/event/{selected_event_id}/category/{selected_cat_id}/sessions"
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
        classification_df['event_id'] = selected_event_id
        classification_df['event_name'] = event

        if self._verbose:
            print("Ok.")
        return classification_df

    def results(self, event: str = 'all', session: str = 'RAC', s_num: int = 0):
        """Retrieves a classification dataframe for a given event.

        Args:
            event (str): event code in the form of QAT, AUS, etc. Defaults to 'all'.

        Raises:
            ValueError: if event code is wrong.

        Returns:
            pandas.DataFrame: dataframe with classification results
        """
        event = event.upper()

        if event not in self.events and event != 'ALL':
            raise ValueError(
                f"Invalid event name. Available events for season "
                f"{self.selected_season_year}: {self.events}"
            )

        if event == 'ALL':
            if self._verbose:
                print(
                    f"Retrieving results for all events in season {self.selected_season_year}:")
            all_dfs = []
            for ev in self.events:
                all_dfs.append(self._get_results(ev, session=session, s_num=s_num))
            if self._verbose:
                print("Dataframe concatenated.")
            return pd.concat(all_dfs)
        else:
            if self._verbose:
                print(
                    f"Retrieving results for event {event} in season {self.selected_season_year}:")
            return self._get_results(event, session=session, s_num=s_num)
