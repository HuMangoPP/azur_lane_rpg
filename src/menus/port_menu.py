import math
import random
import pygame

from engine.util import get_rect, get_vec
from engine.button import Button

from src.constants import DataFiles, Color, Box, Stats, screen_x, screen_y, Decorations
from src.shipgirls import Shipgirl

def get_decoration_tiles(decoration, direction, tilepos_anchor):
    decoration_info = DataFiles.decoration_store[decoration][direction]
    decoration_tiles = set()
    for x in range(decoration_info["width"]):
        for y in range(decoration_info["height"]):
            tilepos = (tilepos_anchor[0]+x, tilepos_anchor[1]+y)
            decoration_tiles.add(tilepos)
    return decoration_tiles

def get_decoration_sprite_rect(decoration, direction, tilepos_anchor):
    decoration_info = DataFiles.decoration_store[decoration][direction]
    tile_rect = get_rect(
        width=decoration_info["width"] * Decorations.TILESIZE,
        height=decoration_info["height"] * Decorations.TILESIZE,
        left=Decorations.floor_rect.left + tilepos_anchor[0] * Decorations.TILESIZE,
        top=Decorations.floor_rect.top + tilepos_anchor[1] * Decorations.TILESIZE
    )
    sprite = DataFiles.sprites["decorations"][f"{decoration}_{direction}"]
    sprite_rect = sprite.get_rect()
    sprite_rect.bottomleft = tile_rect.bottomleft
    return sprite_rect

def get_rotated_rect_polygon(rect, rotated_angle, offset=(0, 0)):
    rect_center = pygame.Vector2(rect.center) + pygame.Vector2(offset)
    rect_horizontal = get_vec(rect.width/2, math.radians(rotated_angle))
    rect_vertical = get_vec(rect.height/2, math.radians(90 + rotated_angle))
    return [
        rect_center + rect_horizontal + rect_vertical,
        rect_center - rect_horizontal + rect_vertical,
        rect_center - rect_horizontal - rect_vertical,
        rect_center + rect_horizontal - rect_vertical,
    ]

def in_tileable_area(tiles):
    return (
        min(tile[0] for tile in tiles) >= 0
        and max(tile[0] for tile in tiles) < Decorations.NUM_TILES_IN_ROW
        and min(tile[1] for tile in tiles) >= 0
        and max(tile[1] for tile in tiles) <= Decorations.NUM_TILES_IN_COL
    )


