import os
import math
import random
import json
import pygame
from engine.font import Font
from engine.button import Button
from engine.util import get_rect, get_vec, draw_slice, pixel_to_hex, hex_to_pixel, get_cluster_edges
from engine.load_sprites import load_sprites
from live2d.live2d import Live2D

with open("data/save_file.json") as f:
    save_file = json.load(f)

with open("data/sorties.json") as f:
    sorties = json.load(f)

with open("data/shipgirls.json") as f:
    shipgirl_data = json.load(f)

with open("data/sirens.json") as f:
    siren_data = json.load(f)

with open("data/equipment.json") as f:
    equipment_data = json.load(f)

pygame.init()

SCREEN_SIZE = pygame.Vector2(600, 600)
TEMP_SCREEN_SIZE = pygame.Vector2(600, 600)
screen = pygame.display.set_mode(SCREEN_SIZE)
temp_screen = pygame.Surface(TEMP_SCREEN_SIZE)
clock = pygame.Clock()
font = Font(font_path="engine/big_font.png")
sprites = load_sprites()

mouse_start_drag = None

def screen_x(t):
    return TEMP_SCREEN_SIZE.x * t

def screen_y(t):
    return TEMP_SCREEN_SIZE.y * t

EDGE_PADDING = 20
LEFT_OF_SCREEN = screen_x(0) + EDGE_PADDING
RIGHT_OF_SCREEN = screen_x(1) - EDGE_PADDING
TOP_OF_SCREEN = screen_y(0) + EDGE_PADDING
BOTTOM_OF_SCREEN = screen_y(1) - EDGE_PADDING

class Box:
    WIDTH = 50
    HEIGHT = 50
    OUTLINE_WIDTH = 2

    PADDING = 10

class Color:
    WHITE = (255,255,255)
    BLACK = (10,10,10)
    BLUE_GREY = (100,100,150)
    DARK_BLUE = (50,50,100)

class Buildings:
    INTEL_CENTER = 0
    SHIPYARD = 1
    GEAR_LAB = 2

class Building:
    def __init__(self, building_type, pos):
        self.building_type = building_type
        self.rect = get_rect(width=Box.WIDTH, height=Box.HEIGHT, centerx=pos.x, centery=pos.y)
        self.sprite = None

    def draw(self, surface):
        if self.sprite is not None:
            pass
        else:
            pygame.draw.rect(surface, Color.WHITE, self.rect, width=Box.OUTLINE_WIDTH)
            font.render(surface, str(self.building_type), self.rect.center, Color.WHITE, 1, style="center", outline_color=Color.BLACK)

