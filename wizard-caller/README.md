# Description
calls the sd creation wizard with json and merged shacl file to fill the non-extractable attributes from the user

# Motivation
non-extractable attributes must be filled by the user

# How to run
- main.py with arguments
	- [filename] : filename of json LD file
    - -shacl : merged shacl file
    - -out : output filename for enhanced json LD file

# Install
    To install the required libraries run: `pip install -r requirements.txt` or `python -m pip install -r requirements.txt`    