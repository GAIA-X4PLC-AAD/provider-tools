# Description
parses an OpenDRIVE file and projects the coordinates of the reference line into LatLon and writes them out as a georeferenced vector format as Google KML or GeoJSON.

# Motivation
the georeferenced vector format is required for the web display of the asset in order to display the route in a Google Map or OpenStreetMap viewn

# How to run
- main.py with arguments
    - -xodr : filename of OpenDRIVE file
    - -output : filename of exported file
	- -format : output format for geo file - choose 'kml', 'geojson'

# Install
    To install the required libraries run: `pip install -r requirements.txt` or `python -m pip install -r requirements.txt`    