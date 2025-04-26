from pathlib import Path
from zipfile import ZipFile
from utils.log_config import setup_logging

import json
import subprocess
import argparse
import shutil
import logging

# configure logging once for the entire application
DEBUG = False
setup_logging(logging.INFO)
logger = logging.getLogger(__name__)

asset_types = {
    "xodr" :"hdmap",
    "xosc" :"scenario",
    "3dmodel" :"environment-model"
}

# load config file for asset_type
def get_configs(config_dir: Path, asset_file: Path) ->list:
    # get asset extension
    asset_type_extension = get_asset_type_extension(asset_file)

    # load process.json
    process_file = config_dir / "process.json"
    if not process_file.exists():
        logger.error(f'config file {process_file} not exists')
        exit(1)
    with open((config_dir / process_file), 'r') as file:
        config_process = json.load(file)

    # filter for asset_type
    config_files = []
    for config in config_process.get("config_files", []):
        if "extensions" in config:
            if asset_type_extension in config["extensions"]:
                config_files.append(config["filename"])
        else:
            config_files.append(config["filename"])   

    # load configs
    configs = []
    for filename in config_files:
        config_file = config_dir / filename
        if not config_file.exists():
            logger.error(f'config file {config_file} not exists')
            exit(1)    

        with open((config_dir / filename), 'r') as file:
            configs.append(json.load(file)) 

    return configs


def replace_file_pattern(filepath: str, path: Path, sub_path: Path, name: str, asset_type: str) -> str:
    updated_string = filepath.replace(r"{path}", str(path))
    updated_string = updated_string.replace(r"{sub_path}", str(sub_path))
    updated_string = updated_string.replace(r"{name}", name)
    updated_string = updated_string.replace(r"{asset_type}", asset_type)
    if 'https:' not in updated_string:
        filename = Path(updated_string)
        filename = filename.as_posix()
        return filename
    else:
        return updated_string

def handle_output(result, name):
    rc = result.returncode

    # 1) Die ganze stderr als Error, wenn returncode != 0
    if rc != 0:
        # log the return code
        logger.error("Command %s exited with return code %d", name, rc)
        # log all stdout as debug, falls du Details brauchst
        if result.stdout:
            logger.debug("=== %s stdout ===\n%s", name, result.stdout.rstrip())
        # log stderr as error (rot)
        logger.error("=== %s stderr ===\n%s", name, result.stderr.rstrip())
        return

    # 2) Wenn returncode == 0, aber stderr nicht leer → nur Warnings
    if result.stderr:
        # split lines and detect keyword "warning"
        for line in result.stderr.splitlines():
            # If the line itself mentions 'warning', treat as warning
            if 'warning' in line.lower():
                logger.warning("=== %s warning === %s", name, line)
            else:
                # sonst immer noch als Info oder Error loggen?
                logger.error("=== %s stderr (non-warning) === %s", name, line)

    # 3) Alles, was auf stdout kam, bleibt Info (grün)
    if result.stdout:
        logger.info("=== %s stdout ===\n%s", name, result.stdout.rstrip())    


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

    # disables frozen standard modules so that Python loads them from the hard disk. 
    # This can be useful if you are working on the Python interpreter itself or testing changes to the standard modules 
    # and do not want to use a frozen version.
    if script_config['environment type'] == "python":
        script_call.append('-X')
        script_call.append('frozen_modules=off')
    script_call.append(script_path)

    asset_type = get_asset_type(get_asset_type_extension(asset_file))     

    # input
    if 'input' in script_config['params']:
        for name,value in script_config['params']['input'].items():
            if name:
                script_call.append(name)
            updated_string = replace_file_pattern(value, output_dir, sub_path, asset_name, asset_type)
            script_call.append(updated_string)
    else:
        script_call.append(asset_file)

    # output
    if 'output' in script_config['params']:     
        for name,value in script_config['params']['output'].items():
            script_call.append(name)
            updated_string = replace_file_pattern(value, output_dir, sub_path, asset_name, asset_type)
            script_call.append(updated_string)    
            # TODO create folder here or in sub script?    
            directory = Path(updated_string).parent
            directory.mkdir(parents=True, exist_ok=True)

    # additional parameters     
    if 'additional' in script_config['params']:
        for name,value in script_config['params']['additional'].items():
            script_call.append(name)
            if value:                
                updated_string = replace_file_pattern(value, output_dir, sub_path, asset_name, asset_type)
                script_call.append(updated_string)

    # run
    try:
        #logger.info(script_call)
        logger.info(f">>>>>>>>>>>>>>>>>>>  start command {script_config['name']}")
        result = subprocess.run(script_call, check=True, capture_output=True, text=True)
        handle_output(result, script_config['name'] )            
        logger.info(f"<<<<<<<<<<<<<<<<<<< end command {script_config['name']}")
    except subprocess.CalledProcessError as e:
        logger.error(f"!!!!!!!!!!!! Command {script_config['name']} failed with return code {e.returncode}")        
        handle_output(e, script_config['name'] )
        exit(1)


