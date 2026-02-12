#! /usr/bin/env python

from setuptools import setup

setup(
    name='PiRSClock-Full',
    version='3.0',
    description='Raspberry Pi Radio Studio Clock with Configurable Studio Indicators',
    author='Masaya Miyazaki',
    url='https://github.com/stcatcom/pirsclockfull',
    scripts=['pirsclockfull.py'],
    python_requires='>=3.7',
    install_requires=['pygame', 'RPi.GPIO'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Environment :: Console :: Framebuffer',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Programming Language :: Python :: 3',
        'Operating System :: POSIX :: Linux',
        'Topic :: Utilities',
    ],
)
