from typing import Tuple, List, Callable
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from lxml import etree
from enum import Enum

import xml.etree.ElementTree as ET
import logging
import typing
import json
import uuid
import os
import extractor

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s.%(msecs)03d [%(levelname)5s-%(name)s] {%(module)s -> %(funcName)s} %(message)s',
                    datefmt='%d/%m/%Y %H:%M:%S')
logging.getLogger(__name__).setLevel(logging.DEBUG)

version = 'v4'

SCRIPT_NAME = Path(__file__).name
IMPLEMENTED_OPENLABEL_TAGS = [
    'weatherWindValue',
    'weatherRainValue',
    'weatherSnowValue',
    'particulatesWaterValue',
    'daySunElevationValue',
    'illuminationCloudinessValue',
    'OddEnvironment',
    'EnvironmentWeather',
    'WeatherWind',
    'WeatherRain',
    'DaySunElevation',
    'IlluminationCloudiness',
    'EnvironmentIllumination',
    'IlluminationDay',
    'IlluminationLowLight',
    'LowLightAmbient',
    'LowLightNight',
    'IlluminationArtificial',
    'ArtificialVehicleLighting',
    'ArtificialStreetLighting',
    'RoadUserVehicle',
    'VehicleCycle',
    'RoadUserHuman',
    'HumanCyclist',
    'VehicleBus',
    'VehicleCar',
    'VehicleMotorcycle',
    'VehicleTailer',
    'VehicleTruck',
    'VehicleVan',
    'VehicleEmergency',
    'VehicleConstruction',
    'RoadUserAnimal',
    'HumanPedestrian',
    'HumanWheelchairUser',
    'VehicleWheelchair',
    'RoadUser',
    'trafficAgentTypeValue',
    'subjectVehicleSpeedValue',
    'ownerName',
    'ownerEmail',
    'ownerURL',
    'licenseURI',
    'scenarioName',
    'scenarioDescription',
    'scenarioVersion',
    'scenarioCreatedDate',
    'scenarioDefinition',
    'scenarioDefinitionLanguageURI',
    'scenarioParentReference',
    'scenarioUniqueReference',
    'scenarioVisualisationURL'
]


class OutputType(Enum):
    openlabel = 1


class NumTagType(Enum):
    value = 'value'
    min = 'min'
    max = 'max'


class VecTagType(Enum):
    values = 'values'
    range = 'range'


class OpenSCENARIO():

    def __init__(self) -> None:
        self.scenario_file: Path = None
        self.scenario_et: ET.Element = None
        self.catalog_locations: typing.Dict[str, typing.List[Path]] = {}
        self.catalogs: typing.Dict[str, typing.List[ET.Element]] = {}
        self.map_location: Path = None
        self.map_et: ET.Element = None
        self.variables: typing.Dict[str, str] = {}

    def __str__(self) -> str:
        ret = f'OpenSCENARIO: {self.scenario_file}\n\tMap: {self.map_location}\n\tCatalogs:\n'
        for name, catalogs in self.catalog_locations.items():
            ret += f'\t\t{name}: '
            for catalog in catalogs:
                ret += f'{catalog}, '
            if ret.endswith(', '):
                ret = ret[:-2]
            ret += '\n'
        return ret


class TagData(ABC):

    def __init__(self) -> None:
        super().__init__()
        self.k = 'tag_data'

    @abstractmethod
    def fill_tag_data(self, fill_dict: typing.Dict):
        pass

    @abstractmethod
    def is_empty(self):
        pass


class StringTag(TagData):

    def __init__(self, value: str) -> None:
        super().__init__()
        self.value: str = value

    def fill_tag_data(self, fill_dict: typing.Dict):
        fill_dict[self.k] = self.value

    def is_empty(self):
        return self.value is None


class BooleanTagValue():

    def __init__(self, value: bool, type: str = 'value', attributes: TagData = None, coordinate_system: str = None, name: str = None) -> None:
        self.value = value
        self.attributes = attributes
        self.coordinate_system = coordinate_system
        self.name = name
        self.type = type

    def to_dict(self) -> typing.Dict:
        ret = {
            'val': self.value
        }
        if self.name is not None:
            ret['name'] = self.name
        if self.coordinate_system is not None:
            ret['coordinate_system'] = self.coordinate_system
        if self.type is not None:
            ret['type'] = self.type
        if self.attributes is not None:
            self.attributes.fill_tag_data(ret, 'attributes')
        return ret


class BooleanTag(TagData):

    def __init__(self, values: typing.List[BooleanTagValue]) -> None:
        super().__init__()
        self.values: typing.List[BooleanTagValue] = values

    def fill_tag_data(self, fill_dict: typing.Dict):
        fill_dict[self.k] = {
            'boolean': []
        }
        for value in self.values:
            fill_dict[self.k]['boolean'].append(value.to_dict())

    def is_empty(self):
        return self.values is None or len(self.values) == 0


class NumTagValue():

    def __init__(self, value: float, type: NumTagType = None, attributes: TagData = None, coordinate_system: str = None, name: str = None) -> None:
        self.value = value
        self.attributes = attributes
        self.coordinate_system = coordinate_system
        self.name = name
        self.type = type

    def to_dict(self) -> typing.Dict:
        ret = {
            'val': self.value
        }
        if self.name is not None:
            ret['name'] = self.name
        if self.coordinate_system is not None:
            ret['coordinate_system'] = self.coordinate_system
        if self.type is not None:
            ret['type'] = self.type.value
        if self.attributes is not None:
            self.attributes.fill_tag_data(ret, 'attributes')
        return ret


class NumTag(TagData):

    def __init__(self, values: typing.List[NumTagValue]) -> None:
        super().__init__()
        self.values: typing.List[NumTagValue] = values

    def fill_tag_data(self, fill_dict: typing.Dict):
        fill_dict[self.k] = {
            'num': []
        }
        for value in self.values:
            fill_dict[self.k]['num'].append(value.to_dict())

    def is_empty(self):
        return self.values is None or len(self.values) == 0


class TextTagValue():

    def __init__(self, value: str, type: str = 'value', attributes: TagData = None, coordinate_system: str = None, name: str = None) -> None:
        self.value = value
        self.attributes = attributes
        self.coordinate_system = coordinate_system
        self.name = name
        self.type = type

    def to_dict(self) -> typing.Dict:
        ret = {
            'val': self.value
        }
        if self.name is not None:
            ret['name'] = self.name
        if self.coordinate_system is not None:
            ret['coordinate_system'] = self.coordinate_system
        if self.type is not None:
            ret['type'] = self.type
        if self.attributes is not None:
            self.attributes.fill_tag_data(ret, 'attributes')
        return ret


class TextTag(TagData):

    def __init__(self, values: typing.List[TextTagValue]) -> None:
        super().__init__()
        self.values: typing.List[TextTagValue] = values

    def fill_tag_data(self, fill_dict: typing.Dict):
        fill_dict[self.k] = {
            'text': []
        }
        for value in self.values:
            fill_dict[self.k]['text'].append(value.to_dict())

    def is_empty(self):
        return self.values is None or len(self.values) == 0 or all([v is None or v.value is None for v in self.values])


