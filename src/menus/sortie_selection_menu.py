import math
import random
import pygame

from engine.util import get_rect, pixel_to_hex, hex_to_pixel, get_cluster_edges, adjacent_hexes
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

    def get_depth(self):
        return max(point.y for point in self.polygon)

    def get_styling(self):
        if self.cleared:
            return (
                Color.CLEARED_ZONE_FILL,
                Color.CLEARED_ZONE_OUTLINE,
                Color.CLEARED_ZONE_GLOW,
                DataFiles.sprites["user_interface"]["cleared"],
            )
        elif self.unlocked:
            fill = Color.UNCLEARED_ZONE_FILL
            outline = Color.UNCLEARED_ZONE_OUTLINE
            glow = Color.UNCLEARED_ZONE_GLOW
            if len(self.hexes) > 1:
                icon = DataFiles.sprites["user_interface"]["boss"]
            else:
                icon = DataFiles.sprites["user_interface"]["uncleared"]
            return fill, outline, glow, icon
        else:
            return (
                Color.LOCKED_ZONE_FILL,
                Color.LOCKED_ZONE_OUTLINE,
                Color.LOCKED_ZONE_GLOW,
                DataFiles.sprites["user_interface"]["locked"],
            )

    def get_selection_glow_sprite(self):
        if self.cleared:
            return DataFiles.sprites["sortie_selection"]["cleared_node_selection_glow"]
        elif self.unlocked:
            return DataFiles.sprites["sortie_selection"]["uncleared_node_selection_glow"]
        else:
            return DataFiles.sprites["sortie_selection"]["locked_node_selection_glow"]

    def draw(self, surface):
        fill, outline, _, icon = self.get_styling()
        polygon = [point + self.center for point in self.polygon]
        pygame.draw.polygon(surface, fill, polygon)
        pygame.draw.polygon(surface, outline, polygon, width=Box.OUTLINE_WIDTH)
        
        for q, r in self.hexes:
            x, y = hex_to_pixel(q, r, self.SIZE)
            icon_rect = icon.get_rect()
            icon_rect.center = pygame.Vector2(x,y) + self.center
            surface.blit(icon, icon_rect)

    def draw_hover_effect(self, surface):
        if not self.hovered:
            return

        _, outline, glow, _ = self.get_styling()
        polygon = [point + self.center for point in self.polygon]
        pygame.draw.polygon(surface, outline, polygon, width=2*Box.OUTLINE_WIDTH)
        pygame.draw.polygon(surface, glow, polygon, width=Box.OUTLINE_WIDTH)

    def draw_selection_effect(self, surface):
        glow = self.get_selection_glow_sprite()
        for q, r in self.hexes:
            x, y = hex_to_pixel(q, r, self.SIZE)
            glow_rect = glow.get_rect()
            glow_rect.midbottom = pygame.Vector2(x, y) + self.center
            surface.blit(glow, glow_rect, special_flags=pygame.BLEND_RGB_ADD)

        _, _, glow, icon = self.get_styling()
        polygon = [point + self.center for point in self.polygon]
        pygame.draw.polygon(surface, glow, polygon)
        
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
            math.radians(random.randint(0, 359))
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

class SortieProp:
    def __init__(self, sprite_key, position):
        self.sprite_key = sprite_key
        self.position = pygame.Vector2(position)
        self.sprite = DataFiles.sprites["sortie_selection"][sprite_key]

    def get_rect(self):
        rect = self.sprite.get_rect()
        rect.center = self.position + SortieNode.center
        return rect

    def get_depth(self):
        return self.position.y

    def draw(self, surface):
        surface.blit(self.sprite, self.get_rect())

