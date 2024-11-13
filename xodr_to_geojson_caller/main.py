
import argparse
import subprocess
from pathlib import Path
from lxml import etree

def main():
    parser = argparse.ArgumentParser(prog='main.py', description='Calls the java tool from VCS https://github.com/virtualcitySYSTEMS/opendriveconverter to convert an OpenDRIVE file into a geojson.')   
    parser.add_argument('filename', help='filename of OpenDRIVE file')
    parser.add_argument('-out', help='geojson file')
    parser.add_argument('-path', help='path to the temp folder for a temporary opendrive with customized header.')
    args = parser.parse_args()

    xodr_file = Path(args.filename)
    if not xodr_file.is_absolute():
        xodr_file = xodr_file.resolve()
    if not xodr_file.exists():
        print (f'json file {xodr_file} not exists')
        exit(1)
        
    filename_out = Path(args.out)
    temp_path = Path(args.path)

    # fix header
    tree = etree.parse(xodr_file)
    root = tree.getroot()
    root.set("xmlns", "http://www.asam.de/ODR/16/")

    # write temp file
    new_temp_file = temp_path / 'temp' / 'geojson'
    new_temp_file.mkdir(parents=True, exist_ok=True)
    new_temp_file = new_temp_file / xodr_file.name 
    with open(new_temp_file, "wb") as f:
        tree.write(f, xml_declaration=True, encoding="UTF-8", pretty_print=True)

    # call java script
    script_call = []
    script_call.append('java')
    script_call.append('-jar')
    script_call.append('vcs-odr-converter-1.0.0.jar')
    script_call.append(new_temp_file.as_posix())
    script_call.append(filename_out.parent.as_posix())
    #script_call.append(new_temp_file.as_posix())
    #script_call.append(filename_out.parent.as_posix())
    print(script_call)
    # run
    try:    
        result = subprocess.run(script_call, check=True, capture_output=True, text=True)
        #result = subprocess.run(["java", "-jar", 'vcs-odr-converter-1.0.0.jar', new_temp_file.as_posix(), filename_out.parent.as_posix()], check=True, capture_output=True, text=True)
        print(f"end command succeeded with output:")
        print(result.stdout)  # print default output from sub process
        print(result.stderr)  # print logging output from sub process
    except subprocess.CalledProcessError as e:
        print(f"Command failed with return code {e.returncode}")
        print(f"Error output: {e.stderr}")
        print(f"Error output: {e.stdout}")
        exit(1)

if __name__ == '__main__':
    main()