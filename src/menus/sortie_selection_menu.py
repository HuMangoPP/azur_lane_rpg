import math
import random
import pygame

from engine.util import get_rect, get_vec, pixel_to_hex, hex_to_pixel, get_cluster_edges, adjacent_hexes
from engine.button import Button

from src.constants import DataFiles, Color, Box, screen_x, screen_y


def anchor():
    return pygame.Vector2(screen_x(1), screen_y(1)) - SortieNode.center


class SortieNode:
    SIZE = Box.WIDTH/2
    center = pygame.Vector2(screen_x(0.5), screen_y(0.5))

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
        hx, hy = pixel_to_hex(mouse_x - anchor().x, mouse_y - anchor().y, self.SIZE)
        self.hovered = self.unlocked and (hx, hy) in self.hexes

    def select(self, mouse_pos):
        if not self.unlocked:
            return False

        mouse_x, mouse_y = mouse_pos
        hx, hy = pixel_to_hex(mouse_x - anchor().x, mouse_y - anchor().y, self.SIZE)
        if (hx, hy) not in self.hexes:
            return False
        
        return True

    def draw_shadow(self, surface):
        polygon = [
            point + anchor() + pygame.Vector2(self.SIZE/4,self.SIZE/2)
            for point in self.polygon
        ]
        pygame.draw.polygon(surface, Color.OCEAN_SHADOW, polygon)

    def get_styling(self):
        if self.cleared:
            return (
                Color.CLEARED_ZONE_FILL,
                Color.CLEARED_ZONE_OUTLINE,
                DataFiles.sprites["user_interface"]["cleared"],
            )
        elif self.unlocked:
            fill = Color.UNCLEARED_ZONE_FILL
            outline = Color.UNCLEARED_ZONE_OUTLINE
            if len(self.hexes) > 1:
                icon = DataFiles.sprites["user_interface"]["boss"]
            else:
                icon = DataFiles.sprites["user_interface"]["uncleared"]
            return fill, outline, icon
        else:
            return (
                Color.LOCKED_ZONE_FILL,
                Color.LOCKED_ZONE_OUTLINE,
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
        fill, outline, icon = self.get_styling()
        polygon = [point + anchor() for point in self.polygon]
        if self.hovered:
            pygame.draw.polygon(surface, outline, polygon)
        else:
            pygame.draw.polygon(surface, fill, polygon)
        pygame.draw.polygon(surface, outline, polygon, width=Box.OUTLINE_WIDTH)
        
        for q, r in self.hexes:
            x, y = hex_to_pixel(q, r, self.SIZE)
            icon_rect = icon.get_rect()
            icon_rect.center = pygame.Vector2(x,y) + anchor()
            surface.blit(icon, icon_rect)

    def draw_selection_effect(self, surface):
        glow = self.get_selection_glow_sprite()
        for q, r in self.hexes:
            x, y = hex_to_pixel(q, r, self.SIZE)
            glow_rect = glow.get_rect()
            glow_rect.midbottom = pygame.Vector2(x, y) + anchor()
            surface.blit(glow, glow_rect, special_flags=pygame.BLEND_RGB_ADD)

        _, outline, icon = self.get_styling()
        polygon = [point + anchor() for point in self.polygon]
        pygame.draw.polygon(surface, outline, polygon)
        
        for q, r in self.hexes:
            x, y = hex_to_pixel(q, r, self.SIZE)
            icon_rect = icon.get_rect()
            icon_rect.center = pygame.Vector2(x,y) + anchor()
            surface.blit(icon, icon_rect)

    def get_bounding_rect(self):
        points = [point + anchor() for point in self.polygon]
        left = min(point.x for point in points)
        right = max(point.x for point in points)
        top = min(point.y for point in points)
        bottom = max(point.y for point in points)
        return pygame.Rect(left, top, right - left, bottom - top)

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
                + anchor()
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
        rect.center = self.position + anchor()
        return rect

    def draw(self, surface):
        surface.blit(self.sprite, self.get_rect())


class NameRibbon:
    PADDING_X = 24
    FONT_SCALE = 1
    
    def __init__(self, position, name):
        self.text = name
        self.position = pygame.Vector2(position)
    
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
        return get_rect(width=width, height=height, center=self.position + anchor())

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

class ChapterNameRibbon:
    CHAPTER_NAMES = [
        "training exercise",
        "patrol route",
        "crimson reef",
        "stormy sea",
        "mirror sea"
    ]

    def __init__(self, chapter, sortie_nodes):
        if chapter < len(self.CHAPTER_NAMES):
            text = self.CHAPTER_NAMES[chapter]
        else:
            text = f"chapter {chapter}"
        position = self.get_position(sortie_nodes)

        self.ribbon = NameRibbon(position, text)

    def get_position(self, sortie_nodes):
        hex_positions = []
        for sortie_node in sortie_nodes:
            for q, r in sortie_node.hexes:
                hex_positions.append(pygame.Vector2(hex_to_pixel(q, r, SortieNode.SIZE)))

        left = min(position.x for position in hex_positions)
        right = max(position.x for position in hex_positions)
        bottom = max(position.y for position in hex_positions)
        return pygame.Vector2((left + right) / 2, bottom + 3 * SortieNode.SIZE)

    def draw(self, surface, font_registry):
        self.ribbon.draw(surface, font_registry)


class Background:
    def __init__(self):
        num_waves = 36
        self.wave_indices = random.choices(list(range(DataFiles.sprites["sortie_selection"]["num_wave_sprites"])), k=num_waves)
        wave_height = DataFiles.sprites["sortie_selection"]["wave"].get_height() / 2
        self.wave_ys = [wave_height * (i - num_waves + 8) for i in range(num_waves)]
        self.wave_timers = [math.radians(random.randint(0, 359)) for _ in range(num_waves)]

    def update(self, dt):
        self.wave_timers = [(wave_timer + dt) % math.radians(360) for wave_timer in self.wave_timers]

    def draw(self, surface):
        num_wave_reps = 10
        for wave_index, wave_y, wave_timer in  zip(self.wave_indices, self.wave_ys, self.wave_timers):
            wave_sprite = DataFiles.sprites["sortie_selection"][f"wave{wave_index}"]
            wave_rect = wave_sprite.get_rect()
            wave_rect.top = wave_y + 4 * math.sin(2 * wave_timer) + anchor().y
            if wave_rect.bottom < 0 or wave_rect.top > screen_y(1):
                continue
            centerx = 32 * math.sin(wave_timer) + anchor().x - screen_x(0.5)
            for i in range(num_wave_reps):
                wave_rect.centerx = centerx + wave_rect.width * i
                if wave_rect.right < 0 or wave_rect.left > screen_x(1):
                    continue
                surface.blit(wave_sprite, wave_rect)

    def draw_markings(self, surface, font_registry):
        compass_rose = DataFiles.sprites["sortie_selection"]["compass_rose"]
        compass_rose_rect = compass_rose.get_rect()
        compass_rose_rect.bottom = Box.BOTTOM_OF_SCREEN
        compass_rose_rect.left = Box.LEFT_OF_SCREEN
        surface.blit(compass_rose, compass_rose_rect)

        map_scale = DataFiles.sprites["sortie_selection"]["map_scale"]
        map_scale_rect = map_scale.get_rect()
        map_scale_rect.bottom = Box.BOTTOM_OF_SCREEN
        map_scale_rect.left = compass_rose_rect.right + Box.PADDING
        surface.blit(map_scale, map_scale_rect)

        for dist, x in zip([0, 50, 100, 200], [
            map_scale_rect.left,
            map_scale_rect.left + map_scale_rect.width * 0.25,
            map_scale_rect.left + map_scale_rect.width * 0.5,
            map_scale_rect.left + map_scale_rect.width
        ]):
            font_registry["big_pixel"].render(
                surface,
                str(dist),
                pygame.Vector2(x, map_scale_rect.top - 10),
                Color.WHITE,
                1,
                style="center",
                outline_color=Color.BLACK
            )
        font_registry["big_pixel"].render(
            surface,
            "kilometers",
            pygame.Vector2(map_scale_rect.right + Box.PADDING, map_scale_rect.centery),
            Color.WHITE,
            1,
            style="centerleft",
            outline_color=Color.BLACK
        )


class SortieOrderCard:
    WIDTH = 3*(Box.WIDTH + Box.PADDING) + Box.PADDING + 2*Box.PADDING
    HEIGHT = 4.5*Box.HEIGHT + 4*Box.PADDING
    HEADER_BOTTOM = 64
    REWARD_TOP = 84
    BUTTON_HEIGHT = Box.HEIGHT
    CHART_GAP = 2 * Box.PADDING

    def __init__(self, authorize_sortie):
        self.rect = get_rect(width=self.WIDTH, height=self.HEIGHT, left=0, top=0)
        self.page_rect = self.rect.inflate(-2*Box.PADDING, -2*Box.PADDING - Box.HEIGHT/2)
        self.side = "right"
        self.node = None

        self.button = Button(
            get_rect(width=self.WIDTH - 4*Box.PADDING, height=self.BUTTON_HEIGHT, left=0, top=0),
            authorize_sortie,
            active=False,
            background_styling={
                "background_color": Color.START_SORTIE_BUTTON,
                "background_img": DataFiles.sprites["user_interface"]["start_sortie"],
                "background_img_align": (1/5, 1/2),
            },
            text_styling={
                "text": "authorize sortie",
                "text_align": (3/5, 1/2),
                "text_color": Color.WHITE,
            },
            hover_styling={
                "background_color": Color.HOVER_START_SORTIE_BUTTON,
            },
        )

    @staticmethod
    def get_safe_rect():
        exit_button_clearance = 48 + Box.PADDING
        return pygame.Rect(
            Box.LEFT_OF_SCREEN,
            Box.TOP_OF_SCREEN,
            Box.RIGHT_OF_SCREEN - exit_button_clearance - Box.LEFT_OF_SCREEN,
            Box.BOTTOM_OF_SCREEN - Box.TOP_OF_SCREEN,
        )

    def get_unclamped_rect(self, node_rect, side=None):
        side = side or self.side
        rect = self.rect.copy()
        rect.centery = node_rect.centery
        if side == "right":
            rect.left = node_rect.right + self.CHART_GAP
        else:
            rect.right = node_rect.left - self.CHART_GAP
        return rect

    def layout(self):
        if self.node is None:
            return

        node_rect = self.node.get_bounding_rect()
        rect = self.get_unclamped_rect(node_rect)
        safe_rect = self.get_safe_rect()
        rect.clamp_ip(safe_rect)
        self.rect.topleft = rect.topleft
        self.page_rect.centerx = self.rect.centerx
        self.page_rect.bottom = self.rect.bottom - Box.PADDING

        self.button.rect.centerx = self.rect.centerx
        self.button.rect.bottom = self.rect.bottom - 2*Box.PADDING

    def select(self, node, side, authorize_immediately):
        self.node = node
        self.side = side
        self.layout()
        self.button.active = authorize_immediately

    def clear(self):
        self.node = None
        self.button.active = False
        self.button.hovered = False

    def get_status(self):
        if self.node.cleared:
            return "cleared", Color.CLEARED_ZONE_FILL
        return "available", Color.UNCLEARED_ZONE_FILL

    def draw_paper(self, surface):
        dossier_rect = self.rect.inflate(0, -Box.HEIGHT/2)
        dossier_rect.bottomleft = self.rect.bottomleft
        pygame.draw.rect(surface, Color.DOSSIER, dossier_rect)
        dossier_tab = [
            pygame.Vector2(self.rect.topleft),
            pygame.Vector2(self.rect.topleft) + pygame.Vector2(Box.WIDTH - Box.PADDING, 0),
            pygame.Vector2(self.rect.topleft) + pygame.Vector2(Box.WIDTH + Box.PADDING, Box.HEIGHT/2),
            pygame.Vector2(self.rect.topleft) + pygame.Vector2(0, Box.HEIGHT/2),
        ]
        pygame.draw.polygon(surface, Color.DOSSIER, dossier_tab)

        undersheets = [
            (-2, pygame.Vector2(-2, 3), Color.DOSSIER_PAPER_UNDERSIDE),
            (2, pygame.Vector2(3, 1), Color.DOSSIER_CARD),
        ]
        for angle, offset, color in undersheets:
            pygame.draw.polygon(
                surface,
                color,
                Box.get_rotated_rect_polygon(self.page_rect, angle, offset),
            )
        pygame.draw.rect(surface, Color.DOSSIER_PAGE, self.page_rect)

    def draw_header(self, surface, font_registry):
        font = font_registry["big_pixel"]
        small_font = font_registry["pixel"]
        left = self.page_rect.left + Box.PADDING
        right = self.page_rect.right - Box.PADDING
        top = self.page_rect.top + Box.PADDING
        status, status_color = self.get_status()

        small_font.render(surface, "azur lane naval command", (left, top), Color.DOSSIER_RULE, 1)
        form_text = f"form so-{self.node.index + 1:03d}"
        form_left = right - small_font.get_width(form_text, 1, 0)
        small_font.render(surface, form_text, (form_left, top), Color.DOSSIER_RULE, 1)
        small_font.render(surface, "operation order", (left, top + 12), Color.DOSSIER_INK, 1)
        font.render(surface, f"sector {self.node.index + 1:02d}", (left, top + 27), Color.DOSSIER_INK, 2)

        status_width = font.get_width(status, 1, 0) + 2*Box.PADDING
        status_rect = get_rect(
            width=status_width,
            height=24,
            right=right,
            bottom=self.page_rect.top + self.HEADER_BOTTOM - Box.PADDING,
        )
        pygame.draw.rect(surface, status_color, status_rect, width=Box.OUTLINE_WIDTH)
        pygame.draw.rect(surface, status_color, status_rect.inflate(-4, -4), width=1)
        font.render(surface, status, status_rect.center, status_color, 1, style="center")

        pygame.draw.line(
            surface,
            Color.DOSSIER_RULE,
            (left, self.page_rect.top + self.HEADER_BOTTOM),
            (right, self.page_rect.top + self.HEADER_BOTTOM),
        )

    def draw_rewards(self, surface, font_registry):
        font = font_registry["big_pixel"]
        left = self.page_rect.left + Box.PADDING
        heading = "allotment issued" if self.node.cleared else "first-clear allotment"
        font.render(surface, heading, (left, self.page_rect.top + 70), Color.DOSSIER_RULE, 1)

        rewards = DataFiles.sortie_data[self.node.index]["rewards"]
        if not rewards:
            reward_area = pygame.Rect(left, self.page_rect.top + self.REWARD_TOP, self.page_rect.width - 2*Box.PADDING, Box.HEIGHT)
            font.render(surface, "no allotment on file", reward_area.center, Color.DOSSIER_RULE, 1, style="center")
            return

        for i, (reward, count) in enumerate(rewards.items()):
            rect = get_rect(
                width=Box.WIDTH,
                height=Box.HEIGHT,
                left=left + i*(Box.WIDTH + Box.PADDING),
                top=self.page_rect.top + self.REWARD_TOP,
            )
            pygame.draw.rect(surface, Color.DOSSIER_CARD_SHADOW, rect.move(2, 2))
            pygame.draw.rect(surface, Color.DOSSIER_CARD, rect)
            surface.blit(DataFiles.get_entity_sprite(reward), rect)

            quantity_rect = pygame.Rect(rect.left, rect.bottom - 14, rect.width, 14)
            pygame.draw.rect(surface, Color.DOSSIER_CARD, quantity_rect)
            pygame.draw.line(surface, Color.DOSSIER_RULE, quantity_rect.topleft, quantity_rect.topright)
            font.render(surface, f"qty {count:02d}", quantity_rect.center, Color.DOSSIER_INK, 1, style="center")
            pygame.draw.rect(surface, Color.DOSSIER_INK, rect, width=1)

        if self.node.cleared:
            obtained_stamp = DataFiles.sprites["sortie_selection"]["obtained_stamp"].copy()
            obtained_stamp.set_alpha(128)
            obtained_stamp_rect = obtained_stamp.get_rect()
            obtained_stamp_rect.centerx = self.page_rect.centerx
            obtained_stamp_rect.top = self.page_rect.top + self.REWARD_TOP
            surface.blit(obtained_stamp, obtained_stamp_rect)

    def draw_props(self, surface):
        paperclip = DataFiles.sprites["props"]["diagonal_paperclip"]
        paperclip_rect = paperclip.get_rect()
        paperclip_rect.left = self.rect.left - 16
        paperclip_rect.top = self.rect.top - 8 + Box.HEIGHT/2
        surface.blit(paperclip, paperclip_rect)

    def draw(self, surface, font_registry):
        if self.node is None:
            return

        self.layout()
        self.draw_paper(surface)
        self.draw_header(surface, font_registry)
        self.draw_rewards(surface, font_registry)
        self.button.draw(surface, font_registry)
        self.draw_props(surface)


class SortieSelectionMenu:
    PATH_DASH_LENGTH = 8
    PATH_DASH_WIDTH = 3
    CAMERA_PAN_DURATION = 0.25
    CAMERA_MIN = pygame.Vector2(screen_x(0.5), -305)
    CAMERA_MAX = pygame.Vector2(1822, screen_y(0.5))

    def __init__(self, menu_manager):
        self.menu_manager = menu_manager

        self.mousedown = False

        self.selected_sortie_node = None
        self.sortie_nodes = [
            SortieNode(sortie_index, sortie_info)
            for sortie_index, sortie_info in enumerate(DataFiles.sortie_data)
        ]

        def start_sortie():
            self.menu_manager.current_menu = self.menu_manager.fleet_selection_menu
            self.menu_manager.fleet_selection_menu.generate_path(self.selected_sortie_node.index)
            self.menu_manager.encounter_menu.current_sortie = self.selected_sortie_node.index
            self.menu_manager.encounter_menu.current_encounter = 0
            self.menu_manager.player_fleet.clear_fleet()
            self.menu_manager.siren_fleet.clear_fleet()

            self.selected_sortie_node.hovered = False
            self.selected_sortie_node = None
            self.sortie_order_card.clear()
        
        self.sortie_order_card = SortieOrderCard(start_sortie)
        self.selected_sortie_info_panel = self.sortie_order_card.rect
        self.camera_pan_start = SortieNode.center.copy()
        self.camera_pan_target = SortieNode.center.copy()
        self.camera_pan_timer = 0

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

        self.background = Background()
        self.chapter_name_ribbons = self.create_chapter_name_ribbons()

        self.fogs = [
            Fog(
                [sortie_node for sortie_node in self.sortie_nodes if sortie_node.chapter == chapter],
                disperse=DataFiles.save_file["chapter_progress"] >= chapter
            )
            for chapter in range(4)
        ]

        self.paths = {}
        self.generate_paths()

        self.sea_location_labels = [
            NameRibbon((-42, -431), "stormy"),
            NameRibbon((747, 69), "glaciers"),
            NameRibbon((670, -618), "glaciers"),
            NameRibbon((1588, -169), "stormy"),
            NameRibbon((1658, -587), "stormy"),
        ]

    def generate_paths(self):
        for chapter, checkpoints in DataFiles.sortie_selection_details["checkpoints"].items():
            checkpoints = [pygame.Vector2(checkpoint) for checkpoint in checkpoints]
            step = 1
            record_every = 16
            record_every_counter = record_every
            relpos = checkpoints[1] - checkpoints[0]
            angle = math.atan2(relpos.y, relpos.x)
            pos = checkpoints[0]
            path = [(pos, angle)]
            for checkpoint in checkpoints[1:]:
                to_target = checkpoint - pos

                if math.atan2(to_target.y, to_target.x) == angle:
                    turn_amount = 0
                else:
                    normal = get_vec(1, angle + math.radians(90))
                    dot_product = normal * to_target
                    radius = to_target.length_squared() / (2 * abs(dot_product))
                    turn_amount = step / radius

                while to_target.length() > 5:
                    pos = pos + get_vec(step, angle)
                    if record_every_counter == 0:
                        path.append((pos, angle))
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
                    angle = new_angle
                    new_left_side = get_vec(1, angle - math.radians(90))
                    new_dot_product = new_left_side * to_target
                    if (
                        (dot_product > 0 and new_dot_product <= 0)
                        or (dot_product <= 0 and new_dot_product > 0)
                    ):
                        angle = math.atan2(to_target.y, to_target.x)
            if record_every_counter < 10:
                pos = pos + get_vec(record_every_counter, angle)
                path.append((pos, angle))
            self.paths[int(chapter)] = path

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

    @classmethod
    def clamp_camera_center(cls, center):
        return pygame.Vector2(
            min(max(cls.CAMERA_MIN.x, center.x), cls.CAMERA_MAX.x),
            min(max(cls.CAMERA_MIN.y, center.y), cls.CAMERA_MAX.y),
        )

    @staticmethod
    def get_viewport_shift(rect, safe_rect):
        shift = pygame.Vector2()
        if rect.left < safe_rect.left:
            shift.x = safe_rect.left - rect.left
        elif rect.right > safe_rect.right:
            shift.x = safe_rect.right - rect.right
        if rect.top < safe_rect.top:
            shift.y = safe_rect.top - rect.top
        elif rect.bottom > safe_rect.bottom:
            shift.y = safe_rect.bottom - rect.bottom
        return shift

    @staticmethod
    def get_viewport_overflow(rect, safe_rect):
        return (
            max(0, safe_rect.left - rect.left)
            + max(0, rect.right - safe_rect.right)
            + max(0, safe_rect.top - rect.top)
            + max(0, rect.bottom - safe_rect.bottom)
        )

    def get_camera_target_for_card_side(self, node, side):
        node_rect = node.get_bounding_rect()
        card_rect = self.sortie_order_card.get_unclamped_rect(node_rect, side)
        combined_rect = node_rect.union(card_rect)
        safe_rect = self.sortie_order_card.get_safe_rect()
        requested_shift = self.get_viewport_shift(combined_rect, safe_rect)

        target = self.clamp_camera_center(SortieNode.center - requested_shift)
        actual_shift = SortieNode.center - target
        shifted_combined_rect = combined_rect.move(round(actual_shift.x), round(actual_shift.y))
        overflow = self.get_viewport_overflow(shifted_combined_rect, safe_rect)
        return target, overflow

    def select_sortie_node(self, node):
        right_target, right_overflow = self.get_camera_target_for_card_side(node, "right")
        if right_overflow == 0:
            side = "right"
            target = right_target
        else:
            left_target, left_overflow = self.get_camera_target_for_card_side(node, "left")
            if left_overflow < right_overflow:
                side = "left"
                target = left_target
            else:
                side = "right"
                target = right_target

        self.selected_sortie_node = node
        self.selected_sortie_node.hovered = False
        self.camera_pan_start = SortieNode.center.copy()
        self.camera_pan_target = target
        camera_will_move = not self.camera_pan_start.distance_squared_to(target) < 0.01
        self.camera_pan_timer = self.CAMERA_PAN_DURATION if camera_will_move else 0
        self.sortie_order_card.select(node, side, authorize_immediately=not camera_will_move)

    def clear_selected_sortie(self):
        if self.selected_sortie_node is not None:
            self.selected_sortie_node.hovered = False
        self.selected_sortie_node = None
        self.sortie_order_card.clear()
        self.camera_pan_timer = 0
        self.camera_pan_start = SortieNode.center.copy()
        self.camera_pan_target = SortieNode.center.copy()

    def update_camera_pan(self, dt):
        if self.camera_pan_timer <= 0:
            return

        self.camera_pan_timer = max(0, self.camera_pan_timer - dt)
        progress = 1 - self.camera_pan_timer / self.CAMERA_PAN_DURATION
        eased_progress = 1 - (1 - progress) ** 3
        SortieNode.center = self.camera_pan_start.lerp(self.camera_pan_target, eased_progress)
        self.sortie_order_card.layout()

        if self.camera_pan_timer == 0:
            SortieNode.center = self.camera_pan_target.copy()
            self.sortie_order_card.layout()
            self.sortie_order_card.button.active = self.selected_sortie_node is not None

    def update(self, dt, events):
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.exit_sortie_selection_menu_button.rect.collidepoint(event.pos):
                    continue
                if self.sortie_order_card.button.rect.collidepoint(event.pos):
                    continue
                if self.selected_sortie_node is not None:
                    continue
                for sortie_node in self.sortie_nodes:
                    if sortie_node.select(event.pos):
                        break
                else:
                    self.mousedown = True
            if event.type == pygame.MOUSEMOTION:
                self.sortie_order_card.button.hover(event.pos)

                if self.selected_sortie_node is None:
                    self.exit_sortie_selection_menu_button.hover(event.pos)
                    if self.mousedown:
                        movement = pygame.Vector2(event.rel)
                        SortieNode.center -= movement
                        SortieNode.center = self.clamp_camera_center(SortieNode.center)
            if event.type == pygame.MOUSEBUTTONUP:
                if self.mousedown:
                    self.mousedown = False
                    continue

                if self.exit_sortie_selection_menu_button.click(event.pos):
                    DataFiles.sfx["click"].play()
                    continue
                if self.sortie_order_card.button.click(event.pos):
                    DataFiles.sfx["click"].play()
                    continue

                if self.selected_sortie_node is None:
                    for sortie_node in self.sortie_nodes:
                        if not sortie_node.select(event.pos):
                            continue
                        self.select_sortie_node(sortie_node)
                        DataFiles.sfx["click"].play()
                        break
                else:
                    if not self.selected_sortie_info_panel.collidepoint(event.pos):
                        self.clear_selected_sortie()

            if event.type == pygame.MOUSEMOTION:
                if self.selected_sortie_node is None:
                    for sortie_node in self.sortie_nodes:
                        sortie_node.hover(event.pos)

        self.update_camera_pan(dt)
        self.background.update(dt)
        for fog in self.fogs:
            fog.update(dt)

    def draw(self, surface, font_registry):
        self.background.draw(surface)

        for chapter in range(DataFiles.save_file["chapter_progress"]+1):
            path = self.paths.get(chapter, [])
            for point, angle in path:
                center = point + anchor()
                dash_offset = get_vec(self.PATH_DASH_LENGTH / 2, angle)
                dash_width_offset = get_vec(self.PATH_DASH_WIDTH / 2, angle + math.radians(90))
                dash_polygon = [
                    center + dash_offset + dash_width_offset,
                    center - dash_offset + dash_width_offset,
                    center - dash_offset - dash_width_offset,
                    center + dash_offset - dash_width_offset,
                ]
                pygame.draw.polygon(
                    surface,
                    Color.WHITE,
                    dash_polygon
                )

        for prop_info in DataFiles.sortie_selection_details["props"]:
            prop = DataFiles.sprites["sortie_selection"][prop_info["prop"]]
            prop_rect = prop.get_rect()
            prop_rect.center = (
                pygame.Vector2(hex_to_pixel(*prop_info["hex"], SortieNode.SIZE))
                + anchor()
            )
            surface.blit(prop, prop_rect)

        for sortie_node in self.sortie_nodes:
            sortie_node.draw_shadow(surface)
        for sortie_node in self.sortie_nodes:
            sortie_node.draw(surface)

        if self.selected_sortie_node is not None:
            self.selected_sortie_node.draw_selection_effect(surface)

        for chapter_name_ribbon in self.chapter_name_ribbons:
            chapter_name_ribbon.draw(surface, font_registry)
        
        for location_ribbon in self.sea_location_labels:
            location_ribbon.draw(surface, font_registry)

        self.background.draw_markings(surface, font_registry)
        
        current_sortie_node = next(
            (
                sortie_node for sortie_node in self.sortie_nodes
                if sortie_node.unlocked and not sortie_node.cleared
            ),
            None
        )
        if current_sortie_node is not None:
            arrow = DataFiles.sprites["sortie_selection"]["arrow"]
            arrow_rect = arrow.get_rect()
            arrow_rect.midbottom = current_sortie_node.get_bounding_rect().midtop
            surface.blit(arrow, arrow_rect)

        for fog in self.fogs:
            fog.draw(surface)
        
        if self.selected_sortie_node is not None:
            self.sortie_order_card.draw(surface, font_registry)

        self.exit_sortie_selection_menu_button.draw(surface, font_registry)
