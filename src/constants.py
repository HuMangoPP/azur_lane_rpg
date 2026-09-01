from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from engine.types import CoordinateType, ColorType
    from src.shipgirls import Shipgirl

import json
import colorsys
import math
import pygame

from engine.util import get_vec
from engine.load_assets import load_sprites, load_sound

TEMP_SCREEN_SIZE = pygame.Vector2(960, 540)
FPS = 60


def screen_x(t: float):
    return TEMP_SCREEN_SIZE.x * t


def screen_y(t: float):
    return TEMP_SCREEN_SIZE.y * t


class Box:
    WIDTH = 64
    HEIGHT = 64
    OUTLINE_WIDTH = 2

    PADDING = 8

    EDGE_MARGIN = 32
    LEFT_OF_SCREEN = screen_x(0) + EDGE_MARGIN
    RIGHT_OF_SCREEN = screen_x(1) - EDGE_MARGIN
    TOP_OF_SCREEN = screen_y(0) + EDGE_MARGIN
    BOTTOM_OF_SCREEN = screen_y(1) - EDGE_MARGIN


    # TODO Consider whether this deserves to be in the engine.
    @staticmethod
    def get_rotated_rect_polygon(rect: pygame.Rect, rotated_angle: float, offset: CoordinateType = (0, 0)):
        """Compute a rotated rect polygon."""
        rect_center = pygame.Vector2(rect.center) + pygame.Vector2(offset)
        rect_horizontal = get_vec(rect.width / 2, math.radians(rotated_angle))
        rect_vertical = get_vec(rect.height / 2, math.radians(90 + rotated_angle))
        return [
            rect_center + rect_horizontal + rect_vertical,
            rect_center - rect_horizontal + rect_vertical,
            rect_center - rect_horizontal - rect_vertical,
            rect_center + rect_horizontal - rect_vertical,
        ]


class Color:
    # TODO Look at which colors are no longer used.
    # Also, if a color is only used in one file, consider moving it either completely.
    # This should only be used for shared colors used across multiple modules.
    WHITE = (255, 255, 255)
    BLACK = (10, 10, 10)
    GREY = (50, 50, 50)
    RED = (255, 10, 10)

    CARGO_BOX = (184, 144, 114)
    CARGO_BOX_BACK = (112, 78, 53)
    CARGO_BOX_OUTLINE = (82, 54, 32)

    DOSSIER_PAGE = (255, 255, 255)
    DOSSIER = (203, 169, 112)
    DOSSIER_BACK = (174, 132, 70)
    DOSSIER_INK = (61, 56, 47)
    DOSSIER_RULE = (177, 169, 151)
    DOSSIER_CARD = (250, 248, 240)
    DOSSIER_CARD_SHADOW = (205, 199, 184)
    DOSSIER_PAPER_UNDERSIDE = (224, 220, 207)
    DOSSIER_FOLD_SHADOW = (181, 177, 166)
    DOSSIER_FOLD_SHADOW_HOVER = (151, 146, 136)
    DOSSIER_FOLD_HIGHLIGHT = (242, 239, 230)

    BLUEPRINT_PAGE = (56, 88, 162)
    BLUEPRINT_PAGE_BACK = (24, 48, 103)
    BLUEPRINT_PAGE_GLOW = (102, 148, 255)
    BLUEPRINT_SLOT_BORDER_GLOW = (204, 220, 255)
    BLUEPRINT_GRID_MINOR = (62, 95, 172)
    BLUEPRINT_GRID_MAJOR = (73, 111, 195)
    BLUEPRINT_INK_MUTED = (164, 190, 239)
    BLUEPRINT_TITLE_BLOCK = (31, 60, 125)
    STICKY_NOTE = (255, 232, 126)
    STICKY_NOTE_BACK = (224, 188, 71)
    STICKY_NOTE_OUTLINE = (169, 126, 41)
    STICKY_NOTE_HANDWRITING = (242, 78, 75)

    CLEARED_ZONE_FILL = (32, 176, 171)
    CLEARED_ZONE_OUTLINE = (0, 222, 214)

    UNCLEARED_ZONE_FILL = (40, 84, 181)
    UNCLEARED_ZONE_OUTLINE = (56, 118, 255)

    LOCKED_ZONE_FILL = (125, 30, 66)
    LOCKED_ZONE_OUTLINE = (207, 0, 79)

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

    QUEST_NOTIFICATION_PANEL = (7, 18, 42)
    QUEST_NOTIFICATION_HEADER = (9, 31, 68)
    QUEST_NOTIFICATION_TEXT = (218, 236, 255)
    QUEST_NOTIFICATION_MUTED = (135, 170, 210)
    QUEST_NOTIFICATION_NEW = (70, 225, 255)
    QUEST_NOTIFICATION_ACTIVE = (102, 148, 255)
    QUEST_NOTIFICATION_COMPLETE = (255, 199, 72)

    CLIPBOARD_CLIP = (150, 150, 150)
    CLIPBOARD_CLIP_FRONT = (175, 175, 175)

    HOLOGRAM_GLOW = (51, 55, 128)
    SIREN_HOLOGRAM_GLOW = (128, 55, 51)

    TARGET_INDICATOR = (225, 240, 255)
    MUTED_TARGET_INDICATOR = (192, 208, 224)


