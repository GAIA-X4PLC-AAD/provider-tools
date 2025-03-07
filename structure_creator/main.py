from pathlib import Path
from urllib.parse import urlparse

import argparse
import json
import shutil
import logging
import os
import requests

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

extensions = {"pdf", "png", "mp4", "geojson", "zip", "json", "txt", "xodr", "md", "html", "did" "other"}

extensions_to_category = {
    'png': 'Image',
    'mp4': 'Video',
    'txt': 'Document',
    'pdf': 'Document',
    'doc': 'Document',
    'geojson': 'Routing',
    'bjson' : 'AssetData', 
    'xqar' : 'MetaData',
    'zip' : 'Asset',
    'json' : '3DPreview'
}

category_to_type = {
   'Image' : 'visualization',
   'Video' : 'visualization',
   '3DPreview' : 'visualization',
   'Routing' : 'visualization',
   'Document' : 'documentation',
   'AssetData' : 'assetData',
   'Asset' : 'assetData',
   'MetaData' : 'metadata',
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
    }
}

type_data = {
    'AssetData' : {
        'folder' : 'data',
        'mask' : '{asset}'
    },
    'Data' : {
        'folder' : 'data',
        'mask' : '{asset}'
    },
    'Document' : {
        'folder' : 'documentation',
        'mask' : '{asset}_{file}'
    }, 
    'License' : {
        'folder' : '../',
        'mask' : 'LICENSE'
    },
    'Metadata' : {
        'folder' : 'metadata',
        'mask' : 'domain_metadata'
    },
    'Validation' : {
        'folder' : 'validation',
        'mask' : 'qcReport'
    },
    'Image' : {
        'folder' : 'visualization',
        'mask' : '{asset}'
    },
    'Routing' : {
        'folder' : 'visualization',
        'mask' : 'roadNetwork'
    },
    'Video' : {
        'folder' : 'visualization',
        'mask' : '{asset}'
    },
    '3DPreview' : {
        'folder' : 'visualization',
        'mask' : 'detailRoadNetwork'
    }
}

def get_data_typ(file: Path)-> str:
    extension = file.suffix.lstrip('.') # Get file extension without the dot
    if extension in extensions_to_category:
        typ = extensions_to_category[extension]
        if typ is not None:
            return typ
    # try with subfolder
    sub_path = file.name if file.is_dir() else file.parent.name
    for key, value in type_data.items():
        if value['folder'] == sub_path:
            return key
    return None


def get_file(user_data, filename: Path) -> Path:
    for file in user_data:
        if file['filename'] == filename:
            return file
    return None

def get_file_type(filename: Path):
    file_ext = filename.suffix.lstrip('.')
    if file_ext in extensions:
        return file_ext
    else:
        return "other"

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
        file_meta_data['manifest:uri'] = relative_path.as_posix()    
        file_meta_data['manifest:filename'] = os.path.basename(relative_path.as_posix())
        if os.path.exists(filename):
            file_meta_data['manifest:fileSize'] =  os.path.getsize(filename.as_posix())           
    
    return file_data


def register_asset(data: dict, filename: Path, abs_data_path: Path, data_type: str, role: str, category: str):
    files = []   
    files.append(create_file_data(filename, abs_data_path, data_type, role))
    
    if category in data:
        data[category].extend(files)
    else:
        data[category] = files

def get_data_type(file_type:str):
    if file_type in category_to_type:
        return category_to_type[file_type]
    else:
        return 'other'


def handle_bjson(filename, abs_data_path, data_type, role, data, category):
    files = []
    files.append(create_file_data(filename, abs_data_path, data_type, role))

    if category in data:
        data[category].extend(files)
    else:
        data[category] = files


