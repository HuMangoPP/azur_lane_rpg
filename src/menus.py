import math
import random
import pygame

from engine.util import get_rect, get_vec, pixel_to_hex, hex_to_pixel, get_cluster_edges
from engine.button import Button

from src.constants import DataFiles, Color, Equipment, Box, screen_x, screen_y
from src.shipgirls import Shipgirl, available_shipgirls, available_shipgirl_rects, player_fleet, siren_fleet

from live2d.live2d import Live2D

EDGE_PADDING = 20
LEFT_OF_SCREEN = screen_x(0) + EDGE_PADDING
RIGHT_OF_SCREEN = screen_x(1) - EDGE_PADDING
TOP_OF_SCREEN = screen_y(0) + EDGE_PADDING
BOTTOM_OF_SCREEN = screen_y(1) - EDGE_PADDING

class Buildings:
    DEPOT = "depot"
    SHIPYARD = "shipyard"
    GEAR_LAB = "gear_lab"
    INTEL_CENTER = "intel_center"

class Building:
    def __init__(self, building_type, pos):
        self.building_type = building_type
        self.rect = get_rect(width=Box.WIDTH, height=Box.HEIGHT, centerx=pos.x, centery=pos.y)
        self.sprite = None

    def draw(self, surface, font):
        if self.sprite is not None:
            pass
        else:
            pygame.draw.rect(surface, Color.WHITE, self.rect, width=Box.OUTLINE_WIDTH)
            font.render(surface, str(self.building_type), self.rect.center, Color.WHITE, 1, style="center", outline_color=Color.BLACK)

class TutorialTask:
    def __init__(self, tutorial_input, tutorial_draw):
        self.tutorial_input = tutorial_input
        self.tutorial_draw = tutorial_draw

    def check_completion(self, event):
        return self.tutorial_input(event)

class Tutorial:
    def __init__(self, tasks, on_complete):
        self.tasks = tasks
        self.task_index = 0
        self.completed = False
        self.on_complete = on_complete

    @property
    def current_task(self):
        if self.task_index < len(self.tasks):
            return self.tasks[self.task_index]
        return None

    def check_completion(self, event):
        if self.current_task.check_completion(event):
            self.task_index += 1
            if self.task_index == len(self.tasks):
                self.completed = True
            return True
        return False

    def draw(self, surface, font):
        current_task = self.current_task
        if current_task is not None:
            current_task.tutorial_draw(surface, font)

mouse_start_drag = None

