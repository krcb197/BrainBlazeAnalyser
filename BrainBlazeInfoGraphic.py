
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime

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

from BrainBlazeAnalyser import BrainBlazeDataSet, three_month_back

if __name__ == "__main__":

    with open('.google_API_key') as fp:
        api_key=fp.readlines()

    data_class = BrainBlazeDataSet(api_key=api_key)

    video_DataFrame = data_class.DataFrame
    #video_DataFrame_noStreams = data_class.scripted_blaze_DataFrame

    # inforgraphic
    three_month_videos = video_DataFrame[video_DataFrame['Published Time'] > three_month_back]
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
    for channel in video_DataFrame['Channel'].unique():
        fig.add_trace(go.Scatter(x=data_to_plot.index,
                                 y=data_to_plot[channel].values,
                                 name=channel,
                                 hoverinfo='x+y',
                                 legendgroup='Channels',
                                 legendgrouptitle={'text':'Channel'},
                                 mode='lines',
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
        value=grouped_percentage_duration.loc['Brain Blaze', midnight_monday],
        delta={'reference': grouped_percentage_duration.loc['Brain Blaze', minight_last_monday]},
        number={'suffix': '%'},
        gauge={'axis': {'range': [0, 100]},
               'threshold': {'value': grouped_percentage_duration.groupby('Channel').mean()['Brain Blaze']}},
        title={'text': "Brain Blaze<br>Percent of total content"}),
                  row=2, col=2)

    fig.add_trace(go.Indicator(
        mode="gauge+number+delta",
        value=grouped_count.loc['Brain Blaze', midnight_monday],
        delta={'reference': grouped_count.loc['Brain Blaze', minight_last_monday]},

        gauge={'axis': {'range': [0, max_brain_blaze_video_per_week]},
               'threshold': {'value': grouped_count.groupby('Channel').mean()['Brain Blaze']}},
        title={'text': "Brain Blaze<br>Number of Videos"}),
                  row=2, col=3)

    fig.add_trace(go.Indicator(
        mode="gauge+number+delta",
        value=grouped_duration.loc['Brain Blaze', midnight_monday],
        delta={'reference': grouped_duration.loc['Brain Blaze', minight_last_monday]},
        gauge={'axis': {'range': [0, grouped_duration.groupby('Channel').max()['Brain Blaze']]},
               'threshold': {'value': grouped_duration.groupby('Channel').mean()['Brain Blaze']}},
        title={'text': "Business Blaze<br>duration (minutes)"}),
                  row=2, col=4)


    fig.update_layout(height=1000, width=1600,
                      title_text=f'Office of Basement Accountability, Weekly report for period ending {midnight_monday:%d %b %Y}',
                      title_x=0.5)
    fig.update_xaxes(title_text="Date of Week Start (always a Monday)", row=1, col=1)
    fig.update_yaxes(title_text="Content Duration (minutes)", row=1, col=1)

    fig.write_image('minutes.png', engine='kaleido')