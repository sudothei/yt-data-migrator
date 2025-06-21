from models import db, connect_db, User, Subscription, LikedVideo, Playlist, PlaylistVideo, Credential
import os
import google.oauth2.credentials
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
import google.auth
import oauthlib
import requests
import datetime

api_service_name = "youtube"
api_version = "v3"

# Get secrets from environment
GOOGLE_CLIENT_SECRET = os.environ['GOOGLE_CLIENT_SECRET']

# Google project config
GOOGLE_CLIENT_ID = '672430455080-viiuujtpq0r09u0fe798kqp0i7oi2a00.apps.googleusercontent.com'
GOOGLE_PROJECT_ID = 'youtube-data-migrator'
GOOGLE_REDIRECT_URIS = ["https://yt-data-migrator.herokuapp.com"]
GOOGLE_JAVASCRIPT_ORIGINS = ["https://yt-data-migrator.herokuapp.com"]

# Client configuration for an OAuth 2.0 web server application
# (cf. https://developers.google.com/identity/protocols/OAuth2WebServer)
CLIENT_CONFIG = {'web': {
    'client_id': GOOGLE_CLIENT_ID,
    'project_id': GOOGLE_PROJECT_ID,
    'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
    'token_uri': 'https://www.googleapis.com/oauth2/v3/token',
    'auth_provider_x509_cert_url': 'https://www.googleapis.com/oauth2/v1/certs',
    'client_secret': GOOGLE_CLIENT_SECRET,
    'redirect_uris': GOOGLE_REDIRECT_URIS,
    'javascript_origins': GOOGLE_JAVASCRIPT_ORIGINS}}

# This scope will allow the application to manage your calendars
SCOPES = ["openid",
        "https://www.googleapis.com/auth/youtube.readonly",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
        "https://www.googleapis.com/auth/youtube"]


def make_expiration_date():
    """
    Returns timestamp used for pruning database
    """

    expiration = datetime.datetime.utcnow() + datetime.timedelta(days=14)
    return expiration.timestamp()

def get_credentials(user_id):
    """
    Returns credentials object formatted for Google API requests
    """

    token = Credential.query.filter_by(user_id=user_id).first_or_404()
    credentials = google.oauth2.credentials.Credentials(
            token = token.token,
            refresh_token = token.refresh_token,
            token_uri = CLIENT_CONFIG['web']['token_uri'],
            client_id = GOOGLE_CLIENT_ID,
            client_secret = GOOGLE_CLIENT_SECRET,
            scopes = SCOPES
            )

    return credentials


def get_authorization_url():
    """
    Makes OAuth 2.0 flow url for user to authorize consent
    """

    # Use the information in the client_secret.json to identify
    # the application requesting authorization.
    flow = google_auth_oauthlib.flow.Flow.from_client_config(
            client_config=CLIENT_CONFIG,
            scopes=SCOPES)

    # Indicate where the API server will redirect the user after the user completes
    # the authorization flow. The redirect URI is required.
    flow.redirect_uri = 'https://yt-data-migrator.herokuapp.com/auth/google/callback'

    # Generate URL for request to Google's OAuth 2.0 server.
    # Use kwargs to set optional request parameters.
    authorization_url, state = flow.authorization_url(
            # Enable offline access so that you can refresh an access token without
            # re-prompting the user for permission. Recommended for web server apps.
            access_type='offline',
            # Enable incremental authorization. Recommended as a best practice.
            include_granted_scopes='true')

    return authorization_url, state

def get_playlists(user, page=None):
    """
    Authenticated API request to get user's playlists
    """

    # Get credentials
    credentials = get_credentials(user.id)

    # Build the service object
    youtube = googleapiclient.discovery.build(
            api_service_name, api_version, credentials=credentials, cache_discovery=False)

    # Request parameters
    request = youtube.playlists().list(
            part="snippet, status",
            maxResults=50,
            mine=True,
            pageToken=page
            )

    # Recursive requests append to original response object until no data left
    response = request.execute()
    if 'nextPageToken' in response:
        pageToken = response['nextPageToken']
        newResponse = get_playlists(user, pageToken)
        response['items'].extend(newResponse['items'])

    return response

