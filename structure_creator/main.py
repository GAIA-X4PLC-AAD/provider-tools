from pathlib import Path
from urllib.parse import urlparse

import argparse
import json
import shutil
import logging
import os
import requests

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

# "assetData" "documentation" "visualization" "metadata" "validation" "license" "other"
categories = {
    "assetData" : [
        {
            "type" : "Asset",
            "extensions" : ["xodr", "xosc", "zip", "crg"],
            "folder" : "data",
            'mask' : '{name}',
            'role' : 'owner'
        }
    ],
    "documentation" : [
        {
            "type" : "Document",
            "extensions" : ["pdf", "txt", "md"],
            "folder" : "documentation",
            'mask' : '{name}_{file}',
            'role' : 'publicUser'
        }
    ],   
    "visualization" : [
        {
            "type" : "Image",
            "extensions" : ["png", "jpeg"],
            "folder" : "visualization",
            'mask' : '{name}_impression-{number}',
            'role' : 'publicUser'
        },
        {
            "type" : "Video",
            "extensions" : ["mp4"],
            "folder" : "visualization",
            'mask' : '{name}',
            'role' : 'publicUser'
        },
        {
            "type" : "3DPreview",
            "extensions" : ["json"],
            "folder" : "visualization/3d_preview",
            'mask' : '{name}',
            'role' : 'publicUser'
        },
        {
            "type" : "Routing",
            "extensions" : ["geojson"],
            "folder" : "visualization",
            'mask' : '',
            'role' : 'publicUser'
        }
    ],      
    "metadata" : [
        {
            "type" : "MetaData",
            "extensions" : ["json"],
            "folder" : "metadata",
            'mask' : 'domain_metadata',
            'role' : 'publicUser'
        }
    ],   
    "validation" : [
        {
            "type" : "Validation",
            "extensions" : ["xqar", "txt"],
            "folder" : "validation",
            'mask' : '',
            'role' : 'publicUser'
        }
    ],
    "license" : [
        {
            "type" : "License",
            "extensions" : ["", "txt", "md"],
            'folder' : '../',
            'mask' : 'LICENSE',
            'role' : 'publicUser'
        }
    ],       
    "other" : [
        {
            "type" : "Service",
            "extensions" : ["bjson"],
            "folder" : "data",
            'mask' : '{name}',
            'role' : 'registeredUser'
        }
    ]            
}

asset_type = {
    'xodr' : {
        'type' : 'HD-Map',
        'classname' : 'hdmap',
        'link' : 'hd-map-asset-example'
    },
    'xosc' : {
        'type' : 'Scenario',
        'classname' : 'scenario',
        'link' : 'scenario-asset-example'
    },
    'zip' : {
        'type' : 'environment-model',
        'classname' : 'environment-model',
        'link' : 'environment-model-asset-example'
    },
    'crg' : {
        'type' : 'surface-model',
        'classname' : 'surface-model',
        'link' : 'surface-model-asset-example'
    }
}

def get_data_from_category_type(category, type):
    if category in categories:
        found_category = categories[category]
        for data in found_category:
            if data["type"] == type:
                return data
    return None

def get_data_from_folder_extension(folder, extension):
    for key, category in categories.items():
        for data in category:
            if folder in data["folder"]:
                for ext in data["extensions"]:
                    if extension == ext:
                        return data, key
    return None, None


def get_file_data_from_category(file: Path)-> dict:
    extension = file.suffix.lstrip('.') # Get file extension without the dot
    folder = file.parent.name

    data, key = get_data_from_folder_extension(folder, extension)
    if data:
        data["category"] = key
        return data
    
    return None


def get_file_data(user_data, filename: Path) -> dict:
    for file in user_data:
        if file['filename'] == filename:
            return file
    return None

