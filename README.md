Subtitles Searcher
==================

This is a command line script that automatically searches for video 
subtitles using [OpenSubtitles.org](http://www.opensubtitles.org) APIs. 

One advantage is that it can automatically search for all videos inside a directory, making it 
easy to download subtitles for TV shows packs. Also, it can usually be configured by any download 
manager to automatically execute it when a movie or video finishes. 

Requirements
------------

Python 2.5+


Usage
-----

Just pass the name of the video file or a directory, in which case it will
search for all video files in that directory.

******

    ] python ss.py Parks.and.Recreation.S05E13.HDTV.x264-LOL.mp4 The.Mentalist.S05E14.HDTV.x264-LOL.mp4
    Language: eng
    Querying OpenSubtitles.org for 2 file(s)...
    
    - Parks.and.Recreation.S05E13.HDTV.x264-LOL.mp4                       OK
    - The.Mentalist.S05E14.HDTV.x264-LOL.mp4                              OK
    
    Downloading...
     - Parks.and.Recreation.S05E13.HDTV.x264-LOL.srt                      DONE
     - The.Mentalist.S05E14.HDTV.x264-LOL.srt                             DONE
 
******

It will try to find the best match online, and automatically download and rename the subtitles.

To change language and other options, use `--config` (or `-c`). For instance, to change 
the language to Brazillian Portuguese and enable searching for files recursively, use:

******

    ] python ss.py --config language=pob recursive=1
    language=pob
    recursive=1

******

TODO
----
-   Better error handling;