class Equipment:
    WEAPON = 0
    AUX1 = 1
    AUX2 = 2

    WEAPON_KEY = "weapon"
    AUX_KEY = "aux"

    HULL_TYPE_MAPPING = {
        "DD": "destroyer",
        "CL": "light cruiser",
        "CA": "heavy cruiser",
        "BB": "battleship",
        "SS": "submarine",
        "CV": "aircraft carrier",
        "aux": "universal",
    }

    AP_SHELL = "AP"
    HE_SHELL = "HE"
    NORMAL_SHELL = "normal"
    TORPEDO = "torpedo"


class Stats:
    EXP_BASE = 12
    EXP_GROWTH = 2

    @classmethod
    def exp_to_level(cls, level: float) -> float:
        """The total amount of exp required to reach this level."""
        return sum(cls.exp_amount_at_level(lvl) for lvl in range(level))

    @classmethod
    def exp_amount_at_level(cls, level: float) -> float:
        """The amount of exp to go from this level to the next."""
        return cls.EXP_BASE * (cls.EXP_GROWTH ** level)

    @classmethod
    def level(cls, exp: float) -> int:
        """The level given this amount of exp."""
        level = 0
        while exp >= cls.exp_amount_at_level(level):
            exp -= cls.exp_amount_at_level(level)
            level += 1
        return level

    @classmethod
    def level_progress(cls, exp: float) -> float:
        """The progress through the current level given the exp."""
        level = 0
        while exp >= cls.exp_amount_at_level(level):
            exp -= cls.exp_amount_at_level(level)
            level += 1
        return exp / cls.exp_amount_at_level(level)

    @classmethod
    def stat(
        cls, base_stat: float, stat_per_level: float, exp: float | None = None, level: float | None = None
    ) -> float | None:
        """The stat value given either the exp or level."""
        if exp is not None:
            return base_stat + stat_per_level * cls.level(exp)
        if level is not None:
            return base_stat + stat_per_level * level
        return None


