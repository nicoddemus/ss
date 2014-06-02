from __future__ import print_function, division
from contextlib import closing
import gzip
import optparse
import os
import shutil
import struct
import tempfile
import time
import sys

import guessit


if sys.version_info[0] == 3:
    from urllib.request import urlopen
    from xmlrpc.client import ServerProxy
else:
    from urllib import urlopen
    from xmlrpclib import Server as ServerProxy


def obtain_guessit_query(movie_filename, language):
    guess = guessit.guess_file_info(os.path.basename(movie_filename), info=['filename'])

    def extract_query(guess, parts):
        result = ['"%s"' % guess.get(k) for k in parts if guess.get(k)]
        return ' '.join(result)

    result = {}
    if guess.get('type') == 'episode':
        result['query'] = extract_query(guess, ['series', 'title', 'releaseGroup'])
        if 'season' in guess:
            result['season'] = guess['season']
        if 'episodeNumber' in guess:
            result['episode'] = guess['episodeNumber']

    elif guess.get('type') == 'movie':
        result['query'] = extract_query(guess, ['title', 'year'])
    else:
        assert 'guessit returned invalid query:'
        result['query'] = os.path.basename(movie_filename)

    result['sublanguageid'] = language

    return result


def obtain_movie_hash_query(movie_filename, language):
    return {
        'moviehash': calculate_hash_for_file(movie_filename),
        'moviebytesize': str(os.path.getsize(movie_filename)),
        'sublanguageid': language,
    }


def filter_bad_results(search_results, guessit_query):
    # filter out search results with bad season and episode number (if applicable);
    # sometimes OpenSubtitles will report search results subtitles that belong
    # to a different episode or season from a tv show; no reason why, but it seems to
    # work well just filtering those out
    if 'season' in guessit_query and 'episode' in guessit_query:
        guessit_season_episode = (guessit_query['season'], guessit_query['episode'])
        search_results = [x for x in search_results
                          if (int(x['SeriesSeason']), int(x['SeriesEpisode'])) == guessit_season_episode]
    return search_results


def query_open_subtitles(movie_filenames, language):
    uri = 'http://api.opensubtitles.org/xml-rpc'
    server = ServerProxy(uri, verbose=0, allow_none=True, use_datetime=True)
    login_info = server.LogIn('', '', 'en', 'OS Test User Agent')
    token = login_info['token']

    try:
        result = {}

        for movie_filename in movie_filenames:
            guessit_query = obtain_guessit_query(movie_filename, language)
            search_queries = [
                guessit_query,
                obtain_movie_hash_query(movie_filename, language),
            ]

            response = server.SearchSubtitles(token, search_queries)
            search_results = response['data']

            if search_results:
                search_results = filter_bad_results(search_results, guessit_query)
                result[movie_filename] = search_results

        return result
    finally:
        server.LogOut(token)


def find_subtitles(movie_filenames, language):
    all_search_results = query_open_subtitles(movie_filenames, language)

    for movie_filename in movie_filenames:
        search_results = all_search_results.get(movie_filename, [])
        if search_results:
            search_result = search_results[0]
            yield movie_filename, search_result['SubDownloadLink'], '.' + search_result['SubFormat']
        else:
            yield movie_filename, None, None


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


def download_subtitle(subtitle_url, subtitle_filename):
    # first download it and save to a temp dir
    with closing(urlopen(subtitle_url)) as urlfile:
        gzip_subtitle_contents = urlfile.read()

    tempdir = tempfile.mkdtemp()
    try:
        basename = subtitle_url.split('/')[-1]
        tempfilename = os.path.join(tempdir, basename)
        with open(tempfilename, 'wb') as f:
            f.write(gzip_subtitle_contents)

        with closing(gzip.GzipFile(tempfilename, 'rb')) as f:
            subtitle_contents = f.read()

        # copy it over the new filename
        with open(subtitle_filename, 'wb') as f:
            f.write(subtitle_contents)
    finally:
        shutil.rmtree(tempdir)


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


def has_subtitle(filename):
    # list of subtitle formats obtained from opensubtitles' advanced search page.
    formats = ['.sub', '.srt', '.ssa', '.smi', '.mpl']
    basename = os.path.splitext(filename)[0]
    for ext in formats:
        if os.path.isfile(basename + ext):
            return True

    return False


