import pygame

from engine.util import get_rect
from engine.button import Button

from src.constants import DataFiles, Color, Box, RIGHT_OF_SCREEN, TOP_OF_SCREEN, BOTTOM_OF_SCREEN, screen_x, screen_y

from live2d.live2d import Live2D

class FleetSelectionMenu:
    def __init__(self, menu_manager):
        self.menu_manager = menu_manager

        self.selected_shipgirl = None
        def start_sortie():
            if all(shipgirl is None for shipgirl in self.menu_manager.player_fleet.shipgirls):
                return
            self.menu_manager.current_menu = self.menu_manager.encounter_menu
            
            self.menu_manager.player_fleet.begin_sortie()
            self.menu_manager.encounter_menu.begin_sortie()

        self.start_sortie_button = Button(
            rect=get_rect(width=2*Box.WIDTH, height=Box.HEIGHT, centerx=screen_x(0.75), bottom=BOTTOM_OF_SCREEN),
            color=Color.BLUE_GREY,
            text="start",
            text_color=Color.WHITE,
            callback=start_sortie,
            active=False
        )

        def exit_fleet_selection_menu():
            self.menu_manager.current_menu = self.menu_manager.sortie_selection_menu
        
        self.exit_fleet_selection_menu_button = Button(
            rect=get_rect(width=2*Box.WIDTH, height=Box.HEIGHT, right=RIGHT_OF_SCREEN, top=TOP_OF_SCREEN),
            color=Color.BLUE_GREY,
            text="go back",
            text_color=Color.WHITE,
            callback=exit_fleet_selection_menu
        )

        num_fleet_slots = len(self.menu_manager.player_fleet.shipgirls)
        fleet_slot_offset = (num_fleet_slots-1)/2
        self.fleet_slots = [
            get_rect(
                width=Box.WIDTH, height=Box.HEIGHT,
                centerx=(fleet_slot_offset-slot_index)*(Box.WIDTH+Box.PADDING)+screen_x(0.25),
                centery=screen_y(0.5)
            ) for slot_index in range(num_fleet_slots)
        ]

    def update(self, dt, events):
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN:
                self.selected_shipgirl = None
                self.menu_manager.mouse_start_drag = None
                shipgirl_names = self.menu_manager.player_fleet.shipgirl_names
                for shipgirl, rect in zip(self.menu_manager.available_shipgirls, self.menu_manager.available_shipgirl_rects):
                    if rect.collidepoint(event.pos) and shipgirl.name not in shipgirl_names:
                        self.menu_manager.mouse_start_drag = event.pos
                        self.selected_shipgirl = shipgirl
                for shipgirl in self.menu_manager.player_fleet.shipgirls:
                    if shipgirl is not None and shipgirl.rect.collidepoint(event.pos):
                        self.menu_manager.mouse_start_drag = event.pos
                        self.selected_shipgirl = shipgirl
            if event.type == pygame.MOUSEBUTTONUP:
                mouse_end_drag = event.pos
                if self.menu_manager.mouse_start_drag is not None and self.selected_shipgirl is not None:
                    for i, slot in enumerate(self.fleet_slots):
                        if slot.collidepoint(mouse_end_drag):
                            for j, shipgirl in enumerate(self.menu_manager.player_fleet.shipgirls):
                                if self.selected_shipgirl == shipgirl:
                                    self.menu_manager.player_fleet.shipgirls[j] = self.menu_manager.player_fleet.shipgirls[i]
                                    if self.menu_manager.player_fleet.shipgirls[j] is not None:
                                        self.menu_manager.player_fleet.shipgirls[j].rect.center = pygame.Vector2(self.fleet_slots[j].center)
                                    break
                            self.menu_manager.player_fleet.shipgirls[i] = self.selected_shipgirl
                            self.selected_shipgirl.rect.center = pygame.Vector2(slot.center)
                            if self.selected_shipgirl.sprite is not None:
                                self.selected_shipgirl.sprite.set_animation(Live2D.IDLE_ANIMATION)
                                self.selected_shipgirl.facing_left = False
                            self.selected_shipgirl = None
                            break
                self.menu_manager.mouse_start_drag = None
                self.start_sortie_button.click(event.pos)
                self.exit_fleet_selection_menu_button.click(event.pos)
        
        if "first_sortie" in self.menu_manager.quest_manager.started_quests:
            self.start_sortie_button.active = len(self.menu_manager.player_fleet.shipgirl_names) > 1
        else:
            self.start_sortie_button.active = len(self.menu_manager.player_fleet.shipgirl_names) > 0

        for shipgirl in self.menu_manager.player_fleet.shipgirls:
            if shipgirl is not None:
                shipgirl.animate(dt)

    def draw(self, surface, font):
        self.menu_manager.player_fleet.draw(surface, font)
        self.start_sortie_button.draw(surface, font)
        self.exit_fleet_selection_menu_button.draw(surface, font)

        for shipgirl, rect in zip(self.menu_manager.available_shipgirls, self.menu_manager.available_shipgirl_rects):
            pygame.draw.rect(surface, Color.WHITE, rect, width=Box.OUTLINE_WIDTH)
            if shipgirl.name in DataFiles.sprites:
                portrait = DataFiles.sprites[shipgirl.name]
                portrait_rect = portrait.get_rect()
                portrait_rect.center = rect.center
                surface.blit(portrait, portrait_rect)
            else:
                font.render(surface, shipgirl.name, rect.center, Color.WHITE, 1, style="center", outline_color=Color.BLACK)

        for slot, shipgirl in zip(self.fleet_slots, self.menu_manager.player_fleet.shipgirls):
            if shipgirl is None:
                rect = get_rect(width=Box.WIDTH, height=Box.HEIGHT, centerx=slot.centerx, centery=slot.centery)
                pygame.draw.rect(surface, Color.WHITE, rect, width=Box.OUTLINE_WIDTH)
        
        mpos = pygame.mouse.get_pos()
        if self.menu_manager.mouse_start_drag is not None:
            pygame.draw.line(surface, Color.WHITE, self.menu_manager.mouse_start_drag, mpos, width=Box.OUTLINE_WIDTH)
