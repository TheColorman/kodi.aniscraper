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

import sys, os
import urllib.parse
import xml.etree.ElementTree as ET

import xbmcgui
import xbmcplugin, xbmcaddon
import xbmc, xbmcvfs

try:
    import cPickle as pickle
except ImportError:
    import pickle

import web_pdb

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
            self._db = pickle.load(open(__picklejar__, 'rb'))
        except Exception as e:
            log("Exception thrown loading the jar, creating empty jar: " + str(e))
            self._db = {}
            self.updatejar()
    
    def loadjar(self):
        """Load the database from the picklejar"""
        try:
            fs = open(__picklejar__, 'rb')
            self._db = pickle.load(fs)
            fs.close()
            return True
        except Exception as e:
            log("Exception thrown loading the jar: " + str(e))
            return False

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
                for folder in os.listdir(path):
                    if folder == folder_name:
                        self._db['sourcepath'] = path
                        self.updatejar()
                        return path

            raise Exception(f"No folder with name \"{folder_name}\" found in any of the video sources in sources.xml")
    
    def scan_anime(self, folder_path):
        """Scan a folder for anime. Returns a dictionary with keyr = anime titles and values = list of absolute paths to episode files"""
        anime = {}
        # def 
        def scan(folder):
            for item in os.listdir(folder):
                item_path = os.path.join(folder, item)
                if os.path.isdir(item_path):
                    scan(item_path)
                elif os.path.isfile(item_path):
                    if item.endswith('.mkv') or item.endswith('.mp4'):
                        anime[folder] = anime.get(folder, []) + [item_path]


main = Main()

if action == 'find':
    log('Find callback')
    title = params['title']
    anime_folder = os.path.join(main.sourcepath(title), title)
    web_pdb.set_trace()
    year = params.get('year', 'not specified')
    xbmc.log(f'Find movie with title "{title}" from year {year}', xbmc.LOGDEBUG)

    liz = xbmcgui.ListItem('Demo show 1', offscreen=True)
    liz.setArt({'thumb': 'DefaultVideo.png'})
    liz.setProperty('relevance', '0.5')
    xbmcplugin.addDirectoryItem(handle=plugin_handle, url='/path/to/show', listitem=liz, isFolder=True)
    liz = xbmcgui.ListItem('Demo show 2', offscreen=True)
    liz.setArt({'thumb': 'DefaultVideo.png'})
    liz.setProperty('relevance', '0.3')
    xbmcplugin.addDirectoryItem(handle=plugin_handle, url='/path/to/show2', listitem=liz, isFolder=True)

elif action == 'getdetails':
    url = params['url']
    if url == '/path/to/show':
        xbmc.log('Get tv show details callback', xbmc.LOGDEBUG)
        liz = xbmcgui.ListItem('Demo show 1', offscreen=True)
        tags = liz.getVideoInfoTag()
        tags.setTitle('Demo show 1')
        tags.setOriginalTitle('Demo shåvv 1')
        tags.setSortTitle('2')
        tags.setUserRating(5)
        tags.setPlotOutline('Outline yo')
        tags.setPlot('Plot yo')
        tags.setTagLine('Tag yo')
        tags.setDuration(110)
        tags.setMpaa('T')
        tags.setTrailer('/home/akva/fluffy/bunnies.mkv')
        tags.setGenres(['Action', 'Comedy'])
        tags.setWriters(['None', 'Want', 'To Admit It'])
        tags.setDirectors(['Director 1', 'Director 2'])
        tags.setStudios(['Studio1', 'Studio2'])
        tags.setDateAdded('2016-01-01')
        tags.setPremiered('2015-01-01')
        tags.setFirstAired('2007-01-01')
        tags.setTvShowStatus('Cancelled')
        tags.setEpisodeGuide('/path/to/show/guide')
        tags.setTagLine('Family / Mom <3')
        tags.setRatings({'imdb': (9, 100000), 'tvdb': (8.9, 1000)}, defaultrating='imdb')
        tags.setUniqueIDs({'imdb': 'tt8938399', 'tmdb': '9837493'}, defaultuniqueid='tvdb')
        tags.addSeason(1, 'Beautiful')
        tags.addSeason(2, 'Sun')
        tags.setCast([xbmc.Actor('spiff', 'himself', order=2, thumbnail='/home/akva/Pictures/fish.jpg'),
                      xbmc.Actor('monkey', 'orange', order=1, thumbnail='/home/akva/Pictures/coffee.jpg')])
        tags.addAvailableArtwork('DefaultBackFanart.png', 'banner')
        tags.addAvailableArtwork('/home/akva/Pictures/hawaii-shirt.png', 'poster')
        liz.setAvailableFanart([{'image': 'DefaultBackFanart.png', 'preview': 'DefaultBackFanart.png'},
                                {'image': '/home/akva/Pictures/hawaii-shirt.png',
                                 'preview': '/home/akva/Pictures/hawaii-shirt.png'}])
        xbmcplugin.setResolvedUrl(handle=plugin_handle, succeeded=True, listitem=liz)

