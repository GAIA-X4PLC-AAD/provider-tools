from pathlib import Path
from datetime import datetime

import logging
import os
import json
from geopy.geocoders import Nominatim
from pyproj import CRS, Transformer


def get_position_from_osm(data_dict, latitude, longitude):
    # custom User-Agent
    custom_user_agent = "GaiaX_ODR_Extractor/1.0"
    # Initialize Nominatim geocoder    
    geolocator = Nominatim(user_agent=custom_user_agent)
    # Reverse geocoding: find address based on coordinates
    location = geolocator.reverse((latitude, longitude), exactly_one=True)
    # Extract the desired information
    address = location.raw['address']
    data_dict['georeference:country'] = address.get('country', '')
    data_dict['georeference:state'] = address.get('state', '')
    #data_dict['postcode'] = address.get('postcode', '')
    data_dict['georeference:region'] = address.get('county', '')
    data_dict['georeference:city'] = address.get('city', address.get('town', address.get('village', '')))


def proj4_to_epsg(proj4_string):
    # create a CRS-Object from Proj4-String
    crs = CRS.from_proj4(proj4_string)
    # get EPSG-Code
    epsg_code = crs.to_epsg()
    return epsg_code


def convert_to_LatLon(x, y, proj4):
    transformer = Transformer.from_proj(proj4, 'epsg:4326')  # WGS84
    lon, lat = transformer.transform(x, y)
    return lon, lat


def datetime_handler(x):
    if isinstance(x, datetime.datetime):
        return x.isoformat()
    raise TypeError("Unknown type")


def extract(file: Path, output_file: Path) -> bool:   
    file = file.expanduser()
    file = file.resolve()
    
    # check folder with extension
    extension = file.suffix.lstrip('.')
    logging.info(extension)
    format_path = Path(__file__).parent / f'{extension}'
    if not format_path.exists() or not format_path.is_dir():
        logging.error(f'Provided format path does not exist or is not a file: {format_path.absolute()}')
        return False
    
    # import python script from subfolder
    files = [extrator_file for extrator_file in format_path.iterdir() if extrator_file.name.endswith('.py') and extrator_file.name != '__init__.py' and extrator_file.name.startswith('extract_')]
    if len(files) == 0:
        return False
    module_name = Path(files[0]).relative_to(Path(__file__).parent).as_posix().replace('/', '.').replace('.py', '')
    required_functions = ['extract_meta_data', 'get_description', 'get_schema_name', 'get_namespace']
    logging.debug(f'Loading extractor {{{module_name}}}')
    try:
        extract_module = __import__(module_name, fromlist=required_functions)
    except:
        logging.exception(f'Could not load extract file {module_name}')
        return False
    
    # check required functions    
    missing_function = False
    for function in required_functions:
        if not hasattr(extract_module, function):    
            logging.error(f'{module_name} has no requried function {function}')
            missing_function = True
            break
    if missing_function: 
        return False      

    # call extract and get filled attributes
    try:
        valid, meta_data = extract_module.extract_meta_data(file)
        if valid is False:
            return valid        
    except:
        logging.exception(f'Could not extract format {extract_module.get_description()}')
        return False     

    with open(output_file, 'w') as f:
        json.dump(meta_data, f, indent=4, default=datetime_handler)
        logging.info(f'write json to {output_file}')
   
    return True