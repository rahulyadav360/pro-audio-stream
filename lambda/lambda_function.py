"""
 Copyright (C) 2020 Dabble Lab - All Rights Reserved
 You may use, distribute and modify this code under the
 terms and conditions defined in file 'LICENSE.txt', which
 is part of this source code package.
 
 For additional copyright information please
 visit : http://dabblelab.com/copyright
 """

from ask_sdk_core.utils import is_request_type, is_intent_name
from ask_sdk_core.dispatch_components import (AbstractRequestHandler, AbstractExceptionHandler, AbstractRequestInterceptor, AbstractResponseInterceptor)
from ask_sdk_core.skill_builder import CustomSkillBuilder
from ask_sdk_model.interfaces.audioplayer import (
    PlayDirective, PlayBehavior, AudioItem, Stream, AudioItemMetadata,
    StopDirective, ClearQueueDirective, ClearBehavior)
from ask_sdk_model.interfaces.display import (Image, ImageInstance)
from ask_sdk_dynamodb.adapter import DynamoDbAdapter
from utils import (create_presigned_url, populate_playlist_from_rss, get_track_index, update_playlist, shuffle_playlist)

import logging
import json
import random
import os
import boto3

# RSS feed URL of the podcast
rss_url = "https://anchor.fm/s/172e72c0/podcast/rss"

# Defining the database region, table name and dynamodb persistence adapter
ddb_region = os.environ.get('DYNAMODB_PERSISTENCE_REGION')
ddb_table_name = os.environ.get('DYNAMODB_PERSISTENCE_TABLE_NAME')
ddb_resource = boto3.resource('dynamodb', region_name=ddb_region)
dynamodb_adapter = DynamoDbAdapter(table_name=ddb_table_name, create_table=False, dynamodb_resource=ddb_resource)

# Initializing the logger and setting the level to "INFO"
# Read more about it here https://www.loggly.com/ultimate-guide/python-logging-basics/
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Intent Handlers

# Check if device supports audio playlack
class CheckAudioInterfaceHandler(AbstractRequestHandler):
    
    def can_handle(self, handler_input):
        if handler_input.request_envelope.context.system.device:
            return handler_input.request_envelope.context.system.device.supported_interfaces.audio_player is None
        else:
            return False

    def handle(self, handler_input):
        logger.info("In CheckAudioInterfaceHandler")
        language_prompts = handler_input.attributes_manager.request_attributes["_"]
        speech_output = random.choice(language_prompts['DEVICE_NOT_SUPPORTED'])
            
        return (
            handler_input.response_builder
                .speak(speech_output)
                .set_should_end_session(True)
                .response
            )

#This Handler is called when the skill is invoked by using only the invocation name(Ex. Alexa, open template four)
class LaunchRequestHandler(AbstractRequestHandler):
    
    def can_handle(self, handler_input):
        return is_request_type("LaunchRequest")(handler_input)
    
    def handle(self, handler_input):
        logger.info("In LaunchRequestHandler")
        language_prompts = handler_input.attributes_manager.request_attributes["_"]
        persistent_attributes = handler_input.attributes_manager.persistent_attributes
        
        if persistent_attributes.get('playback_session_data') is not None:
            episode_number = persistent_attributes['playback_session_data']['token']
            persistent_attributes['playlist'] = update_playlist(rss_url, persistent_attributes['playlist'])
            handler_input.attributes_manager.save_persistent_attributes()
            
            speech_output = random.choice(language_prompts["RESUME_PLAYBACK"]).format(episode_number)
            reprompt = random.choice(language_prompts["RESUME_PLAYBACK_REPROMPT"]).format(episode_number)
            
        else:
            skill_name = language_prompts['SKILL_NAME']
            
            playlist = populate_playlist_from_rss(rss_url)
            index = len(playlist) - 1
            token = playlist[index]['token']
            url = playlist[index]['url']
            offset = 0
            title = playlist[index]['title']
            subtitle = "Episode {}".format(token)
            
            persistent_attributes['playlist'] = playlist
            persistent_attributes["playback_session_data"] = { 'index': index, 'token': token, 'url': url, 'offset': offset, 'title': title, 'loop': False, 'shuffle': False }
            handler_input.attributes_manager.save_persistent_attributes()    
            
            speech_output = random.choice(language_prompts["NEW_USER_GREETING"]).format(skill_name)
            reprompt = random.choice(language_prompts["NEW_USER_GREETING_REPROMPT"])
        
        return (
            handler_input.response_builder
                .speak(speech_output)
                .ask(reprompt)
                .response
            )

