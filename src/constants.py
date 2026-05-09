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

    CARGO_BOX = (184, 144, 114)
    CARGO_BOX_BACK = (112, 78, 53)

    DOSSIER_PAGE = (255, 255, 255)
    DOSSIER = (231, 201, 169)
    DOSSIER_BACK = (220, 177, 130)

    BLUEPRINT_PAGE = (74, 109, 229)
    BLUEPRINT_PAGE_BACK = (0, 32, 130)

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
    OCEAN_SHADOW = (19, 33, 64)

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

def create_wave_sprite(sprite_group, wave_index):
    wave = DataFiles.sprites[sprite_group][f"wave{wave_index}"]
    higher_wave = pygame.Surface((wave.get_width(), 2*wave.get_height()))
    wave_color = wave.get_at((0, wave.get_height()-1))
    higher_wave.fill(wave_color)
    wave.set_colorkey(wave_color)
    higher_wave.blit(wave, (0,0))
    higher_wave.set_colorkey((255,0,0))
    DataFiles.sprites[sprite_group][f"wave{wave_index}"] = higher_wave

DataFiles.sprites["background"]["num_waves"] = 7
for wave_index in range(DataFiles.sprites["background"]["num_waves"]):
    create_wave_sprite("background", wave_index)

sky_surf = pygame.Surface((1,2))
sky_surf.set_at((0, 0), (89, 150, 227))
sky_surf.set_at((0, 1), (150, 197, 255))
sky_surf_scaled = pygame.transform.smoothscale(sky_surf, (128, 256))
DataFiles.sprites["background"]["sky"] = sky_surf_scaled

def create_cloud_shadow_sprite(sprite_group, cloud_index):
    cloud = DataFiles.sprites[sprite_group][f"cloud{cloud_index}"]
    cloud_shadow = pygame.Surface(cloud.get_size())
    cloud_shadow.fill((100,100,100))
    cloud.set_colorkey((255,255,255))
    cloud_shadow.blit(cloud, (0,0))
    cloud_shadow.set_colorkey((255,0,0))
    cloud.set_colorkey((255,0,0))

    cloud_shadow2 = pygame.Surface(cloud_shadow.get_size())
    cloud_shadow2.fill((0,0,0))
    cloud_shadow2.blit(cloud_shadow, (0,0))

    DataFiles.sprites[sprite_group][f"cloud_shadow{cloud_index}"] = cloud_shadow2

DataFiles.sprites["background"]["num_clouds"] = 10
for cloud_index in range(DataFiles.sprites["background"]["num_clouds"]):
    create_cloud_shadow_sprite("background", cloud_index)

blueprint_surf = pygame.Surface((3,3))
blueprint_surf.fill((0, 65, 186))
blueprint_surf.set_at((1,1), (128, 159, 255))

blueprint_page_size = (
    4*(Box.WIDTH + Box.PADDING) + Box.PADDING,
    5*(Box.HEIGHT + Box.PADDING) + Box.PADDING,
)
blueprint_surf_scaled = pygame.transform.smoothscale(blueprint_surf, blueprint_page_size)
DataFiles.sprites["user_interface"]["port_menu_blueprint"] = blueprint_surf_scaled

blueprint_page_size = (
    3*(Box.WIDTH + Box.PADDING)+Box.PADDING,
    4*(Box.HEIGHT+Box.PADDING)+Box.PADDING
)
blueprint_surf_scaled = pygame.transform.smoothscale(blueprint_surf, blueprint_page_size)
blueprint_rect = blueprint_surf_scaled.get_rect()
warship_polygon = [
    (blueprint_rect.centerx + 0.7*Box.WIDTH, blueprint_rect.centery + Box.PADDING),
    (blueprint_rect.centerx + 0.7*Box.WIDTH, blueprint_rect.centery - 0.8*Box.HEIGHT),
    (blueprint_rect.centerx + 0.5*Box.WIDTH, blueprint_rect.centery - 1.4*Box.HEIGHT),
    (blueprint_rect.centerx + 0.2*Box.WIDTH, blueprint_rect.centery - 1.8*Box.HEIGHT),
    (blueprint_rect.centerx, blueprint_rect.centery - 2.0*Box.HEIGHT),
    (blueprint_rect.centerx - 0.2*Box.WIDTH, blueprint_rect.centery - 1.8*Box.HEIGHT),
    (blueprint_rect.centerx - 0.5*Box.WIDTH, blueprint_rect.centery - 1.4*Box.HEIGHT),
    (blueprint_rect.centerx - 0.7*Box.WIDTH, blueprint_rect.centery - 0.8*Box.HEIGHT),
    (blueprint_rect.centerx - 0.7*Box.WIDTH, blueprint_rect.centery + Box.PADDING),
]
pygame.draw.lines(blueprint_surf_scaled, Color.WHITE, False, warship_polygon, width=2)
warship_polygon = [
    (blueprint_rect.centerx + 0.7*Box.WIDTH, blueprint_rect.centery + Box.PADDING + Box.HEIGHT),
    (blueprint_rect.centerx + 0.7*Box.WIDTH, blueprint_rect.centery + 2.0*Box.HEIGHT),
    (blueprint_rect.centerx - 0.7*Box.WIDTH, blueprint_rect.centery + 2.0*Box.HEIGHT),
    (blueprint_rect.centerx - 0.7*Box.WIDTH, blueprint_rect.centery + Box.PADDING + Box.HEIGHT),
]
pygame.draw.lines(blueprint_surf_scaled, Color.WHITE, False, warship_polygon, width=2)
DataFiles.sprites["user_interface"]["equipment_menu_blueprint"] = blueprint_surf_scaled