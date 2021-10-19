"""
This module extends the youtube easy wrapper replacing a few functions with improved versions
"""
from youtube_easy_api.easy_wrapper import YoutubeEasyWrapper
from datetime import datetime, timezone
from time import sleep

class ExtendedYoutubeEasyWrapper(YoutubeEasyWrapper):


    def channel_videos(self, channelID, publishedAfter:datetime=datetime(year=2001, month=1, day=1, tzinfo=timezone.utc), **kwargs):
        kwargs['channelId'] = channelID
        kwargs['publishedAfter'] = publishedAfter.isoformat()
        if 'order' in kwargs.items():
            kwargs['order'] = kwargs['order']
        else:
            kwargs['order'] = 'relevance'
        kwargs['part'] = 'id,snippet'
        kwargs['type'] = 'video'

        items = []
        results = self.service.search().list(**kwargs).execute()

        current_page = 0
        max_pages = 30000
        while results and current_page < max_pages:
            items.extend(results['items'])

            if 'nextPageToken' in results:
                kwargs['pageToken'] = results['nextPageToken']
                sleep(1)
                results = self.service.search().list(**kwargs).execute()
                current_page += 1
            else:
                break

        output = []
        for item in items:
            result = dict()
            result['title'] = item['snippet']['title']
            result['channel'] = item['snippet']['channelTitle']
            result['video_id'] = item['id']['videoId']
            result['channel_id'] = item['snippet']['channelId']
            result['publishedAt'] = item['snippet']['publishedAt']
            output.append(result)

        return output

    def get_metadata(self, video_id, include_comments=True):
        list_videos_by_id = self.service.videos().list(id=video_id,
                                                       part="id, snippet, contentDetails, statistics, liveStreamingDetails").execute()
        results = list_videos_by_id.get("items", [])
        if len(results) > 1:
            output = []
            for result in results:
                output_record = dict.fromkeys(
                    ['video_id', 'title', 'description', 'publishedAt', 'tags', 'contentDetails',
                     'statistics', 'liveStreamingDetails'], None)

                output_record['video_id'] = result['id']
                output_record['title'] = result['snippet']['title']
                output_record['description'] = result['snippet']['description']
                output_record['publishedAt'] = result['snippet']['publishedAt']
                output_record['contentDetails'] = result['contentDetails']
                if 'liveStreamingDetails' in result.keys():
                    output_record['liveStreamingDetails'] = result['liveStreamingDetails']
                output_record['statistics'] = result['statistics']

                if ('commentCount' in result['statistics']) and (include_comments is True):
                    output_record['comments'] = self.extract_video_comments(self.service,
                                                                     part='snippet',
                                                                     videoId=result['id'],
                                                                     textFormat='plainText')
                output.append(output_record)
        else:
            output = dict.fromkeys(['video_id', 'title', 'description', 'publishedAt', 'tags', 'contentDetails', 'statistics'], None)

            output['video_id'] = results[0]['id']
            output['title'] = results[0]['snippet']['title']
            output['description'] = results[0]['snippet']['description']
            output['publishedAt'] = results[0]['snippet']['publishedAt']
            output['contentDetails'] = results[0]['contentDetails']
            if 'liveStreamingDetails' in results[0].keys():
                output['liveStreamingDetails'] = results[0]['liveStreamingDetails']
            output['statistics'] = results[0]['statistics']

            if ('commentCount' in results[0]['statistics']) and (include_comments is True):
                output['comments'] = self.extract_video_comments(self.service,
                                                                 part='snippet',
                                                                 videoId=results[0]['id'],
                                                                 textFormat='plainText')

        return output