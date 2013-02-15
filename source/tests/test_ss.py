import pytest
from ss import FindMovieFiles

    
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
# main    
#===================================================================================================
if __name__ == '__main__':
    pytest.main() #@UndefinedVariable