
from pathlib import Path
from lxml import etree

import argparse
import math
import sys


# helper class for 2d bounding box
class Box2D:
    xMin : float
    xMax : float
    yMin : float
    yMax : float

    def __init__(self, 
                 xMin: float = sys.float_info.max, 
                 xMax: float = -sys.float_info.max, 
                 yMin: float = sys.float_info.max, 
                 yMax: float = -sys.float_info.max) -> None:
        super().__init__()
        self.xMin = xMin
        self.xMax = xMax
        self.yMin = yMin
        self.yMax = yMax

    def intersection(self, box2):
        x_overlap = max(0, min(self.xMax, box2.xMax) - max(self.xMin, box2.xMin))
        y_overlap = max(0, min(self.yMax, box2.yMax) - max(self.yMin, box2.yMin))
        
        if x_overlap > 0 and y_overlap > 0:
            return True
        else:
            return False
        
    def expandByBox(self, box_expand):
        if box_expand.xMin < self.xMin:
            self.xMin = box_expand.xMin
        if box_expand.xMax > self.xMax:
            self.xMax = box_expand.xMax
        if box_expand.yMin < self.yMin:
            self.yMin = box_expand.yMin
        if box_expand.yMax > self.yMax:
            self.yMax = box_expand.yMax       

    def expandByPos(self, x, y):
        if x < self.xMin:
            self.xMin = x
        if x > self.xMax:
            self.xMax = x

        if y < self.yMin:
            self.yMin = y
        if y > self.yMax:
            self.yMax = y            
    
    def expandBySeam(self, seam):
        self.xMin = self.xMin - seam
        self.xMax = self.xMax + seam
        self.yMin = self.yMin - seam
        self.yMax = self.yMax + seam


# calc end position from start pos, heading and length value
def calculate_end_position(start_x, start_y, heading, length):
    # Berechne die Änderung in der x- und y-Richtung
    delta_x = length * math.cos(heading)
    delta_y = length * math.sin(heading)

    # Berechne die Endposition
    x = start_x + delta_x
    y = start_y + delta_y

    return x, y


def calculate_bounding_box(x, y, hdg, length):

    endPos = calculate_end_position(x, y, hdg, length)
    box = Box2D()
    box.expandByPos(x, y)
    box.expandByPos(endPos[0], endPos[1])
    box.expandBySeam(10)
    return box


def getRoadBounding(road):
    geometries = road.findall(".//geometry")
    boxRoad = Box2D()
    for geometry in geometries:
        x = float(geometry.attrib['x'])
        y = float(geometry.attrib['y'])
        hdg = float(geometry.attrib['hdg'])
        length = float(geometry.attrib['length'])
        boxGeom = calculate_bounding_box(x, y, hdg, length)
        boxRoad.expandByBox(boxGeom)
    return boxRoad  


def reduceXODR(box, file_in, file_out):

    root = etree._Element()

    # read file and convert to tree structure    
    print(f"read file {file_in.stem}")
    try:
        tree = etree.parse(file_in)
        root = tree.getroot()
    except etree.ParseError as err:
        print(f'cant load {file_in.stem}: {err.msg}')
        return False
    
    roads = root.findall(".//road")
    for road in roads:
        boxRoad = getRoadBounding(road)
        if boxRoad.intersection(box) == False:
            root.remove(road)
        # TODO remove roads also vom junctions

    tree.write(file_out)


def main():
    parser = argparse.ArgumentParser(prog='main.py', description='removes the streets and intersections that are not in the specified bounding box and writes them out with *_reduce.xodr.')   
    parser.add_argument('filename', help='OpenDRIVE filename')
    parser.add_argument("--bbox", type=int, nargs=4, required=True,
                        metavar=("x_min", "y_min", "x_max", "y_max"),
                        help="bounding box as 4 values: x_min, y_min, x_max, y_max")
    args = parser.parse_args()
    
    # get box
    x_min, y_min, x_max, y_max = args.bbox
    box = Box2D(x_min, y_min, x_max, y_max)

    # get file
    file_in = Path(args.filename)
    file_out = file_in.with_stem(file_in.stem + "_reduced")

    # reduce
    reduceXODR(box, file_in, file_out)
    
if __name__ == '__main__':
    main()    