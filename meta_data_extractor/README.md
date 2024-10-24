# Description
extracts the necessary metadata from the file and converts it into a json dictonary (for jsonLD creator)

# Motivation
In order to fill metadata in a standardised and simple way, the metadata that is already directly contained in the data or calculated from it should be filled automatically.

# How to run
- main.py with arguments
    - [filename] : asset file to extract metadata - support xodr, xosc
    - -out : filename to exported json dict 
    - -u : Activates the user query via dialogues for non-extractable attributes - deprecated

# Install
To install the required libraries run: `pip install -r requirements.txt` or `python -m pip install -r requirements.txt`    
