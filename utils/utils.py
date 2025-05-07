from pathlib import Path
from urllib.parse import urlparse
from rdflib import Graph
from rdflib.namespace import SH, RDF
from rdflib import Graph, URIRef, BNode
from rdflib.collection import Collection
from typing import Optional

import json
import requests
import logging
import uuid

logger = logging.getLogger(__name__)

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
            logger.error(f'No shacl files found in url: {url}')
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
def get_prefixes(shacl_graph: Graph) -> dict[str, str]:
    prefixes = {
        prefix: str(namespace) 
        for prefix, namespace in shacl_graph.namespace_manager.namespaces() 
        if str(namespace).startswith(g_envited_url)
    }   
    return prefixes 


# load shacl as rdf graph
def load_shacl_files(shacl_files) ->Graph:
    shacl_graph = Graph()
    for shacl_file in shacl_files:
        shacl_graph.parse(shacl_file, format='turtle')
    return shacl_graph

# load json ld and add to rdf graph
def load_jsonld_file(jsonld_file : Path):

    if not jsonld_file.exists():
        logger.error(f'JsonLD files not found: {jsonld_file}')
        exit(1)  

    data_graph = Graph()
    logger.info(f'adding jsonld file to data graph: {jsonld_file}.')
    with open(jsonld_file) as f:
        data = json.load(f)
    data_graph.parse(data=json.dumps(data), format='json-ld')
    return data_graph

# load all shacls for jsonld and return as one graph
def get_shacle_from_json_graph(data_graph : Graph, prefixes_to_add : Optional[dict] = None) ->Graph:
    prefixes = get_prefixes(data_graph)
    if prefixes_to_add:
        prefixes.update(prefixes_to_add)

    shacl_files = []
    for key, value in prefixes.items():
        new_url_path = get_url_for_download(value)
        shacl_files.append(download_shacle(new_url_path, key))
    shacl_graph = load_shacl_files(shacl_files)    
    return shacl_graph

# create unique id
def create_uuid() -> str:
    random_uuid = uuid.uuid4()   # e.g. 'f47ac10b-58cc-4372-a567-0e02b2c3d479'
    return str(random_uuid)

#    Recursive function to “resolve” a value.
#    If it is a blank node, it is checked whether it is an RDF list.
#    Otherwise, an attempt is made to convert the blank node into a dict.
def resolve_value(graph, value):
    if isinstance(value, BNode):
        # Check whether it is an RDF list
        if (value, RDF.first, None) in graph:
            try:
                items = list(Collection(graph, value))
                return [resolve_value(graph, it) for it in items]
            except Exception as e:
                # Fallback: recursive conversion of the BNode into a dict
                return convert_bnode_to_dict(graph, value)
        else:
            # If not as a list, then try to convert the BNode into a dict.
            return convert_bnode_to_dict(graph, value)
    else:
        # For URIs or literals, simply return as a string
        return str(value)


# convert blank node recursive to dict
def convert_bnode_to_dict(graph, bnode):
    result = {}
    for pred, obj in graph.predicate_objects(bnode):
        result[str(pred)] = resolve_value(graph, obj)
    return result


# convert rdf graph to dict, resolve blank nodes
def convert_graph_to_dict(graph, search_node_shape: bool):
    graph_dict = {}
    type_to_search = SH.NodeShape if search_node_shape else SH.NodeKind
    for node_shape in graph.subjects(RDF.type, type_to_search):

        prop_list = []
        for prop in graph.objects(node_shape, SH.property):    

            values_dict = {}
            for detail, value in graph.predicate_objects(prop):
                values_dict[str(detail)] = resolve_value(graph, value)

            prop_list.append(values_dict)
        graph_dict[str(node_shape)] = prop_list

    return graph_dict