class VecTagValue():

    def __init__(self, value: typing.List, type: VecTagType = None, attributes: TagData = None, coordinate_system: str = None, name: str = None) -> None:
        self.value = value
        self.attributes = attributes
        self.coordinate_system = coordinate_system
        self.name = name
        self.type = type

    def to_dict(self) -> typing.Dict:
        ret = {
            'val': self.value
        }
        if self.name is not None:
            ret['name'] = self.name
        if self.coordinate_system is not None:
            ret['coordinate_system'] = self.coordinate_system
        if self.type is not None:
            ret['type'] = self.type.value
        if self.attributes is not None:
            self.attributes.fill_tag_data(ret, 'attributes')
        return ret


class VecTag(TagData):

    def __init__(self, values: typing.List[VecTagValue]) -> None:
        super().__init__()
        self.values: typing.List[VecTagValue] = values

    def fill_tag_data(self, fill_dict: typing.Dict):
        fill_dict[self.k] = {
            'vec': []
        }
        for value in self.values:
            fill_dict[self.k]['vec'].append(value.to_dict())

    def is_empty(self):
        return self.values is None or len(self.values) == 0


def get_conf_value(conf: typing.Dict, key: str, default: object = None) -> object:
    keys = key.split('/')
    c = conf
    for k in keys:
        if k in c:
            c = c[k]
        else:
            return default
    if c != conf:
        return c
    else:
        return default


def get_conf_value_v(conf: typing.Dict, key: str, default: object = None) -> object:
    keys = key.split('/')
    c = conf
    for k in keys:
        if k in c:
            c = c[k]
        else:
            return default
    if c != conf:
        return c
    else:
        return default


def extract_variables(osc: OpenSCENARIO, sc: ET.Element):
    for param_declaration in sc.findall('.//ParameterDeclaration'):
        osc.variables['$' + param_declaration.attrib['name']] = param_declaration.attrib['value']


def get_osc_value(el: ET.Element, key: str, osc: OpenSCENARIO) -> str:
    value = el.attrib[key]
    if '$' in value:
        if value in osc.variables:
            return osc.variables[value]
    return value


def load_openscenario_file(osc_path: Path) -> OpenSCENARIO:
    osc = OpenSCENARIO()
    osc.scenario_file = osc_path.resolve()
    sc = ET.parse(osc_path).getroot()
    osc.scenario_et = sc
    extract_variables(osc, sc)
    logic_file = sc.find('.//LogicFile')
    filepath = get_osc_value(logic_file, 'filepath', osc)
    osc.map_location = (
        osc_path.parent / filepath).resolve()
    logging.debug(f'Loading map {osc.map_location}')
    if not osc.map_location.exists():
        logging.error(f'map not exist {osc.map_location}')
        exit(1)
    if './/CatalogLocations' in sc:
        for catalog in sc.find('.//CatalogLocations'):
            if 'path' not in catalog.find('.//Directory').attrib or catalog.find('.//Directory').attrib['path'] == '':
                continue
            location = (osc_path.parent /
                        catalog.find('.//Directory').attrib['path']).resolve()
            osc.catalogs[catalog.tag] = []
            osc.catalog_locations[catalog.tag] = []
            if location.is_dir():
                for file in location.iterdir():
                    if file.name.endswith('osc') or file.name.endswith('xosc'):
                        logging.debug(f'Loading catalog {file}')
                        osc.catalogs[catalog.tag].append(ET.parse(file).getroot())
                        osc.catalog_locations[catalog.tag].append(file)
            elif location.is_file():
                logging.debug(f'Loading catalog {location}')
                osc.catalogs[catalog.tag].append(ET.parse(location).getroot())
    return osc


def add_coordinate_systems(scenario: OpenSCENARIO, coordinate_systems: typing.Dict) -> None:
    if scenario.scenario_et.find('.//WorldPosition') is not None:
        coordinate_systems['WORLD'] = {
            'type': 'geo',
            'parent': ''
        }


def add_ontologies(ontologies: typing.Dict, metadata_config: typing.Dict) -> typing.Tuple[str, str, str]:
    uuid_openlabel = str(uuid.uuid4())
    ontologies[uuid_openlabel] = {
        'uri': get_conf_value(metadata_config, 'openlabel/ontologies/openlabel/uri', 'https://openlabel.asam.net/V1-0-0/ontologies/openlabel_ontology_scenario_tags.ttl'),
        'boundary_list': IMPLEMENTED_OPENLABEL_TAGS,
        'boundary_mode': 'include'
    }
    uuid_setlevel = str(uuid.uuid4())
    ontologies[uuid_setlevel] = {
        'uri': get_conf_value(metadata_config, 'openlabel/ontologies/setlevel/uri', 'https://github.com/GAIA-X4PLC-AAD/map-and-scenario-data/blob/main/ontologies/setlevel/setlevel.ttl'),
        'boundary_list': [],
        'boundary_mode': 'include'
    }
    uuid_gaiax = str(uuid.uuid4())
    ontologies[uuid_gaiax] = {
        'uri': get_conf_value(metadata_config, 'openlabel/ontologies/gaiax/uri', 'https://github.com/GAIA-X4PLC-AAD/map-and-scenario-data/blob/main/ontologies/gaiax4plc/gaiax4plc_meta_auto.ttl'),
        'boundary_list': [],
        'boundary_mode': 'include'
    }
    return uuid_openlabel, uuid_setlevel, uuid_gaiax


def add_resources(scenario: OpenSCENARIO, resources: typing.Dict, metadata_config: typing.Dict) -> str:
    uuid_map = str(uuid.uuid4())
    relative_path = Path(scenario.map_location).relative_to(scenario.scenario_file.parent)
    resources[uuid_map] = get_conf_value(metadata_config, 'map/location', relative_path)
    for catalogs in scenario.catalog_locations.values():
        for catalog in catalogs:
            resources[str(uuid.uuid4())] = Path(catalog).relative_to(scenario.scenario_file.parent)
    return uuid_map


def add_tag(tags: typing.Dict, ontology_uid: str, tag_data: TagData, add_atts: typing.Dict) -> str:
    if tag_data is None or tag_data.is_empty():
        return None
    id = str(uuid.uuid4())
    tags[id] = {
        'ontology_uid': ontology_uid
    }
    tag_data.fill_tag_data(tags[id])
    for k, v in add_atts.items():
        tags[id][k] = v
    return id


def get_simple_attrib_or(el: ET.Element, att_key: str, default: str = '-'):
    if el is not None:
        if att_key in el.attrib:
            return el.attrib[att_key]
    return default


def get_sub_simple_attrib_or(el: ET.Element, sub_el_name: str, att_key: str, default: str = None):
    if el is not None:
        sub_el = el.find(f'.//{sub_el_name}')
        if sub_el is not None:
            if att_key in sub_el.attrib:
                return sub_el.attrib[att_key]
    return default


