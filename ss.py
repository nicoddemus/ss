from __future__ import with_statement
import xmlrpclib
import difflib
import os
import calculate_hash
import gzip
import urllib
import tempfile
import shutil
import time
import optparse

#===================================================================================================
# query_open_subtitles
#===================================================================================================
def query_open_subtitles(movie_filenames, language):
    uri = 'http://api.opensubtitles.org/xml-rpc'
    server = xmlrpclib.Server(uri, verbose=0, allow_none=True, use_datetime=True)
    login_info = server.LogIn('', '', 'en', 'OS Test User Agent')
    token = login_info['token']
    
    try:
        result = {}
        
        for movie_filename in movie_filenames:
            search_queries = [
                dict(
                    moviehash=calculate_hash.CalculateHashForFile(movie_filename),
                    moviebytesize=str(os.path.getsize(movie_filename)),
                    sublanguageid=language,
                ),
                dict(
                    query=os.path.basename(os.path.splitext(movie_filename)[0]),
                    sublanguageid=language,
                )
            ]

            response = server.SearchSubtitles(token, search_queries)
            search_results = response['data']
        
            if search_results:
                result[movie_filename] = search_results
                
        return result 
    finally:
        server.LogOut(token)
    

#===================================================================================================
# find_subtitles
#===================================================================================================
def find_subtitles(movie_filenames, language):
    
    all_search_results = query_open_subtitles(movie_filenames, language)
    
    for movie_filename in movie_filenames:
        criteria = 'MovieReleaseName'
        
        # convert movie names from results to lower case so we can do a case-insensitive
        # comparison when trying to find a suitable match
        search_results = all_search_results.get(movie_filename, [])
        for search_result in search_results:
            search_result[criteria] = search_result[criteria].lower()

        # find search result that best matches the input movie filename (case insensitive)
        possibilities = [search_result[criteria] for search_result in search_results]
        basename = os.path.splitext(os.path.basename(movie_filename))[0].lower()
        closest_matches = difflib.get_close_matches(basename, possibilities)
        
        if closest_matches:
            # found matches; rank them by number of downloads and return that
            filtered = [x for x in search_results if x[criteria] in closest_matches]
            filtered.sort(key=lambda x: (closest_matches.index(x[criteria]), -int(x['SubDownloadsCnt'])))
            search_result = filtered[0]
            yield movie_filename, search_result['SubDownloadLink'], '.' + search_result['SubFormat']
        else:
            yield movie_filename, None, None
                
                
#===================================================================================================
# obtain_subtitle_filename
#===================================================================================================
def obtain_subtitle_filename(movie_filename, language, subtitle_ext):
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
# download_subtitle
#===================================================================================================
def download_subtitle(subtitle_url, subtitle_filename):
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
# find_movie_files
#===================================================================================================
def find_movie_files(input_names, recursive=False):
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
                    for x in find_movie_files([result], recursive):
                        yield x
                        
                        
#===================================================================================================
# has_subtitle
#===================================================================================================
def has_subtitle(filename):
    # list of subtitle formats obtained from opensubtitles' advanced search page.
    formats = ['.sub', '.srt', '.ssa', '.smi', '.mpl']                        
    basename = os.path.splitext(filename)[0]
    for ext in formats:
        if os.path.isfile(basename + ext):
            return True
        
    return False
    
    
            

#===================================================================================================
# change_configuration
#===================================================================================================
def change_configuration(params, filename):
    config = load_configuration(filename)
    config.set_config_from_lines(params)
    
    with file(filename, 'w') as f:
        for line in config.get_lines():
            f.write(line + '\n')
        
    return config
    
        
#===================================================================================================
# load_configuration
#===================================================================================================
def load_configuration(filename):
    
    if os.path.isfile(filename):
        with file(filename) as f:
            lines = f.readlines()
    else:
        lines = []
                        
    config = Configuration()
    config.set_config_from_lines(lines)
    return config


