import json
import colorsys
import math
import pygame

from engine.util import get_vec

TEMP_SCREEN_SIZE = pygame.Vector2(960, 540)
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

    @staticmethod
    def get_rotated_rect_polygon(rect, rotated_angle, offset=(0, 0)):
        rect_center = pygame.Vector2(rect.center) + pygame.Vector2(offset)
        rect_horizontal = get_vec(rect.width/2, math.radians(rotated_angle))
        rect_vertical = get_vec(rect.height/2, math.radians(90 + rotated_angle))
        return [
            rect_center + rect_horizontal + rect_vertical,
            rect_center - rect_horizontal + rect_vertical,
            rect_center - rect_horizontal - rect_vertical,
            rect_center + rect_horizontal - rect_vertical,
        ]

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
    BLUEPRINT_PAGE_GLOW = (102, 148, 255)
    BLUEPRINT_SLOT_BORDER_GLOW = (51, 55, 64)
    STICKY_NOTE = (255, 232, 126)
    STICKY_NOTE_BACK = (224, 188, 71)
    STICKY_NOTE_OUTLINE = (169, 126, 41)
    STICKY_NOTE_HANDWRITING = (242, 78, 75)

    CLEARED_ZONE_FILL = (32, 176, 171)
    CLEARED_ZONE_FILL_HOVER = (24, 222, 215)
    CLEARED_ZONE_OUTLINE = (0, 222, 214)

    UNCLEARED_ZONE_FILL = (40, 84, 181)
    UNCLEARED_ZONE_FILL_HOVER = (41, 99, 227)
    UNCLEARED_ZONE_OUTLINE = (38, 106, 255)

    LOCKED_ZONE_FILL = (125, 30, 66)
    LOCKED_ZONE_FILL_HOVER = (184, 39, 94)
    LOCKED_ZONE_OUTLINE = (143, 30, 73)

    OCEAN_BLUE = (21, 53, 122)
    OCEAN_SHADOW = (0, 16, 71)

    EXP_BAR_BG = (64, 64, 64)
    EXP_BAR_FILL = (255, 200, 0)

    DIALOGUE_OVERLAY = (0, 104, 214)
    DIALOGUE_BOX = (82, 166, 255)
    DIALOGUE_BUTTON = (82, 166, 255)

    START_SORTIE_BUTTON = (204, 51, 51)
    HOVER_START_SORTIE_BUTTON = (240, 60, 60)

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
    
    with open("data/sortie_selection_details.json") as f:
        sortie_selection_details = json.load(f)

    sprites = load_sprites()
    sprites["encounter"]["smoke"].set_alpha(128)
    sprites["encounter"]["hull"].set_colorkey((255,255,255))
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

def create_background_wave_sprite(wave_color):
    wave = DataFiles.sprites["background"]["wave"]
    higher_wave = pygame.Surface((wave.get_width(), 2*wave.get_height()))
    higher_wave.fill(wave_color)
    wave.set_colorkey((255,255,255))
    higher_wave.blit(wave, (0,0))
    higher_wave.set_colorkey((255,0,0))
    return higher_wave

DataFiles.sprites["background"]["num_waves"] = 7
background_wave_palettes = {
    "daytime": {
        "darkest": (60, 85, 200),
        "lightest": (114, 136, 241),
    },
    "nighttime": {
        "darkest": (13, 18, 64),
        "lightest": (56, 50, 128),
    },
    "stormy": {
        "darkest": (43, 72, 91),
        "lightest": (94, 143, 153),
    },
}
DataFiles.sprites["background"]["wave_sets"] = {}
for weather, palette in background_wave_palettes.items():
    DataFiles.sprites["background"]["wave_sets"][weather] = []
    for wave_index in range(DataFiles.sprites["background"]["num_waves"]):
        center_index = (DataFiles.sprites["background"]["num_waves"] - 1) / 2
        t = 1 - abs(wave_index - center_index) / center_index
        wave_color = tuple(
            int(dark + (light - dark) * t)
            for dark, light in zip(palette["darkest"], palette["lightest"])
        )
        wave = create_background_wave_sprite(wave_color)
        DataFiles.sprites["background"]["wave_sets"][weather].append(wave)

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

