import spotipy
from spotipy.oauth2 import SpotifyOAuth

import streamlit as st
from groq import Groq

import json

from dotenv import load_dotenv

load_dotenv()

import os
import requests

################################################################################################################################################################
# - potential features
#   - allow users to type in how they are like feeling (eg. im feeling pretty down can you make me a playlist to lift me up)
#
################################################################################################################################################################

# login to spotify
def login_to_spotify():
    # Set up SpotifyOAuth
    sp_auth = SpotifyOAuth(
        client_id=os.environ['SPOTIFY_CLIENT_ID'],
        client_secret=os.environ['SPOTIFY_CLIENT_SECRET'],
        redirect_uri='http://localhost:8502/',
        scope='playlist-modify-private',
    )
    return sp_auth

# Main function
def main():

    auth_code = login_to_spotify()
    if not auth_code:
        return
    
    spotify_client = spotipy.Spotify(auth_manager=auth_code)
    user = spotify_client.current_user()
    print(f"Logged in as: {user['display_name']} ({user['id']})")

    with st.form("Playlist generation"):
        prompt = st.text_input("Describe the music you'd like to hear..")
        song_count = st.slider("Songs", 1, 5, 10)
        submitted = st.form_submit_button("Generate Playlist")

    if not submitted:
        return
    
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    with st.spinner("Creating playlist.."):
        response = client.chat.completions.create(
            model = "llama-3.3-70b-versatile",
            messages=[
                {
                    'role': "system",
                    'content': "You are MusicGPT, the world's best music recommendation AI. When given a description of a user's music preference, you will recommend songs tailored to the user's preference."
                },
                {
                    'role': "user",
                    'content': f"Create a playlist with {song_count} songs that fit the following description: '''{prompt}'''. Come up with a create and unique name for the playlist."
                }
            ],
            functions=[
                {
                    'name': "create_playlist",
                    'description': "Creates a spotify playlist based on a list of songs that should be added to the list.",
                    'parameters' : {
                        'type': "object",
                        'properties': {
                            'playlist_name': {
                                'type': "string",
                                'description': "Name of playlist"
                            },
                            'playlist_description': {
                                'type': "string",
                                'description': "Description for the playlist.",
                            },
                            'songs': {
                                'type': "array",
                                'items': {
                                    'type': "object",
                                    'properties': {
                                        'song_name': {
                                            'type': "string",
                                            'description': "Name of the song that should be added to the playlist.",
                                        },
                                        'artists': {
                                            'type': "array",
                                            'description': "List of all artists",
                                            'items': {
                                                'type': "string",
                                                'description': "Name of the artist of the song"
                                            },
                                        },
                                    },
                                    'required': ['song_name', 'artists'],
                                },
                            },
                        },
                        'required': ['songs', 'playlist_name', 'playlist_description'],
                    },
                }
            ],
        )

        # Access the first choice in the response
        choice = response.choices[0].message.tool_calls[0]
        arguments = choice.function.arguments

        args = json.loads(arguments)

        st.write("### Playlist Details")
        st.write(f"**Playlist Name:** {args['playlist_name']}")
        st.write(f"**Playlist Description:** {args['playlist_description']}")

        # Display songs in a formatted way
        st.write("### Songs:")
        for idx, song in enumerate(args['songs'], start=1):
            st.write(f"{idx}. **{song['song_name']}** by {', '.join(song['artists'])}")

        song_uris = [
            spotify_client.search(
                q=f"{song['song_name']} {','.join(song['artists'])}", limit=1
            )["tracks"]["items"][0]["uri"]
            for song in args['songs']
        ]

        user_id = spotify_client.me()["id"]
        playlist = spotify_client.user_playlist_create(
            user_id, args['playlist_name'], False, description=args['playlist_description']
        )
        playlist_id = playlist["id"]
        spotify_client.playlist_add_items(playlist_id, song_uris)

        st.write(
            f"Playlist created <a href='{playlist['external_urls']['spotify']}'>Click</a>",
            unsafe_allow_html=True,
        )


if __name__ == "__main__":
    main()