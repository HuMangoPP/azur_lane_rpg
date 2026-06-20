import math
import random
import pygame

from engine.util import get_rect, pixel_to_hex, hex_to_pixel, get_cluster_edges
from engine.button import Button

from src.constants import DataFiles, Color, Box, screen_x, screen_y

class SortieNode:
    SIZE = 32
    center = pygame.Vector2(screen_x(0.15), screen_y(0.75))

    def __init__(self, index, sortie_info):
        self.chapter = sortie_info["chapter"]
        self.index = index
        self.hexes = [tuple(h) for h in sortie_info["coordinates"]]
        self.unlocked = self.index <= DataFiles.save_file["sortie_progress"]
        self.cleared = self.index < DataFiles.save_file["sortie_progress"]
        self.hovered = False

        cluster_edges = get_cluster_edges(self.hexes, self.SIZE)
        self.polygon = [pygame.Vector2(point) for point in cluster_edges]

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

    def draw_shadow(self, surface):
        polygon = [
            point + self.center + pygame.Vector2(self.SIZE/4,self.SIZE/2)
            for point in self.polygon
        ]
        pygame.draw.polygon(surface, Color.OCEAN_SHADOW, polygon)

    def draw(self, surface):
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

        polygon = [point + self.center for point in self.polygon]
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

class Fog:
    def __init__(self, sortie_nodes, disperse=False):
        self.centroids = []
        for sortie_node in sortie_nodes:
            for q, r in sortie_node.hexes:
                x, y = hex_to_pixel(q, r, sortie_node.SIZE)
                self.centroids.append(pygame.Vector2(x, y))
        self.cloud_indices = [random.randint(4, 9) for _ in self.centroids]
        self.cloud_sprites = {
            cloud_index: DataFiles.sprites["background"][f"cloud{cloud_index}"].copy()
            for cloud_index in [4,5,6,7,8,9]
        }
        self.cloud_shadow_sprites = {
            cloud_index: DataFiles.sprites["background"][f"cloud_shadow{cloud_index}"]
            for cloud_index in [4,5,6,7,8,9]
        }
        self.disperse = disperse
        self.disperse_timer = 1

        self.cloud_timers = [
            math.radians(360)*random.random()
            for _ in self.centroids
        ]
    
    def update(self, dt):
        if self.disperse_timer <= 0:
            return
        
        self.cloud_timers = [
            (cloud_timer + dt)%math.radians(360)
            for cloud_timer in self.cloud_timers
        ]
        if self.disperse:
            if self.disperse_timer == 1:
                wind_sfx = DataFiles.sfx["wind"]
                wind_sfx.play()
                wind_sfx.fadeout(3000)
            self.disperse_timer = max(0, self.disperse_timer - 1/3*dt)

    def draw(self, surface):
        if self.disperse_timer <= 0:
            return
        
        if self.disperse_timer < 1:
            cloud_alpha = int(255*self.disperse_timer)
            for cloud_sprite in self.cloud_sprites.values():
                cloud_sprite.set_alpha(cloud_alpha)

        for centroid, cloud_index, cloud_timer in zip(self.centroids, self.cloud_indices, self.cloud_timers):
            center = (
                centroid
                + SortieNode.center
                + pygame.Vector2(16*math.sin(cloud_timer), 4*math.sin(2*cloud_timer))
            )

            if self.disperse_timer >= 1:
                cloud_shadow_sprite = self.cloud_shadow_sprites[cloud_index]
                cloud_shadow_rect = cloud_shadow_sprite.get_rect()
                cloud_shadow_rect.center = center + pygame.Vector2(8, 8)
                surface.blit(cloud_shadow_sprite, cloud_shadow_rect, special_flags=pygame.BLEND_RGB_SUB)

            cloud_sprite = self.cloud_sprites[cloud_index]
            cloud_rect = cloud_sprite.get_rect()
            cloud_rect.center = center
            surface.blit(cloud_sprite, cloud_rect)

