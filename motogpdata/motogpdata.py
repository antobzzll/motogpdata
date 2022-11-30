import pandas as pd
import requests


class MotoGPData:
    def __init__(self, season: int = 0, category: str = "MotoGP",
                 verbose: bool = False):
        self.verbose = verbose
        self.req = requests.Session()

        # season
        seasons_list_url = "https://www.motogp.com/api/results-front/be/results-api/seasons?test=0"
        seasons_list = self.req.get(seasons_list_url, timeout=60).json()

        if not season:
            selected_season = seasons_list[0]
            self.selected_season_id = selected_season['id']
            self.selected_season_year = selected_season['year']
        else:
            seasons_list_df = pd.json_normalize(seasons_list)
            try:
                self.selected_season_id = seasons_list_df.loc[
                    seasons_list_df['year'] == season, 'id'].item()
                self.selected_season_year = season
            except:
                raise ValueError("Invalid season year") from None

        # selected season categories ids
        cat_list_url = f"https://api.motogp.com/riders-api/season/{self.selected_season_year}/categories"
        cat_list = self.req.get(cat_list_url, timeout=60).json()
        cat_list_df = pd.json_normalize(
            cat_list)[['id', 'name']].set_index('name')
        categories = cat_list_df.index.to_list()
        if self.verbose:
            print(f"Available categories: {categories}")

        if category not in categories:
            raise ValueError(
                f"Invalid category. Available categories: {categories}")
        else:
            self.selected_cat_name = category
            self.selected_cat_id = cat_list_df[
                cat_list_df.index == self.selected_cat_name]['id'].item()

        # list of events
        self.fevents_list_url = f"https://www.motogp.com/api/results-front/be/results-api/season/{self.selected_season_id}/events?finished=1"
        self.fevents_list = self.req.get(self.fevents_list_url).json()
        self.fevents_list_df = pd.json_normalize(self.fevents_list)
        self.finished_events_list = self.fevents_list_df['short_name'].to_list(
        )

        if self.verbose:
            print(
                f"Loaded {self.selected_cat_name} season {self.selected_season_year} ({self.selected_season_id})")
            print(f"Available events: ", self.finished_events_list)

    def riders(self):
        if self.verbose:
            print("Riders:")
        riders_url = f"https://api.motogp.com/riders-api/season/{self.selected_season_year}/riders?category={self.selected_cat_id}"
        riders = self.req.get(riders_url)
        riders_df = pd.json_normalize(riders.json())
        self.riders_df = riders_df
        return self.riders_df

    def _get_results(self, _event):
        selected_event_id = self.fevents_list_df.loc[
            self.fevents_list_df['short_name'] == _event, 'id'].item()
        if self.verbose:
            print(f"Getting {_event} ({selected_event_id})...")

        # # category
        categories_list_url = f"https://www.motogp.com/api/results-front/be/results-api/event/{selected_event_id}/categories"
        categories_list = self.req.get(categories_list_url).json()
        categories_list_df = pd.json_normalize(categories_list)
        selected_cat_id = categories_list_df.loc[categories_list_df['name']
                                                 == f"{self.selected_cat_name}™", 'id'].item()

        # session
        sessions_list_url = f"https://www.motogp.com/api/results-front/be/results-api/event/{selected_event_id}/category/{selected_cat_id}/sessions"
        sessions_list = self.req.get(sessions_list_url).json()
        sessions_list_df = pd.json_normalize(sessions_list)
        selected_session_id = sessions_list_df.loc[sessions_list_df['type'] == 'RAC', 'id'].item(
        )

        # classification
        classification_list_url = f"https://www.motogp.com/api/results-front/be/results-api/session/{selected_session_id}/classifications"
        classification = self.req.get(classification_list_url).json()
        classification_df = pd.json_normalize(
            classification['classification'])

        classification_df['event_id'] = selected_event_id
        classification_df['event_name'] = _event
        return classification_df

    def results(self, event: str):
        event = event.upper()

        if event not in self.finished_events_list and event != 'ALL':
            raise ValueError(
                f"Invalid event name. Available events for season "
                f"{self.selected_season_year}: {self.finished_events_list}"
            )

        if event == 'ALL':
            if self.verbose:
                print(
                    f"Getting results for all events in season {self.selected_season_year} ...")
            all_dfs = []
            for ev in self.finished_events_list:
                all_dfs.append(self._get_results(ev))
            return pd.concat(all_dfs)
        else:
            return self._get_results(event)