class PlayNewestEpisodeIntentHandler(AbstractRequestHandler):
    
    def can_handle(self, handler_input):
        return is_intent_name("PlayNewestEpisodeIntent")(handler_input)
    
    def handle(self, handler_input):
        logger.info("In PlayNewestEpisodeIntentHandler")
        language_prompts = handler_input.attributes_manager.request_attributes["_"]
        persistent_attributes = handler_input.attributes_manager.persistent_attributes
        
        playlist = populate_playlist_from_rss(rss_url)
        index = len(playlist) - 1
        token = playlist[index]['token']
        url = playlist[index]['url']
        offset = 0
        title = playlist[index]['title']
        subtitle = "Episode {}".format(token)
        
        persistent_attributes['playlist'] = playlist
        persistent_attributes["playback_session_data"] = { 'index': index, 'token': token, 'url': url, 'offset': offset, 'title': title, 'loop': False, 'shuffle': False }
        handler_input.attributes_manager.save_persistent_attributes()
        
        speech_output = random.choice(language_prompts["PLAY_LATEST_EPISODE"])
        
        audio_directive = PlayDirective(
                            play_behavior = PlayBehavior.REPLACE_ALL, 
                            audio_item = AudioItem(
                                stream = Stream(
                                    token = token,
                                    url = url,
                                    offset_in_milliseconds = offset
                                    ),
                                metadata = AudioItemMetadata(
                                    title = title,
                                    subtitle = subtitle,
                                    art = Image(
                                        sources = [
                                            ImageInstance(
                                                url = create_presigned_url('Media/album_art.png')
                                                )
                                            ]
                                        )
                                    )
                                )
                            )
        return (
            handler_input.response_builder
                .speak(speech_output)
                .add_directive(audio_directive)
                .set_should_end_session(True)
                .response
            )

class PlayOldestEpisodeIntentHandler(AbstractRequestHandler):
    
    def can_handle(self, handler_input):
        return is_intent_name("PlayOldestEpisodeIntent")(handler_input)
    
    def handle(self, handler_input):
        logger.info("In PlayOldestEpisodeIntentHandler")
        language_prompts = handler_input.attributes_manager.request_attributes["_"]
        persistent_attributes = handler_input.attributes_manager.persistent_attributes
        
        playlist = populate_playlist_from_rss(rss_url)
        index = 0
        token = playlist[index]['token']
        url = playlist[index]['url']
        offset = 0
        title = playlist[index]['title']
        subtitle = "Episode {}".format(token)
        
        persistent_attributes['playlist'] = playlist
        persistent_attributes["playback_session_data"] = { 'index': index, 'token': token, 'url': url,'offset': offset, 'title': title, 'loop': False, 'shuffle': False }
        handler_input.attributes_manager.save_persistent_attributes()
        
        speech_output = random.choice(language_prompts["PLAY_OLDEST_EPISODE"])
        
        audio_directive = PlayDirective(
                            play_behavior = PlayBehavior.REPLACE_ALL, 
                            audio_item = AudioItem(
                                stream=Stream(
                                    token=token,
                                    url=url,
                                    offset_in_milliseconds=offset,
                                    ),
                                metadata = AudioItemMetadata(
                                    title = title,
                                    subtitle = subtitle,
                                    art = Image(
                                        sources = [
                                            ImageInstance(
                                                url = create_presigned_url('Media/album_art.png')
                                                )
                                            ]
                                        )
                                    )
                                )
                            )
        return (
            handler_input.response_builder
                .speak(speech_output)
                .add_directive(audio_directive)
                .set_should_end_session(True)
                .response
            )

