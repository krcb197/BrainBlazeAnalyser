
from typing import Optional, Union, List
import datetime
import time
import json
import os
import re
from dateutil.parser import isoparse
import argparse

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px

from ExtendedYoutubeEasyWrapper import ExtendedYoutubeEasyWrapper

from BrainBlazeAnalyser import ISO8601_duration_to_time_delta

import tweepy

today = datetime.date.today()
midnight_monday = datetime.datetime.combine(time=datetime.time(),
                                            date=today - datetime.timedelta(days=today.weekday(), weeks=0),
                                            tzinfo=datetime.timezone.utc)
minight_last_monday = datetime.datetime.combine(time=datetime.time(),
                                                date=today - datetime.timedelta(days=today.weekday(), weeks=1),
                                                tzinfo=datetime.timezone.utc)
midight_12_week_ago_monday = datetime.datetime.combine(time=datetime.time(),
                                                date=today - datetime.timedelta(days=today.weekday(), weeks=12),
                                                tzinfo=datetime.timezone.utc)

import pandas as pd

class BrainBlazeInfoGraphic:

    # YouTube Channel ID other Simon Whistler YouTube channels, thise are used to make sure
    # Simon is not overly focusing on the "wrong" channels
    whistler_channels = ['UCYY5GWf7MHFJ6DZeHreoXgw', # BrainBlaze
                         'UClnDI2sdehVm1zm_LmUHsjQ',  # Biographics
                         'UCHKRfxkMTqiiv4pF99qGKIw',  # Geographics
                         'UCnb-VTwBHEV3gtiB9di9DZQ',  # History Highlights
                           'UC0woBco6Dgcxt0h8SwyyOmw',  # Megaprojects
                           'UC3Wn3dABlgESm8Bzn8Vamgg',  # Side Projects
                           'UCVH8lH7ZLDUe_d9mZ3dlyYQ',  # xplrd
                           'UCf-U0uPVQZtcqXUWa_Hl4Mw',  # Into the shadows
                           'UCp1tsmksyf6TgKFMdt8-05Q',  # Casual Crimalist
                           'UCQ-hpFPF4nOKoKPEAZM_THw',  # Top Tenz
                           'UC64UiPJwM_e9AqAd7RiD7JA',  # Today I found Out
                           'UCZdWrz8pF6B5Y_c6Zi6pmdQ',  # decoding the unknown
                           'UC9h8BDcXwkhZtnqoQJ7PggA']  # Warographics

    _video_cache_fn = 'BrainBlazeInfoGraphic_video_cache.json'
    _video_detail_cache_fn = 'BrainBlazeInfoGraphic_video_detail_cache.json'

    def __init__(self, api_key):

        self.easy_wrapper = ExtendedYoutubeEasyWrapper()
        self.easy_wrapper.initialize(api_key=api_key)

        # the data set is split into brain blaze videos and other simon whistler videos, this
        # allow the usage of the YouTube API to be managed, for example the analyser by default
        # retrieves data on every brain blaze video ever made but restricts other channels to the
        # last three months
        self.videos = self._channel_videos(cache_file=self._video_cache_fn,
                                           channel_id_list=self.whistler_channels,
                                           earliest_date=midight_12_week_ago_monday)
        self.videos_detail = self._video_details(cache_file=self._video_detail_cache_fn,
                                                 videos=self.videos)

    def _channel_videos(self, cache_file: str, earliest_date: datetime, channel_id_list: List[str]):
        """
        Search for Video published on a channel (or list of channels), this has two modes of
        operation, depending on whether the cache exists or not:
        - If the cache does not exist it retrieves all videos from earliest date
        - If the cache exists it looks for video after the last date in the cache

        This search returns some basic information in each video found

        :param cache_file: filename of the file to use as the cache
        :type cache_file: str
        :param earliest_date: date to start the search from
        :type earliest_date: datetime
        :param channel_id_list: list of the YouTube channel IDs to search
        :type channel_id_list: List[str]

        :return:
        """
        def get_videos(search_start_date):

            vid_list = []
            for channel_id in channel_id_list:
                vid_list += self.easy_wrapper.channel_videos(channelID=channel_id,
                                                             order='date',
                                                             publishedAfter=search_start_date)

            return vid_list

        if os.path.isfile(cache_file) is False:
            # The cache file does not exist and must be generated from scratch
            videos = get_videos(earliest_date)

            with open(cache_file, 'w') as fp:
                json.dump(videos, fp)

        else:
            # cache file exists and must be updated
            with open(cache_file) as fp:
                videos = json.load(fp)

            last_update_time = os.path.getmtime(cache_file)
            current_time = time.time()
            one_day_secs = 24 * 60 * 60
            if (current_time - one_day_secs) > last_update_time:
                # if the file was last updated more than 24 hours ago do an update

                # find the latest video publish date in the set of videos read from the cache
                video_ID = []
                last_date_of_interest = earliest_date
                for video in videos:
                    video_ID.append(video['video_id'])
                    video_pub_at = isoparse(video['publishedAt'])
                    if video_pub_at > last_date_of_interest:
                        last_date_of_interest = video_pub_at

                new_videos = get_videos(last_date_of_interest)

                # deduplicate any video found that may have been in the original list
                for video in new_videos:
                    if video['video_id'] in video_ID:
                        new_videos.remove(video)

                # if there are new videos found from the search, then write back out the cache file
                if len(new_videos) > 0:
                    videos += new_videos

                    with open(cache_file, 'w') as fp:
                        json.dump(videos, fp)
            else:
                print(f'{cache_file=} is less than 24 hours old no update performed')

        return videos

    def _get_videos_meta_data(self, video_id):

        if len(video_id) > 50:
            items = []
            for start_point in range(0, len(video_id), 50):
                end_point = start_point + 50
                if end_point > len(video_id):
                    end_point = len(video_id)

                results = self.easy_wrapper.service.videos().list(id=video_id[start_point:end_point],
                                                                  part="id, contentDetails, liveStreamingDetails").execute()
                items.extend( results.get("items", []))


        else:
            results = self.easy_wrapper.service.videos().list(id=video_id,
                                             part="id, contentDetails, liveStreamingDetails").execute()
            items = results.get("items", [])

        output = []
        for item in items:
            output_record = dict.fromkeys(
                ['video_id', 'duration',
                 'liveStreamingDetails'], None)

            output_record['video_id'] = item['id']
            output_record['duration'] = item['contentDetails']['duration']
            if 'liveStreamingDetails' in item.keys():
                output_record['liveStreamingDetails'] = item['liveStreamingDetails']

            output.append(output_record)

        return output

    @staticmethod
    def _get_video_id_list(videos):

        video_df = pd.DataFrame(videos)
        return list(video_df['video_id'])

    def _video_details(self, cache_file, videos):

        video_id_list = self._get_video_id_list(videos)

        if os.path.isfile(cache_file) is False:

            videos_details = self._get_videos_meta_data(video_id_list)

            with open(cache_file, 'w') as fp:
                json.dump(videos_details, fp)
        else:
            with open(cache_file) as fp:
                videos_details = json.load(fp)

            last_update_time = os.path.getmtime(cache_file)
            current_time = time.time()
            one_day_secs = 24 * 60 * 60
            if (current_time - one_day_secs) > last_update_time:
                # if the file was last updated more than 24 hours ago do an update
                detailed_video_id_list = self._get_video_id_list(videos=videos_details)

                missing_video_id = list(set(video_id_list) - set(detailed_video_id_list))
                videos_details += self._get_videos_meta_data(missing_video_id)

                with open(cache_file, 'w') as fp:
                    json.dump(videos_details, fp)
            else:
                print(f'{cache_file=} is less than 24 hours old no update performed')

        return videos_details

    @property
    def _df_videos(self):

        a = pd.DataFrame(self.videos)
        a.set_index('video_id', inplace=True)
        a['Published Time'] = a['publishedAt'].apply(isoparse)
        a.drop('publishedAt', axis=1, inplace=True)
        a.rename(columns={'channel': 'Channel'}, inplace=True)

        return a.drop_duplicates(keep='last')

    @property
    def _df_videos_details(self):

        b = pd.DataFrame(self.videos_detail)
        b.set_index('video_id', inplace=True)
        b['Duration (s)'] = b['duration'].apply(ISO8601_duration_to_time_delta).dt.total_seconds()
        b.drop('duration', axis=1, inplace=True)

        return b.drop_duplicates(keep='last')

    @property
    def DataFrame(self):

        return pd.concat([self._df_videos, self._df_videos_details], axis=1)