def create_file_data(filename: Path, abs_data_path: Path, data_type: str, role: str):
    file_data = {}
    file_data['manifest:accessRole'] = role
    file_data['manifest:type'] = data_type
    file_meta_data = dict()
    file_data['manifest:fileMetaData'] =  file_meta_data
    file_is_url = is_url(str(filename))
    if file_is_url:
        file_meta_data['manifest:uri'] = filename           
    else:        
        relative_path = filename.relative_to(abs_data_path)
        file_meta_data['manifest:uri'] = "./" + relative_path.as_posix()
        file_meta_data['manifest:filename'] = relative_path.name
        if os.path.exists(filename):
            file_meta_data['manifest:fileSize'] =  os.path.getsize(filename.as_posix())           
    
    return file_data


def register_asset(data: dict, filename: Path, abs_data_path: Path, category: str, role: str, data_type: str):
    files = []   
    files.append(create_file_data(filename, abs_data_path, category, role))
    
    if data_type in data:
        data[data_type].extend(files)
    else:
        data[data_type] = files


def register_folder(data: dict, user_data: dict, path: Path, abs_data_path: Path):
    if not path.exists():
        return
    
    for filename in path.rglob("*"):
        if filename.is_dir():
            continue
        
        file_data = get_file_data_from_category(filename) # add from scripts
        if not file_data:
            return

        category = file_data["category"]
        role = file_data['role']
        if category == 'assetData':
            data_type = f'manifest:{category}'
        else:
            data_type = 'manifest:contentData'

        # add to json data
        file_entry = create_file_data(filename, abs_data_path, category, role)
        if data_type not in data:
            data[data_type] = []
        data[data_type].append(file_entry)

def fill_mask(filename: Path, file_data : dict, index : int) -> Path:
    mask = file_data["mask"]
    if file_data["type"] == 'Document' and filename.suffix == '.pdf' and not filename.stem.endswith("_Documentation"):
        mask = mask + '_Documentation'
    return mask

def create_filename(filename: Path, asset_name: Path, file_data : dict, index : int) -> Path:
    basename = str(filename.stem)  # Name without extension

    mask = fill_mask(filename, file_data, index)

    if "{name}" in mask and "{file}" in mask:
        common_prefix  = os.path.commonprefix([basename, asset_name])
        basename = basename[len(common_prefix):]
    mask = mask.replace(r"{name}", asset_name)
    mask = mask.replace(r"{file}", basename)
    
    basename = mask.replace(r"{number}", str(index).zfill(2))
    extension = filename.suffix

    filename_new = f"{basename}{extension}"
    return Path(filename_new)

def is_url(string):
    parsed = urlparse(string)
    # A URL usually has a scheme (e.g. “http”, “https”) and a “netloc” (e.g. “www.example.com”)
    return all([parsed.scheme, parsed.netloc])


def update_readme(file_path_in: Path, file_path_out: Path, name_value: str, description_value: str) -> None:
    # Read the entire content of the file using UTF-8 encoding
    content = file_path_in.read_text(encoding="utf-8")
    
    # Replace the placeholders with the given values
    content = content.replace("< general:description:name >", name_value)
    content = content.replace("< general:description:description >", description_value)
    
    # Write the updated content back to the file using UTF-8 encoding
    file_path_out.write_text(content, encoding="utf-8")


def download_readme(readme_url : str, filename_target : str) -> str:
    # get file from github
    response = requests.get(readme_url)
    if response.status_code == 200:
        content = response.text
        with open(filename_target, "w", encoding="utf-8") as file:
            file.write(content)
    else:
        logging.error(f'No readme files found in url: {readme_url}')
        exit(1)

def safe_get(d, keys, default=None):
    """
    Helper function to safely retrieve nested keys from a dictionary.
    
    :param d: The dictionary to extract the value from.
    :param keys: A list of keys representing the path to the desired value.
    :param default: The value to return if a key in the path does not exist.
    :return: The value found at the end of the key path, or default if any key is missing.
    """
    for key in keys:
        try:
            d = d[key]
        except (KeyError, TypeError):
            return default
    return d


def get_name_description_from_domainMetadata(filename, type):
    with open(filename, "r", encoding="utf-8") as file:
        data = json.load(file)

    name = safe_get(data, [f"{type}:general", "general:description", "general:name", "@value"])
    if not name:
        logging.error(f'name : {name}:general not exists in {filename}')
    description = safe_get(data, [f"{type}:general", "general:description", "general:description", "@value"])
    if not description:
        logging.error(f'description: {name}:general not exists in {filename}')

    return name, description

