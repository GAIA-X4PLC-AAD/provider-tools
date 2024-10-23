#import debugpy

# debugpy, listening on port 5678
#debugpy.listen(("0.0.0.0", 5678))
#print("Waiting for debugger to attach...")

#debugpy.wait_for_client()

#debugpy.breakpoint()


from datetime import datetime
from rdflib.namespace import SH, RDF
from rdflib import Graph, URIRef
from collections import defaultdict
from pathlib import Path
from pyshacl import validate

import glob
import sys
import json
import logging
import argparse
import requests

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')


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
    if namespace:
        last_parts[0] = namespace
    separator = ':'
    namespace = separator.join(last_parts)
    if as_node_name:
        namespace = namespace.lower()
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
        logging.warning(f'{name} not found!!')

    return None


def get_data_from_metadata(path, meta_data):
    if path in meta_data:           
        #if check_data_type(meta_data[path], type_string_simple, name):
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


def create_group(as_list, node_path_name, node_path, schema_name, json_dict, level, register=True):
    if 'hdmap:georeference' == node_path_name:
        found = True
    # create group
    if as_list:
        group = list()
        logging.debug(f'{" " * level * 3}add list {node_path_name}')  

    else:
        group = dict()
        group['@type'] = convert_path_to_namespace(node_path, False, schema_name)
        logging.debug(f'{" " * level * 3}add dict {node_path_name}')  

    if register:
        json_dict[node_path_name] = group
    return group


def fill_content(node, node_path, node_path_name, schema_name, group, shacl_dict, prefixes, meta_data, level):

    # create properties group
    prop_group = create_group(False, node_path_name, node_path, schema_name, group, level, False)

    # loop properties
    for properties in node:                     
        prop_name = getValue('name', properties, False)
        prop_node = getValue('node', properties, False, True)        
        if prop_node: # property has sub structure
            if prop_node in shacl_dict:
                node = shacl_dict[prop_node]
                node_path_name = getValue('path', properties, False)
                node_path_name = convert_path_to_namespace(node_path_name, True, schema_name)
                isList_sub = is_list_property(properties)
                if node_path_name not in meta_data:
                    continue
                # create sub group and fill sub content
                meta_data_sub = meta_data[node_path_name]
                group_sub = create_group(isList_sub, node_path_name, prop_node, schema_name, group, level)
                if isinstance(meta_data_sub, list):                    
                    for meta_sub_element in meta_data_sub:
                        fill_content(node, prop_node, node_path_name, schema_name, group_sub, shacl_dict, prefixes, meta_sub_element, level+1)
                else:
                    fill_content(node, prop_node, node_path_name, schema_name, group_sub, shacl_dict, prefixes, meta_data_sub, level+1)

            else:
                logging.warning(f'{prop_node} not found in shacle {schema_name} !!')
                stop = True # TODO search in other shacls
            continue

        prop_type = getValue('datatype', properties, False)
        if not prop_type:
            continue

        # create property
        isList_prop = is_list_property(properties)
        if isList_prop:
            property = list()           
        else:
            property = dict()           
            data_type = replace_namespace(prop_type, prefixes)
            property['@type'] = data_type                            
        prop_path = getValue('path', properties, False)
        prop_path = replace_namespace(prop_path, prefixes)

        # set value
        data_from_metadata = get_data_from_metadata(prop_path, meta_data)
        if data_from_metadata is not None: # has data
            if isList_prop:
                for data_value in data_from_metadata:
                    property.append(data_value)
            else:
                property['@value'] = data_from_metadata
        elif is_required_property(properties): # is required
            data_value = check_value_type(dataTypeMap[data_type]['default'], data_type)
            if isList_prop:
                property.append(data_value)    
            else:
                property['@value'] = data_value
        elif is_in_namespace(prop_path, schema_name): # not filled -> ignore
            logging.warning(f'{prop_path} not found!!')
            continue
        else:
            continue
        
        # register
        if isinstance(group, list):
            logging.debug(f'{" "  * level * 3}add prop {prop_path}')
            prop_group[prop_path.lower()] = property
        else:
            logging.debug(f'{" " * level * 3}add prop {prop_path}')
            group[prop_path.lower()] = property
    
    if isinstance(group, list):
        group.append(prop_group)


def fill_properties(json_dict, meta_data, schema_namespace, schema_name, shacls):
    shacl_graph_data = shacls[schema_namespace]
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
            name = convert_path_to_namespace(node_path)
            namespace, namespace_name = get_namespace(name)
            if namespace in shacls:
                shacl_graph_add = shacls[namespace]
                prefixes_add = shacl_graph_add['prefixes']
                shacl_dict_add = shacl_graph_add['dict']
                if node_path in shacl_dict_add:
                    # if node_path in metadata
                    group_name = convert_path_to_namespace(node_path, True, schema_namespace)
                    if group_name in meta_data:
                        # switch to subgraph
                        meta_data_sub = meta_data[group_name]
                        group_dict = create_group(False, group_name, node_path, None, json_dict, level)
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
                                    group = create_group(as_list_add, node_path_name, node_path_add, namespace, group_dict, level+1)
                                    fill_content(node, node_path_add, node_path_name, namespace, group, shacl_dict_add, prefixes_add, meta_data_sub_sub, level+2)
                                else:
                                    continue # not filled in meta_data - ignore
                        continue # next node property from original shacl
                    else:
                        continue
                else:
                    continue
            else:
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
            group = create_group(as_list, node_path_name, node_path, schema_name.lower(), json_dict, level)
            fill_content(node, node_path, node_path_name, schema_namespace, group, shacl_dict, prefixes, meta_data_sub, level+1)
        else:
            continue # not extracted - ignore


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
        return prefixes

