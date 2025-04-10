#import debugpy

# debugpy, listening on port 5678
#debugpy.listen(("0.0.0.0", 5678))
#print("Waiting for debugger to attach...")

#debugpy.wait_for_client()

#debugpy.breakpoint()


from datetime import datetime
from rdflib.namespace import SH, RDF
from rdflib import Graph, URIRef, Namespace
from collections import defaultdict
from pathlib import Path

import shutil
import json
import logging
import argparse
import requests

DEBUG = False
if DEBUG:
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - %(message)s')
else:
    logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')


class Config:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            # Initialisiere die Konfigurationen hier
            cls._instance.SHACLS = {}
            cls._instance.JSON_OUT = {}
        return cls._instance

config = Config()

dataTypeMap = {
    'xsd:string': { 'type' : 'str', 'default' : ''},
    'xsd:boolean': { 'type' : 'bool', 'default' : 'false'},
    'xsd:datetime.datetime': { 'type' : 'datetime.datetime', 'default' : '01-01-2000'},
    'xsd:dateTime': { 'type' : 'datetime.datetime', 'default' : '01-01-2000'},
    'xsd:integer': { 'type' : 'int', 'default' : '0'},
    'xsd:int': { 'type' : 'int', 'default' : '0'},
    'xsd:unsignedInt':  { 'type' : 'int', 'default' : '0'},
    'xsd:float': { 'type' : 'float', 'default' : '0.0'},
    'xsd:anyURI': { 'type' : 'str', 'default' : ''}
}   


def datetime_handler(x):
    if isinstance(x, datetime):
        return x.isoformat()
    raise TypeError("Unknown type")


def check_data_type(value, type_string: str, key: str) ->bool:
    if type_string in dataTypeMap:
        
        type_value = str(type(value))
        #suported_type = f'<class \'{dataTypeMap[type_string]['type']}\'>'
        
        # extract 'type' from dataTypeMap before using it in the f-string
        expected_type = dataTypeMap[type_string]['type']
        suported_type = f'<class "{expected_type}">'
        if type_value == suported_type:
            return True
        elif isinstance(value, list):
            return True
        else:
            logging.error(f'data type not match {type_value} != {suported_type} for {key}')
    else:
        logging.error(f'unsupported data type {type_string} for {key}')
    return False


def check_value_type(value: str, data_type: str) -> any:
    if data_type in dataTypeMap:
        if dataTypeMap[data_type]['type'] == 'str':
            return value
        elif dataTypeMap[data_type]['type'] == 'int':
            try:
                return int(value)
            except ValueError:
                return None
        elif dataTypeMap[data_type]['type'] == 'float':
            try:
                return float(value)
            except ValueError:
                return None
        elif dataTypeMap[data_type]['type'] == 'datetime.datetime':
            # TODO doesnt work!
            try:
                data_time = datetime.strptime(value, "%d-%m-%Y")
                logging.debug(type(data_time))
                return data_time
            except ValueError:
                return None
        else:
            logging.error(f'unsupported data type {dataTypeMap[data_type]}')
            return None
    else: 
        logging.error(f'unsupported data type {data_type}')
        return None


def replace_namespace(string: str, namespace: dict) -> str:
    for prefix, name in namespace.items():
        if name in string:
            return string.replace(name, f'{prefix}:')
    return string

def camel_case_to_lower(string):
    return string[0].lower() + string[1:]

def is_required_property(shacl_data):
    if f'{SH}minCount' in shacl_data:
        minCount = int(shacl_data[f'{SH}minCount'])
        if minCount >= 1:
            return True
    return False

def is_list_property(shacl_data):
    if f'{SH}maxCount' in shacl_data:
        maxCount = int(shacl_data[f'{SH}maxCount'])
        if maxCount <= 1:
            return False
    return True

# from 'https://github.com/GAIA-X4PLC-AAD/ontology-management-base/tree/main/hdmap/HdMapShape'
# to hdmap::HdMap
def convert_path_to_namespace(path, as_node_name=False, namespace=None):
    parts = path.split('/')
    last_parts = parts[-2:]
    last_parts[-1] = last_parts[-1].replace('Shape', '')
    if as_node_name:
        last_parts[-1] = last_parts[-1][0].lower()+ last_parts[-1][1:]
    if namespace:
        last_parts[0] = namespace
    separator = ':'
    namespace = separator.join(last_parts)
    return namespace

