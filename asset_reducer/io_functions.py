from lxml import etree
from pathlib import Path
import json
import pickle

# mapping table
def load_mapping_table(mapping_file):
    if not Path(mapping_file).exists():
        print(f"file '{mapping_file}' not exist.")
        return None
    with open(mapping_file, 'r') as f:
        node_mapping = json.load(f)
    return node_mapping

# io functions for JSON 
def save_json(data, file_name, binary):
    if binary:
        with open(file_name, 'wb') as f:
            pickle.dump(data, f)
    else:
        with open(file_name, 'w') as f:
            json.dump(data, f, indent=4)

def read_json_file(file_path, binary):
    if binary:
        with open(file_path, 'rb') as f:
            json_data = pickle.load(f)
    else:
        with open(file_path, 'r') as file:
            json_data_binary = file.read()
            json_data = json.loads(json_data_binary)
    return json_data   

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