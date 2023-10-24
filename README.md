# Foxhole Heightmap Generator

Generates heightmap and normal maps for Foxhole video game.

# Usage

```
usage: Foxhole Heightmap Generator [-h] [-m MAPS] [-o OUTERS] [-d DIRECTORY] [-j JSON] [-t TEXTURES] [-p] [--debug] [-v]

Generates Foxhole's heightmaps and normal maps

optional arguments:
  -h, --help            show this help message and exit
  -m MAPS, --maps MAPS  Comma-separated list of maps (will take all from --directory arguments if empty)
  -o OUTERS, --outers OUTERS
                        Comma-separated list of landscapes (will process all of them if empty)
  -d DIRECTORY, --directory DIRECTORY
                        Directory containing the map export from UmodelExport
  -j JSON, --json JSON  Directory containing JSON export from FModel
  -t TEXTURES, --textures TEXTURES
                        Directory containing the exported textures from foxhole-umap-textures-extractor See https://github.com/Opa-/foxhole-umap-textures-extractor
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
python main.py -m TempestIslandHex -o Landscape9

# Render all maps and all sub-regions in parallel
python main.py -p
```

# TODO

- [ ] Take `RelativeRotation` of landscape into account
- [ ] Merge landscapes into one file
- [ ] Do not rely on exports from [UmodelExport](https://www.gildor.org/en/projects/umodel), [FModel](https://fmodel.app/) or [foxhole-umap-textures-extractor](https://github.com/Opa-/foxhole-umap-textures-extractor)
