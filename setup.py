#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

setup(
    name='hookit-python',
    version='0.0.1',
    author='Xiaohan Song',
    author_email='xiaohan.song@oracle.com',
    description='Semi-transparent HTTP proxy to enhance any API with hooks',
    license='BSD 2-Clause',
    url='https://github.com/xhs/hookit',
    packages=find_packages(),
    install_requires=['trio>=0.10.0', 'loguru>=0.2.5']
)
