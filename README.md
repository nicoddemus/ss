# Subtitle Searcher - SS #

## Introduction ##

Command line script for searching video subtitles using 
[OpenSubtitles.org](http://www.opensubtitles.org ) APIs.

![OpenSubtitles.org](http://static.opensubtitles.org/gfx/logo-transparent.png)

[![version](http://img.shields.io/pypi/v/ss.svg)](https://crate.io/packages/ss)
[![downloads](http://img.shields.io/pypi/dm/ss.svg)](https://crate.io/packages/ss/)
[![ci](http://img.shields.io/travis/nicoddemus/ss.svg)](https://travis-ci.org/nicoddemus/ss)
[![coverage](http://img.shields.io/coveralls/nicoddemus/ss.svg)](https://coveralls.io/r/nicoddemus/ss)

### Features ###

- **Recursive search**: Automatically search for all videos inside a directory, making it 
  easy to download subtitles for TV shows packs. 
- **Multiple languages**: Search for more than one or more subtitle languages.
- **MKV embedding**: Can automatically create an MKV with the embeded subtitles: a single file contains all subtitles, which is easier to carry around.

## Install ##

Install using [pip](http://www.pip-installer.org):

```bash
pip install ss
```

## Requirements ##

- Python 2.6+, 3.3+, PyPy.
- [guessit](https://github.com/wackou/guessit).

## Usage ##

Just pass the name of the video file or a directory, in which case it will
search for all video files in that directory:

```bash
$ python ss.py Parks.and.Recreation.S05E13.HDTV.x264-LOL.mp4 The.Mentalist.S05E14.HDTV.x264-LOL.mp4
Language: eng
Querying OpenSubtitles.org for 2 file(s)...

- Parks.and.Recreation.S05E13.HDTV.x264-LOL.mp4                       OK
- The.Mentalist.S05E14.HDTV.x264-LOL.mp4                              OK

Downloading...
 - Parks.and.Recreation.S05E13.HDTV.x264-LOL.srt                      DONE
 - The.Mentalist.S05E14.HDTV.x264-LOL.srt                             DONE
``` 

It will try to find the best match online, and automatically download and rename the subtitles.

### Configuration ###

You can see the current configuration by executing `ss` with the `--verbose`
parameter:

```bash
$ python ss.py --verbose
Configuration read from ~/.ss.ini
languages = eng, pob
recursive = False
skip = True
mkv = True

Usage: ss [options] <file or dir> <file or dir>...
...
```

Configuration is read from `~/.ss.ini`, which is a standard `ini` file:

```ini
[ss]
languages=eng, pob
recursive=yes
skip=yes
mkv=False
```

The following options are available:

* `languages:` 3 letter codes with the languages to search subtitles for, 
  separated by commas. Use the same codes as when you change search languages.
  For a full list, see http://www.opensubtitles.org/addons/export_languages.php.

* `recursive`: if directories should be recursively searched for movies.

* `skip`: if movies that already have subtitles should be skipped. If this is 0 and a movie 
  already has subtitles, `ss` won't overwrite the current subtitle, but generate a file using
  the language as suffix; if that also already exists, it will use an additional *"ss"* prefix.

* `mkv`: if True, it will automatically create a [mkv](http://www.matroska.org/)
  file with video and subtitles embeded. Requires [mkvmerge](http://www.bunkus.org/videotools/mkvtoolnix)
  to be available in the `$PATH` environment variable.


## Support ##

If you find any issues (not finding subtitles for a specific movie, errors, etc.), please report it in the 
[issues page](https://github.com/nicoddemus/ss/issues).