def getValue(name, values, check_lower_case : bool, optional=False):
    for key, data in values.items():
        if check_lower_case:
            if name in key.lower():
                return data    
        else:
            if name in key:
                return data
    
    if not optional:
        #logging.warning(f'{name} not found!!')
        return 'http://www.w3.org/2001/XMLSchema#string' # default string

    return None

def get_property_value(name, values):
    for key, data in values.items():
        key_str = key.split("#")[-1]
        if name == key_str:
            return data        
    return None        


def get_data_from_metadata(path, meta_data):
    if meta_data is not None:
        if path in meta_data:           
                return meta_data[path]
    return None


def get_namespace_and_name(namespace, name):
    return f'{namespace}:{name}'


def get_namespace(namespace_and_name):
    parts = namespace_and_name.split(':')
    if len(parts) != 2:
        logging.warning(f'{namespace_and_name} not valid!')
    return parts[0], parts[1]


def is_in_namespace(name, namespace):
    if f'{namespace}:' in name:
        return True
    return False

def create_group_name(node_path: str, forType: bool):
    last_part = node_path.rstrip('/').split('/')[-1]
    if last_part.endswith("Shape"):
        last_part = last_part[:-len("Shape")]
    if forType:
        return last_part
    else:
        return last_part[0].lower() + last_part[1:]


def get_schema_from_node_path(node_path: str):
    parts = node_path.split('/')
    return parts[-2]


# create group with type, e.g
#   "hdmap:georeference": {
#    "@type": "georeference:Georeference",
def create_group(as_list, group_name, node_path, parent_group, level, register=True):

    # create group
    if as_list:
        group = list()
        logging.debug(f'{" " * level * 3}add list {group_name}')  

    else:
        group = dict()
        group['@type'] = convert_path_to_namespace(node_path, False, get_schema_from_node_path(node_path))
        logging.debug(f'{" " * level * 3}add dict {group_name}')  

    if register:
        if isinstance(parent_group, list):
            parent_group.append(group)
        else:
            parent_group[group_name] = group
    return group


def find_node_path_in_shacles(node_path):
    name = convert_path_to_namespace(node_path)
    namespace, namespace_name = get_namespace(name)
    if namespace in config.SHACLS:
        shacl_graph = config.SHACLS[namespace]
        prefixes = shacl_graph['prefixes']
        shacl_dict = shacl_graph['dict']
        return namespace, shacl_dict, prefixes
    return None

def fill_content(node, node_path, node_path_name, schema_name, group, shacl_dict, prefixes, meta_data, level):

    # create properties group
    prop_group = create_group(False, node_path_name, node_path, group, level, False)

    # loop properties
    for properties in node:                     
        prop_name = getValue('name', properties, False)
        prop_node = getValue('node', properties, False, True)        
        if prop_node: # property has sub structure
            shacl_data = find_node_path_in_shacles(prop_node)
            if shacl_data is None:
                continue
            namespace_add, shacl_dict_add, prefixes_add = shacl_data
            if prop_node in shacl_dict_add:
                node = shacl_dict_add[prop_node]
                node_path_name = getValue('path', properties, False)
                node_path_name = convert_path_to_namespace(node_path_name, False, schema_name)
                isList_sub = is_list_property(properties)
                if node_path_name not in meta_data:
                    continue
                # create sub group and fill sub content
                meta_data_sub = meta_data[node_path_name]
                group_to_add = group
                if isinstance(group_to_add, list):
                    group_to_add = prop_group
                group_sub = create_group(isList_sub, node_path_name, prop_node, group_to_add, level)
                if isinstance(meta_data_sub, list):                    
                    for meta_sub_element in meta_data_sub:
                        name = convert_path_to_namespace(prop_node)
                        namespace, namespace_name = get_namespace(name)
                        fill_content(node, prop_node, node_path_name, namespace, group_sub, shacl_dict, prefixes, meta_sub_element, level+1)
                else:
                    fill_content(node, prop_node, node_path_name, schema_name, group_sub, shacl_dict, prefixes, meta_data_sub, level+1)

            else:
                if is_required_property(properties):
                    name = convert_path_to_namespace(prop_node)
                    namespace, namespace_name = get_namespace(name)
                    fill_properties_in_other_namespace(properties, prop_node, namespace, meta_data, level)
            continue

        if not create_property(properties, prefixes, meta_data, schema_name, group, prop_group, level):
            continue


    
    if isinstance(group, list):
        group.append(prop_group)

