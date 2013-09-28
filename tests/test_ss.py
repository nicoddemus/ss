from __future__ import with_statement
import pytest
from mock import patch, MagicMock, call
from ss import find_movie_files, query_open_subtitles, find_subtitles, change_configuration, load_configuration,\
    Configuration, has_subtitle

    
#===================================================================================================
# test_find_movie_files
#===================================================================================================
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
    
    
#==================================================================================================
# test_has_subtitles
#==================================================================================================
def test_has_subtitles(tmpdir):
    assert not has_subtitle(str(tmpdir.join('video.avi').ensure()))
    
    tmpdir.join('video.srt').ensure()
    assert has_subtitle(str(tmpdir.join('video.avi').ensure()))
    
    
#===================================================================================================
# test_query_open_subtitles
#===================================================================================================
def test_query_open_subtitles(tmpdir):
    tmpdir.join('movie1.avi').ensure()
    tmpdir.join('movie2.avi').ensure()
    #
    with patch('xmlrpclib.Server') as rpc_mock:
        with patch('calculate_hash.CalculateHashForFile') as hash_mock:
            hash_mock.return_value = '13ab'
            rpc_mock.return_value = server = MagicMock(name='MockServer')
            server.LogIn = MagicMock()    
            server.LogIn.return_value = dict(token='TOKEN')    
            server.SearchSubtitles = MagicMock()    
            server.SearchSubtitles.return_value = dict(data={'SubFileName' : 'movie.srt'})    
            server.LogOut = MagicMock()
            
            filenames = [str(tmpdir.join('movie1.avi')), str(tmpdir.join('movie2.avi'))]
            search_results = query_open_subtitles(filenames, 'eng')    
            server.LogIn.assert_called_once_with('', '', 'en', 'OS Test User Agent')
            calls = [
                call('TOKEN', [dict(moviehash='13ab', moviebytesize='0', sublanguageid='eng'), dict(query='movie1', sublanguageid='eng')]),
                call('TOKEN', [dict(moviehash='13ab', moviebytesize='0', sublanguageid='eng'), dict(query='movie2', sublanguageid='eng')]),
            ]
            server.SearchSubtitles.assert_has_calls(calls)
            server.LogOut.assert_called_once_with('TOKEN')
            
            assert search_results == {
                str(tmpdir.join('movie1.avi')) : {'SubFileName' : 'movie.srt'},
                str(tmpdir.join('movie2.avi')) : {'SubFileName' : 'movie.srt'},
            }
            
            
#===================================================================================================
# test_find_best_subtitles_matches
#===================================================================================================
def test_find_best_subtitles_matches():     
    
    with patch('ss.query_open_subtitles') as mock:
        movie_filename = 'Parks.and.Recreation.S05E13.HDTV.x264-LOL.avi'

        mock.return_value = {
            movie_filename : [
                dict(
                    MovieReleaseName='Parks.and.Recreation.S05E13.HDTV.x264-LOL.srt',
                    SubDownloadsCnt=1000,
                    SubDownloadLink='http://sub1.srt',
                    SubFormat='srt',
                ),
                dict(
                    MovieReleaseName='Parks.and.Recreation.S05E13.HDTV.x264-LOL.srt',
                    SubDownloadsCnt=1500,
                    SubDownloadLink='http://sub2.srt',
                    SubFormat='srt',
                ),
                dict(
                    MovieReleaseName='Parks.and.Recreation.S05E13.HDTV.-LOL.srt',
                    SubDownloadsCnt=9999,
                    SubDownloadLink='http://sub3.srt',
                    SubFormat='srt',
                ),
            ]
        }

        # duplicate the query return value with upper case, to ensure we ignore filename's
        # case when finding matches
        mock.return_value[movie_filename.upper()] = mock.return_value[movie_filename]
        
        # normal query
        expected_result = ('Parks.and.Recreation.S05E13.HDTV.x264-LOL.avi', 'http://sub2.srt', '.srt' )
        results = list(find_subtitles([movie_filename], 'en'))
        assert results == [expected_result]

        # change movie filename to upper; the same query should be returned
        movie_filename = movie_filename.upper()
        expected_result = expected_result[0].upper(), expected_result[1], expected_result[2]

        results = list(find_subtitles([movie_filename], 'en'))
        assert results == [expected_result]
        
        
#===================================================================================================
# test_change_configuration
#===================================================================================================
def test_change_configuration(tmpdir):
    filename = str(tmpdir.join('ss.conf'))
    assert change_configuration([], filename) == Configuration('eng', 0, 0)
    assert change_configuration(['language=br'], filename) == Configuration('br', 0, 0)
    assert change_configuration(['language=us', 'recursive=1'], filename) == Configuration('us', 1, 0)
    assert change_configuration(['foo=bar', 'recursive=0'], filename) == Configuration('us', 0, 0)
    assert change_configuration(['skip=yes'], filename) == Configuration('us', 0, 1)
    
    
#===================================================================================================
# test_load_configuration
#===================================================================================================
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
           
#===================================================================================================
# main    
#===================================================================================================
if __name__ == '__main__':
    pytest.main() #@UndefinedVariable
