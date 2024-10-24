# Description
Creates an asset archive. Reads configuration files for various tools and starts them depending on the type of asset entered.

# Motivation
Creation of a pipeline to automatically generate an asset.zip from asset files (xodr, xosc, ...).

# How to run
- main.py with arguments
	- [filenname] : asset filename
	- -config : config path for sub tools
    - -out : output path for asset archive

# Install
    To install the required libraries run: `pip install -r requirements.txt` or `python -m pip install -r requirements.txt`    