def change_configuration(params, filename):
    config = load_configuration(filename)
    config.set_config_from_lines(params)

    with open(filename, 'w') as f:
        for line in config.get_lines():
            f.write(line + '\n')

    return config


def load_configuration(filename):
    if os.path.isfile(filename):
        with open(filename) as f:
            lines = f.readlines()
    else:
        lines = []

    config = Configuration()
    config.set_config_from_lines(lines)
    return config


def calculate_hash_for_file(name):
    '''
    Calculates the hash for the given filename.

    Algorithm from: http://trac.opensubtitles.org/projects/opensubtitles/wiki/HashSourceCodes

    @param name: str
        Path to the file

    @return: str
        The calculated hash code, as an hex string.
    '''
    longlongformat = 'q'  # long long
    bytesize = struct.calcsize(longlongformat)

    f = open(name, "rb")

    filesize = os.path.getsize(name)
    hash = filesize

    if filesize < 65536 * 2:
        return "SizeError"

    for x in range(65536//bytesize):
        buffer = f.read(bytesize)
        (l_value,)= struct.unpack(longlongformat, buffer)
        hash += l_value
        hash = hash & 0xFFFFFFFFFFFFFFFF #to remain as 64bit number


    f.seek(max(0,filesize-65536),0)
    for x in range(65536//bytesize):
        buffer = f.read(bytesize)
        (l_value,)= struct.unpack(longlongformat, buffer)
        hash += l_value
        hash = hash & 0xFFFFFFFFFFFFFFFF

    f.close()
    returnedhash = "%016x" % hash
    return returnedhash


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

__version__ = '1.4.2'

def main(argv=None):
    if argv is None:
        argv = sys.argv
    parser = optparse.OptionParser(
        usage='Usage: ss [options] <file or dir> <file or dir>...',
        description='Searches for subtitles using OpenSubtitles (http://www.opensubtitles.org).\n\nVersion: %s' % __version__,
        epilog='If a directory is given, search for subtitles for all movies on it (non-recursively).',
    )
    parser.add_option('-c', '--config', help='configuration mode.', action='store_true')
    parser.add_option('--version', help='displayes version and exit.', action='store_true')
    options, args = parser.parse_args(args=argv)
    if options.version:
        print('ss %s' % __version__)
        return 0

    if not options.config and len(args) < 2:
        parser.print_help()
        return 2

    config_filename = os.path.join(os.path.expanduser('~'), '.ss.ini')
    if options.config:
        config = change_configuration(args, config_filename)
        print('Config file at: ', config_filename)
        for line in config.get_lines():
            print(line)
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

    def print_status(text, status):
        spaces = 70 - len(text)
        if spaces < 2:
            spaces = 2
        sys.stdout.write('%s%s%s\n' % (text, ' ' * spaces, status))


    sys.stdout.write('Language: %s\n' % config.language)
    if config.skip and skipped_filenames:
        print('Skipping %d files that already have subtitles.' % len(skipped_filenames))

    if not input_filenames:
        return 1

    sys.stdout.write('Querying OpenSubtitles.org for %d file(s)...\n' % len(input_filenames))
    sys.stdout.write('\n')

    matches = []
    for (movie_filename, subtitle_url, subtitle_ext) in sorted(
            find_subtitles(input_filenames, language=config.language)):
        if subtitle_url:
            status = 'OK'
        else:
            status = 'No matches found.'

        print_status('- %s' % os.path.basename(movie_filename), status)

        if subtitle_url:
            subtitle_filename = obtain_subtitle_filename(movie_filename, config.language, subtitle_ext)
            matches.append((movie_filename, subtitle_url, subtitle_ext, subtitle_filename))

    if not matches:
        return 0

    sys.stdout.write('\n')
    sys.stdout.write('Downloading...\n')
    for (movie_filename, subtitle_url, subtitle_ext, subtitle_filename) in matches:
        download_subtitle(subtitle_url, subtitle_filename)
        print_status(' - %s' % os.path.basename(subtitle_filename), 'DONE')

#===================================================================================================
# main entry
#===================================================================================================
if __name__ == '__main__':
    try:
        sys.exit(main())
    except:
        import traceback

        with open(__file__ + '.log', 'a+') as log_file:
            log_file.write('ERROR ' + ('=' * 80) + '\n')
            log_file.write('Date: %s' % time.strftime('%c'))
            log_file.write('args: ' + repr(sys.argv))
            traceback.print_exc(file=log_file)
        raise