def create_cloud_sprite(cloud_index, color):
    cloud = DataFiles.sprites["background"][f"cloud{cloud_index}"]
    colored_cloud = pygame.Surface(cloud.get_size())
    colored_cloud.fill(color)
    cloud.set_colorkey((255,255,255))
    colored_cloud.blit(cloud, (0,0))
    colored_cloud.set_colorkey((255,0,0))
    cloud.set_colorkey((255,0,0))
    return colored_cloud

DataFiles.sprites["background"]["num_clouds"] = 10
for cloud_index in range(DataFiles.sprites["background"]["num_clouds"]):
    create_cloud_shadow_sprite(cloud_index)

background_cloud_colors = {
    "daytime": (255, 255, 255),
    "nighttime": (132, 124, 162),
    "stormy": (214, 218, 224),
}
DataFiles.sprites["background"]["cloud_sets"] = {}
for weather, cloud_color in background_cloud_colors.items():
    DataFiles.sprites["background"]["cloud_sets"][weather] = [
        create_cloud_sprite(cloud_index, cloud_color)
        for cloud_index in range(DataFiles.sprites["background"]["num_clouds"])
    ]

def create_sortie_selection_wave_sprite(wave_index, wave_color):
    wave = DataFiles.sprites["sortie_selection"][f"wave"]
    higher_wave = pygame.Surface((wave.get_width(), 2*wave.get_height()))
    higher_wave.fill(wave_color)
    wave.set_colorkey((255,255,255))
    higher_wave.blit(wave, (0,0))
    higher_wave.set_colorkey((255,0,0))
    DataFiles.sprites["sortie_selection"][f"wave{wave_index}"] = higher_wave

num_waves = 9
DataFiles.sprites["sortie_selection"]["num_wave_sprites"] = num_waves
base_hue = 0.65
for wave_index in range(num_waves):
    t = wave_index / (num_waves- 1)
    saturation = 0.5 + t*0.1
    value = 1.0 - t*0.1

    r, g, b = colorsys.hsv_to_rgb(base_hue, saturation, value)
    wave_color = (int(r*255), int(g*255), int(b*255))
    create_sortie_selection_wave_sprite(wave_index, wave_color)

lightbulb_light = pygame.Surface((64,64))
pygame.draw.circle(lightbulb_light, (28, 19, 0), (32,32), 32)
DataFiles.sprites["props"]["lightbulb_light"] = lightbulb_light

blueprint_slot_glow = pygame.Surface((1, 2))
blueprint_slot_glow.set_at((0, 1), [c2 - c1 for c1, c2 in zip(
    Color.BLUEPRINT_PAGE, Color.BLUEPRINT_PAGE_GLOW
)])
blueprint_slot_glow = pygame.transform.smoothscale(blueprint_slot_glow, (Box.WIDTH, Box.HEIGHT))
DataFiles.sprites["user_interface"]["blueprint_slot_glow"] = blueprint_slot_glow

