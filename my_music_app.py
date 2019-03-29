from flask import Flask, render_template, request, redirect, url_for, session
import requests
import urllib
import json
# import random
from requests.auth import HTTPBasicAuth
import os
import sys
import time

from pprint import pprint

app = Flask("moodmusic")
app.secret_key = b'_5#y2L"F4J8z\n\xec]/'

#SONGKICK_API_KEY = os.getenv('SONGKICK_API_KEY')

# Port and Hostname that are used to launch App in heroku
PORT = int(os.getenv("PORT", 5000))
HOSTNAME = os.getenv("HEROKU_HOSTNAME", "http://localhost:{}".format(PORT))

# Spotify App data
CLIENT_ID = os.getenv("client_id", None)
CLIENT_SECRET = os.getenv("client_secret", None)

# Redirect URI for Spotify API
REDIRECT_URI = "https://frozen-fjord-48065.herokuapp.com/callback"


# Requeest a token without asking user to log in
def call_api_token():
    endpoint = "https://accounts.spotify.com/api/token"
    make_request = requests.post(endpoint,
                                 data={"grant_type": "client_credentials",
                                   "client_id": CLIENT_ID,
                                       "client_secret": CLIENT_SECRET})
    return make_request


# Get a token without asking user to log in
def final():
    spo_response = call_api_token()
    # Check response from Spotify API
    # Something went wrong. Ask user to try again
    if spo_response.status_code != 200:
        return redirect(url_for('index'))
    return spo_response.json()


# Class that stores token not related to user
class TokenStorage:
    def __init__(self):
        self.token = None
        self.expire_in = None
        self.start = None

    # Check if token has exired
    def expire(self, time_now):
        if (time_now - self.start) > self.expire_in:
            return True
        return False

    # Get token first time or if expired
    def get_token(self, time_now):
        if self.token is None or self.expire(time_now):
            access_data = final()
            self.token = access_data['access_token']
            self.expire_in = access_data['expires_in']
            self.start = time.time()
        # print self.token
        return self.token


# Token to access to Spotify data that do not need access to user related data
# It is stored as class TokenStorage object
# To get token - TOKEN.get_token(time_now)
TOKEN = TokenStorage()


def request_user_data_token(code):
    """
    Function that requests refresh and access tokens from Spotify API.
    This token allows to change and request user related data.
    Step 4 in Guide
    """
    endpoint = "https://accounts.spotify.com/api/token"
    payload = {
              "grant_type": 'authorization_code',
              "code": code,
              "redirect_uri": REDIRECT_URI,
            }
    # Get refresh and access tokens
    response_data = requests.post(endpoint,
                                  auth=HTTPBasicAuth(CLIENT_ID, CLIENT_SECRET),
                                  data=payload)

    # print "RESPONSE", response_data
    # Check response from Spotify API
    # Something went wrong. Ask user to try to login again
    if response_data.status_code != 200:
        print("From spotify: {}".format(response_data))
        return redirect(url_for('index'))

    # Success. Convert response data in json
    # data = response_data.json()
    # access_data = {
    #     'access_token': data["access_token"],
    #     'refresh_token': data["refresh_token"],
    #     'token_type': data["token_type"],
    #     'expires_in': data["expires_in"],
    # }
    return response_data.json()


# Function that checks if it is Python3 version
def python_version_3():
    if sys.version_info[0] == 3:
        return True
    return False


# Create params_query_string
def params_query_string(payload):
    # Python2 version
    url_arg = urllib.urlencode(payload)
    # Python3 version
    if python_version_3():
        url_arg = urllib.parse.urlencode(payload)
    return url_arg


# Function that replace special characters in val string using the %xx escape
def quote_params_val(val):
    # Python2 version
    value = urllib.quote(val)
    # Python3 version
    if python_version_3():
        value = urllib.parse.quote(val)
    return value


