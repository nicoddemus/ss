Subtitles Searcher
==================

This is a command line script that automatically searches for video 
subtitles using [OpenSubtitles.org](http://www.opensubtitles.org) APIs. 

One advantage is that it can automatically search for all videos inside a directory, making it 
easy to download subtitles for TV shows packs.

Requirements
------------

Python 2.5+


Usage
-----

Just pass the name of the video file or a directory, in which case it will
search for all video files in that directory.

> python ss.py [directory or movie file]
>

Currently it is searching for subtitles in English only; until this is fixed, 
you can easily change the language by editting the "language" variable at
the start of the Main() function.

TODO
----

-   Proper command line options:
    *   --language
    *   --recursive

-   Better error handling;

