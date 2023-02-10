import pandas as pd
import numpy as np
from tqdm import tqdm

from .handler import Season, Event


def event_track_info():
    track_temp_list = []
    seasons_list = []
    events_list = []
    circuit_list = []
    avg_speed_list = []
    track_cond_list = []

    for s in tqdm(range(2005, 2023)):
        season = Season(s, 'MotoGP')
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
