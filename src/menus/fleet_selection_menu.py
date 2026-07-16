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
    def __init__(self, text, position):
        self.text = text
        self.position = pygame.Vector2(position)

    def get_rect(self, font_registry):
        width = self.get_width(font_registry)
        height = DataFiles.sprites["sortie_selection"]["name_middle"].get_height()
        return get_rect(width=width, height=height, center=self.position)


class FleetSelectionMenu:
    Y_ALIGN = screen_y(0.3)
    PATH_DASH_LENGTH = 16
    PATH_DASH_WIDTH = 4
    TRAY_WOOD_COLOR = (116, 79, 52)
    TRAY_BEZEL_COLOR = (153, 108, 74)
    TRAY_WOOD_GRAIN_SEED = 1

    def __init__(self, menu_manager):
        self.menu_manager = menu_manager

        # TODO update tray styling
        num_rows = 2
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
            "primary",
            (self.primary_fleet_box.centerx, self.primary_fleet_box.bottom + Box.PADDING + banner_height / 2)
        )
        self.backup_fleet_ribbon = FleetNameRibbon(
            "backup",
            (self.backup_fleet_box.centerx, self.backup_fleet_box.bottom + Box.PADDING + banner_height / 2)
        )

        self.path = []
        self.path_hexes = []

        self.background = Background()

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

    def generate_path(self, sortie_index):
        num_encounters = len(DataFiles.sortie_data[sortie_index]["encounters"])
        encounter_counter = num_encounters
        radius = 48
        sign = random.choice([1, -1])
        straight_distance = random.uniform(10, 30)
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
                straight_distance = random.uniform(80, 150)
            else:
                straight_distance = random.uniform(20, 40)
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
                    self.selected_shipgirl = None
                if self.selected_shipgirl is not None:
                    for _, slot in zip(self.menu_manager.available_shipgirls, self.available_shipgirl_rects):
                        if not slot.collidepoint(event.pos):
                            continue
                        if self.selected_shipgirl_index_from_fleet is not None:
                            self.menu_manager.player_fleet.shipgirls[self.selected_shipgirl_index_from_fleet] = None
                        if self.selected_shipgirl_index_from_backup is not None:
                            self.menu_manager.player_fleet.backups[self.selected_shipgirl_index_from_backup] = None
                        self.selected_shipgirl = None
                        click = True

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

        for point in self.path_hexes:
            icon = DataFiles.sprites["user_interface"]["uncleared"]
            icon_rect = icon.get_rect()
            icon_rect.center = point
            glow = DataFiles.sprites["sortie_selection"]["locked_node_selection_glow"]
            glow_rect = glow.get_rect()
            glow_rect.midbottom = icon_rect.center
            surface.blit(glow, glow_rect, special_flags=pygame.BLEND_RGB_ADD)
            polygon = [pygame.Vector2(icon_rect.center) + get_vec(Box.WIDTH/2, math.radians(30 + i * 60)) for i in range(6)]
            pygame.draw.polygon(surface, Color.LOCKED_ZONE_FILL_HOVER, polygon)
            pygame.draw.polygon(surface, Color.WHITE, polygon, width=Box.OUTLINE_WIDTH)
            surface.blit(icon, icon_rect)

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
                marker_key = "blank" if slot.collidepoint(mpos) else shipgirl.name
                marker = DataFiles.sprites["fleet_selection"][marker_key]
                if marker_key != "blank":
                    marker = pygame.transform.flip(marker, flip_x=True, flip_y=False)
                marker_rect = marker.get_rect()
                marker_rect.center = slot.center
                surface.blit(marker, marker_rect)
                if marker_key == "blank":
                    shipgirl.draw(surface, font_registry)
            elif self.selected_shipgirl is not None:
                anchor_sprite = DataFiles.sprites["user_interface"]["start_sortie"]
                anchor_rect = anchor_sprite.get_rect()
                anchor_rect.center = slot.center
                surface.blit(anchor_sprite, anchor_rect)
        
        self._draw_dashed_rect(surface, self.backup_fleet_box)
        self._draw_dashed_rect(surface, self.primary_fleet_box)
        self.backup_fleet_ribbon.draw(surface, font_registry)
        self.primary_fleet_ribbon.draw(surface, font_registry)

        self.draw_tray_overlay(surface, font_registry)

        self.start_sortie_button.draw(surface, font_registry)
        self.exit_fleet_selection_menu_button.draw(surface, font_registry)
        
        self.background.draw_markings(surface, font_registry)

        if self.mouse_start_drag is not None:
            pygame.draw.line(surface, Color.WHITE, self.mouse_start_drag, mpos, width=Box.OUTLINE_WIDTH)
