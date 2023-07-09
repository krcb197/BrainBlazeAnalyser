
import time
import json
import os
import argparse

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

import re
from datetime import timedelta, datetime, timezone
from dateutil.parser import isoparse
from typing import Optional, Union, List

from google_access_lib import YouTubeWrapper

def ISO8601_duration_to_time_delta(value: str) -> Optional[timedelta]:
    """
    function to convert ISO8601 relative periods (used for video durations) into a Python
    timedelta

    :param value: a string containing a ISO duration
    :return: duration as a timedelta
    """

    if value[0:2] == 'PT':
        analysis = re.findall(r'(\d+\D)', value[2:])

        if analysis is None:
            print(f'failed to process: {value}')
            return None
        else:
            min = 0
            sec = 0
            hour = 0
            for entry in analysis:
                if entry[-1] == 'M':
                    min = int(entry[:-1])
                elif entry[-1] == 'S':
                    sec = int(entry[:-1])
                elif entry[-1] == 'H':
                    hour = int(entry[:-1])
                else:
                    print('unhanded subsection {entry} in {value}')

            return timedelta(minutes=min, seconds=sec, hours=hour)
    else:
        print(f'string should start PT, {value}')
        return None

# constant used in the code to determine
three_month_back = datetime.now(tz=timezone.utc) - timedelta(weeks=13)

