import math
import random
import pygame

from engine.util import get_rect, pixel_to_hex, hex_to_pixel, get_cluster_edges
from engine.button import Button

from src.constants import DataFiles, Color, Box, screen_x, screen_y
from src.menus.background import Background

class SortieNode:
    SIZE = 32
    center = pygame.Vector2(screen_x(0.5), screen_y(0.5))

    def __init__(self, index, hexes):
        self.index = index
        self.hexes = [tuple(h) for h in hexes]
        self.unlocked = self.index <= DataFiles.save_file["sortie_progress"]
        self.cleared = self.index < DataFiles.save_file["sortie_progress"]
        self.hovered = False
    
    def hover(self, mouse_pos):
        mouse_x, mouse_y = mouse_pos
        hx, hy = pixel_to_hex(mouse_x - self.center.x, mouse_y - self.center.y, self.SIZE)
        self.hovered = self.unlocked and (hx, hy) in self.hexes

    def select(self, mouse_pos):
        if not self.unlocked:
            return False

        mouse_x, mouse_y = mouse_pos
        hx, hy = pixel_to_hex(mouse_x - self.center.x, mouse_y - self.center.y, self.SIZE)
        if (hx, hy) not in self.hexes:
            return False
        
        return True

    def draw(self, surface, font):
        if self.cleared:
            fill = Color.CLEARED_ZONE_FILL
            outline = Color.CLEARED_ZONE_OUTLINE
            glow = Color.CLEARED_ZONE_GLOW
            icon = DataFiles.sprites["user_interface"]["cleared"]
        elif self.unlocked:
            fill = Color.UNCLEARED_ZONE_FILL
            outline = Color.UNCLEARED_ZONE_OUTLINE
            glow = Color.UNCLEARED_ZONE_GLOW
            icon = DataFiles.sprites["user_interface"]["uncleared"]
        else:
            fill = Color.LOCKED_ZONE_FILL
            outline = Color.LOCKED_ZONE_OUTLINE
            glow = Color.LOCKED_ZONE_GLOW
            icon = DataFiles.sprites["user_interface"]["locked"]

        polygon = get_cluster_edges(self.hexes, self.SIZE)

        # shadow_polygon = [pygame.Vector2(point) + self.center + pygame.Vector2(self.SIZE/8,self.SIZE/4) for point in polygon]
        # pygame.draw.polygon(surface, Color.OCEAN_SHADOW, shadow_polygon)

        polygon = [pygame.Vector2(point) + self.center for point in polygon]
        pygame.draw.polygon(surface, fill, polygon)
        if self.hovered:
            pygame.draw.polygon(surface, outline, polygon, width=2*Box.OUTLINE_WIDTH)
            pygame.draw.polygon(surface, glow, polygon, width=Box.OUTLINE_WIDTH)
        else:
            pygame.draw.polygon(surface, outline, polygon, width=Box.OUTLINE_WIDTH)
        
        for q, r in self.hexes:
            x, y = hex_to_pixel(q, r, self.SIZE)
            icon_rect = icon.get_rect()
            icon_rect.center = pygame.Vector2(x,y) + self.center
            surface.blit(icon, icon_rect)

