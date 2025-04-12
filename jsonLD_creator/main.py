#import debugpy

# debugpy, listening on port 5678
#debugpy.listen(("0.0.0.0", 5678))
#print("Waiting for debugger to attach...")

#debugpy.wait_for_client()

#debugpy.breakpoint()


from datetime import datetime
from rdflib.namespace import SH, RDF
from rdflib import Graph, URIRef, Namespace, BNode
from rdflib.collection import Collection
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse
from typing import Tuple, Union, Dict, List

import shutil
import json
import logging
import argparse
import requests

DEBUG = True
if DEBUG:
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - %(message)s')
else:
    logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

# global config value with all shacles, dicts and jsonLD output
class Config:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            # initalize config
            cls._instance.SHACLS = {}
            cls._instance.JSON_OUT = {}
        return cls._instance

config = Config()


def datetime_handler(x):
    if isinstance(x, datetime):
        return x.isoformat()
    raise TypeError("Unknown type")
    
# check if value is greater/smaller then value
def check_min_max(shacl_data, name: str, compare_value: int, greater : bool):
    if name in shacl_data:
        value = int(shacl_data[name])
        if greater:
            if value >= compare_value:
                return True
        else:
            if value <= compare_value:
                return True
        return False            
    
    return None


# check if min count >= 1 
def is_required_property(shacl_data):
    check = check_min_max(shacl_data, f'{SH}qualifiedMinCount', 1, True)
    if check is None:
        check = check_min_max(shacl_data, f'{SH}minCount', 1, True)

    if check is None:
        return False
    return check


# check if can have more entries
# max count <= 1 or min count >= 2 
def is_list_property(shacl_data):
    check = check_min_max(shacl_data, f'{SH}qualifiedMaxCount', 1, False)
    if check is None:
        check = check_min_max(shacl_data, f'{SH}maxCount', 1, False)
    if check:
        return not check
    
    check = check_min_max(shacl_data, f'{SH}qualifiedMinCount', 1, True)
    if check is None:
        check = check_min_max(shacl_data, f'{SH}minCount', 1, True)

    if check is None:
        return False    

    return check


# get named value
def get_value(name, values, check_lower_case : bool):
    for key, data in values.items():
        if check_lower_case:
            if name in key.lower():
                return data # list   
        else:
            if name in key:
                return data # list

    return None


# get node value directrly from node or under qualifiedValueShape
def get_node_data(values) -> Tuple[str, list]:
    node_paths = []
    path_data = get_value("path", values, False)
    if path_data == 'manifest:hasLicense':
        test = 0
    for key, data in values.items():        
        if 'qualifiedValueShape' in key:
            node_data = get_value("node", data, False)
            if isinstance(node_data, str):
                node_paths.append(node_data)
                return path_data, node_paths
            
            and_data = get_value("and", node_data, False)
            return path_data, and_data
    
    node_data = get_value("node", values, False)
    if node_data is None:
        node_data = get_value("class", values, False)
    if node_data is not None:
        node_paths.append(node_data)
        return path_data, node_paths
    return path_data, None


# create property like
# "hdmap:elevationRange": {
#       "@value": "5.6",
#       "@type": "xsd:float"
#  },
# or
#  "manifest:hasAccessRole": {
#      "@type": "manifest:AccessRole",
#      "@id": "envited-x:isPublic"
# }
def create_property(namespace : str, property_name : str, value: str, type: str, name: str, lsonLD_dict: dict, level : int):
    property = {}
    if type:
        property['@type'] = f'xsd:{type}'
        property['@value'] = value
    else:
        if name is not None:
            property['@type'] = name
        property['@id'] = value

    key = create_namespace_name(namespace, property_name)
    # debug
    if key == 'manifest:hasAccessRole':
        test = 0
        
    lsonLD_dict[key] = property
    logging.debug(f'{" " * level * 3}add prop {key}')


# from 'https://ontologies.envited-x.net/manifest/v4/ontology#hasManifestReference'
# compare with registered prefixes, e.g  @prefix manifest: <https://ontologies.envited-x.net/manifest/v4/ontology#>
# to manifest, hasManifestReference
def get_namespace_name_from_url(url: str) -> Tuple[str, str]:
    prefixes = config.JSON_OUT['@context']
    for ns_key, uri_ref in prefixes.items():
        prefix = str(uri_ref)
        if url.startswith(prefix):
            shape_name = url[len(prefix):]
            return ns_key, shape_name
    return None, None


