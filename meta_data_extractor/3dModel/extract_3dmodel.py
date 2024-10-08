from typing import Tuple
from pathlib import Path
import json

import logging


def get_meta_data(file_data: dict, attributes: dict):
    if 'project' in file_data:
        project_dict = dict()
        project_dict['environment-model:creationSource'] = file_data['project']['creation_source']
        project_dict['environment-model:creationVersion'] = file_data['project']['creation_version']
        attributes['environment-model:project'] = project_dict

    
    if 'data' in file_data:
        format_dict = dict()
        format_dict['environment-model:formatType'] = file_data['data']['format']
        attributes['environment-model:format'] = format_dict

    if 'quantity' in file_data:
        quantity_dict = dict()
        quantity_dict['environment-model:geometryCount'] = file_data['quantity']['geometry_count']
        quantity_dict['environment-model:triangleCount'] = file_data['quantity']['triangle_count']
        quantity_dict['environment-model:textureMaterialCount'] = file_data['quantity']['texture_material_count']
        attributes['environment-model:quantity'] = quantity_dict


def extract_meta_data(file: Path) ->Tuple[bool, dict]:

    # read json file 
    logging.debug(f'Loading input file {file.absolute()}')
    try: 
        with open(file, 'r') as f:
            file_data = json.load(f)
    except:
        logging.exception(f'Cannot read json file {file.absolute()}')
        return False
        
    # ask in file dialog for file with given file extension -->close program if interrupted
    try:
        attributes = dict()
        get_meta_data(file_data, attributes)
    except:
        logging.exception(f'Cannot extract from file {file.absolute()}')
        return False
    
    data = {}
    data['shacle_type'] = f'{get_namespace()}:{get_schema_name()}'
    data[f'{get_namespace()}:{get_schema_name().lower()}'] = attributes
    
    logging.info(f'Extract from file {file}')
    return True, data
    
def get_description() -> str:
    return 'extract 3Dmodel statistic file from Trian3DBuilder'

def get_schema_name() -> str:
    return 'environmentModel'

def get_namespace() -> str:
    return 'environment-model'