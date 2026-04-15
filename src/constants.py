import json
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

EDGE_PADDING = 20
LEFT_OF_SCREEN = screen_x(0) + EDGE_PADDING
RIGHT_OF_SCREEN = screen_x(1) - EDGE_PADDING
TOP_OF_SCREEN = screen_y(0) + EDGE_PADDING
BOTTOM_OF_SCREEN = screen_y(1) - EDGE_PADDING

class Color:
    WHITE = (255,255,255)
    BLACK = (10,10,10)
    BLUE_GREY = (100,100,150)
    BLUE = (75,75,125)
    DARK_BLUE = (50,50,100)
    RED = (255,10,10)

class Equipment:
    NUM_EQUIPS = 3
    WEAPON = 0
    AUX1 = 1
    AUX2 = 2

class Stats:
    NUM_STATS = 4

    MAX_HP = 0
    EVASION = 1
    FIREPOWER = 2
    RELOAD = 3

    STAT_NAMES = {
        MAX_HP: "HP",
        EVASION: "EVA",
        FIREPOWER: "FP",
        RELOAD: "RLD",
    }

from engine.load_sprites import load_sprites

class DataFiles:
    with open("data/save_file.json") as f:
        save_file = json.load(f)

    with open("data/sorties.json") as f:
        sortie_data = json.load(f)

    with open("data/shipgirls.json") as f:
        shipgirl_data = json.load(f)

    with open("data/sirens.json") as f:
        siren_data = json.load(f)

    with open("data/equipment.json") as f:
        equipment_data = json.load(f)
    
    sprites = load_sprites()