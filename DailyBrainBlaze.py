
from typing import List
import datetime
import time
import json
import os
from dateutil.parser import isoparse
import argparse

from google_access_lib import YouTubeWrapper


import tweepy

today = datetime.date.today()
one_day_old = datetime.datetime.combine(time=datetime.time(),
                                            date=today - datetime.timedelta(hours=24),
                                            tzinfo=datetime.timezone.utc)


import pandas as pd

class DailyBrainBlaze:

    # YouTube Channel ID other Simon Whistler YouTube channels, thise are used to make sure
    # Simon is not overly focusing on the "wrong" channels
    BrainBlazeChannelID = 'UCYY5GWf7MHFJ6DZeHreoXgw'

    _video_cache_fn = 'DailyBrainBlaze_video_cache.json'
    _video_detail_cache_fn = 'DailyBrainBlaze_video_detail_cache.json'

    def __init__(self, api_key):

        self.easy_wrapper = YouTubeWrapper()
        self.easy_wrapper.initialize(api_key=api_key)

        # the data set is split into brain blaze videos and other simon whistler videos, this
        # allow the usage of the YouTube API to be managed, for example the analyser by default
        # retrieves data on every brain blaze video ever made but restricts other channels to the
        # last three months
        self.videos = self._channel_videos(cache_file=self._video_cache_fn,
                                           channel_id_list=[self.BrainBlazeChannelID],
                                           earliest_date=one_day_old)
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
            last_update_time = os.path.getmtime(cache_file)
            current_time = time.time()
            one_day_secs = 24 * 60 * 60
            if (current_time - one_day_secs) > last_update_time:
                # if the file was last updated more than 24 hours ago do an update

                # The cache file does not exist and must be generated from scratch
                videos = get_videos(earliest_date)

                with open(cache_file, 'w') as fp:
                    json.dump(videos, fp)
            else:
                print(f'{cache_file=} is less than 24 hours old no update performed')

                # cache file exists and must be updated
                with open(cache_file) as fp:
                    videos = json.load(fp)

        return videos

    def _get_videos_meta_data(self, video_id):

        if len(video_id) > 50:
            items = []
            for start_point in range(0, len(video_id), 50):
                end_point = start_point + 50
                if end_point > len(video_id):
                    end_point = len(video_id)

                results = self.easy_wrapper.service.videos().list(id=video_id[start_point:end_point],
                                                                  part="id, snippet, contentDetails, liveStreamingDetails").execute()
                items.extend( results.get("items", []))


        else:
            results = self.easy_wrapper.service.videos().list(id=video_id,
                                             part="id, snippet, contentDetails, liveStreamingDetails").execute()
            items = results.get("items", [])

        output = []
        for item in items:
            output_record = dict.fromkeys(
                ['video_id', 'duration',
                 'liveStreamingDetails'], None)

            output_record['video_id'] = item['id']
            output_record['title'] = item['snippet']['title']

            output.append(output_record)

        return output

    @staticmethod
    def _get_video_id_list(videos):

        video_df = pd.DataFrame(videos)
        if len(video_df) == 0:
            return None
        return list(video_df['video_id'])

    def _video_details(self, cache_file, videos):

        video_id_list = self._get_video_id_list(videos)
        if video_id_list is None:
            return None

        if os.path.isfile(cache_file) is False:

            videos_details = self._get_videos_meta_data(video_id_list)

            with open(cache_file, 'w') as fp:
                json.dump(videos_details, fp)
        else:


            last_update_time = os.path.getmtime(cache_file)
            current_time = time.time()
            one_day_secs = 24 * 60 * 60
            if (current_time - one_day_secs) > last_update_time:
                # if the file was last updated more than 24 hours ago do an update
                videos_details = self._get_videos_meta_data(video_id_list)

                with open(cache_file, 'w') as fp:
                    json.dump(videos_details, fp)
            else:
                print(f'{cache_file=} is less than 24 hours old no update performed')

                with open(cache_file) as fp:
                    videos_details = json.load(fp)

        return videos_details

    @property
    def _df_videos_details(self):

        if self.videos_detail is None:
            return None
        b = pd.DataFrame(self.videos_detail)
        b.set_index('video_id', inplace=True)

        return b.drop_duplicates(keep='last')

    @property
    def DataFrame(self):

        return self._df_videos_details

    def __len__(self):

        return len(self.videos)

parse = argparse.ArgumentParser(description='Weekly Office of Basement accountabilit generator')
parse.add_argument('-youtubeapikey', type=str, required=True)
parse.add_argument('-twitter_consumer_key', type=str, required=True)
parse.add_argument('-twitter_consumer_secret', type=str, required=True)
parse.add_argument('-twitter_access_token', type=str, required=True)
parse.add_argument('-twitter_access_secret', type=str, required=True)
parse.add_argument('-test_mode', action='store_true')


if __name__ == "__main__":

    command_args = parse.parse_args()

    data_class = DailyBrainBlaze(api_key=command_args.youtubeapikey)

    if len(data_class) > 0:

        twitter_api = tweepy.Client(consumer_key=command_args.twitter_consumer_key,
                                    consumer_secret=command_args.twitter_consumer_secret,
                                    access_token=command_args.twitter_access_token,
                                    access_token_secret=command_args.twitter_access_secret)

        for video_ID, item in data_class.DataFrame.iterrows():
            tweet_text = f'New Brain Blaze Video: {item["title"]} \n https://www.youtube.com/watch?v={video_ID}'

            if command_args.test_mode:
                print(f'tweet_sent: {tweet_text}')
            else:
                twitter_api.create_tweet(text=tweet_text)
                print(f'tweet_sent: {tweet_text}')

    print('End of Job')
