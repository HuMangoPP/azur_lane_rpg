import json
import pygame

def load_sprites(master_sprite_file="assets/sprites.json", sprite_atlas_file="assets/sprites.png", colorkey=(255,0,0)):
    with open(master_sprite_file) as f:
        master_sprite_dict = json.load(f)
    sprite_atlas = pygame.image.load(sprite_atlas_file).convert()
    sprite_atlas.set_colorkey(colorkey)
    sprites = {}
    for sprite_name, crop_info in master_sprite_dict.items():
        crop = pygame.Rect(crop_info["left"], crop_info["top"], crop_info["width"], crop_info["height"])
        sprite = sprite_atlas.subsurface(crop)
        sprites[sprite_name] = sprite

    return sprites