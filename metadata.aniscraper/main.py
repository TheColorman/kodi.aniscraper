# Copyright (C) 2023, Alexander Thoren aka Colorman <thoren.alex@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# TODO: Rate limits
# TODO: File not found errors
# TODO: Handle 404s

import sys, os
import urllib.parse
import xml.etree.ElementTree as ET
import requests

import xbmcgui
import xbmcplugin, xbmcaddon
import xbmc, xbmcvfs

import anitopy
import web_pdb

try:
    import cPickle as pickle
except ImportError:
    import pickle


def get_params():
    param_string = sys.argv[2][1:]
    if param_string:
        return dict(urllib.parse.parse_qsl(param_string))
    return {}

__addon__   = xbmcaddon.Addon()
__addonname__ = __addon__.getAddonInfo('name')
__profile__ = xbmcvfs.translatePath(__addon__.getAddonInfo("profile"))
__picklejar__ = os.path.join(__profile__, 'db.bin')

params = get_params()
plugin_handle = int(sys.argv[1])
action = params.get('action')

def log(text):
    # Convert text to plain ascii, otherwise kodi will raise an exception
    xbmc.log(u"[{0}] {1}".format(__addonname__, text.encode('ascii', 'replace')), level=xbmc.LOGDEBUG)

class Main:
    def __init__(self):
        # Properties
        try:
            self.initjar()
        except Exception as e:
            log("Exception thrown initializing the picklejar: " + str(e))
    
    def resetjar(self):
        """Reset the database"""
        self._db = {}
        self.updatejar()

    def initjar(self):
        """Load the database from the picklejar"""
        try:
            if not xbmcvfs.exists(__profile__):
                log("Profile folder does not exist, creating it")
                xbmcvfs.mkdir(__profile__)

            if not xbmcvfs.exists(__picklejar__):
                log("Picklejar does not exist, creating empty jar")
                pickle.dump({}, open(__picklejar__, 'wb'), pickle.HIGHEST_PROTOCOL)

            fs = open(__picklejar__, 'rb')
            self._db = pickle.load(fs)
            fs.close()
            return True
        except Exception as e:
            log("Exception thrown initializing the picklejar: " + str(e))
            return False
    
    def validate_db(self):
        """Creates any db missing properties"""
        self._db.setdefault('anime', {
            'titles': {},
            'ids': {}
        })
        self._db.setdefault('sourcepath', None)
        self.updatejar()

    def updatejar(self):
        """Save the database to the picklejar"""
        try:
            fs = open(__picklejar__, 'wb')
            pickle.dump(self._db, fs, pickle.HIGHEST_PROTOCOL)
            fs.close()
            return True
        except Exception as e:
            log("Exception thrown updating the jar: " + str(e))
    
    def sourcepath(self, folder_name):
        """Return the path to the kodi video source"""
        log("Searching for source that includes " + folder_name)
        if self._db.get('sourcepath'):
            log("Sourcepath: " + self._db['sourcepath'])
            return self._db['sourcepath']
        else:
            # Crawl the sources.xml file to find the path
            log("Crawling sources.xml")
            fs = open(xbmcvfs.translatePath("special://userdata/sources.xml"), 'r')
            xml = fs.read()
            fs.close()
            root = ET.fromstring(xml)
            # Go through each source to try to find the media folder
            for source in root.find('video').findall('source'):
                name = source.find('name').text
                path = source.find('path').text
                for folder in xbmcvfs.listdir(path)[0]:
                    if folder == folder_name:
                        self._db['sourcepath'] = path
                        self.updatejar()
                        return path

            raise Exception(f"No folder with name \"{folder_name}\" found in any of the video sources in sources.xml")
    
    def scan_anime(self, folder_path: str) -> str:
        """Scan a folder for anime. Returns a dictionary with keyr = anime titles and values = list of absolute paths to episode files"""
        def parse_anime(filename: str) -> str:
            parsed = anitopy.parse(filename)
            log("Parsed " + filename + " to " + str(parsed))
            return parsed['anime_title']

        anidict = {}
        def add_files(folder: str, files: list):
            for file in files:
                if file.endswith('.mkv') or file.endswith('.mp4'):
                    anime_title = parse_anime(file)
                    anidict.setdefault(anime_title, [])
                    anidict[anime_title].append(os.path.join(folder, file))

        def scan(folder: str) -> dict:
            dirs, files = xbmcvfs.listdir(folder)

            add_files(folder, files)
            for dir in dirs:
                log("Recursing into " + dir)
                scan(os.path.join(folder, dir))
            
        scan(folder_path)
        return anidict
    
    def sort_most_common_key(self, d: dict) -> str:
        """Return the dict sorted by key with the longest list"""
        return sorted(d.items(), key=lambda x: len(x[1]), reverse=True)

    def _AL_qeury(self, query: str, variables: dict):
        """Query the AniList API"""
        url = 'https://graphql.anilist.co'

        response = requests.post(url, json={'query': query, 'variables': variables})

        json = response.json()
        if json.get('errors'):
            raise Exception(json['errors'][0]['message'])
        else:
            return json['data']

    def AL_get_anime_by_title(self, title: str):
        """Uses the AniList API to search for anime by title"""
        log("Using AniList API to search for anime: " + title)
        query = '''
        query ($search: String) {
            Media (search: $search, type: ANIME) {
                id
                idMal
                title {
                    english
                    romaji
                }
                description
                coverImage {
                    extraLarge
                    medium
                }
                averageScore
                meanScore
                popularity
                episodes
                trailer {
                    site
                    id
                }
                genres
                studios {
                    nodes {
                        name
                    }
                }
                startDate {
                    year
                    month
                    day
                }
                status
                bannerImage
                duration
            }
        }
        '''
        variables = {
            'search': title
        }

        response = self._AL_qeury(query, variables)
        anime = response['Media']
        log(f"Anime with id {anime['id']} found!")
        return anime

    def AL_get_anime_by_id(self, id: int):
        """Uses the AniList API to search for anime by id"""
        log("Using AniList API to search for anime with id: " + str(id))
        query = '''
        query ($id: Int) {
            Media (id: $id, type: ANIME) {
                id
                idMal
                title {
                    english
                    romaji
                }
                description
                coverImage {
                    extraLarge
                    medium
                }
                averageScore
                meanScore
                popularity
                episodes
                trailer {
                    site
                    id
                }
                genres
                studios {
                    nodes {
                        name
                    }
                }
                startDate {
                    year
                    month
                    day
                }
                status
                bannerImage
                duration
            }
        }
        '''
        variables = {
            'id': id
        }

        response = self._AL_qeury(query, variables)
        anime = response['Media']
        log(f"Anime with id {anime['id']} found!")
        return anime
    
    def fetch_anime_by_title(self, title: str, no_cache=False):
        """Fetch anime by title from the database, or from the AniList API if not found"""
        self.validate_db()
        if self._db['anime']['titles'].get(title) and not no_cache:
            log("Found anime in database")
            return self._db['anime']['titles'][title]
        else:
            log(f"Fetching {title} from AniList API")
            try:
                anime = self.AL_get_anime_by_title(title)
                self._db['anime']['ids'][anime['id']] = anime
                self._db['anime'][title] = self._db['anime']['ids'][anime['id']] # Faster when we have 2 search keys
                self.updatejar()
                return anime
            except Exception as e:
                log("Failed to fetch anime from AniList API: " + str(e))
                return None
    
    def fetch_anime_by_id(self, id: int):
        """Fetch anime by title from the database, or from the AniList API if not found"""
        self.validate_db()
        if self._db['anime']['ids'].get(id):
            log("Found anime in database")
            return self._db['anime']['ids'][id]
        else:
            log(f"Fetching {id} from AniList API")
            try:
                anime = self.AL_get_anime_by_id(id)
                self._db['anime']['ids'][anime['id']] = anime
                self._db['anime'][anime['title']['english']] = self._db['anime']['ids'][anime['id']]
                self.updatejar()
                return anime
            except Exception as e:
                log("Failed to fetch anime from AniList API: " + str(e))
                return None

