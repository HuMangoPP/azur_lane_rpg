from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from collections.abc import Callable
    from engine.types import CoordinateType, ColorType
    from engine.font import Font
    from src.menus.menu_manager import MenuManager

import math
import random
import pygame

from engine.util import get_rect, get_vec, pixel_to_hex, hex_to_pixel, hex_corners, get_cluster_edges, draw_dashed_rect
from engine.button import RectangularButton

from src.constants import DataFiles, Color, Box, screen_x, screen_y
from src.menus.base_menu import Menu


def anchor():
    return pygame.Vector2(screen_x(1), screen_y(1)) - SortieNode.center


class SortieNode:
    SIZE = Box.WIDTH / 2
    center = pygame.Vector2(screen_x(0.5), screen_y(0.5))
    SELECTION_PULSE_DURATION = 2.4
    SELECTION_GLINT_CYCLE = 0.9
    SELECTION_GLINT_LIFETIME = 0.7
    SELECTION_GLINTS_PER_HEX = 4
    SELECTION_GLINT_MAX_LENGTH = 5
    SELECTION_GLINT_MARGIN = 6
    SELECTION_GLINT_DRIFT = 12

    def __init__(self, index: int, sortie_info: dict):
        self.chapter: int = sortie_info["chapter"]
        self.index = index
        self.hexes = [tuple(h) for h in sortie_info["coordinates"]]
        self.unlocked: bool = self.index <= DataFiles.save_file["sortie_progress"]
        self.cleared: bool = self.index < DataFiles.save_file["sortie_progress"]
        self.hovered = False

        cluster_edges = get_cluster_edges(self.hexes, self.SIZE)
        self.polygon = [pygame.Vector2(point) for point in cluster_edges]
        self._selection_glow_cache = {
            "cleared": self._create_combined_selection_glow(
                DataFiles.sprites["sortie_selection"]["cleared_node_selection_glow"]
            ),
            "unlocked": self._create_combined_selection_glow(
                DataFiles.sprites["sortie_selection"]["uncleared_node_selection_glow"]
            ),
            "locked": self._create_combined_selection_glow(
                DataFiles.sprites["sortie_selection"]["locked_node_selection_glow"]
            ),
        }
        self._combined_glow: pygame.Surface | None = None
        
        self._glint_surface = pygame.Surface(
            (
                2 * self.SELECTION_GLINT_MAX_LENGTH + 1,
                2 * self.SELECTION_GLINT_MAX_LENGTH + 1,
            )
        ).convert()

    def hover(self, mouse_pos: CoordinateType):
        """Update the hover state of this sortie node by checking collisions with its hexes."""
        mouse_x, mouse_y = mouse_pos
        hx, hy = pixel_to_hex(mouse_x - anchor().x, mouse_y - anchor().y, self.SIZE)
        self.hovered = self.unlocked and (hx, hy) in self.hexes

    def select(self, mouse_pos: CoordinateType) -> bool:
        """Select this sortie node by checking collisions with its hexes."""
        if not self.unlocked:
            return False

        mouse_x, mouse_y = mouse_pos
        hx, hy = pixel_to_hex(mouse_x - anchor().x, mouse_y - anchor().y, self.SIZE)
        if (hx, hy) not in self.hexes:
            return False
        
        return True

    def draw_shadow(self, surface: pygame.Surface):
        """Draw the shadow of the hex polygon."""
        polygon = [
            point + anchor() + pygame.Vector2(4, 8)
            for point in self.polygon
        ]
        pygame.draw.polygon(surface, Color.OCEAN_SHADOW, polygon)

    def _get_styling(self) -> tuple[ColorType, ColorType, pygame.Surface]:
        """Get the styling of the sortie node based on status."""
        if self.cleared:
            return (
                Color.CLEARED_ZONE_FILL,
                Color.CLEARED_ZONE_OUTLINE,
                DataFiles.sprites["user_interface"]["cleared"],
            )
        elif self.unlocked:
            fill = Color.UNCLEARED_ZONE_FILL
            outline = Color.UNCLEARED_ZONE_OUTLINE
            if len(self.hexes) > 1:
                icon = DataFiles.sprites["user_interface"]["boss"]
            else:
                icon = DataFiles.sprites["user_interface"]["uncleared"]
            return fill, outline, icon
        else:
            return (
                Color.LOCKED_ZONE_FILL,
                Color.LOCKED_ZONE_OUTLINE,
                DataFiles.sprites["user_interface"]["locked"],
            )

    def _get_selection_glow_state(self) -> str:
        """Get the cached selection-glow state for this node."""
        if self.cleared:
            return "cleared"
        if self.unlocked:
            return "unlocked"
        return "locked"

    def _create_combined_selection_glow(
        self,
        glow_sprite: pygame.Surface,
    ) -> tuple[pygame.Surface, pygame.Rect]:
        """Pre-render the glow shared by every hex in this node."""
        glow_instances: list[tuple[pygame.Surface, pygame.Rect]] = []
        for q, r in self.hexes:
            x, y = hex_to_pixel(q, r, self.SIZE)
            corners = [
                pygame.Vector2(corner)
                for corner in hex_corners(x, y, self.SIZE)
            ]
            glow_left = int(min(corner.x for corner in corners))
            glow_right = int(max(corner.x for corner in corners))
            glow_rect = pygame.Rect(
                glow_left,
                0,
                glow_right - glow_left + 1,
                glow_sprite.get_height(),
            )
            glow_rect.bottom = y
            hex_glow = pygame.transform.smoothscale(glow_sprite, glow_rect.size)
            glow_instances.append((hex_glow, glow_rect))

        glow_bounds = glow_instances[0][1].unionall([
            glow_rect
            for _, glow_rect in glow_instances[1:]
        ])
        combined_glow = pygame.Surface(glow_bounds.size)
        for hex_glow, glow_rect in glow_instances:
            combined_glow.blit(
                hex_glow,
                glow_rect.move(-glow_bounds.left, -glow_bounds.top),
                special_flags=pygame.BLEND_RGB_MAX,
            )
        return combined_glow, glow_bounds

    def draw(self, surface: pygame.Surface):
        """Draw the sortie node."""
        fill, outline, icon = self._get_styling()
        # Draw the hex.
        polygon = [point + anchor() for point in self.polygon]
        if self.hovered:
            pygame.draw.polygon(surface, outline, polygon)
        else:
            pygame.draw.polygon(surface, fill, polygon)
        pygame.draw.polygon(surface, outline, polygon, width=Box.OUTLINE_WIDTH)
        # Draw the icon.
        for q, r in self.hexes:
            x, y = hex_to_pixel(q, r, self.SIZE)
            icon_rect = icon.get_rect()
            icon_rect.center = pygame.Vector2(x,y) + anchor()
            surface.blit(icon, icon_rect)

    def _draw_selection_effect(self, surface: pygame.Surface, effect_time: float):
        """Draw the sortie node selection effect."""
        # Generate the pulsing glow.
        pulse = (math.sin(effect_time * math.tau / self.SELECTION_PULSE_DURATION) + 1) / 2
        node_anchor = anchor()
        cached_glow, glow_bounds = self._selection_glow_cache[
            self._get_selection_glow_state()
        ]
        cached_glow.set_alpha(int(128 + 127 * pulse))
        if self._combined_glow is None:
            self._combined_glow = pygame.Surface(cached_glow.get_size()).convert()
        self._combined_glow.fill((0, 0, 0))
        self._combined_glow.blit(cached_glow, (0, 0))
        surface.blit(
            self._combined_glow,
            glow_bounds.move(node_anchor),
            special_flags=pygame.BLEND_RGB_ADD,
        )
        # Render the hex polygon and icon on top so that the additive rendering
        # from the glow does not cause the hex to be mis-colored.
        _, outline, icon = self._get_styling()
        polygon = [point + anchor() for point in self.polygon]
        pygame.draw.polygon(surface, outline, polygon)

        for q, r in self.hexes:
            x, y = hex_to_pixel(q, r, self.SIZE)
            icon_rect = icon.get_rect()
            icon_rect.center = pygame.Vector2(x,y) + anchor()
            surface.blit(icon, icon_rect)

        # Glint particles.
        hex_centers = [
            pygame.Vector2(hex_to_pixel(q, r, self.SIZE)) + node_anchor
            for q, r in self.hexes
        ]
        glint_count = len(hex_centers) * self.SELECTION_GLINTS_PER_HEX
        for hex_index, hex_center in enumerate(hex_centers):
            for glint_index in range(self.SELECTION_GLINTS_PER_HEX):
                particle_index = glint_index * len(hex_centers) + hex_index
                glint_time = (
                    effect_time
                    + particle_index * self.SELECTION_GLINT_CYCLE / glint_count
                )
                glint_age = glint_time % self.SELECTION_GLINT_CYCLE
                if glint_age >= self.SELECTION_GLINT_LIFETIME:
                    continue

                cycle_index = math.floor(
                    glint_time / self.SELECTION_GLINT_CYCLE
                )
                glint_progress = glint_age / self.SELECTION_GLINT_LIFETIME
                glint_strength = (1 - glint_progress) ** 1.5
                half_spawn_width = (
                    math.sqrt(3) / 2 * self.SIZE - self.SELECTION_GLINT_MARGIN
                )
                spawn_x = (
                    (cycle_index * 29 + particle_index * 17) % (2 * half_spawn_width)
                    - half_spawn_width
                )
                half_spawn_height = (
                    self.SIZE
                    - abs(spawn_x) / math.sqrt(3)
                    - self.SELECTION_GLINT_MARGIN
                )
                spawn_y = (
                    (cycle_index * 19 + particle_index * 31) % (2 * half_spawn_height)
                    - half_spawn_height
                )
                spawn_center = hex_center + pygame.Vector2(spawn_x, spawn_y)
                center = spawn_center - pygame.Vector2(
                    0,
                    self.SELECTION_GLINT_DRIFT * glint_progress,
                )
                glint_length = 1 + round(
                    (self.SELECTION_GLINT_MAX_LENGTH - 1) * glint_strength
                )
                glint_color = tuple(
                    round(channel * glint_strength)
                    for channel in outline
                )
                glint_surface = self._glint_surface
                glint_surface_center = pygame.Vector2(
                    self.SELECTION_GLINT_MAX_LENGTH,
                    self.SELECTION_GLINT_MAX_LENGTH,
                )
                pygame.draw.line(
                    glint_surface,
                    glint_color,
                    glint_surface_center - pygame.Vector2(glint_length, 0),
                    glint_surface_center + pygame.Vector2(glint_length, 0),
                )
                pygame.draw.line(
                    glint_surface,
                    glint_color,
                    glint_surface_center - pygame.Vector2(0, glint_length),
                    glint_surface_center + pygame.Vector2(0, glint_length),
                )
                surface.blit(
                    glint_surface,
                    glint_surface.get_rect(center=center),
                    special_flags=pygame.BLEND_RGB_ADD,
                )

    def get_bounding_rect(self):
        """Compute the bounding rect of the hex polygon."""
        points = [point + anchor() for point in self.polygon]
        left = min(point.x for point in points)
        right = max(point.x for point in points)
        top = min(point.y for point in points)
        bottom = max(point.y for point in points)
        return pygame.Rect(left, top, right - left, bottom - top)


