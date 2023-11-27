import functools
import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import cv2
import numpy as np
import yaml
from UE4Parse.Assets.PackageReader import EPackageLoadMode, Package

from helpers import closed_multiple, rotate_image, FoxholeFileProvider


@dataclass
class Vector:
    x: float
    y: float
    z: float


@dataclass
class Point:
    x: int
    y: int


@dataclass
class Size:
    width: int
    height: int


class Tile(object):
    name: str
    display: bool

    def __init__(self, name: str):
        self.name = name
        self.display = True

    def __eq__(self, other):
        return self.number == other.number

    def __lt__(self, other):
        return self.number < other.number

    def __le__(self, other):
        return self.number <= other.number

    def __gt__(self, other):
        return self.number > other.number

    def __ge__(self, other):
        return self.number >= other.number

    def __hash__(self):
        return self.name

    @classmethod
    def from_heightmap_dict(cls, heightmap_texture_dict):
        try:
            heightmap_texture_name = re.search(r'Texture2D_\d+', heightmap_texture_dict["ObjectName"]).group()
            return cls(heightmap_texture_name)
        except KeyError as e:
            print(f"⚠️\tMissing property {e} for {heightmap_texture_dict}")
            return None
        except AttributeError as e:
            print(f"❗\tCannot extract name for {heightmap_texture_dict['ObjectName']}")
            return None

    @classmethod
    def from_weightmap_dict(cls, weightmap_textures_dict):
        try:
            return [cls(re.search(r'Texture2D_\d+', weightmap["ObjectName"]).group()) for weightmap in weightmap_textures_dict]
        except KeyError as e:
            print(f"⚠️\tMissing property {e} for {landscape_component['Name']}")
            return None
        except AttributeError as e:
            print(f"❗\tCannot extract name for {landscape_component['Name']}")
            return None

    @property
    def number(self) -> int:
        return int(self.name.split('_')[-1])


class LandscapeComponent(object):
    name: str
    pos: Point
    heightmap_tile: Tile
    weightmap_tiles: List[Tile]
    road_index: int
    road_channel: int

    def __init__(self, name: str, pos: Point, heightmap_tile: Tile, weightmap_tiles: List[Tile], road_index: int, road_channel: int):
        self.name = name
        self.pos = pos
        self.heightmap_tile = heightmap_tile
        self.weightmap_tiles = weightmap_tiles

    def __repr__(self):
        return self.name

    def __eq__(self, other):
        return self.heightmap_tile.number == other.heightmap_tile.number

    def __lt__(self, other):
        return self.heightmap_tile.number < other.heightmap_tile.number

    def __le__(self, other):
        return self.heightmap_tile.number <= other.heightmap_tile.number

    def __gt__(self, other):
        return self.heightmap_tile.number > other.heightmap_tile.number

    def __ge__(self, other):
        return self.heightmap_tile.number >= other.heightmap_tile.number

    def __hash__(self):
        return self.heightmap_tile.name

    @classmethod
    def from_dict(cls, landscape_component_dict: Dict):
        try:
            x = closed_multiple((landscape_component_dict["Properties"]["RelativeLocation"]["X"]), 64)
            y = closed_multiple((landscape_component_dict["Properties"]["RelativeLocation"]["Y"]), 64)
            name = landscape_component_dict["Name"]
            heightmap_tile = Tile.from_heightmap_dict(landscape_component_dict["Properties"]["HeightmapTexture"])
            weightmap_tiles = Tile.from_weightmap_dict(landscape_component_dict["Properties"]["WeightmapTextures"])
            road_index = None
            road_channel = None
            for alloc in landscape_component_dict["Properties"]["WeightmapLayerAllocations"]:
                if alloc["LayerInfo"]["ObjectName"] == "Road_LayerInfo":
                    road_index = alloc["WeightmapTextureIndex"]
                    road_channel = alloc["WeightmapTextureChannel"]
            return cls(name, Point(x, y), heightmap_tile, weightmap_tiles, road_index, road_channel)
        except KeyError as e:
            print(f"⚠️\tMissing property {e} for {landscape_component_dict['Name']}")
            return None
        except AttributeError as e:
            print(f"❗\tCannot extract name for {landscape_component_dict['Name']}")
            return None