parse = argparse.ArgumentParser(description='Weekly Office of Basement accountabilit generator')
parse.add_argument('-youtubeapikey', type=str, required=True)
parse.add_argument('-twitter_consumer_key', type=str, required=True)
parse.add_argument('-twitter_consumer_secret', type=str, required=True)
parse.add_argument('-twitter_access_token', type=str, required=True)
parse.add_argument('-twitter_access_secret', type=str, required=True)


if __name__ == "__main__":

    command_args = parse.parse_args()

    data_class = BrainBlazeInfoGraphic(api_key=command_args.youtubeapikey)

    # inforgraphic
    three_month_videos = data_class.DataFrame
    grouped_count = \
        three_month_videos.groupby(
            ['Channel', pd.Grouper(key='Published Time', freq='W-MON', origin='start_day')])[
        'Duration (s)'].count()
    grouped_count.fillna(0)
    grouped_duration = \
        three_month_videos.groupby(
            ['Channel', pd.Grouper(key='Published Time', freq='W-MON', origin='start_day')])[
            'Duration (s)'].sum() / 60
    grouped_duration.fillna(0)
    grouped_percentage_duration = grouped_duration / grouped_duration.groupby('Published Time').sum() * 100

    max_brain_blaze_video_per_week = grouped_count.loc['Brain Blaze'].max()

    fig = make_subplots(rows=2, cols=4,
                        row_heights=[0.8, 0.2],
                        subplot_titles=['Content by Channel (last 12 weeks)'],
                        specs=[[{"type": "xy", "colspan": 4},None, None, None],
                               [{"type": "domain"}, {"type": "domain"}, {"type": "domain"}, {"type": "domain"}]])

    data_to_plot = grouped_duration.unstack('Channel').loc[midight_12_week_ago_monday:midnight_monday]
    for index, channel in enumerate(three_month_videos['Channel'].unique()):
        fig.add_trace(go.Scatter(x=data_to_plot.index,
                                 y=data_to_plot[channel].values,
                                 name=channel,
                                 hoverinfo='x+y',
                                 legendgroup='Channels',
                                 legendgrouptitle={'text':'Channel'},
                                 mode='lines',
                                 line={'color':px.colors.qualitative.Dark24[index]},
                                 stackgroup='one'),
                        row=1, col=1)

    fig.add_trace(go.Indicator(mode="gauge+number+delta",
                                value=grouped_duration.unstack('Channel').loc[midnight_monday].sum(),
                                delta={'reference': grouped_duration.unstack('Channel').loc[minight_last_monday].sum()},
                                gauge={'axis': {'range': [0, grouped_duration.groupby('Published Time').sum().max() * 1.2]},
                                      'threshold': {'value': grouped_duration.groupby('Published Time').sum().mean() }},
                                title={'text': "Total Simon Whistler Output (minutes)"}),
                  row=2, col=1)

    fig.add_trace(go.Indicator(
        mode="gauge+number+delta",
        value=grouped_percentage_duration.unstack('Channel').fillna(0)['Brain Blaze'].loc[midnight_monday],
        delta={'reference': grouped_percentage_duration.unstack('Channel').fillna(0)['Brain Blaze'].loc[minight_last_monday]},
        number={'suffix': '%'},
        gauge={'axis': {'range': [0, 100]},
               'threshold': {'value': grouped_percentage_duration.groupby('Channel').mean()['Brain Blaze']}},
        title={'text': "Brain Blaze<br>Percent of total content"}),
                  row=2, col=2)

    fig.add_trace(go.Indicator(
        mode="gauge+number+delta",
        value=grouped_count.unstack('Channel').fillna(0)['Brain Blaze'].loc[midnight_monday],
        delta={'reference': grouped_count.unstack('Channel').fillna(0)['Brain Blaze'].loc[minight_last_monday]},

        gauge={'axis': {'range': [0, max_brain_blaze_video_per_week+2 ],
                        'nticks' : int(max_brain_blaze_video_per_week+3) },
               'threshold': {'value': grouped_count.groupby('Channel').mean()['Brain Blaze']}},
        title={'text': "Brain Blaze<br>Number of Videos"}),
                  row=2, col=3)

    fig.add_trace(go.Indicator(
        mode="gauge+number+delta",
        value=grouped_duration.unstack('Channel').fillna(0)['Brain Blaze'].loc[midnight_monday],
        delta={'reference': grouped_duration.unstack('Channel').fillna(0)['Brain Blaze'].loc[minight_last_monday]},
        gauge={'axis': {'range': [0, grouped_duration.groupby('Channel').max()['Brain Blaze']]},
               'threshold': {'value': grouped_duration.groupby('Channel').mean()['Brain Blaze']}},
        title={'text': "Business Blaze<br>duration (minutes)"}),
                  row=2, col=4)


    fig.update_layout(height=1000, width=1600,
                      title_text=f'Office of Basement Accountability, Weekly report for period ending {midnight_monday:%d %b %Y}',
                      title_x=0.5)
    fig.update_xaxes(title_text="Date of Week Start (always a Monday)", row=1, col=1)
    fig.update_xaxes(dtick=7*24*60*60*1000, tick0=midight_12_week_ago_monday )
    fig.update_yaxes(title_text="Content Duration (minutes)", row=1, col=1)

    fig.write_image('minutes.png', engine='kaleido')

    auth = tweepy.OAuthHandler(consumer_key=command_args.twitter_consumer_key,
                               consumer_secret=command_args.twitter_consumer_secret)
    auth.set_access_token(key=command_args.twitter_access_token,
                          secret=command_args.twitter_access_secret)

    #auth = tweepy.OAuth2BearerHandler(command_args.twitter_bearer_handler)
    twitter_api = tweepy.API(auth)

    media_list = []
    response = twitter_api.media_upload('minutes.png')
    media_list.append(response.media_id_string)
    twitter_api.update_status('Weekly report from the Office of Basement Accountability',
                              media_ids=media_list)