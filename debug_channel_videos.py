
from ExtendedYoutubeEasyWrapper import ExtendedYoutubeEasyWrapper
import datetime

easy_wrapper = ExtendedYoutubeEasyWrapper()
easy_wrapper.initialize(api_key='AIzaSyBdcDloERbtgS3KImiFIIWJn5YdF8BNdQ4')

if __name__ == "__main__":

    # grab 12 weeks of top tenz videos
    today = datetime.date.today()
    midight_12_week_ago_monday = datetime.datetime.combine(time=datetime.time(),
                                                           date=today - datetime.timedelta(
                                                               days=today.weekday(), weeks=12),
                                                           tzinfo=datetime.timezone.utc)

    video_list = easy_wrapper.channel_videos(channelID='UCQ-hpFPF4nOKoKPEAZM_THw',  # Top Tenz
                                             order='date',
                                             publishedAfter=midight_12_week_ago_monday)

