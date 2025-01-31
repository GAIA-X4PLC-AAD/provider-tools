from pathlib import Path
from urllib.parse import urlparse

import argparse
import json
import shutil
import logging
import os

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
        'link' : 'hd-map-asset-example'
    },
    'xosc' : {
        'type' : 'Scenario',
        'link' : 'scenario-asset-example'
    },
    'xosc' : {
        'type' : 'environment-model',
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

def create_file_data(filename: Path, data_type: str, role: str, category: str):
    file_data = {}
    file_data['manifest:accessRole'] = role
    if is_url(str(filename)):
        file_data['manifest:path'] = filename
        file_data['manifest:format'] = 'html'
    else:
        file_data['manifest:path'] = filename.as_posix()        
        file_data['manifest:format'] = get_file_type(filename)
    file_data['manifest:type'] = data_type
    return file_data


def register_asset(data: dict, filename: Path, data_type: str, role: str, category: str):
    files = []   
    files.append(create_file_data(filename, data_type, role, category))
    
    if category in data:
        data[category].extend(files)
    else:
        data[category] = files

def get_data_type(file_type:str):
    if file_type in category_to_type:
        return category_to_type[file_type]
    else:
        return 'other'


def handle_bjson(relative_path, data_type, role, data):
    files = []
    category = 'manifest:contentData'
    files.append(create_file_data(relative_path, data_type, role, category))

    if category in data:
        data[category].extend(files)
    else:
        data[category] = files


def register_folder(data: dict, user_data: dict, path: Path, data_path: Path, role: str, category: str):
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
        relative_path = filename.relative_to(data_path)
        if filename.suffix.lstrip('.') == 'bjson':
            handle_bjson(relative_path, data_type, role, data)
            continue
        files.append(create_file_data(relative_path, data_type, role, category))

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
    #for file in user_data:
    #    if file['type'] == 'License':
    #        license_file = Path(file['filename'])
    #        break
    if license_file is not None:
        licence_group = {}
        licence_group['manifest:spdxIdentifier'] = 'MPL-2.0'
        
        data['manifest:license'] = licence_group
        register_asset(licence_group, license_file, 'license', 'publicUser', 'manifest:licenseData')
        


    path = filename_out.parent    
    if not path.exists():
        path.mkdir()

    # create readme
    if asset_extension in asset_type:
        asset_typ = asset_type[asset_extension]['type']
        asset_link = asset_type[asset_extension]['link']
        readme_filename = data_path / Path('README.md')
        create_readme(asset_name, asset_typ, asset_link, readme_filename)

    # write metadata json 
    with open(filename_out, 'w') as f:
        json.dump(data, f, indent=4)


if __name__ == '__main__':
    main()