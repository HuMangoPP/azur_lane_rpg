import math
import pygame
import random

from engine.util import get_rect, get_vec
from engine.button import Button

from src.constants import DataFiles, Color, Box, screen_x, screen_y
from src.menus.quests_data import first_sortie_quest
from src.menus.sortie_selection_menu import ChapterNameRibbon, Background

from live2d.live2d import Live2D


class FleetNameRibbon(ChapterNameRibbon):
    def __init__(self, text, position):
        self.text = text
        self.position = pygame.Vector2(position)

    def get_rect(self, font_registry):
        width = self.get_width(font_registry)
        height = DataFiles.sprites["sortie_selection"]["name_middle"].get_height()
        return get_rect(width=width, height=height, center=self.position)


class FleetSelectionMenu:
    Y_ALIGN = screen_y(0.33)

    def __init__(self, menu_manager):
        self.menu_manager = menu_manager

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
                centerx=screen_x(0.25) - (slot_index-1)*slot_size/4,
                centery=self.Y_ALIGN + (slot_index-1)*(slot_size + Box.PADDING)
            ) for slot_index in range(3)
        ]
        self.backup_fleet_slots = [
            get_rect(
                width=slot_size, height=slot_size,
                centerx=slot.centerx - 1.5*slot_size,
                centery=slot.centery,
            ) for slot in self.fleet_slots
        ]

        banner_height = DataFiles.sprites["sortie_selection"]["name_middle"].get_height()
        self.primary_fleet_ribbon = FleetNameRibbon(
            "primary",
            (self.fleet_slots[1].centerx, self.fleet_slots[-1].bottom + Box.PADDING + banner_height / 2)
        )
        self.backup_fleet_ribbon = FleetNameRibbon(
            "backup",
            (self.backup_fleet_slots[1].centerx, self.backup_fleet_slots[-1].bottom + Box.PADDING + banner_height / 2)
        )

        self.path = None

        self.background = Background()

    def generate_path(self, sortie_index):
        num_encounters = len(DataFiles.sortie_data[sortie_index]["encounters"])
        scale = math.radians(random.randint(180, 359))
        offset = math.radians(random.randint(0, 359))

        self.path = (num_encounters, scale, offset)

    def draw_tray_overlay(self, surface, font_registry):
        pygame.draw.rect(surface, Color.CARGO_BOX_BACK, self.tray_overlay)

        for shipgirl, rect in zip(self.menu_manager.available_shipgirls, self.available_shipgirl_rects):
            portrait = DataFiles.get_entity_sprite(shipgirl.name)
            portrait_rect = portrait.get_rect()
            portrait_rect.center = rect.center
            surface.blit(portrait, portrait_rect)
            pygame.draw.rect(surface, Color.WHITE, rect, width=Box.OUTLINE_WIDTH)

    def _drop_shipgirl(self, slot_shipgirls, portrait_slots, shipgirl_slots, event):
        for i, slot in enumerate(portrait_slots):
            if not slot.collidepoint(event.pos):
                continue
            if self.selected_shipgirl_index_from_fleet is not None:
                self.menu_manager.player_fleet.shipgirls[self.selected_shipgirl_index_from_fleet] = slot_shipgirls[i]
                if slot_shipgirls[i] is not None:
                    slot_shipgirls[i].rect.center = (
                        self.menu_manager.encounter_menu.fleet_slots[self.selected_shipgirl_index_from_fleet].center
                    )
            if self.selected_shipgirl_index_from_backup is not None:
                self.menu_manager.player_fleet.backups[self.selected_shipgirl_index_from_backup] = slot_shipgirls[i]
                if slot_shipgirls[i] is not None:
                    slot_shipgirls[i].rect.center = (
                        self.menu_manager.encounter_menu.backup_fleet_slots[self.selected_shipgirl_index_from_backup].center
                    )
            slot_shipgirls[i] = self.selected_shipgirl
            self.selected_shipgirl.rect.center = shipgirl_slots[i].center
            self.selected_shipgirl.sprite.set_animation(Live2D.IDLE_ANIMATION)
            self.selected_shipgirl.facing_left = False
            self.selected_shipgirl = None
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
                        self.menu_manager.encounter_menu.fleet_slots,
                        event
                    )
                    click = click or self._drop_shipgirl(
                        self.menu_manager.player_fleet.backups,
                        self.backup_fleet_slots,
                        self.menu_manager.encounter_menu.backup_fleet_slots,
                        event
                    )
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

    def draw(self, surface, font_registry):
        self.background.draw(surface)

        if self.path is not None:
            num_encounters, scale, offset = self.path
            startx = screen_x(0.5)
            endx = screen_x(0.8)
            num_dots = 30
            for i in range(num_dots):
                t = i / (num_dots-1) * 2 - 0.5
                s = math.sin(scale*t + offset)
                pygame.draw.circle(
                    surface, Color.WHITE,
                    ((endx-startx)*t + startx, screen_y(0.2)*s + self.Y_ALIGN),
                    4,
                )

            for i in range(num_encounters):
                t = i / (num_encounters-1)
                s = math.sin(scale*t + offset)
                icon = DataFiles.sprites["user_interface"]["uncleared"]
                icon_rect = icon.get_rect()
                icon_rect.centerx = (endx-startx)*t + startx
                icon_rect.centery = screen_y(0.2)*s + self.Y_ALIGN
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
            if shipgirl is not None:
                portrait = pygame.transform.flip(DataFiles.get_entity_sprite(shipgirl.name), flip_x=True, flip_y=False)
                portrait_rect = portrait.get_rect()
                portrait_rect.center = slot.center
                surface.blit(portrait, portrait_rect)
            pygame.draw.rect(surface, Color.WHITE, slot, width=Box.OUTLINE_WIDTH)
        
        self.backup_fleet_ribbon.draw(surface, font_registry)
        self.primary_fleet_ribbon.draw(surface, font_registry)

        self.draw_tray_overlay(surface, font_registry)

        self.start_sortie_button.draw(surface, font_registry)
        self.exit_fleet_selection_menu_button.draw(surface, font_registry)
        
        self.background.draw_markings(surface, font_registry)

        mpos = pygame.mouse.get_pos()
        if self.mouse_start_drag is not None:
            pygame.draw.line(surface, Color.WHITE, self.mouse_start_drag, mpos, width=Box.OUTLINE_WIDTH)
