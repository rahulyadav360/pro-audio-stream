from botocore.exceptions import ClientError
from bs4 import BeautifulSoup

import requests
import logging
import os
import boto3
import json
import random

def create_presigned_url(object_name):
    s3_client = boto3.client('s3',
                             region_name=os.environ.get('S3_PERSISTENCE_REGION'),
                             config=boto3.session.Config(signature_version='s3v4',s3={'addressing_style': 'path'}))
    try:
        bucket_name = os.environ.get('S3_PERSISTENCE_BUCKET')
        response = s3_client.generate_presigned_url('get_object',
                                                    Params={'Bucket': bucket_name,
                                                            'Key': object_name},
                                                    ExpiresIn=6000)
    except ClientError as e:
        logging.error(e)
        return None

    # The response contains the presigned URL
    return response

def populate_playlist_from_rss(url):
    playlist = []
    rss_raw_text = requests.get(url).text
    rss_parsed_data = BeautifulSoup(rss_raw_text,'xml')
    all_episodes = rss_parsed_data.find_all('item')
    all_episodes.reverse()
    
    for index, episode in enumerate(all_episodes):
        current_track_data = ({ 'url': episode.enclosure['url'], "title": episode.title.text, "token": str(index+1)})
        playlist.append(current_track_data)

    return playlist

def update_playlist(url, playlist):
    rss_raw_text = requests.get(url).text
    rss_parsed_data = BeautifulSoup(rss_raw_text,'xml')
    all_episodes = rss_parsed_data.find_all('item')
    all_episodes.reverse()
    
    for index in range(len(playlist), len(all_episodes)):
        current_track_data = ({ 'url': all_episodes[index].enclosure['url'], "title": all_episodes[index].title.text, "token": str(index+1)})
        playlist.append(current_track_data)

    return playlist

def get_track_index(token, playlist):
    for index, value in enumerate(playlist):
        if value['token'] == token:
            track_index = index
            break
        else:
            track_index = 0
    return track_index

def shuffle_playlist(index, playlist):
    current_track_data = playlist[index]
    playlist.pop(index)
    random.shuffle(playlist)
    playlist.insert(0,current_track_data)
    return playlist