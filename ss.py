from __future__ import print_function, division
from contextlib import closing
import gzip
import optparse
import os
import shutil
import struct
import tempfile
import sys
import subprocess
import itertools

from concurrent.futures import ThreadPoolExecutor, as_completed
from colorama import init, Fore, Style
import guessit


init(autoreset=True)


__version__ = '1.5.2'

if sys.version_info[0] == 3: # pragma: no cover
    from urllib.request import urlopen
    from xmlrpc.client import ServerProxy
    from configparser import RawConfigParser
else:  # pragma: no cover
    from urllib import urlopen
    from xmlrpclib import Server as ServerProxy
    from ConfigParser import RawConfigParser


def obtain_guessit_query(movie_filename, language):
    guess = guessit.guessit(os.path.basename(movie_filename))

    def extract_query(guess, parts):
        result = ['"%s"' % guess.get(k) for k in parts if guess.get(k)]
        return ' '.join(result)

    result = {}
    if guess.get('type') == 'episode':
        result['query'] = extract_query(guess, ['title', 'episode_title', 'release_group'])
        if 'season' in guess:
            result['season'] = guess['season']
        if 'episode' in guess:
            result['episode'] = guess['episode']

    elif guess.get('type') == 'movie':
        result['query'] = extract_query(guess, ['title', 'year'])
    else:  # pragma: no cover
        assert False, 'internal error: guessit guess: {0}'.format(guess)

    result['sublanguageid'] = language

    return result


def obtain_movie_hash_query(movie_filename, language):
    return {
        'moviehash': calculate_hash_for_file(movie_filename),
        'moviebytesize': str(os.path.getsize(movie_filename)),
        'sublanguageid': language,
    }


def filter_bad_results(search_results, guessit_query):
    """
    filter out search results with bad season and episode number (if
    applicable); sometimes OpenSubtitles will report search results subtitles
    that belong to a different episode or season from a tv show; no reason
    why, but it seems to work well just filtering those out
    """
    if 'season' in guessit_query and 'episode' in guessit_query:
        guessit_season_episode = (guessit_query['season'], guessit_query['episode'])
        search_results = [x for x in search_results
                          if (int(x['SeriesSeason']), int(x['SeriesEpisode'])) == guessit_season_episode]
    return search_results


def query_open_subtitles(movie_filename, language):
    uri = 'http://api.opensubtitles.org/xml-rpc'
    server = ServerProxy(uri, verbose=0, allow_none=True, use_datetime=True)
    login_info = server.LogIn('', '', 'en', 'ss v' + __version__)
    token = login_info['token']

    try:
        guessit_query = obtain_guessit_query(movie_filename, language)
        search_queries = [
            guessit_query,
            obtain_movie_hash_query(movie_filename, language),
        ]

        response = server.SearchSubtitles(token, search_queries)
        try:
            search_results = response['data']
        except KeyError:  # noqa
            raise KeyError('"data" key not found in response: %r' % response)

        if search_results:
            search_results = filter_bad_results(search_results, guessit_query)

        return search_results
    finally:
        server.LogOut(token)


def find_subtitle(movie_filename, language):
    search_results = query_open_subtitles(movie_filename, language)
    if search_results:
        search_result = search_results[0]
        return search_result['SubDownloadLink'], '.' + search_result['SubFormat']
    else:
        return None, None


def obtain_subtitle_filename(movie_filename, language, subtitle_ext, multi):
    # possibilities where we don't override
    if multi:
        new_ext = '.' + language + subtitle_ext
    else:
        new_ext = subtitle_ext
    return os.path.splitext(movie_filename)[0] + new_ext


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


def has_subtitle(filename, language, multi):
    # list of subtitle formats obtained from opensubtitles' advanced search page.
    formats = ['.sub', '.srt', '.ssa', '.smi', '.mpl']
    for ext in formats:
        subtitle_filename = obtain_subtitle_filename(filename, language, ext,
                                                     multi)
        if os.path.isfile(subtitle_filename):
            return True

    return False


def search_and_download(movie_filename, language, multi):
    subtitle_url, subtitle_ext = find_subtitle(movie_filename, language=language)
    if subtitle_url:
        subtitle_filename = obtain_subtitle_filename(movie_filename,
                                                     language,
                                                     subtitle_ext,
                                                     multi=multi)
        download_subtitle(subtitle_url, subtitle_filename)
        return subtitle_filename
    else:
        return None