def create_property(properties, prefixes, meta_data, schema_name, group, prop_group, level):
    # property type
    prop_type = getValue('datatype', properties, False)
    if not prop_type:
        return False

    # create property and get data type
    data_type = None
    isList_prop = is_list_property(properties)
    if isList_prop:
        property = list()           
    else:
        property = dict()
        data_type = replace_namespace(prop_type, prefixes)
        if data_type == "xsd:anyURI":
            property = dict()       

    # prop_path
    prop_path = getValue('path', properties, False)
    prop_path = replace_namespace(prop_path, prefixes)        
    # set value
    data_from_metadata = get_data_from_metadata(prop_path, meta_data)
    if data_from_metadata is not None: # has data
        if isList_prop:
            for data_value in data_from_metadata:
                property.append(data_value)
        elif type(property) == dict:
            property['@value'] = str(data_from_metadata)
        else:
            property = data_from_metadata
    elif is_required_property(properties): # is required
        data_value = check_value_type(dataTypeMap[data_type]['default'], data_type)
        if isList_prop:
            property.append(data_value)    
        elif type(property) == dict:
            property['@value'] = str(data_value)
        else:
            property = data_value
    elif is_in_namespace(prop_path, schema_name): # not filled -> ignore
        #logging.warning(f'{prop_path} not found!!')
        return False
    else:
        return False   
    
    sh_in = get_property_value('in', properties)
    if data_type and not sh_in: # no type for enums!
        property['@type'] = data_type    

        # register
    if isinstance(group, list):
        logging.debug(f'{" "  * level * 3}add prop {prop_path}')
        prop_group[prop_path] = property
    else:
        logging.debug(f'{" " * level * 3}add prop {prop_path}')
        group[prop_path] = property    

    return True 

def fill_properties_in_other_namespace(node_properties, node_path, schema_namespace, meta_data, level):
    # then switch to specific shacle
    shacl_data = find_node_path_in_shacles(node_path)
    if shacl_data is None:
        return
    namespace, shacl_dict_add, prefixes_add = shacl_data
    group_name = convert_path_to_namespace(node_path, True, schema_namespace)
    if group_name in meta_data:
        # switch to subgraph
        meta_data_sub = meta_data[group_name]
        group_dict = create_group(False, group_name, node_path, config.JSON_OUT, level)
        schema_shape_add = shacl_dict_add[node_path]
        # loop properties in specific shacle
        for node_properties_add in schema_shape_add:
            node_path_add = getValue('node', node_properties_add, False)
            if node_path_add in shacl_dict_add:
                # check if node in meta data
                node_path_name = getValue('path', node_properties_add, False)
                node_path_name = convert_path_to_namespace(node_path_name, True, namespace)
                if node_path_name in meta_data_sub:
                    # create sub group and fill sub content
                    node = shacl_dict_add[node_path_add]
                    as_list_add = is_list_property(node_properties_add)
                    meta_data_sub_sub = meta_data_sub[node_path_name]
                    group = create_group(as_list_add, node_path_name, node_path_add, group_dict, level+1)
                    fill_content(node, node_path_add, node_path_name, namespace, group, shacl_dict_add, prefixes_add, meta_data_sub_sub, level+2)
                else:
                    if is_required_property(node_properties_add):
                        # create empty group
                        node = shacl_dict_add[node_path_add]
                        create_required_subgraph(node_properties_add, node_path, node_path_name, group_dict, schema_namespace, shacl_dict_add, namespace, prefixes_add, level+1)
                    #return # not filled in meta_data - ignore
        return # next node property from original shacl
    else:   
        if is_required_property(node_properties):                    
            node_path_name = getValue('path', node_properties, False)
            node_path_name = convert_path_to_namespace(node_path_name, True, schema_namespace)
            group = create_required_subgraph(node_properties, node_path, node_path_name, config.JSON_OUT, schema_namespace, shacl_dict_add, namespace, prefixes_add, level)

      
