import math
import random
import pygame

from engine.util import get_rect
from engine.button import Button

from src.constants import DataFiles, Color, Box, screen_x, screen_y
from src.menus.quests_data import first_sortie_quest
from src.menus.sortie_selection_menu import ChapterNameRibbon

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
    SLOT_SIZE = 96 # TODO

    def __init__(self, menu_manager):
        self.menu_manager = menu_manager

        num_rows = 2
        num_rects_in_row = 4
        row_index_offset = (num_rects_in_row-1) / 2
        self.available_shipgirl_rects = [
            get_rect(
                width=Box.WIDTH, height=Box.HEIGHT,
                centerx=(Box.WIDTH+Box.PADDING)*(i%num_rects_in_row-row_index_offset) + screen_x(0.75),
                centery=(Box.HEIGHT+Box.PADDING)*(i//num_rects_in_row-row_index_offset) + screen_y(0.5)
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
            get_rect(width=2*Box.WIDTH, height=Box.HEIGHT, right=Box.RIGHT_OF_SCREEN, bottom=Box.BOTTOM_OF_SCREEN),
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

        num_fleet_slots = len(self.menu_manager.player_fleet.shipgirls)
        fleet_slot_offset = (num_fleet_slots-1)/2
        self.fleet_slots = [
            get_rect(
                width=self.SLOT_SIZE, height=self.SLOT_SIZE,
                centerx=(fleet_slot_offset-slot_index)*self.SLOT_SIZE+screen_x(0.33),
                centery=screen_y(0.5)
            ) for slot_index in range(num_fleet_slots)
        ]

        num_fleet_slots = len(self.menu_manager.player_fleet.backups)
        self.backup_fleet_slots = [
            get_rect(
                width=self.SLOT_SIZE, height=self.SLOT_SIZE,
                centerx=-slot_index*self.SLOT_SIZE+self.fleet_slots[1].centerx,
                bottom=self.fleet_slots[0].top-2*Box.PADDING
            ) for slot_index in range(num_fleet_slots)
        ]
        banner_height = DataFiles.sprites["sortie_selection"]["name_middle"].get_height()
        self.primary_fleet_ribbon = FleetNameRibbon(
            "primary fleet",
            (self.fleet_slots[1].centerx, self.fleet_slots[0].bottom + Box.PADDING + banner_height / 2)
        )
        self.backup_fleet_ribbon = FleetNameRibbon(
            "backup fleet",
            (self.backup_fleet_slots[1].centerx, self.backup_fleet_slots[0].top - Box.PADDING - banner_height / 2)
        )

    def _drop_shipgirl(self, slot_shipgirls, slots, event):
        for i, slot in enumerate(slots):
            if not slot.collidepoint(event.pos):
                continue
            if self.selected_shipgirl_index_from_fleet is not None:
                self.menu_manager.player_fleet.shipgirls[self.selected_shipgirl_index_from_fleet] = slot_shipgirls[i]
                if self.menu_manager.player_fleet.shipgirls[self.selected_shipgirl_index_from_fleet] is not None:
                    self.menu_manager.player_fleet.shipgirls[self.selected_shipgirl_index_from_fleet].rect.center = self.fleet_slots[self.selected_shipgirl_index_from_fleet].center
            if self.selected_shipgirl_index_from_backup is not None:
                self.menu_manager.player_fleet.backups[self.selected_shipgirl_index_from_backup] = slot_shipgirls[i]
                if self.menu_manager.player_fleet.backups[self.selected_shipgirl_index_from_backup] is not None:
                    self.menu_manager.player_fleet.backups[self.selected_shipgirl_index_from_backup].rect.center = self.backup_fleet_slots[self.selected_shipgirl_index_from_backup].center
            slot_shipgirls[i] = self.selected_shipgirl
            self.selected_shipgirl.rect.center = slots[i].center
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
                for i, shipgirl in enumerate(self.menu_manager.player_fleet.shipgirls):
                    if shipgirl is not None and shipgirl.rect.collidepoint(event.pos):
                        self.mouse_start_drag = event.pos
                        self.selected_shipgirl = shipgirl
                        self.selected_shipgirl_index_from_fleet = i
                for i, shipgirl in enumerate(self.menu_manager.player_fleet.backups):
                    if shipgirl is not None and shipgirl.rect.collidepoint(event.pos):
                        self.mouse_start_drag = event.pos
                        self.selected_shipgirl = shipgirl
                        self.selected_shipgirl_index_from_backup = i
            if event.type == pygame.MOUSEBUTTONUP:
                click = False
                if self.selected_shipgirl is not None:
                    click = self._drop_shipgirl(self.menu_manager.player_fleet.shipgirls, self.fleet_slots, event)
                    click = click or self._drop_shipgirl(self.menu_manager.player_fleet.backups, self.backup_fleet_slots, event)
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

        for shipgirl in self.menu_manager.player_fleet.fleet:
            if shipgirl is not None:
                shipgirl.animate(dt)

        self.menu_manager.background.update(dt)

    def draw(self, surface, font_registry):
        self.menu_manager.background.draw(surface, font_registry, player_fleet=self.menu_manager.player_fleet)

        self.start_sortie_button.draw(surface, font_registry)
        self.exit_fleet_selection_menu_button.draw(surface, font_registry)
        self.backup_fleet_ribbon.draw(surface, font_registry)
        self.primary_fleet_ribbon.draw(surface, font_registry)

        for shipgirl, rect in zip(self.menu_manager.available_shipgirls, self.available_shipgirl_rects):
            pygame.draw.rect(surface, Color.WHITE, rect, width=Box.OUTLINE_WIDTH)
            portrait = DataFiles.get_entity_sprite(shipgirl.name)
            portrait_rect = portrait.get_rect()
            portrait_rect.center = rect.center
            surface.blit(portrait, portrait_rect)

        for slot, shipgirl in zip(self.fleet_slots, self.menu_manager.player_fleet.shipgirls):
            if shipgirl is None:
                pygame.draw.rect(surface, Color.WHITE, slot, width=Box.OUTLINE_WIDTH)
        
        for slot, shipgirl in zip(self.backup_fleet_slots, self.menu_manager.player_fleet.backups):
            if shipgirl is None:
                pygame.draw.rect(surface, Color.WHITE, slot, width=Box.OUTLINE_WIDTH)
        
        mpos = pygame.mouse.get_pos()
        if self.mouse_start_drag is not None:
            pygame.draw.line(surface, Color.WHITE, self.mouse_start_drag, mpos, width=Box.OUTLINE_WIDTH)
