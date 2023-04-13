import pandas as pd
import requests
from PyPDF2 import PdfReader
import io
import re
import numpy as np
import warnings
from datetime import datetime as dt
warnings.simplefilter(action='ignore', category=FutureWarning)


def _tottime2min(time_string):
    if time_string != '':
        time = dt.strptime(time_string, "%M:%S.%f")
        laptime_float = time.minute + time.second / 60
        return laptime_float
    else:
        return None

def _min2tottime(total_minutes):
    minutes = int(total_minutes)
    seconds = round((total_minutes - minutes) * 60, 3)
    time_str = f"{minutes:02d}:{seconds:06.3f}"
    return time_str

def _laptime2sec(time_string):
    if time_string != '':
        time = dt.strptime(time_string, "%M'%S.%f")
        laptime_float = time.minute * 60 + time.second + time.microsecond / 1000000
        return laptime_float
    else:
        return None


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
                self.selected_season_id = self._seasons_df.loc[self._seasons_df['year'] == season, 'id'].item()
                self.selected_season_year = season
            except:
                raise ValueError("Invalid season year") from None

        # selected season category validation
        cat_list_url = f"{self._api_base_url}/riders-api/season/{self.selected_season_year}/categories"
        cat_list = self._req.get(cat_list_url, timeout=60).json()
        cat_list_df = pd.json_normalize(cat_list)[['id', 'name']].set_index('name')
        categories = cat_list_df.index.to_list()
        av_cat_message = f"Available categories in season {self.selected_season_year}: {categories}"

        if category not in categories:
            raise ValueError(
                f"Invalid category. {av_cat_message}")
        else:
            self.selected_cat_name = category
            self.selected_cat_id = cat_list_df[cat_list_df.index == self.selected_cat_name]['id'].item()

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


