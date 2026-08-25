import math
import pygame
import random

from engine.util import get_rect, get_vec
from engine.button import Button

from src.constants import DataFiles, Color, Box, screen_x, screen_y
from src.menus.quests_data import first_sortie_quest
from src.menus.sortie_selection_menu import NameRibbon, Background

from live2d.live2d import Live2D


class FleetNameRibbon(NameRibbon):
    def get_rect(self, font_registry):
        width = self.get_width(font_registry)
        height = DataFiles.sprites["sortie_selection"]["name_middle"].get_height() * self.FONT_SCALE
        return get_rect(width=width, height=height, center=self.position)


class HeaderNameRibbon(FleetNameRibbon):
    FONT_SCALE = 1.5


class FleetSelectionMenu:
    Y_ALIGN = screen_y(0.45)
    PATH_DASH_LENGTH = 16
    PATH_DASH_WIDTH = 4
    SELECTION_PULSE_DURATION = 2.4
    SELECTION_GLINT_CYCLE = 0.9
    SELECTION_GLINT_LIFETIME = 0.7
    SELECTION_GLINT_MAX_LENGTH = 5
    SELECTION_GLINT_DRIFT = 12
    PATH_HEX_GLINTS_PER_HEX = 4
    PATH_HEX_GLINT_MARGIN = 6
    MARKER_GLINT_COUNT = 4
    MARKER_GLINT_MARGIN = 6
    MARKER_PROJECTION_ALPHA = 192
    TRAY_WOOD_COLOR = (116, 79, 52)
    TRAY_BEZEL_COLOR = (153, 108, 74)
    TRAY_WOOD_GRAIN_SEED = 1

    def __init__(self, menu_manager):
        self.menu_manager = menu_manager

        # TODO update tray styling
        num_rows = 1
        num_rects_in_row = 6
        self.tray_overlay = get_rect(
            width=num_rects_in_row*(Box.WIDTH + Box.PADDING) + 4*Box.PADDING,
            height=num_rows*(Box.HEIGHT + Box.PADDING) + 3*Box.PADDING,
            right=Box.RIGHT_OF_SCREEN,
            bottom=Box.BOTTOM_OF_SCREEN
        )
        self.available_shipgirl_rects = [
            get_rect(
                width=Box.WIDTH, height=Box.HEIGHT,
                left=self.tray_overlay.left+2*Box.PADDING+(i%num_rects_in_row)*(Box.WIDTH+Box.PADDING),
                top=self.tray_overlay.top+2*Box.PADDING+(i//num_rects_in_row)*(Box.HEIGHT+Box.PADDING)
            ) for i in range(num_rows * num_rects_in_row)
        ]

        self.mouse_start_drag = None
        self.selected_shipgirl_index_from_fleet = None
        self.selected_shipgirl_index_from_backup = None

        self.selected_shipgirl = None
        def start_sortie():
            if all(shipgirl is None for shipgirl in self.menu_manager.player_fleet.shipgirls):
                return
            self.menu_manager.current_menu = self.menu_manager.encounter_menu
            self.start_sortie_button.active = False
            
            self._position_shipgirls_for_battle()
            self.menu_manager.player_fleet.begin_sortie()
            self.menu_manager.encounter_menu.begin_sortie()

        self.start_sortie_button = Button(
            get_rect(width=2*Box.WIDTH, height=Box.HEIGHT, right=Box.RIGHT_OF_SCREEN, bottom=self.tray_overlay.top - Box.PADDING),
            start_sortie,
            active=False,
            background_styling={
                "background_color": Color.START_SORTIE_BUTTON,
                "background_img": DataFiles.sprites["user_interface"]["start_sortie"],
                "background_img_align": (1/4, 1/2)
            },
            text_styling={
                "text": "start",
                "text_align": (2/3, 1/2),
                "text_color": Color.WHITE
            },
            hover_styling={"background_color": Color.HOVER_START_SORTIE_BUTTON}
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

        self.primary_fleet_box = self.fleet_slots[0].unionall(self.fleet_slots[1:]).inflate(Box.WIDTH, Box.HEIGHT)
        self.backup_fleet_box = self.backup_fleet_slots[0].unionall(self.backup_fleet_slots[1:]).inflate(Box.WIDTH, Box.HEIGHT)

        banner_height = DataFiles.sprites["sortie_selection"]["name_middle"].get_height()
        self.primary_fleet_ribbon = FleetNameRibbon(
            (self.primary_fleet_box.centerx, self.primary_fleet_box.bottom + Box.PADDING + banner_height / 2),
            "primary",
        )
        self.backup_fleet_ribbon = FleetNameRibbon(
            (self.backup_fleet_box.centerx, self.backup_fleet_box.bottom + Box.PADDING + banner_height / 2),
            "backup",
        )

        self.sortie_index = -1
        self.header_ribbon = HeaderNameRibbon((screen_x(0.5), Box.TOP_OF_SCREEN), "")

        self.path = []
        self.path_hexes = []
        self.selection_effect_time = 0

        self.background = Background()
        self.marker_glow_layer = None
        self.marker_projection_layer = None

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

    def draw_tray_wood_grain(self, surface, tray_rect):
        grain_rng = random.Random(self.TRAY_WOOD_GRAIN_SEED)
        y = tray_rect.top

        while y < tray_rect.bottom:
            band_height = min(grain_rng.randint(4, 24), tray_rect.bottom - y)
            color_offset = grain_rng.randint(-14, 14)
            color = (
                max(0, min(255, self.TRAY_WOOD_COLOR[0] + color_offset)),
                max(0, min(255, self.TRAY_WOOD_COLOR[1] + color_offset // 2)),
                max(0, min(255, self.TRAY_WOOD_COLOR[2] + color_offset // 3)),
            )
            band_rect = get_rect(
                width=tray_rect.width,
                height=band_height,
                left=tray_rect.left,
                top=y
            )
            pygame.draw.rect(surface, color, band_rect)
            y += band_height

    def generate_path(self):
        num_encounters = len(DataFiles.sortie_data[self.sortie_index]["encounters"])
        encounter_counter = num_encounters
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
        self.path = [(pos, angle)]
        self.path_hexes = []
        for checkpoint in checkpoints:
            to_target = checkpoint - pos
            while to_target.length() > 5:
                pos = pos + get_vec(step, angle)
                if record_every_counter == 0:
                    if draw_hex:
                        self.path_hexes.append(pos)
                        draw_hex = False
                    self.path.append((pos, angle))
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
        if len(self.path_hexes) < num_encounters:
            self.path_hexes.append(pos)

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

            pygame.draw.polygon(surface, Color.LOCKED_ZONE_FILL_HOVER, polygon)
            pygame.draw.polygon(
                surface,
                Color.LOCKED_ZONE_OUTLINE,
                polygon,
                width=Box.OUTLINE_WIDTH,
            )
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

    def draw_tray_overlay(self, surface, font_registry):
        self.draw_tray_wood_grain(surface, self.tray_overlay)
        pygame.draw.rect(surface, self.TRAY_BEZEL_COLOR, self.tray_overlay, width=6*Box.OUTLINE_WIDTH)

        for shipgirl, rect in zip(self.menu_manager.available_shipgirls, self.available_shipgirl_rects):
            pygame.draw.rect(surface, Color.CARGO_BOX, rect)
            portrait = DataFiles.sprites["fleet_selection"][shipgirl.name]
            portrait_rect = portrait.get_rect()
            portrait_rect.center = rect.center
            surface.blit(portrait, portrait_rect)
            pygame.draw.rect(surface, Color.CARGO_BOX_OUTLINE, rect, width=2*Box.OUTLINE_WIDTH)

    def _position_shipgirls_for_battle(self):
        for shipgirl, slot in zip(
            self.menu_manager.player_fleet.shipgirls,
            self.menu_manager.encounter_menu.fleet_slots,
        ):
            if shipgirl is not None:
                shipgirl.rect.center = slot.center
                shipgirl.sprite.set_animation(Live2D.IDLE_ANIMATION)
                shipgirl.facing_left = False

        for shipgirl, slot in zip(
            self.menu_manager.player_fleet.backups,
            self.menu_manager.encounter_menu.backup_fleet_slots,
        ):
            if shipgirl is not None:
                shipgirl.rect.center = slot.center
                shipgirl.sprite.set_animation(Live2D.IDLE_ANIMATION)
                shipgirl.facing_left = False

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
        for event in events:
            if event.type == pygame.MOUSEMOTION:
                self.exit_fleet_selection_menu_button.hover(event.pos)
                self.start_sortie_button.hover(event.pos)
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
                click = (
                    click
                    or self.start_sortie_button.click(event.pos)
                    or self.exit_fleet_selection_menu_button.click(event.pos)
                )

                if click:
                    DataFiles.sfx["click"].play()

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
        mpos = pygame.mouse.get_pos()

        for point, angle in self.path:
            dash_offset = get_vec(self.PATH_DASH_LENGTH / 2, angle)
            dash_width_offset = get_vec(self.PATH_DASH_WIDTH / 2, angle + math.radians(90))
            dash_polygon = [
                point + dash_offset + dash_width_offset,
                point - dash_offset + dash_width_offset,
                point - dash_offset - dash_width_offset,
                point + dash_offset - dash_width_offset,
            ]
            pygame.draw.polygon(
                surface,
                Color.WHITE,
                dash_polygon
            )

        self.draw_path_hexes(surface)

        # self.background.draw_markings(surface, font_registry)
        
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

        self.start_sortie_button.draw(surface, font_registry)
        self.exit_fleet_selection_menu_button.draw(surface, font_registry)

        if self.mouse_start_drag is not None:
            pygame.draw.line(surface, Color.WHITE, self.mouse_start_drag, mpos, width=Box.OUTLINE_WIDTH)
