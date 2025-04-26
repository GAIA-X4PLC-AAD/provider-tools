from pathlib import Path
from pyshacl import validate
from rdflib.namespace import SH, RDF
from rdflib import Graph, Literal
from utils.utils import download_shacle, get_url_for_download, get_prefixes, load_shacl_files, load_jsonld_file

import argparse
import logging

logger = logging.getLogger(__name__)

gaiax_url_part = 'GAIA-X4PLC-AAD/ontology-management-base'


def validate_jsonld_against_shacl(data_graph : Graph, shacl_graph : Graph):
    conforms, v_graph, v_text = validate(data_graph, shacl_graph=shacl_graph, 
                                         #data_graph_format='json-ld', 
                                         inference='rdfs', 
                                         abort_on_first=False,
                                         advanced=True,  # Erweitertes Validierungsverhalten
                                         allow_warnings=True  # Gibt Warnungen statt Fehler, falls nötig
                                         #debug=False
                                         )
    if not conforms:
        logger.error('####### Validation errors: #######')
        #logger.error(v_text)        
        # Iterate over all ValidationResult nodes
        for result in v_graph.subjects(RDF.type, SH.ValidationResult):
            # Extract severity (e.g., Violation or Warning)
            sev = v_graph.value(result, SH.resultSeverity)
            # Extract the focus node where the violation occurred
            #focus = v_graph.value(result, SH.focusNode)
            # Extract the path/property that failed
            path = v_graph.value(result, SH.resultPath)
            # Extract the human-readable message
            message = v_graph.value(result, SH.resultMessage)

            # Log a structured, one-line summary of each result
            logger.error(
                "-> [%s] Path=%s\n   : %s",
                sev.split('#')[-1] if sev else "UnknownSeverity",
                path or "(no path)",
                message or "(no message)"
            )    

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
    prefixes = get_prefixes(data_graph)
    shacl_files = []
    for key, value in prefixes.items():
        new_url_path = get_url_for_download(value)
        shacl_files.append(download_shacle(new_url_path, key))
    shacl_graph = load_shacl_files(shacl_files)

    # find all closed tags and set to True
    if args.closed:
        for s, p, o in shacl_graph.triples((None, SH.closed, Literal(False))):
            shacl_graph.set((s, SH.closed, Literal(True)))

    # validate
    validate_jsonld_against_shacl(data_graph, shacl_graph)

if __name__ == '__main__':
    main()