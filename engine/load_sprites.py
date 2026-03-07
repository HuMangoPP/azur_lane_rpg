import json
import pygame

def load_sprites(master_sprite_file="assets/sprites.json", colorkey=(255,0,0), scale=1):
    with open(master_sprite_file) as f:
        master_sprite_dict = json.load(f)
    
    sprites = {}
    for sprite_key, sprite_file in master_sprite_dict.items():
        sprite = pygame.transform.scale_by(pygame.image.load(sprite_file).convert_alpha(), scale)
        sprite.set_colorkey(colorkey)
        sprites[sprite_key] = sprite

    return sprites