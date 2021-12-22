
import time
import json
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import re
from datetime import timedelta, datetime, timezone
from dateutil.parser import isoparse
from typing import Optional, Union, List

from ExtendedYoutubeEasyWrapper import ExtendedYoutubeEasyWrapper

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

    # YouTube Channel ID other Simon Whistler YouTube channels, thise are used to make sure
    # Simon is not overly focusing on the "wrong" channels
    other_whistler_channels = ['UClnDI2sdehVm1zm_LmUHsjQ',  # Biographics
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

    # YouTube heavily restrict their API usage, to help manage daily allowances, this library uses
    # a data cache, stored in some JSON files
    _other_whistler_video_fn = 'other_videos.json'
    _detailed_other_whistler_video_fn = 'detailed_other_videos.json'
    _brain_blaze_video_fn = 'brain_blaze_videos.json'
    _detailed_blaze_video_fn = 'detailed_brain_blaze_videos.json'

    def __init__(self, api_key):

        self.easy_wrapper = ExtendedYoutubeEasyWrapper()
        self.easy_wrapper.initialize(api_key=api_key)

        # the data set is split into brain blaze videos and other simon whistler videos, this
        # allow the usage of the YouTube API to be managed, for example the analyser by default
        # retrieves data on every brain blaze video ever made but restricts other channels to the
        # last three months
        self.brain_blaze_videos = self.retrieve_brain_blaze_videos()
        self.other_whistler_videos = self.retrieve_other_whistler_video()
        self.brain_blaze_videos_detail = self.retrieve_brain_blaze_videos_details()
        self.other_videos_detail = self.retrieve_other_videos_details()

    def retrieve_brain_blaze_videos(self):

        return self.channel_videos(cache_file=self._brain_blaze_video_fn,
                                   channel_id_list=[self.brain_blaze_channel_ID],
                                   earliest_date=self.dawn_brain_blaze)

    def retrieve_other_whistler_video(self):

        return self.channel_videos(cache_file=self._other_whistler_video_fn,
                                   channel_id_list=self.other_whistler_channels,
                                   earliest_date=three_month_back)

    def retrieve_brain_blaze_videos_details(self):

        return self.video_details(cache_file=self._detailed_blaze_video_fn,
                                  videos=self.brain_blaze_videos)

    def retrieve_other_videos_details(self):

        return self.video_details(cache_file=self._detailed_other_whistler_video_fn,
                                  videos=self.other_whistler_videos)

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
                video_detail = self.easy_wrapper.get_metadata(video_id=video['video_id'],
                                                              include_comments=False)
                videos_details.append(video_detail)


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

                video_id_list = self._get_video_id_list(videos=videos)
                detailed_video_id_list = self._get_video_id_list(videos=videos_details)

                for video_id in video_id_list:
                    if video_id not in detailed_video_id_list:

                        video_detail = self.easy_wrapper.get_metadata(video_id=video_id,
                                                                      include_comments=False)
                        videos_details.append(video_detail)

                    with open(cache_file, 'w') as fp:
                        json.dump(videos_details, fp)
            else:
                print(f'{cache_file=} is less than 24 hours old no update performed')


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

        videos = self.brain_blaze_videos + self.other_whistler_videos
        videos_detail = self.brain_blaze_videos_detail + self.other_videos_detail

        for (video_summary, video_data) in zip(videos, videos_detail):

            duration = ISO8601_duration_to_time_delta(video_data['contentDetails']['duration'])
            if duration is None:
                continue

            assert video_summary['video_id'] == video_data['video_id']

            channel_list.append(video_summary['channel'])
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

        return to_return

if __name__ == "__main__":

    with open('.krcb197_google_API_key') as fp:
        api_key=fp.readlines()

    data_class = BrainBlazeDataSet(api_key=api_key)

    video_DataFrame = data_class.DataFrame
    video_DataFrame_noStreams = data_class.scripted_blaze_DataFrame

    # make a plot of the data
    fig, ax = plt.subplots(nrows=2, ncols=1, sharex=True, figsize=(16, 9))
    ax[0].plot(video_DataFrame_noStreams['Published Time'], video_DataFrame_noStreams['Duration (s)'] / 60, 'x')
    ax[0].set_ylabel('Duration (Min)')
    ax[0].set_xlabel('Published Date')
    ax[0].set_title('Individual Videos')
    ax[0].grid()


    grouped_weeks = video_DataFrame_noStreams.groupby([pd.Grouper(key='Published Time', freq='W-MON')])['Duration (s)'].sum()
    ax[1].plot(grouped_weeks.index, grouped_weeks / 60, 'x')
    ax[1].plot(grouped_weeks.index[3:], np.convolve(grouped_weeks / 60, np.ones(4)/4)[3:-3], label='4 Week rolling average')
    ax[1].set_ylabel('Total Video Minutes per Week')
    ax[1].set_xlabel('Analysis Week')
    ax[1].set_title('Videos grouped by calendar week')
    ax[1].grid()
    ax[1].legend()
    fig.autofmt_xdate()


    fig.suptitle('Brain Blaze (formally Business Blaze) - YouTube Content')

    fig.savefig('BrainBlazeAnalysis.png')
    #plt.close(fig)

    # make a plot of the data
    fig, ax = plt.subplots(nrows=2, ncols=1, sharex=True, figsize=(16, 9))
    ax[0].plot(video_DataFrame_noStreams['Published Time'],
               video_DataFrame_noStreams['Views Seconds'], 'x')
    ax[0].set_ylabel('Eyeball Duration')
    ax[0].set_xlabel('Published Date')
    ax[0].set_title('Individual Videos')
    ax[0].grid()

    grouped_weeks = \
    video_DataFrame_noStreams.groupby([pd.Grouper(key='Published Time', freq='W-MON')])[
        'Views Seconds'].sum()
    ax[1].plot(grouped_weeks.index, grouped_weeks, 'x')
    ax[1].plot(grouped_weeks.index[3:], np.convolve(grouped_weeks, np.ones(4) / 4)[3:-3],
               label='4 Week rolling average')
    ax[1].set_ylabel('Total Eyeball Seconds per Week')
    ax[1].set_xlabel('Analysis Week')
    ax[1].set_title('Videos grouped by calendar week')
    ax[1].grid()
    ax[1].legend()
    fig.autofmt_xdate()

    fig.suptitle('Brain Blaze (formally Business Blaze) - YouTube Content')
    plt.close(fig)

    #fig.savefig('BrainBlazeAnalysis.png')

    ax_ratio = [None, None, None, None]
    fig, ax = plt.subplots(nrows=4, ncols=1, sharex=True, figsize=(16, 9))
    ax[0].plot(video_DataFrame_noStreams['Published Time'],
               video_DataFrame_noStreams['Views'], 'bx')
    ax[0].set_ylabel('Views', color='b')
    ax[1].plot(video_DataFrame_noStreams['Published Time'],
               video_DataFrame_noStreams['Likes'], 'bx')
    ax[1].set_ylabel('Likes', color='b')
    ax_ratio[1] = ax[1].twinx()
    ax_ratio[1].plot(video_DataFrame_noStreams['Published Time'],
               video_DataFrame_noStreams['Like:Views Ratio'], 'g+')
    ax_ratio[1].set_ylabel('Likes Per View', color='g')
    ax[2].plot(video_DataFrame_noStreams['Published Time'],
               video_DataFrame_noStreams['Dislikes'], 'bx')
    ax[2].set_ylabel('Dislikes', color='b')
    ax_ratio[2] = ax[2].twinx()
    ax_ratio[2].plot(video_DataFrame_noStreams['Published Time'],
                     video_DataFrame_noStreams['Dislikes:Views Ratio'], 'g+')
    ax_ratio[2].set_ylabel('Dislikes Per View', color='g')
    ax[3].plot(video_DataFrame_noStreams['Published Time'],
               video_DataFrame_noStreams['Like:Dislike Ratio'], 'g+')
    ax[3].set_ylabel('Like:Dislike Ratio', color='g')
    plt.close(fig)

    # make a plot of the data
    fig, ax = plt.subplots(nrows=2, ncols=1, sharex=True, figsize=(16, 9))
    three_month_videos = video_DataFrame[video_DataFrame['Published Time'] > three_month_back ]
    grouped_weeks = \
    three_month_videos.groupby(['Channel',pd.Grouper(key='Published Time', freq='W-MON', origin='start_day')])[
        'Duration (s)'].sum() / 3600
    grouped_weeks.unstack('Channel').iloc[1:-1].plot.area(ax = ax[0])
    fig.suptitle('Weekly report from the Office of Basement Accountability')

    percentage_duration = grouped_weeks / grouped_weeks.groupby('Published Time').sum() * 100
    percentage_duration.unstack('Channel').iloc[1:-1].plot.area(ax = ax[1])
    ax[1].set_ylim([0, 100])

    box = ax[1].get_position()
    ax[1].set_position([box.x0, box.y0, box.width * 0.9, box.height])
    ax[1].legend(loc='center left', bbox_to_anchor=(1, 0.5), title='Channel', title_fontsize='large')
    ax[1].set_ylabel('Channel accumulated video duration\n'
                     'for week as percentage of all Video Duration')

    box = ax[0].get_position()
    ax[0].set_position([box.x0, box.y0, box.width * 0.9, box.height])
    ax[0].legend(loc='center left', bbox_to_anchor=(1, 0.5), title='Channel', title_fontsize='large')
    ax[0].set_ylabel('Channel accumulated video duration [hours]')