def analyze_environment(osc_environment: ET.Element, tags: typing.Dict, uuid_openlabel: str, wind_speeds: list, rain_values: list, snow_values: list, fog_visual_range_values: list, sun_elevation_values: list, fractional_cloud_cover_values: list, time_list: list):
    weather = osc_environment.find('.//Weather')
    weather_rain_value = '-'
    weather_snow_value = '-'
    cloud_state = get_simple_attrib_or(weather, 'cloudState')  # deprecated
    atmospheric_pressure = get_simple_attrib_or(weather, 'atmosphericPressue')
    temperature = get_simple_attrib_or(weather, 'temperature')
    fractional_cloud_cover = get_simple_attrib_or(
        weather, 'fractionalCloudCover')

    sun_azimuth = get_sub_simple_attrib_or(weather, 'Sun', 'azimuth')
    sun_elevation = get_sub_simple_attrib_or(weather, 'Sun', 'elevation')
    sun_intensity = get_sub_simple_attrib_or(
        weather, 'Sun', 'intensity')  # deprecated
    sun_illuminance = get_sub_simple_attrib_or(weather, 'Sun', 'illuminance')
    fog_visual_range = get_sub_simple_attrib_or(weather, 'Fog', 'visualRange')
    # ToDo maybe add fog Bounding Box? Required in meta data?
    precipitation_intensity = get_sub_simple_attrib_or(
        weather, 'Precipitation', 'intensity')  # deprecated
    precipitation_type = get_sub_simple_attrib_or(
        weather, 'Precipitation', 'precipitationType')
    precipitation_intensity = get_sub_simple_attrib_or(
        weather, 'Precipitation', 'precipitationIntensity')
    wind_direction = get_sub_simple_attrib_or(weather, 'Wind', 'direction')
    wind_speed = get_sub_simple_attrib_or(weather, 'Wind', 'speed')
    dome_image = weather.find('.//DomeImage')

    wind_speeds.append(wind_speed)
    if precipitation_type == 'rain':
        rain_values.append(precipitation_intensity)
    elif precipitation_type == 'snow':
        snow_values.append(precipitation_intensity)
    sun_elevation_values.append(sun_elevation)
    fractional_cloud_cover_values.append(fractional_cloud_cover)
    fog_visual_range_values.append(fog_visual_range)

    time_of_day = osc_environment.find('.//TimeOfDay')
    if time_of_day is not None:
        time = time_of_day.attrib['dateTime']
        try:
            dt = datetime.strptime(time, '%Y-%m-%dT%H:%M:%S')
        except:
            logging.exception(f'Unknown datetime of environment: {time}')


def add_list_tag(data: list, tags: typing.Dict, uuid_openlabel: str, tag_type: str):
    data = [x for x in data if x is not None]
    if len(data) == 1:
        val = data[0]
        add_tag(tags, uuid_openlabel, NumTag(
            [NumTagValue(val, type=NumTagType.value)]), {'type': tag_type})
    elif len(data) > 1:
        otype = type(data[0])
        for d in data:
            if type(d) != otype:
                otype = object
        if otype == int or otype == float:
            wmin = min(data)
            wmax = max(data)
            if wmin == wmax:
                add_tag(tags, uuid_openlabel, NumTag(
                    [NumTagValue(wmax, type=NumTagType.value)]), {'type': tag_type})
            else:
                add_tag(tags, uuid_openlabel, NumTag(
                    [NumTagValue(wmin, type=NumTagType.min), NumTagValue(wmax, type=NumTagType.max)]), {'type': tag_type})
        else:
            add_tag(tags, uuid_openlabel, VecTag(
                [VecTagValue(data, type=VecTagType.values)]), {'type': tag_type})
    else:
        add_tag(tags, uuid_openlabel, NumTag([]), {'type': tag_type})


def add_environment_tags(scenario: OpenSCENARIO, tags: typing.Dict, uuid_openlabel: str, uuid_setlevel: str, uuid_gaiax: str):
    environment_actions = scenario.scenario_et.findall('.//EnvironmentAction')
    wind_speeds = []
    rain_values = []
    snow_values = []
    fog_visual_range_values = []
    sun_elevation_values = []
    fractional_cloud_cover_values = []
    time_list: typing.List[datetime] = []
    for environment_action in environment_actions:
        if len(environment_action) == 1:
            if environment_action[0].tag == 'Environment':
                analyze_environment(
                    environment_action[0], tags, uuid_openlabel, wind_speeds, rain_values, snow_values, fog_visual_range_values, sun_elevation_values, fractional_cloud_cover_values, time_list)
            elif environment_action[0].tag == 'CatalogReference':
                cat_name = environment_action[0].attrib['catalogName']
                entry = environment_action[0].attrib['entryName']
                if cat_name in scenario.catalogs:
                    catalogs = scenario.catalogs[cat_name]
                    env = None
                    for catalog in catalogs:
                        env = catalog.find(f'.//Environment[@name="{entry}"]')
                        if env is not None:
                            break
                    if env is not None:
                        logging.debug(
                            f'Found environment "{entry}" in catalog {catalog}')
                        analyze_environment(
                            env, tags, uuid_openlabel, wind_speeds, rain_values, snow_values, fog_visual_range_values, sun_elevation_values, fractional_cloud_cover_values, time_list)
                    else:
                        logging.warning(
                            f'Could not find environment "{entry}" in given environment catalogs...')
                else:
                    logging.warning(
                        f'Cannot find environment catalog: {cat_name} in catalog definitions: {scenario.catalogs.keys()}')
            else:
                logging.warning(
                    f'Unknown tag for EnvironmentAction children: {environment_action[0].tag}')
        else:
            logging.warning(
                f'Wrong number of children ({len(environment_action)}) in EnvironmentAction: {environment_action}')

    add_list_tag(wind_speeds, tags, uuid_openlabel, 'weatherWindValue')
    add_list_tag(rain_values, tags, uuid_openlabel, 'weatherRainValue')
    add_list_tag(snow_values, tags, uuid_openlabel, 'weatherSnowValue')
    add_list_tag(fog_visual_range_values, tags,
                 uuid_openlabel, 'particulatesWaterValue')
    add_list_tag(sun_elevation_values, tags,
                 uuid_openlabel, 'daySunElevationValue')
    add_list_tag(fractional_cloud_cover_values, tags,
                 uuid_openlabel, 'illuminationCloudinessValue')
    if len(environment_actions) > 0:
        add_tag(tags, uuid_openlabel, None, {'type': 'OddEnvironment'})
        add_tag(tags, uuid_openlabel, None, {'type': 'EnvironmentWeather'})
    if len(wind_speeds) > 0:
        add_tag(tags, uuid_openlabel, None, {'type': 'WeatherWind'})
    if len(rain_values) > 0:
        add_tag(tags, uuid_openlabel, None, {'type': 'WeatherRain'})
    if len(sun_elevation_values) > 0:
        add_tag(tags, uuid_openlabel, None, {'type': 'DaySunElevation'})
        ''' ToDo
        DaySunPosition
        SunPositionFront
        SunPositionLeft
        SunPositionRight
        SunPositionBehind
        '''
    if len(fractional_cloud_cover_values) > 0:
        for fractional_cloud_cover in fractional_cloud_cover_values:
            if fractional_cloud_cover != 'zeroOktas':
                add_tag(tags, uuid_openlabel, None, {'type': 'IlluminationCloudiness'})
    time_tags = set()
    for time in time_list:
        if time.hour >= 8 and time.hour <= 18:
            time_tags.add('EnvironmentIllumination')
            time_tags.add('IlluminationDay')
        if (time.hour >= 6 and time.hour < 8) or (time.hour > 18 and time.hour <= 20):
            time_tags.add('EnvironmentIllumination')
            time_tags.add('IlluminationLowLight')
            time_tags.add('LowLightAmbient')
        if time.hour < 6 or time.hour > 20:
            time_tags.add('EnvironmentIllumination')
            time_tags.add('IlluminationLowLight')
            time_tags.add('LowLightNight')
    artifical_lights = ['daytimeRunningLights', 'lowBeam', 'highBeam', 'fogLights',
                        'fogLightsFront', 'fogLightsRear', 'warningLights', 'reversingLights', 'specialPurposeLights']
    for el in scenario.scenario_et.findall('.//VehicleLight'):
        if el.attrib['vehicleLightType'] in artifical_lights:
            time_tags.add('ArtificialVehicleLighting')
    ''' ToDo add class tags
    IlluminationArtificial -> OpenDRIVE type="streetlamp", subtype="streetlamp"
    ArtificialStreetLighting -> OpenDRIVE type="streetlamp", subtype="streetlamp"
    '''


