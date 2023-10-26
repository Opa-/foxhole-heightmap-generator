import functools
import json
import os
import random
import re
from dataclasses import dataclass
from typing import Dict, List

import yaml
import numpy as np
import cv2

from helpers import closed_multiple, rotate_image


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
    pos: Point

    def __init__(self, name: str, pos: Point):
        self.name = name
        self.pos = pos

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
    def from_landscape_component(cls, landscape_component):
        try:
            x = closed_multiple((landscape_component["Properties"]["RelativeLocation"]["X"]), 64)
            y = closed_multiple((landscape_component["Properties"]["RelativeLocation"]["Y"]), 64)
            name = re.search(r'Texture2D_\d+',
                             landscape_component["Properties"]["HeightmapTexture"]["ObjectName"]).group()
            return cls(name, Point(x, y))
        except KeyError as e:
            print(f"⚠️\tMissing property {e} for {landscape_component['Name']}")
            return None
        except AttributeError as e:
            print(f"❗\tCannot extract name for {landscape_component['Name']}")
            return None

    @property
    def number(self) -> int:
        return int(self.name.split('_')[-1])


class Landscape(object):
    name: str
    textures_dir: str
    raw_components: List
    texture_components: Dict
    tiles_misplaced: Dict
    tiles_missing: Dict
    tiles: Dict[str, Tile]
    top_left: Point
    bottom_right: Point
    relative_location: Vector
    relative_rotation: Vector

    def __init__(self, name: str, textures_dir: str, tiles_misplaced: dict, tiles_missing: dict, raw_components: list, texture_components: list, root_component: dict):
        self.name = name
        self.textures_dir = textures_dir
        self.raw_components = raw_components
        self.tiles_misplaced = tiles_misplaced
        self.tiles_missing = tiles_missing
        self.texture_components = {texture['Name']: texture for texture in texture_components}
        self.tiles = dict()
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

    def add_tile(self, tile):
        if tile.name in self.tiles.keys():
            if tile.pos.x <= self.tiles[tile.name].pos.x and tile.pos.y <= self.tiles[tile.name].pos.y:
                self.tiles[tile.name].pos = tile.pos
        else:
            self.tiles[tile.name] = tile

    @property
    def width(self):
        return self.bottom_right.x - self.top_left.x

    @property
    def height(self):
        return self.bottom_right.y - self.top_left.y

    def _update_coord(self, tile: Tile, size: Size):
        if not self.top_left:
            self.top_left = Point(tile.pos.x, tile.pos.y)
        if not self.bottom_right:
            self.bottom_right = Point(tile.pos.x + size.width, tile.pos.y + size.height)
        if tile.pos.x < self.top_left.x:
            self.top_left.x = tile.pos.x
        if tile.pos.y < self.top_left.y:
            self.top_left.y = tile.pos.y
        if tile.pos.x + size.width > self.bottom_right.x:
            self.bottom_right.x = tile.pos.x + size.width
        if tile.pos.y + size.height > self.bottom_right.y:
            self.bottom_right.y = tile.pos.y + size.height

    def process(self):
        for raw_component in self.raw_components:
            tile = Tile.from_landscape_component(raw_component)
            if not tile:
                continue
            if tile.name in self.tiles_misplaced.keys():
                tile.pos = Point(self.tiles_misplaced[tile.name]['x'], self.tiles_misplaced[tile.name]['y'])
            self.add_tile(tile)
        for tile_name, tile_data in self.tiles_missing.items():
            tile = Tile(tile_name, Point(tile_data['x'], tile_data['y']))
            self.add_tile(tile)
        for tile_name, tile in self.tiles.items():
            tile_raw_size = self.texture_components[tile.name]['Properties']['ImportedSize']
            tile_size = Size(tile_raw_size['X'], tile_raw_size['Y'])
            self._update_coord(self.tiles[tile.name], tile_size)

    def generate(self, map_name: str, debug=False):
        if debug is True:
            debug_img = np.zeros((self.height + 500, self.width + 500, 3), np.uint8)
            cv2.rectangle(debug_img, (0, 0), (self.width, self.height), (255, 255, 255), 3)
        heightmap_img = np.zeros((self.height, self.width), np.uint8)
        normalmap_img = np.zeros((self.height, self.width, 4), np.uint8)
        for tile_name, tile in sorted(self.tiles.items(), key=lambda x: x[1]):
            tile_path = os.path.join(self.textures_dir, '.'.join([tile.name, 'png']))
            pos_y = tile.pos.y - self.top_left.y
            pos_x = tile.pos.x - self.top_left.x
            try:
                tile_img = cv2.imread(tile_path, cv2.IMREAD_UNCHANGED)
                tile_b, tile_g, tile_r, tile_a = cv2.split(tile_img)
                tile_w = np.full((tile_a.shape[0], tile_a.shape[1], 1), 255, np.uint8)
                heightmap_img[pos_y: pos_y + tile_r.shape[0], pos_x:pos_x + tile_r.shape[1]] = tile_r
                tile_normal = cv2.merge([tile_w, tile_a, tile_b, tile_w])
                normalmap_img[pos_y: pos_y + tile_r.shape[0], pos_x:pos_x + tile_r.shape[1]] = tile_normal
            except ValueError as e:
                print(f"‼️ Could not paste {tile_path} : {e}")
            except FileNotFoundError as e:
                print(f"‼️ Not found {e} for {self.name} landscape")
                pass
            if debug is True:
                random_color = (random.randrange(150, 255), random.randrange(150, 255), random.randrange(150, 255))
                cv2.circle(debug_img, (pos_x, pos_y), 3, random_color, 5)
                cv2.rectangle(debug_img, (pos_x, pos_y), (pos_x + tile_img.shape[1], pos_y + tile_img.shape[0]), random_color, 3)
                cv2.putText(debug_img, tile_name.split('_')[-1], (pos_x + int(tile_img.shape[1]/4), pos_y + int(tile_img.shape[0]/2)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, random_color, 2)
        _, _, _, mask = cv2.split(normalmap_img)
        heightmap_img = cv2.cvtColor(heightmap_img, cv2.COLOR_GRAY2BGRA)
        heightmap_img[:, :, 3] = mask
        heightmap_img = rotate_image(heightmap_img, -self.relative_rotation.y)
        normalmap_img = rotate_image(normalmap_img, -self.relative_rotation.y)
        if debug is True:
            cv2.imwrite(f"maps/{map_name}_{self.name}_debug.png", debug_img)
        cv2.imwrite(f"maps/{map_name}_{self.name}_heightmap.png", heightmap_img)
        cv2.imwrite(f"maps/{map_name}_{self.name}_normalmap.png", normalmap_img)
        print(f"✅\t{map_name}:{self.name}")


class World(object):
    name: str
    json_file: str
    textures_dir: str
    landscapes: Dict[str, Landscape]
    landscapes_filter: List[str]

    def __init__(self, name: str, json_path: str, textures_dir: str, landscapes_filter: list = None):
        self.name = name
        self.json_file = os.path.join(json_path, '.'.join([name, 'json']))
        self.textures_dir = os.path.join(textures_dir, name)
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
        with open(self.json_file, 'r') as f:
            umap_components = json.load(f)
            for landscape in filter(self.filter_landscape, umap_components):
                if self.landscapes_filter and landscape['Name'] not in self.landscapes_filter:
                    continue
                landscape_textures_dir = os.path.join(self.textures_dir, landscape['Name'])
                landscape_components = filter(
                    functools.partial(self.filter_landscape_component, landscape_name=landscape['Name']),
                    umap_components)
                texture_components = filter(
                    functools.partial(self.filter_texture_component, landscape_name=landscape['Name']),
                    umap_components
                )
                # Fetching related "RootComponent0" to get Landscape relative position and rotation
                landscape_root_component = next(filter(functools.partial(self.filter_landscape_root_component, landscape_name=landscape['Name']), umap_components))
                tiles_missing = tiles_missing_yaml.get(self.name, {}).get(landscape['Name'], {})
                tiles_misplaced = tiles_misplaced_yaml.get(self.name, {}).get(landscape['Name'], {})
                self.landscapes[landscape['Name']] = Landscape(landscape['Name'], landscape_textures_dir,
                                                               tiles_misplaced, tiles_missing,
                                                               landscape_components, texture_components, landscape_root_component)
        for landscape_name, landscape in self.landscapes.items():
            landscape.process()
            landscape.generate(self.name, debug=debug)
