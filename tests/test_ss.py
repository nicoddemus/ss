from __future__ import with_statement
from contextlib import closing
from gzip import GzipFile
import os
import re
import sys

import subprocess


if sys.version_info[0] == 3:
    from io import StringIO
else:
    from StringIO import StringIO

import pytest

from mock import MagicMock, call, DEFAULT

import ss


def test_find_movie_files(tmpdir):
    tmpdir.join('video.avi').ensure()
    tmpdir.join('video.mpg').ensure()
    tmpdir.join('video.srt').ensure()
    tmpdir.join('sub', 'video.mp4').ensure()

    obtained = sorted(
        ss.find_movie_files([str(tmpdir.join('video.mpg')), str(tmpdir)]))
    assert obtained == [
        tmpdir.join('video.avi'),
        tmpdir.join('video.mpg'),
    ]

    obtained = sorted(ss.find_movie_files([str(tmpdir)], recursive=True))
    assert obtained == [
        tmpdir.join('sub', 'video.mp4'),
        tmpdir.join('video.avi'),
        tmpdir.join('video.mpg'),
    ]


def test_has_subtitles(tmpdir):
    movie_filename = str(tmpdir.join('video.avi').ensure())
    assert not ss.has_subtitle(movie_filename, 'eng', multi=False)
    assert not ss.has_subtitle(movie_filename, 'eng', multi=True)

    tmpdir.join('video.srt').ensure()
    assert ss.has_subtitle(movie_filename, 'eng', multi=False)
    assert not ss.has_subtitle(movie_filename, 'eng', multi=True)

    tmpdir.join('video.eng.srt').ensure()
    assert ss.has_subtitle(movie_filename, 'eng', multi=True)


def test_query_open_subtitles(tmpdir, mock):
    filename = tmpdir.join('Drive (2011) BDRip XviD-COCAIN.avi').ensure()

    rpc_mock = mock.patch('ss.ServerProxy', autospec=True)
    hash_mock = mock.patch('ss.calculate_hash_for_file', autospec=True)
    hash_mock.return_value = '13ab'
    rpc_mock.return_value = server = MagicMock(name='MockServer')
    server.LogIn.return_value = dict(token='TOKEN')
    server.SearchSubtitles.return_value = dict(
        data=[{'SubFileName': 'movie.srt'}])

    search_results = ss.query_open_subtitles(str(filename), 'eng')
    rpc_mock.assert_called_once_with(
        'http://api.opensubtitles.org/xml-rpc', use_datetime=True,
        allow_none=True, verbose=0)
    server.LogIn.assert_called_once_with('', '', 'en',
                                         'OS Test User Agent')
    expected_calls = [
        call('TOKEN',
             [dict(query=u'"Drive" "2011"', sublanguageid='eng'),
              dict(moviehash='13ab', moviebytesize='0',
                   sublanguageid='eng')]),
    ]

    server.SearchSubtitles.assert_has_calls(expected_calls)
    server.LogOut.assert_called_once_with('TOKEN')

    assert search_results == [{'SubFileName': 'movie.srt'}]


def test_obtain_guessit_query():
    assert ss.obtain_guessit_query('Drive (2011) BDRip XviD-COCAIN.avi',
                                   'eng') == {
               'query': '"Drive" "2011"',
               'sublanguageid': 'eng',
           }

    assert ss.obtain_guessit_query('Project.X.2012.DVDRip.XviD-AMIABLE.avi',
                                   'eng') == {
               'query': '"Project X" "2012"',
               'sublanguageid': 'eng',
           }

    assert ss.obtain_guessit_query(
        'Parks.and.Recreation.S05E13.HDTV.x264-LOL.avi', 'eng') == {
               'query': u'"Parks and Recreation" "LOL"',
               'episode': 13,
               'season': 5,
               'sublanguageid': 'eng',
           }

    assert ss.obtain_guessit_query('Modern.Family.S05E01.HDTV.x264-LOL.mp4',
                                   'eng') == {
               'query': u'"Modern Family" "LOL"',
               'episode': 1,
               'season': 5,
               'sublanguageid': 'eng',
           }

    assert ss.obtain_guessit_query(
        'The.IT.Crowd.S04.The.Last.Byte.PROPER.HDTV.x264-TLA.mp4', 'eng') == {
               'query': u'"The IT Crowd" "The Last Byte" "TLA"',
               'season': 4,
               'sublanguageid': 'eng',
           }

    assert ss.obtain_guessit_query(
        'The.IT.Crowd.E04.The.Last.Byte.PROPER.HDTV.x264-TLA.mp4', 'eng') == {
               'query': u'"The IT Crowd" "The Last Byte" "TLA"',
               'episode': 4,
               'sublanguageid': 'eng',
           }

    assert ss.obtain_guessit_query('Unknown.mp4', 'eng') == {
        'query': u'"Unknown"',
        'sublanguageid': 'eng',
    }