class ChooseEpisodeIntentHandler(AbstractRequestHandler):
    
    def can_handle(self, handler_input):
        return is_intent_name("ChooseEpisodeIntent")(handler_input)
    
    def handle(self, handler_input):
        logger.info("In ChooseEpisodeIntentHandler")
        language_prompts = handler_input.attributes_manager.request_attributes["_"]
        persistent_attributes = handler_input.attributes_manager.persistent_attributes
        
        token = handler_input.request_envelope.request.intent.slots["EpisodeNumber"].value
        if token is None:
            token = handler_input.request_envelope.request.intent.slots["OrdinalNumber"].value
        if token is None:
            speech_output = random.choice(language_prompts["CHOOSE_EPISODE"])
            reprompt = random.choice(language_prompts["CHOOSE_EPISODE_REPROMPT"])
            return handler_input.response_builder.speak(speech_output).ask(reprompt).response
        
        playlist = populate_playlist_from_rss(rss_url)
        index = int(token) - 1
        url = playlist[index]['url']
        offset = 0
        title = playlist[index]['title']
        subtitle = "Episode {}".format(token)
        
        persistent_attributes['playlist'] = playlist
        persistent_attributes["playback_session_data"] = { 'index': index, 'token': token, 'url': url, 'offset': offset, 'title': title, 'loop': False, 'shuffle': False }
        handler_input.attributes_manager.save_persistent_attributes()
        
        speech_output = random.choice(language_prompts["PLAYING_CHOSEN_EPISODE"]).format(token)
        
        audio_directive = PlayDirective(
                            play_behavior = PlayBehavior.REPLACE_ALL, 
                            audio_item = AudioItem(
                                stream=Stream(
                                    token=token,
                                    url=url,
                                    offset_in_milliseconds=offset
                                    ),
                                metadata = AudioItemMetadata(
                                    title = title,
                                    subtitle = subtitle,
                                    art = Image(
                                        sources = [
                                            ImageInstance(
                                                url = create_presigned_url('Media/album_art.png')
                                                )
                                            ]
                                        )
                                    )
                                )
                            )
        return (
            handler_input.response_builder
                .speak(speech_output)
                .add_directive(audio_directive)
                .set_should_end_session(True)
                .response
            )

class PauseIntentHandler(AbstractRequestHandler):
    
    def can_handle(self, handler_input):
        return (
            is_request_type("PlaybackController.PauseCommandIssued")(handler_input) or
            is_intent_name("AMAZON.PauseIntent")(handler_input)    
            )
    
    def handle(self, handler_input):
        logger.info("In PauseIntentHandler")
        audio_directive = StopDirective()
        
        return (
            handler_input.response_builder
                .add_directive(audio_directive)
                .set_should_end_session(True)
                .response
            )

class ResumeIntentHandler(AbstractRequestHandler):
    
    def can_handle(self, handler_input):
        return (
            is_intent_name("AMAZON.ResumeIntent")(handler_input) or
            is_intent_name("AMAZON.YesIntent")(handler_input) or
            is_request_type("PlaybackController.PlayCommandIssued")(handler_input)
            )
    
    def handle(self, handler_input):
        logger.info("In ResumeIntentHandler")
        language_prompts = handler_input.attributes_manager.request_attributes["_"]
        persistent_attributes = handler_input.attributes_manager.persistent_attributes
        
        if persistent_attributes.get("playback_session_data") is not None:
            token = persistent_attributes["playback_session_data"]['token']
            url = persistent_attributes["playback_session_data"]['url']
            offset = persistent_attributes["playback_session_data"]["offset"]
            title = persistent_attributes["playback_session_data"]["title"]
            subtitle = "Episode {}".format(token)

        else:
            playlist = populate_playlist_from_rss(rss_url)
            index = len(playlist) - 1
            token = playlist[index]['token']
            url = playlist[index]['url']
            offset = 0
            title = playlist[index]['title']
            subtitle = "Episode {}".format(token)
            
            handler_input.response_builder.speak(random.choice(language_prompts["PLAY_LATEST_EPISODE"]))
            
            persistent_attributes['playlist'] = playlist
            persistent_attributes["playback_session_data"] = { 'index': index, 'token': token, 'url': url,'offset': offset, 'title': title, 'loop': False, 'shuffle': False }
            handler_input.attributes_manager.save_persistent_attributes()
        
        audio_directive = PlayDirective(
                            play_behavior = PlayBehavior.REPLACE_ALL, 
                            audio_item = AudioItem(
                                stream=Stream(
                                    token=token,
                                    url=url,
                                    offset_in_milliseconds=offset
                                    ),
                                metadata = AudioItemMetadata(
                                    title = title,
                                    subtitle = subtitle,
                                    art = Image(
                                        sources = [
                                            ImageInstance(
                                                url = create_presigned_url('Media/album_art.png')
                                                )
                                            ]
                                        )
                                    )
                                )
                            )
        return (
            handler_input.response_builder
                .add_directive(audio_directive)
                .set_should_end_session(True)
                .response
            )

