from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from engine.font import Font
    from src.menus.menu_manager import MenuManager

import math
import random
import pygame

from engine.util import get_rect, get_vec, pixel_to_hex, hex_to_pixel, hex_corners, get_cluster_edges, adjacent_hexes
from engine.button import Button

from src.constants import DataFiles, Color, Box, screen_x, screen_y
from src.menus.base_menu import Menu


def anchor():
    return pygame.Vector2(screen_x(1), screen_y(1)) - SortieNode.center


class SortieNode:
    SIZE = Box.WIDTH/2
    center = pygame.Vector2(screen_x(0.5), screen_y(0.5))
    SELECTION_PULSE_DURATION = 2.4
    SELECTION_GLINT_CYCLE = 0.9
    SELECTION_GLINT_LIFETIME = 0.7
    SELECTION_GLINTS_PER_HEX = 4
    SELECTION_GLINT_MAX_LENGTH = 5
    SELECTION_GLINT_MARGIN = 6
    SELECTION_GLINT_DRIFT = 12

    def __init__(self, index, sortie_info):
        self.chapter = sortie_info["chapter"]
        self.index = index
        self.hexes = [tuple(h) for h in sortie_info["coordinates"]]
        self.unlocked = self.index <= DataFiles.save_file["sortie_progress"]
        self.cleared = self.index < DataFiles.save_file["sortie_progress"]
        self.hovered = False

        cluster_edges = get_cluster_edges(self.hexes, self.SIZE)
        self.polygon = [pygame.Vector2(point) for point in cluster_edges]

    def hover(self, mouse_pos):
        mouse_x, mouse_y = mouse_pos
        hx, hy = pixel_to_hex(mouse_x - anchor().x, mouse_y - anchor().y, self.SIZE)
        self.hovered = self.unlocked and (hx, hy) in self.hexes

    def select(self, mouse_pos):
        if not self.unlocked:
            return False

        mouse_x, mouse_y = mouse_pos
        hx, hy = pixel_to_hex(mouse_x - anchor().x, mouse_y - anchor().y, self.SIZE)
        if (hx, hy) not in self.hexes:
            return False
        
        return True

    def draw_shadow(self, surface):
        polygon = [
            point + anchor() + pygame.Vector2(self.SIZE/4,self.SIZE/2)
            for point in self.polygon
        ]
        pygame.draw.polygon(surface, Color.OCEAN_SHADOW, polygon)

    def get_styling(self):
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

    def get_selection_glow_sprite(self):
        if self.cleared:
            return DataFiles.sprites["sortie_selection"]["cleared_node_selection_glow"]
        elif self.unlocked:
            return DataFiles.sprites["sortie_selection"]["uncleared_node_selection_glow"]
        else:
            return DataFiles.sprites["sortie_selection"]["locked_node_selection_glow"]

    def draw(self, surface):
        fill, outline, icon = self.get_styling()
        polygon = [point + anchor() for point in self.polygon]
        if self.hovered:
            pygame.draw.polygon(surface, outline, polygon)
        else:
            pygame.draw.polygon(surface, fill, polygon)
        pygame.draw.polygon(surface, outline, polygon, width=Box.OUTLINE_WIDTH)
        
        for q, r in self.hexes:
            x, y = hex_to_pixel(q, r, self.SIZE)
            icon_rect = icon.get_rect()
            icon_rect.center = pygame.Vector2(x,y) + anchor()
            surface.blit(icon, icon_rect)

    def draw_selection_effect(self, surface, effect_time):
        pulse = (
            math.sin(effect_time * math.tau / self.SELECTION_PULSE_DURATION) + 1
        ) / 2
        glow_base = self.get_selection_glow_sprite().copy()
        glow_base.set_alpha(int(128 + 127*pulse))
        glow = pygame.Surface(glow_base.get_size())
        glow.blit(glow_base)

        node_anchor = anchor()
        glow_instances = []
        for q, r in self.hexes:
            x, y = hex_to_pixel(q, r, self.SIZE)
            hex_center = pygame.Vector2(x, y) + node_anchor
            corners = [
                pygame.Vector2(corner) + node_anchor
                for corner in hex_corners(x, y, self.SIZE)
            ]
            glow_left = int(min(corner.x for corner in corners))
            glow_right = int(max(corner.x for corner in corners))
            glow_rect = pygame.Rect(
                glow_left,
                0,
                glow_right - glow_left + 1,
                glow.get_height(),
            )
            glow_rect.bottom = hex_center.y
            hex_glow = pygame.transform.smoothscale(glow, glow_rect.size)
            glow_instances.append((hex_glow, glow_rect, hex_center))

        glow_bounds = glow_instances[0][1].unionall(
            [glow_rect for _, glow_rect, _ in glow_instances[1:]]
        )
        combined_glow = pygame.Surface(glow_bounds.size)
        for hex_glow, glow_rect, _ in glow_instances:
            local_rect = glow_rect.move(-glow_bounds.left, -glow_bounds.top)
            combined_glow.blit(
                hex_glow,
                local_rect,
                special_flags=pygame.BLEND_RGB_MAX,
            )
        surface.blit(
            combined_glow,
            glow_bounds,
            special_flags=pygame.BLEND_RGB_ADD,
        )

        _, outline, icon = self.get_styling()
        polygon = [point + anchor() for point in self.polygon]
        pygame.draw.polygon(surface, outline, polygon)
        
        for q, r in self.hexes:
            x, y = hex_to_pixel(q, r, self.SIZE)
            icon_rect = icon.get_rect()
            icon_rect.center = pygame.Vector2(x,y) + anchor()
            surface.blit(icon, icon_rect)

        glint_count = len(glow_instances) * self.SELECTION_GLINTS_PER_HEX
        for hex_index, (_, _, hex_center) in enumerate(glow_instances):
            for glint_index in range(self.SELECTION_GLINTS_PER_HEX):
                particle_index = glint_index*len(glow_instances) + hex_index
                glint_time = (
                    effect_time
                    + particle_index*self.SELECTION_GLINT_CYCLE/glint_count
                )
                glint_age = glint_time % self.SELECTION_GLINT_CYCLE
                if glint_age >= self.SELECTION_GLINT_LIFETIME:
                    continue

                cycle_index = math.floor(
                    glint_time / self.SELECTION_GLINT_CYCLE
                )
                glint_progress = glint_age / self.SELECTION_GLINT_LIFETIME
                glint_strength = (1 - glint_progress)**1.5
                half_spawn_width = (
                    math.sqrt(3)/2*self.SIZE - self.SELECTION_GLINT_MARGIN
                )
                spawn_x = (
                    (cycle_index*29 + particle_index*17) % (2*half_spawn_width)
                    - half_spawn_width
                )
                half_spawn_height = (
                    self.SIZE
                    - abs(spawn_x)/math.sqrt(3)
                    - self.SELECTION_GLINT_MARGIN
                )
                spawn_y = (
                    (cycle_index*19 + particle_index*31) % (2*half_spawn_height)
                    - half_spawn_height
                )
                spawn_center = hex_center + pygame.Vector2(spawn_x, spawn_y)
                center = spawn_center - pygame.Vector2(
                    0,
                    self.SELECTION_GLINT_DRIFT*glint_progress,
                )
                glint_length = 1 + round(
                    (self.SELECTION_GLINT_MAX_LENGTH - 1)*glint_strength
                )
                glint_color = tuple(
                    round(channel*glint_strength)
                    for channel in outline
                )
                glint_surface = pygame.Surface(
                    (
                        2*self.SELECTION_GLINT_MAX_LENGTH + 1,
                        2*self.SELECTION_GLINT_MAX_LENGTH + 1,
                    )
                )
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

    def __init__(self, chapter, boundary_hexes, sortie_nodes):
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

    def get_state(self):
        if all(node.cleared for node in self.sortie_nodes):
            return "cleared"
        if any(node.unlocked for node in self.sortie_nodes):
            return "uncleared"
        return "locked"

    def create_styled_surface(self, state):
        colors = {
            "cleared": (Color.CLEARED_ZONE_FILL, Color.CLEARED_ZONE_OUTLINE),
            "uncleared": (Color.UNCLEARED_ZONE_FILL, Color.UNCLEARED_ZONE_OUTLINE),
            "locked": (Color.LOCKED_ZONE_FILL, Color.LOCKED_ZONE_OUTLINE),
        }
        fill_color, outline_color = colors[state]

        styled_surface = pygame.Surface(self.size, pygame.SRCALPHA)
        pygame.draw.polygon(
            styled_surface,
            (*fill_color, self.FILL_ALPHA),
            self.polygon,
        )

        hatch_surface = pygame.Surface(self.size, pygame.SRCALPHA)
        width, height = self.size
        for x in range(-height, width + height, self.HATCH_SPACING):
            pygame.draw.line(
                hatch_surface,
                (*outline_color, self.HATCH_ALPHA),
                (x, height),
                (x + height, 0),
                width=Box.OUTLINE_WIDTH
            )
        region_mask = pygame.Surface(self.size, pygame.SRCALPHA)
        pygame.draw.polygon(region_mask, (255, 255, 255, 255), self.polygon)
        hatch_surface.blit(region_mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        styled_surface.blit(hatch_surface, (0, 0))

        pygame.draw.polygon(
            styled_surface,
            (*outline_color, self.OUTLINE_ALPHA),
            self.polygon,
            width=self.OUTLINE_WIDTH,
        )
        return styled_surface

    def draw(self, surface):
        state = self.get_state()
        if state not in self.styled_surfaces:
            self.styled_surfaces[state] = self.create_styled_surface(state)
        surface.blit(self.styled_surfaces[state], self.position + anchor())


class Fog:
    def __init__(self, sortie_nodes, disperse=False):
        self.centroids = []
        for sortie_node in sortie_nodes:
            for q, r in sortie_node.hexes:
                x, y = hex_to_pixel(q, r, sortie_node.SIZE)
                self.centroids.append(pygame.Vector2(x, y))
        self.cloud_indices = [random.randint(4, 9) for _ in self.centroids]
        self.cloud_sprites = {
            cloud_index: DataFiles.sprites["background"][f"cloud{cloud_index}"].copy()
            for cloud_index in [4,5,6,7,8,9]
        }
        self.cloud_shadow_sprites = {
            cloud_index: DataFiles.sprites["background"][f"cloud_shadow{cloud_index}"]
            for cloud_index in [4,5,6,7,8,9]
        }
        self.disperse = disperse
        self.disperse_timer = 1

        self.cloud_timers = [
            math.radians(random.randint(0, 359))
            for _ in self.centroids
        ]
    
    def update(self, dt):
        if self.disperse_timer <= 0:
            return
        
        self.cloud_timers = [
            (cloud_timer + dt)%math.radians(360)
            for cloud_timer in self.cloud_timers
        ]
        if self.disperse:
            if self.disperse_timer == 1:
                wind_sfx = DataFiles.sfx["wind"]
                wind_sfx.play()
                wind_sfx.fadeout(3000)
            self.disperse_timer = max(0, self.disperse_timer - 1/3*dt)

    def draw(self, surface):
        if self.disperse_timer <= 0:
            return
        
        if self.disperse_timer < 1:
            cloud_alpha = int(255*self.disperse_timer)
            for cloud_sprite in self.cloud_sprites.values():
                cloud_sprite.set_alpha(cloud_alpha)

        for centroid, cloud_index, cloud_timer in zip(self.centroids, self.cloud_indices, self.cloud_timers):
            center = (
                centroid
                + anchor()
                + pygame.Vector2(16*math.sin(cloud_timer), 4*math.sin(2*cloud_timer))
            )

            if self.disperse_timer >= 1:
                cloud_shadow_sprite = self.cloud_shadow_sprites[cloud_index]
                cloud_shadow_rect = cloud_shadow_sprite.get_rect()
                cloud_shadow_rect.center = center + pygame.Vector2(8, 8)
                surface.blit(cloud_shadow_sprite, cloud_shadow_rect, special_flags=pygame.BLEND_RGB_SUB)

            cloud_sprite = self.cloud_sprites[cloud_index]
            cloud_rect = cloud_sprite.get_rect()
            cloud_rect.center = center
            surface.blit(cloud_sprite, cloud_rect)

class SortieProp:
    def __init__(self, sprite_key, position):
        self.sprite_key = sprite_key
        self.position = pygame.Vector2(position)
        self.sprite = DataFiles.sprites["sortie_selection"][sprite_key]

    def get_rect(self):
        rect = self.sprite.get_rect()
        rect.center = self.position + anchor()
        return rect

    def draw(self, surface):
        surface.blit(self.sprite, self.get_rect())


class NameRibbon:
    PADDING_X = 24
    
    def __init__(self, position, name, scale=1.0):
        self.text = name
        self.position = pygame.Vector2(position)
        self.scale = scale
    
    def get_width(self, font_registry):
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
        middle_width = max(middle.get_width(), text_width + 2 * self.PADDING_X)
        return left.get_width() + middle_width + right.get_width()

    def get_rect(self, font_registry):
        width = self.get_width(font_registry)
        height = DataFiles.sprites["sortie_selection"]["name_middle"].get_height() * self.scale
        return get_rect(width=width, height=height, center=self.position + anchor())

    def draw(self, surface, font_registry):
        left = pygame.transform.scale_by(
            DataFiles.sprites["sortie_selection"]["name_left"], self.scale
        )
        right = pygame.transform.scale_by(
            DataFiles.sprites["sortie_selection"]["name_right"], self.scale
        )
        middle = pygame.transform.scale_by(
            DataFiles.sprites["sortie_selection"]["name_middle"], self.scale
        )
        rect = self.get_rect(font_registry)

        left_rect = left.get_rect(topleft=rect.topleft)
        surface.blit(left, left_rect)

        middle_rect = middle.get_rect()
        middle_rect.left = left_rect.right
        middle_rect.top = rect.top
        middle_right = rect.right - right.get_width()
        while middle_rect.left < middle_right:
            source_width = min(middle.get_width(), middle_right - middle_rect.left)
            source_rect = pygame.Rect(0, 0, source_width, middle.get_height())
            surface.blit(middle, middle_rect, source_rect)
            middle_rect.left += source_width

        right_rect = right.get_rect(topright=rect.topright)
        surface.blit(right, right_rect)

        font_registry["handwritten"].render(surface, self.text, rect.center, Color.BLACK, self.scale, style="center")

class ChapterNameRibbon:
    Y_OFFSET_IN_HEXES = 4
    CHAPTER_NAMES = [
        "training exercise",
        "patrol route",
        "crimson reef",
        "stormy sea",
        "mirror sea"
    ]

    def __init__(self, chapter, sortie_nodes):
        if chapter < len(self.CHAPTER_NAMES):
            text = self.CHAPTER_NAMES[chapter]
        else:
            text = f"chapter {chapter}"
        position = self.get_position(sortie_nodes)

        self.ribbon = NameRibbon(position, text)

    def get_position(self, sortie_nodes):
        hex_positions = []
        for sortie_node in sortie_nodes:
            for q, r in sortie_node.hexes:
                hex_positions.append(pygame.Vector2(hex_to_pixel(q, r, SortieNode.SIZE)))

        left = min(position.x for position in hex_positions)
        right = max(position.x for position in hex_positions)
        bottom = max(position.y for position in hex_positions)
        return pygame.Vector2(
            (left + right) / 2,
            bottom + self.Y_OFFSET_IN_HEXES*SortieNode.SIZE,
        )

    def draw(self, surface, font_registry):
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

    def __init__(self, chapter, sortie_nodes, text_shift=16):
        self.chapter = chapter
        self.sortie_nodes = sortie_nodes

        hex_centers = [
            pygame.Vector2(hex_to_pixel(*hex_tile, SortieNode.SIZE))
            for sortie_node in sortie_nodes
            for hex_tile in sortie_node.hexes
        ]
        leftmost_hex = min(hex_centers, key=lambda point: point.x)
        rightmost_hex = max(hex_centers, key=lambda point: point.x)

        width_extension = max(
            0,
            (self.MIN_WIDTH - (rightmost_hex.x - leftmost_hex.x))/2,
        )
        start_point = leftmost_hex + pygame.Vector2(-width_extension, 64)
        end_point = rightmost_hex + pygame.Vector2(width_extension, 64)
        mid_point = start_point.lerp(end_point, 0.5) + pygame.Vector2(0, 32)

        self.curve_points = self.create_circular_curve(
            start_point,
            mid_point,
            end_point,
        )
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
            + text_normal*self.TEXT_OFFSET
            + text_direction*text_shift
        )
        self.text_angle = math.degrees(math.atan2(
            -text_direction.y,
            text_direction.x,
        ))

    @classmethod
    def create_circular_curve(cls, start_point, mid_point, end_point):
        start_x, start_y = start_point
        mid_x, mid_y = mid_point
        end_x, end_y = end_point
        determinant = 2*(
            start_x*(mid_y - end_y)
            + mid_x*(end_y - start_y)
            + end_x*(start_y - mid_y)
        )
        if abs(determinant) < 0.001:
            return [start_point, mid_point, end_point]

        start_length_squared = start_point.length_squared()
        mid_length_squared = mid_point.length_squared()
        end_length_squared = end_point.length_squared()
        center = pygame.Vector2(
            (
                start_length_squared*(mid_y - end_y)
                + mid_length_squared*(end_y - start_y)
                + end_length_squared*(start_y - mid_y)
            ) / determinant,
            (
                start_length_squared*(end_x - mid_x)
                + mid_length_squared*(start_x - end_x)
                + end_length_squared*(mid_x - start_x)
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

        arc_length = radius*abs(angle_span)
        num_segments = max(2, math.ceil(arc_length / cls.CURVE_SAMPLE_SPACING))
        return [
            center + get_vec(
                radius,
                start_angle + angle_span*segment/num_segments,
            )
            for segment in range(num_segments + 1)
        ]

    def get_text(self):
        if all(node.cleared for node in self.sortie_nodes):
            return "secured waters"

        current_sortie = DataFiles.save_file["sortie_progress"]
        if any(node.index == current_sortie for node in self.sortie_nodes):
            return "operation plan"
        return None

    def get_curve_points(self):
        return [point + anchor() for point in self.curve_points]

    def draw_text(self, surface, font_registry, text):
        font = font_registry["handwritten"]
        text_size = (
            math.ceil(font.get_width(text, self.TEXT_SCALE, 0)),
            math.ceil(font.get_height(text, self.TEXT_SCALE, 0)),
        )
        text_surface = pygame.Surface(
            (
                text_size[0] + 2*self.TEXT_SURFACE_PADDING,
                text_size[1] + 2*self.TEXT_SURFACE_PADDING,
            ),
            pygame.SRCALPHA,
        )
        font.render(
            text_surface,
            text,
            text_surface.get_rect().center,
            Color.WHITE,
            self.TEXT_SCALE,
            style="center",
        )
        rotated_text = pygame.transform.rotate(text_surface, self.text_angle)
        rotated_text_rect = rotated_text.get_rect(
            center=self.text_position + anchor()
        )
        surface.blit(rotated_text, rotated_text_rect)

    @classmethod
    def draw_dashed_curve(cls, surface, points):
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
                next_position = position + direction*step
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

                if distance_until_toggle <= 0.001:
                    drawing_dash = not drawing_dash
                    distance_until_toggle = (
                        cls.DASH_LENGTH if drawing_dash else cls.DASH_GAP
                    )

    def draw(self, surface, font_registry):
        text = self.get_text()
        if text is None:
            return

        curve_points = self.get_curve_points()
        self.draw_dashed_curve(surface, curve_points)

        arrow_direction = (curve_points[-1] - curve_points[-2]).normalize()
        backwards_angle = math.atan2(-arrow_direction.y, -arrow_direction.x)
        for angle_offset in (-self.ARROWHEAD_ANGLE, self.ARROWHEAD_ANGLE):
            arrow_side = curve_points[-1] + get_vec(
                self.ARROWHEAD_LENGTH,
                backwards_angle + angle_offset,
            )
            pygame.draw.line(
                surface,
                Color.WHITE,
                curve_points[-1],
                arrow_side,
                width=self.LINE_WIDTH,
            )

        self.draw_text(surface, font_registry, text)


class Background:
    def __init__(self):
        num_waves = 36
        self.wave_indices = random.choices(list(range(DataFiles.sprites["sortie_selection"]["num_wave_sprites"])), k=num_waves)
        wave_height = DataFiles.sprites["sortie_selection"]["wave"].get_height() / 2
        self.wave_ys = [wave_height * (i - num_waves + 8) for i in range(num_waves)]
        self.wave_timers = [math.radians(random.randint(0, 359)) for _ in range(num_waves)]

    def update(self, dt):
        self.wave_timers = [(wave_timer + dt) % math.radians(360) for wave_timer in self.wave_timers]

    def draw(self, surface):
        num_wave_reps = 10
        for wave_index, wave_y, wave_timer in  zip(self.wave_indices, self.wave_ys, self.wave_timers):
            wave_sprite = DataFiles.sprites["sortie_selection"][f"wave{wave_index}"]
            wave_rect = wave_sprite.get_rect()
            wave_rect.top = wave_y + 4 * math.sin(2 * wave_timer) + anchor().y
            if wave_rect.bottom < 0 or wave_rect.top > screen_y(1):
                continue
            centerx = 32 * math.sin(wave_timer) + anchor().x - screen_x(0.5)
            for i in range(num_wave_reps):
                wave_rect.centerx = centerx + wave_rect.width * i
                if wave_rect.right < 0 or wave_rect.left > screen_x(1):
                    continue
                surface.blit(wave_sprite, wave_rect)

    def draw_markings(self, surface, font_registry):
        compass_rose = DataFiles.sprites["sortie_selection"]["compass_rose"]
        compass_rose_rect = compass_rose.get_rect()
        compass_rose_rect.bottom = Box.BOTTOM_OF_SCREEN
        compass_rose_rect.left = Box.LEFT_OF_SCREEN
        surface.blit(compass_rose, compass_rose_rect)

        map_scale = DataFiles.sprites["sortie_selection"]["map_scale"]
        map_scale_rect = map_scale.get_rect()
        map_scale_rect.bottom = Box.BOTTOM_OF_SCREEN
        map_scale_rect.left = compass_rose_rect.right + Box.PADDING
        surface.blit(map_scale, map_scale_rect)

        for dist, x in zip([0, 50, 100, 200], [
            map_scale_rect.left,
            map_scale_rect.left + map_scale_rect.width * 0.25,
            map_scale_rect.left + map_scale_rect.width * 0.5,
            map_scale_rect.left + map_scale_rect.width
        ]):
            font_registry["big_pixel"].render(
                surface,
                str(dist),
                pygame.Vector2(x, map_scale_rect.top - 10),
                Color.WHITE,
                1,
                style="center",
                outline_color=Color.BLACK
            )
        font_registry["big_pixel"].render(
            surface,
            "kilometers",
            pygame.Vector2(map_scale_rect.right + Box.PADDING, map_scale_rect.centery),
            Color.WHITE,
            1,
            style="centerleft",
            outline_color=Color.BLACK
        )


class SortieOrderCard:
    WIDTH = 3*(Box.WIDTH + Box.PADDING) + Box.PADDING + 2*Box.PADDING
    HEIGHT = 5*Box.HEIGHT + 4*Box.PADDING
    HEADER_BOTTOM = 96
    REWARD_TOP = 116
    AUTHORIZATION_HEIGHT = 72
    AUTHORIZATION_DURATION = 1
    AUTHORIZATION_IMPACT_TIME = 0.15
    AUTHORIZATION_LIFT_TIME = 0.30
    AUTHORIZATION_DISAPPEAR_TIME = 0.5
    CHART_GAP = 2 * Box.PADDING

    def __init__(self, authorize_sortie):
        self.rect = get_rect(width=self.WIDTH, height=self.HEIGHT, left=0, top=0)
        self.page_rect = self.rect.inflate(-2*Box.PADDING, -2*Box.PADDING - Box.HEIGHT/2)
        self.side = "right"
        self.node = None
        self.authorize_sortie = authorize_sortie
        self.authorizing = False
        self.authorization_timer = 0
        self.authorization_impact_played = False
        self.authorization_pos = pygame.Vector2()

        self.authorization_anchors = {
            "muted": DataFiles.recolor_sprite("user_interface", "start_sortie", Color.DOSSIER_RULE),
            "red":DataFiles.recolor_sprite("user_interface", "start_sortie", Color.START_SORTIE_BUTTON),
        }
        self.authorization_stamp = DataFiles.sprites["props"]["stamp"]

        self.button = Button(
            get_rect(
                width=self.WIDTH - 4*Box.PADDING,
                height=self.AUTHORIZATION_HEIGHT,
                left=0,
                top=0,
            ),
            self.begin_authorization,
            active=False,
        )

    @staticmethod
    def get_safe_rect():
        exit_button_clearance = 48 + Box.PADDING
        return pygame.Rect(
            Box.LEFT_OF_SCREEN,
            Box.TOP_OF_SCREEN,
            Box.RIGHT_OF_SCREEN - exit_button_clearance - Box.LEFT_OF_SCREEN,
            Box.BOTTOM_OF_SCREEN - Box.TOP_OF_SCREEN,
        )

    def get_unclamped_rect(self, node_rect, side=None):
        side = side or self.side
        rect = self.rect.copy()
        rect.centery = node_rect.centery
        if side == "right":
            rect.left = node_rect.right + self.CHART_GAP
        else:
            rect.right = node_rect.left - self.CHART_GAP
        return rect

    def layout(self):
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

    def select(self, node, side, authorize_immediately):
        self.node = node
        self.side = side
        self.authorizing = False
        self.authorization_timer = 0
        self.authorization_impact_played = False
        self.authorization_pos = pygame.Vector2(self.button.rect.center)
        self.layout()
        self.button.active = authorize_immediately

    def clear(self):
        self.node = None
        self.button.active = False
        self.button.hovered = False
        self.authorizing = False
        self.authorization_timer = 0
        self.authorization_impact_played = False
        self.authorization_pos = pygame.Vector2()

    def begin_authorization(self, click_pos=None):
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

    def update(self, dt):
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

    def get_status(self):
        if self.node.cleared:
            return "charted territory", Color.CLEARED_ZONE_FILL
        return "uncharted waters", Color.UNCLEARED_ZONE_FILL

    def draw_paper(self, surface):
        dossier_rect = self.rect.inflate(0, -Box.HEIGHT/2)
        dossier_rect.bottomleft = self.rect.bottomleft
        pygame.draw.rect(surface, Color.DOSSIER, dossier_rect)
        dossier_tab = [
            pygame.Vector2(self.rect.topleft),
            pygame.Vector2(self.rect.topleft) + pygame.Vector2(Box.WIDTH - Box.PADDING, 0),
            pygame.Vector2(self.rect.topleft) + pygame.Vector2(Box.WIDTH + Box.PADDING, Box.HEIGHT/2),
            pygame.Vector2(self.rect.topleft) + pygame.Vector2(0, Box.HEIGHT/2),
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
                Box.get_rotated_rect_polygon(self.page_rect, angle, offset),
            )
        pygame.draw.rect(surface, Color.DOSSIER_PAGE, self.page_rect)

    def draw_header(self, surface, font_registry):
        font = font_registry["big_pixel"]
        small_font = font_registry["pixel"]
        left = self.page_rect.left + Box.PADDING
        right = self.page_rect.right - Box.PADDING
        top = self.page_rect.top + Box.PADDING
        status, status_color = self.get_status()

        small_font.render(surface, "azur lane naval command", (left, top), Color.DOSSIER_RULE, 1)
        form_text = f"form so-{self.node.index + 1:03d}"
        form_left = right - small_font.get_width(form_text, 1, 0)
        small_font.render(surface, form_text, (form_left, top), Color.DOSSIER_RULE, 1)
        small_font.render(surface, "operation order", (left, top + 12), Color.DOSSIER_INK, 1)
        font.render(surface, f"sector {self.node.index + 1:02d}", (left, top + 27), Color.DOSSIER_INK, 2)

        status_width = font.get_width(status, 1, 0) + 2*Box.PADDING
        status_rect = get_rect(
            width=status_width,
            height=24,
            left=left,
            top=top + 52,
        )
        pygame.draw.rect(surface, status_color, status_rect, width=Box.OUTLINE_WIDTH)
        pygame.draw.rect(surface, status_color, status_rect.inflate(-4, -4), width=1)
        font.render(surface, status, status_rect.center, status_color, 1, style="center")

        pygame.draw.line(
            surface,
            Color.DOSSIER_RULE,
            (left, self.page_rect.top + self.HEADER_BOTTOM),
            (right, self.page_rect.top + self.HEADER_BOTTOM),
        )

    def draw_rewards(self, surface, font_registry):
        font = font_registry["big_pixel"]
        left = self.page_rect.left + Box.PADDING
        heading = "allotment issued" if self.node.cleared else "first-clear allotment"
        font.render(surface, heading, (left, self.page_rect.top + 102), Color.DOSSIER_RULE, 1)

        rewards = DataFiles.sortie_data[self.node.index]["rewards"]
        if not rewards:
            reward_area = pygame.Rect(left, self.page_rect.top + self.REWARD_TOP, self.page_rect.width - 2*Box.PADDING, Box.HEIGHT)
            font.render(surface, "no allotment on file", reward_area.center, Color.DOSSIER_RULE, 1, style="center")
            return

        for i, (reward, count) in enumerate(rewards.items()):
            rect = get_rect(
                width=Box.WIDTH,
                height=Box.HEIGHT,
                left=left + i*(Box.WIDTH + Box.PADDING),
                top=self.page_rect.top + self.REWARD_TOP,
            )
            pygame.draw.rect(surface, Color.DOSSIER_CARD_SHADOW, rect.move(2, 2))
            pygame.draw.rect(surface, Color.DOSSIER_CARD, rect)
            surface.blit(DataFiles.get_entity_sprite(reward), rect)

            quantity_rect = pygame.Rect(rect.left, rect.bottom - 14, rect.width, 14)
            pygame.draw.rect(surface, Color.DOSSIER_CARD, quantity_rect)
            pygame.draw.line(surface, Color.DOSSIER_RULE, quantity_rect.topleft, quantity_rect.topright)
            font.render(surface, f"qty {count:02d}", quantity_rect.center, Color.DOSSIER_INK, 1, style="center")
            pygame.draw.rect(surface, Color.DOSSIER_INK, rect, width=1)

        if self.node.cleared:
            obtained_stamp = DataFiles.sprites["sortie_selection"]["obtained_stamp"].copy()
            obtained_stamp.set_alpha(128)
            obtained_stamp_rect = obtained_stamp.get_rect()
            obtained_stamp_rect.centerx = self.page_rect.centerx
            obtained_stamp_rect.top = self.page_rect.top + self.REWARD_TOP - Box.HEIGHT/4
            surface.blit(obtained_stamp, obtained_stamp_rect)

    @staticmethod
    def draw_dashed_rect(surface, color, rect, dash_length=8, gap_length=4, width=2):
        right = rect.right - 1
        bottom = rect.bottom - 1
        dash_step = dash_length + gap_length
        for x in range(rect.left, right + 1, dash_step):
            dash_right = min(x + dash_length, right)
            pygame.draw.line(surface, color, (x, rect.top), (dash_right, rect.top), width)
            pygame.draw.line(surface, color, (x, bottom), (dash_right, bottom), width)
        for y in range(rect.top, bottom + 1, dash_step):
            dash_bottom = min(y + dash_length, bottom)
            pygame.draw.line(surface, color, (rect.left, y), (rect.left, dash_bottom), width)
            pygame.draw.line(surface, color, (right, y), (right, dash_bottom), width)

    def draw_authorization(self, surface, font_registry):
        field_rect = self.button.rect
        label_y = field_rect.top - 16
        rule_y = field_rect.top - 24
        content_left = self.page_rect.left + Box.PADDING
        content_right = self.page_rect.right - Box.PADDING
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

        hovered = self.button.active and self.button.hovered
        imprint_visible = (
            self.authorizing
            and self.authorization_timer >= self.AUTHORIZATION_IMPACT_TIME
        )
        action_highlighted = hovered or self.authorizing
        ink_color = Color.START_SORTIE_BUTTON if action_highlighted else Color.DOSSIER_RULE

        if hovered:
            pygame.draw.rect(surface, Color.DOSSIER_CARD, field_rect)
        self.draw_dashed_rect(surface, ink_color, field_rect, width=Box.OUTLINE_WIDTH)

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

    def draw_authorization_stamp(self, surface):
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
        stamp_rect.bottom = round(stamp_pos.y + Box.HEIGHT/2)
        surface.blit(self.authorization_stamp, stamp_rect)

    def draw_props(self, surface):
        paperclip = DataFiles.sprites["props"]["diagonal_paperclip"]
        paperclip_rect = paperclip.get_rect()
        paperclip_rect.left = self.rect.left - 16
        paperclip_rect.top = self.rect.top - 8 + Box.HEIGHT/2
        surface.blit(paperclip, paperclip_rect)

    def draw(self, surface, font_registry):
        if self.node is None:
            return

        self.layout()
        self.draw_paper(surface)
        self.draw_header(surface, font_registry)
        self.draw_rewards(surface, font_registry)
        self.draw_authorization(surface, font_registry)
        self.button.draw(surface, font_registry)
        self.draw_props(surface)
        self.draw_authorization_stamp(surface)


class SortieSelectionMenu(Menu):
    PATH_DASH_LENGTH = 8
    PATH_DASH_WIDTH = 3
    CAMERA_PAN_DURATION = 0.25
    CAMERA_MIN = pygame.Vector2(screen_x(0.5), -305)
    CAMERA_MAX = pygame.Vector2(1822, screen_y(0.5))

    def __init__(self, menu_manager: MenuManager):
        self.menu_manager = menu_manager

        self.mousedown = False

        self.selected_sortie_node = None
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
        self.camera_pan_start = SortieNode.center.copy()
        self.camera_pan_target = SortieNode.center.copy()
        self.camera_pan_timer = 0

        def exit_sortie_selection_menu():
            self.menu_manager.current_menu = self.menu_manager.port_menu
            DataFiles.sfx["waves"].fadeout(3000)

        button_sprite = DataFiles.sprites["user_interface"]["prev"]
        button_rect = get_rect(width=48,height=48,right=Box.RIGHT_OF_SCREEN,top=Box.TOP_OF_SCREEN)
        self.exit_sortie_selection_menu_button = Button(
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
        self.chapter_regions = self.create_chapter_regions()
        self.chapter_name_ribbons = self.create_chapter_name_ribbons()
        self.chapter_progress_annotations = self.create_chapter_progress_annotations()

        self.fogs = [
            Fog(
                [sortie_node for sortie_node in self.sortie_nodes if sortie_node.chapter == chapter],
                disperse=DataFiles.save_file["chapter_progress"] >= chapter
            )
            for chapter in range(4)
        ]

        self.paths = {}
        self.generate_paths()

        self.sea_location_labels = [
            NameRibbon((-105, -390), "stormy", scale=0.75),
            NameRibbon((747, 69), "glaciers", scale=0.75),
            NameRibbon((670, -618), "glaciers", scale=0.75),
            NameRibbon((1658, -587), "stormy", scale=0.75),
            NameRibbon((188, -565), "northwind archipelago", scale=0.75),
            NameRibbon((1250, 100), "sunward archipelago", scale=0.75),
            NameRibbon((1045, -790), "cinder isles", scale=0.75),
        ]

    def generate_paths(self):
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

                while to_target.length() > 5:
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
            if record_every_counter < 10:
                pos = pos + get_vec(record_every_counter, angle)
                path.append((pos, angle))
            self.paths[int(chapter)] = path

    def get_chapters(self):
        return sorted({sortie_node.chapter for sortie_node in self.sortie_nodes})

    def create_chapter_regions(self):
        regions = []
        boundary_data = DataFiles.sortie_selection_details["chapter_boundaries"]
        for chapter in self.get_chapters():
            chapter_nodes = [
                sortie_node for sortie_node in self.sortie_nodes
                if sortie_node.chapter == chapter
            ]
            regions.append(
                ChapterRegion(chapter, boundary_data[str(chapter)], chapter_nodes)
            )
        return regions

    def create_chapter_name_ribbons(self):
        ribbons = []
        for chapter in self.get_chapters():
            chapter_nodes = [
                sortie_node for sortie_node in self.sortie_nodes
                if sortie_node.chapter == chapter
            ]
            if len(chapter_nodes) == 0:
                continue
            ribbons.append(ChapterNameRibbon(chapter, chapter_nodes))
        return ribbons

    def create_chapter_progress_annotations(self):
        annotations = []
        for chapter in self.get_chapters():
            chapter_nodes = [
                sortie_node for sortie_node in self.sortie_nodes
                if sortie_node.chapter == chapter
            ]
            if len(chapter_nodes) == 0:
                continue
            annotations.append(
                ChapterProgressAnnotation(chapter, chapter_nodes)
            )
        return annotations

    @classmethod
    def clamp_camera_center(cls, center):
        return pygame.Vector2(
            min(max(cls.CAMERA_MIN.x, center.x), cls.CAMERA_MAX.x),
            min(max(cls.CAMERA_MIN.y, center.y), cls.CAMERA_MAX.y),
        )

    @staticmethod
    def get_viewport_shift(rect, safe_rect):
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
    def get_viewport_overflow(rect, safe_rect):
        return (
            max(0, safe_rect.left - rect.left)
            + max(0, rect.right - safe_rect.right)
            + max(0, safe_rect.top - rect.top)
            + max(0, rect.bottom - safe_rect.bottom)
        )

    def get_camera_target_for_card_side(self, node, side):
        node_rect = node.get_bounding_rect()
        card_rect = self.sortie_order_card.get_unclamped_rect(node_rect, side)
        combined_rect = node_rect.union(card_rect)
        safe_rect = self.sortie_order_card.get_safe_rect()
        requested_shift = self.get_viewport_shift(combined_rect, safe_rect)

        target = self.clamp_camera_center(SortieNode.center - requested_shift)
        actual_shift = SortieNode.center - target
        shifted_combined_rect = combined_rect.move(round(actual_shift.x), round(actual_shift.y))
        overflow = self.get_viewport_overflow(shifted_combined_rect, safe_rect)
        return target, overflow

    def select_sortie_node(self, node):
        right_target, right_overflow = self.get_camera_target_for_card_side(node, "right")
        if right_overflow == 0:
            side = "right"
            target = right_target
        else:
            left_target, left_overflow = self.get_camera_target_for_card_side(node, "left")
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
        camera_will_move = not self.camera_pan_start.distance_squared_to(target) < 0.01
        self.camera_pan_timer = self.CAMERA_PAN_DURATION if camera_will_move else 0
        self.sortie_order_card.select(node, side, authorize_immediately=not camera_will_move)

    def clear_selected_sortie(self):
        if self.selected_sortie_node is not None:
            self.selected_sortie_node.hovered = False
        self.selected_sortie_node = None
        self.sortie_order_card.clear()
        self.camera_pan_timer = 0
        self.camera_pan_start = SortieNode.center.copy()
        self.camera_pan_target = SortieNode.center.copy()

    def update_camera_pan(self, dt):
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
        self.selection_effect_time += dt
        for event in events:
            if self.sortie_order_card.authorizing:
                continue
            if event.type == pygame.MOUSEBUTTONDOWN:
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
                self.sortie_order_card.button.hover(event.pos)

                if self.selected_sortie_node is None:
                    self.exit_sortie_selection_menu_button.hover(event.pos)
                    if self.mousedown:
                        movement = pygame.Vector2(event.rel)
                        SortieNode.center -= movement
                        SortieNode.center = self.clamp_camera_center(SortieNode.center)
            if event.type == pygame.MOUSEBUTTONUP:
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
                    for sortie_node in self.sortie_nodes:
                        if not sortie_node.select(event.pos):
                            continue
                        self.select_sortie_node(sortie_node)
                        DataFiles.sfx["click"].play()
                        break
                else:
                    if not self.selected_sortie_info_panel.collidepoint(event.pos):
                        self.clear_selected_sortie()

            if event.type == pygame.MOUSEMOTION:
                if self.selected_sortie_node is None:
                    for sortie_node in self.sortie_nodes:
                        sortie_node.hover(event.pos)

        self.update_camera_pan(dt)
        self.sortie_order_card.update(dt)
        self.background.update(dt)
        for fog in self.fogs:
            fog.update(dt)

    def draw(self, surface: pygame.Surface, font_registry: dict[str, Font]):
        self.background.draw(surface)

        for chapter_region in self.chapter_regions:
            chapter_region.draw(surface)

        for chapter in range(DataFiles.save_file["chapter_progress"]+1):
            path = self.paths.get(chapter, [])
            for point, angle in path:
                center = point + anchor()
                dash_offset = get_vec(self.PATH_DASH_LENGTH / 2, angle)
                dash_width_offset = get_vec(self.PATH_DASH_WIDTH / 2, angle + math.radians(90))
                dash_polygon = [
                    center + dash_offset + dash_width_offset,
                    center - dash_offset + dash_width_offset,
                    center - dash_offset - dash_width_offset,
                    center + dash_offset - dash_width_offset,
                ]
                pygame.draw.polygon(
                    surface,
                    Color.WHITE,
                    dash_polygon
                )

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
            self.selected_sortie_node.draw_selection_effect(
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
        
        if self.selected_sortie_node is not None:
            self.sortie_order_card.draw(surface, font_registry)

        self.exit_sortie_selection_menu_button.draw(surface, font_registry)