class PortMenu:
    NO_OVERLAY = "no_overlay"
    DEPOT = "depot"
    INTEL_CENTER = "intel_center"
    SHIPYARD = "shipyard"
    GEAR_LAB = "gear_lab"
    DECORATION_STORE = "decoration_store"

    DECORATION_DIRECTIONS = ["north", "east", "south", "west"]

    DECORATION_STAMP_ANIMATION_DURATION = 1
    DECORATION_STAMP_DOWN_TIME = 0.15
    DECORATION_STAMP_LIFT_TIME = 0.30
    DECORATION_STAMP_DISAPPEAR_TIME = 0.5

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
        
        self.choose_faction_buttons = [
            Button(
                get_rect(
                    width=Box.WIDTH, height=Box.HEIGHT,
                    centerx=screen_x(0.5) + (i-2)*Box.WIDTH+(i-1.5)*Box.PADDING,
                    centery=screen_y(0.5)
                ),
                choose_faction_factory(faction),
                active=False,
                background_styling={
                    "background_color": Color.BLACK,
                    "background_img": DataFiles.sprites["user_interface"][f"{faction}_big"]
                }
            )
            for i, faction in enumerate(factions)
        ]

        # Sortie button
        def open_select_sortie_menu():
            self.menu_manager.current_menu = self.menu_manager.sortie_selection_menu
            DataFiles.sfx["waves"].play(loops=-1)

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
        num_items_in_row = 6
        num_items_in_col = 4
        self.dossier_overlay = get_rect(
            width=num_items_in_row*(Box.WIDTH + Box.PADDING) + 4*Box.PADDING,
            height=num_items_in_col*(Box.HEIGHT + Box.PADDING) + 3*Box.PADDING + Box.HEIGHT,
            right=screen_x(0.5) + Box.WIDTH,
            centery=screen_y(0.5)
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
        self.dossier_icons = [
            get_rect(
                width=Box.WIDTH, height=Box.HEIGHT,
                left=self.dossier_page.left+Box.PADDING+(i%num_items_in_row)*(Box.WIDTH+Box.PADDING),
                top=self.dossier_page.top+Box.PADDING+(i//num_items_in_row)*(Box.HEIGHT+Box.PADDING)
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
        self.warehouse_overlay = get_rect(
            width=num_items_in_row*(Box.WIDTH+Box.PADDING) + Box.PADDING,
            height=num_items_in_col*(Box.HEIGHT+Box.PADDING) + Box.PADDING,
            right=screen_x(0.5) + Box.WIDTH/2,
            centery=screen_y(0.4)
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

        # Clipboard-themed right panel
        self.clipboard_bg = get_rect(
            width=3*(Box.WIDTH+Box.PADDING) + 3*Box.PADDING,
            height=4*(Box.HEIGHT+Box.PADDING) + 3*Box.PADDING + Box.HEIGHT/2,
            left=self.warehouse_overlay.right + Box.WIDTH/2,
            centery=screen_y(0.5)
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
            text_styling={"text_color": Color.BLACK}
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
            text_styling={"text": "construct", "text_color": Color.BLACK}
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
                DataFiles.save_file["inventory"].get("decoration_coin", 0) - 1
            )
            self.decoration_stamp_animation_timer = self.DECORATION_STAMP_ANIMATION_DURATION
            self.decoration_stamp_animation_pos = pygame.Vector2(pygame.mouse.get_pos())
            self.refresh_overlay_action_buttons()

        self.decoration_stamp_animation_timer = 0
        self.decoration_stamp_animation_pos = pygame.Vector2((0, 0))
        self.decoration_signature_button = Button(
            get_rect(
                width=self.clipboard_page.width - 2*Box.WIDTH,
                height=Box.HEIGHT,
                centerx=self.clipboard_page.centerx,
                bottom=self.clipboard_page.bottom - Box.HEIGHT/2 - Box.PADDING
            ),
            confirm_decoration_signature,
            active=False,
        )
        self.overlay_selected_entity = None

        def toggle_decoration_mode():
            self.is_decorating = not self.is_decorating

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

        self.decoration_depot_overlay = get_rect(
            width=3*(Box.WIDTH+Box.PADDING) + Box.PADDING,
            height=3*(Box.HEIGHT+Box.PADDING) + Box.PADDING,
            left=Box.LEFT_OF_SCREEN,
            top=Box.TOP_OF_SCREEN
        )
        self.selected_decoration_in_depot = None
        self.decoration_direction_index = 0
        self.deleting_decoration = False
        self.decoration_depot_drag_offset = None
        self.dragged_shipgirl = None
        self.dragged_shipgirl_offset = None
        self.moved_decoration_depot_overlay = False
        self.rotated_decoration = False
        self.placed_decoration = False
        self.removed_decoration = False

        Decorations.floor_rect.center = (screen_x(0.5), screen_y(0.5))
        self.camera_dragging = False

        self.hovered_shipgirl = None
        def open_equipment_menu():
            self.menu_manager.equipment_menu.selected_shipgirl = self.hovered_shipgirl
            self.menu_manager.current_menu = self.menu_manager.equipment_menu

        def close_shipgirl_dialogue_options():
            if self.hovered_shipgirl is not None:
                self.hovered_shipgirl.dragged = False
                self.release_shipgirl_from_interaction(self.hovered_shipgirl)
            self.hovered_shipgirl = None
            for option in self.shipgirl_dialogue_options:
                option.active = False

        self.shipgirl_dialogue_options = [
            Button(
                rect=get_rect(width=Box.WIDTH,height=Box.HEIGHT,left=0,top=0),
                callback=callback,
                active=False,
                background_styling={
                    "background_color": Color.BLACK,
                    "background_img": DataFiles.sprites["user_interface"][sprite],
                    "opacity": 160
                },
                hover_styling={"opacity": 200}
            )
            for callback, sprite in zip(
                [open_equipment_menu, lambda : True, close_shipgirl_dialogue_options],
                ["equip", "interact", "close"],
            )
        ]

        self.update_encountered_sirens()

    def position_shipgirl_dialogue_options(self):
        if self.hovered_shipgirl is None:
            return

        dialogue_options_offset = (len(self.shipgirl_dialogue_options)-1)/2
        for i, option in enumerate(self.shipgirl_dialogue_options):
            option.rect.bottom = self.hovered_shipgirl.rect.top
            option.rect.centerx = self.hovered_shipgirl.rect.centerx + (i - dialogue_options_offset) * (Box.WIDTH + Box.PADDING)

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
        if any(button.active and button.rect.collidepoint(pos) for button in buttons):
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
            self.toggle_decoration_mode_button.active
            and self.toggle_decoration_mode_button.rect.collidepoint(pos)
        ):
            return False
        if self.selected_decoration_in_depot is not None:
            return False
        
        if self.deleting_decoration:
            clicked_tilepos = (
                (pos[0] - Decorations.floor_rect.left) // Decorations.TILESIZE,
                (pos[1] - Decorations.floor_rect.top) // Decorations.TILESIZE
            )
            for decoration, tilepos_anchor, direction in DataFiles.save_file["decorations"]:
                decoration_info = DataFiles.decoration_store[decoration][direction]
                if (
                    tilepos_anchor[0] <= clicked_tilepos[0] < tilepos_anchor[0] + decoration_info["width"]
                    and tilepos_anchor[1] <= clicked_tilepos[1] < tilepos_anchor[1] + decoration_info["height"]
                ):
                    return False

        return not any(shipgirl.rect.collidepoint(pos) for shipgirl in self.menu_manager.available_shipgirls)

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
            and DataFiles.save_file["inventory"].get("decoration_coin", 0) > 0
            and self.decoration_stamp_animation_timer <= 0
        )

    def refresh_overlay_action_buttons(self):
        self.shipyard_sticky_note_button.active = False
        self.gear_lab_sticky_note_button.active = False
        self.decoration_signature_button.active = False

        if self.current_overlay == self.SHIPYARD:
            if self.can_construct_selected_shipgirl():
                self.shipyard_sticky_note_button.active = True
                self.shipyard_sticky_note_button.text = "construct"
            elif self.can_start_selected_shipgirl_research():
                self.shipyard_sticky_note_button.active = True
                self.shipyard_sticky_note_button.text = "research"
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

    def update_no_overlay(self, events):
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
                    self.hovered_shipgirl = None
                    continue

                if self.hovered_shipgirl is not None:
                    for option in self.shipgirl_dialogue_options:
                        if option.click(event.pos):
                            DataFiles.sfx["click"].play()
                        option.active = False
                    if self.hovered_shipgirl is not None:
                        self.hovered_shipgirl.dragged = False
                        self.release_shipgirl_from_interaction(self.hovered_shipgirl)
                        self.hovered_shipgirl = None
                    continue

                for shipgirl in self.menu_manager.available_shipgirls:
                    if shipgirl.rect.collidepoint(event.pos):
                        DataFiles.sfx["click"].play()
                        self.hovered_shipgirl = shipgirl
                        self.hovered_shipgirl.dragged = True
                        self.position_shipgirl_dialogue_options()
                        for option in self.shipgirl_dialogue_options:
                            option.active = True

    def exit_overlay(self, mouseup_event):
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
            and (
                self.overlay_selected_entity is None
                or not clicked_right_overlay
            )
        ):
            self.current_overlay = self.NO_OVERLAY
            self.overlay_selected_entity = None
            self.refresh_overlay_action_buttons()
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

    def select_entity(self, mouseup_event):
        if self.current_overlay == self.DEPOT:
            entities = [item for item, count in DataFiles.save_file["inventory"].items() if count > 0]
            rects = self.warehouse_icons
        if self.current_overlay == self.INTEL_CENTER:
            entities = [
                siren for siren in self.encountered_sirens
                if DataFiles.siren_data[siren]["hull_type"] == self.intel_center_filters[self.overlay_selected_filter]
            ]
            rects = self.dossier_icons
        if self.current_overlay == self.SHIPYARD:
            entities = [
                shipgirl for shipgirl, shipgirl_info in DataFiles.shipgirl_data.items()
                if shipgirl not in DataFiles.save_file["shipgirls"]
                and shipgirl_info["faction"] in DataFiles.save_file["unlocked_factions"]
                and shipgirl_info["faction"] == self.shipyard_filters[self.overlay_selected_filter]
            ]
            rects = self.dossier_icons
        if self.current_overlay == self.GEAR_LAB:
            if self.gear_lab_filters[self.overlay_selected_filter] == "AUX":
                entities = [
                    equip for equip, equip_data in DataFiles.equipment_data.items()
                    if equip_data["type"] == "aux"
                ]
            else:
                entities = [
                    equip for equip, equip_data in DataFiles.equipment_data.items()
                    if equip_data["type"] == "weapon"
                    and equip_data["equippable_by"] == self.gear_lab_filters[self.overlay_selected_filter]
                ]
            rects = self.dossier_icons
        if self.current_overlay == self.DECORATION_STORE:
            entities = [decoration for decoration in DataFiles.decoration_store]
            rects = self.warehouse_icons

        for entity, rect in zip(entities, rects):
            if rect.collidepoint(mouseup_event.pos):
                DataFiles.sfx["click"].play()
                self.overlay_selected_entity = entity

                if self.current_overlay in [self.DEPOT, self.INTEL_CENTER]:
                    setattr(self, f"visited_{self.current_overlay}", True)

                self.refresh_overlay_action_buttons()

    def draw_dossier_overlay(self, surface, font):
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

        if self.current_overlay == self.INTEL_CENTER:
            entities = [
                siren for siren in self.encountered_sirens
                if DataFiles.siren_data[siren]["hull_type"] == self.intel_center_filters[self.overlay_selected_filter]
            ]
        if self.current_overlay == self.SHIPYARD:
            entities = [
                shipgirl for shipgirl, shipgirl_info in DataFiles.shipgirl_data.items()
                if shipgirl not in DataFiles.save_file["shipgirls"]
                and shipgirl_info["faction"] in DataFiles.save_file["unlocked_factions"]
                and shipgirl_info["faction"] == self.shipyard_filters[self.overlay_selected_filter]
            ]
        if self.current_overlay == self.GEAR_LAB:
            if self.gear_lab_filters[self.overlay_selected_filter] == "AUX":
                entities = [
                    equip for equip, equip_data in DataFiles.equipment_data.items()
                    if equip_data["type"] == "aux"
                ]
            else:
                entities = [
                    equip for equip, equip_data in DataFiles.equipment_data.items()
                    if equip_data["type"] == "weapon"
                    and equip_data["equippable_by"] == self.gear_lab_filters[self.overlay_selected_filter]
                ]
        misaligned_pages = [
            (-5, pygame.Vector2(-8, 6), (224, 218, 201)),
            (4, pygame.Vector2(6, -4), (235, 229, 212)),
            (-2, pygame.Vector2(3, 5), (244, 239, 224)),
        ]
        for rotated_angle, offset, color in misaligned_pages:
            pygame.draw.polygon(
                surface,
                color,
                get_rotated_rect_polygon(self.dossier_page, rotated_angle, offset)
            )
        pygame.draw.rect(surface, Color.DOSSIER_PAGE, self.dossier_page)
        for entity, rect in zip(entities, self.dossier_icons):
            image = DataFiles.get_entity_sprite(entity)
            image_rect = image.get_rect()
            image_rect.center = rect.center
            surface.blit(image, image_rect)
            if entity == self.overlay_selected_entity:
                selected_sprite = DataFiles.sprites["user_interface"]["red_circle"]
                selected_rect = selected_sprite.get_rect()
                selected_rect.center = rect.center
                surface.blit(selected_sprite, selected_rect)
            pygame.draw.rect(surface, Color.BLACK, rect, width=Box.OUTLINE_WIDTH)
        
        overlay_paperclip_sprite = DataFiles.sprites["user_interface"]["overlay_paperclip"]
        overlay_paperclip_rect = overlay_paperclip_sprite.get_rect()
        overlay_paperclip_rect.left = self.dossier_bg.left - Box.WIDTH/4 # TODO alignment
        overlay_paperclip_rect.top = self.dossier_bg.top
        surface.blit(overlay_paperclip_sprite, overlay_paperclip_rect)

    def draw_sticky_note_overlay(self, surface, font):
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
                get_rotated_rect_polygon(self.sticky_note_page, rotated_angle, offset)
            )
        pygame.draw.rect(surface, Color.STICKY_NOTE, self.sticky_note_page)
        action_button.draw(surface, font)

    def draw_blueprint_overlay(self, surface, font):
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
                get_rotated_rect_polygon(self.blueprint_page, rotated_angle, offset)
            )
        pygame.draw.rect(surface, Color.BLUEPRINT_PAGE, self.blueprint_page)
        font.render(surface, self.overlay_selected_entity, blueprint_name_pos, Color.WHITE, 1, style="center")
        surface.blit(DataFiles.get_entity_sprite(self.overlay_selected_entity), blueprint_highlight_icon)
        pygame.draw.rect(surface, Color.WHITE, blueprint_highlight_icon, width=Box.OUTLINE_WIDTH)

        def draw_blueprint_divider(label, y):
            divider_margin = 2*Box.PADDING
            label_left = self.blueprint_page.left + divider_margin
            line_left = label_left + font.get_width(label, 1, 0) + Box.PADDING
            line_right = self.blueprint_page.right - divider_margin
            font.render(surface, label, (label_left, y), Color.WHITE, 1, style="centerleft")
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
            info = { # TODO scale by level
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

        icon_size = 32 # TODO
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
                font.render(surface,str(info_key),info_rect.center,Color.WHITE,1,style="center")
            font.render(surface,str(info_value),(info_rect.right + Box.PADDING, info_rect.centery),Color.WHITE,1,style="centerleft",)
            info_index += 1
            if info_index % 2 == 0:
                y += icon_size
            
        for (icon_name, icon_text), rect in zip(icons, blueprint_icons):
            surface.blit(DataFiles.get_entity_sprite(icon_name), rect)
            pygame.draw.rect(surface, Color.WHITE, rect, width=Box.OUTLINE_WIDTH)
            xy = (rect.centerx, rect.top+0.67*rect.height)
            font.render(surface, icon_text, xy, Color.WHITE, 1, style="center", outline_color=Color.BLACK)

        overlay_pencil_sprite = DataFiles.sprites["user_interface"]["overlay_pencil"]
        overlay_pencil_rect = overlay_pencil_sprite.get_rect()
        overlay_pencil_rect.right = self.blueprint_page.right + Box.WIDTH/4 # TODO alignment
        overlay_pencil_rect.bottom = self.blueprint_page.bottom + Box.HEIGHT/2
        surface.blit(overlay_pencil_sprite, overlay_pencil_rect)

        overlay_compass_sprite = DataFiles.sprites["user_interface"]["overlay_compass"]
        overlay_compass_rect = overlay_compass_sprite.get_rect()
        overlay_compass_rect.left = self.blueprint_page.left - Box.WIDTH/4 # TODO alignment
        overlay_compass_rect.bottom = self.blueprint_page.bottom + Box.HEIGHT/2
        surface.blit(overlay_compass_sprite, overlay_compass_rect)
        self.draw_sticky_note_overlay(surface, font)

    def draw_warehouse_overlay(self, surface, font):
        pygame.draw.rect(surface, Color.CARGO_BOX_BACK, self.warehouse_overlay)

        if self.current_overlay == self.DEPOT:
            entities = [item for item, count in DataFiles.save_file["inventory"].items() if count > 0]
        if self.current_overlay == self.DECORATION_STORE:
            entities = [decoration for decoration in DataFiles.decoration_store]
        for entity, rect in zip(entities, self.warehouse_icons):
            pygame.draw.rect(surface, Color.CARGO_BOX, rect)
            image = DataFiles.get_entity_sprite(entity)
            image_rect = image.get_rect()
            image_rect.center = rect.center
            surface.blit(image, image_rect)
            pygame.draw.rect(surface, Color.CARGO_BOX_OUTLINE, image_rect, width=2*Box.OUTLINE_WIDTH)

            if self.current_overlay == self.DEPOT:
                count = DataFiles.save_file["inventory"][entity]
                count_pos = pygame.Vector2(rect.bottomright) - pygame.Vector2(2*Box.PADDING, 2*Box.PADDING)
                font.render(surface, str(count), count_pos, Color.WHITE, 1, style="center", outline_color=Color.BLACK)

        cargo_box_sprite = DataFiles.sprites["user_interface"]["cargo_box"]
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
                DataFiles.sprites["user_interface"]["forklift"],
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
        corner_rope_sprite = DataFiles.sprites["user_interface"]["corner_rope"]
        corner_rope_rect = corner_rope_sprite.get_rect()
        corner_rope_rect.right = self.warehouse_overlay.right + Box.WIDTH/8 # TODO
        corner_rope_rect.top = warehouse_decoration_top
        surface.blit(corner_rope_sprite, corner_rope_rect)

        big_corner_rope_sprite = DataFiles.sprites["user_interface"]["big_corner_rope"]
        big_corner_rope_rect = big_corner_rope_sprite.get_rect()
        big_corner_rope_rect.right = self.warehouse_overlay.right + Box.WIDTH/8 # TODO
        big_corner_rope_rect.top = warehouse_decoration_top
        surface.blit(big_corner_rope_sprite, big_corner_rope_rect)

        top_rope_sprite = DataFiles.sprites["user_interface"]["top_rope"]
        top_rope_rect = top_rope_sprite.get_rect()
        top_rope_rect.centerx = self.warehouse_overlay.centerx
        top_rope_rect.top = warehouse_decoration_top
        surface.blit(top_rope_sprite, top_rope_rect)

        rope_hook_sprite = DataFiles.sprites["user_interface"]["rope_hook"]
        rope_hook_rect = rope_hook_sprite.get_rect()
        rope_hook_rect.left = self.warehouse_overlay.left
        rope_hook_rect.top = warehouse_decoration_top
        surface.blit(rope_hook_sprite, rope_hook_rect)

        lightbulb_sprite = DataFiles.sprites["user_interface"]["lightbulb"]
        lightbulb_rect = lightbulb_sprite.get_rect()
        lightbulb_rect.left = self.warehouse_overlay.left + Box.WIDTH
        lightbulb_rect.top = warehouse_decoration_top
        surface.blit(lightbulb_sprite, lightbulb_rect)

        lightbulb_light_sprite = DataFiles.sprites["user_interface"]["lightbulb_light"]
        lightbulb_light_rect = lightbulb_light_sprite.get_rect()
        lightbulb_light_rect.centerx = lightbulb_rect.centerx
        lightbulb_light_rect.bottom = lightbulb_rect.bottom + Box.HEIGHT/4
        surface.blit(lightbulb_light_sprite, lightbulb_light_rect, special_flags=pygame.BLEND_RGB_ADD)

    def draw_clipboard_overlay(self, surface, font):
        if self.overlay_selected_entity is None:
            return
    
        clipboard_clip_rect = get_rect(
            width=Box.WIDTH, height=Box.HEIGHT/2,
            centerx=self.clipboard_bg.centerx,
            top=self.clipboard_bg.top + Box.PADDING
        )

        font_height = 10
        clipboard_name_pos = pygame.Vector2(
            self.clipboard_page.centerx,
            self.clipboard_page.top + font_height/2 + Box.PADDING + Box.HEIGHT/4
        )
        clipboard_highlight_icon = get_rect(
            width=Box.WIDTH, height=Box.HEIGHT,
            centerx=self.clipboard_page.centerx,
            top=clipboard_name_pos.y + font_height/2 + Box.PADDING
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
                get_rotated_rect_polygon(self.clipboard_page, rotated_angle, offset)
            )
        pygame.draw.rect(surface, Color.WHITE, self.clipboard_page)
        if self.current_overlay == self.DECORATION_STORE:
            coin_count = DataFiles.save_file["inventory"].get("decoration_coin", 0)

            coin_sprite = DataFiles.sprites["user_interface"]["decoration_coin"]
            coin_rect = coin_sprite.get_rect()
            coin_rect.right = self.clipboard_page.right - Box.PADDING
            coin_rect.top = self.clipboard_page.top + Box.PADDING

            for _ in range(coin_count):
                coin_rect.y -= 6 # TODO decoration coin height
                surface.blit(coin_sprite, coin_rect)
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
            width=4
        ) # TODO width
        font.render(surface, self.overlay_selected_entity, clipboard_name_pos, Color.BLACK, 1, style="center")
        surface.blit(DataFiles.get_entity_sprite(self.overlay_selected_entity), clipboard_highlight_icon)
        pygame.draw.rect(surface, Color.BLACK, clipboard_highlight_icon, width=Box.OUTLINE_WIDTH)

        if self.current_overlay == self.DEPOT:
            desc = DataFiles.item_descriptions.get(self.overlay_selected_entity, "no description")
        if self.current_overlay == self.DECORATION_STORE:
            desc = DataFiles.decoration_store[self.overlay_selected_entity]["description"]
        
        desc_topleft = pygame.Vector2(
            self.clipboard_page.left + Box.PADDING + Box.WIDTH/4, # TODO fix alignment
            clipboard_highlight_icon.bottom + Box.PADDING + Box.HEIGHT/4
        )
        desc_text_boxwidth = self.clipboard_page.width - 2*Box.PADDING - Box.WIDTH/2
        font.render(surface, desc, desc_topleft, Color.BLACK, 1, style="topleft", box_width=desc_text_boxwidth)

        if self.current_overlay == self.DECORATION_STORE:
            signature_rect = self.decoration_signature_button.rect
            x_rect = get_rect(
                width=Box.WIDTH/6,
                height=Box.WIDTH/6,
                right=signature_rect.left - Box.PADDING,
                bottom=signature_rect.bottom - Box.PADDING
            )
            pygame.draw.rect(surface, (220, 220, 220), signature_rect)
            pygame.draw.line(
                surface,
                Color.BLACK,
                x_rect.topleft,
                x_rect.bottomright,
                width=Box.OUTLINE_WIDTH
            )
            pygame.draw.line(
                surface,
                Color.BLACK,
                x_rect.bottomleft,
                x_rect.topright,
                width=Box.OUTLINE_WIDTH
            )
            pygame.draw.line(
                surface,
                Color.BLACK,
                signature_rect.bottomleft,
                signature_rect.bottomright,
                width=Box.OUTLINE_WIDTH
            )
            font.render(
                surface,
                "stamp here",
                (signature_rect.left, signature_rect.bottom + Box.PADDING),
                Color.BLACK,
                1,
                style="topleft"
            )

            smiley_sprite = DataFiles.sprites["user_interface"]["smiley"]
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

            stamp_sprite = DataFiles.sprites["user_interface"]["stamp"]
            stamp_rect = stamp_sprite.get_rect()
            if self.decoration_stamp_animation_timer <= 0:
                stamp_rect.center = self.clipboard_page.bottomleft
                surface.blit(stamp_sprite, stamp_rect)
            else:
                elapsed = self.DECORATION_STAMP_ANIMATION_DURATION - self.decoration_stamp_animation_timer
                target_pos = pygame.Vector2(self.decoration_stamp_animation_pos)
                above_pos = target_pos - pygame.Vector2(0, Box.HEIGHT)
                if elapsed >= self.DECORATION_STAMP_LIFT_TIME:
                    # stamp is at the above_pos
                    stamp_rect.centerx = above_pos.x
                    stamp_rect.bottom = above_pos.y + Box.HEIGHT/2
                    surface.blit(stamp_sprite, stamp_rect)
                elif elapsed >= self.DECORATION_STAMP_DOWN_TIME:
                    # stamp is moving up
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
                    # stamp is moving down
                    progress = min(
                        1,
                        elapsed / self.DECORATION_STAMP_DOWN_TIME
                    )
                    stamp_pos = above_pos.lerp(target_pos, progress)
                    stamp_rect.centerx = stamp_pos.x
                    stamp_rect.bottom = stamp_pos.y + Box.HEIGHT/2
                    surface.blit(stamp_sprite, stamp_rect)

        overlay_pencil_sprite = DataFiles.sprites["user_interface"]["overlay_pencil"]
        overlay_pencil_rect = overlay_pencil_sprite.get_rect()
        overlay_pencil_rect.right = self.clipboard_page.right + Box.WIDTH/4 # TODO alignment
        overlay_pencil_rect.bottom = self.clipboard_page.bottom + Box.HEIGHT/2
        surface.blit(overlay_pencil_sprite, overlay_pencil_rect)

    def rotate_decoration_direction(self):
        self.decoration_direction_index = (self.decoration_direction_index + 1) % len(self.DECORATION_DIRECTIONS)

    def release_shipgirl_from_interaction(self, shipgirl):
        shipgirl.interacting_decoration = None
        shipgirl.wander_target = pygame.Vector2(
            random.uniform(Decorations.floor_rect.left, Decorations.floor_rect.right),
            random.uniform(Decorations.floor_rect.top, Decorations.floor_rect.bottom)
        )
        shipgirl.pause_time = random.uniform(1, 3) # TODO

    def decoration_has_interacting_shipgirl(self, tilepos_anchor):
        tilepos_anchor = tuple(tilepos_anchor)
        return any(
            shipgirl.interacting_decoration == tilepos_anchor
            for shipgirl in self.menu_manager.available_shipgirls
        )

    def snap_shipgirl_to_interactable_decoration(self, shipgirl):
        for decoration, tilepos_anchor, direction in DataFiles.save_file["decorations"]:
            decoration_store_info = DataFiles.decoration_store[decoration]
            if not decoration_store_info["interactable"]:
                continue

            sprite_rect = get_decoration_sprite_rect(decoration, direction, tilepos_anchor)
            if not sprite_rect.collidepoint(shipgirl.rect.center):
                continue

            if self.decoration_has_interacting_shipgirl(tilepos_anchor):
                continue

            snap_x, snap_y = decoration_store_info[direction]["snap"]
            shipgirl.pos = pygame.Vector2(
                sprite_rect.left + sprite_rect.width * snap_x,
                sprite_rect.top + sprite_rect.height * snap_y
            )
            shipgirl.rect.center = shipgirl.pos
            shipgirl.interacting_decoration = tuple(tilepos_anchor)
            return True

        shipgirl.interacting_decoration = None
        return False

    def release_shipgirls_from_deleted_decoration(self, decoration_data):
        deleted_decoration = tuple(decoration_data[1])
        for shipgirl in self.menu_manager.available_shipgirls:
            if shipgirl.interacting_decoration == deleted_decoration:
                self.release_shipgirl_from_interaction(shipgirl)

    def update_decorate_port_menu_overlay(self, events):
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button != 1:
                    continue

                if self.decoration_depot_overlay.collidepoint(event.pos):
                    decoration_index = 0
                    for decoration, amt in DataFiles.save_file["decoration_depot"].items():
                        if amt <= 0:
                            continue
                        rect = get_rect(
                            width=Box.WIDTH, height=Box.HEIGHT,
                            left=self.decoration_depot_overlay.left + (decoration_index%3)*(Box.WIDTH+Box.PADDING) + Box.PADDING,
                            top=self.decoration_depot_overlay.top + (decoration_index//3)*(Box.HEIGHT+Box.PADDING) + Box.PADDING
                        )
                        if rect.collidepoint(event.pos):
                            DataFiles.sfx["click"].play()
                            if self.selected_decoration_in_depot == decoration:
                                self.selected_decoration_in_depot = None
                            else:
                                self.selected_decoration_in_depot = decoration
                                self.deleting_decoration = False
                            break
                        decoration_index += 1
                    else:
                        delete_rect = get_rect(
                            width=Box.WIDTH, height=Box.HEIGHT,
                            left=self.decoration_depot_overlay.left + (decoration_index%3)*(Box.WIDTH+Box.PADDING) + Box.PADDING,
                            top=self.decoration_depot_overlay.top + (decoration_index//3)*(Box.HEIGHT+Box.PADDING) + Box.PADDING
                        )
                        if delete_rect.collidepoint(event.pos):
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
                                self.dragged_shipgirl_offset = shipgirl.pos - pygame.Vector2(event.pos)
                                shipgirl.dragged = True
                                shipgirl.interacting_decoration = None
                                break

                    if self.dragged_shipgirl is None and self.can_start_decorate_camera_drag(event.pos):
                        self.camera_dragging = True
                        continue
            if event.type == pygame.MOUSEMOTION:
                if self.update_camera_drag(event):
                    continue

                self.toggle_decoration_mode_button.hover(event.pos)

                if self.dragged_shipgirl is not None:
                    self.dragged_shipgirl.pos = pygame.Vector2(event.pos) + self.dragged_shipgirl_offset
                    self.dragged_shipgirl.rect.center = self.dragged_shipgirl.pos
                    continue

                if self.decoration_depot_drag_offset is not None:
                    self.decoration_depot_overlay.topleft = pygame.Vector2(event.pos) + self.decoration_depot_drag_offset
            if event.type == pygame.MOUSEBUTTONUP:
                if event.button == 3 and self.selected_decoration_in_depot is not None:
                    DataFiles.sfx["click"].play()
                    self.rotate_decoration_direction()
                    self.rotated_decoration = True
                    continue

                if event.button != 1:
                    continue

                if self.camera_dragging:
                    self.camera_dragging = False
                    continue

                if self.dragged_shipgirl is not None:
                    self.dragged_shipgirl.dragged = False
                    if not self.snap_shipgirl_to_interactable_decoration(self.dragged_shipgirl):
                        self.release_shipgirl_from_interaction(self.dragged_shipgirl)

                    self.dragged_shipgirl = None
                    self.dragged_shipgirl_offset = None
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
                    decoration_index = 0
                    for decoration, amt in DataFiles.save_file["decoration_depot"].items():
                        if amt <= 0:
                            continue
                        rect = get_rect(
                            width=Box.WIDTH, height=Box.HEIGHT,
                            left=self.decoration_depot_overlay.left + (decoration_index%3)*(Box.WIDTH+Box.PADDING) + Box.PADDING,
                            top=self.decoration_depot_overlay.top + (decoration_index//3)*(Box.HEIGHT+Box.PADDING) + Box.PADDING
                        )
                        if rect.collidepoint(event.pos):
                            DataFiles.sfx["click"].play()
                            if self.selected_decoration_in_depot == decoration:
                                self.selected_decoration_in_depot = None
                            else:
                                self.selected_decoration_in_depot = decoration
                                self.deleting_decoration = False
                            break
                        decoration_index += 1
                    else:
                        delete_rect = get_rect(
                            width=Box.WIDTH, height=Box.HEIGHT,
                            left=self.decoration_depot_overlay.left + (decoration_index%3)*(Box.WIDTH+Box.PADDING) + Box.PADDING,
                            top=self.decoration_depot_overlay.top + (decoration_index//3)*(Box.HEIGHT+Box.PADDING) + Box.PADDING
                        )
                        if delete_rect.collidepoint(event.pos):
                            DataFiles.sfx["click"].play()
                            self.deleting_decoration = not self.deleting_decoration
                            self.selected_decoration_in_depot = None
                elif self.deleting_decoration:
                    clicked_tilepos = (
                        (event.pos[0] - Decorations.floor_rect.left) // Decorations.TILESIZE,
                        (event.pos[1] - Decorations.floor_rect.top) // Decorations.TILESIZE
                    )
                    for decoration_index, decoration_data in enumerate(DataFiles.save_file["decorations"]):
                        decoration, tilepos_anchor, direction = decoration_data
                        decoration_info = DataFiles.decoration_store[decoration][direction]
                        if (
                            tilepos_anchor[0] <= clicked_tilepos[0] < tilepos_anchor[0] + decoration_info["width"]
                            and tilepos_anchor[1] <= clicked_tilepos[1] < tilepos_anchor[1] + decoration_info["height"]
                        ):
                            DataFiles.sfx["click"].play()
                            self.release_shipgirls_from_deleted_decoration(decoration_data)
                            DataFiles.save_file["decorations"].pop(decoration_index)
                            DataFiles.save_file["decoration_depot"][decoration] = (
                                DataFiles.save_file["decoration_depot"].get(decoration, 0) + 1
                            )
                            self.removed_decoration = True
                            break
                elif self.selected_decoration_in_depot is not None:
                    occupied_tiles = set() # TODO code optimization
                    for decoration_data in DataFiles.save_file["decorations"]:
                        decoration, tilepos_anchor, direction = decoration_data
                        occupied_tiles.update(get_decoration_tiles(decoration, direction, tilepos_anchor))

                    decoration = self.selected_decoration_in_depot
                    direction = self.DECORATION_DIRECTIONS[self.decoration_direction_index]
                    clicked_tilepos = (
                        (event.pos[0] - Decorations.floor_rect.left) // Decorations.TILESIZE,
                        (event.pos[1] - Decorations.floor_rect.top) // Decorations.TILESIZE
                    )
                    place_tiles = get_decoration_tiles(decoration, direction, clicked_tilepos)
                    if place_tiles.intersection(occupied_tiles):
                        continue
                    if not in_tileable_area(place_tiles):
                        continue
                    DataFiles.sfx["click"].play()
                    DataFiles.save_file["decorations"].append((decoration,clicked_tilepos,direction))
                    DataFiles.save_file["decoration_depot"][decoration] -= 1
                    self.placed_decoration = True
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
                if event.type == pygame.MOUSEBUTTONUP:
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
            shipgirl.update(dt)
            shipgirl.animate(dt)

    def draw_decoration_mode_overlay(self, surface, font):
        if self.deleting_decoration:
            mpos = pygame.mouse.get_pos()
            hovered_tilepos = (
                (mpos[0] - Decorations.floor_rect.left) // Decorations.TILESIZE,
                (mpos[1] - Decorations.floor_rect.top) // Decorations.TILESIZE
            )
            for decoration_data in DataFiles.save_file["decorations"]:
                decoration, tilepos_anchor, direction = decoration_data
                decoration_info = DataFiles.decoration_store[decoration][direction]
                hovered_decoration_tiles = get_decoration_tiles(decoration, direction, tilepos_anchor)
                if hovered_tilepos in hovered_decoration_tiles:
                    rect = get_rect(
                        width=decoration_info["width"] * Decorations.TILESIZE,
                        height=decoration_info["height"] * Decorations.TILESIZE,
                        left=Decorations.floor_rect.left + tilepos_anchor[0] * Decorations.TILESIZE,
                        top=Decorations.floor_rect.top + tilepos_anchor[1] * Decorations.TILESIZE
                    )
                    pygame.draw.rect(surface, Color.RED, rect, width=Box.OUTLINE_WIDTH)
                    break

        if self.selected_decoration_in_depot:
            occupied_tiles = set() # TODO code optimization
            for decoration_data in DataFiles.save_file["decorations"]:
                decoration, tilepos_anchor, direction = decoration_data
                occupied_tiles.update(get_decoration_tiles(decoration, direction, tilepos_anchor))

            decoration = self.selected_decoration_in_depot
            direction = self.DECORATION_DIRECTIONS[self.decoration_direction_index]
            mpos = pygame.mouse.get_pos()
            hovered_tilepos = (
                (mpos[0] - Decorations.floor_rect.left) // Decorations.TILESIZE,
                (mpos[1] - Decorations.floor_rect.top) // Decorations.TILESIZE
            )
            decoration_info = DataFiles.decoration_store[decoration][direction]
            place_tiles = get_decoration_tiles(decoration, direction, hovered_tilepos)
            rect = get_rect(
                width=decoration_info["width"] * Decorations.TILESIZE,
                height=decoration_info["height"] * Decorations.TILESIZE,
                left=Decorations.floor_rect.left + hovered_tilepos[0] * Decorations.TILESIZE,
                top=Decorations.floor_rect.top + hovered_tilepos[1] * Decorations.TILESIZE
            )
            sprite = DataFiles.sprites["decorations"][f"{decoration}_{direction}"]
            sprite_rect = sprite.get_rect()
            sprite_rect.bottomleft = rect.bottomleft
            surface.blit(sprite, sprite_rect)
            if not place_tiles.intersection(occupied_tiles) and in_tileable_area(place_tiles):
                pygame.draw.rect(surface, Color.WHITE, rect, width=Box.OUTLINE_WIDTH)
            else:
                pygame.draw.rect(surface, Color.RED, rect, width=Box.OUTLINE_WIDTH)

        for shipgirl in self.menu_manager.available_shipgirls:
            shipgirl.draw(surface, font)
        
        for option in self.shipgirl_dialogue_options:
            option.draw(surface, font)

        self.toggle_decoration_mode_button.draw(surface, font)

        pygame.draw.rect(surface, Color.CARGO_BOX_BACK, self.decoration_depot_overlay)
        decoration_index = 0
        for decoration, amt in DataFiles.save_file["decoration_depot"].items():
            if amt <= 0:
                continue
            rect = get_rect(
                width=Box.WIDTH, height=Box.HEIGHT,
                left=self.decoration_depot_overlay.left + (decoration_index%3)*(Box.WIDTH+Box.PADDING) + Box.PADDING,
                top=self.decoration_depot_overlay.top + (decoration_index//3)*(Box.HEIGHT+Box.PADDING) + Box.PADDING
            )
            sprite = DataFiles.get_entity_sprite(decoration)
            pygame.draw.rect(surface, Color.CARGO_BOX, rect)
            surface.blit(sprite, rect)
            font.render(surface,str(amt),rect.center,Color.WHITE,1,style="center",outline_color=Color.BLACK)
            if self.selected_decoration_in_depot == decoration:
                pygame.draw.rect(surface, Color.WHITE, rect, width=Box.OUTLINE_WIDTH)
            decoration_index += 1
        delete_rect = get_rect(
            width=Box.WIDTH, height=Box.HEIGHT,
            left=self.decoration_depot_overlay.left + (decoration_index%3)*(Box.WIDTH+Box.PADDING) + Box.PADDING,
            top=self.decoration_depot_overlay.top + (decoration_index//3)*(Box.HEIGHT+Box.PADDING) + Box.PADDING
        )
        pygame.draw.rect(surface, Color.CARGO_BOX, delete_rect)
        surface.blit(DataFiles.sprites["user_interface"]["remove_decoration"], delete_rect)
        if self.deleting_decoration:
            pygame.draw.rect(surface, Color.WHITE, delete_rect, width=Box.OUTLINE_WIDTH)

    def draw(self, surface, font):
        surface.blit(Decorations.floor_surf, Decorations.floor_rect)

        decorations = sorted(
            DataFiles.save_file["decorations"],
            key=lambda decoration_data : decoration_data[1][1]
        )
        for decoration_data in decorations:
            decoration, tilepos_anchor, direction = decoration_data
            sprite = DataFiles.sprites["decorations"][f"{decoration}_{direction}"]
            sprite_rect = get_decoration_sprite_rect(decoration, direction, tilepos_anchor)
            surface.blit(sprite, sprite_rect)

        if self.is_decorating:
            self.draw_decoration_mode_overlay(surface, font)
            return

        for shipgirl in self.menu_manager.available_shipgirls:
            shipgirl.draw(surface, font)
        
        for option in self.shipgirl_dialogue_options:
            option.draw(surface, font)

        self.toggle_decoration_mode_button.draw(surface, font)
        
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
            button.draw(surface, font)
            self.draw_button_notification(surface, button, notification)

        if self.current_overlay in [self.DEPOT, self.DECORATION_STORE]:
            self.draw_warehouse_overlay(surface, font)
            self.draw_clipboard_overlay(surface, font)
        if self.current_overlay in [self.INTEL_CENTER, self.SHIPYARD, self.GEAR_LAB]:
            self.draw_dossier_overlay(surface, font)
            self.draw_blueprint_overlay(surface, font)
    
        self.menu_manager.quest_manager.draw(surface, font)
        for choose_faction_button in self.choose_faction_buttons:
            choose_faction_button.draw(surface, font)
