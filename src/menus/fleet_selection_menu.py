import pygame

from engine.util import get_rect
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
    SLOT_SIZE = 96 # TODO

    def __init__(self, menu_manager):
        self.menu_manager = menu_manager

        num_rows = 3
        num_rects_in_row = 4
        self.dossier_overlay = get_rect(
            width=num_rects_in_row*(Box.WIDTH + Box.PADDING) + 4*Box.PADDING,
            height=num_rows*(Box.HEIGHT + Box.PADDING) + 3*Box.PADDING + Box.HEIGHT,
            right=Box.RIGHT_OF_SCREEN,
            centery=screen_y(0.5)
        )
        self.dossier_bg = get_rect(
            width=self.dossier_overlay.width,
            height=self.dossier_overlay.height - Box.HEIGHT,
            left=self.dossier_overlay.left,
            bottom=self.dossier_overlay.bottom
        )
        self.dossier_page = get_rect(
            width=self.dossier_bg.width - 2*Box.PADDING,
            height=self.dossier_bg.height - 2*Box.PADDING,
            center=self.dossier_bg.center
        )
        self.available_shipgirl_rects = [
            get_rect(
                width=Box.WIDTH, height=Box.HEIGHT,
                left=self.dossier_page.left+Box.PADDING+(i%num_rects_in_row)*(Box.WIDTH+Box.PADDING),
                top=self.dossier_page.top+Box.PADDING+(i//num_rects_in_row)*(Box.HEIGHT+Box.PADDING)
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

        num_fleet_slots = 3 # TODO
        fleet_slot_offset = (num_fleet_slots-1)/2
        self.fleet_slots = [
            get_rect(
                width=self.SLOT_SIZE, height=self.SLOT_SIZE,
                centerx=screen_x(0.25) + self.SLOT_SIZE - (slot_index-fleet_slot_offset)*self.SLOT_SIZE/2,
                centery=screen_y(0.5) + (slot_index-fleet_slot_offset)*self.SLOT_SIZE
            ) for slot_index in range(num_fleet_slots)
        ]

        self.backup_fleet_slots = [
            get_rect(
                width=self.SLOT_SIZE, height=self.SLOT_SIZE,
                centerx=slot.centerx - 2*self.SLOT_SIZE,
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

        self.background = Background()

    def draw_dossier_overlay(self, surface, font_registry):
        pygame.draw.rect(surface, Color.DOSSIER, self.dossier_bg)
        tab_rect = get_rect(
            width=48, height=32,
            left=self.dossier_bg.left,
            bottom=self.dossier_bg.top
        )
        tab_polygon = [
            tab_rect.bottomleft,
            tab_rect.topleft,
            tab_rect.topright,
            pygame.Vector2(tab_rect.bottomright) + pygame.Vector2(16, 0),
        ]
        pygame.draw.polygon(surface, Color.DOSSIER, tab_polygon)

        misaligned_pages = [
            (-5, pygame.Vector2(-8, 6), (224, 218, 201)),
            (4, pygame.Vector2(6, -4), (235, 229, 212)),
            (-2, pygame.Vector2(3, 5), (244, 239, 224)),
        ]
        for rotated_angle, offset, color in misaligned_pages:
            pygame.draw.polygon(
                surface,
                color,
                Box.get_rotated_rect_polygon(self.dossier_page, rotated_angle, offset)
            )

        sticky_tabs = [
            (-7, 46, "yellow"),
            (-5, 137, "green"),
            (-12, 183, "pink")
        ]
        for sticky_tab_offsetx, sticky_tab_offsety, sticky_tab_color in sticky_tabs:
            sticky_tab_sprite = DataFiles.sprites["props"][f"sticky_tab_{sticky_tab_color}"]
            sticky_tab_rect = sticky_tab_sprite.get_rect()
            sticky_tab_rect.centerx = self.dossier_page.left + sticky_tab_offsetx
            sticky_tab_rect.centery = self.dossier_page.top + sticky_tab_offsety
            surface.blit(sticky_tab_sprite, sticky_tab_rect)

        pygame.draw.rect(surface, Color.DOSSIER_PAGE, self.dossier_page)

        for shipgirl, rect in zip(self.menu_manager.available_shipgirls, self.available_shipgirl_rects):
            portrait = DataFiles.get_entity_sprite(shipgirl.name)
            portrait_rect = portrait.get_rect()
            portrait_rect.center = rect.center
            surface.blit(portrait, portrait_rect)
            pygame.draw.rect(surface, Color.BLACK, rect, width=Box.OUTLINE_WIDTH)

        paperclip_sprite = DataFiles.sprites["props"]["paperclip"]
        paperclip_rect = paperclip_sprite.get_rect()
        paperclip_rect.left = self.dossier_bg.left - 4 # TODO paper clip offset
        paperclip_rect.top = self.dossier_bg.top
        surface.blit(paperclip_sprite, paperclip_rect)

        classified_sprite = pygame.transform.scale_by(DataFiles.sprites["props"]["classified"], 1.5)
        classified_rect = classified_sprite.get_rect()
        classified_rect.topright = self.dossier_bg.topright
        surface.blit(classified_sprite, classified_rect)

        coffee_ring_sprite = pygame.transform.scale_by(DataFiles.sprites["props"]["coffee_ring"], 1.5)
        coffee_ring_rect = coffee_ring_sprite.get_rect()
        coffee_ring_rect.bottomleft = self.dossier_bg.bottomleft
        surface.blit(coffee_ring_sprite, coffee_ring_rect)

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

        self.background.update(dt)

    def draw(self, surface, font_registry):
        self.background.draw(surface)

        self.start_sortie_button.draw(surface, font_registry)
        self.exit_fleet_selection_menu_button.draw(surface, font_registry)
        self.backup_fleet_ribbon.draw(surface, font_registry)
        self.primary_fleet_ribbon.draw(surface, font_registry)

        self.draw_dossier_overlay(surface, font_registry)

        for slot, shipgirl in zip(self.fleet_slots, self.menu_manager.player_fleet.shipgirls):
            if shipgirl is None:
                pygame.draw.rect(surface, Color.WHITE, slot, width=Box.OUTLINE_WIDTH)
        
        for slot, shipgirl in zip(self.backup_fleet_slots, self.menu_manager.player_fleet.backups):
            if shipgirl is None:
                pygame.draw.rect(surface, Color.WHITE, slot, width=Box.OUTLINE_WIDTH)

        self.menu_manager.player_fleet.draw_shipgirl(surface, font_registry)
        
        self.background.draw_markings(surface, font_registry)

        mpos = pygame.mouse.get_pos()
        if self.mouse_start_drag is not None:
            pygame.draw.line(surface, Color.WHITE, self.mouse_start_drag, mpos, width=Box.OUTLINE_WIDTH)
