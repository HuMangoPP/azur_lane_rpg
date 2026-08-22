import math
import random
import functools
import pygame

from engine.util import draw_annulus, get_rect, get_vec
from engine.button import Button

from src.constants import DataFiles, Color, Box, Stats, screen_x, screen_y, Decorations
from src.shipgirls import Shipgirl
from live2d.live2d import Live2D


class AnnularSectorButton:
    SPRITE_SIZE = 96
    ANGLE_WIDTH = math.radians(60)
    ANGLE_PADDING = 2

    def __init__(
        self,
        callback,
        active=True,
        background_styling=None,
        hover_styling=None,
        inner_radius=SPRITE_SIZE / 2,
        outer_radius=SPRITE_SIZE / 2 + Box.WIDTH,
        angle_width=ANGLE_WIDTH,
    ):
        background_styling = background_styling or {}
        hover_styling = hover_styling or {}

        self.active = active
        self.callback = callback
        self.center = pygame.Vector2(0, 0)
        self.angle = 0
        self.angle_width = angle_width
        self.inner_radius = round(inner_radius)
        self.outer_radius = round(outer_radius)

        self.background_color = background_styling.get("background_color")
        self.background_img = background_styling.get("background_img")
        self.opacity = background_styling.get("opacity")

        self.hover_background_color = hover_styling.get("background_color", self.background_color)
        self.hover_opacity = hover_styling.get("opacity", self.opacity)
        self.hovered = False

    def contains_point(self, mpos):
        relpos = pygame.Vector2(mpos) - self.center
        distance = relpos.length()
        if distance < self.inner_radius or distance > self.outer_radius:
            return False

        point_angle = math.atan2(relpos.y, relpos.x)
        angle_delta = (point_angle - self.angle + math.pi) % (2 * math.pi) - math.pi
        return abs(angle_delta) <= self.angle_width / 2

    def hover(self, mpos):
        self.hovered = self.active and self.contains_point(mpos)
        return self.hovered

    def click(self, mpos):
        if not self.active or not self.contains_point(mpos):
            return False

        self.callback()
        return True

    def draw(self, surface, font_registry):
        if not self.active:
            return

        background_color = self.hover_background_color if self.hovered else self.background_color
        opacity = self.hover_opacity if self.hovered else self.opacity
        if background_color is not None:
            wedge_surface = pygame.Surface((2 * self.outer_radius, 2 * self.outer_radius))
            draw_annulus(
                wedge_surface,
                background_color,
                (self.outer_radius, self.outer_radius),
                self.inner_radius,
                self.outer_radius,
                math.degrees(self.angle - self.angle_width / 2) + self.ANGLE_PADDING,
                math.degrees(self.angle + self.angle_width / 2) - self.ANGLE_PADDING,
                resolution=4
            )
            if opacity is not None:
                wedge_surface.set_alpha(opacity)
            wedge_surface.set_colorkey((0, 0, 0))
            wedge_rect = wedge_surface.get_rect(center=self.center)
            surface.blit(wedge_surface, wedge_rect)

        if self.background_img is not None:
            img_rect = self.background_img.get_rect()
            img_rect.center = self.center + get_vec((self.inner_radius + self.outer_radius) / 2, self.angle)
            surface.blit(self.background_img, img_rect)


