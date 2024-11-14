from pathlib import Path
from rdflib import Graph

import json
import argparse
import requests
import logging

logging.basicConfig(level=logging.INFO)

gaiax_url_part = 'GAIA-X4PLC-AAD/ontology-management-base'

def load_shacl_files(shacl_files):
    shacl_graph = Graph()
    for shacl_file in shacl_files:
        shacl_graph.parse(shacl_file, format='turtle')
    return shacl_graph


def load_jsonld_file(jsonld_file : Path):
    data_graph = Graph()
    with open(jsonld_file) as f:
        data = json.load(f)
    data_graph.parse(data=json.dumps(data), format='json-ld')
    return data_graph

def get_shacl_urls_from_data(data_graph: Graph ):
    # get gaia x prefixes
    prefixes = {prefix: str(namespace) for prefix, namespace in data_graph.namespace_manager.namespaces() if gaiax_url_part in str(namespace)}
    return prefixes

def download_shacle(url_path : str, shacle_name: str, folder : Path) -> Path:
    filename = f'{shacle_name}_shacl.ttl'
    local_file_path = Path(f'{folder}/{filename}')

    if not local_file_path.exists():
        # replace github link ro raw data link
        new_url_path = url_path.replace('https://github.com/', 'https://raw.githubusercontent.com/')
        new_url_path = new_url_path.replace('/blob', '')
        new_url_path = new_url_path.replace('/tree', '')
        url = f'{new_url_path}{filename}'
        response = requests.get(url)
        if not response:
            logging.error(f'No shacl files found in url: {url}')
            exit(1)            
        with open(local_file_path, 'wb') as file:
            file.write(response.content) 

    return local_file_path

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

    prefixes = get_shacl_urls_from_data(data_graph)
    shacl_files = []
    for key, value in prefixes.items():
        shacl_files.append(download_shacle(value, key, shacl_folder))
    shacl_graph = load_shacl_files(shacl_files)

    output_path = Path(args.out)
    file = output_path / json_LD_file.with_suffix('.ttl')
    with open(file, 'w') as f:
        f.write(shacl_graph.serialize(format='turtle'))
        f.close()
        logging.info(f'write {file}')

if __name__ == '__main__':
    main()