from __future__ import with_statement
from contextlib import nested
from mock import patch, MagicMock, call
import subprocess
from ss import find_movie_files, query_open_subtitles, find_subtitles, change_configuration, load_configuration,\
    Configuration, has_subtitle, obtain_guessit_query
import pytest


def test_find_movie_files(tmpdir):
    tmpdir.join('video.avi').ensure()
    tmpdir.join('video.mpg').ensure()
    tmpdir.join('video.srt').ensure()
    tmpdir.join('sub', 'video.mp4').ensure()

    obtained = sorted(find_movie_files([str(tmpdir.join('video.mpg')), str(tmpdir)]))
    assert obtained == [
        tmpdir.join('video.avi'),
        tmpdir.join('video.mpg'),
    ]

    obtained = sorted(find_movie_files([str(tmpdir)], recursive=True))
    assert obtained == [
        tmpdir.join('sub', 'video.mp4'),
        tmpdir.join('video.avi'),
        tmpdir.join('video.mpg'),
    ]


def test_has_subtitles(tmpdir):
    assert not has_subtitle(str(tmpdir.join('video.avi').ensure()))

    tmpdir.join('video.srt').ensure()
    assert has_subtitle(str(tmpdir.join('video.avi').ensure()))


def test_query_open_subtitles(tmpdir):
    filename1 = tmpdir.join('Drive (2011) BDRip XviD-COCAIN.avi').ensure()
    filename2 = tmpdir.join('Project.X.2012.DVDRip.XviD-AMIABLE.avi').ensure()

    with nested(patch('xmlrpclib.Server'), patch('ss.calculate_hash_for_file')) as (rpc_mock, hash_mock):
        hash_mock.return_value = '13ab'
        rpc_mock.return_value = server = MagicMock(name='MockServer')
        server.LogIn.return_value = dict(token='TOKEN')
        server.SearchSubtitles.return_value = dict(data={'SubFileName' : 'movie.srt'})

        search_results = query_open_subtitles([str(filename1), str(filename2)], 'eng')
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
    assert obtain_guessit_query('Drive (2011) BDRip XviD-COCAIN.avi', 'eng') == {
        'query': '"Drive" "2011"',
        'sublanguageid' : 'eng',
    }

    assert obtain_guessit_query('Project.X.2012.DVDRip.XviD-AMIABLE.avi', 'eng') == {
        'query': '"Project X" "2012"',
        'sublanguageid' : 'eng',
    }

    assert obtain_guessit_query('Parks.and.Recreation.S05E13.HDTV.x264-LOL.avi', 'eng') == {
        'query': u'"Parks and Recreation" "LOL"',
        'episode': 13,
        'season': 5,
        'sublanguageid' : 'eng',
    }

    assert obtain_guessit_query('Modern.Family.S05E01.HDTV.x264-LOL.mp4', 'eng') == {
        'query': u'"Modern Family" "LOL"',
        'episode': 1,
        'season': 5,
        'sublanguageid' : 'eng',
    }

    assert obtain_guessit_query('The.IT.Crowd.S04.The.Last.Byte.PROPER.HDTV.x264-TLA.mp4', 'eng') == {
        'query': u'"The IT Crowd" "The Last Byte" "TLA"',
        'season': 4,
        'sublanguageid' : 'eng',
    }

    assert obtain_guessit_query('The.IT.Crowd.E04.The.Last.Byte.PROPER.HDTV.x264-TLA.mp4', 'eng') == {
        'query': u'"The IT Crowd" "The Last Byte" "TLA"',
        'episode': 4,
        'sublanguageid' : 'eng',
    }

    assert obtain_guessit_query('Unknown.mp4', 'eng') == {
        'query': u'"Unknown"',
        'sublanguageid': 'eng',
    }


def test_find_best_subtitles_matches(tmpdir):

    movie_filename = str(tmpdir.join('Parks.and.Recreation.S05E13.HDTV.x264-LOL.avi').ensure())

    with nested(patch('xmlrpclib.Server'), patch('ss.calculate_hash_for_file')) as (rpc_mock, hash_mock):
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
        results = list(find_subtitles([movie_filename], 'en'))
        assert results == [expected_result]


def test_change_configuration(tmpdir):
    filename = str(tmpdir.join('ss.conf'))
    assert change_configuration([], filename) == Configuration('eng', 0, 0)
    assert change_configuration(['language=br'], filename) == Configuration('br', 0, 0)
    assert change_configuration(['language=us', 'recursive=1'], filename) == Configuration('us', 1, 0)
    assert change_configuration(['foo=bar', 'recursive=0'], filename) == Configuration('us', 0, 0)
    assert change_configuration(['skip=yes'], filename) == Configuration('us', 0, 1)


def test_load_configuration(tmpdir):
    assert load_configuration(str(tmpdir.join('ss.conf'))) == Configuration('eng', 0, 0)

    f = tmpdir.join('ss.conf').open('w')
    f.write('language=br\n')
    f.write('recursive=yes\n')
    f.write('skip=yes\n')
    f.write('foo=bar\n')
    f.write('foobar=4\n')
    f.close()

    assert load_configuration(str(tmpdir.join('ss.conf'))) == Configuration('br', 1, 1)


def test_script_main():
    """
    Ensure that ss is accessible from the command line.
    """
    output = subprocess.check_output('ss -h', shell=True)
    assert 'Usage: ss [options]' in output

if __name__ == '__main__':
    pytest.main(['', '-s', '-kfind_best_subtitles_matches']) #@UndefinedVariable