class PortMenu:
    NO_OVERLAY = "no_overlay"
    DEPOT = "depot"
    INTEL_CENTER = "intel_center"
    SHIPYARD = "shipyard"
    GEAR_LAB = "gear_lab"
    DECORATION_STORE = "decoration_store"

    DECORATION_DEPOT = "decoration_depot"
    DELETE_DECORATION = "__delete_decoration__"

    DECORATION_STAMP_ANIMATION_DURATION = 1
    DECORATION_STAMP_DOWN_TIME = 0.15
    DECORATION_STAMP_LIFT_TIME = 0.30
    DECORATION_STAMP_DISAPPEAR_TIME = 0.5
    DECORATION_PRICE = 1

    def __init__(self, menu_manager):
        # MenuManager object
        self.menu_manager = menu_manager

        # Factions and choose faction buttons
        factions = ["USS", "HMS", "IJN", "KMS"]
        def choose_faction_factory(faction):
            def choose_faction():
                DataFiles.save_file["unlocked_factions"].append(faction)
                for choose_faction_button in self.choose_faction_buttons:
                    choose_faction_button.active = False
            return choose_faction
        
        self.choose_faction_buttons = []
        choose_faction_center = pygame.Vector2(screen_x(0.5), screen_y(0.5))
        choose_faction_angles = [
            math.radians(-135),
            math.radians(-45),
            math.radians(45),
            math.radians(135),
        ]
        for faction, angle in zip(factions, choose_faction_angles):
            choose_faction_button = AnnularSectorButton(
                callback=choose_faction_factory(faction),
                active=False,
                background_styling={
                    "background_color": Color.BLACK,
                    "background_img": DataFiles.sprites["user_interface"][f"{faction}_big"],
                    "opacity": 160
                },
                hover_styling={"opacity": 200},
                inner_radius=Box.WIDTH,
                outer_radius=Box.WIDTH * 2.5,
                angle_width=math.radians(90),
            )
            choose_faction_button.center = choose_faction_center
            choose_faction_button.angle = angle
            self.choose_faction_buttons.append(choose_faction_button)

        # Sortie button
        def open_select_sortie_menu():
            self.menu_manager.current_menu = self.menu_manager.sortie_selection_menu
            DataFiles.sfx["waves"].play(loops=-1)

            close_shipgirl_dialogue_options()

        self.open_select_sortie_menu_button = Button(
            get_rect(width=2*Box.WIDTH,height=Box.HEIGHT,right=Box.RIGHT_OF_SCREEN,bottom=Box.BOTTOM_OF_SCREEN),
            open_select_sortie_menu,
            active=False,
            background_styling={
                "background_color": Color.START_SORTIE_BUTTON,
                "background_img": DataFiles.sprites["user_interface"]["sortie"],
            },
            hover_styling={"background_color": Color.HOVER_START_SORTIE_BUTTON}
        )

        # Overlay state
        self.current_overlay = self.NO_OVERLAY
        self.overlay_pages = {}
        self.visited_depot = False
        self.visited_intel_center = False
        self.depot_notification = True
        self.intel_center_notification = True
        self.shipyard_notification = True
        self.gear_lab_notification = True
        self.decoration_store_notification = True

        # Overlay buttons
        overlay_buttons_flexbox_width = self.open_select_sortie_menu_button.rect.left
        num_overlay_buttons = 5
        def open_overlay_button_factory(index, overlay_enum, has_notification=True):
            def open_overlay():
                self.current_overlay = overlay_enum
                self.overlay_pages.setdefault(overlay_enum, 0)
                if has_notification:
                    setattr(self, f"{overlay_enum}_notification", False)

                if overlay_enum == self.SHIPYARD:
                    if DataFiles.save_file["research_target"] is not None:
                        self.overlay_selected_entity = DataFiles.save_file["research_target"]
                        self.refresh_overlay_action_buttons()
                    
                    for i, faction in enumerate(self.shipyard_filters):
                        if DataFiles.save_file["unlocked_factions"][0] == faction:
                            self.overlay_selected_filter = i
                            break
                
                close_shipgirl_dialogue_options()

            return Button(
                get_rect(
                    width=Box.WIDTH, height=Box.HEIGHT,
                    centerx=(index+1)/(num_overlay_buttons+1) * overlay_buttons_flexbox_width,
                    bottom=Box.BOTTOM_OF_SCREEN
                ),
                open_overlay,
                active=False,
                background_styling={
                    "background_color": Color.BLACK,
                    "background_img": DataFiles.sprites["user_interface"][overlay_enum],
                    "opacity": 160,
                },
                hover_styling={"opacity": 200}
            )
        overlay_enums = [self.DEPOT, self.INTEL_CENTER, self.SHIPYARD, self.GEAR_LAB, self.DECORATION_STORE]
        for index, enum in enumerate(overlay_enums):
            setattr(self, f"open_{enum}_overlay_button", open_overlay_button_factory(index, enum))

        # Intel center, shipyard, gear lab filters
        self.overlay_selected_filter = 0
        self.intel_center_filters = ["DD", "CL", "CA", "BB", "SS", "CV"]
        self.shipyard_filters = ["USS", "HMS", "IJN", "KMS"]
        self.gear_lab_filters = ["DD", "CL", "CA", "BB", "SS", "CV", "AUX"]

        # Dossier-themed left panel
        # Full overlay left panel area
        num_items_in_row = 5
        num_items_in_col = 4
        dossier_page_margin = 48
        dossier_icon_grid_width = num_items_in_row*Box.WIDTH + (num_items_in_row - 1)*Box.PADDING
        dossier_icon_grid_height = num_items_in_col*Box.HEIGHT + (num_items_in_col - 1)*Box.PADDING
        self.dossier_overlay = get_rect(
            width=dossier_icon_grid_width + 2*dossier_page_margin + 2*Box.PADDING,
            height=dossier_icon_grid_height + 2*dossier_page_margin + Box.HEIGHT + 2*Box.PADDING,
            right=screen_x(0.5) + Box.WIDTH,
            centery=screen_y(0.5) - Box.HEIGHT/2
        )
        # Manila folder background
        self.dossier_bg = get_rect(
            width=self.dossier_overlay.width,
            height=self.dossier_overlay.height - Box.HEIGHT,
            left=self.dossier_overlay.left,
            bottom=self.dossier_overlay.bottom
        )
        # Folder tabs
        num_dossier_tabs = len(self.gear_lab_filters)
        tab_size = 48
        self.dossier_tabs = [
            get_rect(
                width=tab_size, height=tab_size,
                left=self.dossier_bg.left+i*Box.WIDTH,
                bottom=self.dossier_bg.top
            ) for i in range(num_dossier_tabs)
        ]
        # Paper foreground where the entities are listed
        self.dossier_page = get_rect(
            width=self.dossier_bg.width - 2*Box.PADDING,
            height=self.dossier_bg.height - 2*Box.PADDING,
            center=self.dossier_bg.center
        )
        # Icons on page
        dossier_icon_grid_left = self.dossier_page.centerx - dossier_icon_grid_width / 2
        dossier_icon_grid_top = self.dossier_page.centery - dossier_icon_grid_height / 2
        self.dossier_icons = [
            get_rect(
                width=Box.WIDTH, height=Box.HEIGHT,
                left=dossier_icon_grid_left+(i%num_items_in_row)*(Box.WIDTH+Box.PADDING),
                top=dossier_icon_grid_top+(i//num_items_in_row)*(Box.HEIGHT+Box.PADDING)
            ) for i in range(num_items_in_row * num_items_in_col)
        ]

        # Blueprint-themed right panel
        self.blueprint_page = get_rect(
            width=4*(Box.WIDTH + Box.PADDING) + Box.PADDING,
            height=5*(Box.HEIGHT + Box.PADDING) + Box.PADDING + Box.HEIGHT,
            left=self.dossier_overlay.right+Box.PADDING,
            centery=screen_y(0.5),
        )
        # Sticky-note confirm surface attached to the blueprint's top-right corner.
        self.sticky_note_page = get_rect(
            width=2*Box.WIDTH + 2*Box.PADDING,
            height=2*Box.HEIGHT + 2*Box.PADDING,
            right=self.blueprint_page.right + Box.WIDTH + Box.PADDING,
            top=self.blueprint_page.top - Box.HEIGHT/2 - Box.PADDING,
        )

        # Warehouse-themed left panel
        num_items_in_row = 5
        num_items_in_col = 4
        warehouse_overlay_content_height = num_items_in_col*(Box.HEIGHT+Box.PADDING) + Box.PADDING
        self.warehouse_overlay = get_rect(
            width=num_items_in_row*(Box.WIDTH+Box.PADDING) + Box.PADDING,
            height=warehouse_overlay_content_height,
            right=screen_x(0.5) + Box.WIDTH/2,
            top=screen_y(0.4) - warehouse_overlay_content_height/2
        )
        self.warehouse_icons = [
            get_rect(
                width=Box.WIDTH, height=Box.HEIGHT,
                left=self.warehouse_overlay.left+Box.PADDING+(i%num_items_in_row)*(Box.WIDTH+Box.PADDING),
                top=self.warehouse_overlay.top+Box.PADDING+(i//num_items_in_row)*(Box.HEIGHT+Box.PADDING)
            ) for i in range(num_items_in_row * num_items_in_col)
        ]
        self.warehouse_selected_item = None
        self.forklift_x = 0
        self.forklift_dx = 1
        self.forklift_pause = 0

        # Overlay paging buttons
        self.overlay_page_prev_button = Button(
            get_rect(width=48, height=48, left=0, top=0),
            lambda: self.change_overlay_page(-1),
            active=False,
            background_styling={
                "background_color": Color.WHITE,
                "background_img": DataFiles.sprites["user_interface"]["prev"],
                "opacity": 0,
            },
            hover_styling={"opacity": 32}
        )
        self.overlay_page_next_button = Button(
            get_rect(width=48, height=48, left=0, top=0),
            lambda: self.change_overlay_page(1),
            active=False,
            background_styling={
                "background_color": Color.WHITE,
                "background_img": DataFiles.sprites["user_interface"]["next"],
                "opacity": 0,
            },
            hover_styling={"opacity": 32}
        )

        # Clipboard-themed right panel
        self.clipboard_bg = get_rect(
            width=4*Box.WIDTH + 4*Box.PADDING,
            height=5*Box.HEIGHT + 4*Box.PADDING,
            left=self.warehouse_overlay.right + Box.WIDTH/2,
            centery=screen_y(0.5) - Box.HEIGHT/2
        )
        self.clipboard_page = get_rect(
            width=self.clipboard_bg.width - 2*Box.PADDING,
            height=self.clipboard_bg.height - 2*Box.PADDING - Box.HEIGHT/4,
            centerx=self.clipboard_bg.centerx,
            bottom=self.clipboard_bg.bottom - Box.PADDING
        )

        # Overlay logic state
        def confirm_shipyard_sticky_note():
            if self.overlay_selected_entity is None:
                return
            inventory = DataFiles.save_file["inventory"]
            specialized_wisdom_cubes = DataFiles.save_file["specialized_wisdom_cubes"]
            if self.can_construct_selected_shipgirl():
                DataFiles.sfx["knock"].play()
                shipgirl_exp = specialized_wisdom_cubes[self.overlay_selected_entity]
                DataFiles.save_file["shipgirls"][self.overlay_selected_entity] = {
                    "equipment": [None, None, None],
                    "exp": shipgirl_exp
                }
                shipgirl = Shipgirl(self.overlay_selected_entity, True)
                self.menu_manager.available_shipgirls.append(shipgirl)
                for ingredient, req in self.get_selected_shipyard_reqs().items():
                    inventory[ingredient] -= req
                specialized_wisdom_cubes.pop(self.overlay_selected_entity)
                if DataFiles.save_file["research_target"] == self.overlay_selected_entity:
                    DataFiles.save_file["research_target"] = None
                self.overlay_selected_entity = None
            elif self.can_start_selected_shipgirl_research():
                DataFiles.sfx["frequency"].play()
                inventory["wisdom_cube"] -= 1
                specialized_wisdom_cubes[self.overlay_selected_entity] = 0
                DataFiles.save_file["research_target"] = self.overlay_selected_entity
            self.refresh_overlay_action_buttons()
        
        self.shipyard_sticky_note_button = Button(
            self.sticky_note_page.copy(),
            confirm_shipyard_sticky_note,
            active=False,
            text_styling={
                "text_font": "handwritten",
                "text_color": Color.STICKY_NOTE_HANDWRITING,
            }
        )

        def confirm_gear_lab_sticky_note():
            if not self.can_craft_selected_equipment():
                return

            DataFiles.sfx["knock"].play()
            selected_entity_reqs = DataFiles.equipment_data[self.overlay_selected_entity]["craft_reqs"]
            DataFiles.save_file["equipment"][self.overlay_selected_entity] = (
                DataFiles.save_file["equipment"].get(self.overlay_selected_entity, 0) + 1
            )
            for ingredient, req in selected_entity_reqs.items():
                DataFiles.save_file["inventory"][ingredient] -= req

            self.refresh_overlay_action_buttons()
        
        self.gear_lab_sticky_note_button = Button(
            self.sticky_note_page.copy(),
            confirm_gear_lab_sticky_note,
            active=False,
            text_styling={
                "text": "construct?",
                "text_font": "handwritten",
                "text_color": Color.STICKY_NOTE_HANDWRITING,
            }
        )

        def confirm_decoration_signature():
            if not self.can_purchase_selected_decoration():
                return
            if self.decoration_stamp_animation_timer > 0:
                return

            DataFiles.sfx["coins"].play()
            DataFiles.save_file["decoration_depot"][self.overlay_selected_entity] = (
                DataFiles.save_file["decoration_depot"].get(self.overlay_selected_entity, 0) + 1
            )
            DataFiles.save_file["inventory"]["decoration_coin"] = (
                DataFiles.save_file["inventory"].get("decoration_coin", 0) - self.DECORATION_PRICE
            )
            self.decoration_stamp_animation_timer = self.DECORATION_STAMP_ANIMATION_DURATION
            self.decoration_stamp_animation_pos = pygame.Vector2(pygame.mouse.get_pos())
            self.refresh_overlay_action_buttons()

        self.decoration_stamp_animation_timer = 0
        self.decoration_stamp_animation_pos = pygame.Vector2((0, 0))
        self.decoration_signature_button = Button(
            get_rect(
                width=2*Box.WIDTH,
                height=Box.HEIGHT,
                right=self.clipboard_page.right - Box.PADDING,
                bottom=self.clipboard_page.bottom - Box.PADDING
            ),
            confirm_decoration_signature,
            active=False,
        )
        self.overlay_selected_entity = None

        def toggle_decoration_mode():
            self.is_decorating = not self.is_decorating
            if self.is_decorating:
                self.overlay_pages.setdefault(self.DECORATION_DEPOT, 0)
                self.refresh_overlay_page_buttons()
            else:
                self.overlay_page_prev_button.active = False
                self.overlay_page_next_button.active = False

            close_shipgirl_dialogue_options()

        self.toggle_decoration_mode_button = Button(
            rect=get_rect(width=Box.WIDTH, height=Box.HEIGHT, right=Box.RIGHT_OF_SCREEN, top=Box.TOP_OF_SCREEN),
            callback=toggle_decoration_mode,
            active=False,
            background_styling={
                "background_color": Color.BLACK,
                "background_img": DataFiles.sprites["user_interface"]["decorate_toggle"],
                "opacity": 160,
            },
            hover_styling={"opacity": 200}
        )
        self.is_decorating = False

        decoration_depot_content_height = 3*(Box.HEIGHT+Box.PADDING) + Box.PADDING
        self.decoration_depot_overlay = get_rect(
            width=3*(Box.WIDTH+Box.PADDING) + Box.PADDING,
            height=decoration_depot_content_height,
            left=Box.WIDTH,
            top=screen_y(1) - Box.HEIGHT - decoration_depot_content_height
        )
        self.selected_decoration_in_depot = None
        self.decoration_flipped = False
        self.deleting_decoration = False
        self.decoration_depot_drag_offset = None
        self.dragged_shipgirl = None
        self.moved_decoration_depot_overlay = False
        self.flipped_decoration = False
        self.placed_bed_decoration = False
        self.removed_bed_decoration = False
        self.shipgirl_interacted_with_bed = False

        Decorations.floor_rect.center = (screen_x(0.5), screen_y(0.5))
        self.camera_dragging = False

        self.hovered_shipgirl = None
        def open_equipment_menu():
            self.menu_manager.equipment_menu.selected_shipgirl = self.hovered_shipgirl
            self.menu_manager.current_menu = self.menu_manager.equipment_menu

            close_shipgirl_dialogue_options()

        def close_shipgirl_dialogue_options():
            if self.hovered_shipgirl is not None:
                self.hovered_shipgirl.pick_new_wander_target()
            self.hovered_shipgirl = None
            for option in self.shipgirl_dialogue_options:
                option.active = False

        shipgirl_dialogue_option_data = [
            (open_equipment_menu, "equip"),
            (lambda : True, "interact"),
        ]
        self.shipgirl_dialogue_options = [
            AnnularSectorButton(
                callback=callback,
                active=False,
                background_styling={
                    "background_color": Color.BLACK,
                    "background_img": DataFiles.sprites["user_interface"][sprite],
                    "opacity": 160
                },
                hover_styling={"opacity": 200},
            )
            for callback, sprite in shipgirl_dialogue_option_data
        ]

        self.update_encountered_sirens()

    def position_shipgirl_dialogue_options(self):
        if self.hovered_shipgirl is None:
            return

        circle_center = pygame.Vector2(self.hovered_shipgirl.rect.center)
        dialogue_options_offset = (len(self.shipgirl_dialogue_options) - 1) / 2
        top_angle = math.radians(-90)
        for i, option in enumerate(self.shipgirl_dialogue_options):
            angle = top_angle + (i - dialogue_options_offset) * AnnularSectorButton.ANGLE_WIDTH
            option.center = pygame.Vector2(circle_center)
            option.angle = angle

    def update_camera_drag(self, event):
        if not self.camera_dragging:
            return False

        old_topleft = pygame.Vector2(Decorations.floor_rect.topleft)
        Decorations.floor_rect.x += event.rel[0]
        Decorations.floor_rect.y += event.rel[1]

        screen_width = screen_x(1)
        screen_height = screen_y(1)
        if Decorations.floor_rect.width <= screen_width:
            Decorations.floor_rect.centerx = screen_x(0.5)
        else:
            Decorations.floor_rect.left = min(0, max(Decorations.floor_rect.left, screen_width - Decorations.floor_rect.width))

        if Decorations.floor_rect.height <= screen_height:
            Decorations.floor_rect.centery = screen_y(0.5)
        else:
            Decorations.floor_rect.top = min(0, max(Decorations.floor_rect.top, screen_height - Decorations.floor_rect.height))

        actual_delta = pygame.Vector2(Decorations.floor_rect.topleft) - old_topleft
        for shipgirl in self.menu_manager.available_shipgirls:
            shipgirl.pos += actual_delta
            shipgirl.wander_target += actual_delta
            shipgirl.rect.center = shipgirl.pos

        self.position_shipgirl_dialogue_options()
        return True

    def can_start_no_overlay_camera_drag(self, pos):
        if self.menu_manager.quest_manager.selected_quest is not None:
            return False

        rectangular_buttons = [
            self.open_select_sortie_menu_button,
            self.open_depot_overlay_button,
            self.open_shipyard_overlay_button,
            self.open_gear_lab_overlay_button,
            self.open_intel_center_overlay_button,
            self.open_decoration_store_overlay_button,
            self.toggle_decoration_mode_button,
        ]
        if any(button.active and button.rect.collidepoint(pos) for button in rectangular_buttons):
            return False

        annular_buttons = [
            *self.choose_faction_buttons,
            *self.shipgirl_dialogue_options
        ]
        if any(button.active and button.contains_point(pos) for button in annular_buttons):
            return False

        for i in range(len(self.menu_manager.quest_manager.quests)):
            quest_rect = get_rect(
                width=Box.WIDTH,
                height=Box.HEIGHT,
                left=Box.PADDING,
                top=Box.PADDING + (Box.HEIGHT + Box.PADDING) * i
            )
            if quest_rect.collidepoint(pos):
                return False

        return not any(shipgirl.rect.collidepoint(pos) for shipgirl in self.menu_manager.available_shipgirls)

    def can_start_decorate_camera_drag(self, pos):
        if self.decoration_depot_overlay.collidepoint(pos):
            return False
        if (
            self.overlay_page_prev_button.active
            and self.overlay_page_prev_button.rect.collidepoint(pos)
        ) or (
            self.overlay_page_next_button.active
            and self.overlay_page_next_button.rect.collidepoint(pos)
        ):
            return False
        if (
            self.toggle_decoration_mode_button.active
            and self.toggle_decoration_mode_button.rect.collidepoint(pos)
        ):
            return False
        if self.selected_decoration_in_depot is not None:
            return False
        
        if self.deleting_decoration:
            clicked_tilepos = Decorations.get_isometric_tilepos(pos)
            for decoration_data in DataFiles.save_file["decorations"]:
                decoration, tilepos_anchor, flipped = Decorations.unpack_decoration_data(decoration_data)
                if clicked_tilepos in Decorations.get_decoration_tiles(decoration, flipped, tilepos_anchor):
                    return False

        return not any(shipgirl.rect.collidepoint(pos) for shipgirl in self.menu_manager.available_shipgirls)

    def get_decoration_depot_entity_at_pos(self, pos):
        entities = self.get_visible_overlay_entities()
        rects = self.get_overlay_icon_rects()
        for entity, rect in zip(entities, rects):
            if rect.collidepoint(pos):
                return entity
        return None

    def select_decoration_depot_entity(self, pos, allow_delete_toggle):
        entity = self.get_decoration_depot_entity_at_pos(pos)
        if entity is None:
            return False

        if entity == self.DELETE_DECORATION:
            if allow_delete_toggle:
                DataFiles.sfx["click"].play()
                self.deleting_decoration = not self.deleting_decoration
                self.selected_decoration_in_depot = None
            return True

        DataFiles.sfx["click"].play()
        if self.selected_decoration_in_depot == entity:
            self.selected_decoration_in_depot = None
        else:
            self.selected_decoration_in_depot = entity
            self.deleting_decoration = False
        return True

    def update_encountered_sirens(self):
        self.encountered_sirens = set()
        for i in range(DataFiles.save_file["sortie_progress"]):
            encounters = DataFiles.sortie_data[i]["encounters"]
            for encounter in encounters:
                self.encountered_sirens = self.encountered_sirens.union(
                    [siren_name.split(":")[0] for siren_name in encounter["front"]]
                    + [siren_name.split(":")[0] for siren_name in encounter["back"]]
                )
        self.encountered_sirens = list(self.encountered_sirens)

    def draw_button_notification(self, surface, button, notification):
        if not button.active or not notification:
            return

        notification_sprite = DataFiles.sprites["user_interface"]["notification"]
        notification_rect = notification_sprite.get_rect()
        notification_rect.center = button.rect.topright
        surface.blit(notification_sprite, notification_rect)

    def get_selected_shipyard_reqs(self):
        if self.overlay_selected_entity is None:
            return {}

        selected_entity_info = DataFiles.shipgirl_data[self.overlay_selected_entity]
        hull_type = selected_entity_info["hull_type"]
        unique_item = selected_entity_info["unique_item"]
        return {
            f"{hull_type}_blueprint": 1,
            unique_item: 1
        }

    def can_construct_selected_shipgirl(self):
        if self.overlay_selected_entity is None:
            return False

        inventory = DataFiles.save_file["inventory"]
        specialized_wisdom_cubes = DataFiles.save_file["specialized_wisdom_cubes"]
        return (
            self.overlay_selected_entity in specialized_wisdom_cubes
            and all(
                inventory.get(ingredient, 0) >= req
                for ingredient, req in self.get_selected_shipyard_reqs().items()
            )
        )

    def can_start_selected_shipgirl_research(self):
        if self.overlay_selected_entity is None:
            return False

        specialized_wisdom_cubes = DataFiles.save_file["specialized_wisdom_cubes"]
        return (
            self.overlay_selected_entity not in specialized_wisdom_cubes
            and DataFiles.save_file["inventory"].get("wisdom_cube", 0) > 0
        )

    def has_selected_shipgirl_research_project(self):
        return (
            self.overlay_selected_entity is not None
            and self.overlay_selected_entity in DataFiles.save_file["specialized_wisdom_cubes"]
        )

    def can_craft_selected_equipment(self):
        if self.overlay_selected_entity is None:
            return False

        inventory = DataFiles.save_file["inventory"]
        selected_entity_reqs = DataFiles.equipment_data[self.overlay_selected_entity]["craft_reqs"]
        return all(
            inventory.get(ingredient, 0) >= req
            for ingredient, req in selected_entity_reqs.items()
        )

    def can_purchase_selected_decoration(self):
        return (
            self.overlay_selected_entity is not None
            and DataFiles.save_file["inventory"].get("decoration_coin", 0) >= self.DECORATION_PRICE
            and self.decoration_stamp_animation_timer <= 0
        )

    def get_owned_decoration_count(self, decoration):
        owned_count = DataFiles.save_file["decoration_depot"].get(decoration, 0)
        for decoration_data in DataFiles.save_file["decorations"]:
            placed_decoration, _, _ = Decorations.unpack_decoration_data(decoration_data)
            if placed_decoration == decoration:
                owned_count += 1
        return owned_count

    def refresh_overlay_action_buttons(self):
        self.shipyard_sticky_note_button.active = False
        self.gear_lab_sticky_note_button.active = False
        self.decoration_signature_button.active = False

        if self.current_overlay == self.SHIPYARD:
            if self.can_construct_selected_shipgirl():
                self.shipyard_sticky_note_button.active = True
                self.shipyard_sticky_note_button.text = "construct?"
            elif self.can_start_selected_shipgirl_research():
                self.shipyard_sticky_note_button.active = True
                self.shipyard_sticky_note_button.text = "research?"
            elif self.has_selected_shipgirl_research_project():
                self.shipyard_sticky_note_button.active = True
                research_exp = DataFiles.save_file["specialized_wisdom_cubes"].get(self.overlay_selected_entity, 0)
                avg_shipgirl_level = int(
                    sum(
                        Stats.level(shipgirl.battle_component.exp)
                        for shipgirl in self.menu_manager.available_shipgirls
                    )
                    / len(self.menu_manager.available_shipgirls)
                )
                exp_req = max(1, Stats.exp_to_level(avg_shipgirl_level))
                research_percentage = int(100 * min(1, research_exp / exp_req))
                self.shipyard_sticky_note_button.text = f"research progress {research_percentage}%"
        elif self.current_overlay == self.GEAR_LAB:
            self.gear_lab_sticky_note_button.active = self.can_craft_selected_equipment()
        elif self.current_overlay == self.DECORATION_STORE:
            self.decoration_signature_button.active = self.can_purchase_selected_decoration()

    def get_current_overlay_action_button(self):
        if self.current_overlay == self.SHIPYARD:
            return self.shipyard_sticky_note_button
        if self.current_overlay == self.GEAR_LAB:
            return self.gear_lab_sticky_note_button
        if self.current_overlay == self.DECORATION_STORE:
            return self.decoration_signature_button
        return None

    def get_overlay_page_key(self):
        if self.is_decorating:
            return self.DECORATION_DEPOT
        return self.current_overlay

    def get_overlay_entities(self):
        if self.is_decorating:
            decorations = [
                decoration
                for decoration, amt in DataFiles.save_file["decoration_depot"].items()
                if amt > 0
            ]
            return decorations + [self.DELETE_DECORATION]
        if self.current_overlay == self.DEPOT:
            return [item for item, count in DataFiles.save_file["inventory"].items() if count > 0]
        if self.current_overlay == self.INTEL_CENTER:
            return [
                siren for siren in self.encountered_sirens
                if DataFiles.siren_data[siren]["hull_type"] == self.intel_center_filters[self.overlay_selected_filter]
            ]
        if self.current_overlay == self.SHIPYARD:
            return [
                shipgirl for shipgirl, shipgirl_info in DataFiles.shipgirl_data.items()
                if shipgirl not in DataFiles.save_file["shipgirls"]
                and shipgirl_info["faction"] in DataFiles.save_file["unlocked_factions"]
                and shipgirl_info["faction"] == self.shipyard_filters[self.overlay_selected_filter]
            ]
        if self.current_overlay == self.GEAR_LAB:
            if self.gear_lab_filters[self.overlay_selected_filter] == "AUX":
                return [
                    equip for equip, equip_data in DataFiles.equipment_data.items()
                    if equip_data["type"] == "aux"
                ]
            return [
                equip for equip, equip_data in DataFiles.equipment_data.items()
                if equip_data["type"] == "weapon"
                and equip_data["equippable_by"] == self.gear_lab_filters[self.overlay_selected_filter]
            ]
        if self.current_overlay == self.DECORATION_STORE:
            return [decoration for decoration in DataFiles.decoration_store]
        return []

    def get_overlay_icon_rects(self):
        if self.is_decorating:
            return [
                get_rect(
                    width=Box.WIDTH, height=Box.HEIGHT,
                    left=self.decoration_depot_overlay.left + (i%3)*(Box.WIDTH+Box.PADDING) + Box.PADDING,
                    top=self.decoration_depot_overlay.top + (i//3)*(Box.HEIGHT+Box.PADDING) + Box.PADDING
                )
                for i in range(9)
            ]
        if self.current_overlay in [self.DEPOT, self.DECORATION_STORE]:
            return self.warehouse_icons
        if self.current_overlay in [self.INTEL_CENTER, self.SHIPYARD, self.GEAR_LAB]:
            return self.dossier_icons
        return []

    def get_overlay_page_count(self, entities=None):
        if entities is None:
            entities = self.get_overlay_entities()

        page_size = len(self.get_overlay_icon_rects())
        if page_size == 0:
            return 1
        return max(1, math.ceil(len(entities) / page_size))

    def get_overlay_page(self, entities=None):
        page_count = self.get_overlay_page_count(entities)
        page_key = self.get_overlay_page_key()
        page = min(self.overlay_pages.get(page_key, 0), page_count - 1)
        page = max(0, page)
        self.overlay_pages[page_key] = page
        return page

    def get_visible_overlay_entities(self, entities=None):
        if entities is None:
            entities = self.get_overlay_entities()

        page_size = len(self.get_overlay_icon_rects())
        if page_size == 0:
            return []

        page = self.get_overlay_page(entities)
        start = page * page_size
        return entities[start:start + page_size]

    def position_overlay_page_buttons(self):
        if self.is_decorating:
            self.overlay_page_prev_button.rect.center = self.decoration_depot_overlay.bottomleft
            self.overlay_page_next_button.rect.center = self.decoration_depot_overlay.bottomright
            return
        elif self.current_overlay in [self.DEPOT, self.DECORATION_STORE]:
            self.overlay_page_prev_button.rect.topleft = self.warehouse_overlay.bottomleft
            self.overlay_page_next_button.rect.topright = self.warehouse_overlay.bottomright
            return
        elif self.current_overlay in [self.INTEL_CENTER, self.SHIPYARD, self.GEAR_LAB]:
            self.overlay_page_prev_button.rect.topleft = (
                self.dossier_page.left,
                self.dossier_page.top
            )
            self.overlay_page_next_button.rect.bottomright = (
                self.dossier_page.right,
                self.dossier_page.bottom
            )
            return
        else:
            return

    def refresh_overlay_page_buttons(self):
        entities = self.get_overlay_entities()
        page_count = self.get_overlay_page_count(entities)
        page = self.get_overlay_page(entities)
        self.position_overlay_page_buttons()
        self.overlay_page_prev_button.active = page_count > 1 and page > 0
        self.overlay_page_next_button.active = page_count > 1 and page < page_count - 1

    def change_overlay_page(self, delta):
        entities = self.get_overlay_entities()
        page_count = self.get_overlay_page_count(entities)
        page = self.get_overlay_page(entities)
        self.overlay_pages[self.get_overlay_page_key()] = min(page_count - 1, max(0, page + delta))
        self.refresh_overlay_page_buttons()

    def update_no_overlay(self, events):
        for quest in self.menu_manager.quest_manager.started_quests.values():
            quest.completed = quest.completed or quest.completion_criteria(self.menu_manager)

        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1 and self.can_start_no_overlay_camera_drag(event.pos):
                    self.camera_dragging = True
                    continue

            if event.type == pygame.MOUSEMOTION:
                if self.update_camera_drag(event):
                    continue

                buttons = [
                    self.open_select_sortie_menu_button,
                    self.open_depot_overlay_button,
                    self.open_shipyard_overlay_button,
                    self.open_gear_lab_overlay_button,
                    self.open_intel_center_overlay_button,
                    self.open_decoration_store_overlay_button,
                    self.toggle_decoration_mode_button,
                    *self.choose_faction_buttons,
                    *self.shipgirl_dialogue_options,
                ]
                for button in buttons:
                    button.hover(event.pos)
            if event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1 and self.camera_dragging:
                    self.camera_dragging = False
                    continue

                click = False

                selected_quest = self.menu_manager.quest_manager.selected_quest
                if selected_quest is not None:
                    selected_quest = self.menu_manager.quest_manager.selected_quest
                    close_dialogue = selected_quest.go_next(self.menu_manager, event.pos)
                    if close_dialogue:
                        if selected_quest.completed:
                            DataFiles.save_file["quests"][selected_quest.quest_id] = "completed"
                        elif selected_quest.started:
                            DataFiles.save_file["quests"][selected_quest.quest_id] = "in_progress"
                        self.menu_manager.quest_manager.selected_quest = None
                    continue
                
                buttons = [
                    self.open_select_sortie_menu_button,
                    self.open_depot_overlay_button,
                    self.open_shipyard_overlay_button,
                    self.open_gear_lab_overlay_button,
                    self.open_intel_center_overlay_button,
                    self.open_decoration_store_overlay_button,
                    self.toggle_decoration_mode_button,
                ]
                click = (
                    click
                    or self.menu_manager.quest_manager.select_quest(event.pos)
                    or any(button.click(event.pos) for button in buttons)
                )

                for choose_faction_button in self.choose_faction_buttons:
                    click = click or choose_faction_button.click(event.pos)

                if click:
                    DataFiles.sfx["click"].play()
                    continue

                if self.hovered_shipgirl is not None:
                    for option in self.shipgirl_dialogue_options:
                        if option.click(event.pos):
                            DataFiles.sfx["click"].play()
                        option.active = False
                    if self.hovered_shipgirl is not None:
                        self.hovered_shipgirl.pick_new_wander_target()
                        self.hovered_shipgirl = None
                    continue

                for shipgirl in self.menu_manager.available_shipgirls:
                    if shipgirl.rect.collidepoint(event.pos):
                        DataFiles.sfx["click"].play()
                        self.hovered_shipgirl = shipgirl
                        if self.hovered_shipgirl.interacting_decoration is None:
                            self.hovered_shipgirl.sprite.set_animation(Live2D.BOUNCE_ANIMATION)
                        self.position_shipgirl_dialogue_options()
                        for option in self.shipgirl_dialogue_options:
                            option.active = True

    def exit_overlay(self, mouseup_event):
        clicked_page_button = (
            self.overlay_page_prev_button.active
            and self.overlay_page_prev_button.rect.collidepoint(mouseup_event.pos)
        ) or (
            self.overlay_page_next_button.active
            and self.overlay_page_next_button.rect.collidepoint(mouseup_event.pos)
        )
        if self.current_overlay in [self.DEPOT, self.DECORATION_STORE]:
            left_overlay = self.warehouse_overlay
            right_overlay = self.clipboard_bg
            clicked_right_overlay = right_overlay.collidepoint(mouseup_event.pos)
        if self.current_overlay in [self.INTEL_CENTER, self.SHIPYARD, self.GEAR_LAB]:
            left_overlay = self.dossier_overlay
            right_overlay = self.blueprint_page
            action_button = self.get_current_overlay_action_button()
            clicked_right_overlay = (
                right_overlay.collidepoint(mouseup_event.pos)
                or (
                    action_button is not None
                    and action_button.active
                    and self.sticky_note_page.collidepoint(mouseup_event.pos)
                )
            )

        if (
            not left_overlay.collidepoint(mouseup_event.pos)
            and not clicked_page_button
            and (
                self.overlay_selected_entity is None
                or not clicked_right_overlay
            )
        ):
            self.current_overlay = self.NO_OVERLAY
            self.overlay_selected_entity = None
            self.refresh_overlay_action_buttons()
            self.overlay_page_prev_button.active = False
            self.overlay_page_next_button.active = False
            self.overlay_selected_filter = 0
            return True
        return False

    def select_filter(self, mouseup_event):
        if self.current_overlay in [self.DEPOT, self.DECORATION_STORE]:
            return
        
        entity_filters = getattr(self, f"{self.current_overlay}_filters")
        for i, (cat, rect) in enumerate(zip(entity_filters, self.dossier_tabs)):
            if rect.collidepoint(mouseup_event.pos):
                DataFiles.sfx["click"].play()
                self.overlay_selected_filter = i
                self.overlay_pages[self.current_overlay] = 0
                self.refresh_overlay_page_buttons()

    def select_entity(self, mouseup_event):
        entities = self.get_visible_overlay_entities()
        rects = self.get_overlay_icon_rects()

        for entity, rect in zip(entities, rects):
            if rect.collidepoint(mouseup_event.pos):
                DataFiles.sfx["click"].play()
                self.overlay_selected_entity = entity

                if self.current_overlay in [self.DEPOT, self.INTEL_CENTER]:
                    setattr(self, f"visited_{self.current_overlay}", True)

                self.refresh_overlay_action_buttons()

    def draw_overlay_page_buttons(self, surface, font_registry):
        self.refresh_overlay_page_buttons()
        if self.get_overlay_page_count() <= 1:
            return

        if self.current_overlay in [self.INTEL_CENTER, self.SHIPYARD, self.GEAR_LAB]:
            return

        self.overlay_page_prev_button.draw(surface, font_registry)
        self.overlay_page_next_button.draw(surface, font_registry)

    def draw_dossier_overlay(self, surface, font_registry):
        entity_filters = getattr(self, f"{self.current_overlay}_filters")
        pygame.draw.rect(surface, Color.DOSSIER, self.dossier_bg)
        for i, (cat, rect) in enumerate(zip(entity_filters, self.dossier_tabs)):
            if self.overlay_selected_filter == i:
                color = Color.DOSSIER
            else:
                color = Color.DOSSIER_BACK
            tab_extra_width = Box.WIDTH - rect.width
            tab_polygon = [
                rect.bottomleft,
                rect.topleft,
                rect.topright,
                pygame.Vector2(rect.bottomright) + pygame.Vector2(tab_extra_width, 0),
            ]
            pygame.draw.polygon(surface, color, tab_polygon)
            icon = DataFiles.sprites["user_interface"][cat]
            icon_rect = icon.get_rect()
            icon_rect.centerx = rect.left + rect.height/2
            icon_rect.centery = rect.top + rect.height/2
            surface.blit(icon, icon_rect)

        entities = self.get_visible_overlay_entities()
        self.refresh_overlay_page_buttons()
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
            (-7, 78, "yellow"),
            (-5, 159, "green"),
            (-12, 203, "pink"),
        ]
        for sticky_tab_offsetx, sticky_tab_offsety, sticky_tab_color in sticky_tabs:
            sticky_tab_sprite = DataFiles.sprites["props"][f"sticky_tab_{sticky_tab_color}"]
            sticky_tab_rect = sticky_tab_sprite.get_rect()
            sticky_tab_rect.centerx = self.dossier_page.left + sticky_tab_offsetx
            sticky_tab_rect.centery = self.dossier_page.top + sticky_tab_offsety
            surface.blit(sticky_tab_sprite, sticky_tab_rect)

        page_turn_size = self.overlay_page_next_button.rect.width
        if self.overlay_page_next_button.active:
            fold_top = (self.dossier_page.right, self.dossier_page.bottom - page_turn_size)
            fold_left = (self.dossier_page.right - page_turn_size, self.dossier_page.bottom)
            fold_tip = (
                self.dossier_page.right - page_turn_size,
                self.dossier_page.bottom - page_turn_size
            )
            page_polygon = [
                self.dossier_page.topleft,
                self.dossier_page.topright,
                fold_top,
                fold_left,
                self.dossier_page.bottomleft,
            ]
            folded_corner = [
                fold_top,
                fold_left,
                fold_tip,
            ]
            pygame.draw.polygon(surface, Color.DOSSIER_PAGE, page_polygon)
            if self.overlay_page_next_button.hovered:
                folded_corner_color = (196, 196, 188)
            else:
                folded_corner_color = (224, 224, 216)
            pygame.draw.polygon(surface, folded_corner_color, folded_corner)
            pygame.draw.line(surface, (196, 196, 188), fold_top, fold_left, width=Box.OUTLINE_WIDTH)
            pygame.draw.line(surface, (238, 238, 232), fold_left, fold_tip, width=Box.OUTLINE_WIDTH)
        else:
            pygame.draw.rect(surface, Color.DOSSIER_PAGE, self.dossier_page)

        if self.overlay_page_prev_button.active:
            prev_corner = [
                self.dossier_page.topleft,
                (self.dossier_page.left + page_turn_size, self.dossier_page.top),
                (self.dossier_page.left, self.dossier_page.top + page_turn_size),
            ]
            if self.overlay_page_prev_button.hovered:
                prev_corner_color = (196, 196, 188)
            else:
                prev_corner_color = (224, 224, 216)
            pygame.draw.polygon(surface, prev_corner_color, prev_corner)
        red_circle_sprite = DataFiles.sprites["props"]["red_circle"]
        red_circle_rect = red_circle_sprite.get_rect()
        red_circle_rect.topleft = (-2*Box.WIDTH, -2*Box.HEIGHT)
        for entity, rect in zip(entities, self.dossier_icons):
            image = DataFiles.get_entity_sprite(entity)
            image_rect = image.get_rect()
            image_rect.center = rect.center
            surface.blit(image, image_rect)
            if self.overlay_selected_entity == entity:
                red_circle_rect.center = rect.center
            pygame.draw.rect(surface, Color.BLACK, rect, width=Box.OUTLINE_WIDTH)
        surface.blit(red_circle_sprite, red_circle_rect)

        paperclip_sprite = DataFiles.sprites["props"]["diagonal_paperclip"]
        paperclip_rect = paperclip_sprite.get_rect()
        paperclip_rect.left = self.dossier_bg.left - 16 # TODO paper clip offset magic number
        paperclip_rect.top = self.dossier_bg.top - 8
        surface.blit(paperclip_sprite, paperclip_rect)

        classified_sprite = pygame.transform.scale_by(DataFiles.sprites["props"]["classified"], 1.5)
        classified_rect = classified_sprite.get_rect()
        classified_rect.topright = self.dossier_bg.topright
        surface.blit(classified_sprite, classified_rect)

        coffee_ring_sprite = pygame.transform.scale_by(DataFiles.sprites["props"]["coffee_ring"], 1.5)
        coffee_ring_rect = coffee_ring_sprite.get_rect()
        coffee_ring_rect.bottomleft = self.dossier_bg.bottomleft
        surface.blit(coffee_ring_sprite, coffee_ring_rect)
        self.draw_overlay_page_buttons(surface, font_registry)

    def draw_sticky_note_overlay(self, surface, font_registry):
        action_button = self.get_current_overlay_action_button()
        if action_button is None or not action_button.active:
            return

        misaligned_pages = [
            (4, pygame.Vector2(-5, 4), Color.STICKY_NOTE_BACK),
            (-5, pygame.Vector2(5, -3), (239, 207, 87)),
            (2, pygame.Vector2(2, 4), (247, 220, 105)),
        ]
        for rotated_angle, offset, color in misaligned_pages:
            pygame.draw.polygon(
                surface,
                color,
                Box.get_rotated_rect_polygon(self.sticky_note_page, rotated_angle, offset)
            )
        pygame.draw.rect(surface, Color.STICKY_NOTE, self.sticky_note_page)
        action_button.draw(surface, font_registry)

    def draw_blueprint_overlay(self, surface, font_registry):
        if self.overlay_selected_entity is None:
            return

        font_height = 10
        blueprint_name_pos = pygame.Vector2(
            self.blueprint_page.centerx,
            self.blueprint_page.top + font_height/2 + Box.PADDING
        )
        blueprint_highlight_icon = get_rect(
            width=Box.WIDTH, height=Box.HEIGHT,
            centerx=self.blueprint_page.centerx,
            top=blueprint_name_pos.y + font_height/2 + Box.PADDING
        )
        num_icons_per_row = 3
        blueprint_icons = [
            get_rect(
                width=Box.WIDTH, height=Box.HEIGHT,
                centerx=self.blueprint_page.centerx+(i%num_icons_per_row-1)*(Box.WIDTH+Box.PADDING),
                bottom=self.blueprint_page.bottom-2*Box.PADDING-Box.HEIGHT+(i//num_icons_per_row)*(Box.HEIGHT+Box.PADDING)
            ) for i in range(2*num_icons_per_row)
        ]

        misaligned_pages = [
            (-5, pygame.Vector2(-7, 6), Color.BLUEPRINT_PAGE_BACK),
            (4, pygame.Vector2(7, -4), (34, 62, 125)),
            (-2, pygame.Vector2(3, 5), (45, 76, 145)),
        ]
        for rotated_angle, offset, color in misaligned_pages:
            pygame.draw.polygon(
                surface,
                color,
                Box.get_rotated_rect_polygon(self.blueprint_page, rotated_angle, offset)
            )
        pygame.draw.rect(surface, Color.BLUEPRINT_PAGE, self.blueprint_page)
        font_registry["big_pixel"].render(surface, self.overlay_selected_entity, blueprint_name_pos, Color.WHITE, 1, style="center")
        surface.blit(DataFiles.get_entity_sprite(self.overlay_selected_entity), blueprint_highlight_icon)
        pygame.draw.rect(surface, Color.WHITE, blueprint_highlight_icon, width=Box.OUTLINE_WIDTH)

        def draw_blueprint_divider(label, y):
            divider_margin = 2*Box.PADDING
            label_left = self.blueprint_page.left + divider_margin
            line_left = label_left + font_registry["big_pixel"].get_width(label, 1, 0) + Box.PADDING
            line_right = self.blueprint_page.right - divider_margin
            font_registry["big_pixel"].render(surface, label, (label_left, y), Color.WHITE, 1, style="centerleft")
            pygame.draw.line(
                surface,
                Color.WHITE,
                (line_left, y),
                (line_right, y),
                width=Box.OUTLINE_WIDTH
            )

        if self.current_overlay == self.INTEL_CENTER:
            selected_siren = DataFiles.siren_data[self.overlay_selected_entity]
            drop_rates = selected_siren["drops"]
            icons = [(drop, str(drop_rate)) for drop, drop_rate in drop_rates.items()]
            rewards_header = "drops"
            info = { # TODO scale stats by siren level
                "hull_type": selected_siren.get("hull_type"),
                "max_hp": selected_siren["max_hp"][0],
                "evasion": selected_siren["evasion"][0],
                "firepower": selected_siren["firepower"][0],
                "reload": selected_siren["reload"][0],
                "target_pref": selected_siren["target_pref"],
                "EXP": selected_siren["reward_exp"][0],
            }
        if self.current_overlay == self.SHIPYARD:
            selected_shipgirl = DataFiles.shipgirl_data[self.overlay_selected_entity]
            hull_type = selected_shipgirl["hull_type"]
            unique_item = selected_shipgirl["unique_item"]
            inventory = DataFiles.save_file["inventory"]
            specialized_wisdom_cubes = DataFiles.save_file["specialized_wisdom_cubes"]
            wisdom_cube_count = 1 if self.overlay_selected_entity in specialized_wisdom_cubes else inventory.get("wisdom_cube", 0)
            research_reqs = [
                (f"{hull_type}_blueprint", inventory.get(f"{hull_type}_blueprint", 0)),
                ("wisdom_cube", wisdom_cube_count),
                (unique_item, inventory.get(unique_item, 0))
            ]
            icons = [
                (research_req, f"{count}/1")
                for research_req, count in research_reqs
            ]
            rewards_header = "materials"
            hull_type = selected_shipgirl.get("hull_type")
            selected_entity_stats = DataFiles.stats_data[hull_type]
            research_shipgirl_exp = specialized_wisdom_cubes.get(self.overlay_selected_entity, 0)
            info = {
                "hull_type": hull_type,
                "max_hp": Stats.stat(research_shipgirl_exp, *selected_entity_stats["max_hp"]),
                "evasion": Stats.stat(research_shipgirl_exp, *selected_entity_stats["evasion"]),
                "firepower": Stats.stat(research_shipgirl_exp, *selected_entity_stats["firepower"]),
                "reload": Stats.stat(research_shipgirl_exp, *selected_entity_stats["reload"]),
                "EXP": research_shipgirl_exp
            }
        if self.current_overlay == self.GEAR_LAB:
            selected_equipment = DataFiles.equipment_data[self.overlay_selected_entity]
            crafting_reqs = selected_equipment["craft_reqs"]
            inventory = DataFiles.save_file["inventory"]
            icons = [
                (material, f"{inventory.get(material,0)}/{req}")
                for material, req in crafting_reqs.items()
            ]
            rewards_header = "materials"
            info = {
                "hull_type": selected_equipment.get("equippable_by"),
                "max_hp": selected_equipment.get("max_hp"),
                "evasion": selected_equipment.get("evasion"),
                "firepower": selected_equipment.get("firepower"),
                "reload": selected_equipment.get("reload"),
                "shell_type": selected_equipment.get("shell_type"),
            }

        icon_size = Box.WIDTH / 2
        stats_divider_y = blueprint_highlight_icon.bottom + Box.PADDING + font_height/2
        rewards_divider_y = blueprint_icons[0].top - Box.PADDING - font_height/2
        draw_blueprint_divider("stats", stats_divider_y)
        draw_blueprint_divider(rewards_header, rewards_divider_y)

        left_align = [blueprint_icons[0].left + Box.PADDING,self.blueprint_page.centerx + Box.PADDING]
        y = stats_divider_y + font_height/2 + Box.PADDING
        info_index = 0
        for info_key, info_value in info.items():
            if info_value is None:
                continue

            x = left_align[info_index%2]
            if info_key in DataFiles.sprites["user_interface"]:
                info_icon = DataFiles.sprites["user_interface"][info_key]
                info_rect = info_icon.get_rect()
                info_rect.topleft = (x, y)
                surface.blit(info_icon, info_rect)
            else:
                info_rect = get_rect(width=icon_size, height=icon_size, left=x, top=y)
                font_registry["big_pixel"].render(surface,str(info_key),info_rect.center,Color.WHITE,1,style="center")
            font_registry["big_pixel"].render(surface,str(info_value),(info_rect.right + Box.PADDING, info_rect.centery),Color.WHITE,1,style="centerleft",)
            info_index += 1
            if info_index % 2 == 0:
                y += icon_size
            
        for (icon_name, icon_text), rect in zip(icons, blueprint_icons):
            surface.blit(DataFiles.get_entity_sprite(icon_name), rect)
            pygame.draw.rect(surface, Color.WHITE, rect, width=Box.OUTLINE_WIDTH)
            xy = (rect.centerx, rect.top+0.67*rect.height)
            font_registry["big_pixel"].render(surface, icon_text, xy, Color.WHITE, 1, style="center", outline_color=Color.BLACK)

        pencil_sprite = DataFiles.sprites["props"]["pencil"]
        pencil_rect = pencil_sprite.get_rect()
        pencil_rect.right = self.blueprint_page.right + Box.WIDTH/4 # TODO alignment magic number
        pencil_rect.bottom = self.blueprint_page.bottom + Box.HEIGHT/2

        ruler_sprite = DataFiles.sprites["props"]["ruler"]
        ruler_rect = ruler_sprite.get_rect()
        ruler_rect.center = pencil_rect.midleft
        surface.blit(ruler_sprite, ruler_rect)
        surface.blit(pencil_sprite, pencil_rect)

        compass_sprite = DataFiles.sprites["props"]["compass"]
        compass_rect = compass_sprite.get_rect()
        compass_rect.left = self.blueprint_page.left - Box.WIDTH/4 # TODO alignment magic number
        compass_rect.bottom = self.blueprint_page.bottom + Box.HEIGHT/2
        surface.blit(compass_sprite, compass_rect)
        self.draw_sticky_note_overlay(surface, font_registry)

    def draw_warehouse_overlay(self, surface, font_registry):
        pygame.draw.rect(surface, Color.CARGO_BOX_BACK, self.warehouse_overlay)

        entities = self.get_visible_overlay_entities()
        for entity, rect in zip(entities, self.warehouse_icons):
            pygame.draw.rect(surface, Color.CARGO_BOX, rect)
            image = DataFiles.get_entity_sprite(entity)
            image_rect = image.get_rect()
            image_rect.center = rect.center
            surface.blit(image, image_rect)
            pygame.draw.rect(surface, Color.CARGO_BOX_OUTLINE, image_rect, width=2*Box.OUTLINE_WIDTH)

        cargo_box_sprite = DataFiles.sprites["props"]["cargo_box"]
        cargo_box_rect = cargo_box_sprite.get_rect()
        for cargo_box_pos in [
            pygame.Vector2(self.warehouse_overlay.bottomleft),
            pygame.Vector2(self.warehouse_overlay.bottomleft) + pygame.Vector2(cargo_box_rect.width, 0),
            pygame.Vector2(self.warehouse_overlay.bottomleft) + pygame.Vector2(-cargo_box_rect.width, 0),

            pygame.Vector2(self.warehouse_overlay.bottomright),
            pygame.Vector2(self.warehouse_overlay.bottomright) + pygame.Vector2(0, -cargo_box_rect.height),
            pygame.Vector2(self.warehouse_overlay.bottomright) + pygame.Vector2(-cargo_box_rect.width, 0),
        ]:
            cargo_box_rect.center = cargo_box_pos
            surface.blit(cargo_box_sprite, cargo_box_rect)
        forklift_sprite = pygame.transform.scale_by(
            pygame.transform.flip(
                DataFiles.sprites["props"]["forklift"],
                flip_x=self.forklift_dx < 0,
                flip_y=False
            ),
            (min(2*abs(2*self.forklift_pause - 1), 1), 1)
        )
        forklift_rect = forklift_sprite.get_rect()
        forklift_rect.center = (
            pygame.Vector2(self.warehouse_overlay.bottomleft)
            + pygame.Vector2(self.forklift_x * self.warehouse_overlay.width, 0)
        )
        surface.blit(forklift_sprite, forklift_rect)
        for cargo_box_pos in [
            pygame.Vector2(self.warehouse_overlay.bottomleft) + pygame.Vector2(cargo_box_rect.width/2, cargo_box_rect.height/2),
            pygame.Vector2(self.warehouse_overlay.bottomleft) + pygame.Vector2(-cargo_box_rect.width/2, cargo_box_rect.height/2),

            pygame.Vector2(self.warehouse_overlay.bottomright) + pygame.Vector2(-cargo_box_rect.width/2, cargo_box_rect.height/2),
            pygame.Vector2(self.warehouse_overlay.bottomright) + pygame.Vector2(-cargo_box_rect.width*3/2, cargo_box_rect.height/2),
        ]:
            cargo_box_rect.center = cargo_box_pos
            surface.blit(cargo_box_sprite, cargo_box_rect)

        warehouse_decoration_top = self.warehouse_overlay.top - Box.WIDTH/8
        corner_rope_sprite = DataFiles.sprites["props"]["corner_rope"]
        corner_rope_rect = corner_rope_sprite.get_rect()
        corner_rope_rect.right = self.warehouse_overlay.right + Box.WIDTH/8 # TODO magic number
        corner_rope_rect.top = warehouse_decoration_top
        surface.blit(corner_rope_sprite, corner_rope_rect)

        big_corner_rope_sprite = DataFiles.sprites["props"]["big_corner_rope"]
        big_corner_rope_rect = big_corner_rope_sprite.get_rect()
        big_corner_rope_rect.right = self.warehouse_overlay.right + Box.WIDTH/8 # TODO magic number
        big_corner_rope_rect.top = warehouse_decoration_top
        surface.blit(big_corner_rope_sprite, big_corner_rope_rect)

        top_rope_sprite = DataFiles.sprites["props"]["top_rope"]
        top_rope_rect = top_rope_sprite.get_rect()
        top_rope_rect.left = self.warehouse_overlay.centerx + Box.WIDTH/4
        top_rope_rect.top = warehouse_decoration_top
        surface.blit(top_rope_sprite, top_rope_rect)

        big_top_rope_sprite = DataFiles.sprites["props"]["big_top_rope"]
        big_top_rope_rect = big_top_rope_sprite.get_rect()
        big_top_rope_rect.right = self.warehouse_overlay.centerx
        big_top_rope_rect.top = warehouse_decoration_top
        surface.blit(big_top_rope_sprite, big_top_rope_rect)

        rope_hook_sprite = DataFiles.sprites["props"]["rope_hook"]
        rope_hook_rect = rope_hook_sprite.get_rect()
        rope_hook_rect.centerx = self.warehouse_overlay.left + Box.PADDING
        rope_hook_rect.top = warehouse_decoration_top
        surface.blit(rope_hook_sprite, rope_hook_rect)

        aisle_sign_rect = get_rect(
            width=Box.WIDTH,
            height=Box.HEIGHT,
            centerx=rope_hook_rect.centerx,
            bottom=rope_hook_rect.bottom
        )
        font = font_registry["big_pixel"]
        font.render(
            surface,
            "aisle",
            (
                aisle_sign_rect.centerx,
                aisle_sign_rect.centery - 1.25*font.font_height
            ),
            Color.BLACK,
            1,
            style="center"
        )
        font.render(
            surface,
            str(self.get_overlay_page() + 1),
            (
                aisle_sign_rect.centerx,
                aisle_sign_rect.centery + font.font_height/2
            ),
            Color.BLACK,
            2,
            style="center"
        )

        lightbulb_sprite = DataFiles.sprites["props"]["lightbulb"]
        lightbulb_rect = lightbulb_sprite.get_rect()
        lightbulb_rect.left = self.warehouse_overlay.left + Box.WIDTH
        lightbulb_rect.top = warehouse_decoration_top
        surface.blit(lightbulb_sprite, lightbulb_rect)

        lightbulb_light_sprite = DataFiles.sprites["props"]["lightbulb_light"]
        lightbulb_light_rect = lightbulb_light_sprite.get_rect()
        lightbulb_light_rect.centerx = lightbulb_rect.centerx
        lightbulb_light_rect.bottom = lightbulb_rect.bottom + Box.HEIGHT/4
        surface.blit(lightbulb_light_sprite, lightbulb_light_rect, special_flags=pygame.BLEND_RGB_ADD)
        self.draw_overlay_page_buttons(surface, font_registry)

    @staticmethod
    def draw_dashed_rect(surface, color, rect, dash_length=8, gap_length=4, width=2):
        right = rect.right - 1
        bottom = rect.bottom - 1
        dash_step = dash_length + gap_length

        for x in range(rect.left, right + 1, dash_step):
            dash_right = min(x + dash_length, right)
            pygame.draw.line(surface, color, (x, rect.top), (dash_right, rect.top), width)
            pygame.draw.line(surface, color, (x, bottom), (dash_right, bottom), width)

        for y in range(rect.top, bottom + 1, dash_step):
            dash_bottom = min(y + dash_length, bottom)
            pygame.draw.line(surface, color, (rect.left, y), (rect.left, dash_bottom), width)
            pygame.draw.line(surface, color, (right, y), (right, dash_bottom), width)

    def draw_depot_stock_record(self, surface, font_registry):
        font = font_registry["big_pixel"]
        content_left = self.clipboard_page.left + Box.PADDING
        content_width = self.clipboard_page.width - 2*Box.PADDING
        content_top = self.clipboard_page.top + Box.HEIGHT/4 + Box.PADDING

        font.render(
            surface,
            "warehouse stock record",
            (content_left, content_top),
            Color.BLACK,
            1,
            style="topleft"
        )
        header_rule_y = content_top + font.font_height + Box.PADDING
        pygame.draw.line(
            surface,
            Color.BLACK,
            (content_left, header_rule_y),
            (content_left + content_width, header_rule_y),
            width=Box.OUTLINE_WIDTH
        )

        display_name = self.overlay_selected_entity.replace("_", " ")
        name_top = header_rule_y + Box.PADDING
        name_height = font.get_height(display_name, 2, content_width)
        font.render(
            surface,
            display_name,
            (content_left, name_top),
            Color.BLACK,
            2,
            style="topleft",
            box_width=content_width
        )

        identity_rect = get_rect(
            width=content_width,
            height=Box.HEIGHT,
            left=content_left,
            top=name_top + name_height + Box.PADDING
        )
        icon_rect = get_rect(
            width=Box.WIDTH,
            height=Box.HEIGHT,
            left=identity_rect.left,
            top=identity_rect.top
        )
        quantity_rect = get_rect(
            width=identity_rect.width - icon_rect.width,
            height=identity_rect.height,
            left=icon_rect.right,
            top=identity_rect.top
        )

        surface.blit(DataFiles.get_entity_sprite(self.overlay_selected_entity), icon_rect)
        pygame.draw.rect(surface, Color.BLACK, identity_rect, width=Box.OUTLINE_WIDTH)
        pygame.draw.line(
            surface,
            Color.BLACK,
            icon_rect.topright,
            icon_rect.bottomright,
            width=Box.OUTLINE_WIDTH
        )

        quantity_header_rule_y = quantity_rect.top + font.font_height + Box.PADDING
        font.render(
            surface,
            "qty",
            (quantity_rect.centerx, (quantity_rect.top + quantity_header_rule_y) / 2),
            Color.BLACK,
            1,
            style="center"
        )
        pygame.draw.line(
            surface,
            Color.BLACK,
            (quantity_rect.left, quantity_header_rule_y),
            (quantity_rect.right, quantity_header_rule_y),
            width=Box.OUTLINE_WIDTH
        )
        quantity = DataFiles.save_file["inventory"].get(self.overlay_selected_entity, 0)
        font.render(
            surface,
            str(quantity),
            (quantity_rect.centerx, quantity_header_rule_y + Box.PADDING + font.font_height),
            Color.BLACK,
            2,
            style="center"
        )
        font.render(
            surface,
            "in stock",
            (quantity_rect.centerx, quantity_rect.bottom - Box.PADDING - font.font_height/2),
            Color.BLACK,
            1,
            style="center"
        )

        description_label_top = identity_rect.bottom + Box.PADDING
        font.render(
            surface,
            "description",
            (content_left, description_label_top),
            Color.BLACK,
            1,
            style="topleft"
        )
        description_top = description_label_top + font.font_height + Box.PADDING
        description_bottom = self.clipboard_page.bottom - Box.PADDING
        line_spacing = font.font_height + font.padding
        ruled_line_color = (210, 210, 200)
        for line_y in range(
            round(description_top + font.font_height + 2),
            round(description_bottom),
            line_spacing
        ):
            pygame.draw.line(
                surface,
                ruled_line_color,
                (content_left, line_y),
                (content_left + content_width, line_y)
            )

        description = DataFiles.item_descriptions.get(
            self.overlay_selected_entity,
            "no description"
        )
        font.render(
            surface,
            description,
            (content_left, description_top),
            Color.BLACK,
            1,
            style="topleft",
            box_width=content_width
        )

    def draw_decoration_purchase_form(self, surface, font_registry):
        font = font_registry["big_pixel"]
        content_left = self.clipboard_page.left + Box.PADDING
        content_width = self.clipboard_page.width - 2*Box.PADDING
        content_top = self.clipboard_page.top + Box.HEIGHT/4 + Box.PADDING

        font.render(
            surface,
            "decoration purchase form",
            (content_left, content_top),
            Color.BLACK,
            1,
            style="topleft"
        )
        header_rule_y = content_top + font.font_height + Box.PADDING
        pygame.draw.line(
            surface,
            Color.BLACK,
            (content_left, header_rule_y),
            (content_left + content_width, header_rule_y),
            width=Box.OUTLINE_WIDTH
        )

        display_name = self.overlay_selected_entity.replace("_", " ")
        name_top = header_rule_y + Box.PADDING
        name_height = font.get_height(display_name, 2, content_width)
        font.render(
            surface,
            display_name,
            (content_left, name_top),
            Color.BLACK,
            2,
            style="topleft",
            box_width=content_width
        )

        product_rect = get_rect(
            width=content_width,
            height=Box.HEIGHT,
            left=content_left,
            top=name_top + name_height + Box.PADDING
        )
        icon_rect = get_rect(
            width=Box.WIDTH,
            height=Box.HEIGHT,
            left=product_rect.left,
            top=product_rect.top
        )
        field_width = (product_rect.width - icon_rect.width) / 2
        quantity_rect = get_rect(
            width=field_width,
            height=product_rect.height,
            left=icon_rect.right,
            top=product_rect.top
        )
        price_rect = get_rect(
            width=field_width,
            height=product_rect.height,
            left=quantity_rect.right,
            top=product_rect.top
        )

        surface.blit(DataFiles.get_entity_sprite(self.overlay_selected_entity), icon_rect)
        pygame.draw.rect(surface, Color.BLACK, product_rect, width=Box.OUTLINE_WIDTH)
        for divider_x in [icon_rect.right, quantity_rect.right]:
            pygame.draw.line(
                surface,
                Color.BLACK,
                (divider_x, product_rect.top),
                (divider_x, product_rect.bottom),
                width=Box.OUTLINE_WIDTH
            )

        owned_count = self.get_owned_decoration_count(self.overlay_selected_entity)
        for field_rect, label, value, footer in [
            (quantity_rect, "qty", owned_count, "owned"),
            (price_rect, "price", self.DECORATION_PRICE, "coin"),
        ]:
            field_header_rule_y = field_rect.top + font.font_height + Box.PADDING
            font.render(
                surface,
                label,
                (field_rect.centerx, (field_rect.top + field_header_rule_y) / 2),
                Color.BLACK,
                1,
                style="center"
            )
            pygame.draw.line(
                surface,
                Color.BLACK,
                (field_rect.left, field_header_rule_y),
                (field_rect.right, field_header_rule_y),
                width=Box.OUTLINE_WIDTH
            )
            font.render(
                surface,
                str(value),
                (field_rect.centerx, field_header_rule_y + Box.PADDING + font.font_height),
                Color.BLACK,
                2,
                style="center"
            )
            font.render(
                surface,
                footer,
                (field_rect.centerx, field_rect.bottom - Box.PADDING - font.font_height/2),
                Color.BLACK,
                1,
                style="center"
            )

        description_label_top = product_rect.bottom + Box.PADDING
        font.render(
            surface,
            "description",
            (content_left, description_label_top),
            Color.BLACK,
            1,
            style="topleft"
        )
        description_rule_y = description_label_top + font.font_height + Box.PADDING
        pygame.draw.line(
            surface,
            Color.BLACK,
            (content_left, description_rule_y),
            (content_left + content_width, description_rule_y),
            width=Box.OUTLINE_WIDTH
        )
        description_top = description_rule_y + Box.PADDING
        description = DataFiles.decoration_store[self.overlay_selected_entity]["description"]
        font.render(
            surface,
            description,
            (content_left, description_top),
            Color.BLACK,
            1,
            style="topleft",
            box_width=content_width
        )

        signature_rect = self.decoration_signature_button.rect
        approval_label_pos = (
            signature_rect.left,
            signature_rect.top - Box.PADDING - font.font_height
        )
        font.render(
            surface,
            "purchase approval",
            approval_label_pos,
            Color.BLACK,
            1,
            style="topleft"
        )

        has_funds = (
            DataFiles.save_file["inventory"].get("decoration_coin", 0)
            >= self.DECORATION_PRICE
        )
        stamp_box_color = Color.BLACK if has_funds else Color.CLIPBOARD_CLIP
        self.draw_dashed_rect(
            surface,
            stamp_box_color,
            signature_rect,
            width=Box.OUTLINE_WIDTH
        )
        font.render(
            surface,
            "stamp here",
            signature_rect.center,
            stamp_box_color,
            1,
            style="center"
        )

        coin_count = DataFiles.save_file["inventory"].get("decoration_coin", 0)

        coin_sprite = DataFiles.sprites["props"]["decoration_coin"]
        coin_rect = coin_sprite.get_rect()
        coin_rect.centerx = self.clipboard_page.right
        coin_rect.top = self.clipboard_page.top

        for _ in range(coin_count):
            coin_rect.y -= 6 # TODO decoration coin height magic number
            surface.blit(coin_sprite, coin_rect)

        smiley_sprite = DataFiles.sprites["props"]["smiley"]
        smiley_rect = smiley_sprite.get_rect()
        smiley_rect.center = self.decoration_stamp_animation_pos
        if self.decoration_stamp_animation_timer > 0:
            elapsed = self.DECORATION_STAMP_ANIMATION_DURATION - self.decoration_stamp_animation_timer
            if elapsed >= self.DECORATION_STAMP_DISAPPEAR_TIME:
                progress = (
                    self.decoration_stamp_animation_timer
                    / (self.DECORATION_STAMP_ANIMATION_DURATION - self.DECORATION_STAMP_DISAPPEAR_TIME)
                )
                smiley_sprite.set_alpha(int(255 * progress))
                surface.blit(smiley_sprite, smiley_rect)
            elif elapsed >= self.DECORATION_STAMP_DOWN_TIME:
                smiley_sprite.set_alpha(255)
                surface.blit(smiley_sprite, smiley_rect)

        stamp_sprite = DataFiles.sprites["props"]["stamp"]
        stamp_rect = stamp_sprite.get_rect()
        if self.decoration_stamp_animation_timer <= 0:
            stamp_rect.center = self.clipboard_page.bottomleft
            surface.blit(stamp_sprite, stamp_rect)
        else:
            elapsed = self.DECORATION_STAMP_ANIMATION_DURATION - self.decoration_stamp_animation_timer
            target_pos = pygame.Vector2(self.decoration_stamp_animation_pos)
            above_pos = target_pos - pygame.Vector2(0, Box.HEIGHT)
            if elapsed >= self.DECORATION_STAMP_LIFT_TIME:
                stamp_rect.centerx = above_pos.x
                stamp_rect.bottom = above_pos.y + Box.HEIGHT/2
                surface.blit(stamp_sprite, stamp_rect)
            elif elapsed >= self.DECORATION_STAMP_DOWN_TIME:
                progress = min(
                    1,
                    (elapsed - self.DECORATION_STAMP_DOWN_TIME)
                    / (self.DECORATION_STAMP_LIFT_TIME - self.DECORATION_STAMP_DOWN_TIME)
                )
                stamp_pos = target_pos.lerp(above_pos, progress)
                stamp_rect.centerx = stamp_pos.x
                stamp_rect.bottom = stamp_pos.y + Box.HEIGHT/2
                surface.blit(stamp_sprite, stamp_rect)
            else:
                progress = min(1, elapsed / self.DECORATION_STAMP_DOWN_TIME)
                stamp_pos = above_pos.lerp(target_pos, progress)
                stamp_rect.centerx = stamp_pos.x
                stamp_rect.bottom = stamp_pos.y + Box.HEIGHT/2
                surface.blit(stamp_sprite, stamp_rect)

    def draw_clipboard_overlay(self, surface, font_registry):
        if self.overlay_selected_entity is None:
            return
    
        clipboard_clip_rect = get_rect(
            width=Box.WIDTH, height=Box.HEIGHT/2,
            centerx=self.clipboard_bg.centerx,
            top=self.clipboard_bg.top + Box.PADDING
        )

        pygame.draw.rect(surface, Color.CARGO_BOX_BACK, self.clipboard_bg)
        pygame.draw.rect(surface, Color.CLIPBOARD_CLIP, clipboard_clip_rect)
        misaligned_pages = [
            (-5, pygame.Vector2(-6, 5), (220, 220, 210)),
            (4, pygame.Vector2(7, -3), (233, 233, 224)),
            (-2, pygame.Vector2(2, 4), (244, 244, 236)),
        ]
        for rotated_angle, offset, color in misaligned_pages:
            pygame.draw.polygon(
                surface,
                color,
                Box.get_rotated_rect_polygon(self.clipboard_page, rotated_angle, offset)
            )
        pygame.draw.rect(surface, Color.WHITE, self.clipboard_page)
        pygame.draw.lines(
            surface,
            Color.CLIPBOARD_CLIP_FRONT,
            False,
            [
                clipboard_clip_rect.topleft,
                clipboard_clip_rect.bottomleft,
                clipboard_clip_rect.bottomright,
                clipboard_clip_rect.topright
            ],
            width=4 # TODO magic number
        )
        if self.current_overlay == self.DEPOT:
            self.draw_depot_stock_record(surface, font_registry)
        elif self.current_overlay == self.DECORATION_STORE:
            self.draw_decoration_purchase_form(surface, font_registry)

        pencil_sprite = DataFiles.sprites["props"]["pencil"]
        pencil_rect = pencil_sprite.get_rect()
        pencil_rect.right = self.clipboard_page.right + Box.WIDTH/4 # TODO alignment magic number
        pencil_rect.bottom = self.clipboard_page.bottom + Box.HEIGHT/2
        surface.blit(pencil_sprite, pencil_rect)

    def flip_decoration(self):
        self.decoration_flipped = not self.decoration_flipped

    def interacting_shipgirl_of_decoration(self, tilepos_anchor):
        tilepos_anchor = tuple(tilepos_anchor)
        return next(
            (
                shipgirl for shipgirl in self.menu_manager.available_shipgirls
                if shipgirl.interacting_decoration == tilepos_anchor
            ),
            None
        )

    def snap_shipgirl_to_interactable_decoration(self, shipgirl):
        for decoration_data in DataFiles.save_file["decorations"]:
            decoration, tilepos_anchor, flipped = Decorations.unpack_decoration_data(decoration_data)
            decoration_store_info = DataFiles.decoration_store[decoration]
            if not decoration_store_info["interactable"]:
                continue

            shipgirl_tilepos = Decorations.get_isometric_tilepos(shipgirl.rect.center)
            decoration_tiles = Decorations.get_decoration_tiles(decoration, flipped, tilepos_anchor)
            if shipgirl_tilepos not in decoration_tiles:
                continue

            if self.interacting_shipgirl_of_decoration(tilepos_anchor) is not None:
                continue

            sprite_rect = Decorations.get_decoration_sprite_rect(decoration, flipped, tilepos_anchor)
            snap_x, snap_y = decoration_store_info.get("snap", (0.5, 1))
            shipgirl.pos = pygame.Vector2(
                sprite_rect.left + sprite_rect.width * snap_x,
                sprite_rect.top + sprite_rect.height * snap_y
            )
            shipgirl.rect.center = shipgirl.pos
            shipgirl.interacting_decoration = tuple(tilepos_anchor)
            shipgirl.sprite.set_animation(decoration_store_info.get("shipgirl_animation", Live2D.IDLE_ANIMATION))
            shipgirl.facing_left = flipped
            if decoration == "bed":
                self.shipgirl_interacted_with_bed = True
            return True

        shipgirl.interacting_decoration = None
        return False

    def release_shipgirls_from_deleted_decoration(self, decoration_data):
        deleted_decoration = tuple(decoration_data[1])
        for shipgirl in self.menu_manager.available_shipgirls:
            if shipgirl.interacting_decoration == deleted_decoration:
                shipgirl.interacting_decoration = None
                shipgirl.pick_new_wander_target()

    def update_decorate_port_menu_overlay(self, events):
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button != 1:
                    continue

                self.refresh_overlay_page_buttons()
                if (
                    self.overlay_page_prev_button.active
                    and self.overlay_page_prev_button.rect.collidepoint(event.pos)
                ) or (
                    self.overlay_page_next_button.active
                    and self.overlay_page_next_button.rect.collidepoint(event.pos)
                ):
                    continue

                if self.decoration_depot_overlay.collidepoint(event.pos):
                    entity = self.get_decoration_depot_entity_at_pos(event.pos)
                    if entity is not None:
                        self.select_decoration_depot_entity(event.pos, allow_delete_toggle=False)
                        if entity == self.DELETE_DECORATION:
                            continue
                    self.decoration_depot_drag_offset = pygame.Vector2(self.decoration_depot_overlay.topleft) - pygame.Vector2(event.pos)
                    continue

                if (
                    self.selected_decoration_in_depot is None
                    and not self.toggle_decoration_mode_button.rect.collidepoint(event.pos)
                ):
                    if not self.deleting_decoration:
                        for shipgirl in self.menu_manager.available_shipgirls:
                            if shipgirl.rect.collidepoint(event.pos):
                                self.dragged_shipgirl = shipgirl
                                shipgirl.sprite.set_animation(Live2D.DRAG_ANIMATION)
                                shipgirl.interacting_decoration = None
                                break

                    if self.dragged_shipgirl is None and self.can_start_decorate_camera_drag(event.pos):
                        self.camera_dragging = True
                        continue
            if event.type == pygame.MOUSEMOTION:
                if self.update_camera_drag(event):
                    continue

                self.toggle_decoration_mode_button.hover(event.pos)
                self.refresh_overlay_page_buttons()
                self.overlay_page_prev_button.hover(event.pos)
                self.overlay_page_next_button.hover(event.pos)

                if self.dragged_shipgirl is not None:
                    self.dragged_shipgirl.pos = pygame.Vector2(event.pos)
                    self.dragged_shipgirl.rect.center = self.dragged_shipgirl.pos
                    continue

                if self.decoration_depot_drag_offset is not None:
                    self.decoration_depot_overlay.topleft = pygame.Vector2(event.pos) + self.decoration_depot_drag_offset
            if event.type == pygame.MOUSEBUTTONUP:
                if event.button == 3 and self.selected_decoration_in_depot is not None:
                    DataFiles.sfx["click"].play()
                    self.flip_decoration()
                    self.flipped_decoration = True
                    continue

                if event.button != 1:
                    continue

                self.refresh_overlay_page_buttons()
                if (
                    self.overlay_page_prev_button.click(event.pos)
                    or self.overlay_page_next_button.click(event.pos)
                ):
                    DataFiles.sfx["click"].play()
                    continue

                if self.camera_dragging:
                    self.camera_dragging = False
                    continue

                if self.dragged_shipgirl is not None:
                    if not self.snap_shipgirl_to_interactable_decoration(self.dragged_shipgirl):
                        self.dragged_shipgirl.interacting_decoration = None
                        self.dragged_shipgirl.pick_new_wander_target()

                    self.dragged_shipgirl = None
                    continue

                if self.decoration_depot_drag_offset is not None:
                    self.moved_decoration_depot_overlay = True
                    self.decoration_depot_drag_offset = None
                    continue

                if self.toggle_decoration_mode_button.click(event.pos):
                    DataFiles.sfx["click"].play()
                    self.selected_decoration_in_depot = None
                    self.deleting_decoration = False
                    continue
            
                if self.decoration_depot_overlay.collidepoint(event.pos):
                    self.select_decoration_depot_entity(event.pos, allow_delete_toggle=True)
                elif self.deleting_decoration:
                    clicked_tilepos = Decorations.get_isometric_tilepos(event.pos)
                    for decoration_index, decoration_data in enumerate(DataFiles.save_file["decorations"]):
                        decoration, tilepos_anchor, flipped = Decorations.unpack_decoration_data(decoration_data)
                        if clicked_tilepos in Decorations.get_decoration_tiles(decoration, flipped, tilepos_anchor):
                            DataFiles.sfx["click"].play()
                            self.release_shipgirls_from_deleted_decoration(decoration_data)
                            DataFiles.save_file["decorations"].pop(decoration_index)
                            DataFiles.save_file["decoration_depot"][decoration] = (
                                DataFiles.save_file["decoration_depot"].get(decoration, 0) + 1
                            )
                            if decoration == "bed":
                                self.removed_bed_decoration = True
                            break
                elif self.selected_decoration_in_depot is not None:
                    occupied_tiles = set() # TODO code optimization
                    for decoration_data in DataFiles.save_file["decorations"]:
                        decoration, tilepos_anchor, flipped = Decorations.unpack_decoration_data(decoration_data)
                        occupied_tiles.update(Decorations.get_decoration_tiles(decoration, flipped, tilepos_anchor))

                    decoration = self.selected_decoration_in_depot
                    clicked_tilepos = Decorations.get_isometric_tilepos_anchor(event.pos)
                    place_tiles = Decorations.get_decoration_tiles(decoration, self.decoration_flipped, clicked_tilepos)
                    if place_tiles.intersection(occupied_tiles):
                        continue
                    if not Decorations.in_tileable_area(place_tiles):
                        continue
                    DataFiles.sfx["click"].play()
                    DataFiles.save_file["decorations"].append((decoration, clicked_tilepos, self.decoration_flipped))
                    DataFiles.save_file["decoration_depot"][decoration] -= 1
                    if decoration == "bed":
                        self.placed_bed_decoration = True
                    if DataFiles.save_file["decoration_depot"][decoration] <= 0:
                        self.selected_decoration_in_depot = None

    def update(self, dt, events):
        if self.decoration_stamp_animation_timer > 0:
            self.decoration_stamp_animation_timer -= dt
            if self.decoration_stamp_animation_timer <= 0:
                self.decoration_stamp_animation_timer = 0
                self.refresh_overlay_action_buttons()

        if self.is_decorating:
            self.update_decorate_port_menu_overlay(events)
        elif self.current_overlay == self.NO_OVERLAY:
            self.update_no_overlay(events)
        else:
            for event in events:
                if event.type == pygame.MOUSEMOTION:
                    self.refresh_overlay_page_buttons()
                    self.overlay_page_prev_button.hover(event.pos)
                    self.overlay_page_next_button.hover(event.pos)
                    action_button = self.get_current_overlay_action_button()
                    if action_button is not None:
                        action_button.hover(event.pos)
                if event.type == pygame.MOUSEBUTTONUP:
                    self.refresh_overlay_page_buttons()
                    if (
                        self.overlay_page_prev_button.click(event.pos)
                        or self.overlay_page_next_button.click(event.pos)
                    ):
                        DataFiles.sfx["click"].play()
                        continue
                    if self.exit_overlay(event):
                        continue
                    self.select_filter(event)
                    self.select_entity(event)
                    action_button = self.get_current_overlay_action_button()
                    if action_button is not None:
                        action_button.click(event.pos)

        if self.current_overlay in [self.DEPOT, self.DECORATION_STORE]:
            if self.forklift_pause > 0:
                prev_forklift_pause = self.forklift_pause
                self.forklift_pause -= dt
                if prev_forklift_pause > 0.5 and self.forklift_pause <= 0.5:
                    self.forklift_dx *= -1
            elif self.forklift_dx > 0:
                self.forklift_x += dt / 5
                if self.forklift_x >= 1:
                    self.forklift_x = 1
                    self.forklift_pause = 1
            elif self.forklift_dx < 0:
                self.forklift_x -= dt / 5
                if self.forklift_x <= 0:
                    self.forklift_x = 0
                    self.forklift_pause = 1

        for shipgirl in self.menu_manager.available_shipgirls:
            if shipgirl not in [self.hovered_shipgirl, self.dragged_shipgirl]:
                shipgirl.update(dt)
            shipgirl.animate(dt)

    def draw_decoration_stock_sticker(self, surface, font_registry, icon_rect, amount):
        font = font_registry["big_pixel"]
        label_text = f"x{amount}"
        label_rect = get_rect(
            width=font.get_width(label_text, 1, 0) + Box.PADDING,
            height=font.font_height + Box.PADDING,
            left=icon_rect.left + Box.OUTLINE_WIDTH,
            top=icon_rect.top + Box.OUTLINE_WIDTH
        )
        label_shadow_rect = label_rect.move(Box.OUTLINE_WIDTH, Box.OUTLINE_WIDTH)

        pygame.draw.rect(surface, Color.GREY, label_shadow_rect)
        pygame.draw.rect(surface, Color.WHITE, label_rect)
        pygame.draw.rect(
            surface,
            Color.GREY,
            label_rect,
            width=Box.OUTLINE_WIDTH
        )
        font.render(
            surface,
            label_text,
            label_rect.center,
            Color.BLACK,
            1,
            style="center"
        )

    def draw_decoration_mode_overlay(self, surface, font_registry):
        if self.deleting_decoration:
            mpos = pygame.mouse.get_pos()
            hovered_tilepos = Decorations.get_isometric_tilepos(mpos)
            for decoration_data in DataFiles.save_file["decorations"]:
                decoration, tilepos_anchor, flipped = Decorations.unpack_decoration_data(decoration_data)
                hovered_decoration_tiles = Decorations.get_decoration_tiles(decoration, flipped, tilepos_anchor)
                if hovered_tilepos in hovered_decoration_tiles:
                    pygame.draw.polygon(
                        surface,
                        Color.RED,
                        Decorations.get_decoration_base_polygon(decoration, flipped, tilepos_anchor),
                        width=Box.OUTLINE_WIDTH
                    )
                    break

        if self.selected_decoration_in_depot:
            occupied_tiles = set() # TODO code optimization
            for decoration_data in DataFiles.save_file["decorations"]:
                decoration, tilepos_anchor, flipped = Decorations.unpack_decoration_data(decoration_data)
                occupied_tiles.update(Decorations.get_decoration_tiles(decoration, flipped, tilepos_anchor))

            decoration = self.selected_decoration_in_depot
            mpos = pygame.mouse.get_pos()
            hovered_tilepos = Decorations.get_isometric_tilepos_anchor(mpos)
            place_tiles = Decorations.get_decoration_tiles(decoration, self.decoration_flipped, hovered_tilepos)
            sprite = Decorations.get_decoration_sprite(decoration, self.decoration_flipped)
            sprite_rect = Decorations.get_decoration_sprite_rect(decoration, self.decoration_flipped, hovered_tilepos)
            surface.blit(sprite, sprite_rect)
            if not place_tiles.intersection(occupied_tiles) and Decorations.in_tileable_area(place_tiles):
                outline_color = Color.WHITE
            else:
                outline_color = Color.RED
            pygame.draw.polygon(
                surface,
                outline_color,
                Decorations.get_decoration_base_polygon(decoration, self.decoration_flipped, hovered_tilepos),
                width=Box.OUTLINE_WIDTH
            )

        self.toggle_decoration_mode_button.draw(surface, font_registry)

        pygame.draw.rect(surface, Color.CARGO_BOX_BACK, self.decoration_depot_overlay)

        for entity, rect in zip(self.get_visible_overlay_entities(), self.get_overlay_icon_rects()):
            if entity == self.DELETE_DECORATION:
                sprite = DataFiles.sprites["user_interface"]["remove_decoration"]
            else:
                sprite = DataFiles.get_entity_sprite(entity)

            pygame.draw.rect(surface, Color.CARGO_BOX, rect)
            surface.blit(sprite, rect)
            if entity != self.DELETE_DECORATION:
                amt = DataFiles.save_file["decoration_depot"][entity]
                self.draw_decoration_stock_sticker(
                    surface,
                    font_registry,
                    rect,
                    amt
                )
            if self.selected_decoration_in_depot == entity:
                pygame.draw.rect(surface, Color.WHITE, rect, width=Box.OUTLINE_WIDTH)
            if entity == self.DELETE_DECORATION and self.deleting_decoration:
                pygame.draw.rect(surface, Color.WHITE, rect, width=Box.OUTLINE_WIDTH)

        depot_decoration_top = self.decoration_depot_overlay.top - Box.WIDTH/8
        top_rope_sprite = DataFiles.sprites["props"]["top_rope"]
        top_rope_rect = top_rope_sprite.get_rect()
        top_rope_rect.centerx = self.decoration_depot_overlay.centerx + Box.WIDTH/4
        top_rope_rect.top = depot_decoration_top
        surface.blit(top_rope_sprite, top_rope_rect)

        rope_hook_sprite = pygame.transform.flip(
            DataFiles.sprites["props"]["rope_hook"],
            True, False
        )
        rope_hook_rect = rope_hook_sprite.get_rect()
        rope_hook_rect.centerx = self.decoration_depot_overlay.right - Box.PADDING
        rope_hook_rect.top = depot_decoration_top
        surface.blit(rope_hook_sprite, rope_hook_rect)

        aisle_sign_rect = get_rect(
            width=Box.WIDTH,
            height=Box.HEIGHT,
            centerx=rope_hook_rect.centerx,
            bottom=rope_hook_rect.bottom
        )
        font = font_registry["big_pixel"]
        font.render(
            surface,
            "aisle",
            (
                aisle_sign_rect.centerx,
                aisle_sign_rect.centery - 1.25*font.font_height
            ),
            Color.BLACK,
            1,
            style="center"
        )
        font.render(
            surface,
            str(self.get_overlay_page() + 1),
            (
                aisle_sign_rect.centerx,
                aisle_sign_rect.centery + font.font_height/2
            ),
            Color.BLACK,
            2,
            style="center"
        )

        corner_rope_sprite = pygame.transform.flip(
            DataFiles.sprites["props"]["corner_rope"],
            True, False
        )
        corner_rope_rect = corner_rope_sprite.get_rect()
        corner_rope_rect.left = self.decoration_depot_overlay.left - Box.WIDTH/8
        corner_rope_rect.top = depot_decoration_top
        surface.blit(corner_rope_sprite, corner_rope_rect)

        big_corner_rope_sprite = pygame.transform.flip(
            DataFiles.sprites["props"]["big_corner_rope"],
            True, False
        )
        big_corner_rope_rect = big_corner_rope_sprite.get_rect()
        big_corner_rope_rect.left = self.decoration_depot_overlay.left - Box.WIDTH/8 # TODO magic number
        big_corner_rope_rect.top = depot_decoration_top
        surface.blit(big_corner_rope_sprite, big_corner_rope_rect)

        lightbulb_sprite = DataFiles.sprites["props"]["lightbulb"]
        lightbulb_rect = lightbulb_sprite.get_rect()
        lightbulb_rect.centerx = self.decoration_depot_overlay.left + Box.WIDTH
        lightbulb_rect.top = depot_decoration_top
        surface.blit(lightbulb_sprite, lightbulb_rect)

        lightbulb_light_sprite = DataFiles.sprites["props"]["lightbulb_light"]
        lightbulb_light_rect = lightbulb_light_sprite.get_rect()
        lightbulb_light_rect.centerx = lightbulb_rect.centerx
        lightbulb_light_rect.bottom = lightbulb_rect.bottom + Box.HEIGHT/4
        surface.blit(lightbulb_light_sprite, lightbulb_light_rect, special_flags=pygame.BLEND_RGB_ADD)

        cargo_box_sprite = DataFiles.sprites["props"]["cargo_box"]
        cargo_box_rect = cargo_box_sprite.get_rect()
        for cargo_box_pos in [
            pygame.Vector2(self.decoration_depot_overlay.bottomleft),
            pygame.Vector2(self.decoration_depot_overlay.bottomleft) + pygame.Vector2(-cargo_box_rect.width, 0),
            pygame.Vector2(self.decoration_depot_overlay.bottomleft) + pygame.Vector2(-cargo_box_rect.width/2, -cargo_box_rect.height),
            
            pygame.Vector2(self.decoration_depot_overlay.bottomright),
            pygame.Vector2(self.decoration_depot_overlay.bottomright) + pygame.Vector2(cargo_box_rect.width, 0),
        ]:
            cargo_box_rect.center = cargo_box_pos
            surface.blit(cargo_box_sprite, cargo_box_rect)
        self.draw_overlay_page_buttons(surface, font_registry)

    def draw(self, surface, font_registry):
        surface.blit(Decorations.wallpaper_surf, Decorations.get_wallpaper_rect())
        surface.blit(Decorations.floor_surf, Decorations.floor_rect)

        interacting_shipgirls_by_decoration = {
            tuple(shipgirl.interacting_decoration): shipgirl
            for shipgirl in self.menu_manager.available_shipgirls
            if shipgirl.interacting_decoration is not None
        }
        renderables = list(DataFiles.save_file["decorations"])
        renderables.extend(
            shipgirl for shipgirl in self.menu_manager.available_shipgirls
            if shipgirl.interacting_decoration is None
        )

        renderables = sorted(
            renderables,
            key=functools.cmp_to_key(Decorations.compare_decoration_render_order)
        )
        for renderable in renderables:
            if Decorations.is_shipgirl_renderable(renderable):
                renderable.draw(surface, font_registry)
                continue

            decoration_data = renderable
            decoration, tilepos_anchor, flipped = Decorations.unpack_decoration_data(decoration_data)
            sprite = Decorations.get_decoration_sprite(decoration, flipped)
            sprite_rect = Decorations.get_decoration_sprite_rect(decoration, flipped, tilepos_anchor)
            surface.blit(sprite, sprite_rect)

            interacting_shipgirl = interacting_shipgirls_by_decoration.get(tuple(tilepos_anchor))
            if interacting_shipgirl is not None:
                interacting_shipgirl.draw(surface, font_registry)

        if self.is_decorating:
            self.draw_decoration_mode_overlay(surface, font_registry)
            return
        self.toggle_decoration_mode_button.draw(surface, font_registry)
        
        for option in self.shipgirl_dialogue_options:
            option.draw(surface, font_registry)

        buttons = [
            self.open_depot_overlay_button,
            self.open_intel_center_overlay_button,
            self.open_shipyard_overlay_button,
            self.open_gear_lab_overlay_button,
            self.open_decoration_store_overlay_button,
            self.open_select_sortie_menu_button,
        ]
        notifications = [
            self.depot_notification,
            self.intel_center_notification,
            self.shipyard_notification,
            self.gear_lab_notification,
            self.decoration_store_notification,
            False,
        ]
        for button, notification in zip(buttons, notifications):
            button.draw(surface, font_registry)
            self.draw_button_notification(surface, button, notification)

        if self.current_overlay in [self.DEPOT, self.DECORATION_STORE]:
            self.draw_warehouse_overlay(surface, font_registry)
            self.draw_clipboard_overlay(surface, font_registry)
        if self.current_overlay in [self.INTEL_CENTER, self.SHIPYARD, self.GEAR_LAB]:
            self.draw_dossier_overlay(surface, font_registry)
            self.draw_blueprint_overlay(surface, font_registry)
    
        self.menu_manager.quest_manager.draw(surface, font_registry)
        for choose_faction_button in self.choose_faction_buttons:
            choose_faction_button.draw(surface, font_registry)
