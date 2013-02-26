import distribute_setup
distribute_setup.use_setuptools()

from setuptools import setup, find_packages
description = "This is a command line script that automatically searches for video subtitles using [OpenSubtitles.org](http://www.opensubtitles.org) APIs.",

setup(
    name = "ss",
    version = "0.2",
    packages = [],
    scripts = ['ss.py'],
    entry_points = {'console_scripts' : ['ss = ss:Main']},
    
    # metadata for upload to PyPI
    author = "nicoddemus@gmail.com",
    author_email = "nicoddemus@gmail.com",
    description = description,
    license = "GPL",
    keywords = "hello world example examples",
    url = "http://nicoddemus.github.com/ss/",  
    
    use_2to3=True,
)