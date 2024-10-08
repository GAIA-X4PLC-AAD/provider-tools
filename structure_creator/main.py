
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

folder_names = {
    'Asset' : 'data',
    'Data' : 'data',
    'Document' : 'documentation', 
    'License' : 'documentation', 
    'Metadata' : 'metadata',
    'Service' : 'services',
    'Validation' : 'validation', 
    'Image' : 'visualization', 
    'Routing' : 'visualization',
    'Video' : 'visualization',
    '3DPreview' : 'visualization'
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
    
    # copy files
    upload_folder = user_input_file.parent
    for file in user_data:
        filename = Path(file['filename'])
        sub_folder = folder_names[file['type']]
        name = filename.name
        dest = data_path / sub_folder
        if not dest.exists():
            dest.mkdir()
        dest = dest /  name
        source = upload_folder / filename
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