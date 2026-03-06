import math
import random
import json
import pygame
from engine.font import Font
from engine.button import Button
from engine.util import get_rect, get_vec, draw_slice

with open("data/save_file.json") as f:
    save_file = json.load(f)

with open("data/sorties.json") as f:
    sorties = json.load(f)

with open("data/shipgirls.json") as f:
    shipgirl_data = json.load(f)

with open("data/sirens.json") as f:
    siren_data = json.load(f)

with open("data/weapons.json") as f:
    weapon_data = json.load(f)

with open("data/auxiliary_items.json") as f:
    auxiliary_item_data = json.load(f)

pygame.init()

SCREEN_SIZE = pygame.Vector2(600, 600)
TEMP_SCREEN_SIZE = pygame.Vector2(600, 600)
screen = pygame.display.set_mode(SCREEN_SIZE)
temp_screen = pygame.Surface(TEMP_SCREEN_SIZE)
clock = pygame.Clock()
font = Font("engine/big_font.png")

mouse_start_drag = None

EDGE_PADDING = 20
LEFT_OF_SCREEN = EDGE_PADDING
RIGHT_OF_SCREEN = TEMP_SCREEN_SIZE.x - EDGE_PADDING
TOP_OF_SCREEN = EDGE_PADDING
BOTTOM_OF_SCREEN = TEMP_SCREEN_SIZE.y - EDGE_PADDING

class Buildings:
    INTEL_CENTER = 0 # players get intel on shipgirls they have constructed // sirens that they've defeated

    SHIPYARD = 1

    GEAR_LAB = 2

    MUNITIONS = 3

    # DD_SHIPYARD = 10 # players research new DD ships
    # CL_SHIPYARD = 11 # players research new CL ships
    # CA_SHIPYARD = 12 # players research new CA ships
    # BB_SHIPYARD = 13 # players research new BB ships
    # CV_SHIPYARD = 14 # players research new CV ships

    # DD_GEAR_LAB = 20 # players craft new DD gear
    # CL_GEAR_LAB = 21 # players craft new CL gear
    # CA_GEAR_LAB = 22 # players craft new CA gear
    # BB_GEAR_LAB = 23 # players craft new BB gear
    # CV_GEAR_LAB = 24 # players craft new CV gear

    # MUNITIONS = 30 # players produce misc items

    # RESEARCH_CENTER - players select which shipgirl they would like to research
    # as they collect exp over time from sortie-ing, they progress towards a unique item
    # that is eventualyl used to construct the shipgirl

class Building:
    def __init__(self, building_type, pos):
        self.building_type = building_type
        self.rect = get_rect(width=50, height=50, centerx=pos.x, centery=pos.y)
        self.sprite = None

    def draw(self, screen):
        if self.sprite is not None:
            pass
        else:
            pygame.draw.rect(screen, (255,255,255), self.rect, width=2)
            font.render(screen, str(self.building_type), self.rect.center, (255,255,255), 1, style="center", outline_color=(10,10,10))