def get_nth_parent_of(parent_map: dict, of: ET.Element, n):
    for _ in range(n):
        of = parent_map[of]
    return of


def action_belongs_to_entity(action: ET.Element, parent_map: dict, subj_id: str):
    third_parent = get_nth_parent_of(parent_map, action, 3)
    if third_parent.tag == 'Private':
        if third_parent.attrib['entityRef'] == subj_id:
            return True
    elif third_parent.tag == 'Action':
        seventh_parent = get_nth_parent_of(parent_map, action, 7)
        entity_refs = seventh_parent.findall('.//EntityRef')
        for entity_ref in entity_refs:
            if entity_ref.attrib['entityRef'] == subj_id:
                return True
    else:
        logging.warning(
            f'Unknown parent structure for {action}, 3rd parent is {third_parent.tag}')
    return False


def analyze_road_user(child: ET.Element, road_users: set):
    if child.tag == 'Vehicle':
        if child.attrib['vehicleCategory'] == 'bicycle':
            road_users.add('RoadUserVehicle')
            road_users.add('VehicleCycle')
            road_users.add('RoadUserHuman')
            road_users.add('HumanCyclist')
        elif child.attrib['vehicleCategory'] == 'bus':
            road_users.add('RoadUserVehicle')
            road_users.add('VehicleBus')
        elif child.attrib['vehicleCategory'] == 'car':
            road_users.add('RoadUserVehicle')
            road_users.add('VehicleCar')
        elif child.attrib['vehicleCategory'] == 'motorbike':
            road_users.add('RoadUserVehicle')
            road_users.add('VehicleMotorcycle')
        elif child.attrib['vehicleCategory'] == 'semitrailer':
            road_users.add('RoadUserVehicle')
            road_users.add('VehicleTailer')
        elif child.attrib['vehicleCategory'] == 'trailer':
            road_users.add('RoadUserVehicle')
            road_users.add('VehicleTailer')
        elif child.attrib['vehicleCategory'] == 'train':
            road_users.add('RoadUserVehicle')
            # Missing in OD/ODD Taxonomy
        elif child.attrib['vehicleCategory'] == 'tram':
            road_users.add('RoadUserVehicle')
            # Missing in OD/ODD Taxonomy
        elif child.attrib['vehicleCategory'] == 'truck':
            road_users.add('RoadUserVehicle')
            road_users.add('VehicleTruck')
        elif child.attrib['vehicleCategory'] == 'van':
            road_users.add('RoadUserVehicle')
            road_users.add('VehicleVan')
        else:
            logging.warning(
                f'Unknown vehicle category {child.attrib["vehicleCategory"]}')
        if 'role' in child.attrib:
            if child.attrib['role'] == 'ambulance' or child.attrib['role'] == 'police' or child.attrib['role'] == 'fire':
                road_users.add('VehicleEmergency')
            if child.attrib['role'] == 'roadAssistance':
                road_users.add('VehicleConstruction')
    elif child.tag == 'Pedestrian':
        if child.attrib['pedestrianCategory'] == 'animal':
            road_users.add('RoadUserAnimal')
        elif child.attrib['pedestrianCategory'] == 'pedestrian':
            road_users.add('RoadUserHuman')
            road_users.add('HumanPedestrian')
        elif child.attrib['pedestrianCategory'] == 'wheelchair':
            road_users.add('RoadUserHuman') #?
            road_users.add('HumanWheelchairUser')
            road_users.add('RoadUserVehicle') #?
            road_users.add('VehicleWheelchair')
        else:
            logging.warning(
                f'Unknown pedestrian category {child.attrib["pedestrianCategory"]}')
    elif child.tag == 'MiscObject':
        road_users.add('RoadUser') #?
    elif child.tag == 'ExternalObjectReference':
        road_users.add('RoadUser') #?
    else:
        road_users.add('RoadUser') #?


def analyze_traffic_agent_types(scenario: OpenSCENARIO, tags: typing.Dict, uuid_openlabel: str, uuid_setlevel: str, uuid_gaiax: str, metadata_config: typing.Dict):
    road_users = set()
    for el in scenario.scenario_et.findall('.//ScenarioObject'):
        child = el[0]
        if child.tag == 'CatalogReference':
            cat_name = get_osc_value(child, 'catalogName', scenario)
            entry_name = get_osc_value(child, 'entryName', scenario)
            for cat in scenario.catalogs[cat_name]:
                scat = cat.find(
                    f'.//Catalog[@name="{cat_name}"]')
                entry = scat.find(f'.//*[@name="{entry_name}"]')
                if entry is not None:
                    analyze_road_user(entry, road_users)
                else:
                    #pass
                    logging.warning(
                        f'Could not find element {entry_name} in catalog {cat_name}')
        else:
            analyze_road_user(child, road_users)
    add_list_tag(road_users, tags,
                 uuid_openlabel, 'trafficAgentTypeValue')
    for road_user in road_users:
        add_tag(tags, uuid_openlabel, None, {'type': road_user})


def analyze_subject_vehicle_speed(scenario: OpenSCENARIO, tags: typing.Dict, uuid_openlabel: str, uuid_setlevel: str, uuid_gaiax: str, metadata_config: typing.Dict):
    subj_veh = get_conf_value(
        metadata_config, 'openlabel/tags/subjectVehicle', None)
    if subj_veh is not None:
        parent_map = {c: p for p in scenario.scenario_et.iter() for c in p}
        speeds = []
        speed_actions = scenario.scenario_et.findall('.//SpeedAction')
        for speed_action in speed_actions:
            if action_belongs_to_entity(speed_action, parent_map, subj_veh):
                abs_speed = speed_action.find('.//AbsoluteTargetSpeed')
                if abs_speed is not None:
                    if abs_speed.attrib['value'].startswith('$'):
                        formula = abs_speed.attrib['value']
                        for var_name, var_value in scenario.variables.items():
                            formula = formula.replace(var_name, var_value)
                        if formula.startswith('${'):
                            formula = formula[2:]
                        if formula.endswith('}'):
                            formula = formula[:-1]
                        speed = eval(formula)
                        speed = float(speed)
                    else:
                        speed = float(abs_speed.attrib['value'])
                    # Meta data km/h, OpenSCENARIO m/s
                    speeds.append(speed * 3.6)
                # ToDo implement RelativeTargetSpeed
        speed_profile_actions = scenario.scenario_et.findall(
            './/SpeedProfileAction')
        for speed_profile_action in speed_profile_actions:
            if action_belongs_to_entity(speed_profile_action, parent_map, subj_veh):
                if 'entityRef' in speed_profile_action:
                    # ToDo implement RelativeTargetSpeed
                    pass
                else:
                    abs_speed = speed_action.find('.//SpeedProfileEntry')
                    if abs_speed is not None:
                        # Meta data km/h, OpenSCENARIO m/s
                        speeds.append(float(abs_speed.attrib['speed']) * 3.6)
        add_list_tag(speeds, tags,
                     uuid_openlabel, 'subjectVehicleSpeedValue')