def searh_request(token, payload):
    '''
    Search request to Spotify API.
    Can be used both types of tokens.
    Payload specifies what you would like to search (in particular: album,
    playlist, playlist, or track)
    '''
    # Endpoint to search
    endpoint = 'https://api.spotify.com/v1/search'
    # Use the access token to access Spotify API
    authorization_header = {"Authorization": "Bearer {}".format(token)}
    # Prepare URL for search request
    url_arg = "&".join(["{}={}".format(key, quote_params_val(val))
                       for key, val in payload.items()])
    # url_arg = params_query_string(payload)
    auth_url = endpoint + "/?" + url_arg
    # Get request to Spotify API to search
    search_response = requests.get(auth_url, headers=authorization_header)
    # Return the response in json format
    return search_response.json()


def search_playlist(token, playlist):
    '''
    Function that searches the playlist
    Input: token and playlist name
    Returns: array of arist objects in json format
    '''
    # Specify that we want to search the playlist
    payload = {
              "q": playlist,
              "type": "playlist",
            }
    # Return array of arist objects in json format
    return searh_request(token, payload)




def get_playlist_tracks(token, playlistID):
    '''
    Function that gets playlist's Top Tracks
    Input: playlist ID, token
    Returns: dict where key is a name of the track and value - uri of the track
    '''
    # Endpoint to search
    endpoint = 'https://api.spotify.com/v1/playlists/' + playlistID + '/tracks'
    # Use the access token to access Spotify API
    authorization_header = {"Authorization": "Bearer {}".format(token)}
    payload = {"fields": "total,limit"}
    # Creating request URL
    url_arg = params_query_string(payload)
    auth_url = endpoint + "/?" + url_arg
    # Request Spotify API to get Top tracks
    tracks = requests.get(auth_url, headers=authorization_header)
    # Check if Spotify have Top Track for this playlist

    return tracks.json()


def get_playlist(playlistID, token):
    '''
    Request Spotify API for playlist data using playlist ID
    '''
    # Endpint to get playlist related form_data
    endpoint = 'https://api.spotify.com/v1/playlists/' + playlistID + '/tracks'
    # Authorization header
    authorization_header = {"Authorization": "Bearer {}".format(token)}
    # Request Spotify API playlist related data
    playlist_data = requests.get(endpoint, headers=authorization_header)
    # Returns playlist_data in json format
    return playlist_data.json()


def get_current_user_profile(user_data_token):
    '''
    Function that Get Current User's Profile
    Input: user data related token
    Returns: user ID
    '''
    # Endpint to get current user profile
    endpoint = "https://api.spotify.com/v1/me"
    # Authorization header
    authorization_header = {"Authorization": "Bearer {}".format(user_data_token)}
    # Request Spotify API playlist related data
    user_data = requests.get(endpoint, headers=authorization_header)
    # Returns user_data in json format
    return user_data.json()

def create_empty_playlist(userID, playlist_name, user_data_token):
    '''
    Function that creates an empty playlist for user with userID
    Input: user ID
    Returns: ID of the newly created playlist
    '''
    # Endpint to get current user profile
    endpoint = "https://api.spotify.com/v1/users/" + userID + "/playlists"
    # Authorization header
    authorization_header = {"Authorization": "Bearer {}".format(user_data_token)}
    # Specify params of new playlist
    payload = {"name": playlist_name}
    playlist_data = requests.post(endpoint,
                                  headers=authorization_header,
                                  json=payload)
    # print "URL", playlist_data.url
    # print "RESPONSE FOR NEW PLAYLIST", playlist_data.json()
    return playlist_data.json()


def add_tracks_to_playlist(userID, playlistID, uris, user_data_token):
    '''
    Add Tracks to a Playlist
    Input:
    - user ID and user's playlist ID where you want to add Tracks
    - uris - list of Spotify URIs for tracks
    Returns
    For example: True or False
    True - tracks were added to playlist
    False - in case of error
    '''
    # Endpint to get current user profile
    endpoint = "https://api.spotify.com/v1/users/" + userID + "/playlists/" + playlistID + "/tracks"
    # Authorization header
    authorization_header = {"Authorization": "Bearer {}".format(user_data_token)}
    # Specify params of new playlist
    payload = {"uris": uris}
    playlist_with_tracks = requests.post(endpoint,
                                         headers=authorization_header,
                                         json=payload)

    return playlist_with_tracks