def get_playlist_items(user, playlist_id, page=None):
    """
    Authenticated API request to get contents of single playlist
    """

    # Get credentials
    credentials = get_credentials(user.id)

    # Build the service object
    youtube = googleapiclient.discovery.build(
            api_service_name, api_version, credentials=credentials, cache_discovery=False)

    # Request parameters
    request = youtube.playlistItems().list(
            part="snippet",
            playlistId=playlist_id,
            maxResults=50,
            pageToken=page
            )

    # Recursive requests append to original response object until no data left
    response = request.execute()
    if 'nextPageToken' in response:
        pageToken = response['nextPageToken']
        newResponse = get_playlist_items(user, playlist_id, pageToken)
        response['items'].extend(newResponse['items'])

    return response

def save_playlists(playlists, user):
    """
    Saves playlist data from YouTube API response to database
    """

    for playlist in playlists['items']:
        newPlaylist = Playlist(
                user_id = user.id,
                resource_id = playlist['id'],
                title = playlist['snippet']['title'],
                thumbnail = playlist['snippet']['thumbnails']['default']['url'],
                privacy_status = playlist['status']['privacyStatus'],
                expiration_date = make_expiration_date()
                )
        db.session.add(newPlaylist)
    db.session.commit()

    return

def save_playlist_items(playlist_items, dbPlaylistId):
    """
    Saves playlist items data from YouTube API response to database
    """
    for video in playlist_items['items']:
        newVid = PlaylistVideo(
                playlist_id = dbPlaylistId,
                video_id = video['snippet']['resourceId']['videoId']
                )
        db.session.add(newVid)
    db.session.commit()

    return

def import_playlists(user):
    """
    Gets and saves playlists and playlist items
    """

    # Gets playlists from API
    playlists = get_playlists(user)

    # Saves playlists to database
    save_playlists(playlists, user)

    # Iterates over playlist object to save playlist items to appropriate playlist in database
    for playlist in playlists['items']:

        # Get matching playlist in database
        playlist_id = playlist['id']
        dbPlaylist = Playlist.query.filter_by(resource_id=playlist_id).first_or_404()

        # Gets playlist items from API
        playlist_items = get_playlist_items(user, playlist_id)

        # Saves playlist items to database
        save_playlist_items(playlist_items, dbPlaylist.id)

    return

def get_liked_videos(user, page=None):
    """
    Authenticated API request to get user's liked videos
    """

    # Get credentials
    credentials = get_credentials(user.id)

    # Build the service object
    youtube = googleapiclient.discovery.build(
            api_service_name, api_version, credentials=credentials, cache_discovery=False)

    # Request parameters
    request = youtube.videos().list(
            part="snippet",
            myRating="like",
            maxResults=50,
            pageToken=page
            )

    # Recursive requests append to original response object until no data left
    response = request.execute()
    if 'nextPageToken' in response:
        pageToken = response['nextPageToken']
        newResponse = get_liked_videos(user, pageToken)
        response['items'].extend(newResponse['items'])

    return response

def save_liked_videos(liked_videos, user):
    """
    Saves liked videos data from YouTube API response to database
    """

    for video in liked_videos['items']:
        newVid = LikedVideo(
                user_id = user.id,
                video_id = video['id'],
                title = video['snippet']['title'],
                channel_title = video['snippet']['channelTitle'],
                thumbnail = video['snippet']['thumbnails']['default']['url'],
                expiration_date = make_expiration_date()
                )
        db.session.add(newVid)
    db.session.commit()

    return

def import_liked_videos(user):
    """
    Combines functions to get liked videos from API and save to database
    """

    likes = get_liked_videos(user)
    save_liked_videos(likes, user)

    return

def get_subscriptions(user, page=None):
    """
    Authenticated API request to get user's subscriptions
    """

    # Get credentials
    credentials = get_credentials(user.id)

    # Build the service object
    youtube = googleapiclient.discovery.build(
            api_service_name, api_version, credentials=credentials, cache_discovery=False)

    # Request parameters
    request = youtube.subscriptions().list(
            part="snippet",
            mine=True,
            maxResults=50,
            order='alphabetical',
            pageToken=page
            )

    # Recursive requests append to original response object until no data left
    response = request.execute()
    if 'nextPageToken' in response:
        pageToken = response['nextPageToken']
        newResponse = get_subscriptions(user, pageToken)
        response['items'].extend(newResponse['items'])

    return response

