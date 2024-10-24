# Description
reads an excel table with metadata descriptions and converts them into othology and Shacle Shape files for each data 
Excel Table: https://ascs2008.sharepoint.com/:x:/r/sites/team/_layouts/15/Doc.aspx?sourcedoc=%7B29F2C96B-A33B-44B9-92E3-0F513A0ED58B%7D&file=Metadata.xlsx&action=default&mobileredirect=true

# Motivation
The metadata with all its settings and structures can be better managed, edited and maintained in an Excel table. This script therefore automatically converts the table into ontologies and scale files

# How to run
- main.py with arguments
    - -table : Path to Excel Table (default Metadata.xlsx)
	- -out : Path to exported ontology and shacle files (default ontologies/)
	- -url : URL entry for the ontologies (default https://github.com/GAIA-X4PLC-AAD/map-and-scenario-data/tools/ontologie_creator/ontologies/')

# Install
To install the required libraries run: `pip install -r requirements.txt` or `python -m pip install -r requirements.txt`    
