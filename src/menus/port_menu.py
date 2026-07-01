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

def in_tileable_area(tiles):
    return (
        min(tile[0] for tile in tiles) >= 0
        and max(tile[0] for tile in tiles) < Decorations.NUM_TILES_IN_ROW
        and min(tile[1] for tile in tiles) >= 0
        and max(tile[1] for tile in tiles) <= Decorations.NUM_TILES_IN_COL
    )

class PortMenu:
    NO_OVERLAY = -1
    DEPOT = 0
    SHIPYARD = 1
    GEAR_LAB = 2
    INTEL_CENTER = 3
    DECORATION_STORE = 4
    DECORATION_DIRECTIONS = ["north", "east", "south", "west"]

    def __init__(self, menu_manager):
        self.menu_manager = menu_manager
        Decorations.floor_rect.center = (screen_x(0.5), screen_y(0.5))
        self.camera_dragging = False
        self.camera_drag_last_pos = None

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

        self.current_overlay = self.NO_OVERLAY

        self.visited_inventory = False
        self.visited_intel_center = False

        overlay_buttons_flexbox_width = self.open_select_sortie_menu_button.rect.left
        num_overlay_buttons = 5

        def open_overlay_button_factory(index, overlay_enum, icon):
            def open_overlay():
                self.current_overlay = overlay_enum

                if overlay_enum == self.SHIPYARD:
                    if DataFiles.save_file["research_target"] is not None:
                        self.blueprint_selected_item = DataFiles.save_file["research_target"]
                        self.blueprint_confirm_button.active = True
                        unique_item = DataFiles.shipgirl_data[self.blueprint_selected_item]["unique_item"]
                        if DataFiles.save_file["inventory"].get(unique_item, 0) > 0:
                            self.blueprint_confirm_button.background_img = DataFiles.sprites["user_interface"]["construct"]
                            self.blueprint_confirm_button.text = "construct"
                        else:
                            self.blueprint_confirm_button.background_img = DataFiles.sprites["user_interface"]["research"]
                            self.blueprint_confirm_button.text = "research"
                    
                    for i, faction in enumerate(self.shipgirl_filters):
                        if DataFiles.save_file["unlocked_factions"][0] == faction:
                            self.selected_overlay_filter = i
                            break

            return Button(
                get_rect(
                    width=Box.WIDTH, height=Box.HEIGHT,
                    centerx=index/(num_overlay_buttons+1) * overlay_buttons_flexbox_width,
                    bottom=Box.BOTTOM_OF_SCREEN
                ),
                open_overlay,
                active=False,
                background_styling={
                    "background_color": Color.BLACK,
                    "background_img": DataFiles.sprites["user_interface"][icon],
                    "opacity": 160,
                },
                hover_styling={"opacity": 200}
            )

        self.open_depot_overlay_button = open_overlay_button_factory(
            1, self.DEPOT, "depot"
        )
        self.open_intel_center_overlay_button = open_overlay_button_factory(
            2, self.INTEL_CENTER, "intel_center"
        )
        self.open_shipyard_overlay_button = open_overlay_button_factory(
            3, self.SHIPYARD, "shipyard"
        )
        self.open_gear_lab_overlay_button = open_overlay_button_factory(
            4, self.GEAR_LAB, "gear_lab"
        )

        self.dossier_overlay = get_rect(
            width=5*(Box.WIDTH+Box.PADDING)+Box.PADDING + 2*Box.PADDING,
            height=3*(Box.HEIGHT+Box.PADDING)+Box.PADDING + 2*Box.PADDING + Box.HEIGHT,
            right=screen_x(0.5) - Box.PADDING,
            centery=screen_y(0.5)
        )
        self.dossier_bg = get_rect(
            width=self.dossier_overlay.width,
            height=self.dossier_overlay.height - Box.HEIGHT,
            right=self.dossier_overlay.right,
            bottom=self.dossier_overlay.bottom
        )
        num_dossier_tabs = 7
        tab_width = self.dossier_bg.width / num_dossier_tabs
        tab_height = 48
        self.dossier_tabs = [
            get_rect(
                width=tab_width, height=tab_height,
                left=self.dossier_bg.left+i*tab_width,
                bottom=self.dossier_bg.top
            ) for i in range(num_dossier_tabs)
        ]
        self.dossier_page = get_rect(
            width=self.dossier_overlay.width - 2*Box.PADDING,
            height=self.dossier_overlay.height - Box.HEIGHT - 2*Box.PADDING,
            right=self.dossier_overlay.right - Box.PADDING,
            bottom=self.dossier_overlay.bottom - Box.PADDING
        )
        dossier_page_center = pygame.Vector2(self.dossier_page.center)
        rotated_angle = 5
        page_horizontal = get_vec(self.dossier_page.width/2, math.radians(rotated_angle))
        page_vertical = get_vec(self.dossier_page.height/2, math.radians(90+rotated_angle))
        self.misaligned_dossier_page = [
            dossier_page_center + page_horizontal + page_vertical,
            dossier_page_center - page_horizontal + page_vertical,
            dossier_page_center - page_horizontal - page_vertical,
            dossier_page_center + page_horizontal - page_vertical,
        ]
        self.blueprint_page = get_rect(
            left=screen_x(0.5)+Box.PADDING,
            centery=screen_y(0.5),
            width=4*(Box.WIDTH + Box.PADDING) + Box.PADDING,
            height=5*(Box.HEIGHT + Box.PADDING) + Box.PADDING
        )
        self.blueprint_page.left = screen_x(0.5) + Box.PADDING
        self.blueprint_page.centery = screen_y(0.5)
        blueprint_page_center = pygame.Vector2(self.blueprint_page.center)
        rotated_angle = 5
        page_horizontal = get_vec(self.blueprint_page.width/2, math.radians(rotated_angle))
        page_vertical = get_vec(self.blueprint_page.height/2, math.radians(90+rotated_angle))
        self.misaligned_blueprint_page = [
            blueprint_page_center + page_horizontal + page_vertical,
            blueprint_page_center - page_horizontal + page_vertical,
            blueprint_page_center - page_horizontal - page_vertical,
            blueprint_page_center + page_horizontal - page_vertical,
        ]

        self.selected_overlay_filter = 0
        self.shipgirl_filters = ["USS", "HMS", "IJN", "KMS"]
        self.equipment_filters = ["DD", "CL", "CA", "BB", "SS", "CV", "AUX"]
        self.siren_filters = ["DD", "CL", "CA", "BB", "SS", "CV"]

        num_icons_per_row = (self.dossier_page.width-Box.PADDING) // (Box.WIDTH+Box.PADDING)
        icon_padding = (self.dossier_page.width - 2*Box.PADDING - num_icons_per_row*Box.WIDTH) / (num_icons_per_row-1)
        self.dossier_icons = [
            get_rect(
                width=Box.WIDTH, height=Box.HEIGHT,
                left=self.dossier_page.left+Box.PADDING+(i%num_icons_per_row)*(Box.WIDTH+icon_padding),
                top=self.dossier_page.top+Box.PADDING+(i//num_icons_per_row)*(Box.HEIGHT+icon_padding)
            ) for i in range(16)
        ]

        self.blueprint_name = pygame.Vector2(
            self.blueprint_page.centerx,
            self.blueprint_page.top + Box.PADDING + 5
        )
        self.blueprint_icon = get_rect(
            width=Box.WIDTH, height=Box.HEIGHT,
            centerx=self.blueprint_page.centerx,
            top=self.blueprint_name.y + 5 + Box.PADDING
        )
        num_icons_per_row = 3
        self.blueprint_icons = [
            get_rect(
                width=Box.WIDTH, height=Box.HEIGHT,
                centerx=self.blueprint_page.centerx+(i%num_icons_per_row-1)*(Box.WIDTH+Box.PADDING),
                bottom=self.blueprint_page.bottom-2*Box.PADDING-Box.HEIGHT+(i//num_icons_per_row)*(Box.HEIGHT+Box.PADDING)
            ) for i in range(2*num_icons_per_row)
        ]

        def blueprint_confirm():
            if self.current_overlay == self.SHIPYARD:
                selected_entity_info = DataFiles.shipgirl_data[self.blueprint_selected_item]
                hull_type = selected_entity_info["hull_type"]
                unique_item = selected_entity_info["unique_item"]
                inventory = DataFiles.save_file["inventory"]
                specialized_wisdom_cubes = DataFiles.save_file["specialized_wisdom_cubes"]
                selected_entity_reqs = {
                    f"{hull_type}_blueprint": 1,
                    unique_item: 1
                }
                has_specialized_wisdom_cube = self.blueprint_selected_item in specialized_wisdom_cubes
                has_generic_wisdom_cube = inventory.get("wisdom_cube", 0) > 0
                if (
                    all(inventory.get(ingredient, 0) >= req for ingredient, req in selected_entity_reqs.items())
                    and has_specialized_wisdom_cube
                ):
                    shipgirl_exp = specialized_wisdom_cubes[self.blueprint_selected_item]
                    DataFiles.save_file["shipgirls"][self.blueprint_selected_item] = {
                        "equipment": [None, None, None],
                        "exp": shipgirl_exp
                    }
                    shipgirl = Shipgirl(self.blueprint_selected_item, True)
                    self.menu_manager.available_shipgirls.append(shipgirl)
                    for ingredient, req in selected_entity_reqs.items():
                        inventory[ingredient] -= req
                    specialized_wisdom_cubes.pop(self.blueprint_selected_item)
                    DataFiles.save_file["research_target"] = None
                    self.blueprint_selected_item = None
                    self.blueprint_confirm_button.active = False
                elif (
                    DataFiles.save_file["research_target"] != self.blueprint_selected_item
                    and not has_specialized_wisdom_cube
                    and has_generic_wisdom_cube
                ):
                    inventory["wisdom_cube"] -= 1
                    specialized_wisdom_cubes[self.blueprint_selected_item] = 0
                    DataFiles.save_file["research_target"] = self.blueprint_selected_item
            elif self.current_overlay == self.GEAR_LAB:
                selected_entity_reqs = DataFiles.equipment_data[self.blueprint_selected_item]["craft_reqs"]
                if all(DataFiles.save_file["inventory"].get(ingredient, 0) >= req for ingredient, req in selected_entity_reqs.items()):
                    DataFiles.save_file["equipment"][self.blueprint_selected_item] = DataFiles.save_file["equipment"].get(self.blueprint_selected_item, 0) + 1
                    for ingredient, req in selected_entity_reqs.items():
                        DataFiles.save_file["inventory"][ingredient] -= req

        self.blueprint_confirm_button = Button(
            get_rect(
                width=2*Box.WIDTH, height=Box.HEIGHT,
                centerx=self.blueprint_page.centerx,
                bottom=self.blueprint_page.bottom-Box.PADDING
            ),
            blueprint_confirm,
            active=False,
            background_styling={
                "background_img": None,
                "background_img_align": (1/4, 1/2),
                "outline_color": Color.WHITE,
                "outline_width": Box.OUTLINE_WIDTH
            },
            text_styling={
                "text": None,
                "text_align": (2/3, 1/2),
                "text_color": Color.WHITE
            }
        )
        self.blueprint_selected_item = None

        self.depot_overlay = get_rect(
            width=6*(Box.WIDTH+Box.PADDING) + Box.PADDING,
            height=4*(Box.HEIGHT+Box.PADDING) + Box.PADDING,
            center=(screen_x(0.5), screen_y(0.5))
        )

        self.open_decoration_store_overlay_button = open_overlay_button_factory(
            5, self.DECORATION_STORE, "decoration_store"
        )

        self.store_overlay = get_rect(
            width=5*(Box.WIDTH+Box.PADDING) + Box.PADDING,
            height=4*(Box.HEIGHT+Box.PADDING) + Box.PADDING,
            right=screen_x(0.5),
            centery=screen_y(0.5)
        )
        self.store_checkout_overlay = get_rect(
            width=3*(Box.WIDTH+Box.PADDING) + Box.PADDING,
            height=self.store_overlay.height,
            left=screen_x(0.5) + Box.PADDING,
            centery=screen_y(0.5)
        )

        def store_confirm():
            DataFiles.sfx["coins"].play()
            DataFiles.save_file["decoration_depot"][self.store_selected_item] = (
                DataFiles.save_file["decoration_depot"].get(self.store_selected_item, 0) + 1
            )
            DataFiles.save_file["inventory"]["decoration_coin"] = (
                DataFiles.save_file["inventory"].get("decoration_coin", 0) - 1
            )
            if DataFiles.save_file["inventory"]["decoration_coin"] <= 0:
                self.store_confirm_button.active = False

        self.store_confirm_button = Button(
            get_rect(
                width=2*Box.WIDTH, height=Box.HEIGHT,
                centerx=self.store_checkout_overlay.centerx,
                bottom=self.store_checkout_overlay.bottom-Box.PADDING
            ),
            store_confirm,
            active=False,
            background_styling={
                "background_color": Color.CARGO_BOX,
            },
            text_styling={
                "text": "buy decoration",
                "text_color": Color.WHITE
            }
        )
        self.store_selected_item = None

        def open_close_decoration_menu():
            self.decorating_port_menu = not self.decorating_port_menu

            close_shipgirl_dialogue_options()

        self.open_close_decoration_menu_button = Button(
            rect=get_rect(width=Box.WIDTH, height=Box.HEIGHT, right=Box.RIGHT_OF_SCREEN, top=Box.TOP_OF_SCREEN),
            callback=open_close_decoration_menu,
            active=False,
            background_styling={
                "background_color": Color.BLACK,
                "background_img": DataFiles.sprites["user_interface"]["decorate_toggle"],
                "opacity": 160,
            },
            hover_styling={"opacity": 200}
        )
        self.decorating_port_menu = False

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

    def active_button_collidepoint(self, button, pos):
        return button.active and button.rect.collidepoint(pos)

    def port_camera_pan(self, delta):
        old_topleft = pygame.Vector2(Decorations.floor_rect.topleft)
        Decorations.floor_rect.x += int(delta.x)
        Decorations.floor_rect.y += int(delta.y)

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

        current_pos = pygame.Vector2(event.pos)
        self.port_camera_pan(current_pos - self.camera_drag_last_pos)
        self.camera_drag_last_pos = current_pos
        return True

    def stop_camera_drag(self):
        was_dragging = self.camera_dragging
        self.camera_dragging = False
        self.camera_drag_last_pos = None
        return was_dragging

    def decoration_at_pos(self, pos):
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
                return True
        return False

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
            self.open_close_decoration_menu_button,
            *self.choose_faction_buttons,
            *self.shipgirl_dialogue_options,
        ]
        if any(self.active_button_collidepoint(button, pos) for button in buttons):
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
        if self.active_button_collidepoint(self.open_close_decoration_menu_button, pos):
            return False
        if self.selected_decoration_in_depot is not None:
            return False
        if self.deleting_decoration and self.decoration_at_pos(pos):
            return False
        return not any(shipgirl.rect.collidepoint(pos) for shipgirl in self.menu_manager.available_shipgirls)

    def start_camera_drag(self, pos):
        self.camera_dragging = True
        self.camera_drag_last_pos = pygame.Vector2(pos)

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

    def update_no_overlay(self, events):
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1 and self.can_start_no_overlay_camera_drag(event.pos):
                    self.start_camera_drag(event.pos)
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
                    self.open_close_decoration_menu_button,
                    *self.choose_faction_buttons,
                    *self.shipgirl_dialogue_options,
                ]
                for button in buttons:
                    button.hover(event.pos)
            if event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1 and self.stop_camera_drag():
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
                    self.open_close_decoration_menu_button,
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

    def draw_inventory_overlay(self, surface, font):
        pygame.draw.rect(surface, Color.CARGO_BOX_BACK, self.depot_overlay)

        num_items_in_row = (self.depot_overlay.width - Box.PADDING) // (Box.WIDTH+Box.PADDING)
        item_index = 0
        for item, count in DataFiles.save_file["inventory"].items():
            if count <= 0:
                continue
            left = self.depot_overlay.left + Box.PADDING + (item_index%num_items_in_row)*(Box.WIDTH+Box.PADDING)
            top = self.depot_overlay.top + Box.PADDING + (item_index//num_items_in_row)*(Box.HEIGHT+Box.PADDING)
            rect = get_rect(width=Box.WIDTH, height=Box.HEIGHT, left=left, top=top)
            pygame.draw.rect(surface, Color.CARGO_BOX, rect)
            surface.blit(DataFiles.get_entity_sprite(item), rect)
            font.render(surface, str(count), rect.center, Color.WHITE, 1, style="center", outline_color=Color.BLACK)
            item_index += 1

    def exit_overlay(self, mouseup_event):
        if self.current_overlay == self.DEPOT:
            if not self.depot_overlay.collidepoint(mouseup_event.pos):
                self.current_overlay = self.NO_OVERLAY
        elif self.current_overlay == self.DECORATION_STORE:
            if (
                not self.store_overlay.collidepoint(mouseup_event.pos)
                and (
                    self.store_selected_item is None
                    or not self.store_checkout_overlay.collidepoint(mouseup_event.pos)
                )
            ):
                self.current_overlay = self.NO_OVERLAY
                self.store_selected_item = None
                self.store_confirm_button.active = False
        else:
            if (
                not self.dossier_overlay.collidepoint(mouseup_event.pos)
                and (
                    self.blueprint_selected_item is None
                    or not self.blueprint_page.collidepoint(mouseup_event.pos)
                )
            ):
                self.current_overlay = self.NO_OVERLAY
                self.blueprint_selected_item = None
                self.blueprint_confirm_button.active = False
                self.selected_overlay_filter = 0

    def overlay_mouseup_logic(self, mouseup_event, entities, entity_filters, activate_confirm_button):
        click = False
        for entity, rect in zip(entities, self.dossier_icons):
            if rect.collidepoint(mouseup_event.pos):
                click = True
                self.blueprint_selected_item = entity
                self.blueprint_confirm_button.active = activate_confirm_button

                if self.current_overlay == self.SHIPYARD:
                    unique_item = DataFiles.shipgirl_data[self.blueprint_selected_item]["unique_item"]
                    if DataFiles.save_file["inventory"].get(unique_item, 0) > 0:
                        self.blueprint_confirm_button.background_img = DataFiles.sprites["user_interface"]["construct"]
                        self.blueprint_confirm_button.text = "construct"
                    else:
                        self.blueprint_confirm_button.background_img = DataFiles.sprites["user_interface"]["research"]
                        self.blueprint_confirm_button.text = "research"
                else:
                    self.blueprint_confirm_button.background_img = DataFiles.sprites["user_interface"]["construct"]
                    self.blueprint_confirm_button.text = "construct"
        
        for i, (cat, rect) in enumerate(zip(entity_filters, self.dossier_tabs)):
            if rect.collidepoint(mouseup_event.pos):
                click = True
                self.selected_overlay_filter = i

        if click:
            DataFiles.sfx["click"].play()

    def draw_dual_panel_overlay(self, surface, font, entities, entity_filters, info, icons):
        pygame.draw.rect(surface, Color.DOSSIER, self.dossier_bg)
        for i, (cat, rect) in enumerate(zip(entity_filters, self.dossier_tabs)):
            if self.selected_overlay_filter == i:
                color = Color.DOSSIER
            else:
                color = Color.DOSSIER_BACK
            tab_polygon = [
                rect.topleft,
                rect.bottomleft,
                rect.bottomright,
                (rect.left+Box.WIDTH, rect.top)
            ]
            pygame.draw.polygon(surface, color, tab_polygon)
            if cat in DataFiles.sprites["user_interface"]:
                icon = DataFiles.sprites["user_interface"][cat]
                icon_rect = icon.get_rect()
                icon_rect.centerx = rect.left + rect.height/2
                icon_rect.centery = rect.top + rect.height/2
                surface.blit(icon, icon_rect)
            else:
                font.render(surface, cat, rect.center, Color.WHITE, 1, style="center")

        pygame.draw.polygon(surface, Color.DOSSIER_PAGE, self.misaligned_dossier_page)
        pygame.draw.rect(surface, Color.DOSSIER_PAGE, self.dossier_page)

        for entity, rect in zip(entities, self.dossier_icons):
            image = DataFiles.get_entity_sprite(entity)
            image_rect = image.get_rect()
            image_rect.center = rect.center
            surface.blit(image, image_rect)
            pygame.draw.rect(surface, Color.BLACK, rect, width=Box.OUTLINE_WIDTH)
        
        if self.blueprint_selected_item:
            pygame.draw.polygon(surface, Color.BLUEPRINT_PAGE_BACK, self.misaligned_blueprint_page)
            pygame.draw.rect(surface, Color.BLUEPRINT_PAGE, self.blueprint_page)
            font.render(surface, self.blueprint_selected_item, self.blueprint_name, Color.WHITE, 1, style="center")
            surface.blit(DataFiles.get_entity_sprite(self.blueprint_selected_item), self.blueprint_icon)
            pygame.draw.rect(surface, Color.WHITE, self.blueprint_icon, width=Box.OUTLINE_WIDTH)

            icon_size = 32 # TODO
            left_align = [
                self.blueprint_icons[0].left + Box.PADDING,
                self.blueprint_page.centerx + Box.PADDING
            ]
            y = self.blueprint_icon.bottom + Box.PADDING
            info_index = 0
            for info_key, info_value in info.items():
                if info_value is None:
                    continue

                x = left_align[info_index%2]
                if info_key in DataFiles.sprites["user_interface"]:
                    info_icon = DataFiles.sprites["user_interface"][info_key]
                    info_rect = info_icon.get_rect()
                    info_rect.left = x
                    info_rect.top = y
                    surface.blit(info_icon, info_rect)
                else:
                    info_rect = get_rect(width=icon_size, height=icon_size, left=x, top=y)
                    font.render(
                        surface,
                        str(info_key),
                        info_rect.center,
                        Color.WHITE,
                        1,
                        style="center"
                    )
                font.render(
                    surface,
                    str(info_value),
                    (info_rect.right + Box.PADDING, info_rect.centery),
                    Color.WHITE,
                    1,
                    style="centerleft",
                )
                
                info_index += 1
                if info_index % 2 == 0:
                    y += icon_size

            for (icon_name, icon_text), rect in zip(icons, self.blueprint_icons):
                surface.blit(DataFiles.get_entity_sprite(icon_name), rect)
                pygame.draw.rect(surface, Color.WHITE, rect, width=Box.OUTLINE_WIDTH)
                xy = (rect.centerx, rect.top+0.67*rect.height)
                font.render(surface, icon_text, xy, Color.WHITE, 1, style="center", outline_color=Color.BLACK)

            self.blueprint_confirm_button.draw(surface, font)

    def update_shipyard_overlay(self, events):
        for event in events:
            if event.type == pygame.MOUSEBUTTONUP:
                self.exit_overlay(event)

                shipgirls = [
                    shipgirl for shipgirl, shipgirl_info in DataFiles.shipgirl_data.items()
                    if shipgirl not in DataFiles.save_file["shipgirls"]
                    and shipgirl_info["faction"] in DataFiles.save_file["unlocked_factions"]
                    and shipgirl_info["faction"] == self.shipgirl_filters[self.selected_overlay_filter]
                ]
                self.overlay_mouseup_logic(event, shipgirls, self.shipgirl_filters, True)
                if self.blueprint_confirm_button.click(event.pos):
                    if self.blueprint_confirm_button.text == "research":
                        DataFiles.sfx["frequency"].play()
                    else:
                        DataFiles.sfx["knock"].play()

    def draw_shipyard_overlay(self, surface, font):
        shipgirls = [
            shipgirl for shipgirl, shipgirl_info in DataFiles.shipgirl_data.items()
            if shipgirl not in DataFiles.save_file["shipgirls"]
            and shipgirl_info["faction"] in DataFiles.save_file["unlocked_factions"]
            and shipgirl_info["faction"] == self.shipgirl_filters[self.selected_overlay_filter]
        ]
        if self.blueprint_selected_item:
            selected_entity_info = DataFiles.shipgirl_data.get(self.blueprint_selected_item, {})
            hull_type = selected_entity_info["hull_type"]
            unique_item = selected_entity_info["unique_item"]
            inventory = DataFiles.save_file["inventory"]
            specialized_wisdom_cubes = DataFiles.save_file["specialized_wisdom_cubes"]
            wisdom_cube_count = 1 if self.blueprint_selected_item in specialized_wisdom_cubes else inventory.get("wisdom_cube", 0)
            research_reqs = [
                (f"{hull_type}_blueprint", inventory.get(f"{hull_type}_blueprint", 0)),
                ("wisdom_cube", wisdom_cube_count),
                (unique_item, inventory.get(unique_item, 0))
            ]
            research_icons = [
                (research_req, f"{count}/1")
                for research_req, count in research_reqs
            ]
            hull_type = selected_entity_info.get("hull_type")
            selected_entity_stats = DataFiles.stats_data[hull_type]
            research_shipgirl_exp = specialized_wisdom_cubes.get(self.blueprint_selected_item, 0)
            shipgirl_stats = {
                "hull_type": hull_type,
                "max_hp": Stats.stat(research_shipgirl_exp, *selected_entity_stats["max_hp"]),
                "evasion": Stats.stat(research_shipgirl_exp, *selected_entity_stats["evasion"]),
                "firepower": Stats.stat(research_shipgirl_exp, *selected_entity_stats["firepower"]),
                "reload": Stats.stat(research_shipgirl_exp, *selected_entity_stats["reload"]),
                "EXP": research_shipgirl_exp
            }
        else:
            research_icons = []
            shipgirl_stats = {}
        self.draw_dual_panel_overlay(
            surface, font,
            shipgirls,
            self.shipgirl_filters,
            shipgirl_stats,
            research_icons
        )

    def update_gear_lab_overlay(self, events):
        for event in events:
            if event.type == pygame.MOUSEBUTTONUP:
                self.exit_overlay(event)

                if self.selected_overlay_filter == len(self.dossier_tabs) - 1:
                    equipment = [
                        equip for equip, equip_data in DataFiles.equipment_data.items()
                        if equip_data["type"] == "aux"
                    ]
                else:
                    equipment = [
                        equip for equip, equip_data in DataFiles.equipment_data.items()
                        if equip_data["type"] == "weapon"
                        and equip_data["equippable_by"] == self.equipment_filters[self.selected_overlay_filter]
                    ]
                self.overlay_mouseup_logic(event, equipment, self.equipment_filters, True)
                if self.blueprint_confirm_button.click(event.pos):
                    DataFiles.sfx["knock"].play()

    def draw_gear_lab_overlay(self, surface, font):
        if self.selected_overlay_filter == len(self.dossier_tabs) - 1:
            equipment = [
                equip for equip, equip_data in DataFiles.equipment_data.items()
                if equip_data["type"] == "aux"
            ]
        else:
            equipment = [
                equip for equip, equip_data in DataFiles.equipment_data.items()
                if equip_data["type"] == "weapon"
                and equip_data["equippable_by"] == self.equipment_filters[self.selected_overlay_filter]
            ]
        if self.blueprint_selected_item:
            selected_entity_info = DataFiles.equipment_data.get(self.blueprint_selected_item)
            crafting_reqs = selected_entity_info.get("craft_reqs")
            inventory = DataFiles.save_file["inventory"]
            crafting_icons = [
                (material, f"{inventory.get(material,0)}/{req}")
                for material, req in crafting_reqs.items()
            ]
            equip_stats = {
                "hull_type": selected_entity_info.get("equippable_by"),
                "max_hp": selected_entity_info.get("max_hp", 0),
                "evasion": selected_entity_info.get("evasion", 0),
                "firepower": selected_entity_info.get("firepower", 0),
                "reload": selected_entity_info.get("reload", 0),
                "shell_type": selected_entity_info.get("shell_type"),
            }
        else:
            crafting_icons = []
            equip_stats = {}
        self.draw_dual_panel_overlay(
            surface, font,
            equipment,
            self.equipment_filters,
            equip_stats,
            crafting_icons
        )

    def update_intel_center_overlay(self, events):
        for event in events:
            if event.type == pygame.MOUSEBUTTONUP:
                if self.blueprint_selected_item is not None:
                    self.visited_intel_center = True

                self.exit_overlay(event)
                encountered_sirens = [
                    siren for siren in self.encountered_sirens
                    if DataFiles.siren_data[siren]["hull_type"] == self.siren_filters[self.selected_overlay_filter]
                ]
                self.overlay_mouseup_logic(event, encountered_sirens, self.siren_filters, False)

    def draw_intel_center_overlay(self, surface, font):
        encountered_sirens = [
            siren for siren in self.encountered_sirens
            if DataFiles.siren_data[siren]["hull_type"] == self.siren_filters[self.selected_overlay_filter]
        ]
        if self.blueprint_selected_item:
            selected_entity_info = DataFiles.siren_data.get(self.blueprint_selected_item)
            drop_rates = selected_entity_info["drops"]
            drop_icons = [
                (drop, str(drop_rate))
                for drop, drop_rate in drop_rates.items()
            ]
            siren_stats = {
                "hull_type": selected_entity_info.get("hull_type"),
                "max_hp": selected_entity_info["max_hp"][0],
                "evasion": selected_entity_info["evasion"][0],
                "firepower": selected_entity_info["firepower"][0],
                "reload": selected_entity_info["reload"][0],
                "target_pref": selected_entity_info["target_pref"],
                "EXP": selected_entity_info["reward_exp"],
            }
        else:
            drop_icons = []
            siren_stats = {}
        self.draw_dual_panel_overlay(
            surface, font,
            encountered_sirens,
            self.siren_filters,
            siren_stats,
            drop_icons
        )

    def update_decoration_store_overlay(self, events):
        for event in events:
            if event.type == pygame.MOUSEBUTTONUP:
                self.exit_overlay(event)

                num_items_in_row = (self.store_overlay.width - Box.PADDING) // (Box.WIDTH+Box.PADDING)
                padding = (self.store_overlay.width - 2*Box.PADDING - num_items_in_row*Box.WIDTH) / (num_items_in_row-1)
                for i, item in enumerate(DataFiles.decoration_store):
                    left = self.store_overlay.left + Box.PADDING + (i%num_items_in_row)*(Box.WIDTH + padding)
                    top = self.store_overlay.top + Box.PADDING + (i//num_items_in_row)*(Box.HEIGHT+padding)
                    rect = get_rect(width=Box.WIDTH, height=Box.HEIGHT, left=left, top=top)
                    if rect.collidepoint(event.pos):
                        DataFiles.sfx["click"].play()
                        self.store_selected_item = item
                        self.store_confirm_button.active = DataFiles.save_file["inventory"].get("decoration_coin", 0) > 0

                self.store_confirm_button.click(event.pos)

    def draw_decoration_store_overlay(self, surface, font):
        pygame.draw.rect(surface, Color.CARGO_BOX_BACK, self.store_overlay)

        num_items_in_row = (self.store_overlay.width - Box.PADDING) // (Box.WIDTH+Box.PADDING)
        padding = (self.store_overlay.width - 2*Box.PADDING - num_items_in_row*Box.WIDTH) / (num_items_in_row-1)
        for i, item in enumerate(DataFiles.decoration_store):
            left = self.store_overlay.left + Box.PADDING + (i%num_items_in_row)*(Box.WIDTH + padding)
            top = self.store_overlay.top + Box.PADDING + (i//num_items_in_row)*(Box.HEIGHT+padding)
            rect = get_rect(width=Box.WIDTH, height=Box.HEIGHT, left=left, top=top)
            pygame.draw.rect(surface, Color.CARGO_BOX, rect)
            surface.blit(DataFiles.get_entity_sprite(item), rect)
            if self.store_selected_item == item:
                pygame.draw.rect(surface, Color.WHITE, rect, width=Box.OUTLINE_WIDTH)
        
        if self.store_selected_item is not None:
            pygame.draw.rect(surface, Color.CARGO_BOX_BACK, self.store_checkout_overlay)
            font.render(
                surface,
                self.store_selected_item,
                (self.store_checkout_overlay.centerx, self.store_checkout_overlay.top + Box.PADDING + font.font_height/2),
                Color.WHITE,
                1,
                style="center"
            )
            rect = get_rect(
                width=Box.WIDTH, height=Box.HEIGHT,
                centerx=self.store_checkout_overlay.centerx,
                top=self.store_checkout_overlay.top + 2*Box.PADDING + font.font_height
            )
            pygame.draw.rect(surface, Color.CARGO_BOX, rect)
            surface.blit(DataFiles.get_entity_sprite(self.store_selected_item), rect)

            rect = get_rect(
                width=Box.WIDTH, height=Box.HEIGHT,
                centerx=self.store_checkout_overlay.centerx,
                bottom=self.store_confirm_button.rect.top - Box.PADDING
            )
            pygame.draw.rect(surface, Color.CARGO_BOX, rect)
            surface.blit(DataFiles.get_entity_sprite("decoration_coin"), rect)
            num_coins = DataFiles.save_file["inventory"]["decoration_coin"]
            font.render(surface, str(num_coins),rect.center,Color.WHITE,1,style="center",outline_color=Color.BLACK)

            self.store_confirm_button.draw(surface, font)

    def rotate_decoration_direction(self):
        self.decoration_direction_index = (self.decoration_direction_index + 1) % len(self.DECORATION_DIRECTIONS)

    def release_shipgirl_from_interaction(self, shipgirl):
        shipgirl.interacting_decoration = None
        shipgirl.wander_target = pygame.Vector2(
            screen_x(random.random()),
            screen_y(random.random())
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
                    and not self.open_close_decoration_menu_button.rect.collidepoint(event.pos)
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
                        self.start_camera_drag(event.pos)
                        continue
            if event.type == pygame.MOUSEMOTION:
                if self.update_camera_drag(event):
                    continue

                self.open_close_decoration_menu_button.hover(event.pos)

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

                if self.stop_camera_drag():
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

                if self.open_close_decoration_menu_button.click(event.pos):
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
        if self.decorating_port_menu:
            self.update_decorate_port_menu_overlay(events)
        elif self.current_overlay == self.NO_OVERLAY:
            self.update_no_overlay(events)
        elif self.current_overlay == self.DEPOT:
            for event in events:
                if event.type == pygame.MOUSEBUTTONUP:
                    self.exit_overlay(event)
                    self.visited_inventory = True
        elif self.current_overlay == self.SHIPYARD:
            self.update_shipyard_overlay(events)
        elif self.current_overlay == self.GEAR_LAB:
            self.update_gear_lab_overlay(events)
        elif self.current_overlay == self.INTEL_CENTER:
            self.update_intel_center_overlay(events)
        elif self.current_overlay == self.DECORATION_STORE:
            self.update_decoration_store_overlay(events)

        for shipgirl in self.menu_manager.available_shipgirls:
            shipgirl.update(dt)
            shipgirl.animate(dt)

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
            direction = direction = self.DECORATION_DIRECTIONS[self.decoration_direction_index]
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

        self.open_close_decoration_menu_button.draw(surface, font)
        if self.decorating_port_menu:
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
            return
        
        self.open_select_sortie_menu_button.draw(surface, font)
        self.open_depot_overlay_button.draw(surface, font)
        self.open_shipyard_overlay_button.draw(surface, font)
        self.open_gear_lab_overlay_button.draw(surface, font)
        self.open_intel_center_overlay_button.draw(surface, font)
        self.open_decoration_store_overlay_button.draw(surface, font)

        if self.current_overlay == self.DEPOT:
            self.draw_inventory_overlay(surface, font)
        if self.current_overlay == self.SHIPYARD: 
            self.draw_shipyard_overlay(surface, font)
        elif self.current_overlay == self.GEAR_LAB:
            self.draw_gear_lab_overlay(surface, font)
        elif self.current_overlay == self.INTEL_CENTER:
            self.draw_intel_center_overlay(surface, font)
        elif self.current_overlay == self.DECORATION_STORE:
            self.draw_decoration_store_overlay(surface, font)
    
        self.menu_manager.quest_manager.draw(surface, font)
        for choose_faction_button in self.choose_faction_buttons:
            choose_faction_button.draw(surface, font)
