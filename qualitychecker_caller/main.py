from pathlib import Path
from lxml import etree

import subprocess
import argparse
import shutil
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

def update_config_file(template_file: Path, input_file: Path, result_file: Path, config_file: Path) -> Path:
    # Parse the XML file
    logging.info(f"Using template {template_file}")
    tree = etree.parse(template_file)
    root = tree.getroot()

    # Find the Param element 'InputFile' and update its value attribute
    for param in root.findall(".//Param[@name='InputFile']"):
        param.set("value", input_file.as_posix())

    # Find the Param element 'resultFile' and update its value attribute
    for param in root.findall(".//Param[@name='resultFile']"):
        param.set("value", result_file.as_posix())

    # Write the updated XML to the output file
    tree.write(config_file, encoding="utf-8", pretty_print=True, xml_declaration=True)
    logging.info(f"Created configuration file {config_file}")

    return config_file

def create_config_file(input_file: Path, result_file : Path) -> Path:
    file_type = input_file.suffix.lstrip('.') # Get file extension without the dot

    script_folder = Path(__file__).parent
    templates_folder = script_folder / 'templates'

    for file in templates_folder.iterdir():
        if file.is_file() and file_type in file.name:
            template_file = file
            break
    if not template_file:
        logging.error(f'template for file type {file_type} not exists')
        exit(1)

    return update_config_file(template_file, input_file, result_file, Path("qc_config.xml"))

def main():
    # parse arguments
    parser = argparse.ArgumentParser(prog='main.py', description='setup and run quality checker')
    parser.add_argument('filename', type=str,help='ASAM OpenX file, e.g. xodr, xosc')
    parser.add_argument('-out', type=str, help='output result file')
    args = parser.parse_args()

    input_file = Path(args.filename)
    if not input_file.exists():
        logging.error(f'input file {input_file} not exists')
        exit(1)

    # create config file from templates with input_file replacement
    output_file = Path(args.out)
    if not output_file.parent.exists():
        output_file.parent.mkdir()   
    config_file = create_config_file(input_file, output_file)

    # call qc_opendrive
    app_name = 'qc_opendrive'
    script_call = []
    script_call.append(app_name)
    script_call.append('-c')
    script_call.append(config_file.as_posix())

    try:
        logging.info(f"start command {app_name}")
        result = subprocess.run(script_call, check=True, capture_output=True, text=True)
        logging.info(f"end command {app_name} succeeded with output:")
        logging.info(result.stdout)  # print default output from sub process
        logging.info(result.stderr)  # print logging output from sub process
    except subprocess.CalledProcessError as e:
        logging.error(f"Command {app_name} failed with return code {e.returncode}")
        logging.error(f"Error output: {e.stderr}")
        logging.error(f"Error output: {e.stdout}")
        exit(1)

    # call openMSL opendrive
    # TODO


if __name__ == "__main__":
    main()
