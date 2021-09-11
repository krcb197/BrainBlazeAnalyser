
import json
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import re
from datetime import timedelta, datetime
from typing import Optional

from ExtendedYoutubeEasyWrapper import ExtendedYoutubeEasyWrapper

def ISO8601_duration_to_time_delta(value: str) -> Optional[timedelta]:
    """
    function to convert ISO8601 relative periods (used for video durations) into a Python
    timedelta

    :param value: a string containing a ISO duration
    :return: duration as a timedelta
    """

    if value == 'P0D':
        return None

    assert value[0:2] == 'PT', f'string should start PT, {value}'
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

if __name__ == "__main__":

    brain_blaze_video_fn = 'brain_blaze_videos.json'
    detailed_blaze_video_fn = 'detailed_brain_blaze_videos.json'
    brain_blaze_channel_ID = 'UCYY5GWf7MHFJ6DZeHreoXgw'

    with open('.google_API_key') as fp:
        api_key=fp.readlines()

    easy_wrapper = ExtendedYoutubeEasyWrapper()
    easy_wrapper.initialize(api_key=api_key)

    # get the complete catalogue of videos from the channel and create a cached file of them,
    #TODO in the next version this will look for new videos since the last entry in the cache
    if os.path.isfile(brain_blaze_video_fn) is False:
        brain_blaze_videos = easy_wrapper.channel_videos(channelID=brain_blaze_channel_ID)

        with open(brain_blaze_video_fn, 'w') as fp:
            json.dump(brain_blaze_videos, fp)
    else:
        with open(brain_blaze_video_fn) as fp:
            brain_blaze_videos = json.load(fp)

    # collect the detailed meta data for the videos
    # TODO a future version will look only for videos that need to be appended to the dataset
    if os.path.isfile(detailed_blaze_video_fn) is False:
        brain_blaze_videos_details = []
        for video in brain_blaze_videos:
            brain_blaze_videos_details.append(easy_wrapper.get_metadata(video_id=video['video_id'], include_comments=False))

        with open(detailed_blaze_video_fn, 'w') as fp:
            json.dump(brain_blaze_videos_details, fp)
    else:
        with open(detailed_blaze_video_fn) as fp:
            brain_blaze_videos_details = json.load(fp)

    # create a panda dataframe for the data
    duration_list = []
    published_list = []
    title_list = []
    for video_data in brain_blaze_videos_details:

        duration = ISO8601_duration_to_time_delta(video_data['contentDetails']['duration'])
        if duration is None:
            continue

        duration_list.append(duration.total_seconds())
        published_list.append(datetime.strptime(video_data['publishedAt'], "%Y-%m-%dT%H:%M:%S%z"))

        title_list.append(video_data['title'])


    video_DataFrame = pd.DataFrame({'Title':title_list, 'Published Time':published_list, 'Duration (s)':duration_list})

    # exclude videos over 1.5 hours this removes the live streams of gaming which are not proper
    # videos and a very short video that announced the channel name change
    video_DataFrame_noStreams = video_DataFrame[video_DataFrame['Duration (s)'] < 5400]
    video_DataFrame_noStreams = video_DataFrame_noStreams[video_DataFrame_noStreams['Duration (s)'] > 180]


    # make a plot of the data
    fig, ax = plt.subplots(nrows=2, ncols=1, sharex=True, figsize=(16, 9))
    ax[0].plot(video_DataFrame_noStreams['Published Time'], video_DataFrame_noStreams['Duration (s)'] / 60, 'x')
    ax[0].set_ylabel('Duration (Min)')
    ax[0].set_xlabel('Published Data')
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
