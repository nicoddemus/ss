import xmlrpclib
import difflib
import os
from calculate_hash import CalculateHashForFile


uri = 'http://api.opensubtitles.org/xml-rpc'
server = xmlrpclib.Server(uri, verbose=0, allow_none=True, use_datetime=True)

login_info = server.LogIn('', '', 'en', 'OS Test User Agent')
token = login_info['token']

try:
    filename = r'M:\Incoming\The.Big.Bang.Theory.S06E11.HDTV.x264-LOL.mp4'
    
    moviehash = CalculateHashForFile(filename)
    moviebytesize = os.path.getsize(filename)
    search_input = dict(
        moviehash=moviehash,
        moviebytesize=moviebytesize,
        sublanguageid='eng',
    )
    response = server.SearchSubtitles(token, [search_input])
    search_results = response['data']
    possibilities = [] 
    for search_result in search_results:
        print '-' * 80
        keys = ['SeriesSeason', 'MovieName', 'LanguageName', 'SubFileName', 'SubDownloadLink']
        for key in keys:
            print key + ':', search_result[key]
        possibilities.append(search_result['SubFileName'])
            
    print '=' * 80
    print possibilities
    print difflib.get_close_matches('The.Big.Bang.Theory.S06E11.HDTV.x264-LOL.mp4', possibilities, n=1)
finally:
    logout_info = server.LogOut(token)
