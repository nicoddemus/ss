from setuptools import setup

description = "Command line script that automatically searches for video subtitles using OpenSubtitles.org APIs."
long_description = ''

setup(
    name="ss",
    version="1.2.0",
    packages=[],
    scripts=['ss.py'],
    py_modules=['calculate_hash'],
    install_requires=[x.strip() for x in file('requirements.txt')],
    entry_points={'console_scripts': ['ss = ss:Main']},

    # metadata for upload to PyPI
    author="nicoddemus@gmail.com",
    author_email="nicoddemus@gmail.com",
    description=description,
    long_description=long_description,
    license="GPL",
    keywords="subtitles script",
    url="http://nicoddemus.github.io/ss/",
)
