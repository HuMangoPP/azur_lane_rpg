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

    DOSSIER_TITLES = {
        INTEL_CENTER: "threat registry",
        SHIPYARD: "construction register",
        GEAR_LAB: "armaments index",
    }

    HULL_TYPE_MAPPING = {
        "DD": "destroyer",
        "CL": "light cruiser",
        "CA": "heavy cruiser",
        "BB": "battleship",
        "SS": "submarine",
        "CV": "aircraft carrier",
        "AUX": "universal",
    }

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
            right=screen_x(0.5) + Box.WIDTH/2,
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
        # Document regions and icons on page
        dossier_icon_grid_left = self.dossier_page.centerx - dossier_icon_grid_width / 2
        dossier_icon_grid_top = self.dossier_page.centery - dossier_icon_grid_height / 2
        self.dossier_grid = get_rect(
            width=dossier_icon_grid_width,
            height=dossier_icon_grid_height,
            left=dossier_icon_grid_left,
            top=dossier_icon_grid_top,
        )
        self.dossier_header = get_rect(
            width=self.dossier_grid.width,
            height=self.dossier_grid.top - self.dossier_page.top - Box.PADDING,
            left=self.dossier_grid.left,
            top=self.dossier_page.top,
        )
        self.dossier_footer = get_rect(
            width=self.dossier_grid.width,
            height=self.dossier_page.bottom - self.dossier_grid.bottom - Box.PADDING,
            left=self.dossier_grid.left,
            top=self.dossier_grid.bottom + Box.PADDING,
        )
        self.dossier_icons = [
            get_rect(
                width=Box.WIDTH, height=Box.HEIGHT,
                left=dossier_icon_grid_left+(i%num_items_in_row)*(Box.WIDTH+Box.PADDING),
                top=dossier_icon_grid_top+(i//num_items_in_row)*(Box.HEIGHT+Box.PADDING)
            ) for i in range(num_items_in_row * num_items_in_col)
        ]

        # Blueprint-themed right panel
        self.blueprint_page = get_rect(
            width=5*Box.WIDTH + 2*Box.PADDING,
            height=7.5*Box.HEIGHT + 2*Box.PADDING,
            left=self.dossier_overlay.right+Box.PADDING,
            centery=screen_y(0.5),
        )
        # Sticky-note confirm surface attached to the blueprint's top-right corner.
        self.sticky_note_page = get_rect(
            width=2*Box.WIDTH + 2*Box.PADDING,
            height=2*Box.HEIGHT + 2*Box.PADDING,
            right=self.blueprint_page.right + Box.WIDTH + Box.PADDING,
            top=max(Box.PADDING, self.blueprint_page.top - Box.HEIGHT/2 - Box.PADDING),
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

        if self.menu_manager.quest_manager.notifications_collidepoint(pos):
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
        encountered_sirens = set()
        for i in range(DataFiles.save_file["sortie_progress"]):
            encounters = DataFiles.sortie_data[i]["encounters"]
            for encounter in encounters:
                for encoded_siren in encounter["front"] + encounter["back"]:
                    encountered_sirens.add(encoded_siren)
        self.encountered_sirens = sorted(list(encountered_sirens))

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
                encoded_siren for encoded_siren in self.encountered_sirens
                if (
                    DataFiles.siren_data[encoded_siren.split(":")[0]]["hull_type"]
                    == self.intel_center_filters[self.overlay_selected_filter]
                )
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
                if self.menu_manager.quest_manager.selected_quest is not None:
                    continue
                if event.button == 1 and self.can_start_no_overlay_camera_drag(event.pos):
                    self.camera_dragging = True
                    continue

            if event.type == pygame.MOUSEMOTION:
                if self.update_camera_drag(event):
                    continue
                if self.menu_manager.quest_manager.selected_quest is not None:
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
        if (
            self.overlay_page_prev_button.active
            and self.overlay_page_prev_button.rect.collidepoint(mouseup_event.pos)
        ):
            return False
        if (
            self.overlay_page_next_button.active
            and self.overlay_page_next_button.rect.collidepoint(mouseup_event.pos)
        ):
            return False
    
        if self.current_overlay in [self.DEPOT, self.DECORATION_STORE]:
            left_overlay = self.warehouse_overlay
            right_overlay = self.clipboard_bg
        if self.current_overlay in [self.INTEL_CENTER, self.SHIPYARD, self.GEAR_LAB]:
            left_overlay = self.dossier_bg
            entity_filters = getattr(self, f"{self.current_overlay}_filters")
            filter_rects = [filter_rect for _, filter_rect in zip(entity_filters, self.dossier_tabs)]
            if filter_rects[0].unionall(filter_rects[1:]).collidepoint(mouseup_event.pos):
                return False
            right_overlay = self.blueprint_page
            if self.overlay_selected_entity is not None:
                action_button = self.get_current_overlay_action_button()
                if (
                    action_button is not None
                    and action_button.active
                    and action_button.rect.collidepoint(mouseup_event.pos)
                ):
                    return False

        if left_overlay.collidepoint(mouseup_event.pos):
            return False
        if (
            self.overlay_selected_entity is not None
            and right_overlay.collidepoint(mouseup_event.pos)
        ):
            return False

        self.current_overlay = self.NO_OVERLAY
        self.overlay_selected_entity = None
        self.refresh_overlay_action_buttons()
        self.overlay_page_prev_button.active = False
        self.overlay_page_next_button.active = False
        self.overlay_selected_filter = 0
        return True

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

    def draw_dossier_page(self, surface):
        page_turn_size = self.overlay_page_next_button.rect.width
        prev_fold_hovered = self.overlay_page_prev_button.hovered
        prev_fold_size = page_turn_size if prev_fold_hovered else page_turn_size - Box.PADDING
        next_fold_hovered = self.overlay_page_next_button.hovered
        next_fold_size = page_turn_size if next_fold_hovered else page_turn_size - Box.PADDING
        next_fold_shadow = (
            Color.DOSSIER_FOLD_SHADOW_HOVER
            if next_fold_hovered
            else Color.DOSSIER_FOLD_SHADOW
        )
        next_crease_width = Box.OUTLINE_WIDTH + int(next_fold_hovered)

        page_polygon = []
        if self.overlay_page_prev_button.active:
            page_polygon.append((self.dossier_page.left + prev_fold_size, self.dossier_page.top))
        else:
            page_polygon.append(self.dossier_page.topleft)
        page_polygon.append(self.dossier_page.topright)

        if self.overlay_page_next_button.active:
            fold_top = (self.dossier_page.right, self.dossier_page.bottom - next_fold_size)
            fold_left = (self.dossier_page.right - next_fold_size, self.dossier_page.bottom)
            fold_tip = (
                self.dossier_page.right - next_fold_size,
                self.dossier_page.bottom - next_fold_size,
            )
            page_polygon.extend([fold_top, fold_left])
        else:
            page_polygon.append(self.dossier_page.bottomright)

        page_polygon.append(self.dossier_page.bottomleft)
        if self.overlay_page_prev_button.active:
            page_polygon.append((self.dossier_page.left, self.dossier_page.top + prev_fold_size))
        pygame.draw.polygon(surface, Color.DOSSIER_PAGE, page_polygon)

        if self.overlay_page_next_button.active:
            pygame.draw.polygon(
                surface,
                next_fold_shadow,
                [fold_top, fold_left, pygame.Vector2(fold_tip) + pygame.Vector2(3, 3)],
            )
            pygame.draw.polygon(
                surface,
                Color.DOSSIER_PAPER_UNDERSIDE,
                [fold_top, fold_left, fold_tip],
            )
            pygame.draw.line(
                surface,
                next_fold_shadow,
                fold_top,
                fold_left,
                width=next_crease_width,
            )
            pygame.draw.line(surface, Color.DOSSIER_RULE, fold_left, fold_tip)

    def draw_dossier_prev_page_fold(self, surface):
        if not self.overlay_page_prev_button.active:
            return

        page_turn_size = self.overlay_page_prev_button.rect.width
        fold_hovered = self.overlay_page_prev_button.hovered
        fold_size = page_turn_size if fold_hovered else page_turn_size - Box.PADDING
        fold_shadow = (
            Color.DOSSIER_FOLD_SHADOW_HOVER
            if fold_hovered
            else Color.DOSSIER_FOLD_SHADOW
        )
        crease_width = Box.OUTLINE_WIDTH + int(fold_hovered)
        fold_top = pygame.Vector2(self.dossier_page.left + fold_size, self.dossier_page.top)
        fold_left = pygame.Vector2(self.dossier_page.left, self.dossier_page.top + fold_size)
        page_topleft = pygame.Vector2(self.dossier_page.topleft)
        fold_height = 2*Box.PADDING
        fold_polygon = [
            fold_top - pygame.Vector2(0, fold_height),
            fold_top,
            fold_left,
            fold_left - pygame.Vector2(fold_height, 0),
            page_topleft - pygame.Vector2(fold_height, fold_height),
        ]
        pygame.draw.polygon(
            surface,
            Color.DOSSIER_CARD,
            fold_polygon,
        )
        pygame.draw.line(
            surface,
            fold_shadow,
            fold_polygon[1],
            fold_polygon[2],
            width=crease_width,
        )

    def draw_dossier_document_text(self, surface, font_registry, entity_filters, entities):
        font = font_registry["big_pixel"]
        section = entity_filters[self.overlay_selected_filter]
        section_text = f"section: {section}"
        section_right = self.dossier_header.right - Box.WIDTH - Box.PADDING
        section_left = section_right - font.get_width(section_text, 1, 0)

        font.render(
            surface,
            "azur lane naval command",
            (self.dossier_header.left, self.dossier_header.top + Box.PADDING),
            Color.DOSSIER_RULE,
            1,
        )
        font.render(
            surface,
            section_text,
            (section_left, self.dossier_header.top + Box.PADDING),
            Color.DOSSIER_RULE,
            1,
        )
        font.render(
            surface,
            self.DOSSIER_TITLES[self.current_overlay],
            (self.dossier_header.left, self.dossier_header.bottom - 2*font.font_height),
            Color.DOSSIER_INK,
            2,
        )
        pygame.draw.line(
            surface,
            Color.DOSSIER_RULE,
            (self.dossier_grid.left, self.dossier_grid.top - Box.PADDING/2),
            (self.dossier_grid.right, self.dossier_grid.top - Box.PADDING/2),
        )

        page = self.get_overlay_page() + 1
        page_count = self.get_overlay_page_count()
        font.render(
            surface,
            f"sheet {page:02d} of {page_count:02d}",
            self.dossier_footer.center,
            Color.DOSSIER_RULE,
            1,
            style="center",
        )

        if not entities:
            font.render(
                surface,
                "no records on file",
                self.dossier_grid.center,
                Color.DOSSIER_RULE,
                1,
                style="center",
            )

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

        self.draw_dossier_page(surface)
        self.draw_dossier_document_text(surface, font_registry, entity_filters, entities)

        red_circle_sprite = DataFiles.sprites["props"]["red_circle"]
        red_circle_rect = red_circle_sprite.get_rect()
        red_circle_rect.topleft = (-2*Box.WIDTH, -2*Box.HEIGHT)
        for entity, rect in zip(entities, self.dossier_icons):
            card_shadow_rect = rect.move(2, 2)
            pygame.draw.rect(surface, Color.DOSSIER_CARD_SHADOW, card_shadow_rect)
            pygame.draw.rect(surface, Color.DOSSIER_CARD, rect)
            image = DataFiles.get_entity_sprite(entity.split(":")[0])
            image_rect = image.get_rect()
            image_rect.center = rect.center
            surface.blit(image, image_rect)
            if self.overlay_selected_entity == entity:
                red_circle_rect.center = rect.center
            pygame.draw.rect(surface, Color.DOSSIER_INK, rect, width=Box.OUTLINE_WIDTH)
        surface.blit(red_circle_sprite, red_circle_rect)

        paperclip_sprite = DataFiles.sprites["props"]["diagonal_paperclip"]
        paperclip_rect = paperclip_sprite.get_rect()
        paperclip_rect.left = self.dossier_bg.left - 16 # TODO paper clip offset magic number
        paperclip_rect.top = self.dossier_bg.top - 8
        surface.blit(paperclip_sprite, paperclip_rect)
        self.draw_dossier_prev_page_fold(surface)

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

    def get_blueprint_document_data(self):
        display_name = self.overlay_selected_entity.replace("_", " ")

        if self.current_overlay == self.INTEL_CENTER:
            siren_name, siren_level = self.overlay_selected_entity.split(":")
            selected_siren = DataFiles.siren_data[siren_name]
            hull_type = selected_siren["hull_type"]
            siren_level = int(siren_level)
            return {
                "name": display_name.split(":")[0],
                "subtitle": f"hostile contact - threat level: {siren_level}",
                "specifications_header": "observed capabilities",
                "materials_header": "recovered materials",
                "empty_materials": "no recoverable materials logged",
                "specifications": [
                    ("hull_type", "hull class", hull_type),
                    ("max_hp", "structural integrity", Stats.stat(*selected_siren["max_hp"], level=siren_level)),
                    ("evasion", "maneuverability", Stats.stat(*selected_siren["evasion"], level=siren_level)),
                    ("firepower", "firepower", Stats.stat(*selected_siren["firepower"], level=siren_level)),
                    ("reload", "reload cycle", Stats.stat(*selected_siren["reload"], level=siren_level)),
                    ("target_pref", "targeting doctrine", selected_siren["target_pref"]),
                    ("medal", "combat data yield", Stats.stat(*selected_siren["reward_exp"], level=siren_level))
                ],
                "materials": [
                    (drop, f"{drop_rate}%", None)
                    for drop, drop_rate in selected_siren["drops"].items()
                ],
            }

        if self.current_overlay == self.SHIPYARD:
            selected_shipgirl = DataFiles.shipgirl_data[self.overlay_selected_entity]
            hull_type = selected_shipgirl["hull_type"]
            inventory = DataFiles.save_file["inventory"]
            specialized_wisdom_cubes = DataFiles.save_file["specialized_wisdom_cubes"]
            research_exp = specialized_wisdom_cubes.get(self.overlay_selected_entity, 0)
            wisdom_cube_count = (
                1
                if self.overlay_selected_entity in specialized_wisdom_cubes
                else inventory.get("wisdom_cube", 0)
            )
            requirements = [
                (f"{hull_type}_blueprint", inventory.get(f"{hull_type}_blueprint", 0), 1),
                ("wisdom_cube", wisdom_cube_count, 1),
                (
                    selected_shipgirl["unique_item"],
                    inventory.get(selected_shipgirl["unique_item"], 0),
                    1,
                ),
            ]
            selected_entity_stats = DataFiles.stats_data[hull_type]
            return {
                "name": display_name,
                "subtitle": (
                    f"{selected_shipgirl['faction']} - "
                    f"{selected_shipgirl['class']}-class {self.HULL_TYPE_MAPPING[hull_type]}"
                ),
                "specifications_header": "projected specifications",
                "materials_header": "construction requisition",
                "empty_materials": "no components requisitioned",
                "specifications": [
                    ("hull_type", "hull class", hull_type),
                    (
                        "max_hp",
                        "structural integrity",
                        Stats.stat(*selected_entity_stats["max_hp"], exp=research_exp),
                    ),
                    (
                        "evasion",
                        "maneuverability",
                        Stats.stat(*selected_entity_stats["evasion"], exp=research_exp),
                    ),
                    (
                        "firepower",
                        "firepower",
                        Stats.stat(*selected_entity_stats["firepower"], exp=research_exp),
                    ),
                    (
                        "reload",
                        "reload cycle",
                        Stats.stat(*selected_entity_stats["reload"], exp=research_exp),
                    ),
                    ("medal", "research data", research_exp),
                ],
                "materials": [
                    (material, f"{stock}/{required}", stock >= required)
                    for material, stock, required in requirements
                ],
            }

        selected_equipment = DataFiles.equipment_data[self.overlay_selected_entity]
        inventory = DataFiles.save_file["inventory"]
        equipment_type = selected_equipment["type"]
        display_type = "auxiliary" if equipment_type == "aux" else equipment_type
        approved_hulls = selected_equipment.get("equippable_by", "AUX")
        return {
            "name": display_name,
            "subtitle": f"{display_type} - {self.HULL_TYPE_MAPPING[approved_hulls]} fitment",
            "specifications_header": "technical specifications",
            "materials_header": "bill of materials",
            "empty_materials": "no components specified",
            "specifications": [
                ("hull_type", "approved hulls", approved_hulls),
                ("max_hp", "structural integrity", selected_equipment.get("max_hp")),
                ("evasion", "maneuverability", selected_equipment.get("evasion")),
                ("firepower", "firepower", selected_equipment.get("firepower")),
                ("reload", "reload cycle", selected_equipment.get("reload")),
                ("shell_type", "ammunition", selected_equipment.get("shell_type")),
            ],
            "materials": [
                (material, f"{inventory.get(material, 0)}/{required}", inventory.get(material, 0) >= required)
                for material, required in selected_equipment["craft_reqs"].items()
            ],
        }

    def draw_blueprint_corner_brackets(self, surface, rect, color, length=8):
        corners = [
            (rect.topleft, (1, 1)),
            (rect.topright, (-1, 1)),
            (rect.bottomleft, (1, -1)),
            (rect.bottomright, (-1, -1)),
        ]
        for corner, direction in corners:
            corner = pygame.Vector2(corner)
            dx, dy = direction
            pygame.draw.line(surface, color, corner, corner + pygame.Vector2(dx*length, 0))
            pygame.draw.line(surface, color, corner, corner + pygame.Vector2(0, dy*length))

    def draw_blueprint_page(self, surface):
        misaligned_pages = [
            (-5, pygame.Vector2(-7, 6), Color.BLUEPRINT_PAGE_BACK),
            (4, pygame.Vector2(7, -4), (34, 62, 125)),
            (-2, pygame.Vector2(3, 5), (45, 76, 145)),
        ]
        for rotated_angle, offset, color in misaligned_pages:
            pygame.draw.polygon(
                surface,
                color,
                Box.get_rotated_rect_polygon(self.blueprint_page, rotated_angle, offset),
            )
        pygame.draw.rect(surface, Color.BLUEPRINT_PAGE, self.blueprint_page)

        grid_step = 2*Box.PADDING
        for index, x in enumerate(range(
            self.blueprint_page.left + grid_step + Box.PADDING,
            self.blueprint_page.right - Box.PADDING,
            grid_step
        ), 1):
            color = Color.BLUEPRINT_GRID_MAJOR if index % 4 == 0 else Color.BLUEPRINT_GRID_MINOR
            pygame.draw.line(surface, color, (x, self.blueprint_page.top), (x, self.blueprint_page.bottom))
        for index, y in enumerate(range(
            self.blueprint_page.top + grid_step + Box.PADDING,
            self.blueprint_page.bottom - Box.PADDING,
            grid_step), 1
        ):
            color = Color.BLUEPRINT_GRID_MAJOR if index % 4 == 0 else Color.BLUEPRINT_GRID_MINOR
            pygame.draw.line(surface, color, (self.blueprint_page.left, y), (self.blueprint_page.right, y))

        inset_rect = self.blueprint_page.inflate(-2*Box.PADDING, -2*Box.PADDING)
        pygame.draw.rect(surface, Color.BLUEPRINT_GRID_MAJOR, inset_rect, width=Box.OUTLINE_WIDTH)

    def draw_blueprint_title_and_profile(self, surface, font_registry, document):
        title_left = self.blueprint_page.left + 2*Box.PADDING
        title_top = self.blueprint_page.top + 12
        title_safe_right = self.blueprint_page.right - Box.WIDTH - Box.PADDING
        title_width = title_safe_right - title_left
        title_font = font_registry["big_pixel"]
        title_scale = 2 if title_font.get_width(document["name"], 2, 0) <= title_width else 1
        title_font.render(surface, document["name"], (title_left, title_top), Color.WHITE, title_scale)
        subtitle_top = title_top + title_scale * title_font.font_height + Box.PADDING/2
        title_font.render(
            surface,
            document["subtitle"],
            (title_left, subtitle_top),
            Color.BLUEPRINT_INK_MUTED,
            1,
        )
        profile_rect = get_rect(
            width=Box.WIDTH + Box.PADDING,
            height=Box.HEIGHT + Box.PADDING,
            centerx=self.blueprint_page.centerx,
            centery=self.blueprint_page.top + Box.HEIGHT + 3*Box.PADDING,
        )
        pygame.draw.line(
            surface,
            Color.BLUEPRINT_GRID_MAJOR,
            (profile_rect.left - Box.PADDING, profile_rect.centery),
            (profile_rect.right + Box.PADDING, profile_rect.centery),
        )
        pygame.draw.line(
            surface,
            Color.BLUEPRINT_GRID_MAJOR,
            (profile_rect.centerx, profile_rect.top - Box.PADDING),
            (profile_rect.centerx, profile_rect.bottom + Box.PADDING),
        )
        self.draw_blueprint_corner_brackets(
            surface,
            profile_rect,
            Color.BLUEPRINT_SLOT_BORDER_GLOW,
            length=Box.PADDING,
        )
        profile_sprite = DataFiles.get_entity_sprite(self.overlay_selected_entity.split(":")[0])
        profile_sprite_rect = profile_sprite.get_rect(center=profile_rect.center)
        surface.blit(profile_sprite, profile_sprite_rect)

    def draw_blueprint_section_header(self, surface, font_registry, number, label, top):
        header_font = font_registry["big_pixel"]
        section_rect = get_rect(
            width=self.blueprint_page.width - 4*Box.PADDING,
            height=header_font.font_height + Box.PADDING,
            left=self.blueprint_page.left + 2*Box.PADDING,
            top=top,
        )
        pygame.draw.rect(surface, Color.BLUEPRINT_TITLE_BLOCK, section_rect)
        pygame.draw.rect(surface, Color.BLUEPRINT_PAGE_GLOW, section_rect, width=Box.OUTLINE_WIDTH)
        number_rect = get_rect(width=24, height=section_rect.height, left=section_rect.left, top=section_rect.top)
        pygame.draw.line(surface, Color.BLUEPRINT_PAGE_GLOW, number_rect.topright, number_rect.bottomright)
        header_font.render(
            surface,
            number,
            number_rect.center,
            Color.BLUEPRINT_SLOT_BORDER_GLOW,
            1,
            style="center",
        )
        header_font.render(
            surface,
            label,
            (number_rect.right + Box.PADDING, section_rect.centery),
            Color.WHITE,
            1,
            style="centerleft",
        )
        return section_rect

    def draw_blueprint_specifications(self, surface, font_registry, specifications, top):
        specifications = [specification for specification in specifications if specification[2] is not None]
        content_left = self.blueprint_page.left + 2*Box.PADDING
        column_gap = Box.PADDING
        cell_width = (self.blueprint_page.width - 4*Box.PADDING - column_gap) / 2
        cell_height = 32

        for index, (icon_name, label, value) in enumerate(specifications):
            column = index % 2
            row = index // 2
            cell_rect = get_rect(
                width=cell_width,
                height=cell_height,
                left=content_left + column*(cell_width + column_gap),
                top=top + row*cell_height,
            )
            icon = DataFiles.sprites["user_interface"][icon_name]
            surface.blit(icon, icon.get_rect(midleft=cell_rect.midleft))

            text_left = cell_rect.left + 36
            font_registry["pixel"].render(
                surface,
                label,
                (text_left, cell_rect.top + 5),
                Color.BLUEPRINT_INK_MUTED,
                1,
            )
            display_value = str(value).replace("_", " ")
            font_registry["big_pixel"].render(
                surface,
                display_value,
                (text_left, cell_rect.top + 17),
                Color.WHITE,
                1,
            )

    def draw_blueprint_materials(self, surface, font_registry, materials, empty_text, top):
        font = font_registry["big_pixel"]
        materials = materials[:6]
        if not materials:
            font.render(
                surface,
                empty_text,
                (self.blueprint_page.centerx, top + 30),
                Color.BLUEPRINT_INK_MUTED,
                1,
                style="center",
            )
            return

        slot_width = Box.WIDTH + Box.PADDING
        slot_height = Box.HEIGHT + Box.PADDING
        slot_gap = 2*Box.PADDING
        row_gap = 1.5*Box.PADDING
        for row in range(2):
            row_materials = materials[row*3:(row+1)*3]
            if not row_materials:
                continue
            row_width = len(row_materials)*slot_width + (len(row_materials)-1)*slot_gap
            row_left = self.blueprint_page.centerx - row_width/2
            for column, (material, quantity, sufficient) in enumerate(row_materials):
                slot_rect = get_rect(
                    width=slot_width,
                    height=slot_height,
                    left=row_left + column*(slot_width + slot_gap),
                    top=top + row*(slot_height + row_gap),
                )
                icon_frame = get_rect(
                    width=Box.WIDTH + Box.PADDING,
                    height=Box.HEIGHT,
                    centerx=slot_rect.centerx,
                    top=slot_rect.top,
                )
                self.draw_blueprint_corner_brackets(
                    surface,
                    icon_frame,
                    Color.BLUEPRINT_INK_MUTED,
                    length=6,
                )
                icon = DataFiles.get_entity_sprite(material)
                surface.blit(icon, icon.get_rect(center=icon_frame.center))

                plate_color = Color.BLUEPRINT_INK_MUTED
                text_color = Color.BLUEPRINT_INK_MUTED
                if sufficient:
                    plate_color = Color.BLUEPRINT_SLOT_BORDER_GLOW
                    text_color = Color.BLUEPRINT_SLOT_BORDER_GLOW
                quantity_plate = get_rect(
                    width=64,
                    height=font.font_height + Box.PADDING,
                    centerx=slot_rect.centerx,
                    bottom=slot_rect.bottom,
                )
                pygame.draw.rect(surface, Color.BLUEPRINT_TITLE_BLOCK, quantity_plate)
                pygame.draw.rect(surface, plate_color, quantity_plate, width=Box.OUTLINE_WIDTH)
                font.render(
                    surface,
                    quantity,
                    quantity_plate.center,
                    text_color,
                    1,
                    style="center",
                )

    def draw_blueprint_tools(self, surface):
        if self.current_overlay == self.INTEL_CENTER:
            return
        
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

    def draw_blueprint_overlay(self, surface, font_registry):
        if self.overlay_selected_entity is None:
            return

        document = self.get_blueprint_document_data()
        self.draw_blueprint_page(surface)
        self.draw_blueprint_title_and_profile(surface, font_registry, document)

        specifications_header_top = self.blueprint_page.top + 2*Box.HEIGHT + Box.PADDING
        specifications_header_rect = self.draw_blueprint_section_header(
            surface,
            font_registry,
            "01",
            document["specifications_header"],
            specifications_header_top,
        )
        self.draw_blueprint_specifications(
            surface,
            font_registry,
            document["specifications"],
            specifications_header_rect.bottom + Box.PADDING/2,
        )
        materials_header_top = self.blueprint_page.top + 4.5*Box.HEIGHT + Box.PADDING
        materials_header_rect = self.draw_blueprint_section_header(
            surface,
            font_registry,
            "02",
            document["materials_header"],
            materials_header_top,
        )
        self.draw_blueprint_materials(
            surface,
            font_registry,
            document["materials"],
            document["empty_materials"],
            materials_header_rect.bottom + Box.PADDING,
        )
        self.draw_blueprint_tools(surface)
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

        sign_rect = get_rect(
            width=Box.WIDTH,
            height=Box.HEIGHT,
            centerx=rope_hook_rect.centerx,
            bottom=rope_hook_rect.bottom
        )
        font = font_registry["big_pixel"]
        font.render(
            surface,
            "depot" if self.current_overlay == self.DEPOT else "aisle",
            (sign_rect.centerx, sign_rect.centery - 1.25*font.font_height),
            Color.BLACK,
            1,
            style="center"
        )
        font.render(
            surface,
            str(self.get_overlay_page() + 1),
            (sign_rect.centerx, sign_rect.centery + font.font_height/2),
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
        stamp_box_color = (
            (Color.RED if self.decoration_signature_button.hovered else Color.BLACK)
            if has_funds else Color.CLIPBOARD_CLIP
        )
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

        stamp_pattern_sprite = DataFiles.sprites["props"]["stamp_pattern"]
        stamp_pattern_rect = stamp_pattern_sprite.get_rect()
        stamp_pattern_rect.center = self.decoration_stamp_animation_pos
        if self.decoration_stamp_animation_timer > 0:
            elapsed = self.DECORATION_STAMP_ANIMATION_DURATION - self.decoration_stamp_animation_timer
            if elapsed >= self.DECORATION_STAMP_DISAPPEAR_TIME:
                progress = (
                    self.decoration_stamp_animation_timer
                    / (self.DECORATION_STAMP_ANIMATION_DURATION - self.DECORATION_STAMP_DISAPPEAR_TIME)
                )
                stamp_pattern_sprite.set_alpha(int(255 * progress))
                surface.blit(stamp_pattern_sprite, stamp_pattern_rect)
            elif elapsed >= self.DECORATION_STAMP_DOWN_TIME:
                stamp_pattern_sprite.set_alpha(255)
                surface.blit(stamp_pattern_sprite, stamp_pattern_rect)

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

    def position_shipgirl_at_decoration(self, shipgirl, decoration_data):
        decoration, tilepos_anchor, flipped = Decorations.unpack_decoration_data(decoration_data)
        decoration_store_info = DataFiles.decoration_store[decoration]
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

    def restore_shipgirl_decoration_interactions(self):
        decorations_by_anchor = {
            tuple(Decorations.unpack_decoration_data(decoration_data)[1]): decoration_data
            for decoration_data in DataFiles.save_file["decorations"]
        }
        for shipgirl in self.menu_manager.available_shipgirls:
            if shipgirl.interacting_decoration is None:
                continue

            decoration_data = decorations_by_anchor.get(tuple(shipgirl.interacting_decoration))
            if decoration_data is None:
                shipgirl.interacting_decoration = None
                shipgirl.pick_new_wander_target()
                continue

            decoration = Decorations.unpack_decoration_data(decoration_data)[0]
            if not DataFiles.decoration_store[decoration]["interactable"]:
                shipgirl.interacting_decoration = None
                shipgirl.pick_new_wander_target()
                continue

            self.position_shipgirl_at_decoration(shipgirl, decoration_data)

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

            self.position_shipgirl_at_decoration(shipgirl, decoration_data)
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
                    screen_rect = get_rect(
                        width=screen_x(1),
                        height=screen_y(1),
                        left=screen_x(0),
                        top=screen_y(0)
                    )
                    self.decoration_depot_overlay.clamp_ip(screen_rect)
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
        self.menu_manager.quest_manager.update(dt)
        encounter_menu = self.menu_manager.encounter_menu
        if encounter_menu.transition_active:
            encounter_menu.update(dt, ())

        if encounter_menu._transition_state == encounter_menu.TRANSITION_WAVE_COVER:
            return

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

    def draw_decoration_depot_selection_marker(self, surface, icon_rect, color):
        marker_rect = icon_rect.inflate(
            2*Box.OUTLINE_WIDTH,
            2*Box.OUTLINE_WIDTH
        )
        left = marker_rect.left
        top = marker_rect.top
        right = marker_rect.right - 1
        bottom = marker_rect.bottom - 1
        corner_length = Box.PADDING + 2*Box.OUTLINE_WIDTH
        corners = [
            [(left, top + corner_length), (left, top), (left + corner_length, top)],
            [(right - corner_length, top), (right, top), (right, top + corner_length)],
            [(right, bottom - corner_length), (right, bottom), (right - corner_length, bottom)],
            [(left + corner_length, bottom), (left, bottom), (left, bottom - corner_length)],
        ]

        for corner in corners:
            pygame.draw.lines(
                surface,
                color,
                False,
                corner,
                width=2*Box.OUTLINE_WIDTH
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
            selected = self.selected_decoration_in_depot == entity
            delete_tool_active = entity == self.DELETE_DECORATION and self.deleting_decoration
            if selected or delete_tool_active:
                marker_color = Color.RED if delete_tool_active else (240, 190, 60)
                self.draw_decoration_depot_selection_marker(
                    surface,
                    rect,
                    marker_color
                )

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

        sign_rect = get_rect(
            width=Box.WIDTH,
            height=Box.HEIGHT,
            centerx=rope_hook_rect.centerx,
            bottom=rope_hook_rect.bottom
        )
        font = font_registry["big_pixel"]
        font.render(
            surface,
            "depot",
            (sign_rect.centerx, sign_rect.centery - 1.25*font.font_height),
            Color.BLACK,
            1,
            style="center"
        )
        font.render(
            surface,
            str(self.get_overlay_page() + 1),
            (sign_rect.centerx, sign_rect.centery + font.font_height/2),
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
            if self.menu_manager.encounter_menu.transition_active:
                self.menu_manager.encounter_menu._draw_transition_wave_wipe(surface)
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

        for choose_faction_button in self.choose_faction_buttons:
            choose_faction_button.draw(surface, font_registry)

        self.menu_manager.quest_manager.draw(surface, font_registry)

        if self.menu_manager.encounter_menu.transition_active:
            self.menu_manager.encounter_menu._draw_transition_wave_wipe(surface)
