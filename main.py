import argparse
import multiprocessing
from multiprocessing import Pool
from pathlib import Path

from helpers import FoxholeFileProvider
from objects import World


def argparse_init():
    parser = argparse.ArgumentParser(prog='Foxhole Heightmap Generator',
                                     description='Generates Foxhole\'s heightmaps and normal maps')
    parser.add_argument('pak_dir', help='Path to the directory containing .pak file(s)')
    parser.add_argument('-m', '--maps', required=False,
                        help='Comma-separated list of maps (will take all from --directory arguments if empty)')
    parser.add_argument('-o', '--outers', required=False,
                        help='Comma-separated list of landscapes (will process all of them if empty)')
    parser.add_argument('-p', '--parallel', action='store_true', help='Render maps in parallel')
    parser.add_argument('--debug', action='store_true')
    parser.add_argument('-v', '--verbose', action='store_true')
    return parser.parse_args()


if __name__ == "__main__":
    args = argparse_init()

    # Open the .pak to get a list of the maps. We'll re-open the .pak for each of the map because passing the provider
    # as an argument does not work with multiprocessing
    with FoxholeFileProvider(args.pak_dir) as p:
        maps = [m[1] for m in p.files if m[1].Name.endswith('umap')]
        if args.maps:
            maps = filter(lambda x: Path(x.Name).stem in args.maps, maps)
        worlds = [World(args.pak_dir, game_file.Name, landscapes_filter=args.outers) for game_file in maps]

    if args.parallel:
        with Pool(processes=multiprocessing.cpu_count()) as pool:
            pool.map(World.process, worlds)
    else:
        for w in worlds:
            w.process(debug=args.debug)
