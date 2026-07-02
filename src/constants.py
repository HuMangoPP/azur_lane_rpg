import json
import colorsys
import pygame

TEMP_SCREEN_SIZE = pygame.Vector2(960, 540) # TODO
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
    RED = (255,10,10)

    CARGO_BOX = (184, 144, 114)
    CARGO_BOX_BACK = (112, 78, 53)
    CARGO_BOX_OUTLINE = (82, 54, 32)

    DOSSIER_PAGE = (255, 255, 255)
    DOSSIER = (203, 169, 112)
    DOSSIER_BACK = (174, 132, 70)

    BLUEPRINT_PAGE = (56, 88, 162)
    BLUEPRINT_PAGE_BACK = (24, 48, 103)
    STICKY_NOTE = (255, 232, 126)
    STICKY_NOTE_BACK = (224, 188, 71)
    STICKY_NOTE_OUTLINE = (169, 126, 41)

    SKY_BLUE = (100, 195, 255)

    CLEARED_ZONE_FILL = (32, 176, 171)
    CLEARED_ZONE_OUTLINE = (0, 222, 214)
    CLEARED_ZONE_GLOW = (148, 255, 251)

    UNCLEARED_ZONE_FILL = (40, 84, 181)
    UNCLEARED_ZONE_OUTLINE = (38, 106, 255)
    UNCLEARED_ZONE_GLOW = (107, 153, 255)

    LOCKED_ZONE_FILL = (97, 36, 59)
    LOCKED_ZONE_OUTLINE = (143, 30, 73)
    LOCKED_ZONE_GLOW = (189, 89, 127)

    OCEAN_BLUE = (21, 53, 122)
    OCEAN_SHADOW = (0, 16, 71)

    EXP_BAR_BG = (64, 64, 64)
    EXP_BAR_FILL = (255, 200, 0)

    DIALOGUE_OVERLAY = (0, 104, 214)
    DIALOGUE_BOX = (82, 166, 255)
    DIALOGUE_BUTTON = (82, 166, 255)

    START_SORTIE_BUTTON = (204, 61, 61)
    HOVER_START_SORTIE_BUTTON = (189, 32, 32)

    NEW_QUEST_BANNER = (43, 173, 0)
    COMPLETED_QUEST_BANNER = (191, 156, 0)

    CLIPBOARD_CLIP = (150, 150, 150)
    CLIPBOARD_CLIP_FRONT = (175, 175, 175)

class Equipment:
    NUM_EQUIPS = 3
    WEAPON = 0
    AUX1 = 1
    AUX2 = 2

class Stats:
    EXP_BASE = 12
    EXP_GROWTH = 2

    @classmethod
    def exp_to_level(cls, level):
        return sum(cls.exp_amount_at_level(l) for l in range(level))

    @classmethod
    def exp_amount_at_level(cls, level):
        return cls.EXP_BASE * (cls.EXP_GROWTH ** level)

    @classmethod
    def level(cls, exp):
        level = 0
        while exp >= cls.exp_amount_at_level(level):
            exp -= cls.exp_amount_at_level(level)
            level += 1
        return level

    @classmethod
    def level_progress(cls, exp):
        level = 0
        while exp >= cls.exp_amount_at_level(level):
            exp -= cls.exp_amount_at_level(level)
            level += 1
        return exp / cls.exp_amount_at_level(level)

    @classmethod
    def stat(cls, exp, base_stat, stat_per_level):
        return base_stat + stat_per_level * cls.level(exp)

from engine.load_assets import load_sprites, load_sound

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

    with open("data/decoration_store.json") as f:
        decoration_store = json.load(f)
    
    with open("data/item_descriptions.json") as f:
        item_descriptions = json.load(f)

    sprites = load_sprites()
    sfx = load_sound(master_file="sfx.json", file_ext="wav")
    bgm = load_sound(master_file="bgm.json", file_ext="ogg")

    @classmethod
    def recolor_sprite(cls, sprite_group, sprite_key, color):
        sprite = cls.sprites[sprite_group][sprite_key]
        sprite.set_colorkey((255,255,255))
        colored_sprite = pygame.Surface(sprite.get_size())
        colored_sprite.fill(color)
        colored_sprite.blit(sprite, (0,0))
        colored_sprite.set_colorkey((255,0,0))
        sprite.set_colorkey((255,0,0))
        return colored_sprite

    @classmethod
    def get_entity_sprite(cls, sprite_key):
        if sprite_key in cls.sprites["entity"]:
            return cls.sprites["entity"][sprite_key]
        else:
            return cls.sprites["entity"]["placeholder"]
        
    @classmethod
    def get_faction_shipgirls(cls):
        if len(cls.save_file["unlocked_factions"]) == 0:
            return {}
        faction_shipgirls = {}
        chosen_faction = cls.save_file["unlocked_factions"][0]
        for shipgirl, shipgirl_info in cls.shipgirl_data.items():
            if shipgirl_info["faction"] != chosen_faction:
                continue
            faction_shipgirls[shipgirl_info["hull_type"]] = shipgirl
        return faction_shipgirls

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

