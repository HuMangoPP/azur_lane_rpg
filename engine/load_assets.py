from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from engine.types import ColorType

import json
import pygame

from engine.paths import resource_path


def load_sprites(
    directory: str = "assets",
    master_sprite_file: str = "sprites.json",
    default_colorkey: ColorType = (255, 0, 0)
) -> dict[str, dict[str, pygame.Surface]]:
    """
    Load sprites from a master file.

    Sprites are divided into sprite groups for organizational purposes.
    """
    with resource_path(directory, master_sprite_file).open() as f:
        master_sprite_dict = json.load(f)

    sprites = {}
    for sprite_group, sprite_group_info in master_sprite_dict.items():
        group_sprites = {}
        sprite_atlas_file = resource_path(directory, f"{sprite_group}.png")
        
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


def recolor_sprite(sprite: pygame.Surface, color: ColorType, colorkey: ColorType) -> pygame.Surface:
    """
    Recolor a sprite.

    Assumes that the color to be recolored from the original sprite is white.
    """
    # Loaded sprites are shared and may already be RLE-encoded. Changing the
    # colorkey on that cached surface makes later recolors depend on its RLE
    # state (and also leaves the sprite modified for every other caller).
    # Work on a non-RLE copy so recoloring is repeatable and side-effect free.
    recolor_mask = sprite.convert()
    recolor_mask.set_colorkey(None)
    recolor_mask.set_colorkey((255, 255, 255))
    colored_sprite = pygame.Surface(sprite.get_size())
    colored_sprite.fill(color)
    colored_sprite.blit(recolor_mask, (0, 0))
    colored_sprite = colored_sprite.convert()
    colored_sprite.set_colorkey(colorkey, pygame.RLEACCEL)
    return colored_sprite


def load_sound(
    directory: str = "assets", master_file: str = "sfx.json", file_ext: str = "wav"
) -> dict[str, pygame.mixer.Sound]:
    """
    Load Sound objects from a master file.
    """
    with resource_path(directory, master_file).open() as f:
        master_dict = json.load(f)
    sounds = {}
    for sound_key, sound_volume in master_dict.items():
        sound = pygame.mixer.Sound(resource_path(directory, f"{sound_key}.{file_ext}"))
        sound.set_volume(sound_volume)
        sounds[sound_key] = sound
    return sounds