class PortMenu:
    NO_OVERLAY = 0
    SHIPYARD = 1
    GEAR_LAB = 2
    MUNITIONS = 3
    current_overlay = NO_OVERLAY

    buildings = [ # TODO
        Building(Buildings.INTEL_CENTER, pygame.Vector2(25, 25)),
        Building(Buildings.SHIPYARD, pygame.Vector2(75, 25)),
        Building(Buildings.GEAR_LAB, pygame.Vector2(125, 25)),
        Building(Buildings.MUNITIONS, pygame.Vector2(175, 25))
    ]

    overlay_bg = get_rect(width=400, height=400, centerx=0.5*TEMP_SCREEN_SIZE.x, centery=0.5*TEMP_SCREEN_SIZE.y)
    overlay_left_panel = get_rect( # TODO
        width=0.5*(overlay_bg.width-30),
        height=overlay_bg.height-20,
        left=overlay_bg.left+10,
        top=overlay_bg.top+10
    )
    overlay_right_panel = get_rect( # TODO
        width=0.5*(overlay_bg.width-30),
        height=overlay_bg.height-20,
        right=overlay_bg.right-10,
        top=overlay_bg.top+10
    )

    overlay_left_icons = [ # TODO
        get_rect(
            width=50, height=50,
            left=120+(i%3)*(50+7.5),
            top=120+(i//3)*(50+7.5)
        ) for i in range(12)
    ]

    overlay_right_icon = get_rect( # TODO
        width=50, height=50,
        centerx=overlay_right_panel.centerx,
        top=overlay_right_panel.top+10
    )
    overlay_ingredient_icons = [ # TODO
        get_rect(
            width=50, height=50,
            left=315+i*(50+7.5),
            bottom=420
        ) for i in range(3)
    ]

    @staticmethod
    def overlay_confirm():
        if PortMenu.current_overlay == PortMenu.SHIPYARD:
            selected_entity_reqs = shipgirl_data[PortMenu.overlay_selected_entity]["research_reqs"]
            if (
                PortMenu.overlay_selected_entity not in save_file["shipgirls"]
                and all(save_file["inventory"][ingredient] >= req for ingredient, req in selected_entity_reqs.items())
            ):
                save_file["shipgirls"][PortMenu.overlay_selected_entity] = [None, None, None]
                shipgirl = Shipgirl(PortMenu.overlay_selected_entity)
                available_shipgirls.append(shipgirl)
                for ingredient, req in selected_entity_reqs.items():
                    save_file["inventory"][ingredient] -= req
        elif PortMenu.current_overlay == PortMenu.GEAR_LAB:
            selected_entity_reqs = weapon_data[PortMenu.overlay_selected_entity]["craft_reqs"]
            if all(save_file["inventory"][ingredient] >= req for ingredient, req in selected_entity_reqs.items()):
                if PortMenu.overlay_selected_entity in save_file["weapons"]:
                    save_file["weapons"][PortMenu.overlay_selected_entity] += 1
                else:
                    save_file["weapons"][PortMenu.overlay_selected_entity] = 1
                for ingredient, req in selected_entity_reqs.items():
                    save_file["inventory"][ingredient] -= req


    overlay_confirm_button = Button( # TODO
        rect=get_rect(width=100, height=50, centerx=397.5, bottom=480),
        color=(100,100,150),
        text="confirm",
        text_color=(255,255,255),
        callback=overlay_confirm,
        active=False
    )

    overlay_selected_entity = None

    @staticmethod
    def open_select_sortie_menu():
        Menus.current_menu = Menus.SORTIE_SELECTION

    open_select_sortie_menu_button = Button(
        rect=get_rect(width=100, height=50, centerx=0.5*TEMP_SCREEN_SIZE.x, bottom=BOTTOM_OF_SCREEN),
        color=(100,100,150),
        text="sortie",
        text_color=(255,255,255),
        callback=open_select_sortie_menu
    )

    @staticmethod
    def update(dt, events):
        for event in events:
            if event.type == pygame.MOUSEBUTTONUP:
                if PortMenu.current_overlay == PortMenu.NO_OVERLAY:
                    for shipgirl in available_shipgirls:
                        if shipgirl.rect.collidepoint(event.pos):
                            EquipmentMenu.selected_shipgirl = shipgirl
                            Menus.current_menu = Menus.EQUIPMENT
                    
                    for building in PortMenu.buildings:
                        if building.rect.collidepoint(event.pos):
                            if building.building_type == Buildings.SHIPYARD:
                                PortMenu.current_overlay = PortMenu.SHIPYARD
                            if building.building_type == Buildings.GEAR_LAB:
                                PortMenu.current_overlay = PortMenu.GEAR_LAB
                            if building.building_type == Buildings.MUNITIONS:
                                PortMenu.current_overlay = PortMenu.MUNITIONS
                else:
                    if not PortMenu.overlay_bg.collidepoint(event.pos):
                        PortMenu.current_overlay = PortMenu.NO_OVERLAY
                        PortMenu.overlay_selected_entity = None
                        PortMenu.overlay_confirm_button.active = False

                    if PortMenu.current_overlay == PortMenu.SHIPYARD:
                        entities = [shipgirl for shipgirl, shipgirl_info in shipgirl_data.items() if shipgirl_info["research_reqs"]]
                    elif PortMenu.current_overlay == PortMenu.GEAR_LAB:
                        entities = [weapon for weapon in weapon_data]
                    else:
                        entities = []

                    for entity, rect in zip(entities, PortMenu.overlay_left_icons):
                        if rect.collidepoint(event.pos):
                            PortMenu.overlay_selected_entity = entity
                            PortMenu.overlay_confirm_button.active = True
                    
                    PortMenu.overlay_confirm_button.click(event.pos)

                    # TODO write update logic for each overlay in a method
                    # update the overlay enum to point to these methods for each overlay type

                PortMenu.open_select_sortie_menu_button.click(event.pos)
        
        for shipgirl in available_shipgirls:
            shipgirl.update(dt)

    @staticmethod
    def draw(surface):
        for shipgirl in available_shipgirls:
            shipgirl.draw(surface)
        PortMenu.open_select_sortie_menu_button.draw(surface, font)

        for building in PortMenu.buildings:
            building.draw(surface)

        if PortMenu.current_overlay != PortMenu.NO_OVERLAY:
            pygame.draw.rect(surface, (100,100,150), PortMenu.overlay_bg)
            pygame.draw.rect(surface, (50,50,100), PortMenu.overlay_left_panel)
            pygame.draw.rect(surface, (50,50,100), PortMenu.overlay_right_panel)

            if PortMenu.current_overlay == PortMenu.SHIPYARD:
                entities = [shipgirl for shipgirl, shipgirl_info in shipgirl_data.items() if shipgirl_info["research_reqs"]]
                selected_entity_reqs = shipgirl_data.get(PortMenu.overlay_selected_entity, {}).get("research_reqs", {})
                selected_entity_info = shipgirl_data.get(PortMenu.overlay_selected_entity, {})
                selected_entity_info = {
                    "HULL": selected_entity_info.get("hull_type", 0),
                    "HP": selected_entity_info.get("max_hp", 0),
                    "EVA": selected_entity_info.get("evasion", 0),
                    "FP": selected_entity_info.get("firepower", 0),
                    "RLD": selected_entity_info.get("reload", 0),
                }
            elif PortMenu.current_overlay == PortMenu.GEAR_LAB:
                entities = [weapon for weapon in weapon_data]
                selected_entity_reqs = weapon_data.get(PortMenu.overlay_selected_entity, {}).get("craft_reqs", {})
                selected_entity_info = weapon_data.get(PortMenu.overlay_selected_entity, {})
                selected_entity_info = {
                    "HULL": selected_entity_info.get("equippable_by", 0),
                    "FP": selected_entity_info.get("firepower", 0),
                    "RLD": selected_entity_info.get("reload", 0),
                    "SHELL": selected_entity_info.get("shell_type", 0),
                }
            else:
                entities = []
                selected_entity_reqs = {}
                selected_entity_info = {}
            
            for entity, rect in zip(entities, PortMenu.overlay_left_icons):
                pygame.draw.rect(surface, (255,255,255), rect, width=2)
                font.render(surface, entity, rect.center, (255,255,255), 1, style="center", outline_color=(10,10,10))
            if PortMenu.overlay_selected_entity:
                pygame.draw.rect(surface, (255,255,255), PortMenu.overlay_right_icon, width=2)
                font.render(surface, PortMenu.overlay_selected_entity, PortMenu.overlay_right_icon.center, (255,255,255), 1, style="center", outline_color=(10,10,10))
                for (ingredient, req), rect in zip(selected_entity_reqs.items(), PortMenu.overlay_ingredient_icons):
                    pygame.draw.rect(surface, (255,255,255), rect, width=2)
                    xy = (rect.centerx, rect.top+0.33*rect.height)
                    font.render(surface, ingredient, xy, (255,255,255), 1, style="center", outline_color=(10,10,10))
                    xy = (rect.centerx, rect.top+0.67*rect.height)
                    amt = save_file["inventory"].get(ingredient, 0)
                    font.render(surface, f"{amt}-{req}", xy, (255,255,255), 1, style="center", outline_color=(10,10,10))
                
                x = PortMenu.overlay_right_panel.left + 10
                y = PortMenu.overlay_right_icon.bottom + 10
                for i, (info_key, info_value) in enumerate(selected_entity_info.items()):
                    xy = (x, y + i*15)
                    info_name = Stats.STAT_NAMES.get(info_key, info_key)
                    font.render(surface, f"{info_name}: {info_value}", xy, (255,255,255), 1, style="topleft", outline_color=(10,10,10))

            PortMenu.overlay_confirm_button.draw(surface, font)
            # TODO write update logic for each overlay in a method
            # update the overlay enum to point to these methods for each overlay type

class SortieSelectionMenu:
    @staticmethod
    def start_sortie_factory(sortie_index):
        def start_sortie():
            Menus.current_menu = Menus.FLEET_SELECTION

            EncounterMenu.current_sortie = sortie_index
            EncounterMenu.current_encounter = 0

            player_fleet.clear_fleet()
            siren_fleet.clear_fleet()
        return start_sortie

    sortie_buttons = [
        Button(
            rect=get_rect(width=50, height=50, left=100, top=100),
            color=(100,100,150),
            text="0",
            text_color=(255,255,255),
            callback=start_sortie_factory(0)
        )
    ]

    @staticmethod
    def exit_sortie_selection_menu():
        Menus.current_menu = Menus.PORT

    exit_sortie_selection_menu_button = Button(
        rect=get_rect(width=100, height=50, right=TEMP_SCREEN_SIZE.x-EDGE_PADDING, top=EDGE_PADDING),
        color=(100,100,150),
        text="go back",
        text_color=(255,255,255),
        callback=exit_sortie_selection_menu
    )

    # TODO i want the overall style of the sortie selection menu
    # to feel like the OpSi menu where there are different zones that
    # are controlled / not controlled by the player and the player can
    # sortie into uncontrolled zone and by doing so they beat the level
    # i think the best way to do this in a structured way would be to use
    # some sort of grid-like system

    @staticmethod
    def update(dt, events):
        for event in events:
            if event.type == pygame.MOUSEBUTTONUP:
                SortieSelectionMenu.exit_sortie_selection_menu_button.click(event.pos)

                for sortie_button in SortieSelectionMenu.sortie_buttons:
                    sortie_button.click(event.pos)

    @staticmethod
    def draw(surface):
        SortieSelectionMenu.exit_sortie_selection_menu_button.draw(surface, font)

        for sortie_button in SortieSelectionMenu.sortie_buttons:
            sortie_button.draw(surface, font)

class FleetSelectionMenu:
    selected_shipgirl = None
    @staticmethod
    def start_encounter():
        if all(shipgirl is None for shipgirl in player_fleet.shipgirls):
            return
        Menus.current_menu = Menus.ENCOUNTER
        
        player_fleet.begin_sortie()

        EncounterMenu.begin_encounter()

    start_encounter_button = Button(
        rect=get_rect(width=100, height=50, centerx=0.75*TEMP_SCREEN_SIZE.x, bottom=BOTTOM_OF_SCREEN),
        color=(100,100,150),
        text="start",
        text_color=(255,255,255),
        callback=start_encounter
    )

    @staticmethod
    def exit_fleet_selection_menu():
        Menus.current_menu = Menus.SORTIE_SELECTION
    
    exit_fleet_selection_menu_button = Button(
        rect=get_rect(width=100, height=50, right=RIGHT_OF_SCREEN, top=TOP_OF_SCREEN),
        color=(100,100,150),
        text="go back",
        text_color=(255,255,255),
        callback=exit_fleet_selection_menu
    )

    @staticmethod
    def update(dt, events):
        global mouse_start_drag

        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN:
                for shipgirl, rect in zip(available_shipgirls, available_shipgirl_rects):
                    if rect.collidepoint(event.pos) and shipgirl.name not in player_fleet.shipgirl_names:
                        mouse_start_drag = event.pos
                        FleetSelectionMenu.selected_shipgirl = shipgirl
                        break
                else:
                    for shipgirl in player_fleet.shipgirls:
                        if shipgirl is not None and shipgirl.rect.collidepoint(event.pos):
                            mouse_start_drag = event.pos
                            FleetSelectionMenu.selected_shipgirl = shipgirl
                            break
                    else:
                        FleetSelectionMenu.selected_shipgirl = None
            if event.type == pygame.MOUSEBUTTONUP:
                mouse_end_drag = event.pos
                if mouse_start_drag is not None and FleetSelectionMenu.selected_shipgirl is not None:
                    for i, _ in enumerate(player_fleet.shipgirls):
                        x = 75*(1-i) + 0.25*TEMP_SCREEN_SIZE.x
                        rect = get_rect(width=50, height=50, centerx=x, centery=0.5*TEMP_SCREEN_SIZE.y)
                        if rect.collidepoint(mouse_end_drag):
                            for j, shipgirl in enumerate(player_fleet.shipgirls):
                                if FleetSelectionMenu.selected_shipgirl == shipgirl:
                                    player_fleet.shipgirls[j] = player_fleet.shipgirls[i]
                            player_fleet.shipgirls[i] = FleetSelectionMenu.selected_shipgirl
                            FleetSelectionMenu.selected_shipgirl.rect.center = pygame.Vector2(rect.center)
                            FleetSelectionMenu.selected_shipgirl = None
                mouse_start_drag = None
                FleetSelectionMenu.start_encounter_button.click(event.pos)
                FleetSelectionMenu.exit_fleet_selection_menu_button.click(event.pos)

    @staticmethod
    def draw(surface):
        player_fleet.draw(surface)
        FleetSelectionMenu.start_encounter_button.draw(surface, font)
        FleetSelectionMenu.exit_fleet_selection_menu_button.draw(surface, font)

        for shipgirl, rect in zip(available_shipgirls, available_shipgirl_rects):
            pygame.draw.rect(surface, (255,255,255), rect, width=2)
            font.render(surface, shipgirl.name, rect.center, (255,255,255), 1, style="center", outline_color=(10,10,10))

        for i, shipgirl in enumerate(player_fleet.shipgirls):
            if shipgirl is None:
                x = 75*(1-i) + 0.25*TEMP_SCREEN_SIZE.x
                rect = get_rect(width=50, height=50, centerx=x, centery=0.5*TEMP_SCREEN_SIZE.y)
                pygame.draw.rect(surface, (255,255,255), rect, width=2)
        
        mpos = pygame.mouse.get_pos()
        if mouse_start_drag is not None:
            pygame.draw.line(surface, (255,255,255), mouse_start_drag, mpos, width=2)

class EncounterMenu:
    current_sortie = 0
    current_encounter = 0
    selected_shipgirl = None
    @staticmethod
    def begin_encounter():
        siren_fleet_data = sorties[EncounterMenu.current_sortie][EncounterMenu.current_encounter]
        siren_fleet.shipgirls = [
            Shipgirl(siren_name) if siren_name else None
            for siren_name in siren_fleet_data
        ]
        for siren in siren_fleet.shipgirls:
            if siren is not None:
                siren.battle_component.target = player_fleet.front
        player_fleet.begin_encounter()
        siren_fleet.begin_encounter()

        EncounterMenu.next_encounter_button.active = False
        EncounterMenu.return_to_port_button.active = False
        EncounterMenu.retreat_button.active = True

    @staticmethod
    def next_encounter():
        EncounterMenu.current_encounter += 1
        EncounterMenu.begin_encounter()

        EncounterMenu.next_encounter_button.active = False

    next_encounter_button = Button(
        rect=get_rect(width=50, height=50, right=RIGHT_OF_SCREEN, centery=0.5*TEMP_SCREEN_SIZE.y),
        color=(100,100,150),
        text="next",
        text_color=(255,255,255),
        callback=next_encounter,
        active=False
    )

    def return_to_port():
        Menus.current_menu = Menus.PORT

        EncounterMenu.return_to_port_button.active = False

    return_to_port_button = Button(
        rect=get_rect(width=50, height=50, right=RIGHT_OF_SCREEN, centery=0.5*TEMP_SCREEN_SIZE.y),
        color=(100,100,150),
        text="back to port",
        text_color=(255,255,255),
        callback=return_to_port,
        active=False
    )

    @staticmethod
    def retreat():
        Menus.current_menu = Menus.PORT

        player_fleet.end_encounter()        
    
    retreat_button = Button(
        rect=get_rect(width=100, height=50, right=RIGHT_OF_SCREEN, top=TOP_OF_SCREEN),
        color=(100,100,150),
        text="retreat",
        text_color=(255,255,255),
        callback=retreat
    )

    end_encounter_rect = get_rect(width=10, height=10, centerx=0.5*TEMP_SCREEN_SIZE.x, centery=0.25*TEMP_SCREEN_SIZE.y)

    @staticmethod
    def update(dt, events):
        global mouse_start_drag

        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN:
                for shipgirl in player_fleet.shipgirls:
                    if shipgirl is not None and shipgirl.battle_component.active and shipgirl.rect.collidepoint(event.pos):
                        mouse_start_drag = event.pos
                        EncounterMenu.selected_shipgirl = shipgirl
                        EncounterMenu.selected_shipgirl.battle_component.target = None
            if event.type == pygame.MOUSEBUTTONUP:
                mouse_end_drag = event.pos
                if mouse_start_drag is not None and EncounterMenu.selected_shipgirl is not None:
                    for siren in siren_fleet.shipgirls:
                        if siren is not None and siren.rect.collidepoint(mouse_end_drag):
                            if EncounterMenu.selected_shipgirl.battle_component.hull_type in ["DD", "CL"]:
                                if siren == siren_fleet.front:
                                    EncounterMenu.selected_shipgirl.battle_component.target = siren
                            else:
                                EncounterMenu.selected_shipgirl.battle_component.target = siren
                            EncounterMenu.selected_shipgirl = None
                mouse_start_drag = None
                EncounterMenu.next_encounter_button.click(event.pos)
                EncounterMenu.return_to_port_button.click(event.pos)
                EncounterMenu.retreat_button.click(event.pos)
        
        player_fleet.update(dt)
        siren_fleet.update(dt)
        if not player_fleet.afloat or not siren_fleet.afloat:
            player_fleet.end_encounter()
            siren_fleet.end_encounter()
            if not player_fleet.afloat:
                EncounterMenu.return_to_port_button.active = True
            elif EncounterMenu.current_encounter+1 < len(sorties[EncounterMenu.current_sortie]):
                EncounterMenu.next_encounter_button.active = True
            else:
                EncounterMenu.return_to_port_button.active = True
            EncounterMenu.retreat_button.active = False

    @staticmethod
    def draw(surface):
        player_fleet.draw(surface)
        siren_fleet.draw(surface)
        EncounterMenu.next_encounter_button.draw(surface, font)
        EncounterMenu.return_to_port_button.draw(surface, font)
        EncounterMenu.retreat_button.draw(surface, font)
        
        if EncounterMenu.return_to_port_button.active:
            if not player_fleet.afloat:
                font.render(
                    surface,
                    "you lose",
                    EncounterMenu.end_encounter_rect.center,
                    (255,255,255),
                    1,
                    style="center",
                    outline_color=(10,10,10)
                )
            elif not siren_fleet.afloat:
                font.render(
                    surface,
                    "you win",
                    EncounterMenu.end_encounter_rect.center,
                    (255,255,255),
                    1,
                    style="center",
                    outline_color=(10,10,10)
                )

        mpos = pygame.mouse.get_pos()
        if mouse_start_drag is not None:
            pygame.draw.line(temp_screen, (255,255,255), mouse_start_drag, mpos, width=2)
            for siren in siren_fleet.shipgirls:
                if siren is not None and siren.rect.collidepoint(mpos):
                    if EncounterMenu.selected_shipgirl.battle_component.hull_type in ["DD", "CL"]:
                        # TODO magic numbers
                        if siren == siren_fleet.front:
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
    selected_shipgirl = None
    equipped_rects = [
        get_rect(width=50, height=50, centerx=(i-1)*75+0.75*TEMP_SCREEN_SIZE.x, centery=0.5*TEMP_SCREEN_SIZE.y)
        for i in range(Equipment.NUM_EQUIPS)
    ]
    selected_equipment = Equipment.WEAPON

    equippable_rects = [
        get_rect(width=50, height=50, centerx=(i%3-1)*75+0.75*TEMP_SCREEN_SIZE.x, centery=(i//3+1)*75+0.5*TEMP_SCREEN_SIZE.y)
        for i in range(6)
    ]
    hovered_equipment = None

    @staticmethod
    def exit_equipment_menu():
        Menus.current_menu = Menus.PORT

        EquipmentMenu.selected_shipgirl = None

    exit_equipment_menu_button = Button(
        rect=get_rect(width=100, height=50, right=RIGHT_OF_SCREEN, top=TOP_OF_SCREEN),
        color=(100,100,150),
        text="go back",
        text_color=(255,255,255),
        callback=exit_equipment_menu
    )

    stat_rects = [
        get_rect(width=10, height=10, centerx=0.25*TEMP_SCREEN_SIZE.x-25, centery=30+15*i+0.5*TEMP_SCREEN_SIZE.y)
        for i in range(Stats.NUM_STATS)
    ]

    @staticmethod
    def get_stat(shipgirl, stat):
        if stat == Stats.MAX_HP:
            if EquipmentMenu.hovered_equipment is None:
                return shipgirl.battle_component.max_hp()
            else:
                return shipgirl.battle_component.max_hp((EquipmentMenu.selected_equipment, EquipmentMenu.hovered_equipment))
        elif stat == Stats.EVASION:
            if EquipmentMenu.hovered_equipment is None:
                return shipgirl.battle_component.evasion()
            else:
                return shipgirl.battle_component.evasion((EquipmentMenu.selected_equipment, EquipmentMenu.hovered_equipment))
        elif stat == Stats.FIREPOWER:
            if EquipmentMenu.hovered_equipment is None:
                return shipgirl.battle_component.firepower()
            else:
                return shipgirl.battle_component.firepower((EquipmentMenu.selected_equipment, EquipmentMenu.hovered_equipment))
        elif stat == Stats.RELOAD:
            if EquipmentMenu.hovered_equipment is None:
                return shipgirl.battle_component.reload()
            else:
                return shipgirl.battle_component.reload((EquipmentMenu.selected_equipment, EquipmentMenu.hovered_equipment))

    @staticmethod
    def get_stat_delta(shipgirl, stat):
        if EquipmentMenu.hovered_equipment is None:
            return 0
        if stat == Stats.MAX_HP:
            return (
                shipgirl.battle_component.max_hp((EquipmentMenu.selected_equipment, EquipmentMenu.hovered_equipment))
                - shipgirl.battle_component.max_hp()
            )
        elif stat == Stats.EVASION:
            return (
                shipgirl.battle_component.evasion((EquipmentMenu.selected_equipment, EquipmentMenu.hovered_equipment))
                - shipgirl.battle_component.evasion()
            )
        elif stat == Stats.FIREPOWER:
            return (
                shipgirl.battle_component.firepower((EquipmentMenu.selected_equipment, EquipmentMenu.hovered_equipment))
                - shipgirl.battle_component.firepower()
            )
        elif stat == Stats.RELOAD:
            return (
                shipgirl.battle_component.reload((EquipmentMenu.selected_equipment, EquipmentMenu.hovered_equipment))
                - shipgirl.battle_component.reload()
            )

    @staticmethod
    def update(dt, events):
        if EquipmentMenu.selected_equipment == Equipment.WEAPON:
            equippable = [
                weapon_name for weapon_name, weapon_info in weapon_data.items()
                if weapon_info["equippable_by"] == EquipmentMenu.selected_shipgirl.battle_component.hull_type
                and save_file["weapons"].get(weapon_name, 0) > 0
            ]
        else:
            equippable = [
                aux_item_name for aux_item_name in auxiliary_item_data
                if save_file["aux_items"].get(aux_item_name, 0) > 0
            ]
        for event in events:
            if event.type == pygame.MOUSEBUTTONUP:
                for i, rect in enumerate(EquipmentMenu.equipped_rects):
                    if rect.collidepoint(event.pos):
                        EquipmentMenu.selected_equipment = i

                for equipment, rect in zip(equippable, EquipmentMenu.equippable_rects):
                    if rect.collidepoint(event.pos):
                        EquipmentMenu.selected_shipgirl.battle_component.equipment[EquipmentMenu.selected_equipment] = equipment
            
                EquipmentMenu.exit_equipment_menu_button.click(event.pos)
            if event.type == pygame.MOUSEMOTION:
                for equipment, rect in zip(equippable, EquipmentMenu.equippable_rects):
                    if rect.collidepoint(event.pos):
                        EquipmentMenu.hovered_equipment = equipment
                        break
                else:
                    EquipmentMenu.hovered_equipment = None
        
        if EquipmentMenu.selected_shipgirl is not None:
            EquipmentMenu.selected_shipgirl.rect.centerx = 0.25*TEMP_SCREEN_SIZE.x
            EquipmentMenu.selected_shipgirl.rect.centery = 0.5*TEMP_SCREEN_SIZE.y

    @staticmethod
    def draw(surface):
        if EquipmentMenu.selected_shipgirl is not None:
            # shipgirl chibi
            EquipmentMenu.selected_shipgirl.draw(surface)
            # shipgirl stats
            for stat, rect in enumerate(EquipmentMenu.stat_rects):
                font_rect = font.render(
                    surface,
                    f"{Stats.STAT_NAMES[stat]}: {EquipmentMenu.get_stat(EquipmentMenu.selected_shipgirl, stat)}",
                    rect.center,
                    (255,255,255),
                    1,
                    style="topleft",
                    outline_color=(10,10,10)
                )
                stat_delta = EquipmentMenu.get_stat_delta(EquipmentMenu.selected_shipgirl, stat)
                if stat_delta > 0:
                    center = pygame.Vector2(font_rect.left-10,font_rect.centery)
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
            for i, (equipment, rect) in enumerate(zip(EquipmentMenu.selected_shipgirl.battle_component.equipment, EquipmentMenu.equipped_rects)):
                if EquipmentMenu.selected_equipment == i:
                    pygame.draw.rect(surface, (255,255,255), rect, width=4)
                else:
                    pygame.draw.rect(surface, (255,255,255), rect, width=2)
                if equipment is not None:
                    _ = font.render(surface, equipment, rect.center, (255,255,255), 1, style="center", outline_color=(10,10,10))
            # equippable equipment
            if EquipmentMenu.selected_equipment == Equipment.WEAPON:
                equippable = [
                    weapon_name for weapon_name, weapon_info in weapon_data.items()
                    if weapon_info["equippable_by"] == EquipmentMenu.selected_shipgirl.battle_component.hull_type
                    and save_file["weapons"].get(weapon_name, 0) > 0
                ]
            else:
                equippable = [
                    aux_item_name for aux_item_name in auxiliary_item_data
                    if save_file["aux_items"].get(aux_item_name, 0) > 0
                ]
            for equipment, rect in zip(equippable, EquipmentMenu.equippable_rects):
                pygame.draw.rect(surface, (255,255,255), rect, width=2)
                _ = font.render(surface, equipment, rect.center, (255,255,255), 1, style="center", outline_color=(10,10,10))
        # exit button
        EquipmentMenu.exit_equipment_menu_button.draw(surface, font)

class Menus:
    PORT = PortMenu
    EQUIPMENT = EquipmentMenu

    SORTIE_SELECTION = SortieSelectionMenu
    FLEET_SELECTION = FleetSelectionMenu
    ENCOUNTER = EncounterMenu

    current_menu = PORT

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
    def __init__(self, name):
        self.active = False

        if name in shipgirl_data:
            info = shipgirl_data[name]
            info["equipment"] = save_file["shipgirls"][name]
        else:
            info = siren_data[name]

        self.base_max_hp = info["max_hp"]
        self.base_evasion = info["evasion"]
        self.base_firepower = info["firepower"]
        self.base_reload = info["reload"]
        self.hull_type = info["hull_type"]
        self.equipment = info["equipment"]

        self.hp = self.max_hp()
        self.cooldown_timer = 1
        self.target = None

    def max_hp(self, equipment_override=None):
        equipment = self.equipment.copy()
        if equipment_override is not None:
            equipment[equipment_override[0]] = equipment_override[1]
        return (
            self.base_max_hp
            + weapon_data.get(equipment[Equipment.WEAPON], {}).get("max_hp", 0)
            + auxiliary_item_data.get(equipment[Equipment.AUX1], {}).get("max_hp", 0)
            + auxiliary_item_data.get(equipment[Equipment.AUX2], {}).get("max_hp", 0)
        )

    def evasion(self, equipment_override=None):
        equipment = self.equipment.copy()
        if equipment_override is not None:
            equipment[equipment_override[0]] = equipment_override[1]
        return (
            self.base_evasion
            + weapon_data.get(equipment[Equipment.WEAPON], {}).get("evasion", 0)
            + auxiliary_item_data.get(equipment[Equipment.AUX1], {}).get("evasion", 0)
            + auxiliary_item_data.get(equipment[Equipment.AUX2], {}).get("evasion", 0)
        )

    def firepower(self, equipment_override=None):
        equipment = self.equipment.copy()
        if equipment_override is not None:
            equipment[equipment_override[0]] = equipment_override[1]
        return (
            self.base_firepower
            + weapon_data.get(equipment[Equipment.WEAPON], {}).get("firepower", 0)
            + auxiliary_item_data.get(equipment[Equipment.AUX1], {}).get("firepower", 0)
            + auxiliary_item_data.get(equipment[Equipment.AUX2], {}).get("firepower", 0)
        )

    def reload(self, equipment_override=None):
        equipment = self.equipment.copy()
        if equipment_override is not None:
            equipment[equipment_override[0]] = equipment_override[1]
        return (
            self.base_reload
            + weapon_data.get(equipment[Equipment.WEAPON], {}).get("reload", 0)
            + auxiliary_item_data.get(equipment[Equipment.AUX1], {}).get("reload", 0)
            + auxiliary_item_data.get(equipment[Equipment.AUX2], {}).get("reload", 0)
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
            evasion_roll = random.random() * 100
            if evasion_roll > self.target.battle_component.evasion():
                weapon = weapon_data.get(self.equipment[0], {}) if self.equipment[0] is not None else {}
                shell_type = weapon.get("shell_type", "normal")
                armor_type = Armor.HULL_TO_ARMOR_MAP[self.target.battle_component.hull_type]
                self.target.battle_component.hp -= self.firepower() * Armor.DAMAGE_MULTIPLIER[shell_type][armor_type]
            self.cooldown_timer = 1

    def draw(self, screen, rect):
        if not self.active:
            return
        
        bar_background = get_rect(width=100, height=10, centerx=rect.centerx, top=rect.bottom+20)
        bar_fill = get_rect(width=100*self.hp/self.max_hp(), height=10, left=bar_background.left, top=bar_background.top)
        pygame.draw.rect(screen, (50,50,50), bar_background)
        pygame.draw.rect(screen, (255,255,255), bar_fill)

        center = pygame.Vector2(rect.centerx, rect.top-50)
        radius = 30
        start_angle = -90
        end_angle = start_angle + 360 * (1 - self.cooldown_timer)
        color = (50,200,50) if self.target is not None else (200,50,50)
        draw_slice(screen, color, center, radius, start_angle, end_angle)
        pygame.draw.circle(screen, (255,255,255), center, radius, width=2)

class Shipgirl:
    def __init__(self, name):
        self.name = name
        self.sprite = None
    
        self.pos = pygame.Vector2(
            random.random() * TEMP_SCREEN_SIZE.x,
            random.random() * TEMP_SCREEN_SIZE.y
        )
        self.wander_target = self.pos.copy()
        self.pause_time = 0
        self.rect = get_rect(width=50, height=50, centerx=self.pos.x, centery=self.pos.y)

        self.battle_component = ShipgirlBattleComponent(self.name)

    def update(self, dt):
        if self.pause_time > 0:
            self.pause_time -= dt
        else:
            to_target = self.wander_target - self.pos
            if to_target.length() < 10:
                self.wander_target = pygame.Vector2(
                    random.random() * TEMP_SCREEN_SIZE.x,
                    random.random() * TEMP_SCREEN_SIZE.y
                )
                self.pause_time = random.uniform(1, 3)
            else:
                direction = to_target.normalize()
                self.pos += direction * 50 * dt
        self.rect.center = self.pos

    def draw(self, screen):
        if self.sprite:
            pass
        else:
            pygame.draw.rect(screen, (255,255,255), self.rect, width=2)
            _ = font.render(screen, self.name, self.rect.center, (255,255,255), 1, style="center", outline_color=(10,10,10))

        self.battle_component.draw(screen, self.rect)

class Fleet:
    def __init__(self, is_player):
        self.is_player = is_player
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
        for i, shipgirl in enumerate(self.shipgirls):
            if shipgirl is not None:
                if self.is_player:
                    shipgirl.rect.centerx = 0.25*TEMP_SCREEN_SIZE.x + (1-i)*75
                    shipgirl.rect.centery = 0.5*TEMP_SCREEN_SIZE.y
                else:
                    shipgirl.rect.centerx = 0.75*TEMP_SCREEN_SIZE.x + (i-1)*75
                    shipgirl.rect.centery = 0.5*TEMP_SCREEN_SIZE.y

                if shipgirl.battle_component.hp <= 0:
                    shipgirl.battle_component.active = False
                shipgirl.battle_component.update(dt)

    def draw(self, screen):
        for shipgirl in self.shipgirls:
            if shipgirl is not None:
                shipgirl.draw(screen)

available_shipgirls = [Shipgirl(shipgirl_name) for shipgirl_name in save_file["shipgirls"]]
available_shipgirl_rects = [
    get_rect(
        width=50,
        height=50,
        centerx=75*(i%4-1.5) + 0.75*TEMP_SCREEN_SIZE.x,
        centery=75*(i//4-1.5) + 0.5*TEMP_SCREEN_SIZE.y
    ) for i in range(4)
]
player_fleet = Fleet(True)

siren_fleet = Fleet(False)

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

    temp_screen.fill((20,20,50))
    Menus.current_menu.draw(temp_screen)
    screen.blit(pygame.transform.scale(temp_screen, screen.get_size()), (0,0))
    pygame.display.flip()

pygame.quit()

with open("data/save_file.json", "w") as f:
    json.dump(save_file, f)