elif action == 'getepisodelist':
    url = params['url']
    xbmc.log(f'Get episode list callback "{url}"', xbmc.LOGDEBUG)
    if url == '/path/to/show/guide':
        liz = xbmcgui.ListItem('Demo Episode 1x1', offscreen=True)
        tags = liz.getVideoInfoTag()
        tags.setTitle('Demo Episode 1')
        tags.setSeason(1)
        tags.setEpisode(1)
        tags.setFirstAired('2015-01-01')
        tags.addAvailableArtwork('/path/to/episode1', 'banner')
        xbmcplugin.addDirectoryItem(handle=plugin_handle, url="/path/to/episode1", listitem=liz, isFolder=False)

        liz = xbmcgui.ListItem('Demo Episode 2x2', offscreen=True)
        tags = liz.getVideoInfoTag()
        tags.setTitle('Demo Episode 2')
        tags.setSeason(2)
        tags.setEpisode(2)
        tags.setFirstAired('2014-01-01')
        tags.addAvailableArtwork('/path/to/episode2', 'banner')
        xbmcplugin.addDirectoryItem(handle=plugin_handle, url="/path/to/episode1", listitem=liz, isFolder=False)

elif action == 'getepisodedetails':
    url = params['url']
    if url == '/path/to/episode1':
        xbmc.log('Get episode 1 details callback', xbmc.LOGDEBUG)
        liz = xbmcgui.ListItem('Demo Episode 1', offscreen=True)
        tags = liz.getVideoInfoTag()
        tags.setTitle('Demo Episode 1')
        tags.setOriginalTitle('Demo æpisod 1x1')
        tags.setSeason(1)
        tags.setEpisode(1)
        tags.setUserRating(5)
        tags.setPlotOutline('Outline yo')
        tags.setPlot('Plot yo')
        tags.setTagLine('Tag yo')
        tags.setDuration(110)
        tags.setMpaa('T')
        tags.setTrailer('/home/akva/fluffy/unicorns.mkv')
        tags.setGenres(['Action', 'Comedy'])
        tags.setCountries(['Norway', 'Sweden', 'China'])
        tags.setWriters(['None', 'Want', 'To Admit It'])
        tags.setDirectors(['Director 1', 'Director 2'])
        tags.setStudios(['Studio1', 'Studio2'])
        tags.setDateAdded('2016-01-01')
        tags.setPremiered('2015-01-01')
        tags.setFirstAired('2007-01-01')
        tags.setTagLine('Family / Dad <3')
        tags.setRatings({'imdb': (9, 100000), 'tvdb': (8.9, 1000)}, defaultrating='imdb')
        tags.setUniqueIDs({'tvdb': '3894', 'imdb': 'tt384940'}, defaultuniqueid='tvdb')
        tags.addSeason(1, 'Beautiful')
        tags.addSeason(2, 'Sun')
        tags.setCast([xbmc.Actor('spiff', 'himself', order=2, thumbnail='/home/akva/Pictures/fish.jpg'),
                      xbmc.Actor('monkey', 'orange', order=1, thumbnail='/home/akva/Pictures/coffee.jpg')])
        tags.addAvailableArtwork('DefaultBackFanart.png', 'banner')
        tags.addAvailableArtwork('/home/akva/Pictures/hawaii-shirt.png', 'poster')
        liz.setAvailableFanart([{'image': 'DefaultBackFanart.png', 'preview': 'DefaultBackFanart.png'},
                                {'image': '/home/akva/Pictures/hawaii-shirt.png',
                                 'preview': '/home/akva/Pictures/hawaii-shirt.png'}])
        xbmcplugin.setResolvedUrl(handle=plugin_handle, succeeded=True, listitem=liz)

    elif url == '/path/to/episode2':
        xbmc.log('Get episode 2 details callback', xbmc.LOGDEBUG)
        liz = xbmcgui.ListItem('Demo Episode 2', offscreen=True)
        tags = liz.getVideoInfoTag()
        tags.setTitle('Demo Episode 2')
        tags.setOriginalTitle('Demo æpisod 2x2')
        tags.setSortTitle('1')
        tags.setSeason(2)
        tags.setEpisode(2)
        tags.setUserRating(8)
        tags.setPlotOutline('Outline yo')
        tags.setPlot('Plot yo')
        tags.setTagLine('Tag yo')
        tags.setDuration(110)
        tags.setMpaa('T')
        tags.setTrailer('/home/akva/fluffy/puppies.mkv')
        tags.setGenres(['Action', 'Comedy'])
        tags.setCountries(['Norway', 'Sweden', 'China'])
        tags.setWriters(['None', 'Want', 'To Admit It'])
        tags.setDirectors(['Director 1', 'Director 2'])
        tags.setStudios(['Studio1', 'Studio2'])
        tags.setDateAdded('2016-01-01')
        tags.setPremiered('2015-01-01')
        tags.setFirstAired('2007-01-01')
        tags.setTagLine('Something / Else')
        tags.setRatings({'imdb': (7, 25457), 'tvdb': (8.1, 5478)}, defaultrating='imdb')
        tags.setUniqueIDs({'tvdb': '3894', 'imdb': 'tt384940'}, defaultuniqueid='tvdb')
        tags.addSeason(1, 'Beautiful')
        tags.addSeason(2, 'Sun')
        tags.setCast([xbmc.Actor('spiff', 'himself', order=2, thumbnail='/home/akva/Pictures/fish.jpg'),
                      xbmc.Actor('monkey', 'orange', order=1, thumbnail='/home/akva/Pictures/coffee.jpg')])
        tags.addAvailableArtwork('DefaultBackFanart.png', 'banner')
        tags.addAvailableArtwork('/home/akva/Pictures/hawaii-shirt.png', 'poster')
        liz.setAvailableFanart([{'image': 'DefaultBackFanart.png', 'preview': 'DefaultBackFanart.png'},
                                {'image': '/home/akva/Pictures/hawaii-shirt.png',
                                 'preview': '/home/akva/Pictures/hawaii-shirt.png'}])
        xbmcplugin.setResolvedUrl(handle=plugin_handle, succeeded=True, listitem=liz)

elif action == 'nfourl':
    nfo = params['nfo']
    xbmc.log('Find url from nfo file', xbmc.LOGDEBUG)
    liz = xbmcgui.ListItem('Demo show 1', offscreen=True)
    xbmcplugin.addDirectoryItem(handle=plugin_handle, url="/path/to/show", listitem=liz, isFolder=True)

elif action is not None:
    xbmc.log(f'Action "{action}" not implemented', xbmc.LOGDEBUG)

xbmcplugin.endOfDirectory(plugin_handle)
