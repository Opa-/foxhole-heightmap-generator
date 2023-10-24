
def process_map(map_name: str, json_dir, textures_dir, outer_filter=list(), debug=False):
    outers = {}
    debug_tiles_processed = []
    with open("tiles_misplaced.yml") as f:
        textures_fix_file = yaml.safe_load(f)
    with open(f"{json_dir}{map_name}.json", "r") as f:
        umap_items = json.load(f)
        for landscape_component in filter(lambda x: x['Type'] == 'LandscapeComponent', umap_items):
            if len(outer_filter) and "Outer" in landscape_component and landscape_component["Outer"] not in outer_filter:
                continue
            tile = Tile.from_landscape_component(landscape_component)
            if tile is None:
                continue
            if landscape_component['Outer'] not in outers.keys():
                outers[landscape_component['Outer']] = Landscape(landscape_component['Outer'])
            outers[landscape_component['Outer']].add_tile(tile)
        # debug_display_image = False
        # debug_overlay = None
        #             if debug is True:
        #                 key_input = None
        #                 debug_overlay = numpy.zeros((normalmap_img.size[1], normalmap_img.size[0], 4), numpy.uint8)
        for outer_name, outer in outers.items():
            if len(outer_filter) and outer.name not in outer_filter:
                continue
            outer.fix(textures_fix_file, map_name)
            heightmap_img = Image.new("I", (outer.width, outer.height), 0)
            normalmap_img = Image.new("RGB", (outer.width, outer.height), 0)
            # Sorting as a workaround to fix EndlessShoreHex :
            # Texture2D_1342, Texture2D_1362 and Texture2D_1375 needs to be overriden by other textures with higher id
            for tile_name, tile in sorted(outer.tiles.items(), key=lambda x: x[1]):
                try:
                    tile_path = f"{textures_dir}/{map_name}/{outer}/{tile.name}.png"
                    tile_img = Image.open(tile_path)
                    tile_r, tile_g, tile_b, tile_a = tile_img.split()
                    tile_w = Image.new("L", (tile_a.size[0], tile_a.size[1]), 255)
                    tile_img.close()

                    heightmap_img.paste(tile_r, (tile.pos.x + outer.padding.x, tile.pos.y + outer.padding.y))
                    normalmap_img.paste(
                        Image.merge("RGB", (tile_b, tile_a, tile_w)),
                        (tile.pos.x + outer.padding.x, tile.pos.y + outer.padding.y),
                    )
                except ValueError:
                    pass
                # if debug is True:
                #     if not debug_display_image:
                #         heightmap_opencv = numpy.array(normalmap_img)
                #         heightmap_opencv = heightmap_opencv[:, :, ::-1].copy()
                #         tile_opencv = numpy.array(tile_normalmap)
                #         tile_opencv = tile_opencv[:, :, ::-1].copy()
                #         random_color = (random.randint(150, 255), random.randint(150, 255), random.randint(150, 255))
                #         cv2.rectangle(debug_overlay, (tile_data["x"] + padding_x, tile_data["y"] + padding_y), (tile_data["x"] + tile_white.size[0] + padding_x, tile_data["y"] + tile_white.size[1] + padding_y), random_color, 3)
                #         cv2.putText(debug_overlay, os.path.basename(tile_data['heightmap_path']).split('_')[-1].split('.')[0], (tile_data["x"] + padding_x + 10, tile_data["y"] + padding_y + 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, random_color, 2)
                #         cv2.imshow('tile', tile_opencv)
                #         cv2.imshow('debug', heightmap_opencv)
                #         cv2.imshow('debug_overlay', debug_overlay)
                #     if key_input != 27:
                #         key_input = cv2.waitKey(0)
            heightmap_img = heightmap_img.convert("RGBA")
            heightmap_img.save(f"maps/{map_name}_{outer}_heightmap.png", "PNG")
            normalmap_img.save(f"maps/{map_name}_{outer}_normalmap.png", "PNG")
            print(f"✅ {map_name}:{outer_name}")
        # for outer, tiles in outers.items():
        #     rev_dict = {}
        #     print(outer)
        #     for tile, tile_data in tiles.items():
        #         rev_dict.setdefault((tile_data['x'], tile_data['y']), set()).add(tile)
        #     for key, values in sorted(rev_dict.items()):
        #         if len(values) > 1:
        #             print(key, values)

    # if debug is True:
    #     available_tiles = os.listdir(f"{export_pak_path}/{map_name}/{outer}/")
    #     unused_tiles = list(set(available_tiles) - set(debug_tiles_processed))
    #     print("\n".join(sorted(unused_tiles, key=lambda x: int(x.split('_')[-1].split('.')[0]))))
    #     print(f"Unused number of tiles : {len(unused_tiles)}")
    # if debug is True:
    #     key_input = None
    #     while key_input != 27:
    #         key_input = cv2.waitKey(0)
