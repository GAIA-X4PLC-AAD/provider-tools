from pathlib import Path

import webbrowser
import logging
import argparse

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
    url = "http://localhost:80/form" # SD-Creation-Wizard
    webbrowser.open(url)
    # TODO - use jsonLD_file, shacl_file

    # get enhanced jsonLD file from docker 
    # TODO get enhanced jsonLD file

    # copy to target file location
    output_name = Path(args.out)    
    # TODO copy to target location


if __name__ == '__main__':
    main()