def create_zip(output_dir: Path, zip_filename : Path):
    with ZipFile(zip_filename, 'w') as zipf:
        for file_path in output_dir.rglob('*'):            
            if file_path.is_file():
                filename = str(file_path.name)
                if filename == 'asset.zip':
                    continue
                file_local = file_path.relative_to(output_dir)
                zipf.write(file_path, file_local)


def get_asset_type_extension(asset_file: Path):
    asset_type = asset_file.suffix.lstrip('.') # Get file extension without the dot
    if asset_type == 'zip' or asset_type == '7z':
        asset_type = '3dmodel'
    return asset_type

def get_asset_type(asset_type: Path) -> str:
    if asset_type in asset_types:
        return asset_types[asset_type]
    
    logger.error(f'asset type not found {asset_type}')
    exit(1)


def main():
    # parse arguments
    parser = argparse.ArgumentParser(prog='main.py', description='extracted from asset and user infos all extractor/creator scripts are called to create an asset archive.')
    parser.add_argument('filename', type=str,help='filename of asset data.')
    parser.add_argument('-config', type=str, help='config path for sub tools.')
    parser.add_argument('-out', type=str, help='output path for asset archive.')
    args = parser.parse_args()

    # determine asset type (e.g., ".xodr")
    asset_file = Path(args.filename)
    asset_file = asset_file.resolve()
    if not asset_file.exists():
        logger.error(f'asset file {asset_file} not exists')
        exit(1)
    logger.info(f'asset file {asset_file}')

    # load all configs that are applicable to the asset type 
    config_dir = Path(args.config)
    config_dir = config_dir.resolve()
    if not config_dir.is_dir():
        logger.error(f'config path {config_dir} not exists')
        exit(1)
    applicable_scripts = get_configs(config_dir, asset_file)

    # create, cleanup output directory for the asset file
    asset_name = asset_file.stem
    if '.' in asset_name:
        logger.error(f"File {asset_name} has points in name! Not supported!")
        exit(1)

    output_dir = Path(args.out)
    output_dir = output_dir.resolve()    
    output_sub_dir = output_dir / asset_name
    if output_sub_dir.exists():
        shutil.rmtree(output_sub_dir)
    output_sub_dir.mkdir(parents=True, exist_ok=True)
    print (f'output path {output_sub_dir}')  

    # execute each script and collect outputs
    for script_config in applicable_scripts:
        execute_script(script_config, asset_file, output_sub_dir)

    # remove temp folder before
    temp_path = output_sub_dir / 'temp'
    shutil.rmtree(temp_path)

    # create a zip file of the output directory
    zip_filename = output_sub_dir / f"asset.zip"
    create_zip(output_sub_dir, zip_filename)


if __name__ == "__main__":
    main()