def get_asset(user_data):
    for file in user_data:
        if file['category'] == 'assetData' and file['type'] == 'Asset':
            asset_name = Path(file['filename'])            
            asset_extension = asset_name.suffix.lstrip('.')
            asset_name = asset_name.stem
            return asset_name, asset_extension
    return None, None


def main():
    parser = argparse.ArgumentParser(prog='main.py', description='the folder structure is completed from the user info and a metadata table is created for the manifest')   
    parser.add_argument('filename', help='filename of json file from frontend.')
    parser.add_argument('-out', help='json file for manifest.')
    parser.add_argument('-path', help='path to copy/parse data.')
    args = parser.parse_args()

    user_input_file = Path(args.filename)
    data_path = Path(args.path)
    filename_out = Path(args.out)

    if not user_input_file.is_absolute():
        user_input_file = user_input_file.resolve()
    if not user_input_file.exists():
        logging.error(f'json file {user_input_file} not exists')
        exit(1)

    if not data_path.is_absolute():
        data_path = data_path.resolve()
    if not data_path.exists():
        logging.error(f'data path {data_path} not exists')
        exit(1)

    # read json
    with open(user_input_file, 'r') as file:
        user_data = json.load(file)

    # initialize asset_name
    asset_name, asset_extension = get_asset(user_data)
    if not asset_name or not asset_extension:
        logging.error(f'no asset found in {file}')
        exit(1)

    # copy files
    upload_folder = user_input_file.parent
    indexImage = 1
    for file in user_data:
        filename = Path(file['filename'])

        # get cat, type data
        category = file['category']
        typ = file['type']
        cat_type_data = get_data_from_category_type(category, typ)
        if not cat_type_data:
            logging.error(f'type {typ} not found in category {category}')
            exit(1)

        # get dest name
        dest_name = filename.name
        dest_name = create_filename(Path(dest_name), asset_name, cat_type_data, indexImage)        
        if category == "visualization" and typ == 'Image':
            indexImage = indexImage + 1 # increase image index for image mask

        # destination filename
        dest = Path(data_path / cat_type_data["folder"])
        if not dest.exists():
            dest.mkdir()
        dest = dest /  dest_name    
        dest = dest.resolve()    
        # source filename
        source = upload_folder / filename
        source = source.resolve()
        # copy
        shutil.copy(source, dest)

    # create json file for jsonLD creator
    data = {}
    data['shacle_type'] = 'manifest:Manifest'
    data_group = {}
    data['manifest:data'] = data_group
    for sub_folder in data_path.iterdir():
        relative_path = str(sub_folder.relative_to(data_path))
        if relative_path == 'temp':
            continue
        register_folder(data_group, user_data, sub_folder, data_path)

    # register license
    # TODO get license from file or userinput link/type
    license_file = 'https://www.mozilla.org/en-US/MPL/2.0/'
    if license_file is not None:
        licence_group = {}
        licence_group['manifest:spdxIdentifier'] = 'MPL-2.0'
        
        data['manifest:license'] = licence_group
        register_asset(licence_group, license_file, data_path, 'license', 'publicUser', 'manifest:licenseData')
        


    path = filename_out.parent    
    if not path.exists():
        path.mkdir()

    # create readme
    url = "https://raw.githubusercontent.com/GAIA-X4PLC-AAD/ontology-management-base/main/manifest/README.md"
    script_path = Path(__file__).resolve()
    readme_template = script_path.parent / 'README_template.md'
    download_readme(url, readme_template)
    if asset_extension in asset_type:
        # get name + description from domainMetadata.json
        domainMetadata = filename_out.parent.parent / 'metadata/domainMetadata.json'
        name, description = get_name_description_from_domainMetadata(domainMetadata, asset_type[asset_extension]['classname'].lower())
        if name and description:
            readme_file = filename_out.parent.parent / 'README.md'
            update_readme(readme_template, readme_file, name, description)

    # write metadata json 
    with open(filename_out, 'w') as f:
        json.dump(data, f, indent=4)


if __name__ == '__main__':
    main()