def save_subscriptions(subscriptions, user):
    """
    Saves subscriptions data from YouTube API response to database
    """

    for sub in subscriptions['items']:
        newSub = Subscription(
                user_id = user.id,
                channel_id = sub['snippet']['resourceId']['channelId'],
                title = sub['snippet']['title'],
                thumbnail = sub['snippet']['thumbnails']['default']['url'],
                expiration_date = make_expiration_date()
                )
        db.session.add(newSub)
    db.session.commit()

    return

def import_subscriptions(user):
    """
    Combines functions to get subscriptions from API and save to database
    """

    subs = get_subscriptions(user)
    save_subscriptions(subs, user)

    return


def get_access_token(code, state):
    """
    OAuth API reqest to exchange access code for access token
    """

    # Build service object
    flow = google_auth_oauthlib.flow.Flow.from_client_config(
            client_config=CLIENT_CONFIG,
            scopes=SCOPES,
            state=state)
    flow.redirect_uri = 'https://yt-data-migrator.herokuapp.com/auth/google/callback'

    # Make request
    flow.fetch_token(code=code)

    # Credentials are saved to service object
    return flow.credentials

def save_credentials(response, user):
    """
    Saves credentials to database for user
    """

    # Overwrite credentials if already exist
    try:
        creds = Credential.query.filter_by(user_id=user.id).first_or_404()
        creds.token = response.token
        creds.refresh_token = response.refresh_token

    # Save credentials to database
    except:
        newCreds = Credential(
                user_id = user.id,
                token = response.token,
                refresh_token = response.refresh_token
                )
        db.session.add(newCreds)
    db.session.commit()

    return

def export_subscription(channel, user):
    """
    Authenticated API request to subscribe to a channel
    """

    # Get credentials
    credentials = get_credentials(user.id)

    # Build the service object
    youtube = googleapiclient.discovery.build(
            api_service_name, api_version, credentials=credentials, cache_discovery=False)

    # Request parameters
    request = youtube.subscriptions().insert(
            part="snippet",
            body={
                "snippet": {
                    "resourceId": {
                        "kind": "youtube#channel",
                        "channelId": channel.channel_id
                        }
                    }
                }
            )
    request.execute()
     
    return

def export_rating(video, user):
    """
    Authenticated API request to upvote a single video
    """

    # Get credentials
    credentials = get_credentials(user.id)

    # Build the service object
    youtube = googleapiclient.discovery.build(
            api_service_name, api_version, credentials=credentials, cache_discovery=False)

    # Request parameters
    request = youtube.videos().rate(
            id=video.video_id,
            rating="like"
            )
    request.execute()

    return

def export_playlist(playlist, user):
    """
    Authenticated API request to create a single playlist
    """

    # Get credentials
    credentials = get_credentials(user.id)

    # Build the service object
    youtube = googleapiclient.discovery.build(
            api_service_name, api_version, credentials=credentials, cache_discovery=False)

    # Request parameters
    request = youtube.playlists().insert(
            part="snippet, status",
            body={
                "snippet": {
                    "title": playlist.title
                    },
                "status": {
                    "privacyStatus": playlist.privacy_status
                    }
                }
            )
    response = request.execute()

    return response

def export_playlist_vid(videoId, playlistId, user):
    """
    Authenticated API request to add a single video to a playlist
    """
    # Get credentials
    credentials = get_credentials(user.id)

    # Build the service object
    youtube = googleapiclient.discovery.build(
            api_service_name, api_version, credentials=credentials, cache_discovery=False)

    # Request parameters
    request = youtube.playlistItems().insert(
            part="snippet",
            body={
                "snippet": {
                    "playlistId": playlistId,
                    "resourceId": {
                        "kind" : "youtube#video",
                        "videoId": videoId
                        }
                    }
                }
            )
    request.execute()

    return