class BrainBlazeDataSet:

    # YouTube Channel ID for Brain Blaze (formally known as Business Blaze)
    brain_blaze_channel_ID = 'UCYY5GWf7MHFJ6DZeHreoXgw'
    # First ever BrainBlaze Video
    dawn_brain_blaze = datetime(year=2019,
                                month=9,
                                day=1,
                                tzinfo=timezone.utc)

    # YouTube heavily restrict their API usage, to help manage daily allowances, this library uses
    # a data cache, stored in some JSON files
    _brain_blaze_video_fn = 'brain_blaze_videos.json'
    _detailed_blaze_video_fn = 'detailed_brain_blaze_videos.json'

    def __init__(self, api_key):

        self.easy_wrapper = YouTubeWrapper()
        self.easy_wrapper.initialize(api_key=api_key)

        # the data set is split into brain blaze videos and other simon whistler videos, this
        # allow the usage of the YouTube API to be managed, for example the analyser by default
        # retrieves data on every brain blaze video ever made but restricts other channels to the
        # last three months
        self.brain_blaze_videos = self.retrieve_brain_blaze_videos()
        self.brain_blaze_videos_detail = self.retrieve_brain_blaze_videos_details()

    def retrieve_brain_blaze_videos(self):

        return self.channel_videos(cache_file=self._brain_blaze_video_fn,
                                   channel_id_list=[self.brain_blaze_channel_ID],
                                   earliest_date=self.dawn_brain_blaze)

    def retrieve_brain_blaze_videos_details(self):

        return self.video_details(cache_file=self._detailed_blaze_video_fn,
                                  videos=self.brain_blaze_videos)

    def channel_videos(self, cache_file: str, earliest_date: datetime, channel_id_list: List[str]):
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
                videos = get_videos(earliest_date)

                with open(cache_file, 'w') as fid:
                    json.dump(videos, fid)
            else:
                print(f'{cache_file=} is less than 24 hours old no update performed')

        return videos

    @staticmethod
    def _get_video_id_list(videos):

        id_list = []
        for video in videos:
            id_list.append(video['video_id'])

        return id_list

    def video_details(self, cache_file, videos):

        if os.path.isfile(cache_file) is False:
            videos_details = []
            for video in videos:
                video_detail = self.easy_wrapper.get_metadata(video_id=video['video_id'])
                videos_details.append(video_detail)


            with open(cache_file, 'w') as fp:
                json.dump(videos_details, fp)
        else:
            last_update_time = os.path.getmtime(cache_file)
            current_time = time.time()
            one_day_secs = 24 * 60 * 60
            if (current_time - one_day_secs) > last_update_time:
                # if the file was last updated more than 24 hours ago do an update

                video_id_list = self._get_video_id_list(videos=videos)
                videos_details = []

                for video_id in video_id_list:

                    video_detail = self.easy_wrapper.get_metadata(video_id=video_id)
                    videos_details.append(video_detail)

                with open(cache_file, 'w') as fp:
                    json.dump(videos_details, fp)
            else:
                print(f'{cache_file=} is less than 24 hours old no update performed')
                with open(cache_file) as fid:
                    videos_details = json.load(fid)


        return videos_details

    @property
    def DataFrame(self):

        # create a panda dataframe for the data
        duration_list = []
        published_list = []
        title_list = []
        stream_list = []
        views_list = []
        like_list = []
        dislike_list = []
        video_id_list = []
        channel_list = []

        videos = self.brain_blaze_videos
        videos_detail = self.brain_blaze_videos_detail

        for (video_summary, video_data) in zip(videos, videos_detail):

            duration = ISO8601_duration_to_time_delta(video_data['contentDetails']['duration'])
            if duration is None:
                continue

            channel_list.append(video_data['Channel'])
            duration_list.append(duration.total_seconds())
            published_list.append(isoparse(video_data['publishedAt']))
            stream_list.append('liveStreamingDetails' in video_data.keys())
            views_list.append(int(video_data['statistics']['viewCount']))
            like_list.append(int(video_data['statistics']['likeCount']))
            if 'dislikeCount' in video_data['statistics']:
                dislike_list.append(int(video_data['statistics']['dislikeCount']))
            else:
                dislike_list.append(np.nan)
            video_id_list.append(video_summary['video_id'])
            title_list.append(video_data['title'])

        DataFrame = pd.DataFrame({'Title': title_list,
                                        'Channel': channel_list,
                                        'Published Time': published_list,
                                        'Duration (s)': duration_list,
                                        'Stream': stream_list,
                                        'Likes': like_list,
                                        'Dislikes': dislike_list,
                                        'Views': views_list}, index=video_id_list)
        DataFrame['Like:Dislike Ratio'] = DataFrame['Likes'] / DataFrame['Dislikes']
        DataFrame['Like:Views Ratio'] = DataFrame['Likes'] / DataFrame['Views']
        DataFrame['Dislikes:Views Ratio'] = DataFrame['Dislikes'] / DataFrame['Views']
        DataFrame['Views Seconds'] = DataFrame['Duration (s)'] * DataFrame['Views']
        DataFrame['Writer'] = 'Unknown'

        return DataFrame

    @property
    def blaze_DataFrame(self) -> pd.DataFrame:
        """
        Return a DataFrame with the all the Brain Blaze videos

        :return:
        """
        df = self.DataFrame
        return df[df['Channel'] == 'Brain Blaze']

    @property
    def scripted_blaze_DataFrame(self) -> pd.DataFrame:
        """
        Brain Blaze is truely a scripted channel, therefore a number of videos are exclude for
        breaking the rules, this method returns only true brain blaze content

        :return:
        """
        blaze_DataFrame = self.blaze_DataFrame
        to_return = blaze_DataFrame[blaze_DataFrame['Stream'] == False]  # gaming streams

        # A streaming video that was not marked as such
        to_return = to_return.drop(index='VTQU9TwKtqs')

        # An experimental video unscripted: Shopping Channel Fails (Experimental)
        to_return = to_return.drop(index='WuOYQMPOiTI')

        # Announcement that the channel was renamed from Business Blaze to Brain Blaze
        to_return = to_return.drop(index='4E_MFtFKAgQ')

        #
        to_return = to_return.drop(index='vI7v3D9OQ7g')

        return to_return

parse = argparse.ArgumentParser(description='Weekly Office of Basement accountability generator')
parse.add_argument('-youtubeapikey', type=str, required=True)

