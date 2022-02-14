
import plotly.express as px

import pandas as pd

from BrainBlazeAnalyser import BrainBlazeDataSet, three_month_back

if __name__ == "__main__":

    with open('.krcb197_google_API_key') as fp:
        api_key=fp.readlines()

    data_class = BrainBlazeDataSet(api_key=api_key)

    video_DataFrame = data_class.DataFrame
    video_DataFrame = video_DataFrame[video_DataFrame['Stream'] == False]  # gaming streams
    video_DataFrame = video_DataFrame.drop(index='VTQU9TwKtqs')
    video_DataFrame = video_DataFrame.query('Channel=="Brain Blaze" | Channel=="The Casual Criminalist"')
    three_month_videos = video_DataFrame[video_DataFrame['Published Time'] > three_month_back]

    grouped_duration_views = \
        three_month_videos.groupby(
            ['Channel', pd.Grouper(key='Published Time', freq='W-MON', origin='start_day')])[
            'Views Seconds'].sum() / 3600

    fig=px.bar(grouped_duration_views.reset_index(), color='Channel', x='Published Time', y='Views Seconds', barmode='group')
    fig.update_layout(height=600, width=800,
                      title_text=f'Office of Basement Accountability<br>Special Investigation into claims of view time of The Casual Criminalist',
                      title_x=0.5)
    fig.update_xaxes(title_text="Aggragated videos published in week (Week start on a Monday)")
    fig.update_yaxes(title_text="Video view × duration [hours]")

    fig.write_image('special_minutes.png', engine='kaleido')