# TODO Consider whether this serves to be split.
class DataFiles:
    with open("data/save_file.json") as f:
        save_file = json.load(f)

    with open("data/sorties.json") as f:
        sortie_data: list[dict] = json.load(f)

    with open("data/shipgirls.json") as f:
        shipgirl_data: dict[str, dict[str, str]] = json.load(f)

    with open("data/stats.json") as f:
        stats_data: dict[str, dict[str, CoordinateType]] = json.load(f)

    with open("data/sirens.json") as f:
        siren_data: dict[str, dict] = json.load(f)

    with open("data/equipment.json") as f:
        equipment_data: dict[str, dict] = json.load(f)

    with open("data/decoration_store.json") as f:
        decoration_store: dict[str, dict] = json.load(f)
    
    with open("data/item_descriptions.json") as f:
        item_descriptions: dict[str, str] = json.load(f)
    
    with open("data/sortie_selection_details.json") as f:
        sortie_selection_details: dict[str, dict] = json.load(f)

    sprites: dict[str, dict[str, pygame.Surface | dict[str, pygame.Surface]]] = load_sprites()
    sfx = load_sound(master_file="sfx.json", file_ext="wav")
    bgm = load_sound(master_file="bgm.json", file_ext="ogg")

    # TODO Consider whether this is a useful enough util to move to the engine.
    @classmethod
    def recolor_sprite(cls, sprite_group: str, sprite_key: str, color: ColorType) -> pygame.Surface:
        """Recolor the white pixels of the sprite to the target color."""
        sprite = cls.sprites[sprite_group][sprite_key]
        sprite.set_colorkey((255, 255, 255))
        colored_sprite = pygame.Surface(sprite.get_size())
        colored_sprite.fill(color)
        colored_sprite.blit(sprite, (0, 0))
        colored_sprite.set_colorkey((255, 0, 0))
        sprite.set_colorkey((255, 0, 0))
        return colored_sprite

    @classmethod
    def get_entity_sprite(cls, sprite_key: str) -> pygame.Surface:
        """Get sprites from the entity sprite group and fall back to placeholder if it does not exist."""
        if sprite_key in cls.sprites["entity"]:
            return cls.sprites["entity"][sprite_key]
        else:
            return cls.sprites["entity"]["placeholder"]
        
    @classmethod
    def get_faction_shipgirls(cls) -> dict[str, str]:
        """Get the shipgirls for the player's chosen faction.
        
        The returned object is formatted as a dictionary with the key
        being the two letter hull type designation and the value being
        the name of the shipgirl.
        """
        if len(cls.save_file["unlocked_factions"]) == 0:
            return {}
        faction_shipgirls = {}
        chosen_faction = cls.save_file["unlocked_factions"][0]
        for shipgirl, shipgirl_info in cls.shipgirl_data.items():
            if shipgirl_info["faction"] != chosen_faction:
                continue
            faction_shipgirls[shipgirl_info["hull_type"]] = shipgirl
        return faction_shipgirls


# TODO Consider whether these chould be classmethods in DataFiles that are invoked once.
# Generate recolored shell sprites for each shell type.
for shell_type, shell_color in zip(
    [Equipment.NORMAL_SHELL, Equipment.HE_SHELL, Equipment.AP_SHELL],
    [(255, 242, 97), (255, 0, 64), (0, 255, 255)]
):
    alphas = [10, 20, 50, 100, 200, 250]
    lengths = [64, 62, 58, 52, 44, 34]
    heights = [18, 16, 14, 12, 10, 8]
    rights = [64, 62, 60, 58, 56, 54]
    shell_sprite = pygame.Surface((lengths[0], heights[0]), flags=pygame.SRCALPHA)
    for a, l, h, r in zip(alphas, lengths, heights, rights):
        rect = pygame.Rect(0, 0, l, h)
        rect.right = r
        rect.centery = heights[0] / 2
        pygame.draw.ellipse(shell_sprite, (*shell_color, a), rect)
    DataFiles.sprites["encounter"][f"{shell_type}_shell"] = shell_sprite

# Generate wave sprites for each weather condition.
# Wave colors are a gradient between two shades of a color.
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
    wave_set = []
    for wave_index in range(DataFiles.sprites["background"]["num_waves"]):
        center_index = (DataFiles.sprites["background"]["num_waves"] - 1) / 2
        t = 1 - abs(wave_index - center_index) / center_index
        wave_color = tuple(
            int(dark + (light - dark) * t)
            for dark, light in zip(palette["darkest"], palette["lightest"])
        )
        # DataFiles.recolor_sprite not used here because the wave sprite also needs
        # to get taller, and so this approach is actually more efficient than generating
        # the colored sprite then having to manipulate that and make the sprite taller.
        wave = DataFiles.sprites["background"]["wave"]
        higher_wave = pygame.Surface((wave.get_width(), 2 * wave.get_height()))
        higher_wave.fill(wave_color)
        wave.set_colorkey((255, 255, 255))
        higher_wave.blit(wave, (0, 0))
        wave.set_colorkey((255, 0, 0))
        higher_wave.set_colorkey((255, 0, 0))
        wave_set.append(higher_wave)
    DataFiles.sprites["background"]["wave_sets"][weather] = wave_set

