import functools
import json
import os
import re
from dataclasses import dataclass
from typing import Dict, List

import yaml
from PIL import Image

from helpers import closed_multiple


@dataclass
class Vector:
    x: float
    y: float
    z: float


@dataclass
class Point:
    x: int
    y: int


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
            print(f"❗️ Missing property {e} for {landscape_component['Name']}")
            return None
        except AttributeError as e:
            print(f"❗️ Cannot extract name for {landscape_component['Name']}")
            return None

    @property
    def number(self) -> int:
        return int(self.name.split('_')[-1])


class Landscape(object):
    name: str
    textures_dir: str
    raw_components: List
    tiles: Dict[str, Tile]
    top_left: Point
    bottom_right: Point
    padding: Point
    relative_location: Vector
    relative_rotation: Vector

    def __init__(self, name: str, textures_dir: str, raw_components: list, root_component: dict):
        self.name = name
        self.textures_dir = textures_dir
        self.raw_components = raw_components
        self.tiles = dict()
        self.top_left = Point(0, 0)
        self.bottom_right = Point(0, 0)
        self.padding = Point(0, 0)
        rl = root_component['Properties']['RelativeLocation']
        self.relative_location = Vector(rl['X'], rl['Y'], rl['Z'])
        rr = root_component['Properties']['RelativeRotation']
        self.relative_rotation = Vector(rr['Pitch'], rr['Yaw'], rr['Roll'])

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
        self._update_coord(self.tiles[tile.name].pos)

    def fix(self, map_name, tiles_missing, tiles_misplaced):
        try:
            self._fix_missing(tiles_missing[map_name][self.name])
        except KeyError:
            pass
        try:
            self._fix_misplaced(tiles_misplaced[map_name][self.name])
        except KeyError:
            pass

    def _fix_missing(self, missing_tiles):
        for tile_data in missing_tiles:
            tile = Tile(tile_data['name'], Point(tile_data['x'], tile_data['y']))
            self.add_tile(tile)

    def _fix_misplaced(self, misplaced_tiles):
        for tile_data in misplaced_tiles:
            self.tiles[tile_data['name']].pos.x += tile_data['x'] if 'x' in tile_data else 0
            self.tiles[tile_data['name']].pos.y += tile_data['y'] if 'y' in tile_data else 0

    @property
    def width(self):
        return self.bottom_right.x - self.top_left.x + 64

    @property
    def height(self):
        return self.bottom_right.y - self.top_left.y + 64

    def _update_coord(self, pos):
        if pos.x < self.top_left.x:
            self.top_left.x = pos.x
        if pos.y < self.top_left.y:
            self.top_left.y = pos.y
        if pos.x > self.bottom_right.x:
            self.bottom_right.x = pos.x
        if pos.y > self.bottom_right.y:
            self.bottom_right.y = pos.y
        if self.top_left.x < 0:
            self.padding.x = -self.top_left.x
        if self.top_left.y < 0:
            self.padding.y = -self.top_left.y

    def process(self):
        for raw_component in self.raw_components:
            tile = Tile.from_landscape_component(raw_component)
            if not tile:
                continue
            self.add_tile(tile)

    def generate(self, map_name: str):
        heightmap_img = Image.new("I", (self.width, self.height), 0)
        normalmap_img = Image.new("RGB", (self.width, self.height), 0)
        for tile_name, tile in sorted(self.tiles.items(), key=lambda x: x[1]):
            try:
                tile_path = os.path.join(self.textures_dir, '.'.join([tile.name, 'png']))
                tile_img = Image.open(tile_path)
                tile_r, tile_g, tile_b, tile_a = tile_img.split()
                tile_w = Image.new("L", (tile_a.size[0], tile_a.size[1]), 255)
                tile_img.close()

                heightmap_img.paste(tile_r, (tile.pos.x + self.padding.x, tile.pos.y + self.padding.y))
                normalmap_img.paste(
                    Image.merge("RGB", (tile_b, tile_a, tile_w)),
                    (tile.pos.x + self.padding.x, tile.pos.y + self.padding.y),
                )
            except ValueError:
                pass
            except FileNotFoundError as e:
                print(f"‼️ Not found {e} for {self.name} landscape")
                pass
        heightmap_img = heightmap_img.convert("RGBA")
        heightmap_img.save(f"maps/{map_name}_{self.name}_heightmap.png", "PNG")
        normalmap_img.save(f"maps/{map_name}_{self.name}_normalmap.png", "PNG")
        print(f"✅ {map_name}:{self.name}")


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

    def process(self):
        with open('tiles_missing.yml') as f:
            tiles_missing = yaml.safe_load(f)
        with open('tiles_misplaced.yml') as f:
            tiles_misplaced = yaml.safe_load(f)
        with open(self.json_file, 'r') as f:
            umap_components = json.load(f)
            for landscape in filter(self.filter_landscape, umap_components):
                if self.landscapes_filter and landscape['Name'] not in self.landscapes_filter:
                    continue
                landscape_textures_dir = os.path.join(self.textures_dir, landscape['Name'])
                landscape_components = filter(
                    functools.partial(self.filter_landscape_component, landscape_name=landscape['Name']),
                    umap_components)
                # Fetching related "RootComponent0" to get Landscape relative position and rotation
                landscape_root_component = next(filter(functools.partial(self.filter_landscape_root_component, landscape_name=landscape['Name']), umap_components))
                self.landscapes[landscape['Name']] = Landscape(landscape['Name'], landscape_textures_dir,
                                                               landscape_components, landscape_root_component)
        for landscape_name, landscape in self.landscapes.items():
            landscape.process()
            landscape.fix(self.name, tiles_missing, tiles_misplaced)
            landscape.generate(self.name)