main = Main()

if action == 'find':
    title = params['title']
    log(f'Find anime with title "{title}"')
    anime_folder = os.path.join(main.sourcepath(title), title)
    anime_candidates = main.scan_anime(anime_folder)

    anime_candidates = main.sort_most_common_key(anime_candidates)
    anime = None
    for title, episodes in anime_candidates:
        anime = main.fetch_anime_by_title(title, no_cache=True) #! Remove no_cache=True in production
        log(f"Got {str(anime)}")
        if anime is not None:
            break
    
    if anime is None:
        log("No anime found for title " + title)

    else:
        # year = params.get('year', 'not specified')

        liz = xbmcgui.ListItem(anime['title']['english'], anime['title']['romaji'], offscreen=True)
        liz.setArt({
            'thumb': anime['coverImage']['medium'],
            'poster': anime['coverImage']['extraLarge'],
            'banner': anime['bannerImage'],
            'landscape': anime['bannerImage']
        })
        
        xbmcplugin.addDirectoryItem(
            handle=plugin_handle,
            url=str(anime['id']),
            listitem=liz,
            isFolder=True
        )

elif action == 'getdetails':
    anilist_id = params['url']
    log(f'Get details for anime with id {anilist_id}')
    anime = main.fetch_anime_by_id(anilist_id)
    if not anime:
        raise Exception("No anime found for id " + anilist_id)
    
    liz = xbmcgui.ListItem(anime['title']['english'], anime['title']['romaji'], offscreen=True)
    tags = liz.getVideoInfoTag()
    tags.setTitle(anime['title']['english'])
    tags.setOriginalTitle(anime['title']['romaji'])
    tags.setSortTitle(anime['title']['english'])
    tags.setUserRating(anime['averageScore'])
    tags.setPlot(anime['description'])
    tags.setDuration(anime['episodes'])
    if anime['trailer']:
        tags.setTrailer(f'plugin://plugin.video.youtube/?action=play_video&videoid={anime["trailer"]["id"]}')
    tags.setGenres(anime['genres'])
    # tags.setWriters(['None', 'Want', 'To Admit It']) # TODO: Get staff
    # tags.setDirectors(['Director 1', 'Director 2'])
    tags.setStudios([studio['name'] for studio in anime['studios']['nodes']])
    tags.setFirstAired(f'{anime["startDate"]["year"]}-{anime["startDate"]["month"]}-{anime["startDate"]["day"]}')
    tags.setTvShowStatus(anime['status'])
    tags.setEpisodeGuide(str(anime['id']))
    tags.setRatings(
        {
            'average': (anime['averageScore'], 0),
            'mean': (anime['meanScore'], 0),
            'popularity': (anime['popularity'], 0)
        }, defaultrating='average'
    )
    tags.setUniqueIDs(
        {
            'anilist': str(anime['id']),
            'mal': str(anime['idMal'])
        }, defaultuniqueid='anilist')
    tags.addSeason(1)
    # tags.setCast([xbmc.Actor('spiff', 'himself', order=2, thumbnail='/home/akva/Pictures/fish.jpg'), # TODO
    #                 xbmc.Actor('monkey', 'orange', order=1, thumbnail='/home/akva/Pictures/coffee.jpg')])
    tags.addAvailableArtwork(anime['bannerImage'], 'banner')
    tags.addAvailableArtwork(anime['coverImage']['extraLarge'], 'poster')
    liz.setAvailableFanart([{'image': anime['bannerImage'], 'preview': anime['bannerImage']},
                            {'image': anime['coverImage']['extraLarge'],
                                'preview': anime['coverImage']['extraLarge']}])
    xbmcplugin.setResolvedUrl(handle=plugin_handle, succeeded=True, listitem=liz)