def load_configuration(filename):
    p = RawConfigParser()
    p.add_section('ss')
    p.read(filename)

    def read_if_defined(option, getter):
        if p.has_option('ss', option):
            value = getattr(p, getter)('ss', option)
            setattr(config, option, value)

    config = Configuration()
    read_if_defined('recursive', 'getboolean')
    read_if_defined('skip', 'getboolean')
    read_if_defined('mkv', 'getboolean')
    read_if_defined('parallel_jobs', 'getint')

    if p.has_option('ss', 'languages'):
        value = p.get('ss', 'languages')
        config.languages = [x.strip() for x in value.split(',')]

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

    minimum_size = 65536 * 2
    assert filesize >= minimum_size, \
        'Movie {name} must have at least {min} bytes'.format(min=minimum_size,
                                                             name=name)

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

    attrs = 'languages recursive skip mkv parallel_jobs'.split()

    def __init__(self, languages=('eng',), recursive=False, skip=False,
                 mkv=False, parallel_jobs=8):
        self.languages = list(languages)
        self.recursive = recursive
        self.skip = skip
        self.mkv = mkv
        self.parallel_jobs = parallel_jobs

    def __eq__(self, other):
        for attr in self.attrs:
            if getattr(self, attr) != getattr(other, attr):
                return False
        return True

    def __ne__(self, other):  # pragma: no cover
        return not self == other

    def __repr__(self):  # pragma: no cover
        pairs = ['{attr}={value}'.format(attr=attr, value=getattr(self, attr))
                 for attr in self.attrs]
        return 'Configuration({0})'.format(', '.join(pairs))

    def __str__(self):
        values = [
            'languages = %s' % ', '.join(self.languages),
            'recursive = %s' % self.recursive,
            'skip = %s' % self.skip,
            'mkv = %s' % self.mkv,
            'parallel_jobs = %d' % self.parallel_jobs,
        ]
        return '\n'.join(values)