def fill_claim_data(schema_namespace, schema_name, shacls, meta_data, user_did: str):
    json_dict = defaultdict(list)
    # get shacl for asset
    if schema_namespace in shacls:        

        shacl_graph_data = shacls[schema_namespace]

        json_dict['@context'] = shacl_graph_data['prefixes']
        
        # add id and type
        json_dict['@id'] = f'did:web:envited.register.market:{schema_namespace}:{user_did}'
        json_dict['@type'] = f'{schema_namespace}:{schema_name}'

        # fill properties for asset shacle
        fill_properties(json_dict, meta_data, schema_namespace, schema_name, shacls)
    else:
        logging.error(f'Cannot find ontology {schema_namespace}')
    
    return json_dict

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


def download_shacles(url_path : str, shacle_name: str, shacls):

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

    try:
        graph = Graph()
        graph.parse(local_file_path, format='turtle')
        graph_data = {}
        graph_data['graph'] = graph
        graph_data['dict'] = convert_graph_to_dict(graph)
        # debug TODO
        #with open('test.json', 'w') as f:
        #    json.dump(graph_data['dict'], f, indent=4, default=datetime_handler)
        graph_data['prefixes'] = getPrefixes(graph)
        shacls[shacle_name] = graph_data
    except:
        logging.exception(f'cannot read turtle file: {local_file_path}')
        exit(1) 

def load_shacl_files(root_dir):
    shacl_graph = Graph()
    shacl_files = sorted(root_dir.glob('*_shacl.ttl'))
    #shacl_files = glob.glob(f'{root_dir}/**/*_shacl.ttl', recursive=True)
    for shacl_file in shacl_files:
        shacl_graph.parse(shacl_file, format='turtle')
    return shacl_graph


def load_jsonld_file(jsonld_file : Path):
    data_graph = Graph()
    print(f'adding jsonld file to data graph: {jsonld_file}.')
    with open(jsonld_file) as f:
        data = json.load(f)
    data_graph.parse(data=json.dumps(data), format='json-ld')
    return data_graph


def validate_jsonld_against_shacl(data_graph : Graph, shacl_graph : Graph):
    conforms, v_graph, v_text = validate(data_graph, shacl_graph=shacl_graph, data_graph_format='json-ld', inference='rdfs', debug=False)
    print(f'Conforms: {conforms}')
    if not conforms:
        print('####### Validation errors: #######')
        print(v_text)
        print('')
        print('####### Validation graph: #######')
        print(v_graph.serialize(format='turtle'))
        sys.exit(400)        

def validate_jsonld(jsonld_file: Path, shacle_path : Path):
    # load all jsonld files into the graph since they might reference each other
    data_graph = load_jsonld_file(jsonld_file)
    shacl_graph = load_shacl_files(shacle_path)

    validate_jsonld_against_shacl(data_graph, shacl_graph)

def main():
    parser = argparse.ArgumentParser(prog='main.py', description='creates a jsonLD from an attribute table of the meta data extractors')
    parser.add_argument('filename', type=str,help='filename of json attribute table.')
    parser.add_argument('-ontology', type=str,help='githup path to ontologies')
    parser.add_argument('-out', type=str, help='output filname for json LD file.')
    parser.add_argument('-did', type=str, help='user did.')
    args = parser.parse_args()

    # read attribute data
    claim_path = Path(args.filename)
    if not claim_path.exists():
        logging.exception(f'Could not find file {claim_path}')
        exit(1)
    with open(claim_path, 'r', encoding='utf-8') as file:
        claim_data = json.load(file)

    # download shacle file    
    shacle_namespace, shacle_name = get_namespace(claim_data['shacle_type'])
    ontology_path = args.ontology + '/'
    shacl_definitions = {}
    url_path = f'{ontology_path}{shacle_namespace}/'
    download_shacles(url_path, shacle_namespace, shacl_definitions)

    # get gaia x prefixes
    gaiax_url = 'https://github.com/GAIA-X4PLC-AAD/ontology-management-base/tree/main/'
    shacl_data = shacl_definitions[shacle_namespace]
    prefixes = {prefix: str(namespace) for prefix, namespace in shacl_data['graph'].namespace_manager.namespaces() 
        if str(namespace).startswith(gaiax_url)}
    # and download additional shacles
    for key, value in prefixes.items():
        if key not in shacl_definitions:
            new_url_path = value.replace(gaiax_url, ontology_path)
            download_shacles(new_url_path, key, shacl_definitions)
    
    # fill data in shacle structure
    user_did = args.did
    try:
        json_dict = fill_claim_data(shacle_namespace, shacle_name, shacl_definitions, claim_data, user_did)
    except:
        logging.exception(f'Could not convert to json')
        exit(1)
        
    # write claims as json id to output    
    output_path = Path(args.out)
    with open(output_path, 'w') as f:
        json.dump(json_dict, f, indent=4, default=datetime_handler)
        logging.info(f'write json ld to {output_path}')

    # validate
    validate_jsonld(output_path, Path(__file__).parent.resolve() / 'shacles')

if __name__ == '__main__':
    main()