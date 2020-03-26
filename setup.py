#!/usr/bin/env python

from setuptools import setup

setup(
    name='pyolx',
    version='0.0.3',
    description="pyolx - python wrapper for olx",
    author='LimeBrains',
    author_email='mail@limebrains.com',
    url='https://github.com/limebrains/pyolx',
    packages=['olx'],
    install_requires=['mock'
        'requests'
        'https://github.com/limebrains/scrapper-helpers/archive/master.zip'
        'beautifulsoup4'
        'pytest'
        'pytest-cov']
)