def test_find_best_subtitles_matches(tmpdir, mock):
    movie_filename = str(
        (tmpdir / 'Parks.and.Recreation.S05E13.HDTV.x264-LOL.avi').ensure())

    server = MagicMock(name='MockServer')
    mock.patch('ss.ServerProxy', autospec=True, return_value=server)
    mock.patch('ss.calculate_hash_for_file', autospec=True, return_value='13ab')
    server.LogIn.return_value = dict(token='TOKEN')

    server.SearchSubtitles.return_value = {
        'data': [
            # OpenSubtitles returned wrong Season: should be skipped
            dict(
                MovieReleaseName='Parks.and.Recreation.S05E13.HDTV.x264-LOL.srt',
                SubDownloadsCnt='1000',
                SubDownloadLink='http://sub99.srt',
                SubFormat='srt',
                SeriesSeason='4',
                SeriesEpisode='13',
            ),
            # OpenSubtitles returned wrong Episode: should be skipped
            dict(
                MovieReleaseName='Parks.and.Recreation.S05E13.HDTV.x264-LOL.srt',
                SubDownloadsCnt='1000',
                SubDownloadLink='http://sub98.srt',
                SubFormat='srt',
                SeriesSeason='5',
                SeriesEpisode='11',
            ),
            # First with correct season and episode: winner
            dict(
                MovieReleaseName='Parks.and.Recreation.S05E13.HDTV.x264-LOL.srt',
                SubDownloadsCnt='1000',
                SubDownloadLink='http://sub1.srt',
                SubFormat='srt',
                SeriesSeason='5',
                SeriesEpisode='13',
            ),
            dict(
                MovieReleaseName='Parks.and.Recreation.S05E13.HDTV.x264-LOL.srt',
                SubDownloadsCnt=1500,
                SubDownloadLink='http://sub2.srt',
                SubFormat='srt',
                SeriesSeason='5',
                SeriesEpisode='13',
            ),
            dict(
                MovieReleaseName='Parks.and.Recreation.S05E13.HDTV.-LOL.srt',
                SubDownloadsCnt=9999,
                SubDownloadLink='http://sub3.srt',
                SubFormat='srt',
                SeriesSeason='5',
                SeriesEpisode='13',
            ),
        ]
    }

    result = ss.find_subtitle(movie_filename, 'en')
    assert result == ('http://sub1.srt', '.srt' )


def test_load_configuration(tmpdir):
    config_filename = str(tmpdir.join('ss.conf'))
    assert ss.load_configuration(config_filename) == ss.Configuration()

    with open(config_filename, 'w') as f:
        lines = [
            '[ss]',
            'languages = br',
            'recursive = yes',
            'skip = on',
            'mkv = 1',
        ]
        f.write('\n'.join(lines))

    loaded = ss.load_configuration(str(tmpdir.join('ss.conf')))
    assert loaded == ss.Configuration(['br'], recursive=True, skip=True,
                                      mkv=True)


def test_check_mkv_installed(mock):
    mock.patch('ss.check_output', autospec=True)
    assert ss.check_mkv_installed()
    ss.check_output.assert_called_once_with([u'mkvmerge', u'--version'])

    ss.check_output.side_effect = subprocess.CalledProcessError(256,
                                                                'unused')
    assert not ss.check_mkv_installed()