class NoIntentHandler(AbstractRequestHandler):
    
    def can_handle(self, handler_input):
        return is_intent_name("AMAZON.NoIntent")(handler_input)
    
    def handle(self, handler_input):
        logger.info("In NoIntentHandler")
        language_prompts = handler_input.attributes_manager.request_attributes["_"]
        persistent_attributes = handler_input.attributes_manager.persistent_attributes
        
        playlist = populate_playlist_from_rss(rss_url)
        index = len(playlist) - 1
        token = playlist[index]['token']
        url = playlist[index]['url']
        offset = 0
        title = playlist[index]['title']
        subtitle = "Episode {}".format(token)
        
        speech_output = random.choice(language_prompts["PLAY_LATEST_EPISODE"])
        
        persistent_attributes['playlist'] = playlist
        persistent_attributes["playback_session_data"] = { 'index': index, 'token': token, 'url': url,'offset': offset, 'title': title, 'loop': False, 'shuffle': False }
        handler_input.attributes_manager.save_persistent_attributes()

        audio_directive = PlayDirective(
                            play_behavior = PlayBehavior.REPLACE_ALL, 
                            audio_item = AudioItem(
                                stream = Stream(
                                    token = token,
                                    url = url,
                                    offset_in_milliseconds = offset
                                    ),
                                metadata = AudioItemMetadata(
                                    title = title,
                                    subtitle = subtitle,
                                    art = Image(
                                        sources = [
                                            ImageInstance(
                                                url = create_presigned_url('Media/album_art.png')
                                                )
                                            ]
                                        )
                                    )
                                )
                            )
        return (
            handler_input.response_builder
                .speak(speech_output)
                .add_directive(audio_directive)
                .set_should_end_session(True)
                .response
            )

class NextIntentHandler(AbstractRequestHandler):
    
    def can_handle(self, handler_input):
        return ( 
            is_intent_name("AMAZON.NextIntent")(handler_input) or
            is_request_type("PlaybackController.NextCommandIssued")(handler_input)
            )
    
    def handle(self, handler_input):
        logger.info("In NextIntentHandler")
        language_prompts = handler_input.attributes_manager.request_attributes["_"]
        persistent_attributes = handler_input.attributes_manager.persistent_attributes
        
        playlist = persistent_attributes['playlist']
        loop = persistent_attributes["playback_session_data"]["loop"]
        index = int(persistent_attributes["playback_session_data"]["index"])
        
        if index != len(playlist) - 1:
            index += 1
        elif (index == len(playlist) - 1) and loop:
            index = 0
        else:
            speech_output = random.choice(language_prompts["END_OF_PLAYLIST"])
            return handler_input.response_builder.speak(speech_output).set_should_end_session(True).response
        
        token = playlist[index]['token']
        url = playlist[index]['url']
        offset = 0
        title = playlist[index]['title']
        subtitle = "Episode {}".format(token)
        
        persistent_attributes["playback_session_data"].update({ 'index': index, 'token': token, 'url': url, 'offset': offset, 'title': title })
        handler_input.attributes_manager.save_persistent_attributes()        

        audio_directive = PlayDirective(
                            play_behavior = PlayBehavior.REPLACE_ALL, 
                            audio_item = AudioItem(
                                stream = Stream(
                                    token = token,
                                    url = url,
                                    offset_in_milliseconds = offset
                                    ),
                                metadata = AudioItemMetadata(
                                    title = title,
                                    subtitle = subtitle,
                                    art = Image(
                                        sources = [
                                            ImageInstance(
                                                url = create_presigned_url('Media/album_art.png')
                                                )
                                            ]
                                        )
                                    )
                                )
                            )

        return (
            handler_input.response_builder
                .add_directive(audio_directive)
                .set_should_end_session(True)
                .response
            )

