# Description
extracts the necessary metadata from the file and converts it into a claim file

# Motivation
In order to fill metadata in a standardised and simple way, the metadata that is already directly contained in the data or calculated from it should be filled automatically.

# How to run
- main.py with arguments
    - [INPUT_FILES] : file(s) or folder for search
    - -out : Path to exported claims folder (default claims/)
    - -o : Path to ontology and shacl files (default ontologies/)
    - -u : Activates the user query via dialogues for non-extractable attributes

# Installation / How to setup
1. **Clone this git repository:**

2. **Install python** (https://www.python.org/, used python version: Python 3.12.0)

    How to check current version on windows: ```py --version```
    How to check current version on macOS: ```python3 --version```

3. **Install packages with pip**  

    To install the required libraries run: `pip install -r requirements.txt` or `python -m pip install -r requirements.txt`

# Development
Used integrated development environment: Visual Studio Code version 1.84.2


# List of supported formats
- OpenDRIVE (.xodr)
- OpenSCENARIO (.xosc)
- 3DModel : read Trian3DBuilder statistic.3dModel.json