def create_required_subgraph(node_properties, node_path, node_path_name, group_dict, schema_namespace, shacl_dict_sub, namespace_sub, prefixes_sub, level):      
    as_list = is_list_property(node_properties)
    node_path_name = getValue('path', node_properties, False)
    node_path_name = convert_path_to_namespace(node_path_name, True, schema_namespace)
    # add group
    group = create_group(as_list, node_path_name, node_path, group_dict, level)  
    # add subgraph
    if node_path in shacl_dict_sub:
        schema_shape_add = shacl_dict_sub[node_path]
        for node_properties_add in schema_shape_add:
            if is_required_property(node_properties_add):  
                node_path_add = getValue('node', node_properties_add, False, True)
                if node_path_add is None:
                    create_property(node_properties_add, prefixes_sub, None, namespace_sub, group, group, level)
                else:
                    node_path_name_add = getValue('path', node_properties_add, False)
                    node_path_name_add = convert_path_to_namespace(node_path_name_add, True, namespace_sub)
                    create_required_subgraph(node_properties_add, node_path_add, node_path_name_add, group, namespace_sub, shacl_dict_sub, namespace_sub, prefixes_sub, level+1)

    # hack for georeference:GeodeticReferenceSystemShape to add sh:or georeference:coordinateSystemName   
    if node_path_name == "georeference:geodeticReferenceSystem":
        if 'georeference:coordinateSystemName' not in group:
            property = dict()
            property['@type'] = 'xsd:string'   
            property['@value'] = ''
            group['georeference:coordinateSystemName'] = property                
    return group


def fill_properties(meta_data, schema_namespace, schema_name):
    shacl_graph_data = config.SHACLS[schema_namespace]
    prefixes = shacl_graph_data['prefixes']
    shacl_dict = shacl_graph_data['dict']
    level = 0
    
    # find schema shape
    schema_node_name = f'{schema_name}shape'.lower()
    schema_shape = getValue(schema_node_name, shacl_dict, True)
    if not schema_shape:
        return
    
    # loop properties in shacle
    for node_properties in schema_shape:
        node_path = getValue('node', node_properties, False)
        if not node_path:
            continue # in main shacle groups should be only nodes 

        # if node not in current shacle
        if node_path not in shacl_dict:
            # then switch to specific shacle
            fill_properties_in_other_namespace(node_properties, node_path, schema_namespace, meta_data, level)
            continue
        else: # is in current shacle -> get node 
            node = shacl_dict[node_path]

        # check if node in meta data
        node_path_name = getValue('path', node_properties, False)
        node_path_name = convert_path_to_namespace(node_path_name, True, schema_namespace)
        if node_path_name in meta_data:
            # create sub group and fill sub content
            meta_data_sub = meta_data[node_path_name]
            as_list = is_list_property(node_properties)
            group = create_group(as_list, node_path_name, node_path, config.JSON_OUT, level)
            fill_content(node, node_path, node_path_name, schema_namespace, group, shacl_dict, prefixes, meta_data_sub, level+1)
        else:
            if is_required_property(node_properties):
                create_required_subgraph(node_properties, node_path, node_path_name, config.JSON_OUT, schema_namespace, shacl_dict, schema_namespace, prefixes, level)


def get_prefix_for_uri(uri, graph):
    for prefix, namespace in graph.namespace_manager.namespaces():
        # Überprüfe, ob die URI mit dem Namespace beginnt
        if uri.startswith(str(namespace)):
            return prefix
    return None


def get_uri_from_namespace(value):
    if "#" in value:
        uri = value.rsplit('#', 1)[0] + '#'
    else: 
        uri = value.split('#')[0].rsplit('/', 1)[0] + '/'
    return uri

