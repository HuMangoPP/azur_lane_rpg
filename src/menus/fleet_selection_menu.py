import math
import pygame
import random

from engine.util import get_rect, get_vec
from engine.button import Button

from src.constants import DataFiles, Color, Box, screen_x, screen_y
from src.menus.quests_data import first_sortie_quest
from src.menus.sortie_selection_menu import (
    Background,
    ChapterProgressAnnotation,
    NameRibbon,
)

from live2d.live2d import Live2D


def draw_rotated_handwritten_text(
    surface,
    font_registry,
    text,
    position,
    angle,
    scale=1.0,
    padding=2,
):
    font = font_registry["handwritten"]
    text_size = (
        math.ceil(font.get_width(text, scale, 0)),
        math.ceil(font.get_height(text, scale, 0)),
    )
    text_surface = pygame.Surface(
        (
            text_size[0] + 2*padding,
            text_size[1] + 2*padding,
        ),
        pygame.SRCALPHA,
    )
    font.render(
        text_surface,
        text,
        text_surface.get_rect().center,
        Color.WHITE,
        scale,
        style="center",
    )
    rotated_text = pygame.transform.rotate(text_surface, angle)
    surface.blit(rotated_text, rotated_text.get_rect(center=position))


class FleetNameRibbon(NameRibbon):
    def get_rect(self, font_registry):
        width = self.get_width(font_registry)
        height = DataFiles.sprites["sortie_selection"]["name_middle"].get_height() * self.scale
        return get_rect(width=width, height=height, center=self.position)