@app.route("/")
def index():
    '''
    Ask user:
    1) playlist to search, see playlist's top tracks, listen 30 sec preview,
    add playlist's top tracks to user's Spotify account new playlist
    2) Search city for upcoming gigs.
    '''
    if "tracks_uri" in session:
        session.pop('tracks_uri', None)
    if "playlist_name" in session:
        session.pop("playlist_name", None)
    return render_template("index.html")


@app.route("/login")
def requestAuth():
    """
    Application requests authorization from Spotify.
    Step 1 in Guide
    """
    endpoint = "https://accounts.spotify.com/authorize"
    payload = {
              "client_id": CLIENT_ID,
              "response_type": "code",
              "redirect_uri": "https://frozen-fjord-48065.herokuapp.com/callback",
              # "state": "sdfdskjfhkdshfkj",
              "scope": "playlist-modify-public user-read-private",
              # "show_dialog": True
            }

    # Create query string from params
    # url_arg = "&".join(["{}={}".format(key, quote_params_val(val)) for
    #                    key, val in params.items()])
    url_arg = params_query_string(payload)

    # Request URL
    auth_url = endpoint + "/?" + url_arg
    #print "AUTH_URL", auth_url
    # User is redirected to Spotify where user is asked to authorize access to
    # his/her account within the scopes
    return redirect(auth_url)


@app.route("/callback")
def callback():
    """
    After the user accepts (or denies) request to Log in his Spotify account,
    the Spotify Accounts service redirects back to the REDIRECT_URI.
    Step 3 in Guide.
    """
    # Check if the user has not accepted the request or an error has occurred
    if "error" in request.args:
        return redirect(url_for('index'))

    # On success response query string contains parameter "code".
    # Code is used to receive access data from Spotify
    code = request.args['code']
    # print "CODE", code
    # request_token function returns dict of access values
    access_data = request_user_data_token(code)
    # print "TOKEN", access_data["access_token"]
    # Session allows to store information specific to a user from one request
    # to the next one
    session['access_data'] = access_data
    # After the access_data was received our App can use Spotify API
    return redirect(url_for('create_playlist'))


@app.route("/search_playlist", methods=["POST"])
def playlists_search():
    """
    This decorator searches the playlist by name
    Returns:
    1) Template with found playlists that match user input
    2) Template that asks to repeat playlist search in case of
    previous unsuccessful attempt.
    """
    # Check if user is logged in
    #if "access_data" not in session:
    #     return redirect(url_for('index'))
    # User is logged in
    # # Get access token from user's request
    # token = session['access_data']['access_token']

    # Not related to user token is stored as class TokenStorage object
    token = TOKEN.get_token(time.time())

    # Get data that user post to app on index page
    form_data = request.form
    playlist = form_data["playlist"]

    # Get data in json format from search_playlist request
    found_playlists = search_playlist(token, playlist)

    # Check if there is playlist match at Spotify
    if not found_playlists['playlists']['items']:
        return render_template("ask_playlist.html", playlist=playlist.title())

    # Create dict of found playlists
    playlist_dict = dict()
    for playlist in found_playlists['playlists']['items']:
        playlist_dict[playlist["name"]] = str(playlist["id"])

    return render_template("req_to_show_tracks.html", playlist_dict=playlist_dict)


