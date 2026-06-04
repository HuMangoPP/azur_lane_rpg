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
        for sprite_name, load_info in sprite_group_info.items():
            crop = pygame.Rect(load_info["left"], load_info["top"], load_info["width"], load_info["height"])
            sprite = pygame.transform.scale_by(sprite_atlas.subsurface(crop), load_info.get("scale", 1))
            group_sprites[sprite_name] = sprite
        sprites[sprite_group] = group_sprites

    return sprites

def load_sound(directory="assets", master_file="sfx.json", file_ext="wav"):
    with open(f"{directory}/{master_file}") as f:
        master_dict = json.load(f)
    sounds = {}
    for sound_key, sound_volume in master_dict.items():
        sound = pygame.mixer.Sound(f"{directory}/{sound_key}.{file_ext}")
        sound.set_volume(sound_volume)
        sounds[sound_key] = sound
    return sounds