class ChapterNameRibbon:
    PADDING_X = 24
    FONT_SCALE = 1

    def __init__(self, chapter, sortie_nodes):
        self.chapter = chapter
        self.text = f"chapter {chapter}"
        self.position = self.get_position(sortie_nodes)

    def get_position(self, sortie_nodes):
        hex_positions = []
        for sortie_node in sortie_nodes:
            for q, r in sortie_node.hexes:
                hex_positions.append(pygame.Vector2(hex_to_pixel(q, r, SortieNode.SIZE)))

        left = min(position.x for position in hex_positions)
        right = max(position.x for position in hex_positions)
        bottom = max(position.y for position in hex_positions)
        return pygame.Vector2((left + right) / 2, bottom + 3 * SortieNode.SIZE)

    def get_width(self, font_registry):
        left = DataFiles.sprites["sortie_selection"]["name_left"]
        right = DataFiles.sprites["sortie_selection"]["name_right"]
        middle = DataFiles.sprites["sortie_selection"]["name_middle"]
        text_width = font_registry["handwritten"].get_width(self.text, self.FONT_SCALE, 0) - Box.WIDTH
        middle_width = max(middle.get_width(), text_width + 2 * self.PADDING_X)
        return left.get_width() + middle_width + right.get_width()

    def get_rect(self, font_registry):
        width = self.get_width(font_registry)
        height = DataFiles.sprites["sortie_selection"]["name_middle"].get_height()
        return get_rect(width=width, height=height, center=self.position + SortieNode.center)

    def draw(self, surface, font_registry):
        left = DataFiles.sprites["sortie_selection"]["name_left"]
        middle = DataFiles.sprites["sortie_selection"]["name_middle"]
        right = DataFiles.sprites["sortie_selection"]["name_right"]
        rect = self.get_rect(font_registry)

        left_rect = left.get_rect(topleft=rect.topleft)
        surface.blit(left, left_rect)

        middle_rect = middle.get_rect()
        middle_rect.left = left_rect.right
        middle_rect.top = rect.top
        middle_right = rect.right - right.get_width()
        while middle_rect.left < middle_right:
            source_width = min(middle.get_width(), middle_right - middle_rect.left)
            source_rect = pygame.Rect(0, 0, source_width, middle.get_height())
            surface.blit(middle, middle_rect, source_rect)
            middle_rect.left += source_width

        right_rect = right.get_rect(topright=rect.topright)
        surface.blit(right, right_rect)

        text_pos = pygame.Vector2(rect.centerx, rect.centery)
        font_registry["handwritten"].render(surface, self.text, text_pos, Color.BLACK, self.FONT_SCALE, style="center")

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

            self.selected_sortie_node.hovered = False
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
            },
            hover_styling={"opacity": 200}
        )

        num_waves = DataFiles.sprites["sortie_selection"]["num_waves"]
        self.wave_ys = [
            screen_y(0.5) + 64*(i-(num_waves+2)/2)
            for i in range(num_waves)
        ]
        self.wave_timers = [
            math.radians(random.randint(0, 359))
            for _ in range(num_waves)
        ]
        self.chapter_name_ribbons = self.create_chapter_name_ribbons()
        self.sortie_props = self.create_sortie_props()

        self.fogs = [
            Fog(
                [sortie_node for sortie_node in self.sortie_nodes if sortie_node.chapter == chapter],
                disperse=DataFiles.save_file["chapter_progress"] >= chapter
            )
            for chapter in range(4)
        ]

    def get_chapters(self):
        return sorted({sortie_node.chapter for sortie_node in self.sortie_nodes})

    def create_chapter_name_ribbons(self):
        ribbons = []
        for chapter in self.get_chapters():
            chapter_nodes = [
                sortie_node for sortie_node in self.sortie_nodes
                if sortie_node.chapter == chapter
            ]
            if len(chapter_nodes) == 0:
                continue
            ribbons.append(ChapterNameRibbon(chapter, chapter_nodes))
        return ribbons

    def get_prop_count(self, num_nodes):
        if num_nodes <= 4:
            return 1
        if num_nodes <= 7:
            return 2
        if num_nodes <= 10:
            return 3
        return 4

    def create_sortie_props(self):
        occupied_hexes = set()
        for chapter in range(3): # TODO num chapters
            chapter_nodes = [
                sortie_node for sortie_node in self.sortie_nodes
                if sortie_node.chapter == chapter
            ]
            for sortie_node in chapter_nodes:
                occupied_hexes.update(sortie_node.hexes)
        
        sortie_props = []
        for chapter in range(3): # TODO num chapters
            chapter_nodes = [
                sortie_node for sortie_node in self.sortie_nodes
                if sortie_node.chapter == chapter
            ]

            if len(occupied_hexes) <= 1:
                continue

            rng = random.Random(f"sortie-selection-props-chapter-{chapter}")
            count = self.get_prop_count(len(chapter_nodes))
            prop_keys = ["lighthouse", "shipwreck"] + ["island"] * count + ["rocks"] * count

            candidate_hexes = set()
            for sortie_node in chapter_nodes:
                for q, r in sortie_node.hexes:
                    candidate_hexes |= adjacent_hexes(q, r, 2)
            candidate_hexes -= occupied_hexes
            candidate_hexes = sorted(candidate_hexes)

            rng.shuffle(prop_keys)
            rng.shuffle(candidate_hexes)
            for prop_key, (q, r) in zip(prop_keys, candidate_hexes):
                position = pygame.Vector2(hex_to_pixel(q, r, SortieNode.SIZE))
                sortie_props.append(SortieProp(prop_key, position))
                occupied_hexes.add((q, r))

        return sorted(sortie_props, key=lambda prop: prop.position.y)

    def draw_waves(self, surface):
        num_wave_reps = 5
        wave_rep_offset = (num_wave_reps - 1) / 2
        for i, (wave_y, wave_timer) in enumerate(zip(self.wave_ys, self.wave_timers)):
            wave = DataFiles.sprites["sortie_selection"][f"wave{i}"]
            wave_rect = wave.get_rect()
            wave_rect.top = wave_y + 8 * math.sin(2 * wave_timer)
            centerx = 64 * math.sin(wave_timer) + screen_x(0.5)
            for j in range(num_wave_reps):
                wave_rect.centerx = centerx + wave_rect.width * (j - wave_rep_offset)
                surface.blit(wave, wave_rect)

    def draw_nodes_and_props(self, surface):
        for sortie_node in self.sortie_nodes:
            sortie_node.draw_shadow(surface)

        drawables = [
            *[(sortie_node.get_depth(), sortie_node) for sortie_node in self.sortie_nodes],
            *[(sortie_prop.get_depth(), sortie_prop) for sortie_prop in self.sortie_props],
        ]
        for _, drawable in sorted(drawables, key=lambda item: item[0]):
            drawable.draw(surface)

        for sortie_node in self.sortie_nodes:
            sortie_node.draw_hover_effect(surface)

        if self.selected_sortie_node is not None:
            self.selected_sortie_node.draw_selection_effect(surface)

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
                self.start_sortie_button.hover(event.pos)

                if self.selected_sortie_node is None:
                    self.exit_sortie_selection_menu_button.hover(event.pos)
                    if self.mousedown:
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
                        self.selected_sortie_node.hovered = True

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
                            self.start_sortie_button.hover_background_color = Color.CLEARED_ZONE_OUTLINE
                        elif sortie_node.unlocked:
                            self.start_sortie_button.background_color = Color.UNCLEARED_ZONE_FILL
                            self.start_sortie_button.hover_background_color = Color.UNCLEARED_ZONE_OUTLINE
                        else:
                            self.start_sortie_button.background_color = Color.LOCKED_ZONE_FILL
                            self.start_sortie_button.hover_background_color = Color.LOCKED_ZONE_OUTLINE
                else:
                    if not self.selected_sortie_info_panel.collidepoint(event.pos):
                        self.selected_sortie_node.hovered = False
                        self.selected_sortie_node = None
                        self.start_sortie_button.active = False

                if click:
                    DataFiles.sfx["click"].play()

            if event.type == pygame.MOUSEMOTION:
                if self.selected_sortie_node is None:
                    for sortie_node in self.sortie_nodes:
                        sortie_node.hover(event.pos)

        num_waves = DataFiles.sprites["sortie_selection"]["num_waves"]
        self.wave_timers = [
            (wave_timer + (i+1)/num_waves*dt)%math.radians(360)
            for i, wave_timer in enumerate(self.wave_timers)
        ]

        for fog in self.fogs:
            fog.update(dt)

    def draw(self, surface, font_registry):
        self.draw_waves(surface)

        compass_rose = DataFiles.sprites["user_interface"]["compass_rose"]
        compass_rose_rect = compass_rose.get_rect()
        compass_rose_rect.bottom = Box.BOTTOM_OF_SCREEN
        compass_rose_rect.left = Box.LEFT_OF_SCREEN
        surface.blit(compass_rose, compass_rose_rect)

        self.draw_nodes_and_props(surface)
        
        for fog in self.fogs:
            fog.draw(surface)

        for chapter_name_ribbon in self.chapter_name_ribbons:
            chapter_name_ribbon.draw(surface, font_registry)
        
        if self.selected_sortie_node is not None:
            pygame.draw.rect(surface, Color.BLACK, self.selected_sortie_info_panel)
            title_card_rect = get_rect(
                width=self.selected_sortie_info_panel.width,
                height=2*font_registry["big_pixel"].font_height + 2*Box.PADDING,
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
            self.start_sortie_button.draw(surface, font_registry)
            font_registry["big_pixel"].render(
                surface,
                f"zone {self.selected_sortie_node.index + 1}",
                title_card_rect.center,
                Color.WHITE,
                2,
                style="center",
            )

            font_registry["big_pixel"].render(
                surface,
                "first clear rewards",
                (self.selected_sortie_info_panel.left + Box.PADDING, title_card_rect.bottom + Box.PADDING),
                Color.WHITE,
                1,
                style="topleft",
            )

            rewards = DataFiles.sortie_data[self.selected_sortie_node.index]["rewards"]
            for i, (reward, count) in enumerate(rewards.items()):
                rect = get_rect(
                    width=Box.WIDTH, height=Box.HEIGHT,
                    left=self.selected_sortie_info_panel.left + Box.PADDING + (i%3)*(Box.WIDTH+Box.PADDING),
                    top=title_card_rect.bottom + 2*Box.PADDING + font_registry["big_pixel"].font_height + (i//3)*(Box.HEIGHT+Box.PADDING)
                )
                pygame.draw.rect(surface, Color.WHITE, rect, width=Box.OUTLINE_WIDTH)
                surface.blit(DataFiles.get_entity_sprite(reward), rect)
                count_pos = pygame.Vector2(rect.bottomright) - pygame.Vector2(2*Box.PADDING, 2*Box.PADDING)
                font_registry["big_pixel"].render(surface, str(count), count_pos, Color.WHITE, 1, style="center", outline_color=Color.BLACK)

        self.exit_sortie_selection_menu_button.draw(surface, font_registry)