# Generate shadows for each cloud.
DataFiles.sprites["background"]["num_clouds"] = 10
for cloud_index in range(DataFiles.sprites["background"]["num_clouds"]):
    cloud_shadow = DataFiles.recolor_sprite("background", f"cloud{cloud_index}", (100, 100, 100))
    cloud_shadow_black_bg = pygame.Surface(cloud_shadow.get_size())
    cloud_shadow_black_bg.fill((0, 0, 0))
    cloud_shadow_black_bg.blit(cloud_shadow, (0, 0))

    DataFiles.sprites["background"][f"cloud_shadow{cloud_index}"] = cloud_shadow_black_bg

# Create cloud sprites corresponding to each weather condition.
background_cloud_colors = {
    "daytime": (255, 255, 255),
    "nighttime": (132, 124, 162),
    "stormy": (214, 218, 224),
}
DataFiles.sprites["background"]["cloud_sets"] = {}
for weather, cloud_color in background_cloud_colors.items():
    cloud_set = []
    for cloud_index in range(DataFiles.sprites["background"]["num_clouds"]):
        colored_cloud = DataFiles.recolor_sprite("background", f"cloud{cloud_index}", cloud_color)
        cloud_set.append(colored_cloud)
    DataFiles.sprites["background"]["cloud_sets"][weather] = cloud_set

# Generate wave sprites for the sortie selection background.
wave = DataFiles.sprites["sortie_selection"]["wave"]
wave.set_colorkey((255, 255, 255))
num_waves = 9
DataFiles.sprites["sortie_selection"]["num_wave_sprites"] = num_waves
base_hue = 0.65
for wave_index in range(num_waves):
    t = wave_index / (num_waves - 1)
    saturation = 0.5 + t * 0.1
    value = 1.0 - t * 0.1

    r, g, b = colorsys.hsv_to_rgb(base_hue, saturation, value)
    # Sprite gets taller, so DataFiles.recolor_sprite not used.
    wave_color = (int(r * 255), int(g * 255), int(b * 255))
    higher_wave = pygame.Surface((wave.get_width(), 2 * wave.get_height()))
    higher_wave.fill(wave_color)
    higher_wave.blit(wave, (0,0))
    higher_wave.set_colorkey((255, 0, 0))
    DataFiles.sprites["sortie_selection"][f"wave{wave_index}"] = higher_wave

# Generate a lightbulb light sprite for the lightbulb prop..
lightbulb_light = pygame.Surface((64, 64))
pygame.draw.circle(lightbulb_light, (28, 19, 0), (32, 32), 32)
DataFiles.sprites["props"]["lightbulb_light"] = lightbulb_light

# Generate a column glow for the blueprint slot.
blueprint_slot_glow = pygame.Surface((1, 2))
blueprint_slot_glow.set_at((0, 1), [c2 - c1 for c1, c2 in zip(
    Color.BLUEPRINT_PAGE, Color.BLUEPRINT_PAGE_GLOW
)])
blueprint_slot_glow = pygame.transform.smoothscale(blueprint_slot_glow, (Box.WIDTH, Box.HEIGHT))
DataFiles.sprites["user_interface"]["blueprint_slot_glow"] = blueprint_slot_glow