class PreviousIntentHandler(AbstractRequestHandler):
    
    def can_handle(self, handler_input):
        return (
            is_intent_name("AMAZON.PreviousIntent")(handler_input) or
            is_request_type("PlaybackController.PreviousCommandIssued")(handler_input)
            )
    
    def handle(self, handler_input):
        logger.info("In PreviousIntentHandler")
        language_prompts = handler_input.attributes_manager.request_attributes["_"]
        persistent_attributes = handler_input.attributes_manager.persistent_attributes
        
        playlist = persistent_attributes['playlist']
        loop = persistent_attributes["playback_session_data"]["loop"]
        index = int(persistent_attributes["playback_session_data"]["index"])
        
        if index != 0:
            index -= 1
        elif (index == 0) and loop:
            index = len(playlist) - 1
        else:
            speech_output = speech_output = random.choice(language_prompts["START_OF_PLAYLIST"])
            return handler_input.response_builder.speak(speech_output).set_should_end_session(True).response
        
        token = playlist[index]['token']
        url = playlist[index]['url']
        offset = 0
        title = playlist[index]['title']
        subtitle = "Episode {}".format(token)
        
        persistent_attributes["playback_session_data"].update({ 'index': index, 'token': token, 'url': url, 'offset': offset, 'title': title})
        handler_input.attributes_manager.save_persistent_attributes()        

        audio_directive = PlayDirective(
                            play_behavior = PlayBehavior.REPLACE_ALL, 
                            audio_item = AudioItem(
                                stream = Stream(
                                    token = token,
                                    url = url,
                                    offset_in_milliseconds = offset,
                                    ),
                                metadata = AudioItemMetadata(
                                    title = title,
                                    subtitle = subtitle,
                                    art = Image(
                                        sources = [
                                            ImageInstance(
                                                url = create_presigned_url('Media/album_art.png')
                                                )
                                            ]
                                        )
                                    )
                                )
                            )

        return (
            handler_input.response_builder
                .add_directive(audio_directive)
                .set_should_end_session(True)
                .response
            )

class RepeatIntentHandler(AbstractRequestHandler):
    
    def can_handle(self, handler_input):
        return (is_intent_name("AMAZON.RepeatIntent")(handler_input) or
                is_intent_name("AMAZON.StartOverIntent")(handler_input))
    
    def handle(self, handler_input):
        logger.info("In RepeatIntentHandler")
        language_prompts = handler_input.attributes_manager.request_attributes["_"]
        persistent_attributes = handler_input.attributes_manager.persistent_attributes
        
        playlist = persistent_attributes['playlist']
        index = int(persistent_attributes["playback_session_data"]["index"])
        token = persistent_attributes['playlist'][index]['token']
        url = persistent_attributes['playlist'][index]['url']
        offset = 0
        title = persistent_attributes['playlist'][index]['title']
        subtitle = "Episode {}".format(token)
        
        audio_directive = PlayDirective(
                            play_behavior = PlayBehavior.REPLACE_ALL, 
                            audio_item = AudioItem(
                                stream=Stream(
                                    token=token,
                                    url=url,
                                    offset_in_milliseconds=offset,
                                    ),
                                metadata = AudioItemMetadata(
                                    title = title,
                                    subtitle = subtitle,
                                    art = Image(
                                        sources = [
                                            ImageInstance(
                                                url = create_presigned_url('Media/album_art.png')
                                                )
                                            ]
                                        )
                                    )
                                )
                            )

        return (
            handler_input.response_builder
                .add_directive(audio_directive)
                .set_should_end_session(True)
                .response
            )

class ShuffleOnIntentHandler(AbstractRequestHandler):
    
    def can_handle(self, handler_input):
        return is_intent_name("AMAZON.ShuffleOnIntent")(handler_input)
    
    def handle(self, handler_input):
        logger.info("In ShuffleOnIntentHandler")
        language_prompts = handler_input.attributes_manager.request_attributes["_"]
        persistent_attributes = handler_input.attributes_manager.persistent_attributes
        
        index = int(persistent_attributes["playback_session_data"]["index"])
        old_playlist = persistent_attributes['playlist']
        new_playlist = shuffle_playlist(index, old_playlist)
        
        persistent_attributes['playlist'] = new_playlist
        persistent_attributes["playback_session_data"].update({"index": 0, "shuffle": True })
        handler_input.attributes_manager.save_persistent_attributes()
        
        speech_output = random.choice(language_prompts["SHUFFLE_ON"])
        
        return (
            handler_input.response_builder
                .speak(speech_output)
                .set_should_end_session(True)
                .response
            )

