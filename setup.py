from setuptools import setup, find_packages
description = "Command line script that automatically searches for video subtitles using OpenSubtitles.org APIs."

setup(
    name = "ss",
    version = "1.2.0",
    packages = [],
    scripts = ['ss.py'],
    entry_points = {'console_scripts' : ['ss = ss:Main']},
    
    # metadata for upload to PyPI
    author = "nicoddemus@gmail.com",
    author_email = "nicoddemus@gmail.com",
    description = description,
    license = "GPL",
    keywords = "subtitles script",
    url = "http://nicoddemus.github.com/ss/",  
    
    use_2to3=True,
)
