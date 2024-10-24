Map and Scenario Data
====

## Description
This repository contains all the tools of the data providers. These tools are mostly called up in https://github.com/GAIA-X4PLC-AAD/provider-services/tree/main/asset_extractor in the Docker as a pipeline to automatically generate an asset.zip from an asset.


### Content

```
├── asset_extraction: extracts, analyzes the assert and brings all information together in an asset archive
├── asset_reducer: reduces the xml based asset file to relevant nodes and attributes for the advanced search. see provider-services repro
├── configs - config file to control the call in the asset extractor
├── jsonLD_creator: creates a jsonLD from a json file with the help of ontology files.
├── jsonLD_creator: validate jsonLD against shacls
├──	meta_data_extractor: extracts meta data for the asset product description
├──	ontology_creator: creates an ontology and shacl file from an excel table
├──	structure_creator: creates a folder and file structure for the asset archive and writes the structure to a json file (for the creation of the manifest jsonLD)
├── xodr_routing_creator: creates a routing file (KML or GeoJSON) to display the asset geographically in map applications.
├── CONTRIBUTING.md
├── LICENSE.md
├── Readme.md
```


