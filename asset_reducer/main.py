from lxml import etree
from pathlib import Path

import argparse
import logging
import json
import pickle

logger = logging.getLogger(__name__)


################ reduce functions ########################
def calcExtrema(element, nodename):
    if element is None:
        return None
    
    min_value = float('inf')
    max_value = float('-inf')
    
    children = element.findall(nodename)
    if not children:
        return {}
    
    for child in children:
        value = float(child.get('a', 0))
        if value < min_value:
            min_value = value
        if value > max_value:
            max_value = value
    return {'min': min_value, 'max': max_value}


# reduce xml to json functions
def extract_attributes(element, attributes):
    #return {attr: element.get(attr) for attr in attributes if element.get(attr) is not None}
    attres = {}
    for attr in attributes:
        element_attr = element.get(attr)
        if element_attr is not None:
            attres[attr] = element_attr
    return attres


def process_element(element, mapping):
    tag = element.tag
    node_data = {}
        
    # extract attributes
    tag_exist = False
    if tag in mapping:
        tag_exist = True
        tag_mapping = mapping[tag]
        if "attributes" in tag_mapping:
            attres = extract_attributes(element, tag_mapping["attributes"])
            node_data.update(attres)
        if "function" in tag_mapping:
            func_name = tag_mapping['function']
            if func_name[0] == 'calcExtrema':
                values = calcExtrema(element, func_name[1])
                if values:
                    node_data.update(values)

    # traverse children
    children = list(element)
    if children:
        for child in children:
            child_data = process_element(child, mapping)
            if child_data:
                for key, value in child_data.items():
                    if key not in node_data:
                        node_data[key] = []
                    node_data[key].append(value)
    
    if tag == "geoReference" and element.getparent().tag == "header":
        node_data.update({'proj4_str': element.text})  
    
    if node_data or tag_exist: #tag_exist aber node_data is empty
        return {tag: node_data}
    else:
        return None     
    

def read_json_file(file_path, binary):
    if binary:
        with open(file_path, 'rb') as f:
            json_data = pickle.load(f)
    else:
        with open(file_path, 'r') as file:
            json_data_binary = file.read()
            json_data = json.loads(json_data_binary)
    return json_data       


# mapping table
def load_mapping_table(mapping_file):
    if not Path(mapping_file).exists():
        logger.info(f"file '{mapping_file}' not exist.")
        return None
    with open(mapping_file, 'r') as f:
        node_mapping = json.load(f)
    return node_mapping


def json_to_xml_add_attributes_and_children(parent, data):
    for key, value in data.items():
        if isinstance(value, dict):
            child = etree.SubElement(parent, key)
            json_to_xml_add_attributes_and_children(child, value)
        elif isinstance(value, list):
            json_to_xml_handle_list(parent, key, value)
        else:
            parent.set(key, str(value))


def json_to_xml_handle_list(parent, key, data_list):
    for item in data_list:
        element = etree.SubElement(parent, key)
        if isinstance(item, dict):
            json_to_xml_add_attributes_and_children(element, item)
        else:
            element.text = str(item)


def json_to_xml(json_data):
    root = etree.Element("OpenDRIVE")

    for item in json_data:
        for key, value in item.items():
            element = etree.SubElement(root, key)
            if isinstance(value, dict):
                json_to_xml_add_attributes_and_children(element, value)
            elif isinstance(value, list):
                json_to_xml_handle_list(element, key, value)
            else:
                element.text = str(value)

    return root


# io functions for JSON 
def save_json(data, file_name, binary):
    if binary:
        with open(file_name, 'wb') as f:
            pickle.dump(data, f)
    else:
        with open(file_name, 'w') as f:
            json.dump(data, f, indent=4)
  

def main():
    parser = argparse.ArgumentParser(prog='main.py', description='reduces the original xml to relevant nodes and attributes (see mapping_tables) and writes a binary json for the extended search.')   
    parser.add_argument('filename', type=str,help='filename of asset in xml format.')
    parser.add_argument('-out', type=str, help='output filname for reduced file.')
    args = parser.parse_args()

    # Path to the XML file
    xml_file_path = Path(args.filename)
    if not xml_file_path.exists():
        logger.error(f'json file {xml_file_path} not exists')
        exit(1)

    # Target JSON file
    output_json_file = Path(args.out)
    output_json_path = output_json_file.parent
    if not output_json_path.exists():
        output_json_path.mkdir(parents=True, exist_ok=True)

    # read mapping table
    asset_type = xml_file_path.suffix.lstrip('.') # Get file extension without the dot
    mapping_name = f'mapping_tables/mapping_{asset_type}.json'
    script_dir = Path(__file__).parent.resolve()
    mapping_file = script_dir / mapping_name
    node_mapping = load_mapping_table(mapping_file)
    if not node_mapping:
        exit(1)

    # read xml 
    tree = etree.parse(xml_file_path)
    root = tree.getroot()
    
    # convert to json dictonary
    json_data = []
    for child in root:
        result = process_element(child, node_mapping)
        if result:
            json_data.append(result)

    # write to json file
    save_json(json_data, output_json_file, True)

    # test to read json, convert to xml and find nodes
    debug = False
    if debug:
        # read json
        binary = False
        json_read_data = read_json_file(output_json_file, binary)
        # convert to xml
        root_read = json_to_xml(json_read_data)
        
        # write as xml
        xml_str = etree.tostring(root_read, pretty_print=True, encoding='utf-8', xml_declaration=True)
        with open(output_json_file, "wb") as f:
            f.write(xml_str)
        
        #find node
        header = root_read.find('./header')
        if header is not None:
            logger.info('header found')
        
        
if __name__ == '__main__':
    main()