def test_script_main():
    """
    Ensure that ss is accessible from the command line.
    """
    proc = subprocess.Popen('ss', shell=True, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    stdout, stderr = proc.communicate()
    assert stderr == b''
    assert b'Usage: ss [options]' in stdout
    assert proc.returncode == 2


def test_download_subtitle(tmpdir, mock):
    url = 'http://server.com/foo.gz'
    subtitle_filename = str(tmpdir / 'subtitle.srt')

    # write binary contents to ensure that we are not trying to encode/decode
    # subtitles (see issue #20)
    sub_contents = b'\xff' * 10

    gzip_filename = str(tmpdir / 'sub.gz')
    with closing(GzipFile(gzip_filename, 'wb')) as f:
        f.write(sub_contents)

    urlopen_mock = mock.patch('ss.urlopen')
    urlopen_mock.return_value = open(gzip_filename, 'rb')
    ss.download_subtitle(url, subtitle_filename)

    urlopen_mock.assert_called_once_with(url)

    assert os.path.isfile(subtitle_filename)
    with open(subtitle_filename, 'rb') as f:
        assert f.read() == sub_contents


def test_calculate_hash_for_file(tmpdir):
    # we don't actually test the algorithm since we copied from the
    # reference implementation, we just call it with dummy data that we know
    # the resulting hash to ensure the algorithm works across all python
    # versions
    filename = str(tmpdir / u'foo.x')
    data = b'\x08' * (250 * 1024) + b'\xff' * (250 * 1024)
    with open(filename, 'wb') as f:
        f.write(data)

    assert ss.calculate_hash_for_file(filename) == '010101010108b000'


def test_embed_mkv(mock):
    mocked_popen = mock.patch('subprocess.Popen')
    mocked_popen.return_value = popen = MagicMock()
    popen.communicate.return_value = ('', '')
    popen.poll.return_value = 0

    subtitles = [('eng', u'foo.eng.srt'), ('pob', u'foo.pob.srt')]
    mocked_convert = mock.patch('ss.convert_language_code_to_iso639_2',
               side_effect=['eng', 'por', 'eng'])
    assert ss.embed_mkv(u'foo.avi', subtitles) == (True, '')
    mocked_convert.assert_has_calls([call('eng'), call('pob')])

    params = (u'mkvmerge --output foo.mkv foo.avi '
              u'--language 0:eng foo.eng.srt '
              u'--language 0:por foo.pob.srt').split()
    mocked_popen.assert_called_once_with(params, shell=True,
                                         stderr=subprocess.STDOUT,
                                         stdout=subprocess.PIPE)
    popen.communicate.assert_called_once()
    popen.poll.assert_called_once()

    popen.communicate.return_value = ('failed error', '')
    popen.poll.return_value = 2
    result = ss.embed_mkv(u'foo.avi', [('eng', u'foo.srt')])
    assert result == (False, 'failed error')


def test_normal_execution(runner):
    """
    :type runner: _Runner
    """
    runner.register('serieS01E01.avi', ['eng'])
    assert runner.run('serieS01E01.avi') == 0
    runner.check_files('serieS01E01.avi', 'serieS01E01.srt')
    assert 'Downloading' in runner.output


@pytest.mark.parametrize(
    ('subtitle_files', 'languages', 'skip_count'),
    [
        (['movie.srt'], ['eng'], 1),
        (['movie.srt'], ['eng', 'pob'], 0),
        (['movie.eng.srt'], ['eng', 'pob'], 1),
        (['movie.eng.srt', 'movie.pob.srt'], ['eng', 'pob'], 2),
    ]
)
def test_skipping(tmpdir, runner, subtitle_files, languages, skip_count):
    """
    :type runner: _Runner
    """
    runner.register('movie.avi', languages)
    for subtitle_file in subtitle_files:
        (tmpdir / subtitle_file).write('untouched')
    runner.configuration.skip = True
    runner.configuration.languages = languages
    assert runner.run('movie.avi') == 0, runner.output
    expected_files = list(subtitle_files)
    if len(languages) > 1:
        expected_files.extend('movie.%s.srt' % x for x in languages)
    runner.check_files('movie.avi', *expected_files)
    for subtitle_file in subtitle_files:
        assert (tmpdir / subtitle_file).read() == 'untouched'
        assert subtitle_file not in runner.downloaded
    if skip_count:
        assert 'Skipping %d subtitles.' % skip_count in runner.output
    else:
        assert 'Skipping' not in runner.output


def test_mkv(tmpdir, runner):
    """
    :type runner: _Runner
    """
    runner.register('serieS01E01.avi', ['pob', 'eng'])
    runner.configuration.mkv = True
    runner.configuration.languages = ['pob', 'eng']
    assert runner.run('serieS01E01.avi') == 0
    ss.embed_mkv.assert_called_once_with(
        str(tmpdir / 'serieS01E01.avi'), [
            ('eng', str(tmpdir / 'serieS01E01.eng.srt')),
            ('pob', str(tmpdir / 'serieS01E01.pob.srt')),
        ],
    )

    assert 'Embedding MKV...' in runner.output
    runner.check_files('serieS01E01.avi', 'serieS01E01.pob.srt',
                       'serieS01E01.eng.srt', 'serieS01E01.mkv')


@pytest.mark.parametrize(
    ('lang', 'expected'),
    [
        ('eng', 'eng'),
        ('pob', 'por'),
        ('pb', 'por'),
    ],
)
def test_convert_language_code_to_iso639_2(lang, expected):
    assert ss.convert_language_code_to_iso639_2(lang) == expected


def test_verbose(runner):
    """
    :type runner: _Runner
    """
    assert runner.run('--verbose') == 2
    assert 'languages = eng' in runner.output
    assert 'recursive = False' in runner.output
    assert 'skip = False' in runner.output
    assert 'mkv = False' in runner.output


def test_missing_mkv(runner):
    """
    :type runner: _Runner
    """
    runner.register('serieS01E01.avi', ['eng'])
    runner.configuration.mkv = True
    ss.check_mkv_installed.return_value = False
    assert runner.run('serieS01E01.avi') == 4
    assert 'mkvmerge not found in PATH' in runner.output


def test_mkv_error(runner):
    runner.register('movie.avi', ['eng'])
    runner.configuration.mkv = True
    ss.embed_mkv.side_effect = None
    error_message = 'error calling mkvmerge'
    ss.embed_mkv.return_value = (False, error_message)
    assert runner.run('movie.avi') == 0
    runner.check_output_matches(':.*movie.avi:')
    runner.check_output_matches(error_message)


def test_multiple_languages(runner):
    """
    Test downloading multiple languages simultaneously.

    :type runner: _Runner
    """
    runner.register('serieS01E01.avi', ['eng', 'pb'])
    runner.configuration.languages = ['eng', 'pb']
    assert runner.run('serieS01E01.avi') == 0
    runner.check_files('serieS01E01.avi', 'serieS01E01.eng.srt',
                       'serieS01E01.pb.srt')


def test_mkv_with_subtitles_already_inplace(runner, tmpdir):
    """
    :type runner: _Runner
    """
    tmpdir.join('serieS01E01.srt').ensure()
    runner.register('serieS01E01.avi', ['eng'])
    runner.configuration.mkv = True
    assert runner.run('serieS01E01.avi') == 0
    runner.check_output_matches(r' - serieS01E01.mkv \s+ DONE')
    runner.check_files('serieS01E01.avi', 'serieS01E01.srt', 'serieS01E01.mkv')

    assert runner.run('serieS01E01.avi') == 0
    runner.check_output_matches(r' - serieS01E01.mkv \s+ skipped')


def test_no_matches(runner, tmpdir):
    tmpdir.join('movie.avi').ensure()
    assert runner.run('movie.avi') == 0
    runner.check_output_matches(r'- movie.avi \(eng\) \s+ No matches found.')


def test_no_input_files(runner, tmpdir):
    assert runner.run('') == 1
    runner.check_output_matches('No files to search subtitles for. Aborting.')


@pytest.fixture
def runner(tmpdir, mock):
    r = _Runner(tmpdir, mock)
    r.start()
    return r


class _Runner(object):
    def __init__(self, tmpdir, mock):
        self._tmpdir = tmpdir
        self._mock = mock
        self._movies = set()
        self._subtitles = {}  # movie name to set of subtitle langues
        self.configuration = ss.Configuration(mkv=False)
        self.output = None
        self.downloaded = set()


    def register(self, movie_name, subtitle_languages=()):
        self._tmpdir.join(movie_name).ensure()
        self._movies.add(movie_name)
        self._subtitles[movie_name] = frozenset(subtitle_languages)


    def run(self, *args):
        stream = StringIO()
        args = [str(self._tmpdir / x) if not x.startswith('--') else x for x in
                args]
        result = ss.main(['ss'] + args, stream=stream)
        self.output = stream.getvalue()
        return result


    def start(self):
        p = self._mock.patch
        p('ss.query_open_subtitles', side_effect=self._mock_query)
        p('ss.download_subtitle', side_effect=self._mock_download)
        p('ss.load_configuration', return_value=self.configuration)
        p('ss.embed_mkv', side_effect=self._mock_embed_mkv)
        p('ss.check_mkv_installed', return_value=True)


    def _mock_download(self, url, name):
        with open(name, 'w') as f:
            f.write('downloaded')
        self.downloaded.add(name)


    def _mock_query(self, movie_filename, language):
        movie_name = os.path.basename(movie_filename)
        if language in self._subtitles.get(movie_name, set()):
            return [{'SubDownloadLink': 'fake_url', 'SubFormat': 'srt'}]
        else:
            return []


    def _mock_embed_mkv(self, movie_filename, subtitles):
        if not os.path.isfile(movie_filename):
            return False, '{} not found'.format(movie_filename)

        for language, subtitle_filename in subtitles:
            if not os.path.isfile(subtitle_filename):
                return False, '{} not found'.format(subtitle_filename)

        open(os.path.splitext(movie_filename)[0] + '.mkv', 'w').close()
        return True, ''


    def check_files(self, *expected):
        __tracebackhide__ = True
        assert set(os.listdir(str(self._tmpdir))) == set(expected)


    def check_output_matches(self, regex):
        __tracebackhide__ = True
        msg = 'Could not find regex "{regex}" in output:\n{output}'
        assert re.search(regex, self.output) is not None, msg.format(
            regex=regex, output=self.output)



