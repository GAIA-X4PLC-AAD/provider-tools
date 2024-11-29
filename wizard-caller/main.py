from pathlib import Path

import logging
import argparse
import requests

def trigger_open_sd_wizard():
    try:
        nodejs_server_url = 'http://127.0.0.1:3000/openSdWizard'
        response = requests.post(nodejs_server_url)
        if response.status_code == 200:
            print("Triggered the SD Wizard successfully")
        else:
            print(f"Failed to trigger SD Wizard: {response.status_code}")
    except Exception as e:
        print(f"Error triggering SD Wizard: {e}")

def main():
    parser = argparse.ArgumentParser(prog='main.py', description='calls the sd creation wizard with json and merged shacl file to fill the non-extractable attributes from the user')
    parser.add_argument('filename', type=str,help='filename of json LD file')
    parser.add_argument('-shacl', type=str,help='merged shacl file')
    parser.add_argument('-out', type=str, help='output filename for enhanced json LD file')
    args = parser.parse_args()

    jsonLD_file = Path(args.filename)
    if not jsonLD_file.exists():
        logging.error(f'jsonLD file not exist {jsonLD_file}')
        exit(1)

    shacl_file = Path(args.shacl)
    if not shacl_file.exists():
        logging.error(f'shacl file not exist {shacl_file}')
        exit(1)

    # call sd wizrad in docker composed
    trigger_open_sd_wizard()
    # TODO - use jsonLD_file, shacl_file

    # get enhanced jsonLD file from docker 
    # TODO get enhanced jsonLD file

    # copy to target file location
    output_name = Path(args.out)    
    # TODO copy to target location


if __name__ == '__main__':
    main()