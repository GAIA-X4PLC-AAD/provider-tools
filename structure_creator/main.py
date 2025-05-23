from pathlib import Path
from urllib.parse import urlparse
from multiformats import CID
from multiformats.multihash import digest
from PIL import Image
from utils.utils import create_uuid
from datetime import datetime

import re
import argparse
import json
import shutil
import logging
import os
import requests
import secrets
import string

g_envitedX = 'envited-x'
g_envited_url = 'https://ontologies.envited-x.net/'
g_version = 'v2'

logger = logging.getLogger(__name__)

categories = {
    "isSimulationData" : [
        {
            "type" : "Asset",
            "extensions" : ["xodr", "xosc", "zip", "crg"],
            "folder" : "simulation-data",
            'mask' : '{name}',
            'role' : 'isOwner'
        }
    ],
    "isDocumentation" : [
        {
            "type" : "Document",
            "extensions" : ["pdf", "txt", "md"],
            "folder" : "documentation",
            'mask' : '{name}_{file}',
            'role' : 'isPublic'
        }
    ],   
    "isMedia" : [
        {
            "type" : "Image",
            "extensions" : ["png", "jpeg"],
            "folder" : "media",
            'mask' : '{name}_impression-{number}',
            'role' : 'isPublic'
        },
        {
            "type" : "Video",
            "extensions" : ["mp4"],
            "folder" : "media",
            'mask' : '{name}',
            'role' : 'isPublic'
        },
        {
            "type" : "3DPreview",
            "extensions" : ["json"],
            "folder" : "media/3d_preview",
            'mask' : '{name}',
            'role' : 'isPublic'
        },
        {
            "type" : "Routing",
            "extensions" : ["geojson"],
            "folder" : "media",
            'mask' : '',
            'role' : 'isPublic'
        }
    ],      
    "isMetadata" : [
        {
            "type" : "MetaData",
            "extensions" : ["json"],
            "folder" : "metadata",
            'mask' : 'domain_metadata',
            'role' : 'isPublic'
        }
    ],   
    "isValidationReport" : [
        {
            "type" : "Validation",
            "extensions" : ["xqar", "txt"],
            "folder" : "validation-reports",
            'mask' : '',
            'role' : 'isPublic'
        }
    ],
    "isLicense" : [
        {
            "type" : "License",
            "extensions" : ["", "txt", "md"],
            'folder' : '../',
            'mask' : 'LICENSE',
            'role' : 'isPublic'
        }
    ],       
    "isMiscellaneous" : [
        {
            "type" : "Service",
            "extensions" : ["bjson"],
            "folder" : "metadata",
            'mask' : '{name}',
            'role' : 'isRegistered'
        }
    ]            
}

asset_type = {
    'xodr' : {
        'type' : 'HD-Map',
        'category' : 'HdMap',
        'classname' : 'hdmap',
        'link' : 'hd-map-asset-example'
    },
    'xosc' : {
        'type' : 'Scenario',
        'category' : 'Scenario',
        'classname' : 'scenario',
        'link' : 'scenario-asset-example'
    },
    'zip' : {
        'type' : 'environment-model',
        'category' : 'environment-model',
        'classname' : 'environment-model',
        'link' : 'environment-model-asset-example'
    },
    'crg' : {
        'type' : 'surface-model',
        'category' : 'surface-model',
        'classname' : 'surface-model',
        'link' : 'surface-model-asset-example'
    }
}

