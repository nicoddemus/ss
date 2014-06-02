# Subtitle Searcher - SS #

## Introduction ##

This is a command line script that automatically searches for video 
subtitles using [OpenSubtitles.org](http://www.opensubtitles.org ) APIs.

![OpenSubtitles.org](http://static.opensubtitles.org/gfx/logo-transparent.png)

One advantage is that it can automatically search for all videos inside a directory, making it 
easy to download subtitles for TV shows packs. Also, it can usually be configured by any download 
manager to automatically execute it when a movie or video finishes.

**Latest Release**: [1.4.2](https://github.com/nicoddemus/ss/releases/tag/1.4.2)

[![version](http://img.shields.io/pypi/v/ss.svg)](https://crate.io/packages/ss)
[![downloads](http://img.shields.io/pypi/dm/ss.svg)](https://crate.io/packages/ss/)
[![ci](http://img.shields.io/travis/nicoddemus/ss.svg)](https://travis-ci.org/nicoddemus/ss)

## Requirements ##

Python 2.6, 2.7, 3.3, 3.4 or PyPy.
Also uses the [guessit](https://github.com/wackou/guessit) package.

## Install ##

Install using [pip](http://www.pip-installer.org):

```bash
pip install ss
```

Or if you download the source, execute on the extracted folder:

```bash
python setup.py install
```

## Usage ##

Just pass the name of the video file or a directory, in which case it will
search for all video files in that directory:

```
    ] python ss.py Parks.and.Recreation.S05E13.HDTV.x264-LOL.mp4 The.Mentalist.S05E14.HDTV.x264-LOL.mp4
    Language: eng
    Querying OpenSubtitles.org for 2 file(s)...
    
    - Parks.and.Recreation.S05E13.HDTV.x264-LOL.mp4                       OK
    - The.Mentalist.S05E14.HDTV.x264-LOL.mp4                              OK
    
    Downloading...
     - Parks.and.Recreation.S05E13.HDTV.x264-LOL.srt                      DONE
     - The.Mentalist.S05E14.HDTV.x264-LOL.srt                             DONE
``` 

It will try to find the best match online, and automatically download and rename the subtitles.

To change language and other options, use `--config` (or `-c`). For instance, to change 
the language to Brazillian Portuguese and enable searching for files recursively, use:

```

    ] python ss.py --config language=pob recursive=1
    language=pob
    recursive=1
    skip=1
```

The following options are available:

* `language:` 3 letter code with the language to search subtitles for. Use the same code as it 
  appears when you change search languages (as in http://www.opensubtitles.org/en/search/sublanguageid-pob).

* `recursive`: if directories should be recursively searched for movies.

* `skip`: if movies that already have subtitles should be skipped. If this is 0 and a movie 
  already has subtitles, `ss` won't overwrite the current subtitle, but generate a file using
  the language as suffix; if that also already exists, it will use an additional *"ss"* prefix.


## Support ##

If you find any issues (not finding subtitles for a specific movie, errors, etc.), please report it in the 
[issues page](https://github.com/nicoddemus/ss/issues).



