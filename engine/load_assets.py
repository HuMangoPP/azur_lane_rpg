from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from engine.types import ColorType

import os
import json
import pygame


def load_sprites(
    directory: str = "assets",
    master_sprite_file: str = "sprites.json",
    default_colorkey: ColorType = (255, 0, 0)
) -> dict[str, dict[str, pygame.Surface]]:
    with open(os.path.join(directory, master_sprite_file)) as f:
        master_sprite_dict = json.load(f)

    sprites = {}
    for sprite_group, sprite_group_info in master_sprite_dict.items():
        group_sprites = {}
        sprite_atlas_file = os.path.join(directory, f"{sprite_group}.png")
        
        sprite_atlas = pygame.image.load(sprite_atlas_file).convert()
        sprite_atlas.set_colorkey(default_colorkey)
        for sprite_name, load_info in sprite_group_info.items():
            crop = pygame.Rect(load_info["left"], load_info["top"], load_info["width"], load_info["height"])
            sprite = pygame.transform.scale_by(sprite_atlas.subsurface(crop), load_info.get("scale", 1))
            sprite = pygame.transform.rotate(sprite, load_info.get("rotation", 0))
            opacity = load_info.get("opacity", 255)
            sprite.set_alpha(opacity)
            # Combining RLE with partial per-surface alpha changes blend rounding.
            # Keep those few sprites on the pixel-identical, non-RLE path.
            colorkey_flags = pygame.RLEACCEL if opacity == 255 else 0
            sprite.set_colorkey(default_colorkey, colorkey_flags)
            group_sprites[sprite_name] = sprite
        sprites[sprite_group] = group_sprites

    return sprites


def load_sound(
    directory: str = "assets", master_file: str = "sfx.json", file_ext: str = "wav"
) -> dict[str, pygame.mixer.Sound]:
    with open(os.path.join(directory, master_file)) as f:
        master_dict = json.load(f)
    sounds = {}
    for sound_key, sound_volume in master_dict.items():
        sound = pygame.mixer.Sound(os.path.join(directory, f"{sound_key}.{file_ext}"))
        sound.set_volume(sound_volume)
        sounds[sound_key] = sound
    return sounds