def add_dynamic_tags(scenario: OpenSCENARIO, tags: typing.Dict, uuid_openlabel: str, uuid_setlevel: str, uuid_gaiax: str, metadata_config: typing.Dict):
    # ToDo trafficAgentDensityValue - Density (vehicles/km)
    # ToDo trafficVolumeValue - Volume (vehicle km)
    # ToDo trafficFlowRateValue - Rate (vehicles/h)

    analyze_traffic_agent_types(
        scenario, tags, uuid_openlabel, uuid_setlevel, uuid_gaiax, metadata_config)
    analyze_subject_vehicle_speed(
        scenario, tags, uuid_openlabel, uuid_setlevel, uuid_gaiax, metadata_config)
    # ToDo motionAccelerateValue - Rate of acceleration (ms-2)
    # ToDo motionDriveValue - Speed (km/h)
    # ToDo motionDecelerateValue - Rate of deceleration (ms-2)
    ''' ToDo add dynamic class tags
    OddDynamicElements
    DynamicElementsTraffic
    TrafficAgentDensity
    TrafficVolume
    TrafficFlowRate
    TrafficAgentType
    TrafficSpecialVehicle
    DynamicElementsSubjectVehicle
    SubjectVehicleSpeed
    AdminTag
    Behaviour
    BehaviourMotion
    MotionAccelerate
    MotionDrive
    MotionDecelerate
    MotionLaneChangeLeft
    MotionLaneChangeRight
    MotionReverse
    MotionRun
    MotionSlide
    MotionStop
    MotionTurn
    MotionTurnLeft
    MotionTurnRight
    MotionWalk
    MotionCross
    MotionCutIn
    MotionCutOut
    MotionAway
    MotionTowards
    MotionOvertake
    MotionUTurn
    BehaviourCommunication
    CommunicationHeadlightFlash
    CommunicationSignalEmergency
    CommunicationSignalLeft
    CommunicationSignalRight
    CommunicationSignalSlowing
    CommunicationSignalHazard
    CommunicationHorn
    CommunicationWave
    '''


def add_static_tags(scenario: OpenSCENARIO, tags: typing.Dict, uuid_openlabel: str, uuid_setlevel: str, uuid_gaiax: str):
    environment_actions = scenario.scenario_et.findall('.//EnvironmentAction')
    # ToDo horizontalCurvesValue
    # ToDo longitudinalUpSlopeValue
    # ToDo longitudinalDownSlopeValue
    # ToDo laneSpecificationDimensionsValue
    # ToDo laneSpecificationLaneCountValue
    ''' ToDo add static class tags
    OddScenery
    SceneryZone
    ZoneGeoFenced
    ZoneTrafficManagement
    ZoneSchool
    ZoneRegion
    ZoneInterference
    SceneryDrivableArea
    DrivableAreaType
    RoadTypeMotorway
    MotorwayManaged
    MotorwayUnmanaged
    RoadTypeRadial
    RoadTypeDistributor
    RoadTypeMinor
    RoadTypeSlip
    RoadTypeParking
    RoadTypeShared
    DrivableAreaGeometry
    GeometryHorizontal
    HorizontalStraights
    HorizontalCurves
    GeometryTransverse
    TransverseDivided
    TransverseUndivided
    TransversePavements
    TransverseBarriers
    TransverseLanesTogether
    GeometryLongitudinal
    LongitudinalUpSlope
    LongitudinalDownSlope
    LongitudinalLevelPlane
    DrivableAreaLaneSpecification
    LaneSpecificationDimensions
    LaneSpecificationMarking
    LaneSpecificationType
    LaneTypeBus
    LaneTypeCycle
    LaneTypeEmergency
    LaneTypeSpecial
    LaneTypeTram
    LaneTypeTraffic
    LaneSpecificationLaneCount
    LaneSpecificationTravelDirection
    TravelDirectionLeft
    TravelDirectionRight
    DrivableAreaSigns
    SignsInformation
    InformationSignsUniform
    InformationSignsUniformFullTime
    InformationSignsUniformTemporary
    InformationSignsVariable
    InformationSignsVariableFullTime
    InformationSignsVariableTemporary
    SignsRegulatory
    RegulatorySignsUniform
    RegulatorySignsUniformFullTime
    RegulatorySignsUniformTemporary
    RegulatorySignsVariable
    RegulatorySignsVariableFullTime
    RegulatorySignsVariableTemporary
    SignsWarning
    WarningSignsUniform
    WarningSignsUniformFullTime
    WarningSignsUniformTemporary
    WarningSignsVariable
    WarningSignsVariableFullTime
    WarningSignsVariableTemporary
    DrivableAreaEdge
    EdgeLineMarkers
    EdgeShoulderPavedOrGravel
    EdgeShoulderGrass
    EdgeSolidBarriers
    EdgeTemporaryLineMarkers
    EdgeNone
    DrivableAreaSurface
    DrivableAreaSurfaceType
    SurfaceTypeLoose
    SurfaceTypeSegmented
    SurfaceTypeUniform
    DrivableAreaSurfaceFeature
    SurfaceFeatureCrack
    SurfaceFeaturePothole
    SurfaceFeatureRut
    SurfaceFeatureSwell
    DrivableAreaSurfaceCondition
    SurfaceConditionIcy
    SurfaceConditionFlooded
    SurfaceConditionMirage
    SurfaceConditionSnow
    SurfaceConditionStandingWater
    SurfaceConditionWet
    SurfaceConditionContamination
    SceneryJunction
    JunctionIntersection
    IntersectionTJunction
    IntersectionStaggered
    IntersectionYJunction
    IntersectionCrossroad
    IntersectionGradeSeperated
    JunctionRoundabout
    RoundaboutNormal
    RoundaboutNormalNosignal
    RoundaboutNormalSignal
    RoundaboutCompact
    RoundaboutCompactNosignal
    RoundaboutCompactSignal
    RoundaboutDouble
    RoundaboutDoubleNosignal
    RoundaboutDoubleSignal
    RoundaboutLarge
    RoundaboutLargeNosignal
    RoundaboutLargeSignal
    RoundaboutMini
    RoundaboutMiniNosignal
    RoundaboutMiniSignal
    ScenerySpecialStructure
    SpecialStructureAutoAccess
    SpecialStructureBridge
    SpecialStructurePedestrianCrossing
    SpecialStructureRailCrossing
    SpecialStructureTunnel
    SpecialStructureTollPlaza
    SceneryFixedStructure
    FixedStructureBuilding
    FixedStructureStreetlight
    FixedStructureStreetFurniture
    FixedStructureVegetation
    SceneryTemporaryStructure
    TemporaryStructureConstructionDetour
    TemporaryStructureRefuseCollection
    TemporaryStructureRoadWorks
    TemporaryStructureRoadSignage
    '''