class ShuffleOffIntentHandler(AbstractRequestHandler):
    
    def can_handle(self, handler_input):
        return is_intent_name("AMAZON.ShuffleOffIntent")(handler_input)
    
    def handle(self, handler_input):
        logger.info("In ShuffleOffIntentHandler")
        language_prompts = handler_input.attributes_manager.request_attributes["_"]
        persistent_attributes = handler_input.attributes_manager.persistent_attributes
        
        token = persistent_attributes["playback_session_data"]["token"]
        index = int(token) - 1
        playlist = populate_playlist_from_rss(rss_url)
        persistent_attributes['playlist'] = playlist
        persistent_attributes["playback_session_data"].update({"index": index, "shuffle": False})
        handler_input.attributes_manager.save_persistent_attributes()
        
        speech_output = random.choice(language_prompts["SHUFFLE_OFF"])
        
        return (
            handler_input.response_builder
                .speak(speech_output)
                .set_should_end_session(True)
                .response
            )

class LoopOnIntentHandler(AbstractRequestHandler):
    
    def can_handle(self, handler_input):
        return is_intent_name("AMAZON.LoopOnIntent")(handler_input)
    
    def handle(self, handler_input):
        logger.info("In LoopOnIntentHandler")
        language_prompts = handler_input.attributes_manager.request_attributes["_"]
        persistent_attributes = handler_input.attributes_manager.persistent_attributes
        
        persistent_attributes['playback_session_data'].update({"loop": True})
        handler_input.attributes_manager.save_persistent_attributes()
        
        speech_output = random.choice(language_prompts["LOOP_ON"])
        
        return (
            handler_input.response_builder
                .speak(speech_output)
                .set_should_end_session(True)
                .response
            )

class LoopOffIntentHandler(AbstractRequestHandler):
    
    def can_handle(self, handler_input):
        return is_intent_name("AMAZON.LoopOffIntent")(handler_input)
    
    def handle(self, handler_input):
        logger.info("In LoopOffIntentHandler")
        language_prompts = handler_input.attributes_manager.request_attributes["_"]
        persistent_attributes = handler_input.attributes_manager.persistent_attributes
        
        persistent_attributes['playback_session_data'].update({"loop": False})
        handler_input.attributes_manager.save_persistent_attributes()
        
        speech_output = random.choice(language_prompts["LOOP_OFF"])
        
        return (
            handler_input.response_builder
                .speak(speech_output)
                .set_should_end_session(True)
                .response
            )

class PlaybackStartedEventHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_request_type("AudioPlayer.PlaybackStarted")(handler_input)
    
    def handle(self, handler_input):
        logger.info("In PlaybackStartedEventHandler")
        persistent_attributes = handler_input.attributes_manager.persistent_attributes
        audio_player_attributes = handler_input.request_envelope.request
        
        playlist = persistent_attributes['playlist']
        token = audio_player_attributes.token
        index = int(get_track_index(token, playlist))
        url = playlist[index]['url']
        offset = audio_player_attributes.offset_in_milliseconds
        title = playlist[index]['title']
        
        persistent_attributes["playback_session_data"].update({ 'index': index, 'token': token, 'url': url, 'offset': offset, 'title': title})
        handler_input.attributes_manager.save_persistent_attributes()
        
        return handler_input.response_builder.response

class PlaybackStoppedEventHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_request_type("AudioPlayer.PlaybackStopped")(handler_input)
    
    def handle(self, handler_input):
        logger.info("In PlaybackStoppedEventHandler")
        persistent_attributes = handler_input.attributes_manager.persistent_attributes
        audio_player_attributes = handler_input.request_envelope.request
        
        playlist = persistent_attributes['playlist']
        token = audio_player_attributes.token
        index = int(get_track_index(token, playlist))
        url = playlist[index]['url']
        offset = audio_player_attributes.offset_in_milliseconds
        title = playlist[index]['title']
        
        persistent_attributes["playback_session_data"].update({ 'index': index, 'token': token, 'url': url, 'offset': offset, 'title': title})
        handler_input.attributes_manager.save_persistent_attributes()

        return handler_input.response_builder.response

