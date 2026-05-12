import math
import random
import pygame

from engine.util import get_rect
from engine.button import Button

from src.constants import DataFiles, Color, Box, screen_x, screen_y
from src.menus.quests_data import first_sortie_quest

from live2d.live2d import Live2D

class FleetSelectionMenu:
    SLOT_SIZE = 96 # TODO

    def __init__(self, menu_manager):
        self.menu_manager = menu_manager

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
            }
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
            }
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
                centerx=-slot_index*self.SLOT_SIZE+self.fleet_slots[-1].centerx,
                bottom=self.fleet_slots[0].top-2*Box.PADDING
            ) for slot_index in range(num_fleet_slots)
        ]

    def update(self, dt, events):
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN:
                self.selected_shipgirl = None
                self.mouse_start_drag = None
                self.selected_shipgirl_index_from_fleet = None
                self.selected_shipgirl_index_from_backup = None
                for shipgirl, rect in zip(self.menu_manager.available_shipgirls, self.menu_manager.available_shipgirl_rects):
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
                if self.selected_shipgirl is not None:
                    for i, slot in enumerate(self.fleet_slots):
                        if not slot.collidepoint(event.pos):
                            continue
                        if self.selected_shipgirl_index_from_fleet is not None:
                            self.menu_manager.player_fleet.shipgirls[self.selected_shipgirl_index_from_fleet] = self.menu_manager.player_fleet.shipgirls[i]
                            if self.menu_manager.player_fleet.shipgirls[self.selected_shipgirl_index_from_fleet] is not None:
                                self.menu_manager.player_fleet.shipgirls[self.selected_shipgirl_index_from_fleet].rect.center = self.fleet_slots[self.selected_shipgirl_index_from_fleet].center
                        if self.selected_shipgirl_index_from_backup is not None:
                            self.menu_manager.player_fleet.backups[self.selected_shipgirl_index_from_backup] = self.menu_manager.player_fleet.shipgirls[i]
                            if self.menu_manager.player_fleet.backups[self.selected_shipgirl_index_from_backup] is not None:
                                self.menu_manager.player_fleet.backups[self.selected_shipgirl_index_from_backup].rect.center = self.backup_fleet_slots[self.selected_shipgirl_index_from_backup].center
                        self.menu_manager.player_fleet.shipgirls[i] = self.selected_shipgirl
                        self.selected_shipgirl.rect.center = self.fleet_slots[i].center
                        if self.selected_shipgirl.sprite is not None:
                            self.selected_shipgirl.sprite.set_animation(Live2D.IDLE_ANIMATION)
                            self.selected_shipgirl.facing_left = False
                        self.selected_shipgirl = None
                if self.selected_shipgirl is not None:
                    for i, slot in enumerate(self.backup_fleet_slots):
                        if not slot.collidepoint(event.pos):
                            continue
                        if self.selected_shipgirl_index_from_fleet is not None:
                            self.menu_manager.player_fleet.shipgirls[self.selected_shipgirl_index_from_fleet] = self.menu_manager.player_fleet.backups[i]
                            if self.menu_manager.player_fleet.shipgirls[self.selected_shipgirl_index_from_fleet] is not None:
                                self.menu_manager.player_fleet.shipgirls[self.selected_shipgirl_index_from_fleet].rect.center = self.fleet_slots[self.selected_shipgirl_index_from_fleet].center
                        if self.selected_shipgirl_index_from_backup is not None:
                            self.menu_manager.player_fleet.backups[self.selected_shipgirl_index_from_backup] = self.menu_manager.player_fleet.backups[i]
                            if self.menu_manager.player_fleet.backups[self.selected_shipgirl_index_from_backup] is not None:
                                self.menu_manager.player_fleet.backups[self.selected_shipgirl_index_from_backup].rect.center = self.backup_fleet_slots[self.selected_shipgirl_index_from_backup].center
                        self.menu_manager.player_fleet.backups[i] = self.selected_shipgirl
                        self.selected_shipgirl.rect.center = self.backup_fleet_slots[i].center
                        if self.selected_shipgirl.sprite is not None:
                            self.selected_shipgirl.sprite.set_animation(Live2D.IDLE_ANIMATION)
                            self.selected_shipgirl.facing_left = False
                        self.selected_shipgirl = None

                self.mouse_start_drag = None
                self.start_sortie_button.click(event.pos)
                self.exit_fleet_selection_menu_button.click(event.pos)

        if first_sortie_quest.quest_id in self.menu_manager.quest_manager.started_quests:
            self.start_sortie_button.active = self.menu_manager.player_fleet.primary_fleet_size > 1
        else:
            self.start_sortie_button.active = self.menu_manager.player_fleet.primary_fleet_size > 0

        for shipgirl in self.menu_manager.player_fleet.fleet:
            if shipgirl is not None:
                shipgirl.animate(dt)

        self.menu_manager.background.update(dt)

    def draw(self, surface, font):
        self.menu_manager.background.draw(surface, font, player_fleet=self.menu_manager.player_fleet)

        self.start_sortie_button.draw(surface, font)
        self.exit_fleet_selection_menu_button.draw(surface, font)

        for shipgirl, rect in zip(self.menu_manager.available_shipgirls, self.menu_manager.available_shipgirl_rects):
            pygame.draw.rect(surface, Color.WHITE, rect, width=Box.OUTLINE_WIDTH)
            if shipgirl.name in DataFiles.sprites["entity"]:
                portrait = DataFiles.sprites["entity"][shipgirl.name]
                portrait_rect = portrait.get_rect()
                portrait_rect.center = rect.center
                surface.blit(portrait, portrait_rect)
            else:
                font.render(surface, shipgirl.name, rect.center, Color.WHITE, 1, style="center")

        for slot, shipgirl in zip(self.fleet_slots, self.menu_manager.player_fleet.shipgirls):
            if shipgirl is None:
                pygame.draw.rect(surface, Color.WHITE, slot, width=Box.OUTLINE_WIDTH)
        
        for slot, shipgirl in zip(self.backup_fleet_slots, self.menu_manager.player_fleet.backups):
            if shipgirl is None:
                pygame.draw.rect(surface, Color.WHITE, slot, width=Box.OUTLINE_WIDTH)
        
        mpos = pygame.mouse.get_pos()
        if self.mouse_start_drag is not None:
            pygame.draw.line(surface, Color.WHITE, self.mouse_start_drag, mpos, width=Box.OUTLINE_WIDTH)
