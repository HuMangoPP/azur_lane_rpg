import pygame

from engine.util import get_rect, pixel_to_hex, hex_to_pixel, get_cluster_edges
from engine.button import Button

from src.constants import DataFiles, Color, Box, TOP_OF_SCREEN, RIGHT_OF_SCREEN, screen_x, screen_y

class SortieNode:
    SIZE = 50
    CENTER = pygame.Vector2(screen_x(0.25), screen_y(0.5))

    def __init__(self, index, hexes):
        self.index = index
        self.hexes = [tuple(h) for h in hexes]
        self.unlocked = self.index <= DataFiles.save_file["sortie_progress"]
        self.cleared = self.index < DataFiles.save_file["sortie_progress"]
        self.hovered = False
    
    def hover(self, mouse_pos):
        mouse_x, mouse_y = mouse_pos
        hx, hy = pixel_to_hex(mouse_x - self.CENTER.x, mouse_y - self.CENTER.y, self.SIZE)
        self.hovered = self.unlocked and (hx, hy) in self.hexes

    def select(self, menu_manager, mouse_pos):
        if not self.unlocked:
            return

        mouse_x, mouse_y = mouse_pos
        hx, hy = pixel_to_hex(mouse_x - self.CENTER.x, mouse_y - self.CENTER.y, self.SIZE)
        if (hx, hy) not in self.hexes:
            return
            
        menu_manager.current_menu = menu_manager.fleet_selection_menu
        menu_manager.encounter_menu.current_sortie = self.index
        menu_manager.encounter_menu.current_encounter = 0
        menu_manager.player_fleet.clear_fleet()
        menu_manager.siren_fleet.clear_fleet()

    def draw(self, surface, font):
        if self.cleared:
            color = Color.BLUE_GREY
        elif self.unlocked:
            color = Color.DARK_BLUE
        else:
            color = Color.BLACK
        polygon = get_cluster_edges(self.hexes, self.SIZE)
        polygon = [pygame.Vector2(point) + self.CENTER for point in polygon]
        pygame.draw.polygon(surface, color, polygon)
        outline_width = (2 if self.hovered else 1) * Box.OUTLINE_WIDTH
        pygame.draw.polygon(surface, Color.WHITE, polygon, width=outline_width)

        for q, r in self.hexes:
            x, y = hex_to_pixel(q, r, self.SIZE)
            font.render(surface, str(self.index), pygame.Vector2(x, y) + self.CENTER, Color.WHITE, 1, style="center", outline_color=Color.BLACK)


class SortieSelectionMenu:
    def __init__(self, menu_manager):
        self.menu_manager = menu_manager

        self.sortie_nodes = [
            SortieNode(sortie_index, sortie_info["coordinates"])
            for sortie_index, sortie_info in enumerate(DataFiles.sortie_data)
        ]

        def exit_sortie_selection_menu():
            self.menu_manager.current_menu = self.menu_manager.port_menu

        self.exit_sortie_selection_menu_button = Button(
            rect=get_rect(width=2*Box.WIDTH, height=Box.HEIGHT, right=RIGHT_OF_SCREEN, top=TOP_OF_SCREEN),
            color=Color.BLUE_GREY,
            text="go back",
            text_color=Color.WHITE,
            callback=exit_sortie_selection_menu
        )

    def update(self, dt, events):
        for event in events:
            if event.type == pygame.MOUSEBUTTONUP:
                self.exit_sortie_selection_menu_button.click(event.pos)

                for sortie_node in self.sortie_nodes:
                    sortie_node.select(self.menu_manager, event.pos)
            if event.type == pygame.MOUSEMOTION:
                for sortie_node in self.sortie_nodes:
                    sortie_node.hover(event.pos)

    def draw(self, surface, font):
        self.exit_sortie_selection_menu_button.draw(surface, font)

        for sortie_node in self.sortie_nodes:
            sortie_node.draw(surface, font)