def main(argv=sys.argv, stream=sys.stdout):
    parser = optparse.OptionParser(
        usage='Usage: ss [options] <file or dir> <file or dir>...',
        description='Searches for subtitles using OpenSubtitles (http://www.opensubtitles.org).\n\nVersion: %s' % __version__,
        epilog='If a directory is given, search for subtitles for all movies on it (non-recursively).',
    )
    parser.add_option('-v', '--verbose',
                      help='always displays configuration and enable verbose mode.',
                      action='store_true', default=False)
    options, args = parser.parse_args(args=argv)

    config_filename = os.path.join(os.path.expanduser('~'), '.ss.ini')
    config = load_configuration(config_filename)
    if options.verbose:
        print('Configuration read from {0}'.format(config_filename))
        print(config, file=stream)
        print()

    if len(args) < 2:
        parser.print_help(file=stream)
        return 2

    input_filenames = list(find_movie_files(args[1:], recursive=config.recursive))
    if not input_filenames:
        print('No files to search subtitles for. Aborting.', file=stream)
        return 1

    if config.mkv:
        if not check_mkv_installed():
            print('mkvmerge not found in PATH.', file=stream)
            print('Either install mkvtoolnix or disable mkv merging ' +
                  'in your config.', file=stream)
            return 4

    header = Fore.WHITE + Style.BRIGHT
    lang_style = Fore.CYAN + Style.BRIGHT
    languages = ', '.join(
        lang_style + x + Style.RESET_ALL for x in config.languages)
    msg = '{header}Languages: {languages}'.format(header=header,
                                                  languages=languages)
    print(msg, file=stream)
    print(file=stream)

    multi = len(config.languages) > 1

    to_skip = set()
    if config.skip:
        for input_filename in input_filenames:
            for language in config.languages:
                if has_subtitle(input_filename, language, multi):
                    to_skip.add((input_filename, language))

        if to_skip:
            print('Skipping %d subtitles.' % len(to_skip), file=stream)

    def print_status(text, status):
        spaces = max(70 - len(text), 2)
        print('{text}{spaces}{status}'.format(
            text=text, spaces=' ' * spaces, status=status), file=stream)

    to_query = set(itertools.product(input_filenames, config.languages))
    to_query.difference_update(to_skip)

    if not to_query:
        return 0

    header_style = Fore.WHITE + Style.BRIGHT
    print(header_style + 'Downloading', file=stream)
    print(file=stream)

    matches = []
    to_query = sorted(to_query)

    with ThreadPoolExecutor(max_workers=config.parallel_jobs) as executor:
        future_to_movie_and_language = {}
        for movie_filename, language in to_query:
            f = executor.submit(search_and_download, movie_filename,
                                language=language, multi=multi)
            future_to_movie_and_language[f] = (movie_filename, language)

        for future in as_completed(future_to_movie_and_language):
            movie_filename, language = future_to_movie_and_language[future]
            subtitle_filename = future.result()

            if subtitle_filename:
                status = Fore.GREEN + '[OK]'
                matches.append((movie_filename, language, subtitle_filename))
            else:
                status = Fore.RED + '[Not found]'

            name = os.path.basename(movie_filename)
            print_status(
                name,
                status='{lang_color}{lang} {status}'.format(
                    lang_color=Fore.CYAN + Style.BRIGHT,
                    lang=language,
                    status=status))

    if config.mkv:
        print(file=stream)
        print(header_style + 'Embedding MKV', file=stream)
        print(file=stream)
        failures = []  # list of (movie_filename, output)
        to_embed = {}  # dict of movie -> (language, subtitle_filename)
        for movie_filename, language, subtitle_filename in matches:
            to_embed.setdefault(movie_filename, []).append((language,
                                                            subtitle_filename))
        to_embed = sorted(to_embed.items())
        with ThreadPoolExecutor(max_workers=config.parallel_jobs) as executor:
            future_to_mkv_filename = {}
            for movie_filename, subtitles in to_embed:
                subtitles.sort()
                movie_ext = os.path.splitext(movie_filename)[1].lower()
                mkv_filename = os.path.splitext(movie_filename)[0] + u'.mkv'
                if movie_ext != u'.mkv' and not os.path.isfile(mkv_filename):
                    f = executor.submit(embed_mkv, movie_filename, subtitles)
                    future_to_mkv_filename[f] = (mkv_filename, movie_filename)
                else:
                    print_status(os.path.basename(mkv_filename),
                                 Style.BRIGHT + Fore.YELLOW + '[skipped]')

            for future in as_completed(future_to_mkv_filename):
                mkv_filename, movie_filename = future_to_mkv_filename[future]
                status, output = future.result()
                if not status:
                    failures.append((movie_filename, output))
                status = Fore.GREEN + '[OK]' if status else Fore.RED + '[ERROR]'
                status = Style.BRIGHT + status
                print_status(os.path.basename(mkv_filename), status)

        if failures:
            print('_' * 80, file=stream)
            for movie_filename, output in failures:
                print(':%s:' % movie_filename, file=stream)
                print(output, file=stream)

    return 0


def embed_mkv(movie_filename, subtitles):
    output_filename = os.path.splitext(movie_filename)[0] + u'.mkv'
    params = [
        u'mkvmerge',
        u'--output', output_filename,
        movie_filename,
    ]
    for language, subtitle_filename in sorted(subtitles):
        iso_language = convert_language_code_to_iso639_2(language)
        params.extend([
            u'--language', u'0:{0}'.format(iso_language),
            subtitle_filename,
        ])
    try:
        check_output(params)
    except subprocess.CalledProcessError as e:
        return False, e.output
    else:
        return True, ''


def convert_language_code_to_iso639_2(lang_code):
    """
    Translate OpenSubtitle language code to its iso-639-2 equivalent.

    OpenSubtitles seem to support some extensions to iso-639-2, for instance
    "pob" means "brazilian portuguese".

    See http://www.opensubtitles.org/addons/export_languages.php.

    :param str lang_code: original language code from OpenSubtitles
    :return: iso-639-2 compatible
    """
    return {
        'pob': 'por',
        'pb': 'por',
    }.get(lang_code, lang_code)


def check_mkv_installed():
    """
    Returns True if mkvtoolinx seems to be installed.
    """
    try:
        check_output([u'mkvmerge', u'--version'])
    except subprocess.CalledProcessError:
        return False
    else:
        return True


def check_output(params):
    """
    Python 2.6 support: subprocess.check_output from Python 2.7.
    """
    popen = subprocess.Popen(params, shell=True, stderr=subprocess.STDOUT,
                             stdout=subprocess.PIPE)

    output, _ = popen.communicate()
    returncode = popen.poll()
    if returncode != 0:
        error = subprocess.CalledProcessError(returncode=returncode, cmd=params)
        error.output = output
        raise error
    return output


if __name__ == '__main__':
    sys.exit(main(sys.argv))  # pragma: no cover