class PortMenu:
    NO_OVERLAY = -1
    INTEL_CENTER = 0
    SHIPYARD = 1
    GEAR_LAB = 2

    def __init__(self):
        self.current_overlay = self.NO_OVERLAY

        self.buildings = { # TODO magic numbers
            self.INTEL_CENTER: Building(Buildings.INTEL_CENTER, pygame.Vector2(25, 25)),
            self.SHIPYARD: Building(Buildings.SHIPYARD, pygame.Vector2(75, 25)),
            self.GEAR_LAB: Building(Buildings.GEAR_LAB, pygame.Vector2(125, 25)),
        }

        self.overlay_bg = get_rect(width=400, height=400, centerx=screen_x(0.5), centery=screen_y(0.5))
        self.overlay_left_panel = get_rect(
            width=(self.overlay_bg.width-3*Box.PADDING)/2,
            height=self.overlay_bg.height-2*Box.PADDING,
            left=self.overlay_bg.left+Box.PADDING,
            top=self.overlay_bg.top+Box.PADDING
        )
        self.overlay_right_panel = get_rect(
            width=0.5*(self.overlay_bg.width-3*Box.PADDING),
            height=self.overlay_bg.height-2*Box.PADDING,
            right=self.overlay_bg.right-Box.PADDING,
            top=self.overlay_bg.top+Box.PADDING
        )

        num_icons_per_row = 3
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
        icon_padding = (self.overlay_right_panel.width - 2*Box.PADDING - num_icons_per_row*Box.WIDTH) / (num_icons_per_row-1)
        self.overlay_ingredient_icons = [
            get_rect(
                width=Box.WIDTH, height=Box.HEIGHT,
                left=self.overlay_right_panel.left+Box.PADDING+i*(Box.WIDTH+icon_padding),
                bottom=self.overlay_right_panel.bottom-2*Box.PADDING-Box.HEIGHT
            ) for i in range(3)
        ]

        def overlay_confirm():
            if self.current_overlay == self.SHIPYARD:
                selected_entity_info = shipgirl_data[self.overlay_selected_entity]
                hull_type = selected_entity_info["hull_type"]
                unique_item = selected_entity_info["unique_item"]
                selected_entity_reqs = {
                    f"{hull_type}_blueprint": 1,
                    "wisdom_cube": 1,
                    unique_item: 1
                }
                if all(save_file["inventory"][ingredient] >= req for ingredient, req in selected_entity_reqs.items()):
                    save_file["shipgirls"][self.overlay_selected_entity] = {
                        "equipment": [None, None, None],
                        "exp": 0
                    }
                    shipgirl = Shipgirl(self.overlay_selected_entity, True)
                    available_shipgirls.append(shipgirl)
                    for ingredient, req in selected_entity_reqs.items():
                        save_file["inventory"][ingredient] -= req
                else:
                    save_file["research_target"] = self.overlay_selected_entity
            elif self.current_overlay == self.GEAR_LAB:
                selected_entity_reqs = equipment_data[self.overlay_selected_entity]["craft_reqs"]
                if all(save_file["inventory"][ingredient] >= req for ingredient, req in selected_entity_reqs.items()):
                    save_file["equipment"][self.overlay_selected_entity] = save_file["equipment"].get(self.overlay_selected_entity, 0) + 1
                    for ingredient, req in selected_entity_reqs.items():
                        save_file["inventory"][ingredient] -= req

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

    def update(self, dt, events):
        for event in events:
            if event.type == pygame.MOUSEBUTTONUP:
                if self.current_overlay == self.NO_OVERLAY:
                    for shipgirl in available_shipgirls:
                        if shipgirl.rect.collidepoint(event.pos):
                            Menus.EQUIPMENT.selected_shipgirl = shipgirl
                            Menus.current_menu = Menus.EQUIPMENT
                    
                    for overlay_enum, building in self.buildings.items():
                        if building.rect.collidepoint(event.pos):
                            self.current_overlay = overlay_enum

                            if overlay_enum == self.SHIPYARD and save_file["research_target"] is not None:
                                self.overlay_confirm_button.active = True
                                self.overlay_selected_entity = save_file["research_target"]
                else:
                    if not self.overlay_bg.collidepoint(event.pos):
                        self.current_overlay = self.NO_OVERLAY
                        self.overlay_selected_entity = None
                        self.overlay_confirm_button.active = False

                    if self.current_overlay == self.SHIPYARD:
                        entities = [
                            shipgirl for shipgirl in shipgirl_data
                            if shipgirl not in save_file["shipgirls"]
                        ]
                    elif self.current_overlay == self.GEAR_LAB:
                        entities = [weapon for weapon in equipment_data]
                    else:
                        entities = []

                    for entity, rect in zip(entities, self.overlay_left_icons):
                        if rect.collidepoint(event.pos):
                            self.overlay_selected_entity = entity
                            self.overlay_confirm_button.active = True

                    self.overlay_confirm_button.click(event.pos)

                self.open_select_sortie_menu_button.click(event.pos)
        
        for shipgirl in available_shipgirls:
            shipgirl.update(dt)

    def draw(self, surface):
        for shipgirl in available_shipgirls:
            shipgirl.draw(surface)
        self.open_select_sortie_menu_button.draw(surface, font)

        for _, building in self.buildings.items():
            building.draw(surface)

        if self.current_overlay != self.NO_OVERLAY:
            pygame.draw.rect(surface, Color.BLUE_GREY, self.overlay_bg)
            pygame.draw.rect(surface, Color.DARK_BLUE, self.overlay_left_panel)
            pygame.draw.rect(surface, Color.DARK_BLUE, self.overlay_right_panel)

            if self.current_overlay == self.SHIPYARD:
                entities = [
                    shipgirl for shipgirl in shipgirl_data
                    if shipgirl not in save_file["shipgirls"]
                ]
                selected_entity_info = shipgirl_data.get(self.overlay_selected_entity, {})
                if selected_entity_info:
                    hull_type = selected_entity_info["hull_type"]
                    unique_item = selected_entity_info["unique_item"]
                    selected_entity_reqs = {
                        f"{hull_type}_blueprint": 1,
                        "wisdom_cube": 1,
                        unique_item: 1
                    }
                else:
                    selected_entity_reqs = {}
                selected_entity_info = {
                    "HULL": selected_entity_info.get("hull_type"),
                    "HP": selected_entity_info.get("max_hp"),
                    "EVA": selected_entity_info.get("evasion"),
                    "FP": selected_entity_info.get("firepower"),
                    "RLD": selected_entity_info.get("reload"),
                }
            elif self.current_overlay == self.GEAR_LAB:
                entities = [weapon for weapon in equipment_data]
                selected_entity_info = equipment_data.get(self.overlay_selected_entity, {})
                selected_entity_reqs = selected_entity_info.get("craft_reqs")
                selected_entity_info = {
                    "HULL": selected_entity_info.get("equippable_by"),
                    "HP": selected_entity_info.get("max_hp"),
                    "EVA": selected_entity_info.get("evasion"),
                    "FP": selected_entity_info.get("firepower"),
                    "RLD": selected_entity_info.get("reload"),
                    "SHELL": selected_entity_info.get("shell_type"),
                }
            else:
                entities = []
                selected_entity_reqs = {}
                selected_entity_info = {}
            
            for entity, rect in zip(entities, self.overlay_left_icons):
                pygame.draw.rect(surface, Color.WHITE, rect, width=Box.OUTLINE_WIDTH)
                if entity in sprites:
                    surface.blit(sprites[entity], rect)
                else:
                    font.render(surface, entity, rect.center, Color.WHITE, 1, style="center", outline_color=Color.BLACK)
            
            if self.overlay_selected_entity:
                font.render(surface, self.overlay_selected_entity, self.overlay_right_name, Color.WHITE, 1, style="center", outline_color=Color.BLACK)
                if self.overlay_selected_entity in sprites:
                    surface.blit(sprites[self.overlay_selected_entity], self.overlay_right_icon)
                pygame.draw.rect(surface, Color.WHITE, self.overlay_right_icon, width=Box.OUTLINE_WIDTH)

                x = self.overlay_right_panel.left + Box.PADDING
                y = self.overlay_right_icon.bottom + Box.PADDING
                for info_key, info_value in selected_entity_info.items():
                    if info_value is None:
                        continue
                    xy = (x, y)
                    info_name = Stats.STAT_NAMES.get(info_key, info_key)
                    font.render(surface, f"{info_name}: {info_value}", xy, Color.WHITE, 1, style="topleft", outline_color=Color.BLACK)
                    y += Box.PADDING # TODO

                for (ingredient, req), rect in zip(selected_entity_reqs.items(), self.overlay_ingredient_icons):
                    if ingredient in sprites:
                        surface.blit(sprites[ingredient], rect)
                        pygame.draw.rect(surface, Color.WHITE, rect, width=Box.OUTLINE_WIDTH)
                    else:
                        pygame.draw.rect(surface, Color.WHITE, rect, width=Box.OUTLINE_WIDTH)
                        xy = (rect.centerx, rect.top+0.33*rect.height) # TODO
                        font.render(surface, ingredient, xy, Color.WHITE, 1, style="center", outline_color=Color.BLACK)
                    xy = (rect.centerx, rect.top+0.67*rect.height)
                    amt = save_file["inventory"].get(ingredient, 0)
                    font.render(surface, f"{amt}-{req}", xy, Color.WHITE, 1, style="center", outline_color=Color.BLACK)

            self.overlay_confirm_button.draw(surface, font)

