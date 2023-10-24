import multiprocessing
import argparse
import multiprocessing
import os
from multiprocessing import Pool

from objects import World


def argparse_init():
    parser = argparse.ArgumentParser(prog='Foxhole Heightmap Generator',
                                     description='Generates Foxhole\'s heightmaps and normal maps')
    parser.add_argument('-m', '--maps', required=False,
                        help='Comma-separated list of maps (will take all from --directory arguments if empty)')
    parser.add_argument('-o', '--outers', required=False,
                        help='Comma-separated list of landscapes (will process all of them if empty)')
    parser.add_argument('-d', '--directory', required=False,
                        default='/Users/opa/Documents/data/UmodelExport/Maps/Master',
                        help='Directory containing the map export from UmodelExport')
    parser.add_argument('-j', '--json', required=False,
                        default='/Users/opa/Documents/data/FModelExport/War/Content/Maps/Master/',
                        help='Directory containing JSON export from FModel')
    parser.add_argument('-t', '--textures', required=False,
                        default='/Users/opa/Documents/Textures',
                        help='Directory containing the exported textures from foxhole-umap-textures-extractor See https://github.com/Opa-/foxhole-umap-textures-extractor')
    parser.add_argument('-p', '--parallel', action='store_true', help='Render maps in parallel')
    parser.add_argument('--debug', action='store_true')
    parser.add_argument('-v', '--verbose', action='store_true')
    return parser.parse_args()


if __name__ == "__main__":
    args = argparse_init()
    maps = args.maps.split(',') if args.maps else sorted(
        filter(lambda x: not x.startswith('.'), os.listdir(args.directory)))
    worlds = [World(map_name, args.json, args.textures, landscapes_filter=args.outers) for map_name in maps]

    if args.parallel:
        with Pool(processes=multiprocessing.cpu_count()) as pool:
            pool.map(World.process, worlds)
    else:
        for w in worlds:
            w.process()
