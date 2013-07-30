from __future__ import with_statement
import pytest
from mock import patch, MagicMock, call
from ss import FindMovieFiles, QueryOpenSubtitles, FindBestSubtitleMatches, ChangeConfiguration, LoadConfiguration,\
    Configuration, HasSubtitle

    
#===================================================================================================
# testFindMovieFiles
#===================================================================================================
def testFindMovieFiles(tmpdir):
    tmpdir.join('video.avi').ensure()
    tmpdir.join('video.mpg').ensure()
    tmpdir.join('video.srt').ensure()
    tmpdir.join('sub', 'video.mp4').ensure()
    
    obtained = sorted(FindMovieFiles([str(tmpdir.join('video.mpg')), str(tmpdir)]))
    assert obtained == [
        tmpdir.join('video.avi'),
        tmpdir.join('video.mpg'),
    ]
     
    obtained = sorted(FindMovieFiles([str(tmpdir)], recursive=True))
    assert obtained == [
        tmpdir.join('sub', 'video.mp4'),
        tmpdir.join('video.avi'),
        tmpdir.join('video.mpg'),
    ]
    
    
#==================================================================================================
# testHasSubtitles
#==================================================================================================
def testHasSubtitles(tmpdir):
    assert not HasSubtitle(str(tmpdir.join('video.avi').ensure()))
    
    tmpdir.join('video.srt').ensure()
    assert HasSubtitle(str(tmpdir.join('video.avi').ensure()))
    
    
#===================================================================================================
# testQueryOpenSubtitles
#===================================================================================================
def testQueryOpenSubtitles(tmpdir):
    tmpdir.join('movie1.avi').ensure()
    tmpdir.join('movie2.avi').ensure()
    #
    with patch('xmlrpclib.Server') as rpc_mock:
        with patch('calculate_hash.CalculateHashForFile') as hash_mock:
            hash_mock.return_value = 13
            rpc_mock.return_value = server = MagicMock(name='MockServer')
            server.LogIn = MagicMock()    
            server.LogIn.return_value = dict(token='TOKEN')    
            server.SearchSubtitles = MagicMock()    
            server.SearchSubtitles.return_value = dict(data={'SubFileName' : 'movie.srt'})    
            server.LogOut = MagicMock()
            
            filenames = [str(tmpdir.join('movie1.avi')), str(tmpdir.join('movie2.avi'))]
            search_results = QueryOpenSubtitles(filenames, 'eng')    
            server.LogIn.assert_called_once_with('', '', 'en', 'OS Test User Agent')
            calls = [
                call('TOKEN', [dict(moviehash=13, moviebytesize=0, sublanguageid='eng'), dict(query='movie1', sublanguageid='eng')]),
                call('TOKEN', [dict(moviehash=13, moviebytesize=0, sublanguageid='eng'), dict(query='movie2', sublanguageid='eng')]),
            ]
            server.SearchSubtitles.assert_has_calls(calls)
            server.LogOut.assert_called_once_with('TOKEN')
            
            assert search_results == {
                str(tmpdir.join('movie1.avi')) : {'SubFileName' : 'movie.srt'},
                str(tmpdir.join('movie2.avi')) : {'SubFileName' : 'movie.srt'},
            }
            
            
#===================================================================================================
# testFindBestSubtitleMatches
#===================================================================================================
def testFindBestSubtitleMatches():     
    
    with patch('ss.QueryOpenSubtitles') as mock:
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
        results = list(FindBestSubtitleMatches([movie_filename], 'en'))
        assert results == [expected_result]

        # change movie filename to upper; the same query should be returned
        movie_filename = movie_filename.upper()
        expected_result = expected_result[0].upper(), expected_result[1], expected_result[2]

        results = list(FindBestSubtitleMatches([movie_filename], 'en'))
        assert results == [expected_result]
        
        
#===================================================================================================
# testChangeConfiguration
#===================================================================================================
def testChangeConfiguration(tmpdir):
    filename = str(tmpdir.join('ss.conf'))
    assert ChangeConfiguration([], filename) == Configuration('eng', 0, 0)
    assert ChangeConfiguration(['language=br'], filename) == Configuration('br', 0, 0)
    assert ChangeConfiguration(['language=us', 'recursive=1'], filename) == Configuration('us', 1, 0)
    assert ChangeConfiguration(['foo=bar', 'recursive=0'], filename) == Configuration('us', 0, 0)
    assert ChangeConfiguration(['skip=yes'], filename) == Configuration('us', 0, 1)
    
    
#===================================================================================================
# testLoadConfiguration
#===================================================================================================
def testLoadConfiguration(tmpdir):
    assert LoadConfiguration(str(tmpdir.join('ss.conf'))) == Configuration('eng', 0, 0)
    
    f = tmpdir.join('ss.conf').open('w')
    f.write('language=br\n')
    f.write('recursive=yes\n')
    f.write('skip=yes\n')
    f.write('foo=bar\n')
    f.write('foobar=4\n')
    f.close()
    
    assert LoadConfiguration(str(tmpdir.join('ss.conf'))) == Configuration('br', 1, 1)
           
#===================================================================================================
# main    
#===================================================================================================
if __name__ == '__main__':
    pytest.main() #@UndefinedVariable
