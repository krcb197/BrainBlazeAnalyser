"""
This module provides access to the Google API used by the Brain Blaze Analyser, originally
it started out as an extension to the YoutubeEasyWrapper, however, increasingly the whole
class was being overridden so the link was broken
"""
import os
from datetime import datetime, timezone
from time import sleep

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'



class _GoogleAPIBase:

    def __init__(self, service_name, api_version):
        self.service = None
        self.__service_name = service_name
        self.__api_version = api_version

    def initialize(self, api_key):
        self.service = build(self.__service_name, self.__api_version, developerKey=api_key)


class DriveWrapper(_GoogleAPIBase):

    def __init__(self):
        super().__init__(service_name='drive', api_version='v3')

    def upload_basic(self, filename:str):

        file_metadata = {'name': filename}
        media = MediaFileUpload(filename,
                                mimetype='image/jpeg')

        # pylint: disable=maybe-no-member
        file = self.service.files().create(body=file_metadata, media_body=media,
                                           fields='id').execute()
        print(F'File ID: {file.get("id")}')

        return file.get('id')

class YouTubeWrapper(_GoogleAPIBase):

    def __init__(self):
        super().__init__(service_name='youtube', api_version='v3')

    def channel_videos(self, channelID,
                       publishedAfter: datetime = datetime(year=2001, month=1, day=1,
                                                           tzinfo=timezone.utc),
                       publishedBefore: datetime = datetime.now(timezone.utc), **kwargs):
        kwargs['channelId'] = channelID
        kwargs['publishedBefore'] = publishedBefore.isoformat()
        kwargs['publishedAfter'] = publishedAfter.isoformat()
        kwargs['maxResults'] = 50  # maximum number supported by the API
        if 'order' in kwargs.items():
            kwargs['order'] = kwargs['order']
        else:
            kwargs['order'] = 'relevance'
        kwargs['part'] = 'id'
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
            result = {}
            result['video_id'] = item['id']['videoId']
            output.append(result)

        return output

    def channel(self, channelID, **kwargs):
        kwargs['id'] = channelID
        kwargs['part'] = 'id,snippet'

        items = []
        results = self.service.channels().list(**kwargs).execute()

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
            result = {}
            result['title'] = item['snippet']['title']
            result['id'] = item['id']
            output.append(result)

        return output

    def get_metadata(self, video_id):
        parts="id, snippet, contentDetails, statistics, liveStreamingDetails"
        list_videos_by_id = self.service.videos().list(id=video_id,
                                                       part=parts).execute()
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
                output_record['Channel'] = result['snippet']['channelTitle']
                if 'liveStreamingDetails' in result.keys():
                    output_record['liveStreamingDetails'] = result['liveStreamingDetails']
                output_record['statistics'] = result['statistics']

                output.append(output_record)
        else:
            output = dict.fromkeys(['video_id', 'title', 'description', 'publishedAt', 'tags', 'contentDetails', 'statistics'], None)

            output['video_id'] = results[0]['id']
            output['title'] = results[0]['snippet']['title']
            output['description'] = results[0]['snippet']['description']
            output['publishedAt'] = results[0]['snippet']['publishedAt']
            output['contentDetails'] = results[0]['contentDetails']
            output['Channel'] = results[0]['snippet']['channelTitle']
            if 'liveStreamingDetails' in results[0].keys():
                output['liveStreamingDetails'] = results[0]['liveStreamingDetails']
            output['statistics'] = results[0]['statistics']

        return output

    def get_playlist(self, playlist_id:str, **kwargs):

        kwargs['playlistId'] = playlist_id
        kwargs['maxResults'] = 50  # maximum number supported by the API
        kwargs['part'] = 'snippet'

        items = []
        results = self.service.playlistItems().list(**kwargs).execute()

        current_page = 0
        max_pages = 30000
        while results and current_page < max_pages:
            items.extend(results['items'])

            if 'nextPageToken' in results:
                kwargs['pageToken'] = results['nextPageToken']
                sleep(1)
                results = self.service.playlistItems().list(**kwargs).execute()
                current_page += 1
            else:
                break

        output = []
        for item in items:
            result = {}
            result['video_id'] = item['snippet']['resourceId']['videoId']
            output.append(result)

        return output