def getPrefixes(shacl_graph):
            # collect mamespace prefix
        used_namespaces = set()
        for s, p, o in shacl_graph:
            #  check if subject, predicat, object is uri
            if isinstance(s, URIRef):
                used_namespaces.add(get_uri_from_namespace(s))
            if isinstance(p, URIRef):
                used_namespaces.add(get_uri_from_namespace(p))
            if isinstance(o, URIRef):
                used_namespaces.add(get_uri_from_namespace(o))

        prefixes = dict()
        for prefix, namespace in shacl_graph.namespace_manager.namespaces():
            uriStr = str(namespace)
            if uriStr in used_namespaces:
                prefix_str = get_prefix_for_uri(namespace, shacl_graph)
                prefixes[prefix_str] = namespace
        # add gx prefix
        prefixes["gx"] = Namespace("https://registry.lab.gaia-x.eu/development/api/trusted-shape-registry/v1/shapes/jsonld/trustframework#")              
        return prefixes

def fill_claim_data(schema_namespace, schema_name, meta_data, user_did: str):
    config.JSON_OUT = defaultdict(list)
    # get shacl for asset
    if schema_namespace in config.SHACLS:        

        shacl_graph_data = config.SHACLS[schema_namespace]

        config.JSON_OUT['@context'] = shacl_graph_data['prefixes']
        
        # add id and type
        config.JSON_OUT['@id'] = f'did:web:envited.register.market:{schema_namespace}:{user_did}'
        config.JSON_OUT['@type'] = f'{schema_namespace}:{schema_name}'

        # fill properties for asset shacle
        fill_properties(meta_data, schema_namespace, schema_name)
    else:
        logging.error(f'Cannot find ontology {schema_namespace}')
    
    return

def convert_graph_to_dict(graph):
    graph_dict = {}
    for node_shape in graph.subjects(RDF.type, SH.NodeShape):

        prop_list = []
        for prop in graph.objects(node_shape, SH.property):    

            values_dict = {}
            for detail, value in graph.predicate_objects(prop):
                values_dict[str(detail)] = str(value)

            prop_list.append(values_dict)
        graph_dict[str(node_shape)] = prop_list

    return graph_dict

def download_shacle(url_path : str, shacle_name: str) -> str:
    filename = f'{shacle_name}_shacl.ttl'
    subfolder = 'shacles'    
    local_file_path = f'{subfolder}/{filename}'

    if not Path(local_file_path).exists():
        # get file from github
        url = f'{url_path}{filename}'
        response = requests.get(url)
        if not response:
            logging.error(f'No shacl files found in url: {url}')
            exit(1)

        if not Path(subfolder).exists():
            Path(subfolder).mkdir()
        with open(local_file_path, 'wb') as file:
            file.write(response.content) 

    return local_file_path


def handle_shacles(url_path : str, shacle_name: str, shacls):

    local_file_path = download_shacle(url_path, shacle_name)

    try:
        graph = Graph()
        graph.parse(local_file_path, format='turtle')
        
        graph_data = {}
        graph_data['graph'] = graph
        graph_data['dict'] = convert_graph_to_dict(graph)        
        graph_data['prefixes'] = getPrefixes(graph)

        shacls[shacle_name] = graph_data
    except:
        logging.exception(f'cannot read turtle file: {local_file_path}')
        exit(1)

def main():
    parser = argparse.ArgumentParser(prog='main.py', description='creates a jsonLD from an attribute table of the meta data extractors')
    parser.add_argument('filename', type=str,help='filename of json attribute table.')
    parser.add_argument('-ontology', type=str,help='githup path to ontologies')
    parser.add_argument('-out', type=str, help='output filname for json LD file.')
    parser.add_argument('-did', type=str, help='user did.')
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
    handle_shacles(url_path, shacle_namespace, shacl_definitions)

    # get gaia x prefixes
    gaiax_url = 'https://github.com/GAIA-X4PLC-AAD/ontology-management-base/tree/main/'
    shacl_data = shacl_definitions[shacle_namespace]
    prefixes = {prefix: str(namespace) for prefix, namespace in shacl_data['graph'].namespace_manager.namespaces() if str(namespace).startswith(gaiax_url)}

    # and download additional shacles
    for key, value in prefixes.items():
        if key not in shacl_definitions:
            new_url_path = value.replace(gaiax_url, ontology_path)
            handle_shacles(new_url_path, key, shacl_definitions)
    config.SHACLS = shacl_definitions
    
    # fill data in shacle structure
    user_did = args.did
    try:
        fill_claim_data(shacle_namespace, shacle_name, claim_data, user_did)
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