class SortieSelectionMenu:
    def __init__(self, menu_manager):
        self.menu_manager = menu_manager

        self.mousedown = False

        self.selected_sortie_node = None
        self.sortie_nodes = [
            SortieNode(sortie_index, sortie_info)
            for sortie_index, sortie_info in enumerate(DataFiles.sortie_data)
        ]

        num_rect_rows = 1
        num_rects_in_row = 3
        panel_width = Box.PADDING + num_rects_in_row*(Box.WIDTH+Box.PADDING)
        font_height = 9
        panel_height = (
            2*Box.PADDING + 2*font_height
            + 2*Box.PADDING + font_height
            + num_rect_rows*(Box.HEIGHT+Box.PADDING)
            + Box.HEIGHT+Box.PADDING
        )
        self.selected_sortie_info_panel = get_rect(width=panel_width, height=panel_height, left=0, top=0)

        def start_sortie():
            self.menu_manager.current_menu = self.menu_manager.fleet_selection_menu
            self.menu_manager.encounter_menu.current_sortie = self.selected_sortie_node.index
            self.menu_manager.encounter_menu.current_encounter = 0
            self.menu_manager.player_fleet.clear_fleet()
            self.menu_manager.siren_fleet.clear_fleet()

            self.selected_sortie_node = None
            self.start_sortie_button.active = False
        
        self.start_sortie_button = Button(
            get_rect(width=2*Box.WIDTH, height=Box.HEIGHT, top=0, left=0),
            start_sortie,
            active=False,
            background_styling={
                "background_color": Color.BLACK,
                "background_img": DataFiles.sprites["user_interface"]["start_sortie"],
                "background_img_align": (1/4, 1/2)
            },
            text_styling={
                "text": "sortie",
                "text_align": (2/3, 1/2),
                "text_color": Color.WHITE
            }
        )

        def exit_sortie_selection_menu():
            self.menu_manager.current_menu = self.menu_manager.port_menu
            DataFiles.sfx["waves"].fadeout(3000)

        button_sprite = DataFiles.sprites["user_interface"]["prev"]
        button_rect = get_rect(width=48,height=48,right=Box.RIGHT_OF_SCREEN,top=Box.TOP_OF_SCREEN)
        self.exit_sortie_selection_menu_button = Button(
            button_rect,
            exit_sortie_selection_menu,
            background_styling={
                "background_color": Color.BLACK,
                "background_img": button_sprite,
                "opacity": 160
            }
        )

        num_waves = DataFiles.sprites["sortie_selection"]["num_waves"]
        self.wave_ys = [
            screen_y(0.5) + 64*(i-(num_waves+2)/2)
            for i in range(num_waves)
        ]
        self.wave_timers = [
            math.radians(360)*random.random()
            for _ in range(num_waves)
        ]

        self.fogs = [
            Fog(
                [sortie_node for sortie_node in self.sortie_nodes if sortie_node.chapter == chapter],
                disperse=DataFiles.save_file["chapter_progress"] >= chapter
            )
            for chapter in range(3)
        ]
    def update(self, dt, events):
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.exit_sortie_selection_menu_button.rect.collidepoint(event.pos):
                    continue
                if self.start_sortie_button.rect.collidepoint(event.pos):
                    continue
                if self.selected_sortie_node is not None:
                    continue
                for sortie_node in self.sortie_nodes:
                    if sortie_node.select(event.pos):
                        break
                else:
                    self.mousedown = True
            if event.type == pygame.MOUSEMOTION:
                if self.mousedown and self.selected_sortie_node is None:
                    movement = pygame.Vector2(event.rel)
                    SortieNode.center += movement
            if event.type == pygame.MOUSEBUTTONUP:
                if self.mousedown:
                    self.mousedown = False
                    continue

                click = (
                    self.exit_sortie_selection_menu_button.click(event.pos)
                    or self.start_sortie_button.click(event.pos)
                )

                if self.selected_sortie_node is None:
                    for sortie_node in self.sortie_nodes:
                        if not sortie_node.select(event.pos):
                            continue
                        click = True
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

                        if sortie_node.cleared:
                            self.start_sortie_button.background_color = Color.CLEARED_ZONE_FILL
                        elif sortie_node.unlocked:
                            self.start_sortie_button.background_color = Color.UNCLEARED_ZONE_FILL
                        else:
                            self.start_sortie_button.background_color = Color.LOCKED_ZONE_FILL
                else:
                    if not self.selected_sortie_info_panel.collidepoint(event.pos):
                        self.selected_sortie_node = None
                        self.start_sortie_button.active = False

                if click:
                    DataFiles.sfx["click"].play()

            if event.type == pygame.MOUSEMOTION:
                for sortie_node in self.sortie_nodes:
                    sortie_node.hover(event.pos)

        num_waves = DataFiles.sprites["sortie_selection"]["num_waves"]
        self.wave_timers = [
            (wave_timer + (i+1)/num_waves*dt)%math.radians(360)
            for i, wave_timer in enumerate(self.wave_timers)
        ]

        for fog in self.fogs:
            fog.update(dt)

    def draw(self, surface, font):
        num_wave_reps = 5
        wave_rep_offset = (num_wave_reps-1)/2
        for i, (wave_y, wave_timer) in enumerate(zip(self.wave_ys, self.wave_timers)):
            wave = DataFiles.sprites["sortie_selection"][f"wave{i}"]
            wave_rect = wave.get_rect()
            wave_rect.top = wave_y + 8 * math.sin(2*wave_timer)
            centerx = 64 * math.sin(wave_timer) + screen_x(0.5)
            for j in range(num_wave_reps):
                wave_rect.centerx = centerx + wave_rect.width * (j-wave_rep_offset)
                surface.blit(wave, wave_rect)

        self.exit_sortie_selection_menu_button.draw(surface, font)

        compass = DataFiles.sprites["user_interface"]["compass"]
        compass_rect = compass.get_rect()
        compass_rect.bottom = Box.BOTTOM_OF_SCREEN
        compass_rect.left = Box.LEFT_OF_SCREEN
        surface.blit(compass, compass_rect)

        for sortie_node in self.sortie_nodes:
            sortie_node.draw_shadow(surface)
        for sortie_node in self.sortie_nodes[::-1]:
            sortie_node.draw(surface)
        
        for fog in self.fogs:
            fog.draw(surface)
        
        if self.selected_sortie_node is not None:
            pygame.draw.rect(surface, Color.BLACK, self.selected_sortie_info_panel)
            title_card_rect = get_rect(
                width=self.selected_sortie_info_panel.width,
                height=2*font.font_height + 2*Box.PADDING,
                left=self.selected_sortie_info_panel.left,
                top=self.selected_sortie_info_panel.top
            )
            if self.selected_sortie_node.cleared:
                title_card_color = Color.CLEARED_ZONE_FILL
            elif self.selected_sortie_node.unlocked:
                title_card_color = Color.UNCLEARED_ZONE_FILL
            else:
                title_card_color = Color.LOCKED_ZONE_FILL
            pygame.draw.rect(surface, title_card_color, title_card_rect)
            self.start_sortie_button.draw(surface, font)
            font.render(
                surface,
                f"zone {self.selected_sortie_node.index + 1}",
                title_card_rect.center,
                Color.WHITE,
                2,
                style="center",
            )

            font.render(
                surface,
                "rewards",
                (self.selected_sortie_info_panel.left + Box.PADDING, title_card_rect.bottom + Box.PADDING),
                Color.WHITE,
                1,
                style="topleft",
            )

            rewards = DataFiles.sortie_data[self.selected_sortie_node.index]["rewards"]
            for i, reward in enumerate(rewards):
                rect = get_rect(
                    width=Box.WIDTH, height=Box.HEIGHT,
                    left=self.selected_sortie_info_panel.left + Box.PADDING + (i%3)*(Box.WIDTH+Box.PADDING),
                    top=title_card_rect.bottom + 2*Box.PADDING + font.font_height + (i//3)*(Box.HEIGHT+Box.PADDING)
                )
                pygame.draw.rect(surface, Color.WHITE, rect, width=Box.OUTLINE_WIDTH)
                surface.blit(DataFiles.get_entity_sprite(reward), rect)
