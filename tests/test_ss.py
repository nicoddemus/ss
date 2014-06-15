from __future__ import with_statement
from contextlib import closing, contextmanager
from gzip import GzipFile
import os

import subprocess

import pytest

from mock import patch, MagicMock, call

import ss


def test_find_movie_files(tmpdir):
    tmpdir.join('video.avi').ensure()
    tmpdir.join('video.mpg').ensure()
    tmpdir.join('video.srt').ensure()
    tmpdir.join('sub', 'video.mp4').ensure()

    obtained = sorted(ss.find_movie_files([str(tmpdir.join('video.mpg')), str(tmpdir)]))
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
    assert not ss.has_subtitle(str(tmpdir.join('video.avi').ensure()))

    tmpdir.join('video.srt').ensure()
    assert ss.has_subtitle(str(tmpdir.join('video.avi').ensure()))


def test_query_open_subtitles(tmpdir):
    filename1 = tmpdir.join('Drive (2011) BDRip XviD-COCAIN.avi').ensure()
    filename2 = tmpdir.join('Project.X.2012.DVDRip.XviD-AMIABLE.avi').ensure()

    with patch('ss.ServerProxy', autospec=True) as rpc_mock:
        with patch('ss.calculate_hash_for_file', autospec=True) as hash_mock:
            hash_mock.return_value = '13ab'
            rpc_mock.return_value = server = MagicMock(name='MockServer')
            server.LogIn.return_value = dict(token='TOKEN')
            server.SearchSubtitles.return_value = dict(data={'SubFileName' : 'movie.srt'})

            search_results = ss.query_open_subtitles([str(filename1), str(filename2)], 'eng')
            rpc_mock.assert_called_once_with(
                'http://api.opensubtitles.org/xml-rpc',
                use_datetime=True,
                allow_none=True,
                verbose=0,
            )
            server.LogIn.assert_called_once_with('', '', 'en', 'OS Test User Agent')
            expected_calls = [
                 call('TOKEN', [dict(query=u'"Drive" "2011"', sublanguageid='eng'), dict(moviehash='13ab', moviebytesize='0', sublanguageid='eng')]),
                 call('TOKEN', [dict(query=u'"Project X" "2012"', sublanguageid='eng'), dict(moviehash='13ab', moviebytesize='0', sublanguageid='eng')]),
            ]

            server.SearchSubtitles.assert_has_calls(expected_calls)
            server.LogOut.assert_called_once_with('TOKEN')

            assert search_results == {
                str(filename1) : {'SubFileName' : 'movie.srt'},
                str(filename2) : {'SubFileName' : 'movie.srt'},
            }


def test_obtain_guessit_query():
    assert ss.obtain_guessit_query('Drive (2011) BDRip XviD-COCAIN.avi', 'eng') == {
        'query': '"Drive" "2011"',
        'sublanguageid' : 'eng',
    }

    assert ss.obtain_guessit_query('Project.X.2012.DVDRip.XviD-AMIABLE.avi', 'eng') == {
        'query': '"Project X" "2012"',
        'sublanguageid' : 'eng',
    }

    assert ss.obtain_guessit_query('Parks.and.Recreation.S05E13.HDTV.x264-LOL.avi', 'eng') == {
        'query': u'"Parks and Recreation" "LOL"',
        'episode': 13,
        'season': 5,
        'sublanguageid' : 'eng',
    }

    assert ss.obtain_guessit_query('Modern.Family.S05E01.HDTV.x264-LOL.mp4', 'eng') == {
        'query': u'"Modern Family" "LOL"',
        'episode': 1,
        'season': 5,
        'sublanguageid' : 'eng',
    }

    assert ss.obtain_guessit_query('The.IT.Crowd.S04.The.Last.Byte.PROPER.HDTV.x264-TLA.mp4', 'eng') == {
        'query': u'"The IT Crowd" "The Last Byte" "TLA"',
        'season': 4,
        'sublanguageid' : 'eng',
    }

    assert ss.obtain_guessit_query('The.IT.Crowd.E04.The.Last.Byte.PROPER.HDTV.x264-TLA.mp4', 'eng') == {
        'query': u'"The IT Crowd" "The Last Byte" "TLA"',
        'episode': 4,
        'sublanguageid' : 'eng',
    }

    assert ss.obtain_guessit_query('Unknown.mp4', 'eng') == {
        'query': u'"Unknown"',
        'sublanguageid': 'eng',
    }


