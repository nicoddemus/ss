# Subtitle Searcher - SS #

Command line script for searching video subtitles using 
[OpenSubtitles.org](http://www.opensubtitles.org ) APIs.

![OpenSubtitles.org](http://static.opensubtitles.org/gfx/logo-transparent.png)

[![py_versions](https://img.shields.io/pypi/pyversions/ss.svg)](https://pypi.python.org/pypi/ss/)
[![version](http://img.shields.io/pypi/v/ss.svg)](https://pypi.python.org/pypi/ss/)
[![downloads](http://img.shields.io/pypi/dm/ss.svg)](https://pypi.python.org/pypi/ss/)
[![ci](http://img.shields.io/travis/nicoddemus/ss.svg)](https://travis-ci.org/nicoddemus/ss)
[![coverage](http://img.shields.io/coveralls/nicoddemus/ss.svg)](https://coveralls.io/r/nicoddemus/ss)

## Features ##

- **Recursive search**: Search subtitles for all videos inside a directory (and sub-directories), 
  making it easy to download subtitles for TV shows packs. 
- **Multiple languages**: Search for more than one subtitle languages at the same time.
- **MKV embedding**: Can automatically create an MKV file with embedded 
  subtitles, which is easier to carry around.
  Requires [mkvmerge](http://www.bunkus.org/videotools/mkvtoolnix).

## Install ##

Install using [pip](http://www.pip-installer.org):

```bash
pip install ss
```

## Requirements ##

- Python 2.6+, 3.3+, PyPy.
- [guessit](https://github.com/wackou/guessit).
- [mkvmerge](http://www.bunkus.org/videotools/mkvtoolnix) (optional).

## Usage ##

Pass the name of one or more video files or directories:

![screenshot](https://raw.githubusercontent.com/nicoddemus/ss/master/images/screenshot.png)

It will try to find the best match online, and automatically download and 
move the subtitles to the same folder as the video files.

### Configuration ###

Configuration is stored in `~/.ss.ini` (or `C:\Users\<user>\.ss.ini` on Windows) as
a standard `ini` file:

```ini
[ss]
languages=eng, pob
recursive=yes
skip=yes
mkv=no
```

The following options are available:

* `languages:` 3 letter codes with the languages to search subtitles for, 
  separated by commas. 
  For a full list of available languages, see 
  http://www.opensubtitles.org/addons/export_languages.php.

* `recursive`: if directories should be recursively searched for movies (`yes|no`). 

* `skip`: if movies that already have subtitles should be skipped (`yes|no`).

* `mkv`: if `yes`, it will automatically create a [mkv](http://www.matroska.org/)
  file with embedded video and subtitles. Utility [mkvmerge](http://www.bunkus.org/videotools/mkvtoolnix)
  must be available in the `$PATH` environment variable (`yes|no`).

* `parallel_jobs`: number of concurrent threads used to download subtitles and create mkv files.
  Defaults to `8`.


## Support ##

If you find any issues, please report it in the 
[issues page](https://github.com/nicoddemus/ss/issues).


## Changelog ##

See the [releases page](https://github.com/nicoddemus/ss/releases).

