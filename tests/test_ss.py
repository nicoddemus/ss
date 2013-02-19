from __future__ import with_statement
import pytest
from mock import patch, MagicMock, call
from ss import FindMovieFiles, QueryOpenSubtitles, FindBestSubtitleMatches

    
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
            search_results = QueryOpenSubtitles(filenames, 'en')    
            server.LogIn.assert_called_once_with('', '', 'en', 'OS Test User Agent')
            calls = [
                call('TOKEN', [dict(moviehash=13, moviebytesize=0, sublanguageid='en'), dict(query='movie1')]),
                call('TOKEN', [dict(moviehash=13, moviebytesize=0, sublanguageid='en'), dict(query='movie2')]),
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
        mock.return_value = {
            'Parks.and.Recreation.S05E13.HDTV.x264-LOL.avi' : [
                dict(
                    SubFileName='Parks.and.Recreation.S05E13.HDTV.x264-LOL.srt',
                    SubDownloadsCnt=1000,
                    SubDownloadLink='http://sub1.srt',
                    SubFormat='srt',
                ),
                dict(
                    SubFileName='Parks.and.Recreation.S05E13.HDTV.x264-LOL.srt',
                    SubDownloadsCnt=1500,
                    SubDownloadLink='http://sub2.srt',
                    SubFormat='srt',
                ),
                dict(
                    SubFileName='Parks.and.Recreation.S05E13.HDTV.-LOL.srt',
                    SubDownloadsCnt=3000,
                    SubDownloadLink='http://sub3.srt',
                    SubFormat='srt',
                ),
            ]
        }
        
        results = list(FindBestSubtitleMatches(['Parks.and.Recreation.S05E13.HDTV.x264-LOL.avi'], 'en'))
        assert results == [('Parks.and.Recreation.S05E13.HDTV.x264-LOL.avi', 'http://sub1.srt', '.srt' )]
        
           
#===================================================================================================
# main    
#===================================================================================================
if __name__ == '__main__':
    pytest.main() #@UndefinedVariable