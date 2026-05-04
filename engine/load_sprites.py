import os
import json
import pygame

def load_sprites(directory="assets", master_sprite_file="sprites.json", colorkey=(255,0,0)):
    with open(f"{directory}/{master_sprite_file}") as f:
        master_sprite_dict = json.load(f)

    sprites = {}
    for sprite_group, sprite_group_info in master_sprite_dict.items():
        group_sprites = {}
        sprite_atlas_file = f"{directory}/{sprite_group}.png"
        if not os.path.exists(sprite_atlas_file):
            sprites[sprite_group] = group_sprites
            continue
        
        sprite_atlas = pygame.image.load(sprite_atlas_file).convert()
        sprite_atlas.set_colorkey(colorkey)
        for sprite_name, crop_info in sprite_group_info.items():
            crop = pygame.Rect(crop_info["left"], crop_info["top"], crop_info["width"], crop_info["height"])
            sprite = sprite_atlas.subsurface(crop)
            group_sprites[sprite_name] = sprite
        sprites[sprite_group] = group_sprites

    return sprites