class FleetPathAnnotation:
    TEXT_SCALE = 1.0
    TEXT_OFFSET = 20
    TEXT_SURFACE_PADDING = 2
    DASH_LENGTH = 9
    DASH_GAP = 6
    LINE_WIDTH = 2
    ARROWHEAD_LENGTH = 12
    ARROWHEAD_ANGLE = math.radians(32)

    def __init__(self, start_point, end_point, bend, text, text_above=False):
        self.text = text
        mid_point = start_point.lerp(end_point, 0.5) + pygame.Vector2(0, bend)
        self.curve_points = ChapterProgressAnnotation.create_circular_curve(
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
        if (text_above and text_normal.y > 0) or (
            not text_above and text_normal.y < 0
        ):
            text_normal *= -1
        self.text_position = (
            self.curve_points[mid_index]
            + text_normal*self.TEXT_OFFSET
        )
        self.text_angle = math.degrees(math.atan2(
            -text_direction.y,
            text_direction.x,
        ))

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

    def draw_text(self, surface, font_registry):
        draw_rotated_handwritten_text(
            surface,
            font_registry,
            self.text,
            self.text_position,
            self.text_angle,
            scale=self.TEXT_SCALE,
            padding=self.TEXT_SURFACE_PADDING,
        )

    def draw(self, surface, font_registry):
        self.draw_dashed_curve(surface, self.curve_points)

        arrow_direction = (
            self.curve_points[-1] - self.curve_points[-2]
        ).normalize()
        backwards_angle = math.atan2(-arrow_direction.y, -arrow_direction.x)
        for angle_offset in (-self.ARROWHEAD_ANGLE, self.ARROWHEAD_ANGLE):
            arrow_side = self.curve_points[-1] + get_vec(
                self.ARROWHEAD_LENGTH,
                backwards_angle + angle_offset,
            )
            pygame.draw.line(
                surface,
                Color.WHITE,
                self.curve_points[-1],
                arrow_side,
                width=self.LINE_WIDTH,
            )

        self.draw_text(surface, font_registry)


class FleetSelectionMenu:
    Y_ALIGN = screen_y(0.4)
    PATH_DASH_LENGTH = 16
    PATH_DASH_WIDTH = 4
    LAUNCH_MARKER_RADIUS = 32
    LAUNCH_MARKER_HIT_SIZE = 80
    LAUNCH_MARKER_HOVER_LIFT = 2
    LAUNCH_MARKER_SHADOW_OFFSET = pygame.Vector2(2, 4)
    LAUNCH_MARKER_MUTED_INK = (146, 165, 196)
    SELECTION_PULSE_DURATION = 2.4
    SELECTION_GLINT_CYCLE = 0.9
    SELECTION_GLINT_LIFETIME = 0.7
    SELECTION_GLINT_MAX_LENGTH = 5
    SELECTION_GLINT_DRIFT = 12
    PATH_HEX_GLINTS_PER_HEX = 4
    PATH_HEX_GLINT_MARGIN = 6
    PROP_MIN_OFFSET = 64
    PROP_MAX_OFFSET = 96
    PROP_PLACEMENT_ATTEMPTS = 64
    PROP_SPACING = 8
    MARKER_GLINT_COUNT = 4
    MARKER_GLINT_MARGIN = 6
    MARKER_PROJECTION_ALPHA = 192
    TRAY_FRAME_COLOR = (38, 52, 72)
    TRAY_FRAME_HIGHLIGHT = (76, 96, 119)
    TRAY_FRAME_SHADOW = (19, 28, 42)
    TRAY_RECESS_RIM = (15, 24, 36)
    TRAY_BAY_COLOR = (45, 62, 76)
    TRAY_BAY_HIGHLIGHT = (72, 91, 108)
    TRAY_SCREW_COLOR = (58, 75, 91)
    TRAY_CAST_SHADOW = (7, 14, 28)
    TRAY_CORNER_CUT = 4
    TRAY_MARKER_SHADOW_OFFSET = (2, 2)
    TRAY_MARKER_HOVER_LIFT = 4
    TRAY_DRAG_SHADOW_OFFSET = (4, 6)
    SET_SAIL_TEXT = "set sail?"
    SET_SAIL_TEXT_OFFSET = 56
    SET_SAIL_TEXT_ANGLE = 8

    def __init__(self, menu_manager):
        self.menu_manager = menu_manager

        # TODO update tray styling
        num_rows = 1
        num_rects_in_row = 6
        self.tray_overlay = get_rect(
            width=num_rects_in_row*(Box.WIDTH + Box.PADDING) + 5*Box.PADDING,
            height=num_rows*(Box.HEIGHT + Box.PADDING) + 5*Box.PADDING,
            right=Box.RIGHT_OF_SCREEN,
            bottom=Box.BOTTOM_OF_SCREEN
        )
        self.available_shipgirl_rects = [
            get_rect(
                width=Box.WIDTH, height=Box.HEIGHT,
                left=self.tray_overlay.left+3*Box.PADDING+(i%num_rects_in_row)*(Box.WIDTH+Box.PADDING),
                top=self.tray_overlay.top+3*Box.PADDING+(i//num_rects_in_row)*(Box.HEIGHT+Box.PADDING)
            ) for i in range(num_rows * num_rects_in_row)
        ]

        self.mouse_start_drag = None
        self.selected_shipgirl_index_from_fleet = None
        self.selected_shipgirl_index_from_backup = None

        self.selected_shipgirl = None
        def start_sortie():
            if all(shipgirl is None for shipgirl in self.menu_manager.player_fleet.shipgirls):
                return
            self.start_sortie_button.active = False
            self.menu_manager.encounter_menu.start_sortie_transition()

        self.start_sortie_button = Button(
            get_rect(
                width=self.LAUNCH_MARKER_HIT_SIZE,
                height=self.LAUNCH_MARKER_HIT_SIZE,
                center=(screen_x(0.5), self.Y_ALIGN),
            ),
            start_sortie,
            active=False,
        )
        self.start_sortie_anchor = DataFiles.sprites["user_interface"]["start_sortie"]
        self.muted_start_sortie_anchor = DataFiles.recolor_sprite(
            "user_interface",
            "start_sortie",
            self.LAUNCH_MARKER_MUTED_INK,
        )

        def exit_fleet_selection_menu():
            self.menu_manager.current_menu = self.menu_manager.sortie_selection_menu
            self.start_sortie_button.active = False
        
        button_sprite = DataFiles.sprites["user_interface"]["prev"]
        button_rect = get_rect(width=48,height=48,right=Box.RIGHT_OF_SCREEN,top=Box.TOP_OF_SCREEN)
        self.exit_fleet_selection_menu_button = Button(
            button_rect,
            exit_fleet_selection_menu,
            background_styling={
                "background_color": Color.BLACK,
                "background_img": button_sprite,
                "opacity": 160
            },
            hover_styling={"opacity": 200}
        )

        slot_size = 64
        self.fleet_slots = [
            get_rect(
                width=slot_size, height=slot_size,
                centerx=screen_x(0.25) + 1.5 * slot_size - (slot_index-1)*slot_size/4,
                centery=self.Y_ALIGN + (slot_index-1)*(slot_size + Box.PADDING)
            ) for slot_index in range(3)
        ]
        self.backup_fleet_slots = [
            get_rect(
                width=slot_size, height=slot_size,
                centerx=slot.centerx - 3.5 * slot_size,
                centery=slot.centery,
            ) for slot in self.fleet_slots
        ]

        self.primary_fleet_box = self.fleet_slots[0].unionall(self.fleet_slots[1:]).inflate(2*Box.PADDING, 2*Box.PADDING)
        self.backup_fleet_box = self.backup_fleet_slots[0].unionall(self.backup_fleet_slots[1:]).inflate(2*Box.PADDING, 2*Box.PADDING)

        banner_height = DataFiles.sprites["sortie_selection"]["name_middle"].get_height()
        self.primary_fleet_ribbon = FleetNameRibbon(
            (self.primary_fleet_box.centerx, self.primary_fleet_box.bottom + Box.PADDING + banner_height / 2),
            "primary",
            scale=0.75
        )
        self.backup_fleet_ribbon = FleetNameRibbon(
            (self.backup_fleet_box.centerx, self.backup_fleet_box.bottom + Box.PADDING + banner_height / 2),
            "backup",
            scale=0.75
        )

        self.sortie_index = -1
        self.header_ribbon = FleetNameRibbon((screen_x(0.5), Box.TOP_OF_SCREEN), "", scale=1.0)

        self.path = []
        self.path_hexes = []
        self.path_annotations = []
        self.empty_loop_position = None
        self.sortie_props = []
        self.start_sortie_prop_position = None
        self.selection_effect_time = 0

        self.background = Background()
        self.marker_glow_layer = None
        self.marker_projection_layer = None
        self._tray_surface_cache = None
        self._tray_shadow_cache = None
        self._tray_cache_size = None
        self._tray_marker_shadow_cache = {}

    def _draw_dashed_rect(self, surface, rect, color = Color.WHITE, dash_length = PATH_DASH_LENGTH, dash_width = PATH_DASH_WIDTH):
        for start, end in [
            (rect.topleft, rect.topright),
            (rect.topright, rect.bottomright),
            (rect.bottomright, rect.bottomleft),
            (rect.bottomleft, rect.topleft),
        ]:
            start = pygame.Vector2(start)
            end = pygame.Vector2(end)
            edge = end - start
            edge_length = edge.length()
            if edge_length == 0:
                continue
            direction = edge / edge_length
            distance = 0
            while distance < edge_length:
                dash_start = start + direction * distance
                dash_end = start + direction * min(distance + dash_length, edge_length)
                pygame.draw.line(surface, color, dash_start, dash_end, width=dash_width)
                distance += 2 * dash_length

    @classmethod
    def _get_tray_polygon(cls, size, offset=(0, 0)):
        width, height = size
        offset_x, offset_y = offset
        corner_cut = cls.TRAY_CORNER_CUT
        return [
            (offset_x + corner_cut, offset_y),
            (offset_x + width - corner_cut - 1, offset_y),
            (offset_x + width - 1, offset_y + corner_cut),
            (offset_x + width - 1, offset_y + height - corner_cut - 1),
            (offset_x + width - corner_cut - 1, offset_y + height - 1),
            (offset_x + corner_cut, offset_y + height - 1),
            (offset_x, offset_y + height - corner_cut - 1),
            (offset_x, offset_y + corner_cut),
        ]

    def _get_local_tray_bays(self):
        return [
            rect.move(-self.tray_overlay.left, -self.tray_overlay.top)
            for rect in self.available_shipgirl_rects
        ]

    def _draw_tray_screw(self, surface, center):
        center_x, center_y = center
        pygame.draw.circle(
            surface,
            self.TRAY_FRAME_SHADOW,
            center,
            radius=Box.PADDING,
        )
        pygame.draw.circle(
            surface,
            self.TRAY_SCREW_COLOR,
            center,
            radius=Box.PADDING-2,
        )
        pygame.draw.line(
            surface,
            self.TRAY_FRAME_SHADOW,
            (center_x - (Box.PADDING-2), center_y),
            (center_x + (Box.PADDING-2), center_y),
            width=3,
        )

    def _build_tray_surface(self):
        tray_size = self.tray_overlay.size
        tray_surface = pygame.Surface(tray_size, flags=pygame.SRCALPHA)
        tray_polygon = self._get_tray_polygon(tray_size)
        pygame.draw.polygon(tray_surface, self.TRAY_FRAME_COLOR, tray_polygon)

        local_bays = self._get_local_tray_bays()
        for bay_rect in local_bays:
            recess_rect = bay_rect.inflate(4, 4)
            pygame.draw.rect(tray_surface, self.TRAY_RECESS_RIM, recess_rect)
            pygame.draw.rect(tray_surface, self.TRAY_BAY_COLOR, bay_rect)

            # Crisp directional shading makes each bay read as stamped metal.
            pygame.draw.line(
                tray_surface,
                self.TRAY_RECESS_RIM,
                bay_rect.topleft,
                bay_rect.topright,
                width=2,
            )
            pygame.draw.line(
                tray_surface,
                self.TRAY_RECESS_RIM,
                bay_rect.topleft,
                bay_rect.bottomleft,
                width=2,
            )
            pygame.draw.line(
                tray_surface,
                self.TRAY_BAY_HIGHLIGHT,
                bay_rect.bottomleft + pygame.Vector2(2, -2),
                bay_rect.bottomright + pygame.Vector2(-2, -2),
            )
            pygame.draw.line(
                tray_surface,
                self.TRAY_BAY_HIGHLIGHT,
                bay_rect.topright + pygame.Vector2(-2, 2),
                bay_rect.bottomright + pygame.Vector2(-2, -2),
            )

        width, height = tray_size
        corner_cut = self.TRAY_CORNER_CUT
        pygame.draw.lines(
            tray_surface,
            self.TRAY_FRAME_HIGHLIGHT,
            False,
            [
                (0, height - corner_cut - 1),
                (0, corner_cut),
                (corner_cut, 0),
                (width - corner_cut - 1, 0),
            ],
            width=2,
        )
        pygame.draw.lines(
            tray_surface,
            self.TRAY_FRAME_SHADOW,
            False,
            [
                (width - corner_cut - 1, 1),
                (width - 1, corner_cut),
                (width - 1, height - corner_cut - 1),
                (width - corner_cut - 1, height - 1),
                (corner_cut, height - 1),
            ],
            width=4,
        )

        screw_margin = 1.75*Box.PADDING
        for screw_center in [
            (screw_margin, screw_margin),
            (width - screw_margin, screw_margin),
            (screw_margin, height - screw_margin),
            (width - screw_margin, height - screw_margin),
        ]:
            self._draw_tray_screw(tray_surface, screw_center)

        return tray_surface

    def _build_tray_shadow(self):
        width, height = self.tray_overlay.size
        shadow_surface = pygame.Surface(
            (width + 10, height + 12),
            flags=pygame.SRCALPHA,
        )
        pygame.draw.polygon(
            shadow_surface,
            (*self.TRAY_CAST_SHADOW, 56),
            self._get_tray_polygon((width, height), offset=(6, 8)),
        )
        pygame.draw.polygon(
            shadow_surface,
            (*self.TRAY_CAST_SHADOW, 112),
            self._get_tray_polygon((width, height), offset=(3, 4)),
        )
        return shadow_surface

    def _get_tray_surfaces(self):
        if self._tray_cache_size != self.tray_overlay.size:
            self._tray_cache_size = self.tray_overlay.size
            self._tray_surface_cache = self._build_tray_surface()
            self._tray_shadow_cache = self._build_tray_shadow()
        return self._tray_surface_cache, self._tray_shadow_cache

    def generate_path(self):
        num_encounters = len(DataFiles.sortie_data[self.sortie_index]["encounters"])
        extra_loops = 1
        encounter_counter = num_encounters + extra_loops
        radius = 48
        sign = random.choice([1, -1])
        straight_distance = random.uniform(5, 10)
        launch_angle = sign * math.radians(90)
        land_pos = pygame.Vector2(screen_x(0.5), self.Y_ALIGN)
        checkpoints = [land_pos]
        while encounter_counter > 0:
            circle_center = land_pos + get_vec(radius, launch_angle)
            launch_angle = sign * math.radians(random.uniform(5, 15))
            launch_pos = circle_center + get_vec(radius, launch_angle)
            land_pos = launch_pos + get_vec(straight_distance, launch_angle + sign * math.radians(90))
            checkpoints.extend([launch_pos, land_pos])
            sign *= -1
            encounter_counter -= 1

            if encounter_counter > 1:
                straight_distance = random.uniform(80, 120)
            else:
                straight_distance = random.uniform(10, 20)
        circle_center = land_pos + get_vec(radius, launch_angle)
        end_pos = circle_center + get_vec(radius, -sign * math.radians(90))
        checkpoints.append(end_pos)

        step = 1
        record_every = 30
        record_every_counter = record_every
        turn_amount = step / radius
        angle = 0.0
        pos = pygame.Vector2(screen_x(0.5), self.Y_ALIGN)
        draw_hex = False
        candidate_hexes = []
        self.path = [(pos, angle)]
        for checkpoint in checkpoints:
            to_target = checkpoint - pos
            checkpoint_turn_amount = turn_amount
            distance_squared = to_target.length_squared()
            if distance_squared > 0:
                heading = get_vec(1, angle)
                # Curvature of the circle tangent to the current heading that
                # passes through this checkpoint.
                required_curvature = abs(
                    2 * heading.cross(to_target) / distance_squared
                )
                checkpoint_turn_amount = max(
                    checkpoint_turn_amount,
                    required_curvature * step,
                )
            while to_target.length() > 5:
                pos = pos + get_vec(step, angle)
                if record_every_counter == 0:
                    if draw_hex:
                        candidate_hexes.append(pos)
                        draw_hex = False
                    self.path.append((pos, angle))
                    record_every_counter = record_every
                else:
                    record_every_counter -= 1
                left_side = get_vec(1, angle - math.radians(90))
                to_target = checkpoint - pos
                dot_product = left_side * to_target
                if dot_product > 0:
                    new_angle = angle - checkpoint_turn_amount
                else:
                    new_angle = angle + checkpoint_turn_amount
                if (
                    (angle < 0 and new_angle >= 0)
                    or (angle > 0 and new_angle < 0)
                ):
                    draw_hex = True
                angle = new_angle
                new_left_side = get_vec(1, angle - math.radians(90))
                new_dot_product = new_left_side * to_target
                if (
                    (dot_product > 0 and new_dot_product <= 0)
                    or (dot_product <= 0 and new_dot_product > 0)
                ):
                    angle = math.atan2(to_target.y, to_target.x)
        if record_every_counter < record_every:
            pos = pos + get_vec(record_every_counter, angle)
            self.path.append((pos, angle))
        if len(candidate_hexes) < num_encounters + extra_loops:
            candidate_hexes.append(pos)
        encounter_loop_hexes = random.sample(
            candidate_hexes[:-1],
            k=num_encounters - 1,
        )
        self.empty_loop_position = next(
            candidate
            for candidate in candidate_hexes[:-1]
            if candidate not in encounter_loop_hexes
        )
        self.path_hexes = encounter_loop_hexes + [candidate_hexes[-1]]
        self.generate_path_annotations()

        self.start_sortie_button.rect.center = self.path[0][0]
        self.generate_sortie_props()

    def generate_path_annotations(self):
        final_path_hex = self.path_hexes[-1]
        upper_hex_edge = final_path_hex + pygame.Vector2(-24, -16)
        lower_hex_edge = final_path_hex + pygame.Vector2(-24, 16)
        self.path_annotations = [
            FleetPathAnnotation(
                pygame.Vector2(self.primary_fleet_box.topright)
                + pygame.Vector2(Box.PADDING, -Box.PADDING),
                upper_hex_edge,
                -40,
                "initial strike group",
                text_above=True,
            ),
            FleetPathAnnotation(
                pygame.Vector2(self.backup_fleet_box.bottomright)
                + pygame.Vector2(Box.PADDING, Box.PADDING),
                lower_hex_edge,
                64,
                "delayed strike group",
            ),
        ]

    def generate_sortie_props(self):
        self.sortie_props = []
        self.start_sortie_prop_position = None
        prop_sets = DataFiles.sortie_selection_details.get(
            "fleet_selection_props",
            [],
        )
        if not 0 <= self.sortie_index < len(prop_sets):
            return

        prop_anchors = {
            "start": pygame.Vector2(self.start_sortie_button.rect.center),
            "end": self.path_hexes[-1],
            "empty_loop": self.empty_loop_position,
        }
        for prop_info in prop_sets[self.sortie_index]:
            prop_key = prop_info["prop"]
            position = self.get_random_prop_position(
                prop_anchors[prop_info["anchor"]],
                DataFiles.sprites["sortie_selection"][prop_key],
            )
            self.sortie_props.append((prop_key, position))
            if prop_info["anchor"] == "start":
                self.start_sortie_prop_position = pygame.Vector2(position)

    def get_random_prop_position(self, anchor, prop):
        screen_rect = pygame.Rect((0, 0), (screen_x(1), screen_y(1)))
        header_rect = pygame.Rect(0, 0, screen_x(1), 80)
        protected_rects = [
            header_rect,
            self.exit_fleet_selection_menu_button.rect,
            self.backup_fleet_box.inflate(2*Box.PADDING, 2*Box.PADDING),
            self.primary_fleet_box.inflate(2*Box.PADDING, 2*Box.PADDING),
            self.tray_overlay.inflate(2*Box.PADDING, 2*Box.PADDING),
        ]
        marker_centers = [
            pygame.Vector2(self.start_sortie_button.rect.center),
            *self.path_hexes,
        ]
        placed_prop_rects = [
            DataFiles.sprites["sortie_selection"][prop_key].get_rect(
                center=position,
            )
            for prop_key, position in self.sortie_props
        ]

        for _ in range(self.PROP_PLACEMENT_ATTEMPTS):
            position = anchor + get_vec(
                random.uniform(self.PROP_MIN_OFFSET, self.PROP_MAX_OFFSET),
                random.uniform(0, math.tau),
            )
            prop_rect = prop.get_rect(center=position)
            if not screen_rect.contains(prop_rect):
                continue
            if any(prop_rect.colliderect(rect) for rect in protected_rects):
                continue
            if any(
                position.distance_to(marker_center) < self.PROP_MIN_OFFSET
                for marker_center in marker_centers
            ):
                continue
            if any(
                prop_rect.inflate(
                    self.PROP_SPACING,
                    self.PROP_SPACING,
                ).colliderect(rect)
                for rect in placed_prop_rects
            ):
                continue
            return position

        # The anchor regions have ample room in normal layouts. Retain the final
        # randomized candidate if an unusually constrained route exhausts retries.
        return position

    def draw_sortie_props(self, surface):
        for prop_key, position in self.sortie_props:
            prop = DataFiles.sprites["sortie_selection"][prop_key]
            surface.blit(prop, prop.get_rect(center=position))

    def draw_set_sail_annotation(self, surface, font_registry):
        if not self.start_sortie_button.active:
            return

        marker_center = pygame.Vector2(self.start_sortie_button.rect.center)
        prop_is_above = (
            self.start_sortie_prop_position is not None
            and self.start_sortie_prop_position.y < marker_center.y
        )
        text_side = 1 if prop_is_above else -1
        text_position = marker_center + pygame.Vector2(
            -4, text_side*self.SET_SAIL_TEXT_OFFSET,
        )
        text_angle = -self.SET_SAIL_TEXT_ANGLE*text_side
        draw_rotated_handwritten_text(
            surface,
            font_registry,
            self.SET_SAIL_TEXT,
            text_position,
            text_angle,
        )

    def _get_launch_marker_polygon(self, center):
        return [
            pygame.Vector2(center) + get_vec(
                self.LAUNCH_MARKER_RADIUS,
                math.radians(30 + corner_index*60),
            )
            for corner_index in range(6)
        ]

    def draw_launch_marker(self, surface):
        center = pygame.Vector2(self.start_sortie_button.rect.center)
        hovered = (
            self.start_sortie_button.active
            and self.start_sortie_button.hovered
            and self.mouse_start_drag is None
        )
        token_center = center - pygame.Vector2(
            0,
            self.LAUNCH_MARKER_HOVER_LIFT if hovered else 0,
        )

        shadow_polygon = self._get_launch_marker_polygon(
            center + self.LAUNCH_MARKER_SHADOW_OFFSET
        )
        pygame.draw.polygon(surface, self.TRAY_CAST_SHADOW, shadow_polygon)

        if self.start_sortie_button.active:
            glow_sprite = DataFiles.sprites["sortie_selection"][
                "uncleared_node_selection_glow"
            ]
            glow = self.get_pulsing_selection_glow(glow_sprite)
            marker_polygon = self._get_launch_marker_polygon(token_center)
            glow_left = int(min(corner.x for corner in marker_polygon))
            glow_right = int(max(corner.x for corner in marker_polygon))
            glow_rect = pygame.Rect(
                glow_left,
                0,
                glow_right - glow_left + 1,
                glow.get_height(),
            )
            glow_rect.bottom = token_center.y
            marker_glow = pygame.transform.smoothscale(glow, glow_rect.size)
            surface.blit(
                marker_glow,
                glow_rect,
                special_flags=pygame.BLEND_RGB_ADD,
            )

        outline_color = Color.UNCLEARED_ZONE_OUTLINE
        if self.start_sortie_button.active:
            fill_color = Color.UNCLEARED_ZONE_OUTLINE
            anchor = self.start_sortie_anchor
        else:
            fill_color = Color.UNCLEARED_ZONE_FILL
            anchor = self.muted_start_sortie_anchor

        marker_polygon = self._get_launch_marker_polygon(token_center)
        pygame.draw.polygon(surface, fill_color, marker_polygon)
        pygame.draw.polygon(
            surface,
            outline_color,
            marker_polygon,
            width=Box.OUTLINE_WIDTH,
        )

        anchor_rect = anchor.get_rect(center=token_center)
        surface.blit(anchor, anchor_rect)

        if self.start_sortie_button.active:
            glint_count = self.PATH_HEX_GLINTS_PER_HEX
            for glint_index in range(glint_count):
                glint_time = (
                    self.selection_effect_time
                    + glint_index*self.SELECTION_GLINT_CYCLE/glint_count
                )
                glint_age = glint_time % self.SELECTION_GLINT_CYCLE
                if glint_age >= self.SELECTION_GLINT_LIFETIME:
                    continue

                cycle_index = math.floor(glint_time / self.SELECTION_GLINT_CYCLE)
                glint_progress = glint_age / self.SELECTION_GLINT_LIFETIME
                glint_strength = (1 - glint_progress)**1.5
                half_spawn_width = (
                    math.sqrt(3)/2*self.LAUNCH_MARKER_RADIUS
                    - self.PATH_HEX_GLINT_MARGIN
                )
                spawn_x = (
                    (cycle_index*29 + glint_index*17)
                    % (2*half_spawn_width)
                    - half_spawn_width
                )
                half_spawn_height = (
                    self.LAUNCH_MARKER_RADIUS
                    - abs(spawn_x)/math.sqrt(3)
                    - self.PATH_HEX_GLINT_MARGIN
                )
                spawn_y = (
                    (cycle_index*19 + glint_index*31)
                    % (2*half_spawn_height)
                    - half_spawn_height
                )
                spawn_center = token_center + pygame.Vector2(spawn_x, spawn_y)
                glint_center = spawn_center - pygame.Vector2(
                    0,
                    self.SELECTION_GLINT_DRIFT*glint_progress,
                )
                self.draw_selection_glint(
                    surface,
                    glint_center,
                    Color.UNCLEARED_ZONE_OUTLINE,
                    glint_strength,
                )

    def get_pulsing_selection_glow(self, glow_sprite):
        pulse = (
            math.sin(
                self.selection_effect_time
                * math.tau
                / self.SELECTION_PULSE_DURATION
            )
            + 1
        ) / 2
        glow_base = glow_sprite.copy()
        glow_base.set_alpha(int(128 + 127*pulse))
        glow = pygame.Surface(glow_base.get_size())
        glow.blit(glow_base)
        return glow

    def draw_selection_glint(self, surface, center, color, strength):
        glint_length = 1 + round(
            (self.SELECTION_GLINT_MAX_LENGTH - 1)*strength
        )
        glint_color = tuple(round(channel*strength) for channel in color)
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

    def draw_path_hexes(self, surface):
        hex_size = Box.WIDTH/2
        glow_sprite = DataFiles.sprites["sortie_selection"]["locked_node_selection_glow"]
        glow = self.get_pulsing_selection_glow(glow_sprite)

        encounters = DataFiles.sortie_data[self.sortie_index]["encounters"]
        path_hex_centers = []
        for point, encounter in zip(self.path_hexes, encounters):
            has_tester = any(
                siren_encoding.split(":")[0] == "tester"
                for siren_encoding in encounter["front"] + encounter["back"]
            )
            if has_tester:
                icon = DataFiles.sprites["user_interface"]["boss"]
            else:
                icon = DataFiles.sprites["user_interface"]["uncleared"]
            icon_rect = icon.get_rect(center=point)
            hex_center = pygame.Vector2(icon_rect.center)
            polygon = [
                hex_center + get_vec(
                    hex_size,
                    math.radians(30 + corner_index*60),
                )
                for corner_index in range(6)
            ]

            shadow_polygon = [point + pygame.Vector2(2, 4) for point in polygon]
            pygame.draw.polygon(surface, self.TRAY_CAST_SHADOW, shadow_polygon)

            glow_left = int(min(corner.x for corner in polygon))
            glow_right = int(max(corner.x for corner in polygon))
            glow_rect = pygame.Rect(
                glow_left,
                0,
                glow_right - glow_left + 1,
                glow.get_height(),
            )
            glow_rect.bottom = hex_center.y
            hex_glow = pygame.transform.smoothscale(glow, glow_rect.size)
            surface.blit(
                hex_glow,
                glow_rect,
                special_flags=pygame.BLEND_RGB_ADD,
            )

            pygame.draw.polygon(surface, Color.LOCKED_ZONE_OUTLINE, polygon)
            surface.blit(icon, icon_rect)
            path_hex_centers.append(hex_center)

        glint_count = len(path_hex_centers) * self.PATH_HEX_GLINTS_PER_HEX
        for hex_index, hex_center in enumerate(path_hex_centers):
            for glint_index in range(self.PATH_HEX_GLINTS_PER_HEX):
                particle_index = glint_index*len(path_hex_centers) + hex_index
                glint_time = (
                    self.selection_effect_time
                    + particle_index*self.SELECTION_GLINT_CYCLE/glint_count
                )
                glint_age = glint_time % self.SELECTION_GLINT_CYCLE
                if glint_age >= self.SELECTION_GLINT_LIFETIME:
                    continue

                cycle_index = math.floor(glint_time / self.SELECTION_GLINT_CYCLE)
                glint_progress = glint_age / self.SELECTION_GLINT_LIFETIME
                glint_strength = (1 - glint_progress)**1.5
                half_spawn_width = (
                    math.sqrt(3)/2*hex_size - self.PATH_HEX_GLINT_MARGIN
                )
                spawn_x = (
                    (cycle_index*29 + particle_index*17) % (2*half_spawn_width)
                    - half_spawn_width
                )
                half_spawn_height = (
                    hex_size
                    - abs(spawn_x)/math.sqrt(3)
                    - self.PATH_HEX_GLINT_MARGIN
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
                self.draw_selection_glint(
                    surface,
                    center,
                    Color.LOCKED_ZONE_OUTLINE,
                    glint_strength,
                )

    def draw_marker_selection_effect(self, surface, marker_rect):
        glow_sprite = DataFiles.sprites["fleet_selection"]["marker_selection_glow"]
        glow = self.get_pulsing_selection_glow(glow_sprite)
        glow_rect = glow.get_rect(midbottom=marker_rect.center)
        surface.blit(glow, glow_rect, special_flags=pygame.BLEND_RGB_ADD)

        vertical_spawn_range = glow_rect.height - 2*self.MARKER_GLINT_MARGIN
        bottom_width = math.ceil(0.75*Box.WIDTH)
        for glint_index in range(self.MARKER_GLINT_COUNT):
            glint_time = (
                self.selection_effect_time
                + glint_index*self.SELECTION_GLINT_CYCLE/self.MARKER_GLINT_COUNT
            )
            glint_age = glint_time % self.SELECTION_GLINT_CYCLE
            if glint_age >= self.SELECTION_GLINT_LIFETIME:
                continue

            cycle_index = math.floor(glint_time / self.SELECTION_GLINT_CYCLE)
            glint_progress = glint_age / self.SELECTION_GLINT_LIFETIME
            glint_strength = (1 - glint_progress)**1.5
            spawn_y = (
                self.MARKER_GLINT_MARGIN
                + (cycle_index*19 + glint_index*31) % vertical_spawn_range
            )
            y_ratio = spawn_y / (glow_rect.height - 1)
            cone_width = round(
                glow_rect.width - (glow_rect.width - bottom_width)*y_ratio
            )
            half_spawn_width = cone_width/2 - self.MARKER_GLINT_MARGIN
            spawn_x = (
                (cycle_index*29 + glint_index*17) % (2*half_spawn_width)
                - half_spawn_width
            )
            spawn_center = pygame.Vector2(
                glow_rect.centerx + spawn_x,
                glow_rect.top + spawn_y,
            )
            center = spawn_center - pygame.Vector2(
                0,
                self.SELECTION_GLINT_DRIFT*glint_progress,
            )
            if center.y < glow_rect.top:
                continue
            self.draw_selection_glint(
                surface,
                center,
                Color.HOLOGRAM_GLOW,
                glint_strength,
            )

    def get_marker_projection_layers(self, surface):
        surface_size = surface.get_size()
        if (
            self.marker_glow_layer is None
            or self.marker_glow_layer.get_size() != surface_size
        ):
            self.marker_glow_layer = pygame.Surface(surface_size)
            self.marker_projection_layer = pygame.Surface(
                surface_size,
                flags=pygame.SRCALPHA,
            )

        self.marker_glow_layer.fill((0, 0, 0))
        self.marker_projection_layer.fill((0, 0, 0, 0))

        return self.marker_glow_layer, self.marker_projection_layer

    def draw_marker_hologram(
        self,
        surface,
        marker,
        marker_rect,
        shipgirl,
        font_registry,
    ):
        glow_layer, projection_layer = self.get_marker_projection_layers(surface)
        self.draw_marker_selection_effect(glow_layer, marker_rect)

        # The opaque marker occludes the glow, keeping both halves the same color.
        surface.blit(glow_layer, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        surface.blit(marker, marker_rect)

        shipgirl.draw(
            projection_layer,
            font_registry,
            alpha=self.MARKER_PROJECTION_ALPHA,
        )
        surface.blit(projection_layer, (0, 0))

        # Reapply the cone through the projection silhouette so the translucent
        # shipgirl receives the light without brightening exposed marker pixels.
        projection_mask = pygame.mask.from_surface(projection_layer, threshold=1)
        mask_strength = self.MARKER_PROJECTION_ALPHA
        mask_surface = projection_mask.to_surface(
            setcolor=(255, 255, 255),
            unsetcolor=(0, 0, 0),
        )
        mask_surface.set_colorkey(None)
        projection_glow = glow_layer.copy()
        projection_glow.blit(
            mask_surface,
            (0, 0),
            special_flags=pygame.BLEND_RGB_MULT,
        )
        surface.blit(
            projection_glow,
            (0, 0),
            special_flags=pygame.BLEND_RGB_ADD,
        )

    def _draw_tray_bay_highlight(self, surface, rect):
        highlight = pygame.Surface(rect.size, flags=pygame.SRCALPHA)
        highlight.fill((*self.TRAY_BAY_HIGHLIGHT, 72))
        surface.blit(highlight, rect)

    def _get_tray_marker_shadow(self, marker_key, marker):
        cached_shadow = self._tray_marker_shadow_cache.get(marker_key)
        if cached_shadow is not None and cached_shadow.get_size() == marker.get_size():
            return cached_shadow

        marker_shadow = pygame.Surface(marker.get_size(), flags=pygame.SRCALPHA)
        marker_mask = pygame.mask.from_surface(marker)
        marker_mask.to_surface(
            marker_shadow,
            setcolor=(*self.TRAY_CAST_SHADOW, 144),
            unsetcolor=(0, 0, 0, 0),
        )
        self._tray_marker_shadow_cache[marker_key] = marker_shadow
        return marker_shadow

    def _draw_tray_marker(self, surface, shipgirl, rect, lifted=False):
        marker_key = shipgirl.name
        marker = DataFiles.sprites["fleet_selection"][marker_key]
        resting_rect = marker.get_rect(center=rect.center)
        marker_rect = resting_rect.move(
            0,
            -self.TRAY_MARKER_HOVER_LIFT if lifted else 0,
        )
        marker_shadow = self._get_tray_marker_shadow(marker_key, marker)
        shadow_rect = resting_rect.move(self.TRAY_MARKER_SHADOW_OFFSET)
        surface.blit(marker_shadow, shadow_rect)
        surface.blit(marker, marker_rect)

    def _draw_dragged_marker(self, surface, mouse_pos):
        if self.mouse_start_drag is None or self.selected_shipgirl is None:
            return

        marker_key = self.selected_shipgirl.name
        marker = DataFiles.sprites["fleet_selection"][marker_key]
        marker_is_deployed = (
            self.selected_shipgirl_index_from_fleet is not None
            or self.selected_shipgirl_index_from_backup is not None
        )
        shadow_key = marker_key
        if marker_is_deployed:
            marker = pygame.transform.flip(marker, flip_x=True, flip_y=False)
            shadow_key = f"{marker_key}:flipped"

        marker_rect = marker.get_rect(center=mouse_pos)
        marker_shadow = self._get_tray_marker_shadow(shadow_key, marker)
        surface.blit(marker_shadow, marker_rect.move(self.TRAY_DRAG_SHADOW_OFFSET))
        surface.blit(marker, marker_rect)

    def _draw_tray_bay_rims(self, surface):
        for rect in self.available_shipgirl_rects:
            pygame.draw.rect(surface, self.TRAY_RECESS_RIM, rect, width=2)
            pygame.draw.line(
                surface,
                self.TRAY_FRAME_HIGHLIGHT,
                rect.bottomleft + pygame.Vector2(1, -1),
                rect.bottomright + pygame.Vector2(-1, -1),
            )
            pygame.draw.line(
                surface,
                self.TRAY_FRAME_HIGHLIGHT,
                rect.topright + pygame.Vector2(-1, 1),
                rect.bottomright + pygame.Vector2(-1, -1),
            )

    def _draw_tray_drop_target(self, surface, mouse_pos):
        dragging_deployed_marker = (
            self.mouse_start_drag is not None
            and (
                self.selected_shipgirl_index_from_fleet is not None
                or self.selected_shipgirl_index_from_backup is not None
            )
        )
        if not dragging_deployed_marker or not self.tray_overlay.collidepoint(mouse_pos):
            return

        highlight_inset = 4
        highlight_size = (
            self.tray_overlay.width - 2 * highlight_inset,
            self.tray_overlay.height - 2 * highlight_inset,
        )
        tray_polygon = [
            pygame.Vector2(point)
            + self.tray_overlay.topleft
            + (highlight_inset, highlight_inset)
            for point in self._get_tray_polygon(highlight_size)
        ]
        pygame.draw.polygon(
            surface,
            Color.BLUEPRINT_PAGE_GLOW,
            tray_polygon,
            width=Box.OUTLINE_WIDTH,
        )

    def draw_tray_overlay(self, surface, font_registry):
        tray_surface, tray_shadow = self._get_tray_surfaces()
        surface.blit(tray_shadow, self.tray_overlay.topleft)
        surface.blit(tray_surface, self.tray_overlay)

        # Drawing the rims last seats the markers beneath the case lip.
        mouse_pos = pygame.mouse.get_pos()
        self._draw_tray_bay_rims(surface)
        self._draw_tray_drop_target(surface, mouse_pos)
        for shipgirl, rect in zip(
            self.menu_manager.available_shipgirls,
            self.available_shipgirl_rects,
        ):
            marker_available = shipgirl not in self.menu_manager.player_fleet.fleet
            marker_hovered = (
                marker_available
                and self.mouse_start_drag is None
                and rect.collidepoint(mouse_pos)
            )
            marker_dragged = (
                self.mouse_start_drag is not None
                and shipgirl is self.selected_shipgirl
            )
            if marker_hovered:
                self._draw_tray_bay_highlight(surface, rect)
            if marker_available and not marker_dragged:
                self._draw_tray_marker(
                    surface,
                    shipgirl,
                    rect,
                    lifted=marker_hovered,
                )

    def _align_shipgirl_with_fleet_selection_slot(self, shipgirl, slot):
        if shipgirl is not None:
            shipgirl.rect.centerx = slot.centerx
            shipgirl.rect.bottom = slot.centery
            shipgirl.sprite.set_animation(Live2D.IDLE_ANIMATION)
            shipgirl.facing_left = False

    def _drop_shipgirl(self, slot_shipgirls, marker_slots, event):
        for i, slot in enumerate(marker_slots):
            if not slot.collidepoint(event.pos):
                continue
            if self.selected_shipgirl_index_from_fleet is not None:
                self.menu_manager.player_fleet.shipgirls[self.selected_shipgirl_index_from_fleet] = slot_shipgirls[i]
                self._align_shipgirl_with_fleet_selection_slot(
                    slot_shipgirls[i],
                    self.fleet_slots[self.selected_shipgirl_index_from_fleet],
                )
            if self.selected_shipgirl_index_from_backup is not None:
                self.menu_manager.player_fleet.backups[self.selected_shipgirl_index_from_backup] = slot_shipgirls[i]
                self._align_shipgirl_with_fleet_selection_slot(
                    slot_shipgirls[i],
                    self.backup_fleet_slots[self.selected_shipgirl_index_from_backup],
                )
            slot_shipgirls[i] = self.selected_shipgirl
            self._align_shipgirl_with_fleet_selection_slot(self.selected_shipgirl, slot)
            return True
        return False

    def update(self, dt, events):
        self.selection_effect_time += dt
        if self.menu_manager.encounter_menu.transition_active:
            self.menu_manager.encounter_menu.update(dt, ())
            self.background.update(dt)
            return

        for event in events:
            if event.type == pygame.MOUSEMOTION:
                self.exit_fleet_selection_menu_button.hover(event.pos)
                if self.mouse_start_drag is None:
                    self.start_sortie_button.hover(event.pos)
                else:
                    self.start_sortie_button.hovered = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                self.selected_shipgirl = None
                self.mouse_start_drag = None
                self.selected_shipgirl_index_from_fleet = None
                self.selected_shipgirl_index_from_backup = None
                for shipgirl, rect in zip(self.menu_manager.available_shipgirls, self.available_shipgirl_rects):
                    if rect.collidepoint(event.pos) and not self.menu_manager.player_fleet.in_fleet(shipgirl):
                        self.mouse_start_drag = event.pos
                        self.selected_shipgirl = shipgirl
                for i, (shipgirl, slot) in enumerate(zip(self.menu_manager.player_fleet.shipgirls, self.fleet_slots)):
                    if shipgirl is not None and slot.collidepoint(event.pos):
                        self.mouse_start_drag = event.pos
                        self.selected_shipgirl = shipgirl
                        self.selected_shipgirl_index_from_fleet = i
                for i, (shipgirl, slot) in enumerate(zip(self.menu_manager.player_fleet.backups, self.backup_fleet_slots)):
                    if shipgirl is not None and slot.collidepoint(event.pos):
                        self.mouse_start_drag = event.pos
                        self.selected_shipgirl = shipgirl
                        self.selected_shipgirl_index_from_backup = i
            if event.type == pygame.MOUSEBUTTONUP:
                click = False
                was_dragging_shipgirl = self.selected_shipgirl is not None
                if self.selected_shipgirl is not None:
                    click = self._drop_shipgirl(
                        self.menu_manager.player_fleet.shipgirls,
                        self.fleet_slots,
                        event
                    )
                    click = click or self._drop_shipgirl(
                        self.menu_manager.player_fleet.backups,
                        self.backup_fleet_slots,
                        event
                    )
                    if self.tray_overlay.collidepoint(event.pos):
                        if self.selected_shipgirl_index_from_fleet is not None:
                            self.menu_manager.player_fleet.shipgirls[self.selected_shipgirl_index_from_fleet] = None
                        if self.selected_shipgirl_index_from_backup is not None:
                            self.menu_manager.player_fleet.backups[self.selected_shipgirl_index_from_backup] = None
                        click = True
                    self.selected_shipgirl = None

                self.mouse_start_drag = None
                if not was_dragging_shipgirl:
                    click = click or self.start_sortie_button.click(event.pos)
                click = click or self.exit_fleet_selection_menu_button.click(event.pos)

                if click:
                    DataFiles.sfx["click"].play()

                if self.menu_manager.encounter_menu.transition_active:
                    break

        if self.menu_manager.encounter_menu.transition_active:
            self.menu_manager.encounter_menu.update(dt, ())
            self.background.update(dt)
            return

        if first_sortie_quest.quest_id in self.menu_manager.quest_manager.started_quests:
            self.start_sortie_button.active = self.menu_manager.player_fleet.primary_fleet_size > 1
        else:
            self.start_sortie_button.active = self.menu_manager.player_fleet.primary_fleet_size > 0

        self.background.update(dt)

        for shipgirl in self.menu_manager.player_fleet.shipgirls:
            if shipgirl is not None:
                shipgirl.animate(dt)
        for shipgirl in self.menu_manager.player_fleet.backups:
            if shipgirl is not None:
                shipgirl.animate(dt)

    def draw(self, surface, font_registry):
        self.background.draw(surface)
        self.draw_sortie_props(surface)
        mpos = pygame.mouse.get_pos()

        for point, angle in self.path:
            dash_offset = get_vec(self.PATH_DASH_LENGTH / 2, angle)
            dash_width_offset = get_vec(
                self.PATH_DASH_WIDTH / 2,
                angle + math.radians(90),
            )
            dash_polygon = [
                point + dash_offset + dash_width_offset,
                point - dash_offset + dash_width_offset,
                point - dash_offset - dash_width_offset,
                point + dash_offset - dash_width_offset,
            ]
            pygame.draw.polygon(
                surface,
                Color.WHITE,
                dash_polygon,
            )

        self.draw_path_hexes(surface)
        self.draw_launch_marker(surface)

        self.background.draw_markings(surface, font_registry)
        
        self._draw_dashed_rect(surface, self.backup_fleet_box)
        self._draw_dashed_rect(surface, self.primary_fleet_box)
        self.backup_fleet_ribbon.draw(surface, font_registry)
        self.primary_fleet_ribbon.draw(surface, font_registry)

        for slot, shipgirl in zip(
            self.fleet_slots + self.backup_fleet_slots,
            self.menu_manager.player_fleet.shipgirls + self.menu_manager.player_fleet.backups
        ):
            if self.selected_shipgirl is not None:
                # TODO make custom colors
                pygame.draw.rect(surface, Color.BLUEPRINT_PAGE_GLOW, slot)
                # TODO dash value magic numbers
                self._draw_dashed_rect(surface, slot, dash_length=6, dash_width=2)

            if shipgirl is not None:
                if (
                    self.mouse_start_drag is not None
                    and shipgirl is self.selected_shipgirl
                ):
                    continue
                marker_hovered = slot.collidepoint(mpos)
                marker_key = "blank" if marker_hovered else shipgirl.name
                marker = DataFiles.sprites["fleet_selection"][marker_key]
                if marker_key != "blank":
                    marker = pygame.transform.flip(marker, flip_x=True, flip_y=False)
                marker_rect = marker.get_rect()
                marker_rect.center = slot.center
                if marker_hovered:
                    self.draw_marker_hologram(
                        surface,
                        marker,
                        marker_rect,
                        shipgirl,
                        font_registry,
                    )
                else:
                    surface.blit(marker, marker_rect)
            elif self.selected_shipgirl is not None:
                anchor_sprite = DataFiles.sprites["user_interface"]["start_sortie"]
                anchor_rect = anchor_sprite.get_rect()
                anchor_rect.center = slot.center
                surface.blit(anchor_sprite, anchor_rect)

        self.draw_tray_overlay(surface, font_registry)
        self.header_ribbon.draw(surface, font_registry)

        for path_annotation in self.path_annotations:
            path_annotation.draw(surface, font_registry)
        self.draw_set_sail_annotation(surface, font_registry)

        self.exit_fleet_selection_menu_button.draw(surface, font_registry)
        self._draw_dragged_marker(surface, mpos)

        if self.menu_manager.encounter_menu.transition_active:
            self.menu_manager.encounter_menu._draw_transition_wave_wipe(surface)
