from pathlib import Path
from pyshacl import validate
from rdflib.namespace import SH
from rdflib import Graph, Literal

import sys
import json
import argparse
import requests
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

gaiax_url_part = 'GAIA-X4PLC-AAD/ontology-management-base'

def load_shacl_files(root_dir):
    shacl_graph = Graph()
    shacl_files = sorted(root_dir.glob('*_shacl.ttl'))
    for shacl_file in shacl_files:
        shacl_graph.parse(shacl_file, format='turtle')
    return shacl_graph


def load_jsonld_file(jsonld_file : Path):

    if not jsonld_file.exists():
        logging.error(f'JsonLD files not found: {jsonld_file}')
        exit(1)  

    data_graph = Graph()
    logging.info(f'adding jsonld file to data graph: {jsonld_file}.')
    with open(jsonld_file) as f:
        data = json.load(f)
    data_graph.parse(data=json.dumps(data), format='json-ld')
    return data_graph


def validate_jsonld_against_shacl(data_graph : Graph, shacl_graph : Graph):
    conforms, v_graph, v_text = validate(data_graph, shacl_graph=shacl_graph, 
                                         #data_graph_format='json-ld', 
                                         inference='rdfs', 
                                         abort_on_first=False,
                                         advanced=True,  # Erweitertes Validierungsverhalten
                                         allow_warnings=True  # Gibt Warnungen statt Fehler, falls nötig
                                         #debug=False
                                         )
    logging.info(f'Conforms: {conforms}')
    if not conforms:
        logging.error('####### Validation errors: #######')
        logging.error(v_text)
        #sys.exit(400)        

def get_shacl_urls_from_data(data_graph: Graph ):
    # get gaia x prefixes
    prefixes = {prefix: str(namespace) for prefix, namespace in data_graph.namespace_manager.namespaces() if gaiax_url_part in str(namespace)}
    return prefixes

def download_shacle(url_path : str, shacle_name: str, folder : Path) -> str:
    filename = f'{shacle_name}_shacl.ttl'
    local_file_path = f'{folder}/{filename}'

    if not Path(local_file_path).exists():
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
    parser = argparse.ArgumentParser(prog='main.py', description='validate jsonLD against shacls')
    parser.add_argument('filename', type=str,help='json LD filename')
    parser.add_argument('-closed', action="store_true", help='set closed = true in all NodeShapes, to also check the naming of properties')
    args = parser.parse_args()

    # load json
    json_LD_file = Path(args.filename)
    data_graph = load_jsonld_file(json_LD_file)

    # load shacls
    shacl_folder = Path(__file__).parent.resolve() / 'shacles'
    if not shacl_folder.exists():
        shacl_folder.mkdir()        
    prefixes = get_shacl_urls_from_data(data_graph)
    for key, value in prefixes.items():
        download_shacle(value, key, shacl_folder)
    shacl_graph = load_shacl_files(shacl_folder)

    # find all closed tags and set to True
    if args.closed:
        for s, p, o in shacl_graph.triples((None, SH.closed, Literal(False))):
            shacl_graph.set((s, SH.closed, Literal(True)))

    # validate
    validate_jsonld_against_shacl(data_graph, shacl_graph)

if __name__ == '__main__':
    main()