def add_simple_tags(scenario: OpenSCENARIO, tags: typing.Dict, uuid_openlabel: str, uuid_setlevel: str, uuid_gaiax: str, metadata_config: typing.Dict):
    for tag in get_conf_value(metadata_config, 'openlabel/simpleTags', []):
        add_tag(tags, uuid_openlabel, None, {'type': tag})


def add_tags(scenario: OpenSCENARIO, tags: typing.Dict, uuid_openlabel: str, uuid_setlevel: str, uuid_gaiax: str, metadata_config: typing.Dict, prev_scenario_uuid: str) -> None:
    header = scenario.scenario_et.find('.//FileHeader')
    add_tag(tags, uuid_openlabel, TextTag([TextTagValue(get_conf_value(
        metadata_config, 'general/author', header.attrib['author']))]),
        {'type': 'ownerName'})
    add_tag(tags, uuid_openlabel, TextTag([TextTagValue(get_conf_value(
        metadata_config, 'openlabel/tags/ownerEmail', None))]),
        {'type': 'ownerEmail'})
    add_tag(tags, uuid_openlabel, TextTag([TextTagValue(get_conf_value(
        metadata_config, 'openlabel/tags/ownerURL', None))]),
        {'type': 'ownerURL'})
    license = None
    license_att = header.find('.//License')
    if license_att is not None:
        license = license_att.attrib['resource']
    add_tag(tags, uuid_openlabel, TextTag([TextTagValue(get_conf_value(
        metadata_config, 'openlabel/tags/licenseURI', license))]),
        {'type': 'licenseURI'})

    add_tag(tags, uuid_openlabel, TextTag([TextTagValue(get_conf_value(
        metadata_config, 'general/name', header.attrib['description']))]),
        {'type': 'scenarioName'})
    add_tag(tags, uuid_openlabel, TextTag([TextTagValue(header.attrib['description'])]),
            {'type': 'scenarioDescription'})
    add_tag(tags, uuid_openlabel, TextTag([TextTagValue(header.attrib['revMajor'] + '.' + header.attrib['revMinor'])]),
            {'type': 'scenarioVersion'})
    add_tag(tags, uuid_openlabel, TextTag([TextTagValue(header.attrib['date'])]),
            {'type': 'scenarioCreatedDate'})
    add_tag(tags, uuid_openlabel, TextTag([TextTagValue(get_conf_value(
        metadata_config, 'openlabel/tags/scenarioDefinition',
        f'OpenSCENARIO {header.attrib["revMajor"]}.{header.attrib["revMinor"]}'))]),
        {'type': 'scenarioDefinition'})
    add_tag(tags, uuid_openlabel, TextTag([TextTagValue(get_conf_value(
        metadata_config, 'openlabel/tags/scenarioDefinitionLanguageURI',
        f'https://www.asam.net/static_downloads/ASAM_OpenSCENARIO_V{header.attrib["revMajor"]}.{header.attrib["revMinor"]}.0_Model_Documentation/modelDocumentation/'))]),
        {'type': 'scenarioDefinitionLanguageURI'})
    add_tag(tags, uuid_openlabel, TextTag([TextTagValue(get_conf_value(metadata_config, 'openlabel/tags/scenarioParentReference', None))]),
            {'type': 'scenarioParentReference'})
    sc_uuid = str(
        uuid.uuid4()) if prev_scenario_uuid is None else prev_scenario_uuid
    add_tag(tags, uuid_openlabel, TextTag([TextTagValue(get_conf_value(metadata_config, 'openlabel/tags/scenarioUniqueReference', sc_uuid))]),
            {'type': 'scenarioUniqueReference'})
    add_tag(tags, uuid_openlabel, TextTag([TextTagValue(get_conf_value(metadata_config, 'openlabel/tags/scenarioVisualisationURL', None))]),
            {'type': 'scenarioVisualisationURL'})

    add_environment_tags(scenario, tags, uuid_openlabel,
                         uuid_setlevel, uuid_gaiax)
    add_dynamic_tags(scenario, tags, uuid_openlabel,
                     uuid_setlevel, uuid_gaiax, metadata_config)
    add_static_tags(scenario, tags, uuid_openlabel, uuid_setlevel, uuid_gaiax)
    add_simple_tags(scenario, tags, uuid_openlabel,
                    uuid_setlevel, uuid_gaiax, metadata_config)


def find_tag(tag_name: str, d, path: str):
    if type(d) is dict:
        for k, v in d.items():
            if k == 'type' and v == tag_name:
                return path
            if type(v) is dict:
                npath = k if path == '' else path + '/' + k
                id = find_tag(tag_name, v, npath)
                if id is not None:
                    return id


def get_tag(path: str, d: dict):
    for part in path.split('/'):
        d = d[part]
    return d


def generate_openlabel_metadata(scenario: OpenSCENARIO, out_file: Path, metadata_config: typing.Dict = None) -> None:
    metadata = {}
    coordinate_systems = {}
    ontologies = {}
    resources = {}
    tags = {}
    output = {
        'openlabel': {
            'metadata': metadata,
            'coordinate_systems': coordinate_systems,
            'ontologies': ontologies,
            'resources': resources,
            'tags': tags,
        }
    }
    metadata['schema_version'] = '1.0.0'
    metadata['annotator'] = get_conf_value(
        metadata_config, 'general/author', f'GAIA-X - {SCRIPT_NAME} by DLR')
    metadata['comment'] = get_conf_value(
        metadata_config, 'general/comment', f'Automatically generated metadata by {SCRIPT_NAME} ©DLR')
    prev_scenario_uuid = None
    if out_file.exists():
        with open(out_file, 'r') as f:
            prev_meta = json.load(f)
        prev_vers = prev_meta['openlabel']['metadata']['file_version']
        prev_scenario_path = find_tag('scenarioUniqueReference', prev_meta, '')
        prev_scenario_uuid = get_tag(prev_scenario_path, prev_meta)[
            'tag_data']['text'][0]['val']
        index = prev_vers.rindex('.')
        prev_maj = prev_vers[:index]
        prev_min = int(prev_vers[index + 1:])
        metadata['file_version'] = f'{prev_maj}.{prev_min + 1}'
    else:
        metadata['file_version'] = '1.0'
    metadata['name'] = get_conf_value(metadata_config, 'general/name', scenario.scenario_et.find(
        './/FileHeader').attrib['description'])
    metadata['tagged_file'] = Path(scenario.scenario_file).relative_to(Path.cwd())
    add_coordinate_systems(scenario, coordinate_systems)
    uuid_openlabel, uuid_setlevel, uuid_gaiax = add_ontologies(
        ontologies, metadata_config)
    add_resources(scenario, resources, metadata_config)
    add_tags(scenario, tags, uuid_openlabel,
             uuid_setlevel, uuid_gaiax, metadata_config, prev_scenario_uuid)
    with open(out_file, 'w') as f:
        json.dump(output, f, indent=4)