def test_find_best_subtitles_matches(tmpdir):

    movie_filename = str(tmpdir.join('Parks.and.Recreation.S05E13.HDTV.x264-LOL.avi').ensure())

    with patch('ss.ServerProxy', autospec=True) as rpc_mock:
        with patch('ss.calculate_hash_for_file', autospec=True) as hash_mock:
            hash_mock.return_value = '13ab'
            rpc_mock.return_value = server = MagicMock(name='MockServer')
            server.LogIn.return_value = dict(token='TOKEN')

            server.SearchSubtitles.return_value = {
                'data' : [
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

            expected_result = (movie_filename, 'http://sub1.srt', '.srt' )
            results = list(ss.find_subtitles([movie_filename], 'en'))
            assert results == [expected_result]


@pytest.mark.parametrize(
    ['params', 'expected_config'],
    [
        ([], ss.Configuration('eng', recursive=0, skip=0)),
        (['language=br'], ss.Configuration('br', recursive=0, skip=0)),
        (['language=us', 'recursive=1'], ss.Configuration('us', recursive=1, skip=0)),
        (['skip=yes'], ss.Configuration('eng', recursive=0, skip=1)),
        (['mkv=yes'], ss.Configuration('eng', mkv=True)),
    ]
)
def test_change_configuration(tmpdir, params, expected_config):
    filename = str(tmpdir.join('ss.conf'))
    assert ss.change_configuration(params, filename) == expected_config


def test_load_configuration(tmpdir):
    assert ss.load_configuration(str(tmpdir.join('ss.conf'))) == ss.Configuration('eng', 0, 0)

    f = tmpdir.join('ss.conf').open('w')
    f.write('language=br\n')
    f.write('recursive=yes\n')
    f.write('skip=yes\n')
    f.write('foo=bar\n')
    f.write('foobar=4\n')
    f.close()

    assert ss.load_configuration(str(tmpdir.join('ss.conf'))) == ss.Configuration('br', 1, 1)


def test_script_main():
    """
    Ensure that ss is accessible from the command line.
    """
    proc = subprocess.Popen(['ss'], shell=True, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    stdout, stderr = proc.communicate()
    # different return codes for windows/linux, weird
    assert proc.returncode == 2
    assert stderr == b''
    assert b'Usage: ss [options]' in stdout


def test_download_subtitle(tmpdir):
    url = 'http://server.com/foo.gz'
    subtitle_filename = str(tmpdir / 'subtitle.srt')

    # write binary contents to ensure that we are not trying to encode/decode
    # subtitles (see issue #20)
    sub_contents = b'\xff' * 10

    gzip_filename = str(tmpdir / 'sub.gz')
    with closing(GzipFile(gzip_filename, 'wb')) as f:
        f.write(sub_contents)

    with patch('ss.urlopen') as urlopen_mock:
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


def test_embed_mkv():
    with patch('subprocess.Popen') as mocked_popen:
        mocked_popen.return_value = popen = MagicMock()
        popen.communicate.return_value = ('', '')
        popen.poll.return_value = 0

        assert ss.embed_mkv(u'foo.avi', u'foo.srt', 'eng') == (True, '')
        params = u'mkvmerge --output foo.mkv foo.avi --language 0:eng foo.srt'.split()
        mocked_popen.assert_called_once_with(params, shell=True,
                                             stderr=subprocess.STDOUT,
                                             stdout=subprocess.PIPE)
        popen.communicate.assert_called_once()
        popen.poll.assert_called_once()

        popen.communicate.return_value = ('failed error', '')
        popen.poll.return_value = 2
        assert ss.embed_mkv(u'foo.avi', u'foo.srt', 'eng') == (False, 'failed error')


def test_main(tmpdir):
    movie = tmpdir.join('serieS01E01.avi')
    movie.ensure()

    @contextmanager
    def patch_functions():
        patchers = [
            patch('ss.query_open_subtitles'),
            patch('ss.download_subtitle'),
            patch('ss.load_configuration'),
        ]
        yield [x.start() for x in patchers]
        for p in patchers:
            p.stop()

    with patch_functions() as (mocked_query, mocked_download, mocked_config):
        mocked_query.return_value = {
            str(movie):
                [{'SubDownloadLink': 'fake_url', 'SubFormat': 'srt'}],
        }
        mocked_download.side_effect = lambda url, name: open(name, 'w').close()
        mocked_config.return_value = ss.Configuration(mkv=False)
        assert ss.main(['ss', str(movie)]) == 0
        mocked_download.assert_called_with('fake_url', str(tmpdir.join('serieS01E01.srt')))
        assert tmpdir.join('serieS01E01.srt').isfile()

