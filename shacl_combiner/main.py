from pathlib import Path
from utils.utils import download_shacle, get_prefixes, get_url_for_download, load_shacl_files, load_jsonld_file

import argparse
import logging

logging.basicConfig(level=logging.INFO)

gaiax_url_part = 'GAIA-X4PLC-AAD/ontology-management-base'
   
def main():
    parser = argparse.ArgumentParser(prog='main.py', description='combine shalce file for jsonLD to one file')
    parser.add_argument('filename', type=str,help='json LD filename')
    parser.add_argument('-out', type=str, help='output path for combined shacle file')
    args = parser.parse_args()

    # load json
    json_LD_file = Path(args.filename)
    data_graph = load_jsonld_file(json_LD_file)

    # load shacls
    shacl_folder = Path(__file__).parent.resolve() / 'shacles'
    if not shacl_folder.exists():
        shacl_folder.mkdir()        

    prefixes = get_prefixes(data_graph)
    shacl_files = []
    for key, value in prefixes.items():
        new_url_path = get_url_for_download(value)
        shacl_files.append(download_shacle(new_url_path, key))
    shacl_graph = load_shacl_files(shacl_files)

    output_path = Path(args.out)
    if not output_path.exists():
        output_path.mkdir()    
    file = output_path / Path(json_LD_file.stem + '.ttl')
    with open(file, 'w') as f:
        f.write(shacl_graph.serialize(format='turtle'))
        f.close()
        logging.info(f'write {file}')

if __name__ == '__main__':
    main()