class ChapterRegion:
    OUTLINE_WIDTH = 2
    HATCH_SPACING = 14
    FILL_ALPHA = 28
    HATCH_ALPHA = 96
    OUTLINE_ALPHA = 190

    def __init__(self, chapter: int, boundary_hexes: list[CoordinateType], sortie_nodes: list[SortieNode]):
        self.chapter = chapter
        self.sortie_nodes = sortie_nodes
        polygon = [
            hex_to_pixel(*hex_coordinate, SortieNode.SIZE)
            for hex_coordinate in boundary_hexes
        ]

        left = math.floor(min(point[0] for point in polygon)) - self.OUTLINE_WIDTH
        top = math.floor(min(point[1] for point in polygon)) - self.OUTLINE_WIDTH
        right = math.ceil(max(point[0] for point in polygon)) + self.OUTLINE_WIDTH
        bottom = math.ceil(max(point[1] for point in polygon)) + self.OUTLINE_WIDTH
        self.position = pygame.Vector2(left, top)
        self.size = (right - left + 1, bottom - top + 1)
        self.polygon = [
            pygame.Vector2(point) - self.position
            for point in polygon
        ]
        self.styled_surfaces = {}

    def _get_state(self) -> str:
        """Get the status of the region."""
        if all(node.cleared for node in self.sortie_nodes):
            return "cleared"
        if any(node.unlocked for node in self.sortie_nodes):
            return "uncleared"
        return "locked"

    def _create_styled_surface(self, state: str):
        """Create the hatched region boundary surface."""
        colors = {
            "cleared": (Color.CLEARED_ZONE_FILL, Color.CLEARED_ZONE_OUTLINE),
            "uncleared": (Color.UNCLEARED_ZONE_FILL, Color.UNCLEARED_ZONE_OUTLINE),
            "locked": (Color.LOCKED_ZONE_FILL, Color.LOCKED_ZONE_OUTLINE),
        }
        fill_color, outline_color = colors[state]

        styled_surface = pygame.Surface(self.size, pygame.SRCALPHA)
        # Shade in region polygon.
        pygame.draw.polygon(
            styled_surface,
            (*fill_color, self.FILL_ALPHA),
            self.polygon,
        )
        # Draw hatching within region polygon.
        hatch_surface = pygame.Surface(self.size)
        hatch_surface.set_colorkey((0, 0, 0))
        hatch_surface.set_alpha(self.HATCH_ALPHA)
        width, height = self.size
        for x in range(-height, width + height, self.HATCH_SPACING):
            pygame.draw.line(
                hatch_surface,
                outline_color,
                (x, height),
                (x + height, 0),
                width=Box.OUTLINE_WIDTH
            )
        region_mask = pygame.Surface(self.size)
        pygame.draw.polygon(region_mask, (255, 255, 255), self.polygon)
        hatch_surface.blit(region_mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        styled_surface.blit(hatch_surface, (0, 0))
        # Draw region polygon outline.
        pygame.draw.polygon(
            styled_surface,
            (*outline_color, self.OUTLINE_ALPHA),
            self.polygon,
            width=self.OUTLINE_WIDTH,
        )
        styled_surface = styled_surface.convert_alpha()
        return styled_surface

    def draw(self, surface: pygame.Surface):
        """Draw the chapter region."""
        state = self._get_state()
        if state not in self.styled_surfaces:
            self.styled_surfaces[state] = self._create_styled_surface(state)
        surface.blit(self.styled_surfaces[state], self.position + anchor())


class Fog:
    def __init__(self, sortie_nodes: list[SortieNode], disperse: bool = False):
        self.centroids: list[pygame.Vector2] = []
        for sortie_node in sortie_nodes:
            for q, r in sortie_node.hexes:
                x, y = hex_to_pixel(q, r, sortie_node.SIZE)
                self.centroids.append(pygame.Vector2(x, y))

        small_cloud_indices = [4, 5, 6, 7, 8, 9]
        self.cloud_indices = [random.choice(small_cloud_indices) for _ in self.centroids]
        self.cloud_sprites: dict[int, pygame.Surface] = {
            cloud_index: DataFiles.sprites["background"][f"cloud{cloud_index}"].copy()
            for cloud_index in small_cloud_indices
        }
        self.cloud_shadow_sprites: dict[int, pygame.Surface] = {
            cloud_index: DataFiles.sprites["background"][f"cloud_shadow{cloud_index}"]
            for cloud_index in small_cloud_indices
        }
        self.disperse = disperse
        self.disperse_timer: float = 1

        self.cloud_timers = [
            math.radians(random.randint(0, 359))
            for _ in self.centroids
        ]
    
    def update(self, dt: float):
        """Update all clouds in the fog."""
        if self.disperse_timer <= 0:
            return
        
        self.cloud_timers = [
            (cloud_timer + dt) % math.radians(360)
            for cloud_timer in self.cloud_timers
        ]
        if self.disperse:
            if self.disperse_timer == 1:
                wind_sfx = DataFiles.sfx["wind"]
                wind_sfx.play()
                wind_sfx.fadeout(3000)
            disperse_speed = 0.33
            self.disperse_timer = max(0, self.disperse_timer - disperse_speed * dt)

    def draw(self, surface: pygame.Surface):
        """Draw all of the clouds in the fog.
        
        The clouds will move in a sinusoidal figure-8 pattern. If the clouds
        are dispersing, then they will slowly fade out, and will be rendered
        without a shadow.
        """
        if self.disperse_timer <= 0:
            return
        
        if self.disperse_timer < 1:
            cloud_alpha = int(255 * self.disperse_timer)
            for cloud_sprite in self.cloud_sprites.values():
                cloud_sprite.set_alpha(cloud_alpha)

        for centroid, cloud_index, cloud_timer in zip(self.centroids, self.cloud_indices, self.cloud_timers):
            horizontal_movement = 16
            vertical_movement = 4
            center = (
                centroid
                + anchor()
                + pygame.Vector2(horizontal_movement * math.sin(cloud_timer), vertical_movement * math.sin(2 * cloud_timer))
            )

            if self.disperse_timer >= 1:
                cloud_shadow_sprite = self.cloud_shadow_sprites[cloud_index]
                cloud_shadow_rect = cloud_shadow_sprite.get_rect()
                cloud_shadow_rect.center = center + pygame.Vector2(4, 8)
                surface.blit(cloud_shadow_sprite, cloud_shadow_rect, special_flags=pygame.BLEND_RGB_SUB)

            cloud_sprite = self.cloud_sprites[cloud_index]
            cloud_rect = cloud_sprite.get_rect()
            cloud_rect.center = center
            surface.blit(cloud_sprite, cloud_rect)


class SortieProp:
    def __init__(self, sprite_key: str, position: CoordinateType):
        self.sprite_key = sprite_key
        self.position = pygame.Vector2(position)
        self.sprite: pygame.Surface = DataFiles.sprites["sortie_selection"][sprite_key]

    def _get_rect(self):
        """Get the rect of this prop based on camera pan anchor."""
        rect = self.sprite.get_rect()
        rect.center = self.position + anchor()
        return rect

    def draw(self, surface):
        surface.blit(self.sprite, self._get_rect())


class NameRibbon:
    PADDING_X = 24
    
    def __init__(self, position: CoordinateType, text: str, scale: float = 1.0):
        self.text = text
        self.position = pygame.Vector2(position)
        self.scale = scale
        self._previous_text: str | None = None
        self._cached_surface: pygame.Surface | None = None
    
    def _get_width(self, font_registry: dict[str, Font]):
        """Get the full width of the ribbon banner."""
        if self._previous_text == self.text and self._cached_surface is not None:
            return self._cached_surface.get_width()

        left = pygame.transform.scale_by(
            DataFiles.sprites["sortie_selection"]["name_left"], self.scale
        )
        right = pygame.transform.scale_by(
            DataFiles.sprites["sortie_selection"]["name_right"], self.scale
        )
        middle = pygame.transform.scale_by(
            DataFiles.sprites["sortie_selection"]["name_middle"], self.scale
        )
        text_width = font_registry["handwritten"].get_width(self.text, self.scale, 0) - Box.WIDTH
        # Extend the middle portion by the text width if necessary.
        middle_width = max(middle.get_width(), text_width + 2 * self.PADDING_X)
        return left.get_width() + middle_width + right.get_width()

    def _get_rect(self, font_registry: dict[str, Font]):
        """Get the bounding rectangle of the ribbon banner."""
        width = self._get_width(font_registry)
        height = DataFiles.sprites["sortie_selection"]["name_middle"].get_height() * self.scale
        return get_rect(width=width, height=height, center=self.position + anchor())

    def _render_surface(self, font_registry: dict[str, Font]) -> pygame.Surface:
        """Render the ribbon banner and text into a cacheable surface."""
        left = pygame.transform.scale_by(
            DataFiles.sprites["sortie_selection"]["name_left"], self.scale
        )
        right = pygame.transform.scale_by(
            DataFiles.sprites["sortie_selection"]["name_right"], self.scale
        )
        middle = pygame.transform.scale_by(
            DataFiles.sprites["sortie_selection"]["name_middle"], self.scale
        )
        text_width = (
            font_registry["handwritten"].get_width(self.text, self.scale, 0)
            - Box.WIDTH
        )
        middle_width = max(middle.get_width(), text_width + 2 * self.PADDING_X)
        width = int(left.get_width() + middle_width + right.get_width())
        ribbon_surface = pygame.Surface((width, middle.get_height())).convert()
        ribbon_surface.fill((255, 0, 0))

        left_rect = left.get_rect(topleft=(0, 0))
        ribbon_surface.blit(left, left_rect)

        middle_rect = middle.get_rect()
        middle_rect.left = left_rect.right
        middle_rect.top = 0
        middle_right = ribbon_surface.get_width() - right.get_width()
        while middle_rect.left < middle_right:
            # Extend the middle portion by however much the text width requires.
            source_width = min(middle.get_width(), middle_right - middle_rect.left)
            source_rect = pygame.Rect(0, 0, source_width, middle.get_height())
            ribbon_surface.blit(middle, middle_rect, source_rect)
            middle_rect.left += source_width

        right_rect = right.get_rect(topright=(ribbon_surface.get_width(), 0))
        ribbon_surface.blit(right, right_rect)

        font_registry["handwritten"].render(
            ribbon_surface,
            self.text,
            ribbon_surface.get_rect().center,
            Color.BLACK,
            self.scale,
            style="center",
        )
        ribbon_surface.set_colorkey((255, 0, 0), pygame.RLEACCEL)
        return ribbon_surface

    def draw(self, surface: pygame.Surface, font_registry: dict[str, Font]):
        """Draw the cached ribbon, rebuilding it when its text changes."""
        if self._previous_text != self.text:
            self._cached_surface = self._render_surface(font_registry)
            self._previous_text = self.text

        rect = self._get_rect(font_registry)
        surface.blit(self._cached_surface, rect)

class ChapterNameRibbon:
    Y_OFFSET_IN_HEXES = 4
    CHAPTER_NAMES = [
        "training exercise",
        "patrol route",
        "crimson reef",
        "stormy sea",
        "mirror sea"
    ]

    def __init__(self, chapter: int, sortie_nodes: list[SortieNode]):
        if chapter < len(self.CHAPTER_NAMES):
            text = self.CHAPTER_NAMES[chapter]
        else:
            text = f"region {chapter}"
        position = self._get_position(sortie_nodes)

        self.ribbon = NameRibbon(position, text)

    def _get_position(self, sortie_nodes: list[SortieNode]):
        """Compute the position to place the ribbon based on the sortie node bounding box."""
        hex_positions = []
        for sortie_node in sortie_nodes:
            for q, r in sortie_node.hexes:
                hex_positions.append(pygame.Vector2(hex_to_pixel(q, r, SortieNode.SIZE)))

        left = min(position.x for position in hex_positions)
        right = max(position.x for position in hex_positions)
        bottom = max(position.y for position in hex_positions)
        return pygame.Vector2(
            (left + right) / 2,
            bottom + self.Y_OFFSET_IN_HEXES * SortieNode.SIZE,
        )

    def draw(self, surface: pygame.Surface, font_registry: dict[str, Font]):
        """Draw the chapter name ribbon banner."""
        self.ribbon.draw(surface, font_registry)


class ChapterProgressAnnotation:
    TEXT_SCALE = 1.0
    TEXT_OFFSET = 24
    TEXT_SURFACE_PADDING = 2
    MIN_WIDTH = 160
    CURVE_SAMPLE_SPACING = 6
    DASH_LENGTH = 9
    DASH_GAP = 6
    LINE_WIDTH = 2
    ARROWHEAD_LENGTH = 12
    ARROWHEAD_ANGLE = math.radians(32)

    def __init__(self, chapter: int, sortie_nodes: list[SortieNode], text_shift: int = 16):
        self.chapter = chapter
        self.sortie_nodes = sortie_nodes

        # This annotation is a upwards curving arrow from the leftside of the
        # sortie node cluster to the right side, as the general layout of
        # the sortie nodes for a given chapter climbs to the topright.
        hex_centers = [
            pygame.Vector2(hex_to_pixel(*hex_tile, SortieNode.SIZE))
            for sortie_node in sortie_nodes
            for hex_tile in sortie_node.hexes
        ]
        leftmost_hex = min(hex_centers, key=lambda point: point.x)
        rightmost_hex = max(hex_centers, key=lambda point: point.x)

        width_extension = max(
            0,
            (self.MIN_WIDTH - (rightmost_hex.x - leftmost_hex.x)) / 2,
        )
        vertical_down_shift = 64
        start_point = leftmost_hex + pygame.Vector2(-width_extension, vertical_down_shift)
        end_point = rightmost_hex + pygame.Vector2(width_extension, vertical_down_shift)
        midpoint_offset = pygame.Vector2(0, 32)
        mid_point = start_point.lerp(end_point, 0.5) + midpoint_offset

        self.curve_points = self.create_circular_curve(start_point, mid_point, end_point)
        # The text is placed at the center of the curve.
        # The text is also rotated so that it is tangent to the curve
        # at that midpoint.
        mid_index = min(
            range(len(self.curve_points)),
            key=lambda index: self.curve_points[index].distance_squared_to(mid_point),
        )
        previous_point = self.curve_points[max(0, mid_index - 1)]
        next_point = self.curve_points[min(len(self.curve_points) - 1, mid_index + 1)]
        text_direction = (next_point - previous_point).normalize()
        text_normal = pygame.Vector2(-text_direction.y, text_direction.x)
        if text_normal.y < 0:
            text_normal *= -1
        self.text_position = (
            self.curve_points[mid_index]
            + text_normal * self.TEXT_OFFSET
            + text_direction * text_shift
        )
        self.text_angle = math.degrees(math.atan2(-text_direction.y, text_direction.x,))
        self.curve_surface, self.curve_surface_position = self._create_curve_surface()
        self.cached_text: str | None = None
        self.cached_text_surface: pygame.Surface | None = None

    # TODO Consider whether this is useful enough to move to engine.
    @classmethod
    def create_circular_curve(
        cls, start_point: pygame.Vector2, mid_point: pygame.Vector2, end_point: pygame.Vector2
    ) -> list[pygame.Vector2]:
        """Compute a circular point given the start, mid, and end points.
        """
        start_x, start_y = start_point
        mid_x, mid_y = mid_point
        end_x, end_y = end_point
        determinant = 2 * (
            start_x * (mid_y - end_y)
            + mid_x * (end_y - start_y)
            + end_x * (start_y - mid_y)
        )
        floating_point_tolerance = 0.001
        if abs(determinant) < floating_point_tolerance:
            return [start_point, mid_point, end_point]

        start_length_squared = start_point.length_squared()
        mid_length_squared = mid_point.length_squared()
        end_length_squared = end_point.length_squared()
        center = pygame.Vector2(
            (
                start_length_squared * (mid_y - end_y)
                + mid_length_squared * (end_y - start_y)
                + end_length_squared * (start_y - mid_y)
            ) / determinant,
            (
                start_length_squared * (end_x - mid_x)
                + mid_length_squared * (start_x - end_x)
                + end_length_squared * (mid_x - start_x)
            ) / determinant,
        )
        radius = center.distance_to(start_point)

        start_angle = math.atan2(start_y - center.y, start_x - center.x)
        mid_angle = math.atan2(mid_y - center.y, mid_x - center.x)
        end_angle = math.atan2(end_y - center.y, end_x - center.x)
        counterclockwise_span = (end_angle - start_angle) % math.tau
        counterclockwise_mid_span = (mid_angle - start_angle) % math.tau
        if counterclockwise_mid_span <= counterclockwise_span:
            angle_span = counterclockwise_span
        else:
            angle_span = -((start_angle - end_angle) % math.tau)

        arc_length = radius * abs(angle_span)
        num_segments = max(2, math.ceil(arc_length / cls.CURVE_SAMPLE_SPACING))
        return [
            center + get_vec(
                radius,
                start_angle + angle_span * segment / num_segments,
            )
            for segment in range(num_segments + 1)
        ]

    def _get_text(self) -> str | None:
        """Get the text content of the annotation based on clear state."""
        if all(node.cleared for node in self.sortie_nodes):
            return "secured waters"

        current_sortie = DataFiles.save_file["sortie_progress"]
        if any(node.index == current_sortie for node in self.sortie_nodes):
            return "operation plan"
        return None

    def _render_text_surface(
        self,
        font_registry: dict[str, Font],
        text: str,
    ) -> pygame.Surface:
        """Render and cache-ready the rotated text annotation."""
        font = font_registry["handwritten"]
        text_size = (
            math.ceil(font.get_width(text, self.TEXT_SCALE, 0)),
            math.ceil(font.get_height(text, self.TEXT_SCALE, 0)),
        )
        text_surface = pygame.Surface((
            text_size[0] + 2 * self.TEXT_SURFACE_PADDING,
            text_size[1] + 2 * self.TEXT_SURFACE_PADDING,
        ))
        text_surface.fill((255, 0, 0))
        text_surface.set_colorkey((255, 0, 0))
        font.render(
            text_surface,
            text,
            text_surface.get_rect().center,
            Color.WHITE,
            self.TEXT_SCALE,
            style="center",
        )
        rotated_text = pygame.transform.rotate(text_surface, self.text_angle)
        rotated_text = rotated_text.convert()
        rotated_text.set_colorkey((255, 0, 0), pygame.RLEACCEL)
        return rotated_text

    def _draw_text(
        self,
        surface: pygame.Surface,
        font_registry: dict[str, Font],
        text: str,
        camera_anchor: pygame.Vector2,
    ):
        """Draw the cached rotated text annotation."""
        if text != self.cached_text:
            self.cached_text = text
            self.cached_text_surface = self._render_text_surface(font_registry, text).convert()

        rotated_text_rect = self.cached_text_surface.get_rect(
            center=self.text_position + camera_anchor
        )
        surface.blit(self.cached_text_surface, rotated_text_rect)

    @classmethod
    def _draw_dashed_curve(cls, surface: pygame.Surface, points: list[pygame.Vector2]):
        """Draw a curve using a dashed line."""
        drawing_dash = True
        distance_until_toggle = cls.DASH_LENGTH

        for segment_start, segment_end in zip(points, points[1:]):
            direction = segment_end - segment_start
            segment_length = direction.length()
            if segment_length == 0:
                continue
            direction /= segment_length
            position = segment_start
            distance_remaining = segment_length

            while distance_remaining > 0:
                step = min(distance_remaining, distance_until_toggle)
                next_position = position + direction * step
                if drawing_dash:
                    pygame.draw.line(
                        surface,
                        Color.WHITE,
                        position,
                        next_position,
                        width=cls.LINE_WIDTH,
                    )
                position = next_position
                distance_remaining -= step
                distance_until_toggle -= step

                floating_point_tolerance = 0.001
                if distance_until_toggle <= floating_point_tolerance:
                    drawing_dash = not drawing_dash
                    distance_until_toggle = (
                        cls.DASH_LENGTH if drawing_dash else cls.DASH_GAP
                    )

    def _create_curve_surface(self) -> tuple[pygame.Surface, pygame.Vector2]:
        """Pre-render the static dashed curve and arrowhead."""
        arrow_direction = (self.curve_points[-1] - self.curve_points[-2]).normalize()
        backwards_angle = math.atan2(-arrow_direction.y, -arrow_direction.x)
        arrow_sides = [
            self.curve_points[-1]
            + get_vec(self.ARROWHEAD_LENGTH, backwards_angle + angle_offset)
            for angle_offset in (-self.ARROWHEAD_ANGLE, self.ARROWHEAD_ANGLE)
        ]

        drawn_points = self.curve_points + arrow_sides
        left = math.floor(min(point.x for point in drawn_points)) - self.LINE_WIDTH
        top = math.floor(min(point.y for point in drawn_points)) - self.LINE_WIDTH
        right = math.ceil(max(point.x for point in drawn_points)) + self.LINE_WIDTH
        bottom = math.ceil(max(point.y for point in drawn_points)) + self.LINE_WIDTH
        surface_position = pygame.Vector2(left, top)

        curve_surface = pygame.Surface((right - left + 1, bottom - top + 1)).convert()
        curve_surface.fill((255, 0, 0))
        local_curve_points = [
            point - surface_position
            for point in self.curve_points
        ]
        self._draw_dashed_curve(curve_surface, local_curve_points)

        arrow_tip = local_curve_points[-1]
        for arrow_side in arrow_sides:
            pygame.draw.line(
                curve_surface,
                Color.WHITE,
                arrow_tip,
                arrow_side - surface_position,
                width=self.LINE_WIDTH,
            )

        curve_surface.set_colorkey((255, 0, 0), pygame.RLEACCEL)
        return curve_surface, surface_position

    def draw(self, surface: pygame.Surface, font_registry: dict[str, Font]):
        """Draw the chapter progress annotation."""
        text = self._get_text()
        if text is None:
            return

        camera_anchor = anchor()
        surface.blit(
            self.curve_surface,
            self.curve_surface_position + camera_anchor,
        )
        self._draw_text(surface, font_registry, text, camera_anchor)


class Background:
    def __init__(self):
        num_waves = 36
        wave_index_offset = 8
        wave_sprites = [
            DataFiles.sprites["sortie_selection"][f"wave{wave_index}"]
            for wave_index in range(
                DataFiles.sprites["sortie_selection"]["num_wave_sprites"]
            )
        ]
        self.wave_sprites = random.choices(wave_sprites, k=num_waves)
        wave_height = DataFiles.sprites["sortie_selection"]["wave"].get_height() / 2
        self.wave_ys: list[float] = [wave_height * (i - num_waves + wave_index_offset) for i in range(num_waves)]
        self.wave_timers = [math.radians(random.randint(0, 359)) for _ in range(num_waves)]

        self._markings_surf: pygame.Surface | None = None
        self._markings_rect: pygame.Rect | None = None

    def update(self, dt: float):
        """Update the background timers."""
        self.wave_timers = [(wave_timer + dt) % math.radians(360) for wave_timer in self.wave_timers]

    def draw(self, surface: pygame.Surface):
        """Draw the background waves."""
        num_wave_reps = 10
        vertical_movement = 4
        horizontal_movement = 32
        camera_anchor = anchor()
        screen_right = screen_x(1)
        screen_bottom = screen_y(1)
        for wave_sprite, wave_y, wave_timer in zip(
            self.wave_sprites,
            self.wave_ys,
            self.wave_timers,
        ):
            wave_rect = wave_sprite.get_rect()
            wave_rect.top = (
                wave_y
                + vertical_movement * math.sin(2 * wave_timer)
                + camera_anchor.y
            )
            if wave_rect.bottom < 0 or wave_rect.top > screen_bottom:
                continue
            centerx = (
                horizontal_movement * math.sin(wave_timer)
                + camera_anchor.x
                - screen_x(0.5)
            )
            for i in range(num_wave_reps):
                wave_rect.centerx = centerx + wave_rect.width * i
                surface.blit(wave_sprite, wave_rect)

    def draw_markings(self, surface: pygame.Surface, font_registry: dict[str, Font]):
        """Draw background markings like a compass rose and cosmetic map scale."""
        if self._markings_surf is None:
            compass_rose = DataFiles.sprites["sortie_selection"]["compass_rose"]
            compass_rose_rect = compass_rose.get_rect()

            map_scale = DataFiles.sprites["sortie_selection"]["map_scale"]
            map_scale_rect = map_scale.get_rect()
            map_scale_rect.bottom = compass_rose_rect.height
            map_scale_rect.left = compass_rose_rect.right + Box.PADDING

            big_pixel_font = font_registry["big_pixel"]
            surf_width = (
                map_scale_rect.right
                - compass_rose_rect.left
                + Box.PADDING
                + big_pixel_font.get_width("kilometers", scale=1, box_width=0)
                + 1
            )
            surf_height = compass_rose_rect.height
            self._markings_surf = pygame.Surface((surf_width, surf_height))
            self._markings_surf.fill((255, 0, 0))
            self._markings_surf.blit(compass_rose, compass_rose_rect)
            self._markings_surf.blit(map_scale, map_scale_rect)

            scale_distance = 200
            for x in [0, 0.25, 0.5, 1]:
                big_pixel_font.render(
                    self._markings_surf,
                    str(int(x * scale_distance)),
                    (map_scale_rect.left + x * map_scale_rect.width, map_scale_rect.top - big_pixel_font.font_height),
                    Color.WHITE,
                    scale=1,
                    style="center",
                    outline_color=Color.BLACK
                )
            big_pixel_font.render(
                self._markings_surf,
                "kilometers",
                pygame.Vector2(map_scale_rect.right + Box.PADDING, map_scale_rect.centery),
                Color.WHITE,
                scale=1,
                style="centerleft",
                outline_color=Color.BLACK
            )
            self._markings_surf = self._markings_surf.convert()
            self._markings_surf.set_colorkey((255, 0, 0), pygame.RLEACCEL)
            self._markings_rect = self._markings_surf.get_rect(bottomleft=(Box.LEFT_OF_SCREEN, Box.BOTTOM_OF_SCREEN))

        surface.blit(self._markings_surf, self._markings_rect)


class SortieOrderCard:
    WIDTH = 3 * (Box.WIDTH + Box.PADDING) + Box.PADDING + 2 * Box.PADDING
    HEIGHT = 5 * Box.HEIGHT + Box.PADDING
    AUTHORIZATION_HEIGHT = 72
    AUTHORIZATION_DURATION = 1
    AUTHORIZATION_IMPACT_TIME = 0.15
    AUTHORIZATION_LIFT_TIME = 0.30
    AUTHORIZATION_DISAPPEAR_TIME = 0.5
    CHART_GAP = 2 * Box.PADDING

    def __init__(self, authorize_sortie: Callable):
        self.rect = get_rect(width=self.WIDTH, height=self.HEIGHT, left=0, top=0)
        self.page_rect = self.rect.inflate(-2 * Box.PADDING, -2 * Box.PADDING - Box.HEIGHT / 2)
        self.side = "right"
        self.node: SortieNode | None = None
        self.authorize_sortie = authorize_sortie
        self.authorizing = False
        self.authorization_timer = 0
        self.authorization_impact_played = False
        self.authorization_pos = pygame.Vector2()

        self.authorization_stamp = DataFiles.sprites["props"]["stamp"]

        self.button = RectangularButton(
            get_rect(width=self.WIDTH - 4 * Box.PADDING, height=self.AUTHORIZATION_HEIGHT),
            self.begin_authorization,
            active=False,
        )

        self._cache_rect = pygame.Rect((0, 0), self.rect.size)
        self._cache_page_rect = self.page_rect.copy()
        self._cache_page_rect.centerx = self._cache_rect.centerx
        self._cache_page_rect.bottom = self._cache_rect.bottom - Box.PADDING
        self._cache_button_rect = self.button.rect.copy()
        self._cache_button_rect.centerx = self._cache_rect.centerx
        self._cache_button_rect.bottom = self._cache_page_rect.bottom - Box.PADDING
        self._state_independent_surface = self._create_state_independent_surface()
        self._state_independent_content_rendered = False
        self._state_cache_key: tuple[int, bool] | None = None
        self._state_cached_surface: pygame.Surface | None = None

    @staticmethod
    def get_safe_rect() -> pygame.Rect:
        """Compute the safe bound of the screen.
        
        This is the inset rect of the screen where this sortie order card can
        be rendered without being off-screen.
        """
        return pygame.Rect(
            Box.LEFT_OF_SCREEN,
            Box.TOP_OF_SCREEN,
            Box.RIGHT_OF_SCREEN - Box.LEFT_OF_SCREEN,
            Box.BOTTOM_OF_SCREEN - Box.TOP_OF_SCREEN,
        )

    def get_unclamped_rect(self, node_rect: pygame.Rect, side: str = None) -> pygame.Rect:
        """Get the rect for the sortie order card that is not clamped to screen bounds."""
        side = side or self.side
        rect = self.rect.copy()
        rect.centery = node_rect.centery
        if side == "right":
            rect.left = node_rect.right + self.CHART_GAP
        else:
            rect.right = node_rect.left - self.CHART_GAP
        return rect

    def layout(self):
        """Format the screen to accommodate the sortie order card.
        
        Compute the node bounding rect and get the unclamped rect based off that
        bounding rect. Then clamp the order card based on screen bounds.
        """
        if self.node is None:
            return

        node_rect = self.node.get_bounding_rect()
        rect = self.get_unclamped_rect(node_rect)
        safe_rect = self.get_safe_rect()
        rect.clamp_ip(safe_rect)
        self.rect.topleft = rect.topleft
        self.page_rect.centerx = self.rect.centerx
        self.page_rect.bottom = self.rect.bottom - Box.PADDING

        self.button.rect.centerx = self.rect.centerx
        self.button.rect.bottom = self.page_rect.bottom - Box.PADDING
        if not self.authorizing:
            self.authorization_pos = pygame.Vector2(self.button.rect.center)

    def select(self, node: SortieNode, side: str, authorize_immediately: bool):
        """Select the node, and hence layout the order card next to the node bounding rect.
        
        The authorize_immediately flag indicates whether the button should immediately be
        active or not.
        """
        self.node = node
        self.side = side
        self.authorizing = False
        self.authorization_timer = 0
        self.authorization_impact_played = False
        self.authorization_pos = pygame.Vector2(self.button.rect.center)
        self.layout()
        self.button.active = authorize_immediately

    def clear(self):
        """Clear the order card state."""
        self.node: SortieNode | None = None
        self.button.active = False
        self.button.hovered = False
        self.authorizing = False
        self.authorization_timer = 0
        self.authorization_impact_played = False
        self.authorization_pos = pygame.Vector2()

    def begin_authorization(self, click_pos: CoordinateType | None = None):
        """Start the authorization animation."""
        if self.node is None or self.authorizing or not self.button.active:
            return

        if click_pos is None:
            click_pos = pygame.mouse.get_pos()
        self.authorization_pos = pygame.Vector2(click_pos)
        self.authorizing = True
        self.authorization_timer = 0
        self.authorization_impact_played = False
        self.button.active = False
        self.button.hovered = False

    def update(self, dt: float):
        """Update the order card, i.e. animate the authorization animation."""
        if not self.authorizing:
            return

        previous_timer = self.authorization_timer
        self.authorization_timer = min(
            self.AUTHORIZATION_DURATION,
            self.authorization_timer + dt,
        )
        if (
            not self.authorization_impact_played
            and previous_timer < self.AUTHORIZATION_IMPACT_TIME <= self.authorization_timer
        ):
            self.authorization_impact_played = True
            DataFiles.sfx["click"].play()

        if self.authorization_timer >= self.AUTHORIZATION_DURATION:
            self.authorizing = False
            self.authorize_sortie()

    def _draw_paper(
        self,
        surface: pygame.Surface,
        card_rect: pygame.Rect,
        page_rect: pygame.Rect,
    ):
        """Draw the paper component of the order card."""
        dossier_rect = card_rect.inflate(0, -Box.HEIGHT / 2)
        dossier_rect.bottomleft = card_rect.bottomleft
        pygame.draw.rect(surface, Color.DOSSIER, dossier_rect)
        dossier_tab = [
            pygame.Vector2(card_rect.topleft),
            pygame.Vector2(card_rect.topleft) + pygame.Vector2(Box.WIDTH - Box.PADDING, 0),
            pygame.Vector2(card_rect.topleft) + pygame.Vector2(Box.WIDTH + Box.PADDING, Box.HEIGHT / 2),
            pygame.Vector2(card_rect.topleft) + pygame.Vector2(0, Box.HEIGHT / 2),
        ]
        pygame.draw.polygon(surface, Color.DOSSIER, dossier_tab)

        undersheets = [
            (-2, pygame.Vector2(-2, 3), Color.DOSSIER_PAPER_UNDERSIDE),
            (2, pygame.Vector2(3, 1), Color.DOSSIER_CARD),
        ]
        for angle, offset, color in undersheets:
            pygame.draw.polygon(
                surface,
                color,
                Box.get_rotated_rect_polygon(page_rect, angle, offset),
            )
        pygame.draw.rect(surface, Color.DOSSIER_PAGE, page_rect)

    def _draw_static_header(
        self,
        surface: pygame.Surface,
        font_registry: dict[str, Font],
        page_rect: pygame.Rect,
    ):
        """Draw header content shared by every sortie state."""
        small_font = font_registry["pixel"]
        left = page_rect.left + Box.PADDING
        top = page_rect.top + Box.PADDING
        small_font.render(
            surface,
            "azur lane naval command",
            (left, top),
            Color.DOSSIER_RULE,
            1,
        )
        text_y_padding = 5
        operation_order_text_y = top + small_font.font_height + text_y_padding
        small_font.render(
            surface,
            "operation order",
            (left, operation_order_text_y),
            Color.DOSSIER_INK,
            scale=1,
        )

    def _draw_header(
        self,
        surface: pygame.Surface,
        font_registry: dict[str, Font],
        page_rect: pygame.Rect,
    ) -> int:
        """Draw header content that depends on the selected sortie."""
        font = font_registry["big_pixel"]
        small_font = font_registry["pixel"]
        left = page_rect.left + Box.PADDING
        right = page_rect.right - Box.PADDING
        top = page_rect.top + Box.PADDING

        # Get the header text based on node status.
        if self.node.cleared:
            status = "charted territory"
            status_color = Color.CLEARED_ZONE_FILL
        else:
            status = "uncharted waters"
            status_color = Color.UNCLEARED_ZONE_FILL

        form_text = f"form so-{self.node.index + 1:03d}"
        form_left = right - small_font.get_width(form_text, 1, 0)
        small_font.render(surface, form_text, (form_left, top), Color.DOSSIER_RULE, 1)
        text_y_padding = 5
        operation_order_text_y = top + small_font.font_height + text_y_padding
        sector_text_y = operation_order_text_y + small_font.font_height + text_y_padding
        sector_text_scale = 2
        font.render(
            surface,
            f"sector {self.node.index + 1:02d}",
            (left, sector_text_y),
            Color.DOSSIER_INK,
            sector_text_scale
        )

        status_width = font.get_width(status, scale=1, box_width=0) + 2 * Box.PADDING
        status_rect = get_rect(
            width=status_width,
            height=font.font_height + 2 * Box.PADDING,
            left=left,
            top=sector_text_y + sector_text_scale * font.font_height + text_y_padding,
        )
        pygame.draw.rect(surface, status_color, status_rect, width=Box.OUTLINE_WIDTH)
        pygame.draw.rect(surface, status_color, status_rect.inflate(-4, -4), width=1)
        font.render(surface, status, status_rect.center, status_color, scale=1, style="center")

        rule_y = status_rect.bottom + text_y_padding
        pygame.draw.line(surface, Color.DOSSIER_RULE, (left, rule_y), (right, rule_y))

        return rule_y

    def _draw_rewards(
        self,
        surface: pygame.Surface,
        font_registry: dict[str, Font],
        header_bottom: int,
        page_rect: pygame.Rect,
    ):
        """Draw the rewards section of the order card."""
        font = font_registry["big_pixel"]
        left = page_rect.left + Box.PADDING
        heading = "allotment issued" if self.node.cleared else "first-clear allotment"
        text_y_padding = 5
        header_text_y = header_bottom + text_y_padding
        font.render(surface, heading, (left, header_text_y), Color.DOSSIER_RULE, scale=1)

        reward_top = header_text_y + font.font_height + text_y_padding
        rewards = DataFiles.sortie_data[self.node.index]["rewards"]
        if not rewards:
            # No rewards are present, so render a default empty text.
            reward_area = pygame.Rect(
                left,
                reward_top,
                page_rect.width - 2 * Box.PADDING,
                Box.HEIGHT,
            )
            font.render(surface, "no allotment on file", reward_area.center, Color.DOSSIER_RULE, scale=1, style="center")
            return

        for i, (reward, count) in enumerate(rewards.items()):
            rect = get_rect(
                width=Box.WIDTH,
                height=Box.HEIGHT,
                left=left + i * (Box.WIDTH + Box.PADDING),
                top=reward_top,
            )
            pygame.draw.rect(surface, Color.DOSSIER_CARD_SHADOW, rect.move(2, 2))
            pygame.draw.rect(surface, Color.DOSSIER_CARD, rect)
            surface.blit(DataFiles.get_entity_sprite(reward), rect)

            quantity_rect = get_rect(width=rect.width, height=14, left=rect.left, bottom=rect.bottom)
            pygame.draw.rect(surface, Color.DOSSIER_CARD, quantity_rect)
            pygame.draw.line(surface, Color.DOSSIER_RULE, quantity_rect.topleft, quantity_rect.topright)
            font.render(surface, f"qty {count:02d}", quantity_rect.center, Color.DOSSIER_INK, scale=1, style="center")
            pygame.draw.rect(surface, Color.DOSSIER_INK, rect, width=1)

        # The sortie has already been cleared.
        # Render a special stamp sprite that indicates this to the player.
        if self.node.cleared:
            obtained_stamp = DataFiles.sprites["sortie_selection"]["obtained_stamp"].copy()
            obtained_stamp.set_alpha(128)
            obtained_stamp_rect = obtained_stamp.get_rect()
            obtained_stamp_rect.centerx = page_rect.centerx
            obtained_stamp_rect.top = reward_top - Box.HEIGHT / 3
            surface.blit(obtained_stamp, obtained_stamp_rect)

    def _draw_static_authorization(
        self,
        surface: pygame.Surface,
        font_registry: dict[str, Font],
        page_rect: pygame.Rect,
        button_rect: pygame.Rect,
    ):
        """Draw authorization labels shared by every sortie and button state."""
        label_y = button_rect.top - 16
        rule_y = button_rect.top - 24
        content_left = page_rect.left + Box.PADDING
        content_right = page_rect.right - Box.PADDING
        pygame.draw.line(
            surface,
            Color.DOSSIER_RULE,
            (content_left, rule_y),
            (content_right, rule_y),
        )
        font_registry["big_pixel"].render(
            surface,
            "command authorization",
            (content_left, label_y),
            Color.DOSSIER_RULE,
            1,
        )

    def _create_state_independent_surface(self) -> pygame.Surface:
        """Create the position-independent paper layer."""
        surface = pygame.Surface(self._cache_rect.size).convert()
        surface.fill((255, 0, 0))
        self._draw_paper(
            surface,
            self._cache_rect,
            self._cache_page_rect,
        )
        return surface

    def _ensure_state_independent_content(
        self,
        font_registry: dict[str, Font],
    ):
        """Render font-dependent static page content once."""
        if self._state_independent_content_rendered:
            return

        self._draw_static_header(
            self._state_independent_surface,
            font_registry,
            self._cache_page_rect,
        )
        self._draw_static_authorization(
            self._state_independent_surface,
            font_registry,
            self._cache_page_rect,
            self._cache_button_rect,
        )
        self._state_independent_content_rendered = True

    def _ensure_state_cache(self, font_registry: dict[str, Font]):
        """Rebuild the selected-sortie layer when its state changes."""
        assert self.node is not None
        self._ensure_state_independent_content(font_registry)
        state_cache_key = (self.node.index, self.node.cleared)
        if (
            state_cache_key == self._state_cache_key
            and self._state_cached_surface is not None
        ):
            return

        state_surface = self._state_independent_surface.copy()
        header_bottom = self._draw_header(
            state_surface,
            font_registry,
            self._cache_page_rect,
        )
        self._draw_rewards(
            state_surface,
            font_registry,
            header_bottom,
            self._cache_page_rect,
        )
        state_surface.set_colorkey((255, 0, 0), pygame.RLEACCEL)
        self._state_cached_surface = state_surface
        self._state_cache_key = state_cache_key

    def _draw_authorization(self, surface: pygame.Surface, font_registry: dict[str, Font]):
        """Draw the authorization button."""
        field_rect = self.button.rect
        # Button with hover state.
        hovered = self.button.active and self.button.hovered
        imprint_visible = (
            self.authorizing
            and self.authorization_timer >= self.AUTHORIZATION_IMPACT_TIME
        )
        action_highlighted = hovered or self.authorizing
        ink_color = Color.START_SORTIE_BUTTON if action_highlighted else Color.DOSSIER_RULE

        if hovered:
            pygame.draw.rect(surface, Color.DOSSIER_CARD, field_rect)
        draw_dashed_rect(surface, ink_color, field_rect, dash_length=8, gap_length=4, width=Box.OUTLINE_WIDTH)

        font_registry["big_pixel"].render(
            surface,
            "stamp here",
            (field_rect.centerx, field_rect.centery - 5),
            ink_color,
            2,
            style="center",
        )
        font_registry["big_pixel"].render(
            surface,
            "authorize sortie",
            (field_rect.centerx, field_rect.centery + 15),
            ink_color,
            1,
            style="center",
        )

        # Stamp pattern for authorization animation.
        if imprint_visible:
            stamp_pattern_sprite = DataFiles.sprites["props"]["stamp_pattern"].copy()
            if self.authorization_timer >= self.AUTHORIZATION_DISAPPEAR_TIME:
                fade_duration = (
                    self.AUTHORIZATION_DURATION
                    - self.AUTHORIZATION_DISAPPEAR_TIME
                )
                fade_progress = (
                    (self.AUTHORIZATION_DURATION - self.authorization_timer)
                    / fade_duration
                )
                stamp_pattern_sprite.set_alpha(int(255 * fade_progress))
            else:
                stamp_pattern_sprite.set_alpha(255)
            stamp_pattern_rect = stamp_pattern_sprite.get_rect()
            stamp_pattern_rect.center = self.authorization_pos
            surface.blit(stamp_pattern_sprite, stamp_pattern_rect)

    def _draw_authorization_stamp(self, surface: pygame.Surface):
        """Draw the stamp prop for the authorization animation.
        
        This stamp plays an up and stamp down animation like the decoration store.
        """
        if not self.authorizing or self.authorization_timer > self.AUTHORIZATION_LIFT_TIME:
            return

        target_pos = self.authorization_pos
        raised_pos = target_pos - pygame.Vector2(0, Box.HEIGHT)
        if self.authorization_timer <= self.AUTHORIZATION_IMPACT_TIME:
            progress = self.authorization_timer / self.AUTHORIZATION_IMPACT_TIME
            stamp_pos = raised_pos.lerp(target_pos, progress)
        else:
            lift_duration = self.AUTHORIZATION_LIFT_TIME - self.AUTHORIZATION_IMPACT_TIME
            progress = (
                (self.authorization_timer - self.AUTHORIZATION_IMPACT_TIME)
                / lift_duration
            )
            stamp_pos = target_pos.lerp(raised_pos, progress)

        stamp_rect = self.authorization_stamp.get_rect()
        stamp_rect.centerx = round(stamp_pos.x)
        stamp_rect.bottom = round(stamp_pos.y + Box.HEIGHT / 2)
        surface.blit(self.authorization_stamp, stamp_rect)

    def draw(self, surface: pygame.Surface, font_registry: dict[str, Font]):
        """Draw the sortie order card."""
        if self.node is None:
            return

        self.layout()
        self._ensure_state_cache(font_registry)
        assert self._state_cached_surface is not None
        surface.blit(self._state_cached_surface, self.rect)
        self._draw_authorization(surface, font_registry)

        # Draw paperclip prop.
        paperclip = DataFiles.sprites["props"]["diagonal_paperclip"]
        paperclip_rect = paperclip.get_rect()
        paperclip_offset = (16, 8)
        paperclip_rect.left = self.rect.left - paperclip_offset[0]
        paperclip_rect.top = self.rect.top - paperclip_offset[1] + Box.HEIGHT / 2
        surface.blit(paperclip, paperclip_rect)
        
        self._draw_authorization_stamp(surface)


class SortieSelectionMenu(Menu):
    PATH_DASH_LENGTH = 8
    PATH_DASH_WIDTH = 3
    CAMERA_PAN_DURATION = 0.25
    CAMERA_MIN = pygame.Vector2(screen_x(0.5), -305)
    CAMERA_MAX = pygame.Vector2(1822, screen_y(0.5))

    def __init__(self, menu_manager: MenuManager):
        self.menu_manager = menu_manager

        self.mousedown = False

        self.selected_sortie_node: SortieNode | None = None
        self.selection_effect_time = 0
        self.sortie_nodes = [
            SortieNode(sortie_index, sortie_info)
            for sortie_index, sortie_info in enumerate(DataFiles.sortie_data)
        ]

        def start_sortie():
            self.menu_manager.fleet_selection_menu.sortie_index = self.selected_sortie_node.index
            self.menu_manager.current_menu = self.menu_manager.fleet_selection_menu
            self.menu_manager.encounter_menu.current_sortie = self.selected_sortie_node.index
            self.menu_manager.encounter_menu.current_encounter = 0
            self.menu_manager.player_fleet.clear_fleet()
            self.menu_manager.siren_fleet.clear_fleet()

            self.selected_sortie_node.hovered = False
            self.selected_sortie_node = None
            self.sortie_order_card.clear()
        
        self.sortie_order_card = SortieOrderCard(start_sortie)
        self.selected_sortie_info_panel = self.sortie_order_card.rect

        # Camera pan logic for sortie order card.
        self.camera_pan_start = SortieNode.center.copy()
        self.camera_pan_target = SortieNode.center.copy()
        self.camera_pan_timer = 0

        def exit_sortie_selection_menu():
            self.menu_manager.current_menu = self.menu_manager.port_menu
            DataFiles.sfx["waves"].fadeout(3000)

        button_size = 48
        button_sprite = DataFiles.sprites["user_interface"]["prev"]
        button_rect = get_rect(
            width=button_size, height=button_size,
            right=Box.RIGHT_OF_SCREEN, top=Box.TOP_OF_SCREEN
        )
        self.exit_sortie_selection_menu_button = RectangularButton(
            button_rect,
            exit_sortie_selection_menu,
            background_styling={
                "background_color": Color.BLACK,
                "background_img": button_sprite,
                "opacity": 160
            },
            hover_styling={"opacity": 200}
        )

        self.background = Background()

        chapters = sorted({sortie_node.chapter for sortie_node in self.sortie_nodes})

        # Generate the chapter region objects with boundary data.
        self.chapter_regions: list[ChapterRegion] = []
        boundary_data = DataFiles.sortie_selection_details["chapter_boundaries"]
        for chapter in chapters:
            chapter_nodes = [
                sortie_node for sortie_node in self.sortie_nodes
                if sortie_node.chapter == chapter
            ]
            self.chapter_regions.append(
                ChapterRegion(chapter, boundary_data[str(chapter)], chapter_nodes)
            )
        # Generate the chapter name ribbon banners.
        self.chapter_name_ribbons: list[ChapterNameRibbon] = []
        for chapter in chapters:
            chapter_nodes = [
                sortie_node for sortie_node in self.sortie_nodes
                if sortie_node.chapter == chapter
            ]
            if len(chapter_nodes) == 0:
                continue
            self.chapter_name_ribbons.append(ChapterNameRibbon(chapter, chapter_nodes))
        # Generate the chapter progress annotations.
        self.chapter_progress_annotations: list[ChapterProgressAnnotation] = []
        for chapter in chapters:
            chapter_nodes = [
                sortie_node for sortie_node in self.sortie_nodes
                if sortie_node.chapter == chapter
            ]
            if len(chapter_nodes) == 0:
                continue
            self.chapter_progress_annotations.append(
                ChapterProgressAnnotation(chapter, chapter_nodes)
            )
        # Generate the fogs for each chapter region.
        self.fogs = [
            Fog(
                [sortie_node for sortie_node in self.sortie_nodes if sortie_node.chapter == chapter],
                disperse=DataFiles.save_file["chapter_progress"] >= chapter
            )
            for chapter in chapters
        ]

        self.paths = {}
        self._generate_paths()
        self._path_surface_cache = self._create_path_surface_cache()

        self.sea_location_labels = [
            NameRibbon((-105, -390), "western stormbelt", scale=0.75),
            NameRibbon((747, 69), "southreach glaciers", scale=0.75),
            NameRibbon((670, -618), "northreach glaciers", scale=0.75),
            NameRibbon((1658, -587), "eastern stormbelt", scale=0.75),
            NameRibbon((188, -565), "northwind archipelago", scale=0.75),
            NameRibbon((1250, 100), "sunward archipelago", scale=0.75),
            NameRibbon((1045, -790), "cinder isles", scale=0.75),
        ]

    def _generate_paths(self):
        """Generate paths based on pre-saved checkpoints in sortie_selection_details.json."""
        for chapter, checkpoints in DataFiles.sortie_selection_details["checkpoints"].items():
            checkpoints = [pygame.Vector2(checkpoint) for checkpoint in checkpoints]
            step = 1
            record_every = 16
            record_every_counter = record_every
            relpos = checkpoints[1] - checkpoints[0]
            angle = math.atan2(relpos.y, relpos.x)
            pos = checkpoints[0]
            path = [(pos, angle)]
            for checkpoint in checkpoints[1:]:
                to_target = checkpoint - pos

                if math.atan2(to_target.y, to_target.x) == angle:
                    turn_amount = 0
                else:
                    normal = get_vec(1, angle + math.radians(90))
                    dot_product = normal * to_target
                    radius = to_target.length_squared() / (2 * abs(dot_product))
                    turn_amount = step / radius

                to_target_tolerance = 5
                while to_target.length() > to_target_tolerance:
                    pos = pos + get_vec(step, angle)
                    if record_every_counter == 0:
                        path.append((pos, angle))
                        record_every_counter = record_every
                    else:
                        record_every_counter -= 1
                    left_side = get_vec(1, angle - math.radians(90))
                    to_target = checkpoint - pos
                    dot_product = left_side * to_target
                    if dot_product > 0:
                        new_angle = angle - turn_amount
                    else:
                        new_angle = angle + turn_amount
                    angle = new_angle
                    new_left_side = get_vec(1, angle - math.radians(90))
                    new_dot_product = new_left_side * to_target
                    if (
                        (dot_product > 0 and new_dot_product <= 0)
                        or (dot_product <= 0 and new_dot_product > 0)
                    ):
                        angle = math.atan2(to_target.y, to_target.x)
            # Record the final point if not already recorded.
            if record_every_counter < record_every:
                pos = pos + get_vec(record_every_counter, angle)
                path.append((pos, angle))
            self.paths[int(chapter)] = path

    @classmethod
    def _create_path_surface(
        cls,
        path: list[tuple[pygame.Vector2, float]],
    ) -> tuple[pygame.Surface, pygame.Vector2]:
        """Pre-render one chapter path in world space."""
        dash_polygons = []
        for point, angle in path:
            dash_offset = get_vec(cls.PATH_DASH_LENGTH / 2, angle)
            dash_width_offset = get_vec(
                cls.PATH_DASH_WIDTH / 2,
                angle + math.radians(90),
            )
            dash_polygons.append([
                point + dash_offset + dash_width_offset,
                point - dash_offset + dash_width_offset,
                point - dash_offset - dash_width_offset,
                point + dash_offset - dash_width_offset,
            ])

        points = [point for polygon in dash_polygons for point in polygon]
        left = math.floor(min(point.x for point in points)) - 1
        top = math.floor(min(point.y for point in points)) - 1
        right = math.ceil(max(point.x for point in points)) + 1
        bottom = math.ceil(max(point.y for point in points)) + 1
        surface_position = pygame.Vector2(left, top)
        path_surface = pygame.Surface((right - left + 1, bottom - top + 1)).convert()
        path_surface.fill((255, 0, 0))
        for polygon in dash_polygons:
            pygame.draw.polygon(
                path_surface,
                Color.WHITE,
                [point - surface_position for point in polygon],
            )
        path_surface.set_colorkey((255, 0, 0), pygame.RLEACCEL)
        return path_surface, surface_position

    def _create_path_surface_cache(
        self,
    ) -> dict[int, tuple[pygame.Surface, pygame.Vector2]]:
        """Pre-render every generated chapter path."""
        return {
            chapter: self._create_path_surface(path)
            for chapter, path in self.paths.items()
            if path
        }

    @classmethod
    def _clamp_camera_center(cls, center: pygame.Vector2) -> pygame.Vector2:
        """Clamp camera to the camera pan bounds."""
        return pygame.Vector2(
            min(max(cls.CAMERA_MIN.x, center.x), cls.CAMERA_MAX.x),
            min(max(cls.CAMERA_MIN.y, center.y), cls.CAMERA_MAX.y),
        )

    @staticmethod
    def _get_viewport_shift(rect: pygame.Rect, safe_rect: pygame.Rect) -> pygame.Vector2:
        """Get the required camera shift so that rect is within safe_rect."""
        shift = pygame.Vector2()
        if rect.left < safe_rect.left:
            shift.x = safe_rect.left - rect.left
        elif rect.right > safe_rect.right:
            shift.x = safe_rect.right - rect.right
        if rect.top < safe_rect.top:
            shift.y = safe_rect.top - rect.top
        elif rect.bottom > safe_rect.bottom:
            shift.y = safe_rect.bottom - rect.bottom
        return shift

    @staticmethod
    def _get_viewport_overflow(rect: pygame.Rect, safe_rect: pygame.Rect) -> float:
        """Get the total overflow of the rect against the safe_rect, which it should be within."""
        return (
            max(0, safe_rect.left - rect.left)
            + max(0, rect.right - safe_rect.right)
            + max(0, safe_rect.top - rect.top)
            + max(0, rect.bottom - safe_rect.bottom)
        )

    def _get_camera_target_for_card_side(self, node: SortieNode, side: str) -> tuple[pygame.Vector2, int]:
        """Compute the camera target for the card side.
        
        The rect is the combined rect of the sortie node bounding box and the
        sortie order card pinned to its side.
        """
        node_rect = node.get_bounding_rect()
        card_rect = self.sortie_order_card.get_unclamped_rect(node_rect, side)
        combined_rect = node_rect.union(card_rect)
        safe_rect = self.sortie_order_card.get_safe_rect()
        requested_shift = self._get_viewport_shift(combined_rect, safe_rect)

        target = self._clamp_camera_center(SortieNode.center - requested_shift)
        actual_shift = SortieNode.center - target
        shifted_combined_rect = combined_rect.move(round(actual_shift.x), round(actual_shift.y))
        overflow = self._get_viewport_overflow(shifted_combined_rect, safe_rect)
        return target, overflow

    def _select_sortie_node(self, node: SortieNode):
        """Update the selected sortie state with the input sortie node.
        
        Compare the total overflow as a result of needing to pan the camera in either
        the right or left directions, and choose the camera pan which has the least
        overflow (i.e. movement). Then pan the camera in that direction to make space
        for the combined sortie node bounding rect and the sortie order card. Based
        on if the camera needs to pan, the order card can either have its button active
        immediately, or it will wait for the camera pan to finish and then make it active.
        """
        right_target, right_overflow = self._get_camera_target_for_card_side(node, "right")
        if right_overflow == 0:
            side = "right"
            target = right_target
        else:
            left_target, left_overflow = self._get_camera_target_for_card_side(node, "left")
            if left_overflow < right_overflow:
                side = "left"
                target = left_target
            else:
                side = "right"
                target = right_target

        self.selected_sortie_node = node
        self.selected_sortie_node.hovered = False
        self.camera_pan_start = SortieNode.center.copy()
        self.camera_pan_target = target
        camera_pan_tolerance = 0.01
        camera_will_move = not self.camera_pan_start.distance_squared_to(target) < camera_pan_tolerance
        self.camera_pan_timer = self.CAMERA_PAN_DURATION if camera_will_move else 0
        self.sortie_order_card.select(node, side, authorize_immediately=not camera_will_move)

    def _clear_selected_sortie(self):
        """Clear the selected sortie state."""
        if self.selected_sortie_node is not None:
            self.selected_sortie_node.hovered = False
        self.selected_sortie_node = None
        self.sortie_order_card.clear()
        self.camera_pan_timer = 0
        self.camera_pan_start = SortieNode.center.copy()
        self.camera_pan_target = SortieNode.center.copy()

    def _update_camera_pan(self, dt: float):
        """Update the camera pan mechanic for the sortie selection."""
        if self.camera_pan_timer <= 0:
            return

        self.camera_pan_timer = max(0, self.camera_pan_timer - dt)
        progress = 1 - self.camera_pan_timer / self.CAMERA_PAN_DURATION
        eased_progress = 1 - (1 - progress) ** 3
        SortieNode.center = self.camera_pan_start.lerp(self.camera_pan_target, eased_progress)
        self.sortie_order_card.layout()

        if self.camera_pan_timer == 0:
            SortieNode.center = self.camera_pan_target.copy()
            self.sortie_order_card.layout()
            self.sortie_order_card.button.active = self.selected_sortie_node is not None

    def update(self, dt: float, events: list[pygame.Event]):
        """Update the sortie selection menu."""
        self.selection_effect_time += dt
        for event in events:
            if self.sortie_order_card.authorizing:
                continue
            if event.type == pygame.MOUSEBUTTONDOWN:
                # Prevent manual camera pans if the player clicks on any UI that is interactable.
                if self.exit_sortie_selection_menu_button.rect.collidepoint(event.pos):
                    continue
                if self.sortie_order_card.button.rect.collidepoint(event.pos):
                    continue
                if self.selected_sortie_node is not None:
                    continue
                for sortie_node in self.sortie_nodes:
                    if sortie_node.select(event.pos):
                        break
                else:
                    self.mousedown = True
            if event.type == pygame.MOUSEMOTION:
                if self.selected_sortie_node is None:
                    if self.mousedown:
                        # Update manual camera panning.
                        movement = pygame.Vector2(event.rel)
                        SortieNode.center -= movement
                        SortieNode.center = self._clamp_camera_center(SortieNode.center)
                    else:
                        # Allow hovering if the player is not panning the camera.
                        self.exit_sortie_selection_menu_button.hover(event.pos)
                        for sortie_node in self.sortie_nodes:
                            sortie_node.hover(event.pos)
                else:
                    # Update hover state for the sortie order card, which is rendered when
                    # the selected sortie node is not None.
                    self.sortie_order_card.button.hover(event.pos)
            if event.type == pygame.MOUSEBUTTONUP:
                # Prevent mouse interactions when the player is panning camera.
                if self.mousedown:
                    self.mousedown = False
                    continue

                if self.exit_sortie_selection_menu_button.click(event.pos):
                    DataFiles.sfx["click"].play()
                    continue
                if (
                    self.sortie_order_card.button.active
                    and self.sortie_order_card.button.rect.collidepoint(event.pos)
                ):
                    self.sortie_order_card.begin_authorization(event.pos)
                    continue

                if self.selected_sortie_node is None:
                    # Allow selection of sortie nodes when the selected node is None.
                    for sortie_node in self.sortie_nodes:
                        if not sortie_node.select(event.pos):
                            continue
                        self._select_sortie_node(sortie_node)
                        DataFiles.sfx["click"].play()
                        break
                else:
                    # Player can de-select the selected sortie node by clicking outside
                    # of the order card panel.
                    if not self.selected_sortie_info_panel.collidepoint(event.pos):
                        self._clear_selected_sortie()

        self._update_camera_pan(dt)
        self.sortie_order_card.update(dt)
        self.background.update(dt)
        for fog in self.fogs:
            fog.update(dt)

    def draw(self, surface: pygame.Surface, font_registry: dict[str, Font]):
        """Draw the sortie selection menu."""
        self.background.draw(surface)

        for chapter_region in self.chapter_regions:
            chapter_region.draw(surface)

        camera_anchor = anchor()
        for chapter in range(DataFiles.save_file["chapter_progress"] + 1):
            cached_path = self._path_surface_cache.get(chapter)
            if cached_path is None:
                continue
            path_surface, surface_position = cached_path
            surface.blit(path_surface, surface_position + camera_anchor)

        for prop_info in DataFiles.sortie_selection_details["props"]:
            prop = DataFiles.sprites["sortie_selection"][prop_info["prop"]]
            prop_rect = prop.get_rect()
            prop_rect.center = (
                pygame.Vector2(hex_to_pixel(*prop_info["hex"], SortieNode.SIZE))
                + anchor()
            )
            surface.blit(prop, prop_rect)

        for sortie_node in self.sortie_nodes:
            sortie_node.draw_shadow(surface)
        for sortie_node in self.sortie_nodes:
            sortie_node.draw(surface)

        if self.selected_sortie_node is not None:
            self.selected_sortie_node._draw_selection_effect(
                surface,
                self.selection_effect_time,
            )

        for chapter_name_ribbon in self.chapter_name_ribbons:
            chapter_name_ribbon.draw(surface, font_registry)

        for location_ribbon in self.sea_location_labels:
            location_ribbon.draw(surface, font_registry)

        self.background.draw_markings(surface, font_registry)

        for chapter_progress_annotation in self.chapter_progress_annotations:
            chapter_progress_annotation.draw(surface, font_registry)

        # Draw the current objective indicator.
        current_sortie_node = next(
            (
                sortie_node for sortie_node in self.sortie_nodes
                if sortie_node.unlocked and not sortie_node.cleared
            ),
            None
        )
        if current_sortie_node is not None:
            current_objective = DataFiles.sprites["sortie_selection"]["current_objective"]
            current_objective_rect = current_objective.get_rect()
            current_objective_rect.midbottom = current_sortie_node.get_bounding_rect().midtop
            surface.blit(current_objective, current_objective_rect)

        for fog in self.fogs:
            fog.draw(surface)

        self.exit_sortie_selection_menu_button.draw(surface, font_registry)

        if self.selected_sortie_node is not None:
            self.sortie_order_card.draw(surface, font_registry)
