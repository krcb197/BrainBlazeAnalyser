"""
This module extends the youtube easy wrapper replacing a few functions with improved versions
"""
from youtube_easy_api.easy_wrapper import YoutubeEasyWrapper

class ExtendedYoutubeEasyWrapper(YoutubeEasyWrapper):


    def channel_videos(self, channelID, **kwargs):
        kwargs['channelId'] = channelID
        if 'order' in kwargs.items():
            kwargs['order'] = kwargs['order']
        else:
            kwargs['order'] = 'relevance'
        kwargs['part'] = 'id,snippet'
        kwargs['type'] = 'video'

        items = []
        results = self.service.search().list(**kwargs).execute()

        current_page = 0
        max_pages = 300
        while results and current_page < max_pages:
            items.extend(results['items'])

            if 'nextPageToken' in results:
                kwargs['pageToken'] = results['nextPageToken']
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
            output.append(result)

        return output

    def get_metadata(self, video_id, include_comments=True):
        list_videos_by_id = self.service.videos().list(id=video_id,
                                                       part="id, snippet, contentDetails, statistics").execute()
        results = list_videos_by_id.get("items", [])[0]
        output = dict.fromkeys(['title', 'description', 'publishedAt', 'tags', 'contentDetails', 'statistics'], None)

        output['title'] = results['snippet']['title']
        output['description'] = results['snippet']['description']
        output['publishedAt'] = results['snippet']['publishedAt']
        output['contentDetails'] = results['contentDetails']
        output['statistics'] = results['statistics']

        if ('commentCount' in results['statistics']) and (include_comments is True):
            output['comments'] = self.extract_video_comments(self.service,
                                                             part='snippet',
                                                             videoId=video_id,
                                                             textFormat='plainText')

        return output