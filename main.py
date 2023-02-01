from urllib import request, response
from bs4 import BeautifulSoup as bs
import requests, re, json

# Declare your Apple Music playlist URL 
apple_music_URL = ""

# Declare your Spotify playlist ID 
# (e.g.: in https://open.spotify.com/playlist/37i9dQZF1DX2LTcinqsO68, 37i9dQZF1DX2LTcinqsO68 is the ID) 
spotify_playlist_URL = ""

# Spotify 'Get/Search' and 'Add Items to Playlist' params
market = "US"
limit = 50
offset = 0
accessToken = '' 

# Debug params. 1 = yes. rest = no
print_unadded_songs = 0 # print list of songs that were not added to playlist
print_spotify_GET_json = 0 # print 'GET/search' JSON response for each song


'''
Find the closet song/artist match from the returned JSON of search results from Spotify. Names tend to slightly differ between platforms
and so a 1-to-1 match cannot always be made. 
For example, Apple Music may have a song as "Song X (feat. Artist Y)" while Spotify may have it simply as "Song X".
'''
def find_match(track, artist, limit, json_response):
    # Debug print
    if print_spotify_GET_json == 1:
        print("Finding", track, "from", artist)
        print(json.dumps(json_response, indent=2), "\n\n")

    # Find closest match on Spotify
    if len(json_response) != 0:
        for x in range(limit):
            track = track.lower()
            json_response[x]['name'] = json_response[x]['name'].lower()
            artist = artist.lower()
            json_response[x]['album']['artists'][0]['name'] = json_response[x]['album']['artists'][0]['name'].lower()
            if (track in json_response[x]['name']) and (artist in json_response[x]['album']['artists'][0]['name']) \
                or (json_response[x]['name'] in track) and (json_response[x]['album']['artists'][0]['name'] in artist) \
                or (json_response[x]['name'] in track) and (artist in json_response[x]['album']['artists'][0]['name']) \
                or (track in json_response[x]['name']) and (json_response[x]['album']['artists'][0]['name'] in artist):
                return x
    return -1


'''
Send "GET/search" request to Spotify and return the JSON catalogue of search results 
'''
def get_json(market, limit, offset, track, artist, accessToken):
    endpoint = 'https://api.spotify.com/v1/search?'
    query = f'{endpoint}q=remaster%2520track%3A{track}%2520artist%3A{artist}&type=track%2Cartist&market={market}&limit={limit}&offset={offset}'
    response = requests.get(query, headers={"Content-Type":"application/json", "Authorization":f"Bearer {accessToken}"})
    if response.status_code == 401:
        print("Unauthorized - The request requires user authentication or, if the request included authorization credentials,"\
            " authorization has been refused for those credentials. Ensure Access Token is valid")
        exit()
    return response


'''
Adds songs to playlist (if found) by first calling get_json and find_match to find the song on Spotify and then sending
an 'Add items to Playlist' request.  
'''
def add_to_spotify(songs, artists, unadded_songs):
    # Loop through all songs to be added
    for i in range(len(songs)):
        # Format song and artist names for Spotify API requests
        track = songs[i].replace(" ", "%20").replace("!", "%21").replace("#", "%23").replace("$", "%24").replace("&", "%26")
        artist = artists[i].replace(" ", "%20").replace("!", "%21").replace("#", "%23").replace("$", "%24").replace("&", "%26")

        # Send GET request and store response
        response = get_json(market, limit, offset, track, artist, accessToken)

        try:
            json_response = response.json()['tracks']['items'] # trim request for relevant data
        except:
            if print_unadded_songs == 1:
                unadded_songs.append(songs[i])
            continue
        
        # Find matching track from returned results
        matched_index = find_match(songs[i], artists[i], limit, json_response)

        # Failed to find song on Spotify. Print name if required
        if matched_index == -1:
            unadded_songs.append(songs[i])
        elif  print_unadded_songs == 1:
            unadded_songs.append(songs[i])
            continue
        # Found song on Spotify. Add to playlist
        else:
            uri = json_response[matched_index]['uri'].split(":")[2]
            endpoint = f"https://api.spotify.com/v1/playlists/{spotify_playlist_URL}/tracks?uris=spotify%3Atrack%3A{uri}"
            response = requests.post(url = endpoint, headers={"Content-Type":"application/json", 
                                    "Authorization":f"Bearer {accessToken}"})


'''
Scrape and return song/artist names from Apple Music playlist on web
'''
def get_songs_and_artists(page):
    soup = bs(page.content, "html.parser")
    # Grab all tags containing the song names
    song_tags = soup.find_all('div', 'songs-list-row__song-name svelte-1yo4jst')
    # Grab all tags containing the artist names
    artist_tags = soup.find_all('span', 'svelte-1yo4jst')
    # Lists to hold song/artist names alone
    songList = list()
    artistList = list()

    # Simplify song name
    for s in song_tags:
        song = s.text
        song = re.sub(' \(feat. .*?\)', '', song)
        songList.append(song)
    
    # Simplify artist name
    for a in artist_tags:
        artist = a.text.replace("\n", "")
        artist = re.sub(' +', ' ', artist)
        if artist != None:
            artistList.append(artist)

    return songList, artistList


def main():
    # Get Apple Music playlist 
    page = requests.get(apple_music_URL)

    # Check if GET request successful. Else exit
    if page.status_code != 200:
        print("Apple Music URL GET request unsuccessful.\nStatus:", page.status_code)
        exit()
    
    # Scrape tracks and corresponding artists from playlist
    song_list, artist_list = get_songs_and_artists(page)

    # List to store unadded music. Used if var print_unadded_songs = 1
    unadded_songs = list()
    # Add songs to Spotify playlist
    add_to_spotify(song_list, artist_list, unadded_songs)
    
    if print_unadded_songs == 1:
        print("Tracks not added:")
        for s in unadded_songs:
            print(s)
        print(len(song_list) - len(unadded_songs), "/", len(song_list), "tracks were added")


if __name__ == "__main__":
    main()