def register_folder(data: dict, user_data: dict, path: Path, abs_data_path: Path, role: str, category: str):
    if not path.exists():
        return
    
    files = []  
    for filename in path.rglob("*"):
        if filename.is_dir():
            continue
        file = get_file(user_data, filename.name)
        if file:
            file_type = file['type']
        else:
            file_type = get_data_typ(filename)

        if file_type == 'Service':
            role = 'publicUser'
        data_type = get_data_type(file_type)
        if filename.suffix.lstrip('.') == 'bjson':
            handle_bjson(filename, abs_data_path, data_type, role, data, category)
            continue
        files.append(create_file_data(filename, abs_data_path, data_type, role))

    if len(files):
        if category in data:
            data[category].extend(files)
        else:
            data[category] = files

def getMask(filename: Path, type : str, index : int) -> Path:
    if type in type_data:
        mask = type_data[type]['mask']
    else:
        logging.error(f'type {type} not found in type_data')
        exit(1)

    if type == 'Image':
        mask = mask + '_impression-{number}'
    elif type == 'Document' and filename.suffix == '.pdf' and not filename.stem.endswith("_Documentation"):
        mask = mask + '_Documentation'
    return mask

def createFileName(filename: Path, asset_name: Path, type : str, index : int) -> Path:
    basename = str(filename.stem)  # Name without extension

    mask = getMask(filename, type, index)

    if "{asset}" in mask and "{file}" in mask:
        common_prefix  = os.path.commonprefix([basename, asset_name])
        basename = basename[len(common_prefix):]
    mask = mask.replace(r"{asset}", asset_name)
    mask = mask.replace(r"{file}", basename)
    
    basename = mask.replace(r"{number}", str(index).zfill(2))
    extension = filename.suffix

    filename_new = f"{basename}{extension}"
    return Path(filename_new)

def create_readme(asset_name: Path, asset_typ: str, asset_link: str, filename: Path):
    template = """# {asset_name}
This example serves as a reference for onboarding an {asset_typ} asset into the data space of ENVITED and can be used as a template for other dataspaces as well. 
It contains a fully described and consistent example of an {asset_typ} asset and an **`manifest.json` - file**.
A complete **`asset`** in a specific domain includes the data itself and all necessary files for describing, evaluating, and visualizing the dataset. 
The **`asset`** has a specific following folder structure and the sample can be downloaded here in this repo from the lastest release (**`asset.zip`**).

# FAQ: 
Get all information [here](https://github.com/GAIA-X4PLC-AAD/{asset_link})
"""

    readme_content = template.format(asset_name=asset_name, asset_typ=asset_typ, asset_link=asset_link)
    with open(filename, "w", encoding="utf-8") as f:
        f.write(readme_content)

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
    asset_name = None
    asset_extension = None
    # get asset name from Data entry
    for file in user_data:
        if file['type'] == 'AssetData':
            asset_name = Path(file['filename'])            
            asset_extension = asset_name.suffix.lstrip('.')
            asset_name = asset_name.stem
            break
    if not asset_name:
        logging.error(f'no asset found in {file}')
        exit(1)

    # copy files
    upload_folder = user_input_file.parent
    indexImage = 1
    for file in user_data:
        filename = Path(file['filename'])
        # get sub folder
        type = file['type']
        if type in type_data:
            sub_folder = type_data[type]['folder']
        else:
            logging.error(f'type {type} not found in type_data')
            exit(1)
        # get dest name
        dest_name = filename.name
        dest_name = createFileName(Path(dest_name), asset_name, type, indexImage)        
        if type == 'Image':
            indexImage = indexImage + 1 # incrase image index for image mask

        # destination filename
        dest = data_path / sub_folder
        if not dest.exists():
            dest.mkdir()
        dest = dest /  dest_name        
        # source filename
        source = upload_folder / filename
        # copy
        shutil.copy(source, dest)

    # create json file for jsonLD creator
    data = {}
    data['shacle_type'] = 'manifest:Manifest'
    data_group = {}
    data['manifest:data'] = data_group
    for sub_folder in data_path.iterdir():
        relative_path = str(sub_folder.relative_to(data_path))
        if relative_path == 'data':
            type = 'manifest:assetData'
            role = 'owner'
        elif relative_path == 'temp':
            continue
        else:
            type = 'manifest:contentData'
            role = 'publicUser'
        register_folder(data_group, user_data, sub_folder, data_path, role, type)

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