class PlaybackNearlyFinishedEventHandler(AbstractRequestHandler):
    
    def can_handle(self, handler_input):
        return is_request_type("AudioPlayer.PlaybackNearlyFinished")(handler_input)
    
    def handle(self, handler_input):
        logger.info("In PlaybackNearlyFinishedEventHandler")
        language_prompts = handler_input.attributes_manager.request_attributes["_"]
        persistent_attributes = handler_input.attributes_manager.persistent_attributes

        playlist = persistent_attributes['playlist']
        loop = persistent_attributes["playback_session_data"]["loop"]
        index = int(persistent_attributes["playback_session_data"]["index"])
        old_token = playlist[index]['token']
        
        if index != len(playlist) - 1:
            index += 1
        elif (index == len(playlist) - 1) and loop:
            index = 0
        else:
            return handler_input.response_builder.response
        
        new_token = playlist[index]['token']
        url = playlist[index]['url']
        offset = 0
        title = playlist[index]['title']
        subtitle = "Episode {}".format(new_token)

        audio_directive = PlayDirective(
                            play_behavior = PlayBehavior.ENQUEUE, 
                            audio_item = AudioItem(
                                stream = Stream(
                                    token = new_token,
                                    url = url,
                                    offset_in_milliseconds = offset,
                                    expected_previous_token = old_token
                                    ),
                                metadata = AudioItemMetadata(
                                    title = title,
                                    subtitle = subtitle,
                                    art = Image(
                                        sources = [
                                            ImageInstance(
                                                url = create_presigned_url('Media/album_art.png')
                                                )
                                            ]
                                        )
                                    )
                                )
                            )
        return (
            handler_input.response_builder
                .add_directive(audio_directive)
                .response
            )

class PlaybackFinishedEventHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_request_type("AudioPlayer.PlaybackFinished")(handler_input)

    def handle(self, handler_input):
        logger.info("In PlaybackFinishedEventHandler")
        persistent_attributes = handler_input.attributes_manager.persistent_attributes
        audio_player_attributes = handler_input.request_envelope.request
        
        playlist = persistent_attributes['playlist']
        token = audio_player_attributes.token
        index = int(get_track_index(token, playlist))
        url = playlist[index]['url']
        offset = audio_player_attributes.offset_in_milliseconds
        title = playlist[index]['title']
        
        persistent_attributes["playback_session_data"].update({ 'index': index, 'token': token, 'url': url, 'offset': offset, 'title': title})
        handler_input.attributes_manager.save_persistent_attributes()

        return handler_input.response_builder.response


class PlaybackFailedEventHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_request_type("AudioPlayer.PlaybackFailed")(handler_input)
    
    def handle(self,handler_input):
        logger.info("In PlaybackFailedEventHandler")
        persistent_attributes = handler_input.attributes_manager.persistent_attributes
        audio_player_attributes = handler_input.request_envelope.request
        
        playlist = persistent_attributes['playlist']
        token = audio_player_attributes.current_playback_state.token
        index = int(get_track_index(token, playlist))
        url = playlist[index]['url']
        offset = audio_player_attributes.current_playback_state.offset_in_milliseconds
        title = playlist[index]['title']
        
        persistent_attributes["playback_session_data"].update({ 'index': index, 'token': token, 'url': url, 'offset': offset, 'title': title})
        handler_input.attributes_manager.save_persistent_attributes()

        logger.info("Playback Failed: {}".format(handler_input.request_envelope.request.error))
        return handler_input.response_builder.response

# Handler to handle exceptions from responses sent by AudioPlayer request.
class ExceptionEncounteredHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_request_type("System.ExceptionEncountered")(handler_input)

    def handle(self, handler_input):
        logger.info("System exception encountered: {}".format(handler_input.request_envelope.request))
        return handler_input.response_builder.response

class CancelOrStopIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return (is_intent_name("AMAZON.CancelIntent")(handler_input) or
                is_intent_name("AMAZON.StopIntent")(handler_input))
    
    def handle(self, handler_input):
        logger.info("In CancelOrStopIntentHandler")
        language_prompts = handler_input.attributes_manager.request_attributes["_"]
        
        speech_output = random.choice(language_prompts["CANCEL_STOP_RESPONSE"])
        
        return (
            handler_input.response_builder
                .speak(speech_output)
                .set_should_end_session(True)
                .response
            )

class HelpIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("AMAZON.HelpIntent")(handler_input)
    
    def handle(self, handler_input):
        logger.info("In HelpIntentHandler")
        language_prompts = handler_input.attributes_manager.request_attributes["_"]
        
        skill_name = language_prompts["SKILL_NAME"]
        speech_output = random.choice(language_prompts["HELP"])
        reprompt = random.choice(language_prompts["HELP_REPROMPT"])
        
        return (
            handler_input.response_builder
                .speak(speech_output)
                .ask(reprompt)
                .response
            )