# from hdmap::Quantity 
# to hdmap, Quantity
def get_namespace(namespace_and_name):
    parts = namespace_and_name.split('::')
    if len(parts) != 2:
        logging.error(f'{namespace_and_name} not valid!')
        exit(1)
    return parts[0], parts[1]

def get_name_from_url(url):
    parts = url.split('#')
    if len(parts) == 2:
        return parts[1]
    
    return None
    

def create_namespace_name(namespace : str, shapename : str) -> str:
    return f'{namespace}:{shapename}'

# create node like
# "hdmap:hasQuantity": {
#       "@type": "hdmap:Quantity",
def create_node(namespace : str, shapename : str, type: str, lsonLD_dict: dict, is_list : bool, level : int) -> dict:
    node = {}
    type_without_shape = type.replace('Shape', '')
    node['@type'] = create_namespace_name(namespace, type_without_shape)

    key = create_namespace_name(namespace, shapename)

    # debug
    if key == 'manifest:hasArtifacts':
        test = 0

    if is_list:
        if key in lsonLD_dict:
            lsonLD_dict[key].append(node)
        else:
            node_as_list = []
            node_as_list.append(node)
            lsonLD_dict[key] = node_as_list
    else:
        lsonLD_dict[key] = node

    logging.debug(f'{" " * level * 3}add node {key}')
    return node


# get shacle shema
def get_shacle_shema(namespace : str) -> dict:
    if namespace in config.SHACLS:
        return config.SHACLS[namespace]
    logging.error(f'{namespace} not found!')
    exit(1)


# get shape from shacle data
def get_shacle_shape(namespace : str, shapename : str) -> dict:
    shacl_graph_data = get_shacle_shema(namespace)
    if shapename in shacl_graph_data['dict']:
        return shacl_graph_data['dict'][shapename]
    
    return None

# register key + value to json ld
def register_key(key : str, value, meta_data: dict, nodes : list, namespace: str, shapename: str, path: str, is_required: bool, lsonLD_dict: dict, level : int):
    if key in meta_data:
        if isinstance(meta_data[key], list):
            logging.error(f'meta_data of {key} should be dict or str!')
            exit(1)

        if nodes is None:
            # register as property
            namespace_sub, name_subtype = get_namespace_name_from_url(path)
            type_url = get_value("#datatype", value, False)
            if type_url:
                namespace_type, type = get_namespace_name_from_url(type_url)
                create_property(namespace, shapename, meta_data[key], type, None, lsonLD_dict, level)
            else:
                name_url = get_value("#name", value, False)
                name = get_name_from_url(name_url)
                property_name = create_namespace_name(namespace, name) if name is not None else None
                create_property(namespace, shapename, meta_data[key], None, property_name, lsonLD_dict, level)
        else:
            created_node = None
            for node in nodes:
                namespace_sub, type = get_namespace_name_from_url(node)
                shape_value_sub = get_shacle_shape(namespace_sub, str(node))
                if shape_value_sub is None:
                    continue
                
                if created_node is None:
                    created_node = create_node(namespace_sub, shapename, type, lsonLD_dict, False, level)
                # only subnodes / properties of further nodes are registered

                # go deeper
                lsonLD_node = created_node# if isinstance(meta_data[key], dict) else lsonLD_dict
                process_node(shape_value_sub, meta_data[key], lsonLD_node, level + 1)


    elif is_required:
        # TODO write empty node
        test = 0

# register list of key + value to json ld
def register_list(key : str, value, meta_data: list, nodes : list, namespace: str, shapename: str, path: str, is_required: bool, lsonLD_dict: dict, level : int):
    if key in meta_data:
        if not isinstance(meta_data[key], list):
            logging.error(f'meta_data of {key} should be list!')
            exit(1)
        if nodes is None:
            # register as property
            namespace_sub, name_subtype = get_namespace_name_from_url(path)
            type_url = get_value("#datatype", value, False)
            if type_url:
                namespace_type, type = get_namespace_name_from_url(type_url)
                create_property(namespace, shapename, meta_data[key], type, None, lsonLD_dict, level)
            else:
                name_url = get_value("#name", value, False)
                name = get_name_from_url(name_url)
                property_name = create_namespace_name(namespace, name) if name is not None else None
                create_property(namespace, shapename, meta_data[key], None, property_name, lsonLD_dict, level)
        else:
            # register as node
            for sub_meta_data in meta_data[key]:
                #test = sub_meta_data['manifest:hasCategory']
                #logging.debug(f'{test}')
                created_node = None
                for node in nodes:
                    namespace_sub, type = get_namespace_name_from_url(node)
                    shape_value_sub = get_shacle_shape(namespace_sub, str(node))
                    if shape_value_sub is None:
                        continue
                    
                    if created_node is None:
                        created_node = create_node(namespace_sub, shapename, type, lsonLD_dict, True, level)
                    # only subnodes / properties of further nodes are registered

                    # go deeper
                    process_node(shape_value_sub, sub_meta_data, created_node, level + 1)


    elif is_required:
        # TODO write empty node
        test = 0        

