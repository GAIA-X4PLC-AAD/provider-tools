from pathlib import Path
from pyshacl import validate
from rdflib import Graph

import sys
import json
import argparse


def load_shacl_files(root_dir):
    shacl_graph = Graph()
    shacl_files = sorted(root_dir.glob('*_shacl.ttl'))
    #shacl_files = glob.glob(f'{root_dir}/**/*_shacl.ttl', recursive=True)
    for shacl_file in shacl_files:
        shacl_graph.parse(shacl_file, format='turtle')
    return shacl_graph


def load_jsonld_file(jsonld_file : Path):
    data_graph = Graph()
    print(f'adding jsonld file to data graph: {jsonld_file}.')
    with open(jsonld_file) as f:
        data = json.load(f)
    data_graph.parse(data=json.dumps(data), format='json-ld')
    return data_graph


def validate_jsonld_against_shacl(data_graph : Graph, shacl_graph : Graph):
    conforms, v_graph, v_text = validate(data_graph, shacl_graph=shacl_graph, data_graph_format='json-ld', inference='rdfs', debug=False)
    print(f'Conforms: {conforms}')
    if not conforms:
        print('####### Validation errors: #######')
        print(v_text)
        #print('')
        #print('####### Validation graph: #######')
        #print(v_graph.serialize(format='turtle'))
        sys.exit(400)        


def main():
    parser = argparse.ArgumentParser(prog='main.py', description='validate jsonLD against shacls')
    parser.add_argument('filename', type=str,help='json LD filename')
    args = parser.parse_args()

    # load json and shacls
    json_LD_file = Path(args.filename)
    data_graph = load_jsonld_file(json_LD_file)
    shacl_graph = load_shacl_files(Path(__file__).parent.resolve() / 'shacles')

    # validate
    validate_jsonld_against_shacl(data_graph, shacl_graph)

if __name__ == '__main__':
    main()