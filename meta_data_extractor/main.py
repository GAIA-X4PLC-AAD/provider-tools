#!/bin/python3

if __name__ == '__main__':
    from extractor import extract
else:
    from .extractor import extract
from pathlib import Path

import argparse
import logging


logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s.%(msecs)03d [%(levelname)5s-%(name)s] {%(module)s -> %(funcName)s} %(message)s',
                    datefmt='%d/%m/%Y %H:%M:%S')
logging.getLogger(__name__).setLevel(logging.WARNING)


def main():
    parser = argparse.ArgumentParser(prog='main.py', description='extractor meta data from a given file.')
    parser.add_argument('-out', '--output', type=str, default='claims/', help='filename to exported claim.')
    parser.add_argument('-u', '--user_input', action='store_true', help='Activates the user query via dialogues for non-extractable attributes.')
    parser.add_argument('filename', help='filename to extract metadata')

    # 1. get and check arguments
    args = parser.parse_args()

    # get output dir
    output_file = Path(args.output)
    if not output_file:
        exit(1)
    logging.info(f'output_file {output_file}')
    directory = output_file.parent
    if not directory.exists():
        directory.mkdir(parents=True, exist_ok=True)

    # open file, extract, an write 
    file = Path(args.filename)
    if not file.exists():
        exit(1)
    logging.info(f'file {file}')
    valid = extract(file, output_file)
    if valid is not True:
        logging.error(f'file {file.absolute()} can not be extraced')

if __name__ == '__main__':
    main()
