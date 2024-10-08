from pyproj import CRS, Transformer
from pathlib import Path

import xml.etree.ElementTree as ET
import simplekml
import argparse
import json
import math


class Vec2:
    def __init__(self, x, y):
        self.x = x
        self.y = y

# Function to parse the XML file and extract coordinates
def parse_xml(file_path):
    tree = ET.parse(file_path)
    root = tree.getroot()

    georef = root.find('.//geoReference')
    proj4_str = None
    if georef is not None:
        proj4_str = georef.text.strip()
    
    offset_node = root.find('.//offset')
    offset = Vec2(0,0)
    if offset_node is not None:
        offset = Vec2(float(offset_node.attrib['x']), float(offset_node.attrib['y']))

    lines = []
    for line in root.findall('.//planView'):
        coordinates = []
        for point in line.findall('.//geometry'):
            x = float(point.attrib['x'])
            y = float(point.attrib['y'])
            hdg = float(point.attrib['hdg'])
            length = float(point.attrib['length'])
            coordinates.append((x, y, hdg, length))
        lines.append(coordinates)
    return proj4_str, offset, lines

def calculate_end_position(start_pos : Vec2, heading, length):
    end_x = start_pos.x + math.cos(heading) * length
    end_y = start_pos.y + math.sin(heading) * length
    return Vec2(end_x, end_y)

# Function to reproject the coordinates
def reproject(lines, offset, transformer):
    transformed_lines = []
    for line in lines:
        transformed_coords = []
        count = len(line) - 1
        for x, y, hdg, length in line:
            pos_abs = Vec2(x + offset.x, y + offset.y)
            lon, lat = transformer.transform(pos_abs.x, pos_abs.y)
            transformed_coords.append((lon, lat))
            if count == 0:
                end_pos = calculate_end_position(pos_abs, hdg, length)
                lon, lat = transformer.transform(end_pos.x, end_pos.y)
                transformed_coords.append((lon, lat))
            count = count - 1
        transformed_lines.append(transformed_coords)
    return transformed_lines


# Function to create and write KML lines
def create_kml(lines, output_file):
    kml = simplekml.Kml()
    for line in lines:
        linestring = kml.newlinestring(name="Line")
        linestring.coords = line

    kml.save(output_file)

# Function to create and write a GeoJson lines
def create_geojson(lines, output_file):
    features = []
    for line in lines:
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": [(lon, lat) for lon, lat in line]
            },
            "properties": {}
        }
        features.append(feature)

    geojson = {
        "type": "FeatureCollection",
        "features": features
    }

    # write GeoJSON
    with open(output_file, 'w') as f:
        json.dump(geojson, f, indent=2)

def main():
    parser = argparse.ArgumentParser(prog='main.py', description='creates routing files (as geojson or kml) on OpenDRIVE files.')   
    parser.add_argument('filename', help='filename of OpenDRIVE file.')
    parser.add_argument('-out', type=str,help='filename of exported geo file.')
    parser.add_argument('-format', choices=['kml', 'geojson'], default='geojson', help='output format for geo file.')
    args = parser.parse_args()

    xodr_file = Path(args.filename)
    if not xodr_file.exists():
        print (f'xodr file {xodr_file} not exists')
        exit(1)

    output_file = Path(args.out)
    if not output_file.parent.exists():
        output_file.parent.mkdir()

    format = args.format

    # Parse the XML file and extract coordinates
    in_proj, offset, lines = parse_xml(xodr_file)
    if in_proj is None or lines is None:
        print(f"no projection found!")    
        return

    # PROJ.4 projections
    #web_mecator = CRS.from_epsg(3857)
    web_mecator = CRS.from_proj4(in_proj)
    wgs84 = CRS.from_epsg(4326)
    transformer_proj_to_wgs84 = Transformer.from_crs(web_mecator, wgs84, always_xy=True)

    # Reproject the coordinates
    transformed_lines= reproject(lines, offset, transformer_proj_to_wgs84)

    # Create the KML line
    if format == "geojson":
        create_geojson(transformed_lines, output_file)
    else:
        create_kml(transformed_lines, output_file)

    print(f"KML file created: {output_file}")

if __name__ == '__main__':
    main()