class PortMenu:
    NO_OVERLAY = -1
    DEPOT = 0
    SHIPYARD = 1
    GEAR_LAB = 2
    INTEL_CENTER = 3

    def __init__(self):
        self.current_overlay = self.NO_OVERLAY

        self.buildings = { # TODO magic numbers
            self.DEPOT: Building(Buildings.DEPOT, pygame.Vector2(50, 50)),
            self.SHIPYARD: Building(Buildings.SHIPYARD, pygame.Vector2(150, 50)),
            self.GEAR_LAB: Building(Buildings.GEAR_LAB, pygame.Vector2(250, 50)),
            self.INTEL_CENTER: Building(Buildings.INTEL_CENTER, pygame.Vector2(350, 50)),
        }

        self.overlay_bg = get_rect(width=600, height=400, centerx=screen_x(0.5), centery=screen_y(0.5))
        self.overlay_right_panel = get_rect(
            width=3*Box.WIDTH + 4*Box.PADDING,
            height=self.overlay_bg.height-2*Box.PADDING,
            right=self.overlay_bg.right-Box.PADDING,
            top=self.overlay_bg.top+Box.PADDING
        )
        self.overlay_left_panel = get_rect(
            width=self.overlay_bg.width-self.overlay_right_panel.width-3*Box.PADDING,
            height=self.overlay_bg.height-2*Box.PADDING-Box.HEIGHT,
            left=self.overlay_bg.left+Box.PADDING,
            bottom=self.overlay_bg.bottom-Box.PADDING
        )

        self.overlay_filter_rects = [
            get_rect(
                width=Box.WIDTH, height=Box.HEIGHT,
                left=self.overlay_left_panel.left+i*(Box.WIDTH+Box.PADDING),
                bottom=self.overlay_left_panel.top
            ) for i in range(5)
        ]
        self.selected_overlay_filter = None
        self.shipgirl_filters = ["USS", "HMS", "IJN", "KMS"]
        self.equipment_filters = ["AUX", "DD", "CL", "CA", "BB"]
        self.siren_filters = ["DD", "CA", "BB"]

        num_icons_per_row = (self.overlay_left_panel.width-Box.PADDING) // (Box.WIDTH+Box.PADDING)
        icon_padding = (self.overlay_left_panel.width - 2*Box.PADDING - num_icons_per_row*Box.WIDTH) / (num_icons_per_row-1)
        self.overlay_left_icons = [
            get_rect(
                width=Box.WIDTH, height=Box.HEIGHT,
                left=self.overlay_left_panel.left+Box.PADDING+(i%num_icons_per_row)*(Box.WIDTH+icon_padding),
                top=self.overlay_left_panel.top+Box.PADDING+(i//num_icons_per_row)*(Box.HEIGHT+icon_padding)
            ) for i in range(18)
        ]

        self.overlay_right_name = pygame.Vector2(
            self.overlay_right_panel.centerx,
            self.overlay_right_panel.top+Box.PADDING
        )
        self.overlay_right_icon = get_rect(
            width=Box.WIDTH, height=Box.HEIGHT,
            centerx=self.overlay_right_panel.centerx,
            top=self.overlay_right_name.y+Box.PADDING
        )
        num_icons_per_row = 3
        self.overlay_ingredient_icons = [
            get_rect(
                width=Box.WIDTH, height=Box.HEIGHT,
                left=self.overlay_right_panel.left+Box.PADDING+i*(Box.WIDTH+Box.PADDING),
                bottom=self.overlay_right_panel.bottom-2*Box.PADDING-Box.HEIGHT
            ) for i in range(3)
        ]

        def overlay_confirm():
            if self.current_overlay == self.SHIPYARD:
                selected_entity_info = DataFiles.shipgirl_data[self.overlay_selected_entity]
                hull_type = selected_entity_info["hull_type"]
                unique_item = selected_entity_info["unique_item"]
                selected_entity_reqs = {
                    f"{hull_type}_blueprint": 1,
                    "wisdom_cube": 1,
                    unique_item: 1
                }
                if all(DataFiles.save_file["inventory"].get(ingredient, 0) >= req for ingredient, req in selected_entity_reqs.items()):
                    DataFiles.save_file["shipgirls"][self.overlay_selected_entity] = {
                        "equipment": [None, None, None],
                        "exp": 0
                    }
                    shipgirl = Shipgirl(self.overlay_selected_entity, True)
                    available_shipgirls.append(shipgirl)
                    for ingredient, req in selected_entity_reqs.items():
                        DataFiles.save_file["inventory"][ingredient] -= req
                    DataFiles.save_file["research_target"] = None
                else:
                    DataFiles.save_file["research_target"] = self.overlay_selected_entity
            elif self.current_overlay == self.GEAR_LAB:
                selected_entity_reqs = DataFiles.equipment_data[self.overlay_selected_entity]["craft_reqs"]
                if all(DataFiles.save_file["inventory"].get(ingredient, 0) >= req for ingredient, req in selected_entity_reqs.items()):
                    DataFiles.save_file["equipment"][self.overlay_selected_entity] = DataFiles.save_file["equipment"].get(self.overlay_selected_entity, 0) + 1
                    for ingredient, req in selected_entity_reqs.items():
                        DataFiles.save_file["inventory"][ingredient] -= req

        self.overlay_confirm_button = Button(
            rect=get_rect(
                width=2*Box.WIDTH, height=Box.HEIGHT,
                centerx=self.overlay_right_panel.centerx,
                bottom=self.overlay_right_panel.bottom-Box.PADDING
            ),
            color=Color.BLUE_GREY,
            text="confirm",
            text_color=Color.WHITE,
            callback=overlay_confirm,
            active=False
        )
        self.overlay_selected_entity = None

        def open_select_sortie_menu():
            Menus.current_menu = Menus.SORTIE_SELECTION

        self.open_select_sortie_menu_button = Button(
            rect=get_rect(width=2*Box.WIDTH, height=Box.HEIGHT, centerx=screen_x(0.5), bottom=BOTTOM_OF_SCREEN),
            color=Color.BLUE_GREY,
            text="sortie",
            text_color=Color.WHITE,
            callback=open_select_sortie_menu
        )

        self.update_encountered_sirens()
    
    def update_encountered_sirens(self):
        self.encountered_sirens = set()
        for i in range(DataFiles.save_file["sortie_progress"]):
            encounters = DataFiles.sortie_data[i]["encounters"]
            for encounter in encounters:
                self.encountered_sirens = self.encountered_sirens.union(encounter["front"] + encounter["back"])
        self.encountered_sirens = list(self.encountered_sirens)

    def update_no_overlay(self, events):
        for event in events:
            if event.type == pygame.MOUSEBUTTONUP:
                for shipgirl in available_shipgirls:
                    if shipgirl.rect.collidepoint(event.pos):
                        Menus.EQUIPMENT.selected_shipgirl = shipgirl
                        Menus.current_menu = Menus.EQUIPMENT
                
                for overlay_enum, building in self.buildings.items():
                    if building.rect.collidepoint(event.pos):
                        self.current_overlay = overlay_enum

                        if overlay_enum == self.SHIPYARD and DataFiles.save_file["research_target"] is not None:
                            self.overlay_confirm_button.active = True
                            self.overlay_selected_entity = DataFiles.save_file["research_target"]
                
                self.open_select_sortie_menu_button.click(event.pos)

    def draw_inventory_overlay(self, surface, font):
        pygame.draw.rect(surface, Color.DARK_BLUE, self.overlay_bg)

        num_items_in_row = (self.overlay_bg.width - 2*Box.PADDING) // Box.WIDTH
        padding = (self.overlay_bg.width - 2*Box.PADDING - num_items_in_row*Box.WIDTH) / (num_items_in_row-1)
        item_index = 0
        for item, count in DataFiles.save_file["inventory"].items():
            if count <= 0:
                continue
            left = self.overlay_bg.left + Box.PADDING + (item_index%num_items_in_row)*(Box.WIDTH + padding)
            top = self.overlay_bg.top + Box.PADDING + (item_index//num_items_in_row)*(Box.HEIGHT+padding)
            rect = get_rect(width=Box.WIDTH, height=Box.HEIGHT, left=left, top=top)
            pygame.draw.rect(surface, Color.WHITE, rect, width=Box.OUTLINE_WIDTH)
            if item in DataFiles.sprites:
                surface.blit(DataFiles.sprites[item], rect)
                font.render(surface, str(count), rect.center, Color.WHITE, 1, style="center", outline_color=Color.BLACK)
            else:
                font.render(surface, f"{item} ({count})", rect.center, Color.WHITE, 1, style="center", outline_color=Color.BLACK)
            item_index += 1

    def exit_overlay(self, mouseup_event):
        if not self.overlay_bg.collidepoint(mouseup_event.pos):
            self.current_overlay = self.NO_OVERLAY
            self.overlay_confirm_button.active = False
            self.selected_overlay_filter = None
            self.overlay_selected_entity = None

    def overlay_mouseup_logic(self, mouseup_event, entities, entity_filters, activate_confirm_button):
        for entity, rect in zip(entities, self.overlay_left_icons):
            if rect.collidepoint(mouseup_event.pos):
                self.overlay_selected_entity = entity
                self.overlay_confirm_button.active = activate_confirm_button
        
        for i, (cat, rect) in enumerate(zip(entity_filters, self.overlay_filter_rects)):
            if rect.collidepoint(mouseup_event.pos):
                if self.selected_overlay_filter == i:
                    self.selected_overlay_filter = None
                else:
                    self.selected_overlay_filter = i

    def draw_dual_panel_overlay(self, surface, font, entities, entity_filters, stats, reqs):
        pygame.draw.rect(surface, Color.BLUE_GREY, self.overlay_bg)
        pygame.draw.rect(surface, Color.DARK_BLUE, self.overlay_left_panel)
        pygame.draw.rect(surface, Color.DARK_BLUE, self.overlay_right_panel)

        for i, (cat, rect) in enumerate(zip(entity_filters, self.overlay_filter_rects)):
            if self.selected_overlay_filter == i:
                pygame.draw.rect(surface, Color.DARK_BLUE, rect)
            else:
                pygame.draw.rect(surface, Color.BLUE, rect)
            font.render(surface, cat, rect.center, Color.WHITE, 1, style="center", outline_color=Color.BLACK)

        for entity, rect in zip(entities, self.overlay_left_icons):
            pygame.draw.rect(surface, Color.WHITE, rect, width=Box.OUTLINE_WIDTH)
            if entity in DataFiles.sprites:
                image = DataFiles.sprites[entity]
                image_rect = image.get_rect()
                image_rect.center = rect.center
                surface.blit(image, image_rect)
            else:
                font.render(surface, entity, rect.center, Color.WHITE, 1, style="center", outline_color=Color.BLACK)
        
        if self.overlay_selected_entity:
            font.render(surface, self.overlay_selected_entity, self.overlay_right_name, Color.WHITE, 1, style="center", outline_color=Color.BLACK)
            if self.overlay_selected_entity in DataFiles.sprites:
                surface.blit(DataFiles.sprites[self.overlay_selected_entity], self.overlay_right_icon)
            pygame.draw.rect(surface, Color.WHITE, self.overlay_right_icon, width=Box.OUTLINE_WIDTH)

            x = self.overlay_right_panel.left + Box.PADDING
            y = self.overlay_right_icon.bottom + Box.PADDING
            for info_key, info_value in stats.items():
                if info_value is None:
                    continue
                xy = (x, y)
                info_name = Stats.STAT_NAMES.get(info_key, info_key)
                font.render(surface, f"{info_name}: {info_value}", xy, Color.WHITE, 1, style="topleft", outline_color=Color.BLACK)
                y += Box.PADDING # TODO

            for (ingredient, req), rect in zip(reqs.items(), self.overlay_ingredient_icons):
                if ingredient in DataFiles.sprites:
                    surface.blit(DataFiles.sprites[ingredient], rect)
                    pygame.draw.rect(surface, Color.WHITE, rect, width=Box.OUTLINE_WIDTH)
                else:
                    pygame.draw.rect(surface, Color.WHITE, rect, width=Box.OUTLINE_WIDTH)
                    xy = (rect.centerx, rect.top+0.33*rect.height) # TODO
                    font.render(surface, ingredient, xy, Color.WHITE, 1, style="center", outline_color=Color.BLACK)
                xy = (rect.centerx, rect.top+0.67*rect.height)
                amt = DataFiles.save_file["inventory"].get(ingredient, 0)
                font.render(surface, f"{amt}-{req}", xy, Color.WHITE, 1, style="center", outline_color=Color.BLACK)

    def update_shipyard_overlay(self, events):
        for event in events:
            if event.type == pygame.MOUSEBUTTONUP:
                self.exit_overlay(event)

                if self.selected_overlay_filter is None:
                    shipgirls = [
                        shipgirl for shipgirl in DataFiles.shipgirl_data
                        if shipgirl not in DataFiles.save_file["shipgirls"]
                    ]
                else:
                    shipgirls = [
                        shipgirl for shipgirl, shipgirl_info in DataFiles.shipgirl_data.items()
                        if shipgirl not in DataFiles.save_file["shipgirls"]
                        and shipgirl_info["faction"] == self.shipgirl_filters[self.selected_overlay_filter]
                    ]
                self.overlay_mouseup_logic(event, shipgirls, self.shipgirl_filters, True)
                self.overlay_confirm_button.click(event.pos)

    def draw_shipyard_overlay(self, surface, font):
        if self.selected_overlay_filter is None:
            shipgirls = [
                shipgirl for shipgirl in DataFiles.shipgirl_data
                if shipgirl not in DataFiles.save_file["shipgirls"]
            ]
        else:
            shipgirls = [
                shipgirl for shipgirl, shipgirl_info in DataFiles.shipgirl_data.items()
                if shipgirl not in DataFiles.save_file["shipgirls"]
                and shipgirl_info["faction"] == self.shipgirl_filters[self.selected_overlay_filter]
            ]
        if self.overlay_selected_entity:
            selected_entity_info = DataFiles.shipgirl_data.get(self.overlay_selected_entity, {})
            hull_type = selected_entity_info["hull_type"]
            unique_item = selected_entity_info["unique_item"]
            research_reqs = {
                f"{hull_type}_blueprint": 1,
                "wisdom_cube": 1,
                unique_item: 1
            }
            shipgirl_stats = {
                "HULL": selected_entity_info.get("hull_type"),
                "HP": selected_entity_info.get("max_hp"),
                "EVA": selected_entity_info.get("evasion"),
                "FP": selected_entity_info.get("firepower"),
                "RLD": selected_entity_info.get("reload"),
            }
        else:
            research_reqs = {}
            shipgirl_stats = {}
        self.draw_dual_panel_overlay(surface, font, shipgirls, self.shipgirl_filters, shipgirl_stats, research_reqs)

    def update_gear_lab_overlay(self, events):
        for event in events:
            if event.type == pygame.MOUSEBUTTONUP:
                self.exit_overlay(event)

                if self.selected_overlay_filter is None:
                    equipment = [equip for equip in DataFiles.equipment_data]
                elif self.selected_overlay_filter == 4: # TODO
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
                self.overlay_confirm_button.click(event.pos)

    def draw_gear_lab_overlay(self, surface, font):
        if self.selected_overlay_filter is None:
            equipment = [equip for equip in DataFiles.equipment_data]
        elif self.selected_overlay_filter == 0: # TODO
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
        if self.overlay_selected_entity:
            selected_entity_info = DataFiles.equipment_data.get(self.overlay_selected_entity)
            crafting_reqs = selected_entity_info.get("craft_reqs")
            equip_stats = {
                "HULL": selected_entity_info.get("equippable_by"),
                "HP": selected_entity_info.get("max_hp"),
                "EVA": selected_entity_info.get("evasion"),
                "FP": selected_entity_info.get("firepower"),
                "RLD": selected_entity_info.get("reload"),
                "SHELL": selected_entity_info.get("shell_type"),
            }
        else:
            crafting_reqs = {}
            equip_stats = {}
        self.draw_dual_panel_overlay(surface, font, equipment, self.equipment_filters, equip_stats, crafting_reqs)

    def update_intel_center_overlay(self, events):
        for event in events:
            if event.type == pygame.MOUSEBUTTONUP:
                self.exit_overlay(event)

                if self.selected_overlay_filter is None:
                    encountered_sirens = self.encountered_sirens
                else:
                    encountered_sirens = [
                        siren for siren in self.encountered_sirens
                        if self.siren_filters[self.selected_overlay_filter] == siren # TODO
                    ]
                self.overlay_mouseup_logic(event, encountered_sirens, self.siren_filters, True)

    def draw_intel_center_overlay(self, surface, font):
        if self.selected_overlay_filter is None:
            encountered_sirens = self.encountered_sirens
        else:
            encountered_sirens = [
                siren for siren in self.encountered_sirens
                if self.siren_filters[self.selected_overlay_filter] == siren # TODO
            ]
        if self.overlay_selected_entity:
            selected_entity_info = DataFiles.siren_data.get(self.overlay_selected_entity)
            siren_stats = {
                "HULL": selected_entity_info.get("hull_type"),
                "HP": selected_entity_info.get("max_hp"),
                "EVA": selected_entity_info.get("evasion"),
                "FP": selected_entity_info.get("firepower"),
                "RLD": selected_entity_info.get("reload"),
                "TARGET": selected_entity_info.get("target_pref"),
                "EXP": selected_entity_info.get("exp"),
            }
        else:
            siren_stats = {}
        self.draw_dual_panel_overlay(surface, font, encountered_sirens, self.siren_filters, siren_stats, {})

    def update(self, dt, events):
        if self.current_overlay == self.NO_OVERLAY:
            self.update_no_overlay(events)
        elif self.current_overlay == self.DEPOT:
            for event in events:
                if event.type == pygame.MOUSEBUTTONUP:
                    self.exit_overlay(event)
        elif self.current_overlay == self.SHIPYARD:
            self.update_shipyard_overlay(events)
        elif self.current_overlay == self.GEAR_LAB:
            self.update_gear_lab_overlay(events)
        elif self.current_overlay == self.INTEL_CENTER:
            self.update_intel_center_overlay(events)
        
        for shipgirl in available_shipgirls:
            shipgirl.update(dt)

    def draw(self, surface, font):
        for shipgirl in available_shipgirls:
            shipgirl.draw(surface, font)
        self.open_select_sortie_menu_button.draw(surface, font)

        for _, building in self.buildings.items():
            building.draw(surface, font)

        if self.current_overlay != self.NO_OVERLAY:
            if self.current_overlay == self.DEPOT:
                self.draw_inventory_overlay(surface, font)
            if self.current_overlay == self.SHIPYARD: 
                self.draw_shipyard_overlay(surface, font)
            elif self.current_overlay == self.GEAR_LAB:
                self.draw_gear_lab_overlay(surface, font)
            elif self.current_overlay == self.INTEL_CENTER:
                self.draw_intel_center_overlay(surface, font)

            self.overlay_confirm_button.draw(surface, font)

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

    def select(self, mouse_pos):
        if not self.unlocked:
            return

        mouse_x, mouse_y = mouse_pos
        hx, hy = pixel_to_hex(mouse_x - self.CENTER.x, mouse_y - self.CENTER.y, self.SIZE)
        if (hx, hy) not in self.hexes:
            return
            
        Menus.current_menu = Menus.FLEET_SELECTION
        Menus.ENCOUNTER.current_sortie = self.index
        Menus.ENCOUNTER.current_encounter = 0
        player_fleet.clear_fleet()
        siren_fleet.clear_fleet()

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
    def __init__(self):
        self.sortie_nodes = [
            SortieNode(sortie_index, sortie_info["coordinates"])
            for sortie_index, sortie_info in enumerate(DataFiles.sortie_data)
        ]

        def exit_sortie_selection_menu():
            Menus.current_menu = Menus.PORT

        self.exit_sortie_selection_menu_button = Button(
            rect=get_rect(width=2*Box.WIDTH, height=Box.HEIGHT, right=RIGHT_OF_SCREEN, top=TOP_OF_SCREEN),
            color=Color.BLUE_GREY,
            text="go back",
            text_color=Color.WHITE,
            callback=exit_sortie_selection_menu
        )

        # TODO i want the overall style of the sortie selection menu
        # to feel like the OpSi menu where there are different zones that
        # are controlled / not controlled by the player and the player can
        # sortie into uncontrolled zone and by doing so they beat the level
        # i think the best way to do this in a structured way would be to use
        # some sort of grid-like system

    def update(self, dt, events):
        for event in events:
            if event.type == pygame.MOUSEBUTTONUP:
                self.exit_sortie_selection_menu_button.click(event.pos)

                for sortie_node in self.sortie_nodes:
                    sortie_node.select(event.pos)
            if event.type == pygame.MOUSEMOTION:
                for sortie_node in self.sortie_nodes:
                    sortie_node.hover(event.pos)

    def draw(self, surface, font):
        self.exit_sortie_selection_menu_button.draw(surface, font)

        for sortie_node in self.sortie_nodes:
            sortie_node.draw(surface, font)

class FleetSelectionMenu:
    def __init__(self):
        self.selected_shipgirl = None
        def start_sortie():
            if all(shipgirl is None for shipgirl in player_fleet.shipgirls):
                return
            Menus.current_menu = Menus.ENCOUNTER
            
            player_fleet.begin_sortie()
            Menus.ENCOUNTER.begin_sortie()

        self.start_sortie_button = Button(
            rect=get_rect(width=2*Box.WIDTH, height=Box.HEIGHT, centerx=screen_x(0.75), bottom=BOTTOM_OF_SCREEN),
            color=Color.BLUE_GREY,
            text="start",
            text_color=Color.WHITE,
            callback=start_sortie
        )

        def exit_fleet_selection_menu():
            Menus.current_menu = Menus.SORTIE_SELECTION
        
        self.exit_fleet_selection_menu_button = Button(
            rect=get_rect(width=2*Box.WIDTH, height=Box.HEIGHT, right=RIGHT_OF_SCREEN, top=TOP_OF_SCREEN),
            color=Color.BLUE_GREY,
            text="go back",
            text_color=Color.WHITE,
            callback=exit_fleet_selection_menu
        )

        num_fleet_slots = len(player_fleet.shipgirls)
        fleet_slot_offset = (num_fleet_slots-1)/2
        self.fleet_slots = [
            get_rect(
                width=Box.WIDTH, height=Box.HEIGHT,
                centerx=(fleet_slot_offset-slot_index)*(Box.WIDTH+Box.PADDING)+screen_x(0.25),
                centery=screen_y(0.5)
            ) for slot_index in range(num_fleet_slots)
        ]

    def update(self, dt, events):
        global mouse_start_drag

        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN:
                for shipgirl, rect in zip(available_shipgirls, available_shipgirl_rects):
                    if rect.collidepoint(event.pos) and shipgirl.name not in player_fleet.shipgirl_names:
                        mouse_start_drag = event.pos
                        self.selected_shipgirl = shipgirl
                        break
                else:
                    for shipgirl in player_fleet.shipgirls:
                        if shipgirl is not None and shipgirl.rect.collidepoint(event.pos):
                            mouse_start_drag = event.pos
                            self.selected_shipgirl = shipgirl
                            break
                    else:
                        self.selected_shipgirl = None
            if event.type == pygame.MOUSEBUTTONUP:
                mouse_end_drag = event.pos
                if mouse_start_drag is not None and self.selected_shipgirl is not None:
                    for i, slot in enumerate(self.fleet_slots):
                        if slot.collidepoint(mouse_end_drag):
                            for j, shipgirl in enumerate(player_fleet.shipgirls):
                                if self.selected_shipgirl == shipgirl:
                                    player_fleet.shipgirls[j] = player_fleet.shipgirls[i]
                            player_fleet.shipgirls[i] = self.selected_shipgirl
                            self.selected_shipgirl.rect.center = pygame.Vector2(slot.center)
                            if self.selected_shipgirl.sprite is not None:
                                self.selected_shipgirl.sprite.set_animation(Live2D.IDLE_ANIMATION)
                                self.selected_shipgirl.facing_left = False
                            self.selected_shipgirl = None
                mouse_start_drag = None
                self.start_sortie_button.click(event.pos)
                self.exit_fleet_selection_menu_button.click(event.pos)
        
        for shipgirl in player_fleet.shipgirls:
            if shipgirl is not None:
                shipgirl.animate(dt)

    def draw(self, surface, font):
        player_fleet.draw(surface, font)
        self.start_sortie_button.draw(surface, font)
        self.exit_fleet_selection_menu_button.draw(surface, font)

        for shipgirl, rect in zip(available_shipgirls, available_shipgirl_rects):
            pygame.draw.rect(surface, Color.WHITE, rect, width=Box.OUTLINE_WIDTH)
            if shipgirl.name in DataFiles.sprites:
                portrait = DataFiles.sprites[shipgirl.name]
                portrait_rect = portrait.get_rect()
                portrait_rect.center = rect.center
                surface.blit(portrait, portrait_rect)
            else:
                font.render(surface, shipgirl.name, rect.center, Color.WHITE, 1, style="center", outline_color=Color.BLACK)

        for slot, shipgirl in zip(self.fleet_slots, player_fleet.shipgirls):
            if shipgirl is None:
                rect = get_rect(width=Box.WIDTH, height=Box.HEIGHT, centerx=slot.centerx, centery=slot.centery)
                pygame.draw.rect(surface, Color.WHITE, rect, width=Box.OUTLINE_WIDTH)
        
        mpos = pygame.mouse.get_pos()
        if mouse_start_drag is not None:
            pygame.draw.line(surface, Color.WHITE, mouse_start_drag, mpos, width=Box.OUTLINE_WIDTH)

class Drop:
    def __init__(self, item, pos, vel):
        self.item = item
        self.pos = pos
        self.vel = vel

    def update(self, dt):
        bottom = screen_y(0.6)
        if self.pos.y < bottom:
            self.pos = self.pos + self.vel * dt
            self.pos.y = min(self.pos.y, bottom)
            self.vel = self.vel + pygame.Vector2(0, 200) * dt
    
    def draw(self, surface, font):
        if self.item in DataFiles.sprites:
            image = DataFiles.sprites[self.item]
            rect = image.get_rect()
            rect.center = self.pos
            surface.blit(image, rect)
        else:
            rect = get_rect(width=Box.WIDTH, height=Box.HEIGHT, centerx=self.pos.x, centery=self.pos.y)
            pygame.draw.rect(surface, Color.WHITE, rect, width=Box.OUTLINE_WIDTH)
            font.render(surface, self.item, rect.center, Color.WHITE, 1, style="center", outline_color=Color.BLACK)

class EncounterMenu:
    def __init__(self):
        self.current_sortie = 0
        self.current_encounter = 0
        self.selected_shipgirl = None

        def next_encounter():
            self.current_encounter += 1
            self.begin_encounter()

            self.next_encounter_button.active = False

        self.next_encounter_button = Button(
            rect=get_rect(width=Box.WIDTH, height=Box.HEIGHT, right=RIGHT_OF_SCREEN, centery=screen_y(0.5)),
            color=Color.BLUE_GREY,
            text="next",
            text_color=Color.WHITE,
            callback=next_encounter,
            active=False
        )

        def return_to_port():
            for drop in self.drops:
                DataFiles.save_file["inventory"][drop.item] = DataFiles.save_file["inventory"].get(drop.item, 0) + 1

            Menus.current_menu = Menus.PORT

            Menus.ENCOUNTER.return_to_port_button.active = False

            sortie_progress = DataFiles.save_file["sortie_progress"]
            tutorial = tutorials.sortie_end_tutorial_triggers.get(sortie_progress)
            if tutorial is not None and not tutorial.completed:
                Menus.tutorial = tutorial

        self.return_to_port_button = Button(
            rect=get_rect(width=Box.WIDTH, height=Box.HEIGHT, right=RIGHT_OF_SCREEN, centery=screen_y(0.5)),
            color=Color.BLUE_GREY,
            text="back to port",
            text_color=Color.WHITE,
            callback=return_to_port,
            active=False
        )

        def retreat():
            Menus.current_menu = Menus.PORT

            player_fleet.end_encounter()        
        
        self.retreat_button = Button(
            rect=get_rect(width=2*Box.WIDTH, height=Box.HEIGHT, right=RIGHT_OF_SCREEN, top=TOP_OF_SCREEN),
            color=Color.BLUE_GREY,
            text="retreat",
            text_color=Color.WHITE,
            callback=retreat
        )

        self.end_sortie_text_pos = pygame.Vector2(screen_x(0.5), screen_y(0.25))
        self.encounter_end_flag = True

        self.drops = []

    def begin_sortie(self):
        self.drops = []
        self.begin_encounter()

    def begin_encounter(self):
        encounter_data = DataFiles.sortie_data[self.current_sortie]["encounters"][self.current_encounter]
        siren_fleet._front = [Shipgirl(siren_name, False) for siren_name in encounter_data["front"]] #
        siren_fleet._back = [Shipgirl(siren_name, False) for siren_name in encounter_data["back"]]
        for siren in siren_fleet.fleet:
            if DataFiles.siren_data[siren.name]["target_pref"] == "front":
                siren.facing_left = True
                siren.battle_component.target = player_fleet.front
        player_fleet.begin_encounter()
        siren_fleet.begin_encounter()

        self.next_encounter_button.active = False
        self.return_to_port_button.active = False
        self.retreat_button.active = True
        self.encounter_end_flag = True

    def update(self, dt, events):
        global mouse_start_drag

        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN:
                for shipgirl in player_fleet.shipgirls:
                    if (
                        shipgirl is not None
                        and shipgirl.battle_component.active
                        and shipgirl.battle_component.attack_timer <= 0
                        and shipgirl.rect.collidepoint(event.pos)
                    ):
                        mouse_start_drag = event.pos
                        self.selected_shipgirl = shipgirl
                        self.selected_shipgirl.battle_component.target = None
            if event.type == pygame.MOUSEBUTTONUP:
                mouse_end_drag = event.pos
                if mouse_start_drag is not None and self.selected_shipgirl is not None:
                    for siren in siren_fleet.fleet:
                        if siren.rect.collidepoint(mouse_end_drag):
                            if self.selected_shipgirl.battle_component.hull_type in ["DD", "CL"]:
                                if siren in siren_fleet.front:
                                    self.selected_shipgirl.battle_component.target = siren
                            else:
                                self.selected_shipgirl.battle_component.target = siren
                            self.selected_shipgirl = None
                mouse_start_drag = None
                self.next_encounter_button.click(event.pos)
                self.return_to_port_button.click(event.pos)
                self.retreat_button.click(event.pos)
        
        player_fleet.update(dt)
        siren_fleet.update(dt)
        for drop in self.drops:
            drop.update(dt)

        if self.encounter_end_flag:
            if not player_fleet.afloat:
                self.encounter_end_flag = False
                player_fleet.end_encounter()
                siren_fleet.end_encounter()
                self.return_to_port_button.active = True
                self.retreat_button.active = False
            if not siren_fleet.afloat:
                self.encounter_end_flag = False
                for siren in siren_fleet.fleet:
                    for shipgirl in player_fleet.shipgirls:
                        if shipgirl is not None:
                            shipgirl.battle_component.exp += siren.battle_component.exp
                    if DataFiles.save_file["research_target"] is not None:
                        DataFiles.save_file["research_progress"] += siren.battle_component.exp
                
                exp_req = 5 # TODO
                if DataFiles.save_file["research_progress"] >= exp_req:
                    if DataFiles.save_file["research_target"] is not None:
                        unique_item = DataFiles.shipgirl_data[DataFiles.save_file["research_target"]]["unique_item"]
                        DataFiles.save_file["inventory"][unique_item] = 1
                        DataFiles.save_file["research_progress"] -= exp_req

                player_fleet.end_encounter()
                siren_fleet.end_encounter()
                num_encounters = len(DataFiles.sortie_data[self.current_sortie]["encounters"])
                if self.current_encounter+1 < num_encounters:
                    self.next_encounter_button.active = True
                    
                    if not tutorials.next_encounter.completed:
                        Menus.tutorial = tutorials.next_encounter
                else:
                    self.return_to_port_button.active = True

                    if not tutorials.return_to_port.completed:
                        Menus.tutorial = tutorials.return_to_port

                    if self.current_sortie == DataFiles.save_file["sortie_progress"]:
                        rewards = DataFiles.sortie_data[self.current_sortie]["rewards"]
                        for reward in rewards:
                            self.drops.append(Drop(
                                reward,
                                pygame.Vector2(screen_x(0.75), screen_y(0.5)),
                                get_vec(100, math.radians(random.uniform(-15,15)-90))
                            ))
                    else:
                        for siren in siren_fleet.fleet:
                            drops = DataFiles.siren_data[siren.name]["drops"]
                            for drop, drop_probability in drops.items():
                                roll = random.random()*100
                                if roll > drop_probability:
                                    continue
                                self.drops.append(Drop(
                                    drop,
                                    pygame.Vector2(screen_x(0.75), screen_y(0.5)),
                                    get_vec(100, math.radians(random.uniform(-15,15)-90))
                                ))

                    new_sortie_progress = self.current_sortie + 1
                    if DataFiles.save_file["sortie_progress"] < new_sortie_progress:
                        DataFiles.save_file["sortie_progress"] = new_sortie_progress
                    
                    for sortie_node in Menus.SORTIE_SELECTION.sortie_nodes:
                        if sortie_node.index <= DataFiles.save_file["sortie_progress"]:
                            sortie_node.unlocked = True
                    Menus.PORT.update_encountered_sirens()
                self.retreat_button.active = False

    def draw(self, surface, font):
        player_fleet.draw(surface, font)
        siren_fleet.draw(surface, font)
        self.next_encounter_button.draw(surface, font)
        self.return_to_port_button.draw(surface, font)
        self.retreat_button.draw(surface, font)

        for drop in self.drops:
            drop.draw(surface, font)
        
        if self.return_to_port_button.active:
            if not player_fleet.afloat:
                font.render(surface, "you lose", self.end_sortie_text_pos, Color.WHITE, 1, style="center", outline_color=Color.BLACK)
            elif not siren_fleet.afloat:
                font.render(surface, "you win", self.end_sortie_text_pos, Color.WHITE, 1, style="center", outline_color=Color.BLACK)

        mpos = pygame.mouse.get_pos()
        if mouse_start_drag is not None:
            pygame.draw.line(surface, Color.WHITE, mouse_start_drag, mpos, width=Box.OUTLINE_WIDTH)
            for siren in siren_fleet.fleet:
                if siren.rect.collidepoint(mpos):
                    if self.selected_shipgirl.battle_component.hull_type in ["DD", "CL"]:
                        # TODO 
                        if siren in siren_fleet.front:
                            pygame.draw.circle(surface, (50,200,50), pygame.Vector2(mpos) + pygame.Vector2(30, 30), 25)
                        else:
                            pygame.draw.circle(surface, (200,50,50), pygame.Vector2(mpos) + pygame.Vector2(30, 30), 25)
                    else:
                        pygame.draw.circle(surface, (50,200,50), pygame.Vector2(mpos) + pygame.Vector2(30, 30), 25)

class Stats:
    NUM_STATS = 4

    MAX_HP = 0
    EVASION = 1
    FIREPOWER = 2
    RELOAD = 3

    STAT_NAMES = {
        MAX_HP: "HP",
        EVASION: "EVA",
        FIREPOWER: "FP",
        RELOAD: "RLD",
    }

class EquipmentMenu:
    def __init__(self):
        self.selected_shipgirl = None
        self.equipped_rects = [
            get_rect(
                width=Box.WIDTH, height=Box.HEIGHT,
                centerx=(i-1)*(Box.WIDTH+Box.PADDING)+screen_x(0.75),
                centery=screen_y(0.5)
            ) for i in range(Equipment.NUM_EQUIPS)
        ]
        self.selected_equipment = Equipment.WEAPON

        num_rects_in_row = 3
        x_rect_offset = (num_rects_in_row-1)/2
        self.equippable_rects = [
            get_rect(
                width=Box.WIDTH, height=Box.HEIGHT,
                centerx=(i%num_rects_in_row-x_rect_offset)*(Box.WIDTH+Box.PADDING)+screen_x(0.75),
                top=(i//num_rects_in_row)*(Box.HEIGHT+Box.PADDING)+Box.HEIGHT/2+Box.PADDING+screen_y(0.5)
            )
            for i in range(6)
        ]
        self.hovered_equipment = None

        def exit_equipment_menu():
            Menus.current_menu = Menus.PORT

            self.selected_shipgirl = None

        self.exit_equipment_menu_button = Button(
            rect=get_rect(width=2*Box.WIDTH, height=Box.HEIGHT,right=RIGHT_OF_SCREEN, top=TOP_OF_SCREEN),
            color=Color.BLUE_GREY,
            text="go back",
            text_color=Color.WHITE,
            callback=exit_equipment_menu
        )

        self.stat_text_xy = [
            pygame.Vector2(screen_x(0.25)-Box.WIDTH/2, Box.HEIGHT/2+Box.PADDING*(2+1.5*i)+screen_y(0.5))
            for i in range(Stats.NUM_STATS)
        ]

    def get_stat(self, shipgirl, stat):
        if stat == Stats.MAX_HP:
            if self.hovered_equipment is None:
                return shipgirl.battle_component.max_hp()
            else:
                return shipgirl.battle_component.max_hp((self.selected_equipment, self.hovered_equipment))
        elif stat == Stats.EVASION:
            if self.hovered_equipment is None:
                return shipgirl.battle_component.evasion()
            else:
                return shipgirl.battle_component.evasion((self.selected_equipment, self.hovered_equipment))
        elif stat == Stats.FIREPOWER:
            if self.hovered_equipment is None:
                return shipgirl.battle_component.firepower()
            else:
                return shipgirl.battle_component.firepower((self.selected_equipment, self.hovered_equipment))
        elif stat == Stats.RELOAD:
            if self.hovered_equipment is None:
                return shipgirl.battle_component.reload()
            else:
                return shipgirl.battle_component.reload((self.selected_equipment, self.hovered_equipment))

    def get_stat_delta(self, shipgirl, stat):
        if self.hovered_equipment is None:
            return 0
        if stat == Stats.MAX_HP:
            return (
                shipgirl.battle_component.max_hp((self.selected_equipment, self.hovered_equipment))
                - shipgirl.battle_component.max_hp()
            )
        elif stat == Stats.EVASION:
            return (
                shipgirl.battle_component.evasion((self.selected_equipment, self.hovered_equipment))
                - shipgirl.battle_component.evasion()
            )
        elif stat == Stats.FIREPOWER:
            return (
                shipgirl.battle_component.firepower((self.selected_equipment, self.hovered_equipment))
                - shipgirl.battle_component.firepower()
            )
        elif stat == Stats.RELOAD:
            return (
                shipgirl.battle_component.reload((self.selected_equipment, self.hovered_equipment))
                - shipgirl.battle_component.reload()
            )

    def update(self, dt, events):
        if self.selected_equipment == Equipment.WEAPON:
            equippable = [
                weapon_name for weapon_name, weapon_info in DataFiles.equipment_data.items()
                if DataFiles.save_file["equipment"].get(weapon_name, 0) > 0
                and weapon_info["type"] == "weapon"
                and weapon_info["equippable_by"] == self.selected_shipgirl.battle_component.hull_type
            ]
        else:
            equippable = [
                aux_name for aux_name, aux_info in DataFiles.equipment_data.items()
                if DataFiles.save_file["equipment"].get(aux_name, 0) > 0
                and aux_info["type"] == "aux"
            ]
        for event in events:
            if event.type == pygame.MOUSEBUTTONUP:
                for i, rect in enumerate(self.equipped_rects):
                    if rect.collidepoint(event.pos):
                        self.selected_equipment = i

                for new_equipment, rect in zip(equippable, self.equippable_rects):
                    if rect.collidepoint(event.pos):
                        current_equipment = self.selected_shipgirl.battle_component.equipment[self.selected_equipment]
                        if current_equipment is not None:
                            DataFiles.save_file["equipment"][current_equipment] = DataFiles.save_file["equipment"].get(current_equipment, 0) + 1
                        self.selected_shipgirl.battle_component.equipment[self.selected_equipment] = new_equipment
                        DataFiles.save_file["equipment"][new_equipment] -= 1
            
                self.exit_equipment_menu_button.click(event.pos)
            if event.type == pygame.MOUSEMOTION:
                for equipment, rect in zip(equippable, self.equippable_rects):
                    if rect.collidepoint(event.pos):
                        self.hovered_equipment = equipment
                        break
                else:
                    self.hovered_equipment = None
        
        if self.selected_shipgirl is not None:
            self.selected_shipgirl.rect.centerx = screen_x(0.25)
            self.selected_shipgirl.rect.centery = screen_y(0.5)
            if self.selected_shipgirl.sprite is not None:
                self.selected_shipgirl.sprite.set_animation(Live2D.IDLE_ANIMATION)
            self.selected_shipgirl.animate(dt)

    def draw(self, surface, font):
        if self.selected_shipgirl is not None:
            # shipgirl chibi
            self.selected_shipgirl.draw(surface, font)
            # shipgirl stats
            for stat, xy in enumerate(self.stat_text_xy):
                font_rect = font.render(
                    surface,
                    f"{Stats.STAT_NAMES[stat]}: {self.get_stat(self.selected_shipgirl, stat)}",
                    xy,
                    Color.WHITE,
                    1,
                    style="topleft",
                    outline_color=Color.BLACK
                )
                stat_delta = self.get_stat_delta(self.selected_shipgirl, stat)
                if stat_delta > 0:
                    center = pygame.Vector2(font_rect.left-10,font_rect.centery) # TODO
                    pygame.draw.polygon(surface, (0,255,0),[
                        center+get_vec(length=5, angle=math.radians(30)),
                        center+get_vec(length=5, angle=math.radians(150)),
                        center+get_vec(length=5, angle=math.radians(270))
                    ])
                elif stat_delta < 0:
                    center = pygame.Vector2(font_rect.left-10,font_rect.centery)
                    pygame.draw.polygon(surface, (255,0,0),[
                        center+get_vec(length=5, angle=math.radians(90)),
                        center+get_vec(length=5, angle=math.radians(210)),
                        center+get_vec(length=5, angle=math.radians(330))
                    ])
            # shipgirl equipment
            for i, (equipment, rect) in enumerate(zip(self.selected_shipgirl.battle_component.equipment, self.equipped_rects)):
                if self.selected_equipment == i:
                    pygame.draw.rect(surface, Color.WHITE, rect, width=2*Box.OUTLINE_WIDTH)
                else:
                    pygame.draw.rect(surface, Color.WHITE, rect, width=Box.OUTLINE_WIDTH)
                if equipment is not None:
                    _ = font.render(surface, equipment, rect.center, Color.WHITE, 1, style="center", outline_color=Color.BLACK)
            # equippable equipment
            if self.selected_equipment == Equipment.WEAPON:
                equippable = [
                    weapon_name for weapon_name, weapon_info in DataFiles.equipment_data.items()
                    if DataFiles.save_file["equipment"].get(weapon_name, 0) > 0
                    and weapon_info["type"] == "weapon"
                    and weapon_info["equippable_by"] == self.selected_shipgirl.battle_component.hull_type
                ]
            else:
                equippable = [
                    aux_name for aux_name, aux_info in DataFiles.equipment_data.items()
                    if DataFiles.save_file["equipment"].get(aux_name, 0) > 0
                    and aux_info["type"] == "aux"
                ]
            for equipment, rect in zip(equippable, self.equippable_rects):
                pygame.draw.rect(surface, Color.WHITE, rect, width=Box.OUTLINE_WIDTH)
                _ = font.render(surface, equipment, rect.center, Color.WHITE, 1, style="center", outline_color=Color.BLACK)
        # exit button
        self.exit_equipment_menu_button.draw(surface, font)

class Menus:
    PORT = PortMenu()
    EQUIPMENT = EquipmentMenu()
    SORTIE_SELECTION = SortieSelectionMenu()
    FLEET_SELECTION = FleetSelectionMenu()
    ENCOUNTER = EncounterMenu()

    current_menu = PORT
    tutorial = None

class Tutorials:
    def __init__(self):
        def draw_tb(surface, font, text, point_pos, point_down, point_right):
            point_pos = pygame.Vector2(point_pos)

            if point_down:
                pointer = DataFiles.sprites["TB_point_down"]
            else:
                pointer = DataFiles.sprites["TB_point_up"]
            
            pointer = pygame.transform.flip(pointer, point_right, False)
            pointer_rect = pointer.get_rect()
            if point_down:
                pointer_rect.bottom = point_pos.y
            else:
                pointer_rect.top = point_pos.y
            if point_right:
                pointer_rect.right = point_pos.x
            else:
                pointer_rect.left = point_pos.x
            surface.blit(pointer, pointer_rect)

            text_scale = 1
            text_width = 2*Box.WIDTH-Box.PADDING
            text_height = font.get_height(text, text_scale, text_width)
            text_rect = get_rect(
                width=text_width, height=text_height + Box.PADDING,
                centerx=pointer_rect.centerx,
                bottom=pointer_rect.top
            )
            if point_right:
                text_rect.right = pointer_rect.left
                polygon = [
                    (text_rect.right, text_rect.bottom-Box.PADDING),
                    (text_rect.right+Box.PADDING, text_rect.bottom+Box.PADDING),
                    (text_rect.right-Box.PADDING, text_rect.bottom)
                ]
            else:
                text_rect.left = pointer_rect.right
                polygon = [
                    (text_rect.left, text_rect.bottom-Box.PADDING),
                    (text_rect.left-Box.PADDING, text_rect.bottom+Box.PADDING),
                    (text_rect.left+Box.PADDING, text_rect.bottom)
                ]
            pygame.draw.rect(surface, Color.DARK_BLUE, text_rect)
            pygame.draw.polygon(surface, Color.DARK_BLUE, polygon)
            font.render(
                surface,
                text,
                pygame.Vector2(text_rect.topleft) + pygame.Vector2(0.5*Box.PADDING, 0.5*Box.PADDING),
                Color.WHITE,
                text_scale,
                outline_color=Color.BLACK,
                box_width=text_rect.width
            )
            
        def start_sortie_on_complete():
            Menus.tutorial = self.assign_fleet

        def draw_start_a_sortie(surface, font):
            button_rect = Menus.PORT.open_select_sortie_menu_button.rect
            rect = get_rect(
                width=button_rect.width + 2*Box.PADDING,
                height=button_rect.height + 2*Box.PADDING,
                center=button_rect.center
            )
            pygame.draw.rect(surface, Color.RED, rect, width=Box.OUTLINE_WIDTH)

            draw_tb(
                surface, font,
                "let's start a sortie!",
                rect.topright,
                True, False
            )

        def select_sortie_node(event):
            mouse_x, mouse_y = event.pos
            hx, hy = pixel_to_hex(mouse_x - SortieNode.CENTER.x, mouse_y - SortieNode.CENTER.y, SortieNode.SIZE)
            return (hx, hy) in Menus.SORTIE_SELECTION.sortie_nodes[0].hexes

        def draw_select_sortie_node(surface, font):
            q, r = Menus.SORTIE_SELECTION.sortie_nodes[0].hexes[0]
            xy = hex_to_pixel(q, r, SortieNode.SIZE)
            rect = get_rect(
                width=2*SortieNode.SIZE, height=2*SortieNode.SIZE,
                center=pygame.Vector2(xy) + SortieNode.CENTER
            )
            pygame.draw.rect(surface, Color.RED, rect, width=Box.OUTLINE_WIDTH)

            draw_tb(
                surface, font,
                "select the area to explore",
                rect.bottomright,
                False, False
            )

        self.start_sortie = Tutorial([
            TutorialTask(
                lambda event : Menus.PORT.open_select_sortie_menu_button.rect.collidepoint(event.pos),
                draw_start_a_sortie
            ),
            TutorialTask(
                select_sortie_node,
                draw_select_sortie_node
            ),
        ], start_sortie_on_complete)

        def assign_fleet_on_complete():
            Menus.tutorial = self.combat_mechanics

        def assign_laffey_input(event):
            return (
                available_shipgirl_rects[0].collidepoint(mouse_start_drag)
                and any(fleet_slot.collidepoint(event.pos) for fleet_slot in Menus.FLEET_SELECTION.fleet_slots)
            )

        def draw_assign_laffey(surface, font):
            shipgirl_rect = available_shipgirl_rects[0]
            rect = get_rect(
                width=shipgirl_rect.width + 2*Box.PADDING,
                height=shipgirl_rect.height + 2*Box.PADDING,
                center=shipgirl_rect.center
            )
            pygame.draw.rect(surface, Color.RED, rect, width=Box.OUTLINE_WIDTH)

            draw_tb(
                surface, font,
                "drag laffey...",
                rect.bottomleft,
                False, True
            )

            center_fleet_slot = Menus.FLEET_SELECTION.fleet_slots[1]
            rect = get_rect(
                width=3*Box.WIDTH + 4*Box.PADDING,
                height=Box.HEIGHT + 2*Box.PADDING,
                center=center_fleet_slot.center
            )
            pygame.draw.rect(surface, Color.RED, rect, width=Box.OUTLINE_WIDTH)

            draw_tb(
                surface, font,
                "...and assign her to your fleet",
                rect.bottomright,
                False, False
            )

        def assign_new_jersey_input(event):
            return (
                available_shipgirl_rects[1].collidepoint(mouse_start_drag)
                and any(fleet_slot.collidepoint(event.pos) for fleet_slot in Menus.FLEET_SELECTION.fleet_slots)
            )
    
        def draw_assign_new_jersey(surface, font):
            shipgirl_rect = available_shipgirl_rects[1]
            rect = get_rect(
                width=shipgirl_rect.width + 2*Box.PADDING,
                height=shipgirl_rect.height + 2*Box.PADDING,
                center=shipgirl_rect.center
            )
            pygame.draw.rect(surface, Color.RED, rect, width=Box.OUTLINE_WIDTH)

            draw_tb(
                surface, font,
                "drag new jersey...",
                rect.bottomleft,
                False, True
            )

            center_fleet_slot = Menus.FLEET_SELECTION.fleet_slots[1]
            rect = get_rect(
                width=3*Box.WIDTH + 4*Box.PADDING,
                height=Box.HEIGHT + 2*Box.PADDING,
                center=center_fleet_slot.center
            )
            pygame.draw.rect(surface, Color.RED, rect, width=Box.OUTLINE_WIDTH)

            draw_tb(
                surface, font,
                "...and assign her to your fleet",
                rect.bottomright,
                False, False
            )

        def draw_start_sortie(surface, font):
            button_rect = Menus.FLEET_SELECTION.start_sortie_button.rect
            rect = get_rect(
                width=button_rect.width + 2*Box.PADDING,
                height=button_rect.height + 2*Box.PADDING,
                center=button_rect.center
            )
            pygame.draw.rect(surface, Color.RED, rect, width=Box.OUTLINE_WIDTH)

            draw_tb(
                surface, font,
                "we're ready to start our sortie!",
                rect.topleft,
                True, True
            )

        self.assign_fleet = Tutorial([
            TutorialTask(
                assign_laffey_input,
                draw_assign_laffey
            ),
            TutorialTask(
                assign_new_jersey_input,
                draw_assign_new_jersey
            ),
            TutorialTask(
                lambda event : Menus.FLEET_SELECTION.start_sortie_button.rect.collidepoint(event.pos),
                draw_start_sortie
            ),
        ], assign_fleet_on_complete)

        def combat_mechanics_on_complete():
            Menus.tutorial = None
        
        def combat_mechanics_input(event):
            return (
                player_fleet.front.rect.collidepoint(mouse_start_drag)
                and any(siren.rect.collidepoint(event.pos) for siren in siren_fleet.front)
            )

        def draw_combat_mechanics(surface, font):
            pygame.draw.rect(surface, Color.RED, player_fleet.front.rect, width=Box.OUTLINE_WIDTH)

            draw_tb(
                surface, font,
                "drag laffey...",
                player_fleet.front.rect.bottomright,
                False, False
            )

            for siren in siren_fleet.front:
                pygame.draw.rect(surface, Color.RED, siren.rect, width=Box.OUTLINE_WIDTH)
            
            draw_tb(
                surface, font,
                "...onto the enemy siren",
                siren_fleet.front[0].rect.bottomleft,
                False, True
            )

        self.combat_mechanics = Tutorial([
            TutorialTask(
                combat_mechanics_input,
                draw_combat_mechanics
            ),
        ], combat_mechanics_on_complete)

        def next_encounter_on_complete():
            Menus.tutorial = None
        
        def draw_next_encounter(surface, font):
            button_rect = Menus.ENCOUNTER.next_encounter_button.rect
            rect = get_rect(
                width=button_rect.width + 2*Box.PADDING,
                height=button_rect.height + 2*Box.PADDING,
                center=button_rect.center
            )
            pygame.draw.rect(surface, Color.RED, rect, width=Box.OUTLINE_WIDTH)

            draw_tb(
                surface, font,
                "go to the next encounter",
                rect.bottomleft,
                False, True
            )

        self.next_encounter = Tutorial([
            TutorialTask(
                lambda event : Menus.ENCOUNTER.next_encounter_button.rect.collidepoint(event.pos),
                draw_next_encounter
            ),
        ], next_encounter_on_complete)

        def draw_return_to_port(surface, font):
            button_rect = Menus.ENCOUNTER.return_to_port_button.rect
            rect = get_rect(
                width=button_rect.width + 2*Box.PADDING,
                height=button_rect.height + 2*Box.PADDING,
                center=button_rect.center
            )
            pygame.draw.rect(surface, Color.RED, rect, width=Box.OUTLINE_WIDTH)

            draw_tb(
                surface, font,
                "let's go home",
                rect.bottomleft,
                False, True
            )

        self.return_to_port = Tutorial([
            TutorialTask(
                lambda event : Menus.ENCOUNTER.return_to_port_button.rect.collidepoint(event.pos),
                draw_return_to_port
            ),
        ], lambda : True)

        # def research_new_ship_on_complete():
        #     Menus.tutorial = None

        # self.research_new_ship = Tutorial([
        #     TutorialTask(
        #         "let's research a new shipgirl! go the shipyard", 
        #         lambda event : Menus.PORT.buildings[PortMenu.SHIPYARD].rect.collidepoint(event.pos)
        #     ),
        #     TutorialTask(
        #         "filter the shipgirls by faction",
        #         lambda event : Menus.PORT.overlay_filter_rects[0].collidepoint(event.pos)
        #     ),
        #     TutorialTask(
        #         "let's research guam", 
        #         lambda event : Menus.PORT.overlay_left_icons[1].collidepoint(event.pos)
        #     ),
        #     TutorialTask(
        #         "start researching!",
        #         lambda event : Menus.PORT.overlay_confirm_button.rect.collidepoint(event.pos)
        #     ),
        #     TutorialTask(
        #         "exit the menu by clicking outside of the overlay",
        #         lambda event : not Menus.PORT.overlay_bg.collidepoint(event.pos)
        #     ),
        #     TutorialTask(
        #         "earning exp during battles will contribute towards researching a new ship!", 
        #         lambda event : True
        #     )
        # ], research_new_ship_on_complete)

        # def construct_new_ship_on_complete():
        #     Menus.tutorial = None

        # self.construct_new_ship = Tutorial([
        #     TutorialTask(
        #         "we've collected enough combat data to construct the shipgirl! go to the shipyard", 
        #         lambda event : Menus.PORT.buildings[PortMenu.SHIPYARD].rect.collidepoint(event.pos)
        #     ),
        #     TutorialTask(
        #         "let's construct the shipgirl",
        #         lambda event : Menus.PORT.overlay_confirm_button.rect.collidepoint(event.pos)
        #     ),
        #     TutorialTask(
        #         "congratulations! guam has joined our fleet!",
        #         lambda event : not Menus.PORT.overlay_bg.collidepoint(event.pos)
        #     )
        # ], construct_new_ship_on_complete)

        # def craft_new_gear_on_complete():
        #     Menus.tutorial = None

        # self.craft_new_gear = Tutorial([
        #     TutorialTask(
        #         "we've collected enough materials to craft a new weapon! go to the gear lab", 
        #         lambda event : Menus.PORT.buildings[PortMenu.GEAR_LAB].rect.collidepoint(event.pos)
        #     ),
        #     TutorialTask(
        #         "filter the gear by hull type",
        #         lambda event : Menus.PORT.overlay_filter_rects[1].collidepoint(event.pos)
        #     ),
        #     TutorialTask(
        #         "let's craft this new DD gun", 
        #         lambda event : Menus.PORT.overlay_left_icons[0].collidepoint(event.pos)
        #     ),
        #     TutorialTask(
        #         "craft!",
        #         lambda event : Menus.PORT.overlay_confirm_button.rect.collidepoint(event.pos)
        #     ),
        #     TutorialTask(
        #         "exit the menu",
        #         lambda event : not Menus.PORT.overlay_bg.collidepoint(event.pos)
        #     ),
        #     TutorialTask(
        #         "let's equip this new gun to laffey. click on her to open the equipment screen",
        #         lambda event : available_shipgirls[0].rect.collidepoint(event.pos)
        #     ),
        #     TutorialTask(
        #         "equip the gun",
        #         lambda event : Menus.EQUIPMENT.equippable_rects[0].collidepoint(event.pos)
        #     ),
        #     TutorialTask(
        #         "congratulations! you've equipped a new gun on laffey! exit this menu",
        #         lambda event : Menus.EQUIPMENT.exit_equipment_menu_button.rect.collidepoint(event.pos)
        #     ),
        # ], craft_new_gear_on_complete)

        self.sortie_end_tutorial_triggers = {
            # 1: self.research_new_ship,
            # 2: self.construct_new_ship,
            # 3: self.craft_new_gear
        }


tutorials = Tutorials()
Menus.tutorial = tutorials.start_sortie