@app.route("/show_tracks", methods=["POST"])
def show_tracks():
    '''
    This decorator does next:
    1) Gets an playlist's Top Tracks using playlist ID
    2) Displays playlist name, image, playlist's Top Tracks and
    asks user to create playlist
    Returns: Template shows playlist's Top Tracks and asks user
             to create playlist
    '''
    # # Check if user is logged in
    if "access_data" not in session:
         print "No access data"
         return redirect(url_for('index'))
    # User is logged in
    # Get access token from user's request
    token = session['access_data']['access_token']

    # Not related to user token is stored as class TokenStorage object
    token = TOKEN.get_token(time.time())

    # Get playlist ID from the request form
    playlistID = str(request.args.get("playlist"))
    form_data = request.form
    playlistID = form_data["playlist"]
    # Get playlist data in json format
    playlist_data = get_playlist(playlistID, token)
    # playlist name
    #playlist_name = playlist_data["id"]
    # playlist picture
    #playlist_pic = playlist_data["images"]
    # Get playlist top tracks
    results = get_playlist_tracks(token, playlistID)
    # print top_tracks
    # Initiate dictionary to story only needed data
    #tracks_dict = {}
    #tracks_uri = []
    # Storing in dict name, uri and preview_url of top tracks
    #for item in playlists['items']:
        #id = item['uri']
        #print id
    #results = playlist_tracks(token, playlistID)
    tracks = results['playlists']['items'][0]['tracks']
    print (items)
    #for track in top_tracks["tracks"]:
    tracks_dict[track["name"]] = {"preview_url": track["preview_url"]}
    tracks_uri.append(track["uri"])
    # Session allows to store information specific to a user from one request
    # to the next one
    session['playlist_name'] = playlist_name
    session['tracks_uri'] = tracks_uri
    return render_template("req_to_create_playlist.html",
                            tracks_dict=tracks_dict,
                            name=playlist_name.title(),
                            picture=playlist_pic)




@app.route("/create_playlist")
def create_playlist():
    '''
    What to do:
    1) Get Current User's Profile:
    https://beta.developer.spotify.com/documentation/web-api/reference/users-profile/get-current-users-profile/
    2) Take from User's Profile "user ID":
    3) Create empty playlist using user ID:
    https://beta.developer.spotify.com/documentation/web-api/reference/playlists/create-playlist/
    4) Add playlist's Top Tracks to a Playlist:
    https://beta.developer.spotify.com/documentation/web-api/reference/playlists/add-tracks-to-playlist/

    Returns: template
    Template saies that playlist is successfully created and there is a link
    to Index page
    '''

    # Check if user is logged in
    if "access_data" not in session:
        return redirect(url_for('index'))
    # User is logged in
    # Get access token from user's request
    token = session['access_data']['access_token']
    # print "TOKEN", token
    if "tracks_uri" not in session:
        return redirect(url_for('index'))

    tracks_uri = session['tracks_uri']
    playlist_name = session['playlist_name']
    session.pop('tracks_uri', None)
    session.pop('playlist_name', None)
    # print "TRACKS_URI", tracks_uri
    # Get user ID from Current User's Profile
    userID = get_current_user_profile(token)["id"]
    # print "USER ID", userID
    # Create empty playlist using user ID
    playlistID = create_empty_playlist(userID, playlist_name, token)["id"]
    # playlistID = None
    # Add playlist's Top Tracks to a Playlist
    response = add_traks_to_playlist(userID, playlistID, tracks_uri, token)
    return render_template("playlist_creation.html", res=response)
    # if response.status_code != 201:
    #     return 'Sorry. An error accured. Playlist was not created'
    # return 'Playlist successfully created'



def get_sample_track(playlist_id):
    '''
    Function that uses playlist_id to get the first track from playlist's top-tracks
    Input: playlist ID
    Returns: preview URL of the first track from playlist's top-tracks
    '''
    # Not related to user token is stored as class TokenStorage object
    token = TOKEN.get_token(time.time())
    headers = {
                'Authorization': 'Bearer ' + token}
    response = requests.get('https://api.spotify.com/v1/playlists/' + playlist_id
                            + '/top-tracks?country=SE', headers=headers)
    return response.json()['tracks'][0]['preview_url']

app.run(host='0.0.0.0', port=PORT, debug=True)