# process node with all props and sub nodes
def process_node(shape_value: dict, meta_data: Union[Dict, List], lsonLD_dict: dict, level : int):
    for value in shape_value:
        path, nodes = get_node_data(value)
        namespace, shapename = get_namespace_name_from_url(path)
        key = create_namespace_name(namespace, shapename)
        is_required = is_required_property(value)
        is_list = is_list_property(value)
        if is_list:
            register_list(key, value, meta_data, nodes, namespace, shapename, path, is_required, lsonLD_dict, level)                
        else:
            register_key(key, value, meta_data, nodes, namespace, shapename, path, is_required, lsonLD_dict, level)


# get prefix from url
def get_prefix_for_url(url, graph):
    for prefix, namespace in graph.namespace_manager.namespaces():
        # check if uri starts with namespace
        if url.startswith(str(namespace)):
            return prefix
    return None


# from https://ontologies.envited-x.net/envited-x/v2/ontology#isMedia
# to https://ontologies.envited-x.net/envited-x/v2/ontology#
def get_url_from_namespace(value):
    if "#" in value:
        url = value.rsplit('#', 1)[0] + '#'
    else: 
        url = value.split('#')[0].rsplit('/', 1)[0] + '/'
    return url


# get prefixes
def getPrefixes(shacl_graph):
    # collect mamespace prefix
    used_namespaces = set()
    for s, p, o in shacl_graph:
        #  check if subject, predicat, object is uri
        if isinstance(s, URIRef):
            used_namespaces.add(get_url_from_namespace(s))
        if isinstance(p, URIRef):
            used_namespaces.add(get_url_from_namespace(p))
        if isinstance(o, URIRef):
            used_namespaces.add(get_url_from_namespace(o))

    prefixes = dict()
    for prefix, namespace in shacl_graph.namespace_manager.namespaces():
        uriStr = str(namespace)
        if uriStr in used_namespaces:
            prefix_str = get_prefix_for_url(namespace, shacl_graph)
            prefixes[prefix_str] = namespace
    # add gx prefix
    prefixes["gx"] = Namespace("https://registry.lab.gaia-x.eu/development/api/trusted-shape-registry/v1/shapes/jsonld/trustframework#")              
    return prefixes


# use shacls and extracted data to create json ld dict
def process_graph(schema_namespace, schema_name, meta_data):
    config.JSON_OUT = defaultdict(list)
    # get shacl for asset
    if schema_namespace in config.SHACLS:        

        shacl_graph_data = config.SHACLS[schema_namespace]

        config.JSON_OUT['@context'] = shacl_graph_data['prefixes']
        
        # add id and type
        if 'did' in meta_data:
            config.JSON_OUT['@id'] = meta_data['did']
        else:
            logging.error(f'did not found in extraced data!')
            exit(1)
        config.JSON_OUT['@type'] = create_namespace_name(schema_namespace, schema_name)

        # get first element of main shacle        
        shape_value = get_shacle_shape(schema_namespace, schema_name)
        process_node(shape_value, meta_data, config.JSON_OUT, 0)
    else:
        logging.error(f'Cannot find ontology {schema_namespace}')
    
    return


#    Recursive function to “resolve” a value.
#    If it is a blank node, it is checked whether it is an RDF list.
#    Otherwise, an attempt is made to convert the blank node into a dict.
def resolve_value(graph, value):
    if isinstance(value, BNode):
        # Check whether it is an RDF list
        if (value, RDF.first, None) in graph:
            try:
                collection = list(Collection(graph, value))
                return collection
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
def convert_graph_to_dict(graph):
    graph_dict = {}
    for node_shape in graph.subjects(RDF.type, SH.NodeShape):

        prop_list = []
        for prop in graph.objects(node_shape, SH.property):    

            values_dict = {}
            for detail, value in graph.predicate_objects(prop):
                values_dict[str(detail)] = resolve_value(graph, value)

            prop_list.append(values_dict)
        graph_dict[str(node_shape)] = prop_list

    return graph_dict