# This handler handles utterances that can't be matched to any other intent handler.
class FallbackIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("AMAZON.FallbackIntent")(handler_input)
    
    def handle(self, handler_input):
        logger.info("In FallbackIntentHandler")
        language_prompts = handler_input.attributes_manager.request_attributes["_"]
        
        speech_output = random.choice(language_prompts["FALLBACK"])
        reprompt = random.choice(language_prompts["FALLBACK_REPROMPT"])
        
        return (
            handler_input.response_builder
                .speak(speech_output)
                .ask(reprompt)
                .response
            )

class SessionEndedRequestHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_request_type("SessionEndedRequest")(handler_input)
    
    def handle(self, handler_input):
        logger.info("Session ended with the reason: {}".format(handler_input.request_envelope.request.reason))
        return handler_input.response_builder.response

# Exception Handlers

# This exception handler handles syntax or routing errors. If you receive an error stating 
# the request handler is not found, you have not implemented a handler for the intent or 
# included it in the skill builder below
class CatchAllExceptionHandler(AbstractExceptionHandler):
    
    def can_handle(self, handler_input, exception):
        return True
    
    def handle(self, handler_input, exception):
        logger.error(exception, exc_info=True)
        
        language_prompts = handler_input.attributes_manager.request_attributes["_"]
        
        speech_output = language_prompts["ERROR"]
        reprompt = language_prompts["ERROR_REPROMPT"]
        
        return (
            handler_input.response_builder
                .speak(speech_output)
                .ask(reprompt)
                .response
            )

# Interceptors

# This interceptor logs each request sent from Alexa to our endpoint.
class RequestLogger(AbstractRequestInterceptor):

    def process(self, handler_input):
        logger.debug("Alexa Request: {}".format(
            handler_input.request_envelope.request))

# This interceptor logs each response our endpoint sends back to Alexa.
class ResponseLogger(AbstractResponseInterceptor):

    def process(self, handler_input, response):
        logger.debug("Alexa Response: {}".format(response))

# This interceptor is used for supporting different languages and locales. It detects the users locale,
# loads the corresponding language prompts and sends them as a request attribute object to the handler functions.
class LocalizationInterceptor(AbstractRequestInterceptor):

    def process(self, handler_input):
        locale = handler_input.request_envelope.request.locale
        #logger.info("Locale is {}".format(locale))
        
        try:
            with open("languages/"+str(locale)+".json") as language_data:
                language_prompts = json.load(language_data)
        except:
            with open("languages/"+ str(locale[:2]) +".json") as language_data:
                language_prompts = json.load(language_data)
        
        handler_input.attributes_manager.request_attributes["_"] = language_prompts

# Skill Builder
# Define a skill builder instance and add all the request handlers,
# exception handlers and interceptors to it.

sb = CustomSkillBuilder(persistence_adapter = dynamodb_adapter)
sb.add_request_handler(CheckAudioInterfaceHandler())
sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(PlayNewestEpisodeIntentHandler())
sb.add_request_handler(PlayOldestEpisodeIntentHandler())
sb.add_request_handler(ChooseEpisodeIntentHandler())
sb.add_request_handler(PauseIntentHandler())
sb.add_request_handler(ResumeIntentHandler())
sb.add_request_handler(NoIntentHandler())
sb.add_request_handler(NextIntentHandler())
sb.add_request_handler(PreviousIntentHandler())
sb.add_request_handler(RepeatIntentHandler())
sb.add_request_handler(ShuffleOnIntentHandler())
sb.add_request_handler(ShuffleOffIntentHandler())
sb.add_request_handler(LoopOnIntentHandler())
sb.add_request_handler(LoopOffIntentHandler())
sb.add_request_handler(PlaybackStartedEventHandler())
sb.add_request_handler(PlaybackStoppedEventHandler())
sb.add_request_handler(PlaybackNearlyFinishedEventHandler())
sb.add_request_handler(PlaybackFinishedEventHandler())
sb.add_request_handler(PlaybackFailedEventHandler())
sb.add_request_handler(ExceptionEncounteredHandler())
sb.add_request_handler(CancelOrStopIntentHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(FallbackIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())

sb.add_exception_handler(CatchAllExceptionHandler())

sb.add_global_request_interceptor(LocalizationInterceptor())
sb.add_global_request_interceptor(RequestLogger())
sb.add_global_response_interceptor(ResponseLogger())

lambda_handler = sb.lambda_handler()