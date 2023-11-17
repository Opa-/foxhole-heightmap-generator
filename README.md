# Foxhole Heightmap Generator

Generates heightmap and normal maps for Foxhole video game.

# Usage

```
usage: Foxhole Heightmap Generator [-h] [-m MAPS] [-o OUTERS] [-p] [--debug]
                                   [-v]
                                   pak_dir

Generates Foxhole's heightmaps and normal maps

positional arguments:
  pak_dir               Path to the directory containing .pak file(s)

optional arguments:
  -h, --help            show this help message and exit
  -m MAPS, --maps MAPS  Comma-separated list of maps (will take all from
                        --directory arguments if empty)
  -o OUTERS, --outers OUTERS
                        Comma-separated list of landscapes (will process all
                        of them if empty)
  -p, --parallel        Render maps in parallel
  --debug
  -v, --verbose
```

## Examples

```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Only render Landscape9 sub-region of TempestIslandHex map
python main.py "C:\Program Files (x86)\Steam\steamapps\common\Foxhole\War\Content\Paks" -m TempestIslandHex -o Landscape9

# Render all maps and all sub-regions in parallel
python main.py "C:\Program Files (x86)\Steam\steamapps\common\Foxhole\War\Content\Paks" -p
```

# TODO

- [x] Take `RelativeRotation` of landscape into account
- [ ] Merge landscapes into one file
- [ ] Position/scale landscapes based on map images
- [x] Do not rely on exports from [UmodelExport](https://www.gildor.org/en/projects/umodel), [FModel](https://fmodel.app/) or [foxhole-umap-textures-extractor](https://github.com/Opa-/foxhole-umap-textures-extractor)