if __name__ == "__main__":

    command_args = parse.parse_args()

    data_class = BrainBlazeDataSet(api_key=command_args.youtubeapikey)

    with open('.krcb197_google_API_key') as fp:
        api_key=fp.readlines()

    data_class = BrainBlazeDataSet(api_key=api_key)

    video_DataFrame_noStreams = data_class.scripted_blaze_DataFrame
    video_DataFrame_noStreams.at['XatOAULW03c','Writer'] = 'Liam Bird'
    # Kevin Jennings groups his Brain Blaze Videos by a YouTube Play list
    kevin_videos = data_class.easy_wrapper.get_playlist(playlist_id='PLrwYSRD-7tO0W4gc-6hlZ8895JJ7FZVQC')
    for kevin_video in kevin_videos:
        video_DataFrame_noStreams.at[kevin_video['video_id'], 'Writer'] = 'Kevin Jennings'

    video_DataFrame_noStreams.sort_values('Published Time', inplace=True)

    plt.figure()
    non_epic = video_DataFrame_noStreams[video_DataFrame_noStreams['Duration (s)'] / 60 < 80]
    epic =  video_DataFrame_noStreams[video_DataFrame_noStreams['Duration (s)'] / 60 >= 80]
    plt.plot(video_DataFrame_noStreams['Published Time'][9:],
             np.convolve(video_DataFrame_noStreams['Duration (s)'] / 60, np.ones(10) / 10)[9:-9],
             linewidth=5,
             color='grey',
             label='10 Video rolling average')
    plt.plot(non_epic['Published Time'], non_epic['Duration (s)'] / 60, 'x', markerfacecolor='blue', markersize=7)
    plt.plot(epic['Published Time'], epic['Duration (s)'] / 60, marker='*', markersize=20,
             markerfacecolor='yellow', markeredgecolor='red', linestyle='None', label='Epic Blaze')
    plt.ylabel('Duration (Min)')
    plt.ylabel('Video Duration (Min)')
    plt.xlabel('Published Date')
    plt.grid()
    plt.title('Brain Blaze Video Duration by publication date')
    plt.legend()
    ax = plt.gca()

    x_lim = ax.get_xlim()
    ax.hlines(y=80, xmin=x_lim[0], xmax=x_lim[1])
    ax.set_xlim(x_lim)

    axins = ax.inset_axes([0.7, 0.67, 0.15, 0.2])
    axins.plot(non_epic['Published Time'], non_epic['Duration (s)'] / 60, 'x', markerfacecolor='blue', markersize=20)
    axins.hlines(y=80, xmin=x_lim[0], xmax=x_lim[1])
    axins.set_xlim(19305, 19310)
    axins.set_ylim(79.3, 80.2)
    axins.set_xticklabels([])
    axins.set_yticklabels([])
    near_epic_video = non_epic.loc['fGSiTjbN1Gk']
    epic_short_fall =(80*60)-near_epic_video['Duration (s)']
    axins.arrow(x=near_epic_video['Published Time'], y=near_epic_video['Duration (s)'] / 60, dx=0, dy=80 - (near_epic_video['Duration (s)'] / 60), shape='full', width=0.05, length_includes_head=True, head_length=0.1)
    axins.text(x=near_epic_video['Published Time'],
               y=np.mean([(near_epic_video['Duration (s)'] / 60), 80]),
               s=f'{epic_short_fall}s short of epic', ha='center', va='center', bbox=dict(facecolor='white', boxstyle='round'))
    ax.indicate_inset_zoom(axins, edgecolor="black")

    writer_fig = plt.figure()
    ax = plt.gca()
    writer_summary = video_DataFrame_noStreams.groupby('Writer')['Duration (s)'].sum() / 60
    writer_summary.plot(kind='pie', autopct='%.5f%%', pctdistance=1.2, labeldistance=1.5,
                        ylabel='',
                        title='Cumulative Total of Brain Blaze Video Duration by Writer')