# Generate column glows for sortie node hexes.
for sprite_key, color in zip(
    ["cleared_node_selection_glow", "uncleared_node_selection_glow", "locked_node_selection_glow"],
    [Color.CLEARED_ZONE_OUTLINE, Color.UNCLEARED_ZONE_OUTLINE, Color.LOCKED_ZONE_OUTLINE]
):
    glow_color = tuple(c // 2 for c in color)
    glow = pygame.Surface((1, 2))
    glow.set_at((0, 1), glow_color)
    glow = pygame.transform.smoothscale(glow, (math.ceil(Box.WIDTH * math.sqrt(3) / 2), Box.HEIGHT))
    DataFiles.sprites["sortie_selection"][sprite_key] = glow

# Generate a conic glow for the fleet selection markers.
fleet_marker_selection_glow_top_width = math.ceil(2 * Box.WIDTH)
fleet_marker_selection_glow_bottom_width = math.ceil(0.75 * Box.WIDTH)
fleet_marker_selection_glow_size = (fleet_marker_selection_glow_top_width, math.ceil(1.5 * Box.HEIGHT))
fleet_marker_selection_glow = pygame.Surface(fleet_marker_selection_glow_size)
fleet_marker_selection_glow_color = Color.HOLOGRAM_GLOW
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

# Generate a conic glow for the shipgirl and siren battlestations.
reload_gauge_width = 48
bar_width = 64
battlestation_glow_top_width = math.ceil(reload_gauge_width + bar_width + 4 * Box.PADDING)
battlestation_glow_bottom_width = 2
battlestation_glow_size = (battlestation_glow_top_width, math.ceil(Box.HEIGHT / 1.5))
battlestation_glow_colors = [Color.HOLOGRAM_GLOW, Color.SIREN_HOLOGRAM_GLOW]
battlestation_glow_keys = ["shipgirl_battlestation_glow", "siren_battlestation_glow"]
for battlestation_glow_key, battlestation_glow_color in zip(
    battlestation_glow_keys, battlestation_glow_colors
):
    battlestation_glow = pygame.Surface(battlestation_glow_size)
    for y in range(battlestation_glow_size[1]):
        y_ratio = y / (battlestation_glow_size[1] - 1)
        cone_width = round(
            battlestation_glow_top_width
            - (battlestation_glow_top_width - battlestation_glow_bottom_width) * y_ratio
        )
        min_glow = 0.33
        top_blend = min(1, min_glow + (1 - min_glow) * y_ratio)
        glow_color = tuple(math.ceil(c * top_blend) for c in battlestation_glow_color)
        left = (battlestation_glow_size[0] - cone_width) // 2
        pygame.draw.line(
            battlestation_glow,
            glow_color,
            (left, y),
            (left + cone_width - 1, y)
        )
    DataFiles.sprites["encounter"][battlestation_glow_key] = battlestation_glow

# Generate a lightbulb glow for the equipment menu lightbulb prop.
lightbulb_light = pygame.Surface((64, 64))
pygame.draw.circle(lightbulb_light, (54, 39, 10), (32, 32), 32)
DataFiles.sprites["equipment_menu"]["lightbulb_light"] = lightbulb_light


# TODO Consider whether the isometric utilities for this class are useful as engine-level
# utilities.
class Decorations:
    FLOOR_TILES_WIDE = 14
    FLOOR_TILES_TALL = 14
    ISO_TILE_WIDTH = 64
    ISO_TILE_HEIGHT = 32
    ISO_HALF_TILE_WIDTH = ISO_TILE_WIDTH // 2
    ISO_HALF_TILE_HEIGHT = ISO_TILE_HEIGHT // 2
    WALLPAPER_HEIGHT = 128

    @staticmethod
    def unpack_decoration_data(decoration_data: tuple[str, CoordinateType, bool]) -> tuple[str, CoordinateType, bool]:
        """Unpack decoration data safely."""
        decoration, tilepos_anchor, flipped = decoration_data
        if not isinstance(flipped, bool):
            flipped = False
        return decoration, tilepos_anchor, flipped

    @staticmethod
    def get_decoration_base_dimensions(decoration: str, flipped: bool) -> CoordinateType:
        """Get the footprint size of a decoration."""
        decoration_info = DataFiles.decoration_store[decoration]
        width = decoration_info["width"]
        height = decoration_info["height"]
        if flipped:
            return height, width
        return width, height

    @classmethod
    def get_decoration_tiles(
        cls, decoration: str, flipped: bool, tilepos_anchor: CoordinateType
    ) -> set[CoordinateType]:
        """Compute the occupied tiles of a decoration placed at this location."""
        base_width, base_height = cls.get_decoration_base_dimensions(decoration, flipped)
        decoration_tiles = set()
        for x in range(base_width):
            for y in range(base_height):
                tilepos = (
                    tilepos_anchor[0] + 1 - base_width + x,
                    tilepos_anchor[1] + 1 - base_height + y
                )
                decoration_tiles.add(tilepos)
        return decoration_tiles

    @staticmethod
    def is_shipgirl_renderable(renderable: Shipgirl | tuple[str, CoordinateType, bool]) -> bool:
        """Checks if this renderable is a shipgirl."""
        return (
            hasattr(renderable, "rect")
            and hasattr(renderable, "interacting_decoration")
        )

    @classmethod
    def get_shipgirl_standing_tilepos(cls, shipgirl: Shipgirl) -> CoordinateType:
        """Get the tilepos the shipgirl is standing on."""
        return cls.get_isometric_tilepos((
            shipgirl.rect.centerx,
            shipgirl.rect.bottom - shipgirl.SPRITE_SIZE / 8
        ))

    @classmethod
    def get_render_order_tiles(
        cls, renderable: Shipgirl | tuple[str, CoordinateType, bool]
    ) -> set[CoordinateType]:
        """Get the tiles occupied by this renderable."""
        if cls.is_shipgirl_renderable(renderable):
            return {cls.get_shipgirl_standing_tilepos(renderable)}

        decoration, tilepos_anchor, flipped = cls.unpack_decoration_data(renderable)
        return cls.get_decoration_tiles(decoration, flipped, tilepos_anchor)

    @classmethod
    def renderable_is_behind(
        cls,
        behind_renderable: Shipgirl | tuple[str, CoordinateType, bool],
        front_renderable: Shipgirl | tuple[str, CoordinateType, bool]
    ) -> bool:
        """Determines whether the behind renderable is behind the front renderable.
        
        A renderable is behind another renderable if the former's occupied tiles
        overlaps a tile that is behind the latter.
        A tile is behind another tile if the formers coordinates are both smaller
        then the latter's.
        A tile is behind a renderable if the tile if behind any of the tiles the
        renderable occupies.
        """
        behind_tiles = cls.get_render_order_tiles(behind_renderable)
        front_tiles = cls.get_render_order_tiles(front_renderable)
        return any(
            behind_tile[0] <= front_tile[0]
            and behind_tile[1] <= front_tile[1]
            for behind_tile in behind_tiles
            for front_tile in front_tiles
        )

    @classmethod
    def compare_decoration_render_order(
        cls,
        renderable_a: Shipgirl | tuple[str, CoordinateType, bool],
        renderable_b: Shipgirl | tuple[str, CoordinateType, bool],
    ) -> int:
        """Compare two renderables.
        
        If A is behind B but B is not behind A, then return a negative number.
        If B is behind A but A is not behind B, then return a positive number.

        """
        # If both renderables are shipgirls, then order based on y-value.
        a_is_shipgirl = cls.is_shipgirl_renderable(renderable_a)
        b_is_shipgirl = cls.is_shipgirl_renderable(renderable_b)
        if a_is_shipgirl and b_is_shipgirl:
            if renderable_a.rect.centery > renderable_b.rect.centery:
                return 1
            else:
                return -1

        # Check if A is behind B and vice-versa.
        # Early return if one is clearly behind the other.
        a_behind_b = cls.renderable_is_behind(renderable_a, renderable_b)
        b_behind_a = cls.renderable_is_behind(renderable_b, renderable_a)
        if a_behind_b and not b_behind_a:
            return -1
        if b_behind_a and not a_behind_b:
            return 1

        # Since the decoration footprints are all rectangular, the comparison
        # only reaches this part of the code if exactly one of the renderables is
        # a shipgirl and the other is a decoration.
        # This means that the shipgirl is on a tile occupied by the decoration.
        # Render the shipgirl above if the shipgirl is occuping a tile on the
        # bottomleft and right edges of the decoration footprint.
        if a_is_shipgirl:
            shipgirl_anchor = cls.get_shipgirl_standing_tilepos(renderable_a)
            _, decoration_anchor, _ = cls.unpack_decoration_data(renderable_b)
            if (
                shipgirl_anchor[0] == decoration_anchor[0]
                or shipgirl_anchor[1] == decoration_anchor[1]
            ):
                return 1
            return -1
        else:
            shipgirl_anchor = cls.get_shipgirl_standing_tilepos(renderable_b)
            _, decoration_anchor, _ = cls.unpack_decoration_data(renderable_a)
            if (
                shipgirl_anchor[0] == decoration_anchor[0]
                or shipgirl_anchor[1] == decoration_anchor[1]
            ):
                return -1
            return 1

    @classmethod
    def get_isometric_tilepos(cls, screen_pos: CoordinateType) -> CoordinateType:
        """Convert a screen position to an isometric coordinate."""
        rel_x = screen_pos[0] - cls.floor_rect.left - cls.floor_rect.width / 2
        rel_y = screen_pos[1] - cls.floor_rect.top
        iso_x = (rel_y / cls.ISO_HALF_TILE_HEIGHT + rel_x / cls.ISO_HALF_TILE_WIDTH) / 2
        iso_y = (rel_y / cls.ISO_HALF_TILE_HEIGHT - rel_x / cls.ISO_HALF_TILE_WIDTH) / 2
        return (math.floor(iso_x), math.floor(iso_y))

    @classmethod
    def get_isometric_floor_pos(cls, tilepos: CoordinateType) -> CoordinateType:
        """Convert an isometric coordinate to to the bottom corner of that tile."""
        return pygame.Vector2(
            cls.floor_rect.left
            + cls.floor_rect.width / 2
            + (tilepos[0] - tilepos[1]) * cls.ISO_HALF_TILE_WIDTH,
            cls.floor_rect.top
            + (tilepos[0] + tilepos[1] + 2) * cls.ISO_HALF_TILE_HEIGHT
        )

    @staticmethod
    def get_decoration_sprite(decoration: str, flipped: bool) -> pygame.Surface:
        """Get the decoration sprite."""
        sprite = DataFiles.sprites["decorations"][decoration]
        if flipped:
            sprite = pygame.transform.flip(sprite, True, False)
        return sprite

    @classmethod
    def get_decoration_sprite_rect(cls, decoration: str, flipped: bool, tilepos_anchor: CoordinateType) -> pygame.Rect:
        """Get the decoration sprite bounding rect."""
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
    def get_decoration_base_polygon(
        cls, decoration: str, flipped: bool, tilepos_anchor: CoordinateType
    ) -> list[CoordinateType]:
        """Get the polygon which bounds the footprint of this decoration."""
        base_width, base_height = cls.get_decoration_base_dimensions(decoration, flipped)
        top_tilepos = (
            tilepos_anchor[0] - base_width,
            tilepos_anchor[1] - base_height
        )
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
        """Create the isometric wallpaper surface.
        
        The left and right wallpaper sprites are loaded from the spritesheet
        then skewed so that it fits the slanted edge of the isometric floor.
        """
        floor_width = (cls.FLOOR_TILES_WIDE + cls.FLOOR_TILES_TALL) * cls.ISO_HALF_TILE_WIDTH
        floor_height = (cls.FLOOR_TILES_WIDE + cls.FLOOR_TILES_TALL) * cls.ISO_HALF_TILE_HEIGHT
        wall_height = cls.WALLPAPER_HEIGHT

        wallpaper_left = DataFiles.sprites["decorations"]["wallpaper_left"]
        wallpaper_right = DataFiles.sprites["decorations"]["wallpaper_right"]

        skewed_height = wall_height + floor_height // 2
        skewed_wallpaper = pygame.Surface((floor_width, skewed_height))
        skewed_wallpaper.fill((255, 0, 0))
        skewed_wallpaper.set_colorkey((255, 0, 0))

        step = cls.ISO_HALF_TILE_WIDTH // cls.ISO_HALF_TILE_HEIGHT
        y = floor_height // 2
        for x in range(0, floor_width // 2, step):
            skewed_wallpaper.blit(
                wallpaper_left,
                (x, y),
                pygame.Rect(x, 0, step, wall_height)
            )
            y -= 1
        for x in range(0, floor_width // 2, step):
            skewed_wallpaper.blit(
                wallpaper_right,
                (floor_width // 2 + x, y),
                pygame.Rect(x, 0, step, wall_height)
            )
            y += 1

        cls.wallpaper_surf = skewed_wallpaper
        cls.wallpaper_rect = cls.wallpaper_surf.get_rect()
        cls.wallpaper_rect.left = cls.floor_rect.left
        cls.wallpaper_rect.top = cls.floor_rect.top - wall_height

    @classmethod
    def get_wallpaper_rect(cls) -> pygame.Rect:
        """Get the bounding rect for the wallpaper surface."""
        wallpaper_rect = cls.wallpaper_surf.get_rect()
        wallpaper_rect.midbottom = cls.floor_rect.center
        return wallpaper_rect

    @classmethod
    def create_floor_surf(cls):
        """Create the isometric floor surface."""
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