def create_sortie_node_selection_glow(sprite_key, color):
    glow_color = tuple(c // 2 for c in color)
    glow = pygame.Surface((1, 2))
    glow.set_at((0, 1), glow_color)
    glow = pygame.transform.smoothscale(glow, (math.ceil(Box.WIDTH * 3**(1/2)/2), Box.HEIGHT))
    DataFiles.sprites["sortie_selection"][sprite_key] = glow

create_sortie_node_selection_glow("cleared_node_selection_glow", Color.CLEARED_ZONE_OUTLINE)
create_sortie_node_selection_glow("uncleared_node_selection_glow", Color.UNCLEARED_ZONE_OUTLINE)
create_sortie_node_selection_glow("locked_node_selection_glow", Color.LOCKED_ZONE_OUTLINE)

fleet_marker_selection_glow_top_width = math.ceil(2 * Box.WIDTH)
fleet_marker_selection_glow_bottom_width = math.ceil(0.75 * Box.WIDTH)
fleet_marker_selection_glow_size = (fleet_marker_selection_glow_top_width, math.ceil(1.5 * Box.HEIGHT))
fleet_marker_selection_glow = pygame.Surface(fleet_marker_selection_glow_size)
fleet_marker_selection_glow_color = Color.BLUEPRINT_SLOT_BORDER_GLOW
fleet_marker_selection_glow_top_fade = math.ceil(fleet_marker_selection_glow_size[1] * 1.0)
for y in range(fleet_marker_selection_glow_size[1]):
    y_ratio = y / (fleet_marker_selection_glow_size[1] - 1)
    cone_width = round(
        fleet_marker_selection_glow_top_width
        - (fleet_marker_selection_glow_top_width - fleet_marker_selection_glow_bottom_width) * y_ratio
    )
    top_blend = min(1, y / fleet_marker_selection_glow_top_fade)
    glow_color = tuple(math.ceil(c * top_blend) for c in fleet_marker_selection_glow_color)
    left = (fleet_marker_selection_glow_size[0] - cone_width) // 2
    pygame.draw.line(
        fleet_marker_selection_glow,
        glow_color,
        (left, y),
        (left + cone_width - 1, y)
    )
DataFiles.sprites["fleet_selection"]["marker_selection_glow"] = fleet_marker_selection_glow

battlestation_glow_top_width = math.ceil(48 + 64 + 3*Box.PADDING)
battlestation_glow_bottom_width = 2
battlestation_glow_size = (battlestation_glow_top_width, math.ceil(Box.HEIGHT/1.5))
battlestation_glow = pygame.Surface(battlestation_glow_size)
battlestation_glow_color = Color.BLUEPRINT_SLOT_BORDER_GLOW
for y in range(battlestation_glow_size[1]):
    y_ratio = y / (battlestation_glow_size[1] - 1)
    cone_width = round(
        battlestation_glow_top_width
        - (battlestation_glow_top_width - battlestation_glow_bottom_width) * y_ratio
    )
    top_blend = min(1, (0.5 + y_ratio)/1.5)
    glow_color = tuple(math.ceil(c * top_blend) for c in battlestation_glow_color)
    left = (battlestation_glow_size[0] - cone_width) // 2
    pygame.draw.line(
        battlestation_glow,
        glow_color,
        (left, y),
        (left + cone_width - 1, y)
    )
DataFiles.sprites["encounter"]["shipgirl_battlestation_glow"] = battlestation_glow

battlestation_glow_top_width = math.ceil(64 + 2*Box.PADDING)
battlestation_glow_bottom_width = 2
battlestation_glow_size = (battlestation_glow_top_width, math.ceil(Box.HEIGHT/1.5))
battlestation_glow = pygame.Surface(battlestation_glow_size)
battlestation_glow_color = Color.BLUEPRINT_SLOT_BORDER_GLOW
for y in range(battlestation_glow_size[1]):
    y_ratio = y / (battlestation_glow_size[1] - 1)
    cone_width = round(
        battlestation_glow_top_width
        - (battlestation_glow_top_width - battlestation_glow_bottom_width) * y_ratio
    )
    top_blend = min(1, (0.5 + y_ratio)/1.5)
    glow_color = tuple(math.ceil(c * top_blend) for c in battlestation_glow_color)
    left = (battlestation_glow_size[0] - cone_width) // 2
    pygame.draw.line(
        battlestation_glow,
        glow_color,
        (left, y),
        (left + cone_width - 1, y)
    )
DataFiles.sprites["encounter"]["siren_battlestation_glow"] = battlestation_glow

lightbulb_light = pygame.Surface((64, 64))
pygame.draw.circle(lightbulb_light, (54, 39, 10), (32, 32), 32)
DataFiles.sprites["equipment_menu"]["lightbulb_light"] = lightbulb_light

class Decorations:
    FLOOR_TILES_WIDE = 14
    FLOOR_TILES_TALL = 14
    ISO_TILE_WIDTH = 64
    ISO_TILE_HEIGHT = 32
    ISO_HALF_TILE_WIDTH = ISO_TILE_WIDTH // 2
    ISO_HALF_TILE_HEIGHT = ISO_TILE_HEIGHT // 2
    WALLPAPER_HEIGHT = 128

    @staticmethod
    def unpack_decoration_data(decoration_data):
        decoration, tilepos_anchor, flipped = decoration_data
        if not isinstance(flipped, bool):
            flipped = False
        return decoration, tilepos_anchor, flipped

    @staticmethod
    def get_decoration_base_dimensions(decoration, flipped):
        decoration_info = DataFiles.decoration_store[decoration]
        width = decoration_info["width"]
        height = decoration_info["height"]
        if flipped:
            return height, width
        return width, height

    @classmethod
    def get_decoration_tiles(cls, decoration, flipped, tilepos_anchor):
        base_width, base_height = cls.get_decoration_base_dimensions(decoration, flipped)
        decoration_tiles = set()
        for x in range(base_width):
            for y in range(base_height):
                tilepos = (
                    tilepos_anchor[0] - base_width + x,
                    tilepos_anchor[1] - base_height + y
                )
                decoration_tiles.add(tilepos)
        return decoration_tiles

    @classmethod
    def get_decoration_top_tilepos(cls, decoration, flipped, tilepos_anchor):
        base_width, base_height = cls.get_decoration_base_dimensions(decoration, flipped)
        return (
            tilepos_anchor[0] - base_width,
            tilepos_anchor[1] - base_height
        )

    @staticmethod
    def is_shipgirl_renderable(renderable):
        return (
            hasattr(renderable, "rect")
            and hasattr(renderable, "SPRITE_SIZE")
            and hasattr(renderable, "interacting_decoration")
        )

    @classmethod
    def get_shipgirl_standing_tilepos(cls, shipgirl):
        return cls.get_isometric_tilepos((
            shipgirl.rect.centerx,
            shipgirl.rect.bottom - shipgirl.SPRITE_SIZE / 8
        ))

    @classmethod
    def get_render_order_tiles(cls, renderable):
        if cls.is_shipgirl_renderable(renderable):
            return {cls.get_shipgirl_standing_tilepos(renderable)}

        decoration, tilepos_anchor, flipped = cls.unpack_decoration_data(renderable)
        return cls.get_decoration_tiles(decoration, flipped, tilepos_anchor)

    @classmethod
    def get_render_order_top_tilepos(cls, renderable):
        if cls.is_shipgirl_renderable(renderable):
            return cls.get_shipgirl_standing_tilepos(renderable)

        decoration, tilepos_anchor, flipped = cls.unpack_decoration_data(renderable)
        return cls.get_decoration_top_tilepos(decoration, flipped, tilepos_anchor)

    @classmethod
    def get_render_order_anchor(cls, renderable):
        if cls.is_shipgirl_renderable(renderable):
            if renderable.interacting_decoration is None:
                return None
            return tuple(renderable.interacting_decoration)

        _, tilepos_anchor, _ = cls.unpack_decoration_data(renderable)
        return tuple(tilepos_anchor)

    @classmethod
    def renderable_is_behind(cls, behind_renderable, front_renderable):
        behind_tiles = cls.get_render_order_tiles(behind_renderable)
        front_tiles = cls.get_render_order_tiles(front_renderable)
        return any(
            behind_tile[0] <= front_tile[0]
            and behind_tile[1] <= front_tile[1]
            for behind_tile in behind_tiles
            for front_tile in front_tiles
        )

    @classmethod
    def compare_decoration_render_order(cls, renderable_a, renderable_b):
        a_is_shipgirl = cls.is_shipgirl_renderable(renderable_a)
        b_is_shipgirl = cls.is_shipgirl_renderable(renderable_b)
        anchor_a = cls.get_render_order_anchor(renderable_a)
        anchor_b = cls.get_render_order_anchor(renderable_b)
        if a_is_shipgirl != b_is_shipgirl and anchor_a == anchor_b:
            return 1 if a_is_shipgirl else -1

        a_behind_b = cls.renderable_is_behind(renderable_a, renderable_b)
        b_behind_a = cls.renderable_is_behind(renderable_b, renderable_a)
        if a_behind_b and not b_behind_a:
            return -1
        if b_behind_a and not a_behind_b:
            return 1

        top_tilepos_a = cls.get_render_order_top_tilepos(renderable_a)
        top_tilepos_b = cls.get_render_order_top_tilepos(renderable_b)
        fallback_a = (
            top_tilepos_a[0] + top_tilepos_a[1],
            top_tilepos_a[1],
            top_tilepos_a[0],
            1 if a_is_shipgirl else 0
        )
        fallback_b = (
            top_tilepos_b[0] + top_tilepos_b[1],
            top_tilepos_b[1],
            top_tilepos_b[0],
            1 if b_is_shipgirl else 0
        )
        return (fallback_a > fallback_b) - (fallback_a < fallback_b)

    @classmethod
    def get_isometric_tilepos(cls, screen_pos):
        rel_x = screen_pos[0] - cls.floor_rect.left - cls.floor_rect.width / 2
        rel_y = screen_pos[1] - cls.floor_rect.top
        iso_x = (rel_y / cls.ISO_HALF_TILE_HEIGHT + rel_x / cls.ISO_HALF_TILE_WIDTH) / 2
        iso_y = (rel_y / cls.ISO_HALF_TILE_HEIGHT - rel_x / cls.ISO_HALF_TILE_WIDTH) / 2
        return (math.floor(iso_x), math.floor(iso_y))

    @classmethod
    def get_isometric_tilepos_anchor(cls, screen_pos):
        tilepos = cls.get_isometric_tilepos(screen_pos)
        return (tilepos[0] + 1, tilepos[1] + 1)

    @classmethod
    def get_isometric_floor_pos(cls, tilepos):
        return pygame.Vector2(
            cls.floor_rect.left
            + cls.floor_rect.width / 2
            + (tilepos[0] - tilepos[1]) * cls.ISO_HALF_TILE_WIDTH,
            cls.floor_rect.top
            + (tilepos[0] + tilepos[1]) * cls.ISO_HALF_TILE_HEIGHT
        )

    @staticmethod
    def get_decoration_sprite(decoration, flipped):
        sprite = DataFiles.sprites["decorations"][decoration]
        if flipped:
            sprite = pygame.transform.flip(sprite, True, False)
        return sprite

    @classmethod
    def get_decoration_sprite_rect(cls, decoration, flipped, tilepos_anchor):
        base_width, _ = cls.get_decoration_base_dimensions(decoration, flipped)
        sprite = cls.get_decoration_sprite(decoration, flipped)
        sprite_rect = sprite.get_rect()
        anchor_pos = cls.get_isometric_floor_pos(tilepos_anchor)
        sprite_rect.bottomleft = (
            anchor_pos.x - base_width * cls.ISO_HALF_TILE_WIDTH,
            anchor_pos.y
        )
        return sprite_rect

    @classmethod
    def get_decoration_base_polygon(cls, decoration, flipped, tilepos_anchor):
        base_width, base_height = cls.get_decoration_base_dimensions(decoration, flipped)
        top_tilepos = cls.get_decoration_top_tilepos(decoration, flipped, tilepos_anchor)
        left_tilepos = (
            tilepos_anchor[0] - base_width,
            tilepos_anchor[1]
        )
        right_tilepos = (
            tilepos_anchor[0],
            tilepos_anchor[1] - base_height
        )
        return [
            cls.get_isometric_floor_pos(top_tilepos),
            cls.get_isometric_floor_pos(right_tilepos),
            cls.get_isometric_floor_pos(tilepos_anchor),
            cls.get_isometric_floor_pos(left_tilepos),
        ]

    @classmethod
    def in_tileable_area(cls, tiles):
        return (
            min(tile[0] for tile in tiles) >= 0
            and max(tile[0] for tile in tiles) < cls.FLOOR_TILES_WIDE
            and min(tile[1] for tile in tiles) >= 0
            and max(tile[1] for tile in tiles) < cls.FLOOR_TILES_TALL
        )

    @classmethod
    def create_wallpaper_surf(cls):
        floor_width = (cls.FLOOR_TILES_WIDE + cls.FLOOR_TILES_TALL) * cls.ISO_HALF_TILE_WIDTH
        floor_height = (cls.FLOOR_TILES_WIDE + cls.FLOOR_TILES_TALL) * cls.ISO_HALF_TILE_HEIGHT
        wall_height = cls.WALLPAPER_HEIGHT
        stripe_width = 24

        left_back_edge_length = math.hypot(
            cls.FLOOR_TILES_TALL * cls.ISO_HALF_TILE_WIDTH,
            cls.FLOOR_TILES_TALL * cls.ISO_HALF_TILE_HEIGHT
        )
        right_back_edge_length = math.hypot(
            cls.FLOOR_TILES_WIDE * cls.ISO_HALF_TILE_WIDTH,
            cls.FLOOR_TILES_WIDE * cls.ISO_HALF_TILE_HEIGHT
        )
        wallpaper_width = math.ceil(left_back_edge_length + right_back_edge_length)
        wallpaper = pygame.Surface((wallpaper_width, wall_height), pygame.SRCALPHA)

        for x in range(wallpaper_width):
            for y in range(wall_height):
                stripe_index = (x + y) // stripe_width
                color = (134, 179, 252) if stripe_index % 2 else (35, 93, 186)
                wallpaper.set_at((x, y), color)

        skewed_height = wall_height + floor_height // 2
        cls.wallpaper_surf = pygame.Surface((floor_width + 1, skewed_height + 1), pygame.SRCALPHA)

        left_point = pygame.Vector2(0, skewed_height)
        corner_point = pygame.Vector2(floor_width / 2, wall_height)
        right_point = pygame.Vector2(floor_width, skewed_height)

        for source_x in range(wallpaper_width):
            if source_x < left_back_edge_length:
                t = source_x / left_back_edge_length
                bottom_pos = left_point.lerp(corner_point, t)
            else:
                t = (source_x - left_back_edge_length) / right_back_edge_length
                bottom_pos = corner_point.lerp(right_point, t)

            dest_x = round(bottom_pos.x)
            dest_bottom_y = round(bottom_pos.y)
            for source_y in range(wall_height):
                cls.wallpaper_surf.set_at(
                    (dest_x, dest_bottom_y - wall_height + source_y),
                    wallpaper.get_at((source_x, source_y))
                )

        cls.wallpaper_rect = cls.wallpaper_surf.get_rect()
        cls.wallpaper_rect.left = cls.floor_rect.left
        cls.wallpaper_rect.top = cls.floor_rect.top - wall_height

    @classmethod
    def get_wallpaper_rect(cls):
        wallpaper_rect = cls.wallpaper_surf.get_rect()
        wallpaper_rect.left = cls.floor_rect.left
        wallpaper_rect.top = cls.floor_rect.top - cls.WALLPAPER_HEIGHT
        return wallpaper_rect

    @classmethod
    def create_floor_surf(cls):
        floor_width = (cls.FLOOR_TILES_WIDE + cls.FLOOR_TILES_TALL) * cls.ISO_HALF_TILE_WIDTH
        floor_height = (cls.FLOOR_TILES_WIDE + cls.FLOOR_TILES_TALL) * cls.ISO_HALF_TILE_HEIGHT

        cls.floor_surf = pygame.Surface((floor_width, floor_height), pygame.SRCALPHA)
        x_offset = (cls.FLOOR_TILES_TALL - 1) * cls.ISO_HALF_TILE_WIDTH
        for i in range(cls.FLOOR_TILES_WIDE):
            for j in range(cls.FLOOR_TILES_TALL):
                x = (i - j) * cls.ISO_HALF_TILE_WIDTH + x_offset
                y = (i + j) * cls.ISO_HALF_TILE_HEIGHT
                if (i + j) % 2:
                    tile = DataFiles.sprites["decorations"]["tile_dark"]
                else:
                    tile = DataFiles.sprites["decorations"]["tile_light"]
                cls.floor_surf.blit(tile, (x,y))
        
        cls.floor_rect = cls.floor_surf.get_rect()
        cls.floor_rect.center = (screen_x(0.5), screen_y(0.5))

Decorations.create_floor_surf()
Decorations.create_wallpaper_surf()
