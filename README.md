Subtitles Searcher
==================

This is a command line script that automatically searches for video 
subtitles using [OpenSubtitles.org](http://www.opensubtitles.org) APIs. 

One advantage is that it can automatically search
for all videos inside a directory, making it easy to download subtitle
for TV shows season packs.

This script is in its early stages, but is usable as it is.

Requirements
------------

Python 2.5+


Usage
-----

Just pass the name of the video file or a directory, in which case it will
search for all video files in that directory.

> python ss.py <directory or movie file>
>

Currently it is searching for subtitles in English only; until this is fixed, 
you can easily change the language by editting the "language" variable at
the start of the Main() function.

TODO
----

-   **Better search**
    Currently it calculates the movie hash and uses only that to find a 
    suitable subtitle, which sometimes makes it miss subtitles;  
    *   Order subtitles by Downloaded# to find one that fits better;
    *   If querying by hashing fails, try to find one with the closest name;
    
-   Proper command line options:
    *   --language
    *   --recursive

-   Better error handling;