elif action == 'getepisodelist':
    anilist_id = params['url']
    log(f'Get episode list for anime with id {anilist_id}')

    anime = main.fetch_anime_by_id(anilist_id)
    if not anime:
        raise Exception("No anime found for id " + anilist_id)
    
    log(f"Anime has {anime['episodes']} episodes")
    for i in range(1, anime['episodes'] + 1):
        liz = xbmcgui.ListItem(f'Episode {i}', offscreen=True)
        tags = liz.getVideoInfoTag()
        tags.setTitle(f'Episode {i}')
        tags.setSeason(1)
        tags.setEpisode(i)
        xbmcplugin.addDirectoryItem(handle=plugin_handle, url=f"{anime['id']}-1-{i}", listitem=liz, isFolder=False)

elif action == 'getepisodedetails':
    anilist_id, season, episode = params['url'].split('-')
    log(f'Get episode {episode} details for anime with id {anilist_id}')
    anime = main.fetch_anime_by_id(anilist_id)

    liz = xbmcgui.ListItem(f'Episode {episode}', offscreen=True)
    tags = liz.getVideoInfoTag()
    tags.setTitle(f'Episode {episode}')
    tags.setSeason(1)
    tags.setEpisode(int(episode))
    tags.setDuration(anime['duration'])
    tags.setGenres(anime['genres'])
    tags.setStudios([studio['name'] for studio in anime['studios']['nodes']])
    tags.addSeason(1)
    xbmcplugin.setResolvedUrl(handle=plugin_handle, succeeded=True, listitem=liz)

elif action == 'getartwork':
    anilist_id = params['id']
    log(f'Get artwork for anime with id {anilist_id}')
    anime = main.fetch_anime_by_id(anilist_id)

    liz = xbmcgui.ListItem(anime['title']['english'], anime['title']['romaji'], offscreen=True)
    liz.addAvailableArtwork(anime['bannerImage'], 'banner')
    liz.addAvailableArtwork(anime['coverImage']['extraLarge'], 'poster')
    liz.setAvailableFanart([{'image': anime['bannerImage'], 'preview': anime['bannerImage']},
                            {'image': anime['coverImage']['extraLarge'],
                                'preview': anime['coverImage']['extraLarge']}])
    xbmcplugin.setResolvedUrl(handle=plugin_handle, succeeded=True, listitem=liz)

elif "nfo" in action.lower():
    log("NFO not supported")

elif action is not None:
    xbmc.log(f'Action "{action}" not implemented', xbmc.LOGDEBUG)
    web_pdb.set_trace()

xbmcplugin.endOfDirectory(plugin_handle)
