import json
import subprocess
import argparse
import shutil

from pathlib import Path
from zipfile import ZipFile


def load_configs(config_dir: Path) -> list:
    configs = []
    
    # Sort the filenames by their numeric prefix
    #sorted_filenames = sorted(config_dir.glob('*.json'), key=lambda f: int(f.stem.split('_')[0]))
    sorted_filenames = sorted(config_dir.glob('*.json'))

    for filename in sorted_filenames:
        with open((config_dir / filename), 'r') as file:
            configs.append(json.load(file))
    
    return configs


def filter_scripts_by_asset_type(configs: list, asset_type: str) -> list:
    matching_configs = [config for config in configs if any(asset['extension'] == asset_type for asset in config['asset types'])]
    return matching_configs


def replace_file_pattern(filepath: str, path: Path, sub_path: Path, name: str) -> str:
    updated_string = filepath.replace(r"{path}", str(path))
    updated_string = updated_string.replace(r"{sub_path}", str(sub_path))
    updated_string = updated_string.replace(r"{name}", name)
    if 'https:' not in updated_string:
        filename = Path(updated_string)
        filename = filename.as_posix()
        return filename
    else:
        return updated_string


def execute_script(script_config: dict, asset_file: Path, output_dir: Path):    
    # prepare script path
    script_path = Path(script_config['params']['call'])
    if not script_path.is_absolute():  # is no absolute path
        parent_dir = Path(__file__).parent.parent
        #script_path = script_path.resolve()  # convert to absolute
        script_path = (parent_dir / script_path).resolve()
    if not script_path.exists():
        raise FileNotFoundError(f"Script not found: {script_path}")
    
    # prepare output path
    if not output_dir.is_absolute():  # is no absolute path
        output_dir = output_dir.resolve()  # convert to absolute
    sub_path = Path(script_config['data folder'])

    # prepare asset name
    asset_name = asset_file.stem  # remove extension 

    # setup script params
    script_call = []
    script_call.append(script_config['environment type'])    
    script_call.append('-X')
    script_call.append('frozen_modules=off')
    script_call.append(script_path)

    # input
    if 'input' in script_config['params']:
        for name,value in script_config['params']['input'].items():
            if name:
                script_call.append(name)
            updated_string = replace_file_pattern(value, output_dir, sub_path, asset_name)
            script_call.append(updated_string)
    else:
        script_call.append(asset_file)

    # output
    if 'output' in script_config['params']:     
        for name,value in script_config['params']['output'].items():
            script_call.append(name)
            updated_string = replace_file_pattern(value, output_dir, sub_path, asset_name)
            script_call.append(updated_string)    
            # TODO create folder here or in sub script?    
            directory = Path(updated_string).parent
            directory.mkdir(parents=True, exist_ok=True)

    # additional parameters     
    if 'additional' in script_config['params']:
        for name,value in script_config['params']['additional'].items():
            script_call.append(name)
            if value:                
                updated_string = replace_file_pattern(value, output_dir, sub_path, asset_name)
                script_call.append(updated_string)

    # run
    try:
        print(f"start command {script_config['name']}")
        result = subprocess.run(script_call, check=True, capture_output=True, text=True)
        print(f"end command {script_config['name']} succeeded with output:")
        print(result.stdout)  # print default output from sub process
        print(result.stderr)  # print logging output from sub process
    except subprocess.CalledProcessError as e:
        print(f"Command {script_config['name']} failed with return code {e.returncode}")
        print(f"Error output: {e.stderr}")
        print(f"Error output: {e.stdout}")
        exit(1)

def create_zip(output_dir: Path, zip_filename : Path):
    with ZipFile(zip_filename, 'w') as zipf:
        for file_path in output_dir.rglob('*'):            
            if file_path.is_file():
                filename = str(file_path.name)
                if filename == 'manifest.json' or filename == 'asset.zip':
                    continue
                file_local = file_path.relative_to(output_dir)
                zipf.write(file_path, file_local)

def main():
    # parse arguments
    parser = argparse.ArgumentParser(prog='main.py', description='extracted from asset and user infos all extractor/creator scripts are called to create an asset archive.')
    parser.add_argument('filename', type=str,help='filename of asset data.')
    parser.add_argument('-config', type=str, help='config path for sub tools.')
    parser.add_argument('-out', type=str, help='output path for asset archive.')
    args = parser.parse_args()

    # Load configuration files
    config_dir = Path(args.config)
    config_dir = config_dir.resolve()
    if not config_dir.is_dir():
        print (f'config path {config_dir} not exists')
        exit(1)
    configs = load_configs(config_dir)

    # Determine asset type (e.g., ".xodr")
    asset_file = Path(args.filename)
    asset_file = asset_file.resolve()
    if not asset_file.exists():
        print (f'asset file {asset_file} not exists')
        exit(1)
    print (f'asset file {asset_file}')
    asset_type = asset_file.suffix.lstrip('.') # Get file extension without the dot

    # Filter scripts that are applicable to the asset type
    applicable_scripts = filter_scripts_by_asset_type(configs, asset_type)

    # Create output directory for the asset file
    asset_name = asset_file.stem
    output_dir = Path(args.out)
    output_dir = output_dir.resolve()    
    output_sub_dir = output_dir / asset_name     
    output_sub_dir.mkdir(parents=True, exist_ok=True)
    print (f'output path {output_sub_dir}')  

    # Execute each script and collect outputs
    for script_config in applicable_scripts:
        execute_script(script_config, asset_file, output_sub_dir)

    # Create a zip file of the output directory
    # remove temp folder before
    temp_path = output_sub_dir / 'temp'
    shutil.rmtree(temp_path)
    # create zip
    zip_filename = output_sub_dir / f"asset.zip"
    create_zip(output_sub_dir, zip_filename)
    # remove zipped folder
    #shutil.rmtree(output_sub_dir)

if __name__ == "__main__":
    main()