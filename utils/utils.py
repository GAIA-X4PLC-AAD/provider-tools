from pathlib import Path
from urllib.parse import urlparse
from rdflib import Graph

import json
import requests
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

g_envited_url = 'https://ontologies.envited-x.net'
g_gaiax_server = "https://raw.githubusercontent.com/GAIA-X4PLC-AAD/ontology-management-base"
g_shacle_folder = 'shacles' 

# download shacl from url if not in local shacles folder
def download_shacle(url_path : str, shacle_name: str) -> Path:
    filename = f'{shacle_name}_shacl.ttl'   
    local_filepath = Path(f'{g_shacle_folder}/{filename}')

    if not local_filepath.exists():
        # get file from github
        url = f'{url_path}{filename}' if str(url_path).startswith(g_envited_url) else url_path
        response = requests.get(url)
        if not response:
            logging.error(f'No shacl files found in url: {url}')
            exit(1)

        if not Path(g_shacle_folder).exists():
            Path(g_shacle_folder).mkdir()
        with open(local_filepath, 'wb') as file:
            file.write(response.content) 

    return local_filepath


# replace url with raw.githubusercontent.com
def get_url_for_download(url: str) -> str:
    
    is_gaiax_ontology = True if str(url).startswith(g_envited_url) else False
    if is_gaiax_ontology:
        # Break the old URL into components
        parsed = urlparse(url)
        # Split the path into individual segments (empty parts are removed)
        segments = [seg for seg in parsed.path.split("/") if seg]
        
        if segments:
            name = segments[0]
            # Create the new URL: new server, /main/, then the extracted name
            new_url = f"{g_gaiax_server}/main/{name}/{name}_shacl.ttl"
            return new_url
    else:
        # If no path segments were found, return the new server
        return url.replace('#', '.ttl')
    

# get all envited x prefixes    
def get_prefixes(shacl_graph: Graph) -> list:
    prefixes = {
        prefix: str(namespace) 
        for prefix, namespace in shacl_graph.namespace_manager.namespaces() 
        if str(namespace).startswith(g_envited_url)
    }   
    return prefixes 


# load shacl as rdf graph
def load_shacl_files(shacl_files):
    shacl_graph = Graph()
    for shacl_file in shacl_files:
        shacl_graph.parse(shacl_file, format='turtle')
    return shacl_graph

# load json ld and add to rdf graph
def load_jsonld_file(jsonld_file : Path):

    if not jsonld_file.exists():
        logging.error(f'JsonLD files not found: {jsonld_file}')
        exit(1)  

    data_graph = Graph()
    logging.info(f'adding jsonld file to data graph: {jsonld_file}.')
    with open(jsonld_file) as f:
        data = json.load(f)
    data_graph.parse(data=json.dumps(data), format='json-ld')
    return data_graph