
import argparse
import json
import shutil
from pathlib import Path

extensions = {
    'png': 'Image',
    'mp4': 'Video',
    'txt': 'Document',
    'pdf': 'Document',
    'doc': 'Document',
    'geojson': 'Routing',
    'json': 'Data',
    'xml': 'Data'
}

type_data = {
    'Asset' : {
        'folder' : 'data',
        'mask' : '{asset}'
    },
    'Data' : {
        'folder' : 'data',
        'mask' : '{asset}'
    },
    'Document' : {
        'folder' : 'documentation',
        'mask' : '{asset}_technicalDocumentation'
    }, 
    'License' : {
        'folder' : 'documentation',
        'mask' : 'LICENSE'
    },
    'Metadata' : {
        'folder' : 'metadata',
        'mask' : 'domain_metadata'
    },
    'Service' : {
        'folder' : 'services',
        'mask' : '{asset}_extSearch'
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
    if extension in extensions:
        typ = extensions[extension]
        if typ is not None:
            return typ
    return None


def get_file(user_data, filename: Path) -> Path:
    for file in user_data:
        if file['filename'] == filename:
            return file
    return None


def register_data(data: dict, user_data: dict, path: Path, role: str, category: str):
    if not path.exists():
        return
    
    files = []    
    for filename in path.rglob("*"):
        if filename.is_dir():
            continue
        file_data = {}
        file_data['manifest:accessRole'] = role
        file_data['manifest:relativePath'] = str(filename)
        file = get_file(user_data, filename.name)
        if file:
            typ = file['type']
        else:
            typ = get_data_typ(filename)
        file_data['manifest:type'] = typ
        file_data['manifest:format'] = filename.suffix.lstrip('.')
        files.append(file_data)

    if len(files):
        if category in data:
            data[category].extend(files)
        else:
            data[category] = files


def createFileName(filename: Path, asset_name: Path, type : str, index : int) -> Path:
    basename = str(filename.stem)  # Name without extension
    if type in type_data:
        mask = type_data[type]['mask']
    else:
        print (f'type {type} not found in type_data')
        exit(1)
    basename = mask.replace(r"{file}", basename)
    basename = mask.replace(r"{asset}", asset_name)
    extension = filename.suffix

    if type == 'Image':
        if index == 0:
            filename_new = f"{basename}_eyecatcher{extension}"
        else:
            number = str(index).zfill(2)
            filename_new = f"{basename}_impression-{number}{extension}"
    else:
        filename_new = f"{basename}{extension}"
    return Path(filename_new)


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
        print (f'json file {user_input_file} not exists')
        exit(1)

    if not data_path.is_absolute():
        data_path = data_path.resolve()
    if not data_path.exists():
        print (f'data path {data_path} not exists')
        exit(1)

    # read json
    with open(user_input_file, 'r') as file:
        user_data = json.load(file)

    # get asset name
    for file in user_data:
        if file['type'] == 'Asset':
            asset_name = Path(file['filename'])
            asset_name = asset_name.stem
            break
    if not asset_name:
        print (f'no asset found in {file}')
        exit(1)

    # copy files
    upload_folder = user_input_file.parent
    indexImage = 0
    for file in user_data:
        filename = Path(file['filename'])
        # get sub folder
        type = file['type']
        if type in type_data:
            sub_folder = type_data[type]['folder']
        else:
            print (f'type {type} not found in type_data')
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
    data['manifest:links'] = data_group
    for sub_folder in data_path.iterdir():
        if sub_folder == 'data':
            type = 'manifest:data'
            role = 'owner'
        else:
            type = 'manifest:media'
            role = 'publicUser'
        register_data(data_group, user_data, sub_folder, role, type)

    # write metadata json 
    path = filename_out.parent
    if not path.exists():
        path.mkdir()
    with open(filename_out, 'w') as f:
        json.dump(data, f, indent=4)


if __name__ == '__main__':
    main()