Map and Scenario Data
====

## Description
This repository contains all the services of the data providers



### Content

```
├── configs - config file to control the call in the asset extractor
├── asset_extraction: extracts, analyzes the assert and brings all information together in an asset archive
├── jsonLD_creator: creates a jsonLD from a json file with the help of ontology files.
├──	meta_data_extractor: extracts meta data for the asset product description
├──	ontology_creator: creates an ontology and shacl file from an excel table
├──	structure_creator: creates a folder and file structure for the asset archive and writes the structure to a json file (for the creation of the manifest jsonLD)
├── xodr_reducer: reduces the OpenDRIVE file to relevant nodes and attributes for the advanced search. see provider-services repro
├── xodr_routing_creator: creates a routing file (KML or GeoJSON) to display the asset geographically in map applications.
├── CONTRIBUTING.md
├── LICENSE.md
├── Readme.md
```