class SortieNode:
    SIZE = 50
    CENTER = pygame.Vector2(screen_x(0.25), screen_y(0.5))

    def __init__(self, index, hexes):
        self.index = index
        self.hexes = hexes
        self.unlocked = self.index <= save_file["sortie_progress"]
        self.cleared = self.index < save_file["sortie_progress"]
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

    def draw(self, surface):
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
            # pygame.draw.polygon(surface, color, polygon)
            # outline_width = (2 if self.hovered else 1) * Box.OUTLINE_WIDTH
            # pygame.draw.polygon(surface, Color.WHITE, polygon, width=outline_width)
            font.render(surface, str(self.index), pygame.Vector2(x, y) + self.CENTER, Color.WHITE, 1, style="center", outline_color=Color.BLACK)


class SortieSelectionMenu:
    def __init__(self):
        self.sortie_nodes = [
            SortieNode(0, [(0,0)]),
            SortieNode(1, [(1,-1)]),
            SortieNode(2, [(0,1)]),
            SortieNode(3, [(1,0),(2,0),(1,1),(2,-1)])
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

    def draw(self, surface):
        self.exit_sortie_selection_menu_button.draw(surface, font)

        for sortie_node in self.sortie_nodes:
            sortie_node.draw(surface)

class FleetSelectionMenu:
    def __init__(self):
        self.selected_shipgirl = None
        def start_encounter():
            if all(shipgirl is None for shipgirl in player_fleet.shipgirls):
                return
            Menus.current_menu = Menus.ENCOUNTER
            
            player_fleet.begin_sortie()

            Menus.ENCOUNTER.begin_encounter()

        self.start_encounter_button = Button(
            rect=get_rect(width=2*Box.WIDTH, height=Box.HEIGHT, centerx=screen_x(0.75), bottom=BOTTOM_OF_SCREEN),
            color=Color.BLUE_GREY,
            text="start",
            text_color=Color.WHITE,
            callback=start_encounter
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
                            self.selected_shipgirl = None
                mouse_start_drag = None
                self.start_encounter_button.click(event.pos)
                self.exit_fleet_selection_menu_button.click(event.pos)
        
        for shipgirl in player_fleet.shipgirls:
            if shipgirl is not None:
                shipgirl.animate(dt)

    def draw(self, surface):
        player_fleet.draw(surface)
        self.start_encounter_button.draw(surface, font)
        self.exit_fleet_selection_menu_button.draw(surface, font)

        for shipgirl, rect in zip(available_shipgirls, available_shipgirl_rects):
            pygame.draw.rect(surface, Color.WHITE, rect, width=Box.OUTLINE_WIDTH)
            font.render(surface, shipgirl.name, rect.center, Color.WHITE, 1, style="center", outline_color=Color.BLACK)

        for slot, shipgirl in zip(self.fleet_slots, player_fleet.shipgirls):
            if shipgirl is None:
                rect = get_rect(width=Box.WIDTH, height=Box.HEIGHT, centerx=slot.centerx, centery=slot.centery)
                pygame.draw.rect(surface, Color.WHITE, rect, width=Box.OUTLINE_WIDTH)
        
        mpos = pygame.mouse.get_pos()
        if mouse_start_drag is not None:
            pygame.draw.line(surface, Color.WHITE, mouse_start_drag, mpos, width=Box.OUTLINE_WIDTH)

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
            Menus.current_menu = Menus.PORT

            Menus.ENCOUNTER.return_to_port_button.active = False

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

    def begin_encounter(self):
        sortie_data = sorties[self.current_sortie]
        encounter_data = sortie_data["encounters"][self.current_encounter]
        siren_fleet._front = [Shipgirl(siren_name, False) for siren_name in encounter_data["front"]] # TODO
        siren_fleet._back = [Shipgirl(siren_name, False) for siren_name in encounter_data["back"]]
        for siren in siren_fleet.fleet:
            if siren_data[siren.name]["target_pref"] == "front":
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
                    if shipgirl is not None and shipgirl.battle_component.active and shipgirl.rect.collidepoint(event.pos):
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
                    save_file["research_progress"] += siren.battle_component.exp
                    
                    if self.current_sortie < save_file["sortie_progress"]:
                        drops = siren_data[siren.name]["drops"]
                        for drop, drop_probability in drops.items():
                            roll = random.random()*100
                            if roll > drop_probability:
                                continue
                            save_file["inventory"][drop] = save_file["inventory"].get(drop, 0) + 1
                
                exp_req = 5 # TODO
                if save_file["research_progress"] >= exp_req:
                    if save_file["research_target"] is not None:
                        unique_item = shipgirl_data[save_file["research_target"]]["unique_item"]
                        save_file["inventory"][unique_item["name"]] = 1
                        save_file["research_target"] = None
                        save_file["research_progress"] -= exp_req

                player_fleet.end_encounter()
                siren_fleet.end_encounter()
                num_encounters = len(sorties[self.current_sortie]["encounters"])
                if self.current_encounter+1 < num_encounters:
                    self.next_encounter_button.active = True
                else:
                    self.return_to_port_button.active = True

                    if self.current_sortie == save_file["sortie_progress"]:
                        rewards = sorties[self.current_sortie]["rewards"]
                        for reward in rewards:
                            save_file["inventory"][reward] = save_file["inventory"].get(reward, 0) + 1

                    save_file["sortie_progress"] = max(
                        save_file["sortie_progress"],
                        self.current_sortie + 1
                    )
                    for sortie_node in Menus.SORTIE_SELECTION.sortie_nodes:
                        if sortie_node.index <= save_file["sortie_progress"]:
                            sortie_node.unlocked = True
                self.retreat_button.active = False

    def draw(self, surface):
        player_fleet.draw(surface)
        siren_fleet.draw(surface)
        self.next_encounter_button.draw(surface, font)
        self.return_to_port_button.draw(surface, font)
        self.retreat_button.draw(surface, font)
        
        if self.return_to_port_button.active:
            if not player_fleet.afloat:
                font.render(surface, "you lose", self.end_sortie_text_pos, Color.WHITE, 1, style="center", outline_color=Color.BLACK)
            elif not siren_fleet.afloat:
                font.render(surface, "you win", self.end_sortie_text_pos, Color.WHITE, 1, style="center", outline_color=Color.BLACK)

        mpos = pygame.mouse.get_pos()
        if mouse_start_drag is not None:
            pygame.draw.line(temp_screen, Color.WHITE, mouse_start_drag, mpos, width=Box.OUTLINE_WIDTH)
            for siren in siren_fleet.fleet:
                if siren.rect.collidepoint(mpos):
                    if self.selected_shipgirl.battle_component.hull_type in ["DD", "CL"]:
                        # TODO 
                        if siren in siren_fleet.front:
                            pygame.draw.circle(temp_screen, (50,200,50), pygame.Vector2(mpos) + pygame.Vector2(30, 30), 25)
                        else:
                            pygame.draw.circle(temp_screen, (200,50,50), pygame.Vector2(mpos) + pygame.Vector2(30, 30), 25)
                    else:
                        pygame.draw.circle(temp_screen, (50,200,50), pygame.Vector2(mpos) + pygame.Vector2(30, 30), 25)

class Equipment:
    NUM_EQUIPS = 3
    WEAPON = 0
    AUX1 = 1
    AUX2 = 2

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
                weapon_name for weapon_name, weapon_info in equipment_data.items()
                if save_file["equipment"].get(weapon_name, 0) > 0
                and weapon_info["type"] == "weapon"
                and weapon_info["equippable_by"] == self.selected_shipgirl.battle_component.hull_type
            ]
        else:
            equippable = [
                aux_name for aux_name, aux_info in equipment_data.items()
                if save_file["equipment"].get(aux_name, 0) > 0
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
                            save_file["equipment"][current_equipment] = save_file["equipment"].get(current_equipment, 0) + 1
                        self.selected_shipgirl.battle_component.equipment[self.selected_equipment] = new_equipment
                        save_file["equipment"][new_equipment] -= 1
            
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

    def draw(self, surface):
        if self.selected_shipgirl is not None:
            # shipgirl chibi
            self.selected_shipgirl.draw(surface)
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
                    weapon_name for weapon_name, weapon_info in equipment_data.items()
                    if save_file["equipment"].get(weapon_name, 0) > 0
                    and weapon_info["type"] == "weapon"
                    and weapon_info["equippable_by"] == self.selected_shipgirl.battle_component.hull_type
                ]
            else:
                equippable = [
                    aux_name for aux_name, aux_info in equipment_data.items()
                    if save_file["equipment"].get(aux_name, 0) > 0
                    and aux_info["type"] == "aux"
                ]
            for equipment, rect in zip(equippable, self.equippable_rects):
                pygame.draw.rect(surface, Color.WHITE, rect, width=Box.OUTLINE_WIDTH)
                _ = font.render(surface, equipment, rect.center, Color.WHITE, 1, style="center", outline_color=Color.BLACK)
        # exit button
        self.exit_equipment_menu_button.draw(surface, font)

class Armor:
    LIGHT = 0
    MEDIUM = 1
    HEAVY = 2

    HULL_TO_ARMOR_MAP = {
        "DD": LIGHT,
        "CL": MEDIUM,
        "CA": MEDIUM,
        "BB": HEAVY
    }

    DAMAGE_MULTIPLIER = {
        "normal": {LIGHT: 1.0, MEDIUM: 1.0, HEAVY: 1.0},
        "HE": {LIGHT: 1.5, MEDIUM: 1.25, HEAVY: 1.0},
        "AP": {LIGHT: 1.0, MEDIUM: 1.25, HEAVY: 1.5},
    }

class ShipgirlBattleComponent:
    def __init__(self, name, is_player):
        self.active = False
        self.display_timer = is_player

        if name in shipgirl_data:
            info = shipgirl_data[name]
            info["equipment"] = save_file["shipgirls"][name]["equipment"]
            info["exp"] = save_file["shipgirls"][name]["exp"]
        else:
            info = siren_data[name]

        self.base_max_hp = info["max_hp"]
        self.base_evasion = info["evasion"]
        self.base_firepower = info["firepower"]
        self.base_reload = info["reload"]
        self.hull_type = info["hull_type"]
        self.equipment = info["equipment"]
        self.exp =  info["exp"]

        self.hp = self.max_hp()
        self.cooldown_timer = 1
        self.target = None
        self.evasion_gauge = 0

    def max_hp(self, equipment_override=None):
        equipment = self.equipment.copy()
        if equipment_override is not None:
            equipment[equipment_override[0]] = equipment_override[1]
        return (
            self.base_max_hp
            + equipment_data.get(equipment[Equipment.WEAPON], {}).get("max_hp", 0)
            + equipment_data.get(equipment[Equipment.AUX1], {}).get("max_hp", 0)
            + equipment_data.get(equipment[Equipment.AUX2], {}).get("max_hp", 0)
        )

    def evasion(self, equipment_override=None):
        equipment = self.equipment.copy()
        if equipment_override is not None:
            equipment[equipment_override[0]] = equipment_override[1]
        return (
            self.base_evasion
            + equipment_data.get(equipment[Equipment.WEAPON], {}).get("evasion", 0)
            + equipment_data.get(equipment[Equipment.AUX1], {}).get("evasion", 0)
            + equipment_data.get(equipment[Equipment.AUX2], {}).get("evasion", 0)
        )

    def firepower(self, equipment_override=None):
        equipment = self.equipment.copy()
        if equipment_override is not None:
            equipment[equipment_override[0]] = equipment_override[1]
        return (
            self.base_firepower
            + equipment_data.get(equipment[Equipment.WEAPON], {}).get("firepower", 0)
            + equipment_data.get(equipment[Equipment.AUX1], {}).get("firepower", 0)
            + equipment_data.get(equipment[Equipment.AUX2], {}).get("firepower", 0)
        )

    def reload(self, equipment_override=None):
        equipment = self.equipment.copy()
        if equipment_override is not None:
            equipment[equipment_override[0]] = equipment_override[1]
        return (
            self.base_reload
            + equipment_data.get(equipment[Equipment.WEAPON], {}).get("reload", 0)
            + equipment_data.get(equipment[Equipment.AUX1], {}).get("reload", 0)
            + equipment_data.get(equipment[Equipment.AUX2], {}).get("reload", 0)
        )

    def reset(self):
        self.hp = self.max_hp()
        self.cooldown_timer = 1

    def update(self, dt):
        if not self.active:
            return

        if self.target is not None and self.target.battle_component.hp <= 0:
            self.target = None
        
        self.cooldown_timer = max(0, self.cooldown_timer - self.reload()/1000*dt)
        if self.target is not None and self.cooldown_timer <= 0:
            if self.target.battle_component.evasion_gauge >= 1:
                self.target.battle_component.evasion_gauge -= 1
            else:
                weapon_info = equipment_data.get(self.equipment[0], {}) if self.equipment[0] is not None else {}
                shell_type = weapon_info.get("shell_type", "normal")
                armor_type = Armor.HULL_TO_ARMOR_MAP[self.target.battle_component.hull_type]
                self.target.battle_component.hp -= self.firepower() * Armor.DAMAGE_MULTIPLIER[shell_type][armor_type]
                self.target.battle_component.evasion_gauge += self.target.battle_component.evasion() / 1000
            self.cooldown_timer = 1

    def draw(self, screen, rect):
        if not self.active:
            return
        
        bar_width = 50
        bar_background = get_rect(width=bar_width, height=10, centerx=rect.centerx, top=rect.bottom+20) # TODO
        bar_fill = get_rect(width=bar_width*self.hp/self.max_hp(), height=bar_background.height, left=bar_background.left, top=bar_background.top)
        pygame.draw.rect(screen, (50,50,50), bar_background)
        pygame.draw.rect(screen, Color.WHITE, bar_fill)

        if not self.display_timer:
            return

        center = pygame.Vector2(rect.centerx, rect.top-50) # TODO
        radius = 30
        start_angle = -90
        end_angle = start_angle + 360 * (1 - self.cooldown_timer)
        color = (50,200,50) if self.target is not None else (200,50,50)
        draw_slice(screen, color, center, radius, start_angle, end_angle)
        pygame.draw.circle(screen, Color.WHITE, center, radius, width=Box.OUTLINE_WIDTH)

class Shipgirl:
    def __init__(self, name, is_player):
        self.name = name
    
        self.pos = pygame.Vector2(
            screen_x(random.random()),
            screen_y(random.random())
        )
        self.wander_target = self.pos.copy()
        self.pause_time = 0
        if os.path.exists(f"live2d/{self.name}/model.json"):
            self.sprite = Live2D(f"live2d/{self.name}/model.json")
        else:
            self.sprite = None
        self.facing_left = False
            
        self.rect = get_rect(width=Box.WIDTH, height=Box.HEIGHT, centerx=self.pos.x, centery=self.pos.y)

        self.battle_component = ShipgirlBattleComponent(self.name, is_player)

    def update(self, dt):
        if self.pause_time > 0:
            self.pause_time -= dt
            if self.sprite is not None:
                self.sprite.set_animation(Live2D.IDLE_ANIMATION)
        else:
            to_target = self.wander_target - self.pos
            if to_target.length() < 10: # TODO
                self.wander_target = pygame.Vector2(
                    screen_x(random.random()),
                    screen_y(random.random())
                )
                self.pause_time = random.uniform(1, 3) # TODO
            else:
                direction = to_target.normalize()
                self.pos += direction * 50 * dt # TODO
                if direction.x >= 0:
                    self.facing_left = False
                else:
                    self.facing_left = True
            
            if self.sprite is not None:
                self.sprite.set_animation(Live2D.WALK_ANIMATION)
        self.rect.center = self.pos

        self.animate(dt)

    def animate(self, dt):
        if self.sprite is not None:
            self.sprite.update(dt)

    def draw(self, screen):
        if self.sprite is not None:
            self.sprite.draw(screen, self.rect.centerx, self.rect.centery, self.facing_left)
        else:
            pygame.draw.rect(screen, Color.WHITE, self.rect, width=Box.OUTLINE_WIDTH)
            _ = font.render(screen, self.name, self.rect.center, Color.WHITE, 1, style="center", outline_color=Color.BLACK)

        self.battle_component.draw(screen, self.rect)

class PlayerFleet:
    def __init__(self):
        self.shipgirls = [None, None, None]
    
    @property
    def afloat(self):
        return any(shipgirl is not None and shipgirl.battle_component.hp > 0 for shipgirl in self.shipgirls)

    @property
    def shipgirl_names(self):
        return [shipgirl.name for shipgirl in self.shipgirls if shipgirl is not None]

    @property
    def front(self):
        for shipgirl in self.shipgirls:
            if shipgirl is not None and shipgirl.battle_component.hp > 0:
                return shipgirl
        return None

    def clear_fleet(self):
        self.shipgirls = [None, None, None]

    def begin_sortie(self):
        for shipgirl in self.shipgirls:
            if shipgirl is not None:
                shipgirl.battle_component.reset()

    def begin_encounter(self):
        for shipgirl in self.shipgirls:
            if shipgirl is not None:
                shipgirl.battle_component.active = True

    def end_encounter(self):
        for shipgirl in self.shipgirls:
            if shipgirl is not None:
                shipgirl.battle_component.target = None
                shipgirl.battle_component.active = False

    def update(self, dt):
        fleet_slot_offset = (len(self.shipgirls)-1)/2
        for i, shipgirl in enumerate(self.shipgirls):
            if shipgirl is not None:
                shipgirl.rect.centerx = screen_x(0.25) + (fleet_slot_offset-i)*(Box.WIDTH+Box.PADDING)
                shipgirl.rect.centery = screen_y(0.5)

                if shipgirl.battle_component.hp <= 0:
                    shipgirl.battle_component.active = False
                shipgirl.battle_component.update(dt)

                shipgirl.animate(dt)

    def draw(self, screen):
        for shipgirl in self.shipgirls:
            if shipgirl is not None:
                shipgirl.draw(screen)

class SirenFleet:
    def __init__(self):
        self._front = []
        self._back = []
    
    @property
    def afloat(self):
        return any(siren.battle_component.hp > 0 for siren in self.fleet)

    @property
    def siren_names(self):
        return [siren.name for siren in self.fleet]

    @property
    def front(self):
        return (
            [siren for siren in self._front if siren.battle_component.hp > 0]
            or [siren for siren in self._back if siren.battle_component.hp > 0]
        )

    @property
    def fleet(self):
        return self._front + self._back

    def clear_fleet(self):
        self._front = []
        self._back = []

    def begin_sortie(self):
        for siren in self.fleet:
            siren.battle_component.reset()

    def begin_encounter(self):
        for siren in self.fleet:
            siren.battle_component.active = True

    def end_encounter(self):
        for siren in self.fleet:
            siren.battle_component.target = None
            siren.battle_component.active = False

    def update(self, dt):
        front_offset = (len(self._front)-1)/2
        for i, siren in enumerate(self._front):
            siren.rect.centerx = screen_x(0.75) - (Box.WIDTH+Box.PADDING) + (i-front_offset)*(Box.WIDTH+Box.PADDING)
            siren.rect.centery = screen_y(0.5) + (i-front_offset)*Box.WIDTH

            if siren.battle_component.hp <= 0:
                siren.battle_component.active = False
            siren.battle_component.update(dt)
        
        back_offset = (len(self._back)-1)/2
        for i, siren in enumerate(self._back): 
            siren.rect.centerx = screen_x(0.75) + (Box.WIDTH+Box.PADDING) + (i-back_offset)*(Box.WIDTH+Box.PADDING)
            siren.rect.centery = screen_y(0.5) + (i-back_offset)*Box.WIDTH

            if siren.battle_component.hp <= 0:
                siren.battle_component.active = False
            siren.battle_component.update(dt)

    def draw(self, screen):
        for siren in self.fleet:
            siren.draw(screen)

available_shipgirls = [Shipgirl(shipgirl_name, True) for shipgirl_name in save_file["shipgirls"]]
available_shipgirl_rects = [
    get_rect( # TODO
        width=Box.WIDTH, height=Box.HEIGHT,
        centerx=(Box.WIDTH+Box.PADDING)*(i%4-1.5) + screen_x(0.75),
        centery=(Box.HEIGHT+Box.PADDING)*(i//4-1.5) + screen_y(0.5)
    ) for i in range(4)
]
player_fleet = PlayerFleet()
siren_fleet = SirenFleet()

class Menus:
    PORT = PortMenu()
    EQUIPMENT = EquipmentMenu()
    SORTIE_SELECTION = SortieSelectionMenu()
    FLEET_SELECTION = FleetSelectionMenu()
    ENCOUNTER = EncounterMenu()

    current_menu = PORT

running = True
while running:
    clock.tick()
    dt = clock.get_time() / 1000
    pygame.display.set_caption(f"{clock.get_fps()}")

    events = pygame.event.get()
    for event in events:
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            running = False

    Menus.current_menu.update(dt, events)

    temp_screen.fill((20,20,50)) # TODO
    Menus.current_menu.draw(temp_screen)
    screen.blit(pygame.transform.scale(temp_screen, screen.get_size()), (0,0))
    pygame.display.flip()

pygame.quit()

for shipgirl in available_shipgirls:
    save_file["shipgirls"][shipgirl.name]["exp"] = shipgirl.battle_component.exp

with open("data/save_file.json", "w") as f:
    json.dump(save_file, f, indent=4)