mime_type = {
    'isManifest' : {
        'json' : 'application/ld+json'
    },
    'isLicense' : {
        '' : 'text/html'
    },
    'isSimulationData' : {
        '' : 'application/x-{extension}'
    },    
    'isMiscellaneous' : {
        'bjson' : 'application/json'
    },    
    'isDocumentation' : {
        'pdf' : 'application/pdf',
        'txt' : 'text/plain',
        'md' : 'text/markdown'
    },   
    'isValidationReport' : {
        'xqar' : 'application/x-xqar',
        'txt' : 'text/plain'
    },      
    'isMetadata' : {
        'json' : 'application/ld+json'
    },       
    'isMedia' : {
        'png' : 'image/png',
        'geojson' : 'application/x-geojson',
        'json' : 'application/json',
        'mp4' : 'video/mp4'
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

def get_mime_type(category: str, extension: str) -> str:
    if category in mime_type:
        cat_data = mime_type[category]
        if extension in cat_data:
            mime_type_str = cat_data[extension]
        elif '' in cat_data:
            mime_type_str = cat_data['']
        else:
            return None
        
        mime_type_str = mime_type_str.replace(r"{extension}", extension)
        return mime_type_str
    
    return None


def create_file_data(filename: Path, abs_data_path: Path, data_type: str, role: str, asset_info : dict):
    file_data = {}
    file_data['manifest:hasAccessRole'] = 'manifest:' + role
    file_data['manifest:hasCategory'] = 'manifest:' + data_type
    file_meta_data = dict()
    file_data['manifest:hasFileMetadata'] =  file_meta_data
    if is_url(filename):
        file_meta_data['manifest:filePath'] = url_from_path(filename)
        file_meta_data['manifest:mimeType'] = get_mime_type(data_type, '')
    else:        
        relative_path = filename.relative_to(abs_data_path)        
        file_meta_data['manifest:filename'] = relative_path.name            

        if os.path.exists(filename) and data_type != 'isManifest':
            file_meta_data['manifest:fileSize'] =  os.path.getsize(filename.as_posix()) 
            creation_ts = filename.stat().st_ctime
            creation_dt = datetime.fromtimestamp(creation_ts)
            formatted_creation_data = creation_dt.isoformat(timespec="seconds")

            if data_type == "isSimulationData":
                if asset_info and 'recordingTime' in asset_info:
                    formatted_creation_data = asset_info['recordingTime']
                file_meta_data['manifest:timestamp'] =  formatted_creation_data
            else:
                file_meta_data['manifest:timestamp'] =  formatted_creation_data
            # create IPFS CIDv1 identifier   
            with open(filename, "rb") as f:
                data = f.read()
            # create Multihash (SHA-256)
            mh = digest(data, "sha2-256")       
            # create CIDv1 with code "raw"
            cid = CID("base32", 1, "raw", bytes(mh))
            # convert in Base32 coded string
            cid_str = cid.encode("base32")
            file_meta_data['manifest:cid'] = cid_str            
            file_meta_data['manifest:filePath'] = "ipfs://" + cid_str

            if data_type == "isMedia" and filename.suffix.lstrip('.') == "png":
                img = Image.open(filename)
                width, height = img.size
                dimesion_group = {}
                dimesion_group["manifest:unit"] = "pixels"
                dimesion_group["manifest:width"] = str(width)
                dimesion_group["manifest:height"] = str(height)
                file_meta_data['manifest:hasDimensions'] = dimesion_group
        else:
            file_meta_data['manifest:filePath'] = "./" + relative_path.as_posix()
                
        file_meta_data['manifest:mimeType'] = get_mime_type(data_type, relative_path.suffix.lstrip('.'))
    
    return file_data

def register_licence(data: dict, filename: Path, abs_data_path: Path, category: str, role: str, data_type=None):
    data = create_file_data(filename, abs_data_path, category, role, None)
    if data_type:
        if data_type in data:
            data[data_type].extend(data)
        else:
            data[data_type] = data
    else:
        data.clear()
        data.update(data)

def register_asset(data: dict, filename: Path, abs_data_path: Path, category: str, role: str, data_type=None):
    files = []   
    files.append(create_file_data(filename, abs_data_path, category, role, None))
    if data_type:
        if data_type in data:
            data[data_type].extend(files)
        else:
            data[data_type] = files
    else:
        data.clear()
        data.update(files[0])


def register_folder(data: list, user_data: dict, path: Path, abs_data_path: Path, asset_data: dict, asset_info: dict):
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

        # add to json data
        file_entry = create_file_data(filename, abs_data_path, category, role, asset_info)
        if category == 'isMetadata':
            file_entry['manifest:iri'] = asset_info['did']
            file_entry['skos:note'] = f'This is the domain metadata for a {asset_data["type"]}.'
            file_entry['sh:conformsTo'] = [f'{g_envited_url}{asset_data["classname"]}/{g_version}/ontology']
                     
        data.append(file_entry)

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

def url_from_path(path: Path) -> str:
    s = path.as_posix()
    # from 'http:/example.com' to 'http://example.com'
    s = re.sub(
        r'^(?P<scheme>https?):/+',
        lambda m: f"{m.group('scheme')}://",
        s,
        flags=re.IGNORECASE
    )
    return s

def is_url(path: Path):
    url = url_from_path(path)
    parsed = urlparse(url)
    # A URL usually has a scheme (e.g. “http”, “https”) and a “netloc” (e.g. “www.example.com”)
    return parsed.scheme in ('http', 'https') and bool(parsed.netloc)


def update_readme(file_path_in: Path, file_path_out: Path, name_value: str, description_value: str) -> None:
    # Read the entire content of the file using UTF-8 encoding
    content = file_path_in.read_text(encoding="utf-8")
    
    # Replace the placeholders with the given values
    content = content.replace("< envited-x:DataResource:name >", name_value)
    content = content.replace("< envited-x:DataResource:description >", description_value)
    
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
        logger.error(f'No readme files found in url: {readme_url}')
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

    name = safe_get(data, [f"{type}:hasDataResource", "gx:name"])
    if not name:
        logger.error(f'name : {type}:hasDataResource -> gx:name not exists in {filename}')
    description = safe_get(data, [f"{type}:hasDataResource", "gx:description"])
    if not description:
        logger.error(f'description: {type}:hasDataResource -> gx:description not exists in {filename}')

    return name, description


def get_asset(user_data):
    for file in user_data:
        if file['category'] == 'isSimulationData' and file['type'] == 'Asset':
            asset_name = Path(file['filename'])            
            asset_extension = asset_name.suffix.lstrip('.')
            asset_name = asset_name.stem
            return asset_name, asset_extension
    return None, None


def get_asset_info(asset_json : Path, asset_extractor : Path) -> dict:
    
    # load asset json
    if not asset_json.is_absolute():
        asset_json = asset_json.resolve()     
    if not asset_json.exists():
        logger.error(f'asset file {asset_json} not exists')
        exit(1)
    with open(asset_json, 'r') as file:
        asset_json_data = json.load(file)
    asset_info = {}
    asset_info['did'] = asset_json_data['@id'] # to get did

    # load asset extractor data
    if not asset_extractor.is_absolute():
        asset_extractor = asset_extractor.resolve()   
    if not asset_extractor.exists():
        logger.error(f'asset file {asset_extractor} not exists')
        exit(1) 
    with open(asset_extractor, 'r') as file:
        asset_extractor_data = json.load(file)

    if 'recordingTime' in asset_extractor_data:
        asset_info['recordingTime'] = asset_extractor_data['recordingTime']    # to get recordingTime

    return asset_info


def main():
    parser = argparse.ArgumentParser(prog='main.py', description='the folder structure is completed from the user info and a metadata table is created for the manifest')   
    parser.add_argument('filename', help='filename of json file from frontend.')
    parser.add_argument('-out', help='json file for manifest.')
    parser.add_argument('-path', help='path to copy/parse data.')
    parser.add_argument('-asset_json', help='filename to final asset json.')
    parser.add_argument('-asset_extractor', help='filename to temp asset json.')
    args = parser.parse_args()

    user_input_file = Path(args.filename)
    data_path = Path(args.path)
    filename_out = Path(args.out)

    if not user_input_file.is_absolute():
        user_input_file = user_input_file.resolve()
    if not user_input_file.exists():
        logger.error(f'json file {user_input_file} not exists')
        exit(1)

    if not data_path.is_absolute():
        data_path = data_path.resolve()
    if not data_path.exists():
        logger.error(f'data path {data_path} not exists')
        exit(1)

    # read json
    with open(user_input_file, 'r') as file:
        user_data = json.load(file)

    manifest_uuid = create_uuid()

    # get asset info (uuid, recordingTime)
    asset_json = Path(args.asset_json)
    asset_info = get_asset_info(asset_json, Path(args.asset_extractor))

    # initialize asset_name
    asset_name, asset_extension = get_asset(user_data)
    if not asset_name or not asset_extension:
        logger.error(f'no asset found in {file}')
        exit(1)
    if asset_extension in asset_type:        
        asset_data = asset_type[asset_extension]

    # copy files
    upload_folder = user_input_file.parent
    indexImage = 1
    license_data = None
    for file in user_data:
        filename = Path(file['filename'])

        # get cat, type data
        category = file['category']
        typ = file['type']
        cat_type_data = get_data_from_category_type(category, typ)
        if not cat_type_data:
            logger.error(f'type {typ} not found in category {category}')
            exit(1)

        if not is_url(filename):      
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

        if 'license_type' in file:
            license_data = {}
            license_data = file

    # create json file for jsonLD creator
    data = {}
    data['did'] = 'did:web:registry.gaia-x.eu:Manifest:' + manifest_uuid
    data['shacl_type'] = f'{g_envitedX}::{g_envited_url}{g_envitedX}/{g_version}/ontology#ManifestShape'
    data_group = []
    data['manifest:hasArtifacts'] = data_group
    for sub_folder in data_path.iterdir():
        relative_path = str(sub_folder.relative_to(data_path))
        if relative_path == 'temp':
            continue
        register_folder(data_group, user_data, sub_folder, data_path, asset_data, asset_info)

    # register license
    # TODO get license from file or user input link/type
    #license_file = Path('https://www.mozilla.org/en-US/MPL/2.0/')
    if license_data is not None:
        licence_group = {}        
        licence_group['gx:license'] = license_data['license_type']
        data['manifest:hasLicense'] = licence_group
        hasLink_group = {}
        licence_group['manifest:hasLink'] = hasLink_group
        register_asset(hasLink_group, Path(license_data['filename']), data_path, 'isLicense', 'isPublic')        
        
    # register manifest
    manifest_group = {}
    data['manifest:hasManifestReference'] = manifest_group
    register_asset(manifest_group, data_path / 'manifest_reference.json', data_path, 'isManifest', 'isPublic')

    path = filename_out.parent    
    if not path.exists():
        path.mkdir()

    # create readme
    url = "https://raw.githubusercontent.com/GAIA-X4PLC-AAD/ontology-management-base/main/envited-x/README.md"
    script_path = Path(__file__).resolve()
    readme_template = script_path.parent / 'README_template.md'
    download_readme(url, readme_template)    
    #readme_template = Path(__file__).parent.resolve() / 'README_template.md'
    if asset_extension in asset_type:
        # get name + description from {asset_type}_instance.json
        classname = asset_type[asset_extension]['classname']
        domainMetadata = filename_out.parent.parent / f'metadata/{classname}_instance.json'
        name, description = get_name_description_from_domainMetadata(domainMetadata, classname.lower())
        if name and description:
            readme_file = filename_out.parent.parent / 'README.md'
            readme_file.write_bytes(readme_template.read_bytes())
            update_readme(readme_template, readme_file, name, description)

    # write metadata json 
    with open(filename_out, 'w') as f:
        json.dump(data, f, indent=4)

    # replace with uuid in json
    asset_content = asset_json.read_text(encoding="utf-8")
    asset_content = asset_content.replace("Manifest:uuid", f"Manifest:{manifest_uuid}")
    asset_json.write_text(asset_content, encoding="utf-8")

if __name__ == '__main__':
    main()