def find_files_with_ending(parent: Path, ending: str, files: typing.List[Path]) -> None:
    if parent.is_dir():
        for file in parent.iterdir():
            find_files_with_ending(file, ending, files)
    elif parent.is_file():
        if parent.name.endswith(ending):
            files.append(parent)


def get_scenario_files(scenario_dir: Path):
    logging.debug(f'Finding OSC files in {scenario_dir}')
    osc_files = []
    find_files_with_ending(scenario_dir, '.xosc', osc_files)
    scenario_files = []
    for osc_file in osc_files:
        try: 
            root = ET.parse(osc_file).getroot()
            if root.find('.//Storyboard') is not None:
                scenario_files.append(osc_file)
            else:
                logging.debug(f'Not analyzing {osc_file} since it is not a Scenario (probably a catalog)')
        except:
            logging.exception(f'Could not read {osc_file} - not generating meta data for it.')
    return scenario_files


def default_one_filler(sc_header: etree._Element, header_attribs: List[str], seperator: str = ', '):
    if len(header_attribs) == 1:
        return sc_header.attrib[header_attribs[0]]
    else:
        value = ''
        for header_attrib in header_attribs:
            value += sc_header.attrib[header_attrib] + seperator
        if value.endswith(seperator):
            value = value[:-len(seperator)]
        return value


def fill_from_header_value(meta_data_dict: dict, meta_keyword: str, sc_header: etree._Element, header_attribs: List[str], default_value: str, fill_method: Callable = default_one_filler):
    if sc_header is not None:
        are_present = True
        for header_attrib in header_attribs:
            if header_attrib not in sc_header.attrib:
                are_present = False
                break
        if are_present:
            meta_data_dict[meta_keyword] = fill_method(sc_header, header_attribs)
        else:
            meta_data_dict[meta_keyword] = default_value
    else:
        meta_data_dict[meta_keyword] = default_value

def register_links(links_dic, dict_name, links):
    if len(links):
        links_data = list()
        for link in links:
            link_data = dict()            
            link_data['manifest:accessRole'] =  'owner'
            link_data['manifest:type'] = 'assetData'
            file_meta_data = dict()
            link_data['manifest:fileMetaData'] =  file_meta_data
            file_meta_data['manifest:uri'] =  link
            file_meta_data['manifest:filename'] =  os.path.basename(link)
            if os.path.exists(link):
                file_meta_data['manifest:fileSize'] =  os.path.getsize(link)
            links_data.append(link_data)
        links_dic[dict_name] = links_data


def get_general_meta_data(meta_data_dict: dict, osc: OpenSCENARIO, file_path: Path, default_value: str = "Unknown", unknown_unit: str = "Unknown Unit") -> dict:
    sc_header = osc.scenario_et.find('.//FileHeader')

    ### description
    #meta_data_dict['scenario:type'] = 'scenario'
    general_dict = dict()
    description_dict = dict()
    description_dict['general:name'] = file_path.name.replace('.xosc', '')
    fill_from_header_value(description_dict, 'general:description', sc_header, ['description'], default_value)
    general_dict['general:description'] = description_dict

    ### format
    format_dict = dict()
    format_dict['scenario:formatType'] = 'ASAM OpenSCENARIO'
    fill_from_header_value(format_dict, 'scenario:version', sc_header, ['revMajor', 'revMinor'], default_value, lambda sc_header, _: f'{sc_header.attrib["revMajor"]}.{sc_header.attrib["revMinor"]}')
    meta_data_dict['scenario:format'] = format_dict

    ### vendor
    #fill_from_header_value(meta_data_dict, 'vendor_name', sc_header, ['author'], default_value)
    data_dict = dict()
    fill_from_header_value(data_dict, 'general:recordingTime', sc_header, ['date'], default_value)
    general_dict['general:data'] = data_dict
    meta_data_dict['scenario:general'] = general_dict

    ### position
    #meta_data_dict['country'] = default_value
    #meta_data_dict['bounding'] = default_value

    ### links
    if 'scenario:content' in meta_data_dict:
        links_dic = meta_data_dict['scenario:content']
    else:
        links_dic = dict()
        meta_data_dict['scenario:content'] = links_dic

    # get catalog
    links = list()
    catalog_locations = osc.scenario_et.find('.//CatalogLocations')
    if catalog_locations is not None:        
        for catalog in catalog_locations:
            path = catalog.find('Directory').attrib['path']
            if len(path):
                links.append(path)
    # register
    register_links(links_dic, 'scenario:catalogs', links)
    links.clear()
    
    # environment model
    scene_graph_file = osc.scenario_et.find('.//SceneGraphFile')
    if scene_graph_file is not None:
        links.append(scene_graph_file.attrib['filepath'])
    # register
    register_links(links_dic, 'scenario:environmentModels', links)
    links.clear()

    # trafficSpace
    road_network = osc.scenario_et.find('.//LogicFile')
    if road_network is not None:
        links.append(road_network.attrib['filepath'])
    # register
    register_links(links_dic, 'scenario:trafficSpace', links)
    links.clear()

    ### licence
    if sc_header is not None:
        license = sc_header.find('.//License')
        if license is not None:
            links_data = list()
            link_data = dict()
            link_data['manifest:type'] = 'Document'
            #meta_data_dict['licence_type'] = license.attrib['name']
            if 'resource' in license.attrib:
                link_data['manifest:url'] = license.attrib['resource']
            links_data.append(link_data)
            # not used yet -> should be defined in manifest file
            # links_dic['general:media'] = link_data


def convert_env_to_string(env: etree._Element) -> str:
    val = ''
    tod = env.find('TimeOfDay')
    val += f'time of day: {tod.attrib["dateTime"]}'
    weather = env.find('Weather')
    val += f', 	CloudState: {weather.attrib["cloudState"]}'
    sun =  weather.find('Sun')
    val += f', 	sun intensity: {sun.attrib["intensity"]}'
    val += f', 	sun azimuth: {sun.attrib["azimuth"]}'
    val += f', 	sun elevation: {sun.attrib["elevation"]}'
    fog =  weather.find('Fog')
    val += f', 	visuale range: {fog.attrib["visualRange"]}'
    precipitation =  weather.find('Precipitation')
    val += f', 	precipitation type: {precipitation.attrib["precipitationType"]}'
    val += f', 	precipitation intensity: {precipitation.attrib["intensity"]}'
    return val