class Event:
    def __init__(self, season_obj: object, short_name: str):
        self.selected_event_id = season_obj.events.loc[season_obj.events['short_name'] == short_name, 'id'].item()
        if season_obj._verbose:
            print(f"Loading event '{short_name}' ({self.selected_event_id}) ... ", end='')

        self.season_obj = season_obj
        self.name = season_obj.events.loc[season_obj.events['short_name'] == short_name, 'name'].item()
        self.short_name = short_name

        # category
        categories_list_url = f"{season_obj._base_url}/results-front/be/results-api/event/{self.selected_event_id}/categories"
        categories_list = season_obj._req.get(categories_list_url).json()
        categories_list_df = pd.json_normalize(categories_list)
        selected_cat_id = categories_list_df.loc[categories_list_df['name'] == f"{season_obj.selected_cat_name}™", 'id'].item()

        # session
        sessions_list_url = f"{season_obj._base_url}/results-front/be/results-api/event/{self.selected_event_id}/category/{selected_cat_id}/sessions"
        sessions_list = season_obj._req.get(sessions_list_url).json()
        sessions_list_df = pd.json_normalize(sessions_list)
        sessions_list_df['number'] = sessions_list_df['number'].fillna(0)
        self.sessions = sessions_list_df
        self.circuit = self.sessions['circuit'][1]

        if self.season_obj._verbose:
            print("Done.")

    def results(self,
                session: str = 'RAC',
                s_num: int = 0,
                # include_session: bool = False
                ):

        selected_session_id = self.sessions.loc[(self.sessions['type'] == session) & (self.sessions['number'] == s_num), 'id'].item()

        # classification
        classification_list_url = f"{self.season_obj._base_url}/results-front/be/results-api/session/{selected_session_id}/classifications"
        classification = self.season_obj._req.get(classification_list_url).json()
        classification_df = pd.json_normalize(classification['classification'])
        classification_df['event_id'] = self.selected_event_id
        classification_df['event_name'] = self.short_name

        return classification_df
    
    def race_analysis(self, save_pdf: bool = False, performance: bool = False):
        url = f'https://resources.motogp.com/files/results/2022/{self.short_name}/MotoGP/RAC/Analysis.pdf'
        response = requests.get(url)
        pdf_data = response.content
        if save_pdf:
            with open(f"{self.short_name}.pdf", "wb") as file:
                file.write(pdf_data)
        pdf_reader = PdfReader(io.BytesIO(pdf_data))
        
        names = self.season_obj.riders['name'].to_list()
        surnames = self.season_obj.riders['surname'].str.upper().to_list()

        text = ''
        for page in pdf_reader.pages:
            text += page.extract_text()
            
        def perc_word(word, perc):
            len_word = len(word)
            new_len = round(len_word * perc)
            return word[:new_len]
        
        pattern = r"\d+\.\d+"
        riders = []
        laptime_rows = []
        for line in text.splitlines():
            for name, surname in zip(names, surnames):
                if perc_word(name, 0.65) in line and perc_word(surname, 0.75) in line:
                    rider = name + ' ' + surname
                    if rider not in riders:
                        riders.append(rider)
                        # print(rider)
            if "'" in line and 'Page' not in line and re.search(pattern, line):
                line = line.strip(' * *')
                line = re.sub("[a-zA-Z]", "", line)
                # print(line)
                quotes = [match.start() for match in re.finditer("'", line)]
                if len(quotes) == 2:
                    split_pos = quotes[1]-1
                    # print(line[:split_pos])
                    # print(line[split_pos:])
                    laptime_rows.append(line[:split_pos])
                    laptime_rows.append(line[split_pos:])
                else:
                    laptime_rows.append(line)
                    # print(line)
                    
        data_rows = []
        for _, col in self.results().iterrows():
            for n, row in enumerate(laptime_rows, start=1):
                row = row.split(' ')
                # timesheet = timesheet.append(
                #     {'rider':col['rider.full_name'],
                #     'lap': row[1],
                #     'laptime_str': row[0],
                #     't1': row[2], 
                #     't2': row[3], 
                #     't3': row[4],
                #     't4': row[6],
                #     'speed': row[5]}, ignore_index=True)
                data_rows.append({'rider':col['rider.full_name'],
                     'lap': row[1],
                     'laptime_str': row[0],
                     't1': row[2],
                     't2': row[3],
                     't3': row[4],
                     't4': row[6],
                     'speed': row[5]})
                if n == col['total_laps']:
                    laptime_rows = laptime_rows[n:]
                    break
                
        timesheet = pd.DataFrame(data_rows, columns=['rider', 'lap', 'laptime_str', 't1', 't2', 't3', 't4', 'speed'])
        
        timesheet['laptime_sec'] = timesheet['laptime_str'].apply(_laptime2sec)
        timesheet['lap'] = timesheet['lap'].astype(int)
        timesheet[['t1', 't2', 't3', 't4', 'speed']] = timesheet[['t1', 't2', 't3', 't4', 'speed']].astype(float)
        self.season_obj.riders['rider'] = self.season_obj.riders['name'] + ' ' + self.season_obj.riders['surname']
        timesheet = timesheet.merge(
            self.season_obj.riders[['rider', 'current_career_step.team.constructor.name', 'current_career_step.team.name']], how='left',
            on='rider')
        timesheet = timesheet.rename(columns={'current_career_step.team.constructor.name': 'constructor',
                                            'current_career_step.team.name': 'team'})

        laptimes_riders = pd.pivot_table(timesheet, values='laptime_sec', index='lap', columns='rider').sort_index()
        laptimes_riders['avg_laptime'] = laptimes_riders.mean(axis=1)
        laptimes_riders['lap'] = laptimes_riders.index
        
        laptimes_teams = pd.pivot_table(timesheet, values='laptime_sec', index='lap', columns='team').sort_index()
        laptimes_teams['avg_laptime'] = laptimes_teams.mean(axis=1)
        laptimes_teams['lap'] = laptimes_teams.index
        
        laptimes_constructors = pd.pivot_table(timesheet, values='laptime_sec', index='lap', columns='constructor').sort_index()
        laptimes_constructors['avg_laptime'] = laptimes_constructors.mean(axis=1)
        laptimes_constructors['lap'] = laptimes_constructors.index
        
        # performance model
        if performance:
            race_performance = timesheet.groupby('rider').agg(
                team=('team', pd.Series.mode),
                constructor=('constructor', pd.Series.mode),
                min_laptime=('laptime_sec', 'min'),
                avg_laptime=('laptime_sec', 'mean'),
                std_laptime=('laptime_sec', 'std'),
                max_speed=('speed', 'max'),
                avg_speed=('speed', 'mean'),
                std_speed=('speed', 'std'))
            race_performance = race_performance.merge(self.results()[[
                'rider.full_name', 'position', 'points', 'total_laps', 'gap.first'
                ]], how='left', left_on='rider', right_on='rider.full_name')
            race_performance = race_performance.rename(columns={'rider.full_name': 'rider', 'total_laps':'laps', 'gap.first':'gap_first'})
            race_performance = race_performance.sort_values('position')
            race_performance['gap_first'] = race_performance['gap_first'].astype(float)
            race_performance['gap_prev'] = race_performance['gap_first'].diff().apply(lambda x: 0 if x < 0 else x)
            race_performance['race_completion'] = (race_performance['laps'] / race_performance['laps'].max()).round(2)
            
            race_performance['delta_avg_laptime'] = (race_performance['avg_laptime'].mean() - race_performance['avg_laptime'])
            race_performance['delta_std_laptime'] = (race_performance['std_laptime'].mean() - race_performance['std_laptime'])
            
            race_performance['rel_delta_avg_laptime'] = (race_performance['delta_avg_laptime'] / race_performance['avg_laptime'].mean()) * 100
            race_performance['rel_delta_std_laptime'] = (race_performance['delta_std_laptime'] / race_performance['std_laptime'].mean()) * 100
            
            race_performance['pace_speed_index'] = (race_performance['delta_avg_laptime'] * race_performance['race_completion'])
            race_performance['pace_consistency_index'] = (race_performance['delta_std_laptime'] * race_performance['race_completion'])
            

            q_grid = pd.concat([self.results('Q', 2), self.results('Q', 1)]).drop_duplicates(subset=['rider.full_name'])
            q_grid['grid'] = pd.Series(np.arange(1, q_grid.shape[0]+1))
            race_performance = race_performance.merge(q_grid[['rider.full_name', 'grid']], how='left', left_on='rider', right_on='rider.full_name')
            race_performance['pos_delta'] = race_performance['grid'] - race_performance['position']
            race_performance['pos_delta'] = race_performance.apply(
                lambda row: row['grid'] - race_performance['position'].notna().sum() if np.isnan(row['pos_delta']) else row['pos_delta'], 
                axis=1)
            
            race_performance['performance_index'] =  race_performance[['pace_consistency_index', 'pace_speed_index']].mean(axis=1)
            # from sklearn.preprocessing import StandardScaler
            # ss = StandardScaler()
            # race_performance['performance_index'] = ss.fit_transform(race_performance['performance_index'].values.reshape(-1, 1)).round(2)

            
            race_performance = race_performance[
                ['constructor', 'team', 'rider', 'grid', 'pos_delta', 'position', 'points', 
                 'laps', 'race_completion', 'gap_first', 'gap_prev', 
                 'min_laptime', 
                 'avg_laptime', 'delta_avg_laptime', 'rel_delta_avg_laptime', 
                 'std_laptime', 'delta_std_laptime', 'rel_delta_std_laptime',
                 'max_speed', 'avg_speed', 'std_speed', 
                 'pace_speed_index', 'pace_consistency_index', 'performance_index']]
            # race_performance = race_performance.sort_values('performance_index', ascending=False)
            
            return timesheet, laptimes_riders, laptimes_teams, laptimes_constructors, race_performance
        else:
            return timesheet, laptimes_riders, laptimes_teams, laptimes_constructors