def create_background_wave_sprite(wave_index):
    wave = DataFiles.sprites["background"][f"wave{wave_index}"]
    higher_wave = pygame.Surface((wave.get_width(), 2*wave.get_height()))
    wave_color = wave.get_at((0, wave.get_height()-1))
    higher_wave.fill(wave_color)
    wave.set_colorkey(wave_color)
    higher_wave.blit(wave, (0,0))
    higher_wave.set_colorkey((255,0,0))
    DataFiles.sprites["background"][f"wave{wave_index}"] = higher_wave

DataFiles.sprites["background"]["num_waves"] = 7
for wave_index in range(DataFiles.sprites["background"]["num_waves"]):
    create_background_wave_sprite(wave_index)

sky_surf = pygame.Surface((1,2))
sky_surf.set_at((0, 0), (89, 150, 227))
sky_surf.set_at((0, 1), (150, 197, 255))
sky_surf_scaled = pygame.transform.smoothscale(sky_surf, (128, 256))
DataFiles.sprites["background"]["sky"] = sky_surf_scaled

def create_cloud_shadow_sprite(cloud_index):
    cloud = DataFiles.sprites["background"][f"cloud{cloud_index}"]
    cloud_shadow = pygame.Surface(cloud.get_size())
    cloud_shadow.fill((100,100,100))
    cloud.set_colorkey((255,255,255))
    cloud_shadow.blit(cloud, (0,0))
    cloud_shadow.set_colorkey((255,0,0))
    cloud.set_colorkey((255,0,0))

    cloud_shadow2 = pygame.Surface(cloud_shadow.get_size())
    cloud_shadow2.fill((0,0,0))
    cloud_shadow2.blit(cloud_shadow, (0,0))

    DataFiles.sprites["background"][f"cloud_shadow{cloud_index}"] = cloud_shadow2

DataFiles.sprites["background"]["num_clouds"] = 10
for cloud_index in range(DataFiles.sprites["background"]["num_clouds"]):
    create_cloud_shadow_sprite(cloud_index)

def create_sortie_selection_wave_sprite(wave_index, wave_color):
    wave = DataFiles.sprites["sortie_selection"][f"wave"]
    higher_wave = pygame.Surface((wave.get_width(), 2*wave.get_height()))
    higher_wave.fill(wave_color)
    wave.set_colorkey((255,255,255))
    higher_wave.blit(wave, (0,0))
    higher_wave.set_colorkey((255,0,0))
    DataFiles.sprites["sortie_selection"][f"wave{wave_index}"] = higher_wave

num_waves = 11
DataFiles.sprites["sortie_selection"]["num_waves"] = num_waves
base_hue = 0.65
for wave_index in range(DataFiles.sprites["sortie_selection"]["num_waves"]):
    t = wave_index / (num_waves- 1)
    s = 4*(t-0.5)**2
    saturation = 0.5 + s*0.5
    value = 1.0 - s*0.5

    r, g, b = colorsys.hsv_to_rgb(base_hue, saturation, value)
    wave_color = (int(r*255), int(g*255), int(b*255))
    create_sortie_selection_wave_sprite(wave_index, wave_color)

lightbulb_light = pygame.Surface((64,64))
pygame.draw.circle(lightbulb_light, (28, 19, 0), (32,32), 32)
DataFiles.sprites["user_interface"]["lightbulb_light"] = lightbulb_light

class Decorations:
    TILESIZE = 64
    NUM_TILES_IN_ROW = 2 * int(TEMP_SCREEN_SIZE[0] // TILESIZE)
    NUM_TILES_IN_COL = 2 * int(TEMP_SCREEN_SIZE[1] // TILESIZE)

    @classmethod
    def create_floor_surf(cls):
        cls.floor_surf = pygame.Surface((cls.NUM_TILES_IN_ROW*cls.TILESIZE, cls.NUM_TILES_IN_COL*cls.TILESIZE))
        for i in range(cls.NUM_TILES_IN_ROW):
            x = i * cls.TILESIZE
            for j in range(cls.NUM_TILES_IN_COL):
                y = j * cls.TILESIZE
                if (i + j) % 2:
                    tile = DataFiles.sprites["decorations"]["tile_dark"]
                else:
                    tile = DataFiles.sprites["decorations"]["tile_light"]
                cls.floor_surf.blit(tile, (x,y))
        
        cls.floor_rect = cls.floor_surf.get_rect()
        cls.floor_rect.center = (screen_x(0.5), screen_y(0.5))

Decorations.create_floor_surf()
