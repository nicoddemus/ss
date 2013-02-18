from __future__ import with_statement
import xmlrpclib
import difflib
import os
from calculate_hash import CalculateHashForFile
import gzip
import urllib
import tempfile
import shutil
import glob
import Queue
import threading
import time


DEBUG = False


#===================================================================================================
# QueryOpenSubtitles
#===================================================================================================
def QueryOpenSubtitles(hash_to_movie_filename, language):
    uri = 'http://api.opensubtitles.org/xml-rpc'
    server = xmlrpclib.Server(uri, verbose=0, allow_none=True, use_datetime=True)
    
    login_info = server.LogIn('', '', 'en', 'OS Test User Agent')
    token = login_info['token']
    
    try:
        search_queries = []
        for moviehash, movie_filename in hash_to_movie_filename.iteritems():
            moviebytesize = os.path.getsize(movie_filename)
            search_query = dict(
                moviehash=moviehash,
                moviebytesize=moviebytesize,
                sublanguageid=language,
            )
            search_queries.append(search_query)
            
        response = server.SearchSubtitles(token, search_queries)
        search_results = response['data']
        if search_results:
            return search_results
        else:
            return []
    finally:
        server.LogOut(token)
    

#===================================================================================================
# FindBestSubtitleMatches
#===================================================================================================
def FindBestSubtitleMatches(movie_filenames, language):
    
    hash_to_movie_filename = dict((CalculateHashForFile(x), x) for x in movie_filenames) 
    
    search_results = QueryOpenSubtitles(hash_to_movie_filename, language)
    
    hash_to_search_results = {}
    for search_data in search_results:
        hash_to_search_results.setdefault(search_data['MovieHash'], []).append(search_data)
    
    for hash, movie_filename in hash_to_movie_filename.iteritems():
        
        if hash not in hash_to_search_results:
            yield movie_filename, None, None
            continue
        
        search_results = hash_to_search_results[hash]
    
        possibilities = [] 
        for search_result in search_results:
            possibilities.append(search_result['SubFileName']) # this does not include the file extension
            
        closest_matches = difflib.get_close_matches(os.path.basename(movie_filename), possibilities)
        
        if closest_matches:
            closest_match = closest_matches[0]
            for search_result in search_results:
                if search_result['SubFileName'] == closest_match:
                    yield movie_filename, search_result['SubDownloadLink'], '.' + search_result['SubFormat']
                    break
        else:
            yield movie_filename, None, None
                
                
#===================================================================================================
# ObtainSubtitleFilename
#===================================================================================================
def ObtainSubtitleFilename(movie_filename, language, subtitle_ext):
    dirname = os.path.dirname(movie_filename)
    basename = os.path.splitext(os.path.basename(movie_filename))[0]
    
    # possibilities where we don't override
    filenames = [
        #  -> movie.srt
        os.path.join(dirname, basename + subtitle_ext),
        #  -> movie.eng.srt
        os.path.join(dirname, '%s.%s%s' % (basename, language, subtitle_ext)),
    ]
    for filename in filenames:  
        if not os.path.isfile(filename):
            return filename
    
    # use also ss on the extension and always overwrite
    #  -> movie.eng.ss.srt
    return os.path.join(dirname, '%s.%s.%s%s' % (basename, language, 'ss', subtitle_ext))


#===================================================================================================
# DownloadSub
#===================================================================================================
def DownloadSub(subtitle_url, subtitle_filename):
    # first download it and save to a temp dir
    urlfile = urllib.urlopen(subtitle_url)
    try:
        gzip_subtitle_contents = urlfile.read()
    finally:
        urlfile.close()
        
    tempdir = tempfile.mkdtemp()
    try:
        basename = subtitle_url.split('/')[-1]
        tempfilename = os.path.join(tempdir, basename)
        with file(tempfilename, 'wb') as f:
            f.write(gzip_subtitle_contents)
        
        f = gzip.GzipFile(tempfilename, 'r')
        try:
            subtitle_contents = f.read()
        finally:
            f.close()
            
        # copy it over the new filename
        with file(subtitle_filename, 'w') as f:
            f.write(subtitle_contents)
    finally:
        shutil.rmtree(tempdir)
        
        
        
#===================================================================================================
# FindMovieFiles
#===================================================================================================
def FindMovieFiles(input_names, recursive=False):
    extensions = set(['.avi', '.mp4', '.mpg', '.mkv'])
    returned = set()
    
    for input_name in input_names:
        
        if os.path.isfile(input_name) and input_name not in returned:
            yield input_name
            returned.add(input_name)
        else:
            names = os.listdir(input_name)
            for name in names:
                result = os.path.join(input_name, name)
                if name[-4:] in extensions:
                    if result not in returned:
                        yield result
                        returned.add(result)
                
                elif os.path.isdir(result) and recursive:
                    for x in FindMovieFiles([result], recursive):
                        yield x
            

#===================================================================================================
# Main
#===================================================================================================
def Main(argv):
    if len(argv) < 2:
        sys.stdout.write('ERROR: insufficient arguments\n')
        sys.stdout.write('\n') 
        sys.stdout.write('Usage:\n')
        sys.stdout.write('    ss file_or_dir1 file_or_dir2 ...\n')
        sys.stdout.write('\n') 
        sys.stdout.write('If a directory is given, search for subtitles for all movies on it (non-recursively).\n')
        return 2

    input_filenames = list(FindMovieFiles(argv[1:]))
    language = 'eng' 
    
    def PrintStatus(text, status):
        spaces = 70 - len(text)
        if spaces < 2:
            spaces = 2
        sys.stdout.write('%s%s%s\n' % (text, ' ' * spaces, status))
        
    
    
    if not input_filenames:
        sys.stdout.write('No files to search subtitles for. Aborting.\n')
        return 1
    
    
    sys.stdout.write('Querying OpenSubtitles.org for %d file(s)...\n' % len(input_filenames))
    sys.stdout.write('\n')
    matches = []
    for (movie_filename, subtitle_url, subtitle_ext) in sorted(FindBestSubtitleMatches(input_filenames, language=language)):
        if subtitle_url:
            status = 'OK'
        else:
            status = 'No matches found.' 
        
        PrintStatus('- %s' % os.path.basename(movie_filename), status)
        
        if subtitle_url:
            subtitle_filename = ObtainSubtitleFilename(movie_filename, language, subtitle_ext)
            matches.append((movie_filename, subtitle_url, subtitle_ext, subtitle_filename))
    
    if not matches:
        return 0
    
    sys.stdout.write('\n') 
    sys.stdout.write('Downloading...\n')
    for (movie_filename, subtitle_url, subtitle_ext, subtitle_filename) in matches:
        DownloadSub(subtitle_url, subtitle_filename)
        PrintStatus(' - %s' % os.path.basename(subtitle_filename), 'DONE')
        
#===================================================================================================
# Entry
#===================================================================================================
if __name__ == '__main__':
    try:
        import sys
        Main(sys.argv)    
    except:
        import traceback
        with file(__file__ + '.log', 'a+') as log_file:
            log_file.write('ERROR ' + ('=' * 80) + '\n') 
            log_file.write('Date: %s' % time.strftime('%c'))
            log_file.write('args: ' + repr(sys.argv))
            traceback.print_exc(file=log_file)