class SortieSelectionMenu:
    def __init__(self, menu_manager):
        self.menu_manager = menu_manager

        self.mousedown = False

        self.selected_sortie_node = None
        self.sortie_nodes = [
            SortieNode(sortie_index, sortie_info["coordinates"])
            for sortie_index, sortie_info in enumerate(DataFiles.sortie_data)
        ]

        num_rects = 6
        num_rects_in_row = 3
        panel_width = Box.PADDING + num_rects_in_row*(Box.WIDTH+Box.PADDING)
        reward_rect_start = 6*Box.PADDING
        panel_height = reward_rect_start + num_rects//num_rects_in_row*(Box.HEIGHT+Box.PADDING) + Box.HEIGHT+Box.PADDING
        self.selected_sortie_info_panel = get_rect(width=panel_width, height=panel_height, left=0, top=0)
        self.reward_rects = [
            get_rect(
                width=Box.WIDTH, height=Box.HEIGHT, 
                left=Box.PADDING + (Box.WIDTH+Box.PADDING) * (i%num_rects_in_row),
                top=reward_rect_start + (Box.HEIGHT+Box.PADDING) * (i//num_rects_in_row)
            ) for i in range(num_rects)
        ]

        def start_sortie():
            self.menu_manager.current_menu = self.menu_manager.fleet_selection_menu
            self.menu_manager.encounter_menu.current_sortie = self.selected_sortie_node.index
            self.menu_manager.encounter_menu.current_encounter = 0
            self.menu_manager.player_fleet.clear_fleet()
            self.menu_manager.siren_fleet.clear_fleet()

            self.selected_sortie_node = None
            self.start_sortie_button.active = False
        
        self.start_sortie_button = Button(
            rect=get_rect(width=2*Box.WIDTH, height=Box.HEIGHT, top=0, left=0),
            color=Color.BLUE_GREY,
            sprite=DataFiles.sprites["user_interface"]["start_sortie"],
            text="sortie",
            text_pos=(0.66,0.5),
            text_color=Color.WHITE,
            callback=start_sortie,
            active=False
        )

        def exit_sortie_selection_menu():
            self.menu_manager.current_menu = self.menu_manager.port_menu

        button_sprite = DataFiles.sprites["user_interface"]["prev"]
        button_rect = button_sprite.get_rect()
        button_rect.right = Box.RIGHT_OF_SCREEN
        button_rect.top = Box.TOP_OF_SCREEN
        self.exit_sortie_selection_menu_button = Button(rect=button_rect,sprite=button_sprite,callback=exit_sortie_selection_menu)

    def update(self, dt, events):
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN:
                self.mousedown = True
            if event.type == pygame.MOUSEMOTION:
                if self.mousedown and self.selected_sortie_node is None:
                    movement = pygame.Vector2(event.rel)
                    SortieNode.center += movement
            if event.type == pygame.MOUSEBUTTONUP:
                self.mousedown = False
                self.exit_sortie_selection_menu_button.click(event.pos)
                self.start_sortie_button.click(event.pos)

                if self.selected_sortie_node is None:
                    for sortie_node in self.sortie_nodes:
                        if not sortie_node.select(event.pos):
                            continue
                        self.selected_sortie_node = sortie_node

                        rx = -100 # get x value of rightmost hex
                        cy = 0 # get average y value of all hexes
                        n_hexes = len(sortie_node.hexes)
                        for q, r in sortie_node.hexes:
                            x, y = hex_to_pixel(q, r, SortieNode.SIZE)
                            if x > rx:
                                rx = x
                            cy += y / n_hexes
                            
                        self.selected_sortie_info_panel.left = rx + SortieNode.center.x + SortieNode.SIZE + Box.PADDING
                        self.selected_sortie_info_panel.centery = cy + SortieNode.center.y

                        self.start_sortie_button.active = True
                        self.start_sortie_button.rect.centerx = self.selected_sortie_info_panel.centerx
                        self.start_sortie_button.rect.bottom = self.selected_sortie_info_panel.bottom - Box.PADDING
                else:
                    if not self.selected_sortie_info_panel.collidepoint(event.pos):
                        self.selected_sortie_node = None
                        self.start_sortie_button.active = False

            if event.type == pygame.MOUSEMOTION:
                for sortie_node in self.sortie_nodes:
                    sortie_node.hover(event.pos)

        self.menu_manager.background.update(dt)

    def draw(self, surface, font):
        self.menu_manager.background.draw(surface, font)

        self.exit_sortie_selection_menu_button.draw(surface, font)

        compass = DataFiles.sprites["user_interface"]["compass"]
        compass_rect = compass.get_rect()
        compass_rect.bottom = Box.BOTTOM_OF_SCREEN
        compass_rect.left = Box.LEFT_OF_SCREEN
        surface.blit(compass, compass_rect)

        for sortie_node in self.sortie_nodes[::-1]:
            sortie_node.draw(surface, font)
        
        if self.selected_sortie_node is not None:
            pygame.draw.rect(surface, Color.DARK_BLUE, self.selected_sortie_info_panel)
            self.start_sortie_button.draw(surface, font)
            font.render(
                surface,
                f"zone {self.selected_sortie_node.index + 1}",
                (self.selected_sortie_info_panel.centerx, self.selected_sortie_info_panel.top + 2*Box.PADDING),
                Color.WHITE,
                2,
                style="center",
                outline_color=Color.BLACK
            )
            font.render(
                surface,
                "rewards",
                (self.selected_sortie_info_panel.left+Box.PADDING, self.selected_sortie_info_panel.top + 4*Box.PADDING),
                Color.WHITE,
                1,
                style="topleft",
                outline_color=Color.BLACK
            )

            rewards = DataFiles.sortie_data[self.selected_sortie_node.index]["rewards"]
            for reward, reward_rect in zip(rewards, self.reward_rects):
                rect = reward_rect.copy()
                rect.left = rect.left + self.selected_sortie_info_panel.left
                rect.top = rect.top + self.selected_sortie_info_panel.top
                pygame.draw.rect(surface, Color.WHITE, rect, width=Box.OUTLINE_WIDTH)
                if reward in DataFiles.sprites["entity"]:
                    surface.blit(DataFiles.sprites["entity"][reward], rect)
                else:
                    font.render(surface, reward, rect.center, Color.WHITE, 1, style="center", outline_color=Color.BLACK)