def get_osc_meta_data(meta_data_dict: dict, osc: OpenSCENARIO, file_path: Path, default_value: str = "Unknown", unknown_unit: str = "Unknown Unit") -> dict:
    vehicles = []
    pedestrians = []
    misc_objects = []
    external_object_references = []
    environ_actions = []
    controllers = []
    user_defined_actions = []
    time_of_days = []
    time_of_days.extend(osc.scenario_et.findall('.//TimeOfDay'))
    controllers.extend(osc.scenario_et.findall('.//Controller'))
    vehicles.extend(osc.scenario_et.findall('.//Vehicle'))
    pedestrians.extend(osc.scenario_et.findall('.//Pedestrian'))
    misc_objects.extend(osc.scenario_et.findall('.//MiscObject'))
    external_object_references.extend(osc.scenario_et.findall('.//ExternalObjectReference'))
    environ_actions.extend(osc.scenario_et.findall('.//EnvironmentAction'))
    user_defined_actions.extend(osc.scenario_et.findall('.//UserDefinedAction'))
    for catalogs in osc.catalogs.values():
        for catalog in catalogs:
            vehicles.extend(catalog.findall('.//Vehicle'))
            pedestrians.extend(catalog.findall('.//Pedestrian'))
            misc_objects.extend(catalog.findall('.//MiscObject'))
            external_object_references.extend(catalog.findall('.//ExternalObjectReference'))    
            environ_actions.extend(catalog.findall('.//EnvironmentAction'))
            controllers.extend(catalog.findall('.//Controller'))    
            time_of_days.extend(catalog.findall('.//TimeOfDay'))
    
    ### quantity 
    # participants    
    quantity_dict = dict()
    number_traffic_objects = 0
    number_traffic_objects += len(vehicles)
    number_traffic_objects += len(pedestrians)
    number_traffic_objects += len(misc_objects)
    number_traffic_objects += len(external_object_references)
    quantity_dict['scenario:numberTrafficObjects'] = str(number_traffic_objects)
    #meta_data_dict['temporary_traffic_objects'] = default_value # TODO
    #meta_data_dict['permanent_traffic_objects'] = default_value # TODO
    traffic_participant_types = set()
    if len(pedestrians)> 0:
        traffic_participant_types.add('pedestrian')
    for veh in vehicles:
        traffic_participant_types.add(veh.attrib['vehicleCategory'])
    #meta_data_dict['traffic_participant_types'] = ', '.join(map(str, traffic_participant_types))
    #meta_data_dict['scenario:movementDescription'] = default_value
    controller_names = set()
    for controller in controllers:
        if 'controllerType' in controller.attrib:
            controller_names.add(f'{controller.attrib["controllerType"]}: {controller.attrib["name"]}')
        else:
            controller_names.add(controller.attrib['name'])
    if controllers:            
        quantity_dict['scenario:controllers'] = list(controller_names)

    meta_data_dict['scenario:quantity'] = quantity_dict
    
    ##### content
    if 'scenario:content' in meta_data_dict:
        content_dict = meta_data_dict['scenario:content']
    else:
        content_dict = dict()
        meta_data_dict['scenario:content'] = content_dict

    custom_commands = set()
    for user_defined_action in user_defined_actions:
        custom_commands.add(user_defined_action.attrib['type'])
    if len(custom_commands):
        content_dict['scenario:customCommands'] = ', '.join(map(str, custom_commands))

    ### common data
    if not file_path.name.endswith('.xosc'): # OpenSCENARIO DSL
        content_dict['scenario:abstractionLevel'] = 'Functional'
    if osc.scenario_et.find('.//ParameterValueDistributionDefinition') is not None:
        content_dict['scenario:abstractionLevel'] = 'Logical'
    elif osc.scenario_et.find('.//ScenarioDefinition') is not None:
        content_dict['scenario:abstractionLevel'] = 'Concrete'
    #else: 
    #    common_dict['scenario:abstractionLevel'] = default_value

    time_date = default_value
    if time_of_days is not None and len(time_of_days) > 0:
        time_date = ''
        separator = ', '
        for time_of_day in time_of_days:
            time_date += time_of_day.attrib['dateTime'] + separator
        if time_date.endswith(separator):
            time_date = time_date[:-len(separator)]
        content_dict['scenario:timeDate'] = time_date
    osc_tags = set()
    for el in osc.scenario_et.findall('.//'):
        osc_tags.add(el.tag)
    content_dict['scenario:usedStandardFunctions'] = ', '.join(map(str, osc_tags))
    #content_dict['scenario:aim'] = default_value      

    # environmental
    if len(environ_actions) > 0:
        separator = ', '
        environment_conditions = set()
        sun_elevation = set()
        sun_azimuth = set()
        wetness = set()
        for environ_action in environ_actions:
            env = environ_action.find('.//Environment')
            if env is not None:
                environment_conditions += convert_env_to_string + separator
                sun = env.find('.//Sun')
                if sun is not None:
                    sun_elevation.add(sun.attrib['elevation'])
                    sun_azimuth.add(sun.attrib['azimuth'])
                precipitation = env.find('.//Precipitation')
                if precipitation is not None:
                    wetness.add(precipitation.attrib['precipitationType'])
        #meta_data_dict['environment_conditions'] = ', '.join(map(str, environment_conditions))
        #meta_data_dict['sun_elevation'] = ', '.join(map(str, sun_elevation))
        content_dict['scenario:sunAzimuth'] = ', '.join(map(str, sun_azimuth))
        #meta_data_dict['wetness'] = ', '.join(map(str, wetness))

    # traffic
    country_specific_sign = set()
    if osc.map_et is not None:
        roads = osc.map_et.findall('.//road')
        if len(roads) > 0:
            rules = set()
            for road in roads:
                if 'rule' in road.attrib:
                    rules.add(road.attrib['rule'])
            #meta_data_dict['rule_of_the_road'] = ', '.join(map(str, rules))
        for signal in osc.map_et.findall('.//signal'):
            if signal.attrib['country'] != 'OpenDRIVE':
                country_specific_sign.add(f'{signal.attrib["country"]}:{signal.attrib["type"]}')

    misc_objects = osc.scenario_et.findall('.//MiscObject')
    country_specific_tp = set()
    for misc_object in misc_objects:
        country_specific_tp.add(misc_object.attrib['name'])
    if len(country_specific_tp):
        content_dict['scenario:countrySpecificTrafficParticipants'] = ', '.join(map(str, country_specific_tp))

    if len(country_specific_sign):
        content_dict['scenario:countrySpecificSign'] = ', '.join(map(str, country_specific_sign))

    ### Data_Sources
    #meta_data_dict['data_source'] = default_value


def get_meta_data(osc: OpenSCENARIO, file_path: Path, default_value: str = "Unknown", unknown_unit: str = "Unknown Unit") -> dict:
    
    meta_data_dict = dict()
    meta_data_dict['did'] = 'did:web:registry.gaia-x.eu:Scenario:' + extractor.generate_global_unique_id()
    meta_data_dict['shacle_type'] = f'{get_schema_name().lower()}::{get_namespace()}#{get_schema_name()}Shape'
    get_general_meta_data(meta_data_dict, osc, file_path, default_value, unknown_unit)
    get_osc_meta_data(meta_data_dict, osc, file_path, default_value, unknown_unit)

    return meta_data_dict


def extract_meta_data(file: Path) -> Tuple[bool, dict]:

    # read file
    logging.debug(f'Loading input file {file.absolute()}')
    try: 
        with open(file, 'r') as f:
            _ = f.read()
    except:
        logging.exception(f'Cannot read file {file.absolute()}')
        return False
    
    # parse xml
    try: 
        osc = load_openscenario_file(file)
    except:
        logging.exception(f'Cannot parse XML from file {file.absolute()}')
        return False
    
    try:
        attributes = get_meta_data(osc, file)
    except:
        logging.exception(f'Cannot extract from file {file.absolute()}')
        return False
    
    logging.info(f'Extract from file {file}')
    return True, attributes
    
def get_description() -> str:
    return 'extract OpenSCENARIO'

def get_schema_name() -> str:
    return 'Scenario'

def get_namespace() -> str:
    return f'https://ontologies.envited-x.net/{get_schema_name().lower()}/{version}/ontology'