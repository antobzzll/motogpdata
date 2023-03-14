import pandas as pd
import numpy as np
from tqdm import tqdm
from datetime import datetime as dt
from .handler import _Handler, Season, Event, _tottime2min

this_year = int(dt.today().year)


def seasons_list():
    handler = _Handler()
    return handler._seasons


def event_track_info(category: str = 'MotoGP', start: int = 2005, end: int = this_year):
    track_temp_list = []
    seasons_list = []
    events_list = []
    circuit_list = []
    avg_speed_list = []
    track_cond_list = []

    for s in tqdm(range(start, end)):
        season = Season(s, category)
        # print(s)
        for e in season.events_list:
            try:
                event = Event(season, e)
                # print(e)
            except ValueError:
                pass
            else:
                avg_track_temp = pd.to_numeric(
                    event.sessions['condition.ground'].str.replace('º', '')).mean()
                track_temp_list.append(avg_track_temp)
                seasons_list.append(s)
                events_list.append(event.short_name)
                circuit_list.append(event.circuit)
                try:
                    condition = event.sessions.loc[(event.sessions['type'] == 'RAC') & (
                        event.sessions['status'] == 'Official'), 'condition.track'].item()
                    track_cond_list.append(condition)
                except ValueError:
                    track_cond_list.append(condition)
                # print(f"{event.short_name}: {condition}")

                try:
                    rac_res = event.results(session='RAC')
                    avg_speed = rac_res['average_speed'].mean()
                    avg_speed_list.append(avg_speed)
                except KeyError:
                    avg_speed_list.append(np.nan)
        # print('- OK')

    track_temp = pd.DataFrame({
        'season_year': seasons_list,
        'event': events_list,
        'circuit': circuit_list,
        'avg_track_temp': track_temp_list,
        'avg_speed': avg_speed_list,
        'track_condition': track_cond_list
    })
    track_temp['season_year'] = pd.to_datetime(
        track_temp['season_year'], format="%Y")
    track_temp = track_temp.set_index('season_year')
    print("Done.")
    return track_temp


def rider_summary(rider_name: str, category: str, seasons_list: list = seasons_list()):
    date = []
    event_shortname_ls = []
    circuit_ls = []
    time_ls = []
    avg_speed_ls = []
    position_ls = []
    gap_first_ls = []
    gap_lap_ls = []
    condition_ls = []
    total_laps_ls = []
    rider_name_ls = []
    points_ls = []
    
    for s in tqdm(seasons_list):
        try:
            season = Season(s, 'MotoGP')
        except ValueError:
            pass
        else:
            for e in season.events_list:
                try:
                    event = Event(season, e)
                except ValueError:
                    pass
                else:
                    try:
                        if event.results()['rider.full_name'].str.contains(rider_name).any():
                            res = event.results()
                            date.append(event.sessions.loc[(event.sessions['type'] == 'RAC') & (event.sessions['status'] == 'Official'), 'date'].item())
                            event_shortname_ls.append(event.short_name)
                            circuit_ls.append(event.circuit)
                            time_ls.append(res.loc[res['rider.full_name'] == rider_name, 'time'].item())
                            avg_speed_ls.append(res.loc[res['rider.full_name'] == rider_name, 'average_speed'].item())
                            position_ls.append(res.loc[res['rider.full_name'] == rider_name, 'position'].item())
                            gap_first_ls.append(res.loc[res['rider.full_name'] == rider_name, 'gap.first'].item())
                            gap_lap_ls.append(res.loc[res['rider.full_name'] == rider_name, 'gap.lap'].item())
                            
                            condition = event.sessions.loc[(event.sessions['type'] == 'RAC') & (event.sessions['status'] == 'Official'), 'condition.track'].item()
                            condition_ls.append(condition)
                            
                            total_laps_ls.append(res.loc[res['rider.full_name'] == rider_name, 'total_laps'].item())
                            points_ls.append(res.loc[res['rider.full_name'] == rider_name, 'points'].item())
                            rider_name_ls.append(rider_name)
                    except KeyError:
                        pass
            # print(s)

    # dataframe creation
    df = pd.DataFrame({
        'rider_name': rider_name_ls,
        'date': date,
        'event_short_name': event_shortname_ls,
        'circuit': circuit_ls,
        'track_cond': condition_ls,
        'tot_time': time_ls,
        'avg_speed': avg_speed_ls,
        'position': position_ls,
        'points': points_ls,
        'gap_first': gap_first_ls,
        'gap_lap': gap_lap_ls,
        'tot_laps': total_laps_ls
    })
    
    
    df['tot_time_m'] = df['tot_time'].apply(_tottime2min)
    df['avg_lap_time_m'] = df['tot_time_m'] / df['tot_laps']
    df = df.drop(columns=['tot_time'])
    
    categories = df['position'].sort_values(ascending=False).to_list()
    categories = list(set((int(i) for i in categories if not np.isnan(i))))
    categories = [str(i) for i in categories]
    categories.append('NC')
    categories = list(reversed(categories))
    df['position'] = pd.Categorical(
        df['position'].astype(str).str.split('.', expand=True)[0],
        categories=categories, 
        ordered=True)
    df['position'] = df['position'].fillna('NC')
    df['date'] = pd.to_datetime(df['date'])
    df['year'] = df['date'].dt.year

    return df