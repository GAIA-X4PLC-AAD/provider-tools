Map and Scenario Data
====

## Description
This repository contains all the services of the data providers



### Content

```
├── asset_extractor
	Docker environment for asser extraction tooling. Frontend with NodeJS for input asset, media file and Python for script execution
│   copies the tools from:
		https://github.com/GAIA-X4PLC-AAD/provider-tools.git
		https://github.com/GAIA-X4PLC-AAD/OpenValidator.git
├── extended_search
	Docker environment for extended search. 
	NodeJS frontend for selection of search scripts, Python for script for parsing in the xml file. 
	Requires reduced binary json file -> see asset extractor
├── CONTRIBUTING.md
├── LICENSE.md
├── Readme.md
```