class Landscape(object):
    name: str
    raw_components: List
    texture_components: Dict
    tiles_misplaced: Dict
    tiles_missing: Dict
    landscape_components: Dict[str, LandscapeComponent]
    top_left: Point
    bottom_right: Point
    relative_location: Vector
    relative_rotation: Vector

    def __init__(self, name: str, tiles_misplaced: dict, tiles_missing: dict, raw_components: list,
                 texture_components: list, root_component: dict):
        self.name = name
        self.raw_components = raw_components
        self.tiles_misplaced = tiles_misplaced
        self.tiles_missing = tiles_missing
        self.texture_components = {texture['Name']: texture for texture in texture_components}
        self.landscape_components = dict()
        self.top_left = None
        self.bottom_right = None
        # self.padding = Point(0, 0)
        try:
            rl = root_component['Properties']['RelativeLocation']
            self.relative_location = Vector(rl['X'], rl['Y'], rl['Z'])
        except KeyError:
            self.relative_location = Vector(0, 0, 0)
        try:
            rr = root_component['Properties']['RelativeRotation']
            self.relative_rotation = Vector(rr['Pitch'], rr['Yaw'], rr['Roll'])
        except KeyError:
            self.relative_rotation = Vector(0, 0, 0)

    def __hash__(self):
        return self.name

    def __str__(self):
        return self.name

    def add_landscape_component(self, ls_component: LandscapeComponent):
        existing_ls_components = list(filter(lambda ls: ls[1].heightmap_tile.name == ls_component.heightmap_tile.name and ls[1].heightmap_tile.display == True, self.landscape_components.copy().items()))
        if existing_ls_components:
            for _, existing_ls_component in existing_ls_components:
                if ls_component.pos.x <= existing_ls_component.pos.x and ls_component.pos.y <= existing_ls_component.pos.y:
                    self.landscape_components[existing_ls_component.name].heightmap_tile.display = False
                    self.landscape_components[ls_component.name] = ls_component
        else:
            self.landscape_components[ls_component.name] = ls_component

    @property
    def width(self):
        return self.bottom_right.x - self.top_left.x

    @property
    def height(self):
        return self.bottom_right.y - self.top_left.y

    def _update_coord(self, landscape_component: LandscapeComponent, size: Size):
        if not landscape_component.heightmap_tile.display:  # Relying on heightmap display for now
            return
        if not self.top_left:
            self.top_left = Point(landscape_component.pos.x, landscape_component.pos.y)
        if not self.bottom_right:
            self.bottom_right = Point(landscape_component.pos.x + size.width, landscape_component.pos.y + size.height)
        if landscape_component.pos.x < self.top_left.x:
            self.top_left.x = landscape_component.pos.x
        if landscape_component.pos.y < self.top_left.y:
            self.top_left.y = landscape_component.pos.y
        if landscape_component.pos.x + size.width > self.bottom_right.x:
            self.bottom_right.x = landscape_component.pos.x + size.width
        if landscape_component.pos.y + size.height > self.bottom_right.y:
            self.bottom_right.y = landscape_component.pos.y + size.height

    def process(self):
        for raw_component in self.raw_components:
            landscape_component = LandscapeComponent.from_dict(raw_component)
            if not landscape_component:
                continue
            if landscape_component.heightmap_tile.name in self.tiles_misplaced.keys():
                landscape_component.pos = Point(self.tiles_misplaced[landscape_component.heightmap_tile.name]['x'], self.tiles_misplaced[landscape_component.heightmap_tile.name]['y'])
            self.add_landscape_component(landscape_component)
        for tile_name, tile_data in self.tiles_missing.items():
            landscape_component = LandscapeComponent(tile_name, Point(tile_data['x'], tile_data['y']), Tile(tile_name), list(), 0, 0)
            self.add_landscape_component(landscape_component)
        for _, landscape_component in self.landscape_components.items():
            raw_size = self.texture_components[landscape_component.heightmap_tile.name]['Properties']['ImportedSize']
            self._update_coord(landscape_component, Size(raw_size['X'], raw_size['Y']))

    def generate(self, package: Package, map_name: str, debug=False):
        if debug is True:
            debug_img = np.zeros((self.height + 500, self.width + 500, 3), np.uint8)
            cv2.rectangle(debug_img, (0, 0), (self.width, self.height), (255, 255, 255), 3)
        heightmap_img = np.zeros((self.height, self.width), np.uint8)
        # road_img = np.zeros((self.height, self.width), np.uint8)
        normalmap_img = np.zeros((self.height, self.width, 4), np.uint8)
        for _, ls_component in sorted(self.landscape_components.items(), key=lambda x: x[1]):
            if not ls_component.heightmap_tile.display:
                continue
            pos_y = ls_component.pos.y - self.top_left.y
            pos_x = ls_component.pos.x - self.top_left.x
            try:
                texture_2d = list(filter(lambda x: x.name.string == ls_component.heightmap_tile.name and x.OuterIndex.Name.string == self.name,
                                         package.ExportMap))[0]
                tile_img = np.array(texture_2d.exportObject.decode())
                tile_r, tile_g, tile_b, tile_a = cv2.split(tile_img)
                tile_w = np.full((tile_a.shape[0], tile_a.shape[1], 1), 255, np.uint8)
                heightmap_img[pos_y: pos_y + tile_r.shape[0], pos_x:pos_x + tile_r.shape[1]] = tile_r
                tile_normal = cv2.merge([tile_w, tile_a, tile_b, tile_w])
                normalmap_img[pos_y: pos_y + tile_r.shape[0], pos_x:pos_x + tile_r.shape[1]] = tile_normal

                # if tile.road_texture and tile.road_channel:
                #     texture_2d = list(filter(
                #         lambda x: x.name.string == tile.road_texture and x.OuterIndex.Name.string == self.name,
                #         package.ExportMap))[0]
                #     texture_road = np.array(texture_2d.exportObject.decode())
                #     tile_road = texture_road[:, :, tile.road_channel]
                #     road_img[pos_y: pos_y + tile_road.shape[0], pos_x:pos_x + tile_road.shape[1]] = tile_road
            except IndexError as e:
                print(f"‼️ {ls_component.heightmap_tile.name} not found for {self.name}")
                pass
            except ValueError as e:
                print(f"‼️ Could not paste {ls_component.name} : {e}")
            except FileNotFoundError as e:
                print(f"‼️ Not found {e} for {self.name} landscape")
                pass
            if debug is True:
                random_color = (random.randrange(150, 255), random.randrange(150, 255), random.randrange(150, 255))
                cv2.circle(debug_img, (pos_x, pos_y), 3, random_color, 5)
                cv2.rectangle(debug_img, (pos_x, pos_y), (pos_x + tile_img.shape[1], pos_y + tile_img.shape[0]),
                              random_color, 3)
                cv2.putText(debug_img, str(ls_component.heightmap_tile.number),
                            (pos_x + int(tile_img.shape[1] / 4), pos_y + int(tile_img.shape[0] / 2)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, random_color, 2)
        _, _, _, mask = cv2.split(normalmap_img)
        heightmap_img = cv2.cvtColor(heightmap_img, cv2.COLOR_GRAY2BGRA)
        heightmap_img[:, :, 3] = mask
        heightmap_img = rotate_image(heightmap_img, -self.relative_rotation.y)
        normalmap_img = rotate_image(normalmap_img, -self.relative_rotation.y)
        # road_img = rotate_image(road_img, -self.relative_rotation.y)
        if debug is True:
            cv2.imwrite(f"maps/{map_name}_{self.name}_debug.png", debug_img)
        cv2.imwrite(f"maps/{map_name}_{self.name}_heightmap.png", heightmap_img)
        cv2.imwrite(f"maps/{map_name}_{self.name}_normalmap.png", normalmap_img)
        # cv2.imwrite(f"maps/{map_name}_{self.name}_roadmap.png", road_img)
        print(f"✅\t{map_name}:{self.name}")


class World(object):
    pak_path: str
    name: str
    landscapes: Dict[str, Landscape]
    landscapes_filter: List[str]

    def __init__(self, pak_path: str, name: str, landscapes_filter: list = None):
        self.pak_path = pak_path
        self.name = name
        self.landscapes = dict()
        self.landscapes_filter = landscapes_filter

    @staticmethod
    def filter_landscape(x):
        return x['Type'] == 'Landscape'

    @staticmethod
    def filter_landscape_component(x, landscape_name):
        return x['Type'] == 'LandscapeComponent' and x['Outer'] == landscape_name

    @staticmethod
    def filter_landscape_root_component(x, landscape_name):
        return x['Type'] == 'SceneComponent' and x['Name'] == 'RootComponent0' and x['Outer'] == landscape_name

    @staticmethod
    def filter_texture_component(x, landscape_name):
        return x['Type'] == 'Texture2D' and x['Outer'] == landscape_name

    def process(self, debug=False):
        with open('tiles_missing.yml') as f:
            tiles_missing_yaml = yaml.safe_load(f)
        with open('tiles_misplaced.yml') as f:
            tiles_misplaced_yaml = yaml.safe_load(f)
        with FoxholeFileProvider(self.pak_path) as p:
            package = p.try_load_package(self.name, load_mode=EPackageLoadMode.Full)
        map_name = Path(self.name).stem
        if package is None:
            print(f"🚫 Cannot load package {self.name}")
            return
        umap_components = package.get_dict()
        # Iterate over Landscapes only
        for landscape in filter(self.filter_landscape, umap_components):
            if self.landscapes_filter and landscape['Name'] not in self.landscapes_filter:
                continue
            landscape_components = list(filter(
                functools.partial(self.filter_landscape_component, landscape_name=landscape['Name']),
                umap_components))
            texture_components = list(filter(
                functools.partial(self.filter_texture_component, landscape_name=landscape['Name']),
                umap_components
            ))
            # Fetching related "RootComponent0" to get Landscape relative position and rotation
            landscape_root_component = next(
                filter(functools.partial(self.filter_landscape_root_component, landscape_name=landscape['Name']),
                       umap_components))
            tiles_missing = tiles_missing_yaml.get(map_name, {}).get(landscape['Name'], {})
            tiles_misplaced = tiles_misplaced_yaml.get(map_name, {}).get(landscape['Name'], {})
            self.landscapes[landscape['Name']] = Landscape(landscape['Name'],
                                                           tiles_misplaced, tiles_missing,
                                                           landscape_components, texture_components,
                                                           landscape_root_component)
        for landscape_name, landscape in self.landscapes.items():
            landscape.process()
            landscape.generate(package, map_name, debug=debug)