#===================================================================================================
# Configuration
#===================================================================================================
class Configuration(object):
    
    def __init__(self, language='eng', recursive=False, skip=False):
        self.language = language
        self.recursive = recursive
        self.skip = skip


    def set_config_from_lines(self, strings):
        
        def parse_bool(value):
            return int(value.lower() in ('1', 'true', 'yes'))
        
        for line in strings:
            if '=' in line:
                name, value = [x.strip() for x in line.split('=', 1)]
                if name == 'language':
                    self.language = value
                elif name == 'recursive':
                    self.recursive = parse_bool(value)
                elif name == 'skip':
                    self.skip = parse_bool(value) 
                    
                    
    def get_lines(self):
        return [
            'language=%s' % self.language,
            'recursive=%s' % self.recursive,
            'skip=%s' % self.skip,
        ]
        
        
    def __eq__(self, other):
        return self.language == other.language and \
            self.recursive == other.recursive and \
            self.skip == other.skip
            
            
    def __ne__(self, other):
        return not self == other
    

#===================================================================================================
# main
#===================================================================================================
def main(argv):
    parser = optparse.OptionParser(
        usage='Usage: %prog [options] <file or dir> <file or dir>...',
        description='Searches for subtitles using OpenSubtitles (http://www.opensubtitles.org).',
        epilog='If a directory is given, search for subtitles for all movies on it (non-recursively).',
    )
    parser.add_option('-c', '--config', help='configuration mode.', action='store_true')
    options, args = parser.parse_args(args=argv)
    if not options.config and len(args) < 2:
        parser.print_help()
        return 2
    
    config_filename = os.path.join(os.path.expanduser('~'), '.ss.ini')
    if options.config:
        config = change_configuration(args, config_filename)
        print 'Config file at:', config_filename
        for line in config.get_lines():
            print line
        return 0
    else:
        config = load_configuration(config_filename)

    input_filenames = list(find_movie_files(args[1:], recursive=config.recursive))
    if not input_filenames:
        sys.stdout.write('No files to search subtitles for. Aborting.\n')
        return 1
    
    skipped_filenames = []
    if config.skip:
        new_input_filenames = []
        for input_filename in input_filenames:
            if has_subtitle(input_filename):
                skipped_filenames.append(input_filename)
            else:
                new_input_filenames.append(input_filename)
        input_filenames = new_input_filenames
    
    def PrintStatus(text, status):
        spaces = 70 - len(text)
        if spaces < 2:
            spaces = 2
        sys.stdout.write('%s%s%s\n' % (text, ' ' * spaces, status))
    
    
    sys.stdout.write('Language: %s\n' % config.language)
    if config.skip and skipped_filenames:
        print 'Skipping %d files that already have subtitles.' % len(skipped_filenames)
    
    if not input_filenames:
        return 1
    
    sys.stdout.write('Querying OpenSubtitles.org for %d file(s)...\n' % len(input_filenames))
    sys.stdout.write('\n')
    
        
    matches = []
    for (movie_filename, subtitle_url, subtitle_ext) in sorted(find_subtitles(input_filenames, language=config.language)):
        if subtitle_url:
            status = 'OK'
        else:
            status = 'No matches found.' 
        
        PrintStatus('- %s' % os.path.basename(movie_filename), status)
        
        if subtitle_url:
            subtitle_filename = obtain_subtitle_filename(movie_filename, config.language, subtitle_ext)
            matches.append((movie_filename, subtitle_url, subtitle_ext, subtitle_filename))
    
    if not matches:
        return 0
    
    sys.stdout.write('\n') 
    sys.stdout.write('Downloading...\n')
    for (movie_filename, subtitle_url, subtitle_ext, subtitle_filename) in matches:
        download_subtitle(subtitle_url, subtitle_filename)
        PrintStatus(' - %s' % os.path.basename(subtitle_filename), 'DONE')
        
#===================================================================================================
# main entry
#===================================================================================================
if __name__ == '__main__':
    try:
        import sys
        main(sys.argv)    
    except:
        import traceback
        with file(__file__ + '.log', 'a+') as log_file:
            log_file.write('ERROR ' + ('=' * 80) + '\n') 
            log_file.write('Date: %s' % time.strftime('%c'))
            log_file.write('args: ' + repr(sys.argv))
            traceback.print_exc(file=log_file)
        raise