# download shacl from url
def download_shacle(url_path : str, shacle_name: str) -> Path:
    filename = f'{shacle_name}_shacl.ttl'
    subfolder = 'shacles'    
    local_filepath = Path(f'{subfolder}/{filename}')

    if not local_filepath.exists():
        # get file from github
        url = f'{url_path}{filename}'
        response = requests.get(url)
        if not response:
            logging.error(f'No shacl files found in url: {url}')
            exit(1)

        if not Path(subfolder).exists():
            Path(subfolder).mkdir()
        with open(local_filepath, 'wb') as file:
            file.write(response.content) 

    return local_filepath

# create shacl data structure and register
def register_shacle(url_path : str, shacle_name: str, shacls):

    local_file_path = download_shacle(url_path, shacle_name)

    try:
        graph = Graph()
        graph.parse(local_file_path, format='turtle')
        
        graph_data = {}
        graph_data['graph'] = graph
        graph_data['dict'] = convert_graph_to_dict(graph)        
        graph_data['prefixes'] = getPrefixes(graph)

        # debug write as json
        debug_json_file = local_file_path.with_suffix(".json")
        with open(debug_json_file, 'w') as f:
            json.dump(graph_data['dict'], f, indent=2, default=datetime_handler)

        shacls[shacle_name] = graph_data
    except:
        logging.exception(f'cannot read turtle file: {local_file_path}')
        exit(1)


# replace url with raw.githubusercontent.com
def get_url_for_download(url):
    new_server = "https://raw.githubusercontent.com/GAIA-X4PLC-AAD/ontology-management-base"
    
    # Break the old URL into components
    parsed = urlparse(url)
    # Split the path into individual segments (empty parts are removed)
    segments = [seg for seg in parsed.path.split("/") if seg]
    
    if segments:
        name = segments[0]
        # Create the new URL: new server, /main/, then the extracted name
        new_url = f"{new_server}/main/{name}/"
        return new_url
    else:
        # If no path segments were found, return the new server
        return new_server 


def main():
    parser = argparse.ArgumentParser(prog='main.py', description='creates a jsonLD from an attribute table of the meta data extractors')
    parser.add_argument('filename', type=str,help='filename of json attribute table.')
    parser.add_argument('-ontology', type=str,help='githup path to ontologies')
    parser.add_argument('-out', type=str, help='output filname for json LD file.')
    parser.add_argument('-removeShacl', action="store_true", help='remove the downloaded folder shacl first')
    args = parser.parse_args()

    # read attribute data
    claim_path = Path(args.filename)
    claim_path = claim_path.resolve()
    if not claim_path.exists():
        logging.exception(f'Could not find file {claim_path}')
        exit(1)
    with open(claim_path, 'r', encoding='utf-8') as file:
        claim_data = json.load(file)

    # download shacle file    
    if args.removeShacl:
        shacl_folder = Path('shacles')
        if shacl_folder.exists():
            shutil.rmtree(shacl_folder)
    shacle_namespace, shacle_name = get_namespace(claim_data['shacle_type'])
    ontology_path = args.ontology + '/'
    shacl_definitions = {}
    url_path = f'{ontology_path}{shacle_namespace}/'
    register_shacle(url_path, shacle_namespace, shacl_definitions)

    # get gaiaX/envited prefixes
    envited_url = 'https://ontologies.envited-x.net'
    shacl_data = shacl_definitions[shacle_namespace]
    prefixes = {
            prefix: str(namespace) 
            for prefix, namespace in shacl_data['graph'].namespace_manager.namespaces() 
            if str(namespace).startswith(envited_url)
    }

    # and download additional shacles
    for key, value in prefixes.items():
        if key not in shacl_definitions:
            new_url_path = get_url_for_download(value)
            register_shacle(new_url_path, key, shacl_definitions)
    config.SHACLS = shacl_definitions
    
    # fill data in shacle structure
    try:
        process_graph(shacle_namespace, shacle_name, claim_data)
    except:
        logging.exception(f'Could not convert to json')
        exit(1)
        
    # write claims as json id to output    
    output_path = Path(args.out)
    with open(output_path, 'w') as f:
        json.dump(config.JSON_OUT, f, indent=2, default=datetime_handler)
        logging.info(f'write json ld to {output_path}')


if __name__ == '__main__':
    main()