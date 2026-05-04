import json
import colorsys
import pygame

TEMP_SCREEN_SIZE = pygame.Vector2(1120, 630)
FPS = 60

def screen_x(t):
    return TEMP_SCREEN_SIZE.x * t

def screen_y(t):
    return TEMP_SCREEN_SIZE.y * t

class Box:
    WIDTH = 64
    HEIGHT = 64
    OUTLINE_WIDTH = 2

    PADDING = 8

    EDGE_PADDING = 32
    LEFT_OF_SCREEN = screen_x(0) + EDGE_PADDING
    RIGHT_OF_SCREEN = screen_x(1) - EDGE_PADDING
    TOP_OF_SCREEN = screen_y(0) + EDGE_PADDING
    BOTTOM_OF_SCREEN = screen_y(1) - EDGE_PADDING

class Color:
    WHITE = (255,255,255)
    BLACK = (10,10,10)
    GREY = (50,50,50)
    BLUE_GREY = (100,100,150)
    BLUE = (75,75,125)
    DARK_BLUE = (50,50,100)
    RED = (255,10,10)

    SKY_BLUE = (100, 195, 255)

class Equipment:
    NUM_EQUIPS = 3
    WEAPON = 0
    AUX1 = 1
    AUX2 = 2

class Stats:
    RESEARCH_EXP_REQUIREMENTS = [0, 0, 5, 8]
    EXP_BREAKPOINTS = [3, 5, 8, 13, 21]

    @classmethod
    def level(cls, exp):
        level_index = 0
        while exp >= cls.EXP_BREAKPOINTS[level_index]:
            exp -= cls.EXP_BREAKPOINTS[level_index]
            level_index += 1
        return level_index

    @classmethod
    def level_progress(cls, exp):
        level_index = 0
        while exp >= cls.EXP_BREAKPOINTS[level_index]:
            exp -= cls.EXP_BREAKPOINTS[level_index]
            level_index += 1
        return exp / cls.EXP_BREAKPOINTS[level_index]

    @classmethod
    def stat(cls, exp, base_stat, stat_per_level):
        return base_stat + stat_per_level * cls.level(exp)

from engine.load_sprites import load_sprites

class DataFiles:
    with open("data/save_file.json") as f:
        save_file = json.load(f)

    with open("data/sorties.json") as f:
        sortie_data = json.load(f)

    with open("data/shipgirls.json") as f:
        shipgirl_data = json.load(f)

    with open("data/stats.json") as f:
        stats_data = json.load(f)

    with open("data/sirens.json") as f:
        siren_data = json.load(f)

    with open("data/equipment.json") as f:
        equipment_data = json.load(f)
    
    sprites = load_sprites()

def create_shell_sprite(shell_key, color):
    alphas = [10, 20, 50, 100, 200, 250]
    lengths = [64, 62, 58, 52, 44, 34]
    heights = [18, 16, 14, 12, 10, 8]
    rights = [64, 62, 60, 58, 56, 54]
    shell_sprite = pygame.Surface((lengths[0], heights[0]), flags=pygame.SRCALPHA)
    for a, l, h, r in zip(alphas, lengths, heights, rights):
        rect = pygame.Rect(0, 0, l, h)
        rect.right = r
        rect.centery = heights[0] / 2
        pygame.draw.ellipse(shell_sprite, (*color, a), rect)
    DataFiles.sprites["encounter"][f"{shell_key}_shell"] = shell_sprite

create_shell_sprite("normal", (255, 242, 97))
create_shell_sprite("HE", (255, 0, 64))
create_shell_sprite("AP", (0, 255, 255))

def create_wave_sprite(wave_index, wave_color):
    wave = DataFiles.sprites["encounter"]["wave"]
    wave.set_colorkey((255,255,255))
    colored_wave = pygame.Surface(wave.get_size())
    colored_wave.fill(wave_color)
    colored_wave.blit(wave, (0,0))
    colored_wave.set_colorkey((255,0,0))
    wave.set_colorkey((255,0,0))

    num_reps = 10
    wave_layer = pygame.Surface((colored_wave.get_width()*num_reps, colored_wave.get_height()))
    wave_layer.fill((255,0,0))
    wave_layer.set_colorkey((255,0,0))
    for j in range(num_reps):
        wave_layer.blit(colored_wave, (j*colored_wave.get_width(), 0))

    DataFiles.sprites["encounter"][f"wave{wave_index}"] = wave_layer

num_waves = 15
base_hue = 0.55
for wave_index in range(num_waves):
    t = wave_index / (num_waves - 1)
    saturation = 0.3 + t * 0.5
    value = 0.85 - t * 0.5
    r, g, b = colorsys.hsv_to_rgb(base_hue, saturation, value)
    wave_color = (int(r*255), int(g*255), int(b*255))
    create_wave_sprite(num_waves-1-wave_index, wave_color)

DataFiles.sprites["encounter"]["num_waves"] = num_waves