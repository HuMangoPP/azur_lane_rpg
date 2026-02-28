import math
import random
import json
import pygame
from engine.font import Font
from engine.button import Button
from engine.util import get_rect, get_vec, draw_slice

with open("data/sorties.json") as f:
    sorties = json.load(f)

with open("data/shipgirls.json") as f:
    shipgirl_data = json.load(f)

with open("data/weapons.json") as f:
    weapon_data = json.load(f)

with open("data/auxiliary_items.json") as f:
    auxiliary_item_data = json.load(f)

pygame.init()

SCREEN_SIZE = (600,600)
TEMP_SCREEN_SIZE = (600,600)
screen = pygame.display.set_mode(SCREEN_SIZE)
temp_screen = pygame.Surface(TEMP_SCREEN_SIZE)
clock = pygame.Clock()
font = Font("engine/big_font.png")

mouse_start_drag = None

class Menus:
    PORT = 0
    EQUIPMENT = 1

    SORTIE_SELECTION = 10
    FLEET_SELECTION = 11
    ENCOUNTER = 12

    current_menu = PORT

EDGE_PADDING = 20

class PortMenu:
    @staticmethod
    def open_build_menu():
        pass

    open_build_menu_button = Button(
        get_rect(100, 50, centerx=0.25*TEMP_SCREEN_SIZE[0], bottom=TEMP_SCREEN_SIZE[1]-EDGE_PADDING),
        (100,100,150),
        "build",
        (255,255,255),
        open_build_menu
    )

    @staticmethod
    def open_select_sortie_menu():
        Menus.current_menu = Menus.SORTIE_SELECTION

    open_select_sortie_menu_button = Button(
        get_rect(100, 50, centerx=0.5*TEMP_SCREEN_SIZE[0], bottom=TEMP_SCREEN_SIZE[1]-EDGE_PADDING),
        (100,100,150),
        "sortie",
        (255,255,255),
        open_select_sortie_menu
    )

class SortieSelectionMenu:
    @staticmethod
    def start_sortie_factory(sortie_index):
        def start_sortie():
            Menus.current_menu = Menus.FLEET_SELECTION

            EncounterMenu.current_sortie = sortie_index
            EncounterMenu.current_encounter = 0

            EncounterMenu.next_encounter_button.active = False
            EncounterMenu.return_to_port_button.active = False

            player_fleet.clear_fleet()
            siren_fleet.clear_fleet()
        return start_sortie

    sortie_buttons = [
        Button(
            get_rect(50, 50, left=100, top=100),
            (100,100,150),
            "0",
            (255,255,255),
            start_sortie_factory(0)
        )
    ]

    @staticmethod
    def exit_sortie_selection_menu():
        Menus.current_menu = Menus.PORT

    exit_sortie_selection_menu_button = Button(
        get_rect(100, 50, right=TEMP_SCREEN_SIZE[0]-EDGE_PADDING, top=EDGE_PADDING),
        (100,100,150),
        "go back",
        (255,255,255),
        exit_sortie_selection_menu
    )

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
        get_rect(100, 50, centerx=0.75*TEMP_SCREEN_SIZE[0], bottom=TEMP_SCREEN_SIZE[1]-EDGE_PADDING),
        (100,100,150),
        "start",
        (255,255,255),
        start_encounter
    )

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

    @staticmethod
    def next_encounter():
        EncounterMenu.current_encounter += 1
        EncounterMenu.begin_encounter()

        EncounterMenu.next_encounter_button.active = False

    next_encounter_button = Button(
        get_rect(50, 50, right=TEMP_SCREEN_SIZE[0]-EDGE_PADDING, centery=0.5*TEMP_SCREEN_SIZE[1]),
        (100,100,150),
        "next",
        (255,255,255),
        next_encounter,
        active=False
    )

    def return_to_port():
        Menus.current_menu = Menus.PORT

        EncounterMenu.return_to_port_button.active = False

    return_to_port_button = Button(
        get_rect(50, 50, right=TEMP_SCREEN_SIZE[0]-EDGE_PADDING, centery=0.5*TEMP_SCREEN_SIZE[1]),
        (100,100,150),
        "back to port",
        (255,255,255),
        return_to_port,
        active=False
    )

    end_encounter_rect = get_rect(10, 10, centerx=0.5*TEMP_SCREEN_SIZE[0], centery=0.25*TEMP_SCREEN_SIZE[1])

class EquipmentMenu:
    selected_shipgirl = None

    @staticmethod
    def exit_equipment_menu():
        Menus.current_menu = Menus.PORT

        EquipmentMenu.selected_shipgirl = None

    exit_equipment_menu_button = Button(
        get_rect(100, 50, right=TEMP_SCREEN_SIZE[0]-EDGE_PADDING, top=EDGE_PADDING),
        (100,100,150),
        "go back",
        (255,255,255),
        exit_equipment_menu
    )

class Equipment:
    NUM_EQUIPS = 3
    WEAPON = 0
    AUX1 = 1
    AUX2 = 2

equipped_rects = [
    get_rect(50, 50, centerx=(i-1)*75+0.75*TEMP_SCREEN_SIZE[0], centery=0.5*TEMP_SCREEN_SIZE[1])
    for i in range(Equipment.NUM_EQUIPS)
]
selected_equipment = Equipment.WEAPON

equippable_rects = [
    get_rect(
        50, 50,
        centerx=(i%3-1)*75+0.75*TEMP_SCREEN_SIZE[0],
        centery=(i//3+1)*75+0.5*TEMP_SCREEN_SIZE[1]
    )
    for i in range(6)
]
hovered_equipment = None

class Stats:
    NUM_STATS = 4
    MAX_HP = 0
    EVASION = 1
    FIREPOWER = 2
    RELOAD = 3

stat_rects = [
    get_rect(
        10, 10,
        centerx=0.25*TEMP_SCREEN_SIZE[0]-25, centery=30+15*i+0.5*TEMP_SCREEN_SIZE[1]
    )
    for i in range(Stats.NUM_STATS)
]

def get_stat(shipgirl, stat):
    if stat == Stats.MAX_HP:
        if hovered_equipment is None:
            return shipgirl.battle_component.max_hp()
        else:
            return shipgirl.battle_component.max_hp((selected_equipment, hovered_equipment))
    elif stat == Stats.EVASION:
        if hovered_equipment is None:
            return shipgirl.battle_component.evasion()
        else:
            return shipgirl.battle_component.evasion((selected_equipment, hovered_equipment))
    elif stat == Stats.FIREPOWER:
        if hovered_equipment is None:
            return shipgirl.battle_component.firepower()
        else:
            return shipgirl.battle_component.firepower((selected_equipment, hovered_equipment))
    elif stat == Stats.RELOAD:
        if hovered_equipment is None:
            return shipgirl.battle_component.reload()
        else:
            return shipgirl.battle_component.reload((selected_equipment, hovered_equipment))

def get_stat_delta(shipgirl, stat):
    if hovered_equipment is None:
        return 0
    if stat == Stats.MAX_HP:
        return (
            shipgirl.battle_component.max_hp((selected_equipment, hovered_equipment))
            - shipgirl.battle_component.max_hp()
        )
    elif stat == Stats.EVASION:
        return (
            shipgirl.battle_component.evasion((selected_equipment, hovered_equipment))
            - shipgirl.battle_component.evasion()
        )
    elif stat == Stats.FIREPOWER:
        return (
            shipgirl.battle_component.firepower((selected_equipment, hovered_equipment))
            - shipgirl.battle_component.firepower()
        )
    elif stat == Stats.RELOAD:
        return (
            shipgirl.battle_component.reload((selected_equipment, hovered_equipment))
            - shipgirl.battle_component.reload()
        )

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
    def __init__(self, shipgirl_data):
        self.active = False

        self.base_max_hp = shipgirl_data["max_hp"]
        self.base_evasion = shipgirl_data["evasion"]
        self.base_firepower = shipgirl_data["firepower"]
        self.base_reload = shipgirl_data["reload"]
        self.hull_type = shipgirl_data["hull_type"]
        self.equipment = shipgirl_data["equipment"]

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
        
        bar_background = get_rect(100, 10, centerx=rect.centerx, top=rect.bottom+20)
        bar_fill = get_rect(100*self.hp/self.max_hp(), 10, left=bar_background.left, top=bar_background.top)
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
    
        self.pos = pygame.Vector2(0,0)
        self.rect = get_rect(50, 50, centerx=self.pos.x, centery=self.pos.y)

        self.battle_component = ShipgirlBattleComponent(shipgirl_data[self.name])

    def update(self, dt):
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
                shipgirl.battle_component.active = False

    def update(self, dt):
        for i, shipgirl in enumerate(self.shipgirls):
            if shipgirl is not None:
                if self.is_player:
                    shipgirl.rect.centerx = 0.25*TEMP_SCREEN_SIZE[0] + (1-i)*75
                    shipgirl.rect.centery = 0.5*TEMP_SCREEN_SIZE[1]
                else:
                    shipgirl.rect.centerx = 0.75*TEMP_SCREEN_SIZE[0] + (i-1)*75
                    shipgirl.rect.centery = 0.5*TEMP_SCREEN_SIZE[1]

                if shipgirl.battle_component.hp <= 0:
                    shipgirl.battle_component.active = False
                shipgirl.battle_component.update(dt)

    def draw(self, screen):
        for shipgirl in self.shipgirls:
            if shipgirl is not None:
                shipgirl.draw(screen)

laffey = Shipgirl("laffey")
laffey.pos = pygame.Vector2(
    0.25*TEMP_SCREEN_SIZE[0],
    0.25*TEMP_SCREEN_SIZE[1]
)
san_diego = Shipgirl("san_diego")
san_diego.pos = pygame.Vector2(
    0.75*TEMP_SCREEN_SIZE[0],
    0.25*TEMP_SCREEN_SIZE[1]
)
guam = Shipgirl("guam")
guam.pos = pygame.Vector2(
    0.25*TEMP_SCREEN_SIZE[0],
    0.75*TEMP_SCREEN_SIZE[1]
)
new_jersey = Shipgirl("new_jersey")
new_jersey.pos = pygame.Vector2(
    0.75*TEMP_SCREEN_SIZE[0],
    0.75*TEMP_SCREEN_SIZE[1]
)
available_shipgirls = [laffey, san_diego, guam, new_jersey]
available_shipgirl_rects = [
    get_rect(
        width=50,
        height=50,
        centerx=75*(i%4-1.5) + 0.75*TEMP_SCREEN_SIZE[0],
        centery=75*(i//4-1.5) + 0.5*TEMP_SCREEN_SIZE[1]
    ) for i in range(4)
]
player_fleet = Fleet(True)

siren_fleet = Fleet(False)

running = True
while running:
    clock.tick()
    dt = clock.get_time() / 1000

    events = pygame.event.get()
    for event in events:
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            running = False

    if Menus.current_menu == Menus.PORT:
        for event in events:
            if event.type == pygame.MOUSEBUTTONUP:
                for shipgirl in available_shipgirls:
                    if shipgirl.rect.collidepoint(event.pos):
                        EquipmentMenu.selected_shipgirl = shipgirl
                        Menus.current_menu = Menus.EQUIPMENT

                PortMenu.open_select_sortie_menu_button.click(event.pos)
        
        for shipgirl in available_shipgirls:
            shipgirl.update(dt)
    elif Menus.current_menu == Menus.EQUIPMENT:
        if selected_equipment == Equipment.WEAPON:
            equippable = [
                weapon_name for weapon_name, weapon_info in weapon_data.items()
                if weapon_info["equippable_by"] == EquipmentMenu.selected_shipgirl.battle_component.hull_type
            ]
        else:
            equippable = auxiliary_item_data
        for event in events:
            if event.type == pygame.MOUSEBUTTONUP:
                for i, rect in enumerate(equipped_rects):
                    if rect.collidepoint(event.pos):
                        selected_equipment = i

                for equipment, rect in zip(equippable, equippable_rects):
                    if rect.collidepoint(event.pos):
                        EquipmentMenu.selected_shipgirl.battle_component.equipment[selected_equipment] = equipment
            
                EquipmentMenu.exit_equipment_menu_button.click(event.pos)
            if event.type == pygame.MOUSEMOTION:
                for equipment, rect in zip(equippable, equippable_rects):
                    if rect.collidepoint(event.pos):
                        hovered_equipment = equipment
                        break
                else:
                    hovered_equipment = None
        
        if EquipmentMenu.selected_shipgirl is not None:
            EquipmentMenu.selected_shipgirl.rect.centerx = 0.25*TEMP_SCREEN_SIZE[0]
            EquipmentMenu.selected_shipgirl.rect.centery = 0.5*TEMP_SCREEN_SIZE[1]
    elif Menus.current_menu == Menus.SORTIE_SELECTION:
        for event in events:
            if event.type == pygame.MOUSEBUTTONUP:
                SortieSelectionMenu.exit_sortie_selection_menu_button.click(event.pos)

                for sortie_button in SortieSelectionMenu.sortie_buttons:
                    sortie_button.click(event.pos)
    elif Menus.current_menu == Menus.FLEET_SELECTION:
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
                        x = 75*(1-i) + 0.25*TEMP_SCREEN_SIZE[0]
                        rect = get_rect(width=50, height=50, centerx=x, centery=0.5*TEMP_SCREEN_SIZE[1])
                        if rect.collidepoint(mouse_end_drag):
                            for j, shipgirl in enumerate(player_fleet.shipgirls):
                                if FleetSelectionMenu.selected_shipgirl == shipgirl:
                                    player_fleet.shipgirls[j] = player_fleet.shipgirls[i]
                            player_fleet.shipgirls[i] = FleetSelectionMenu.selected_shipgirl
                            FleetSelectionMenu.selected_shipgirl.rect.center = pygame.Vector2(rect.center)
                            FleetSelectionMenu.selected_shipgirl = None
                mouse_start_drag = None
                FleetSelectionMenu.start_encounter_button.click(event.pos)
    elif Menus.current_menu == Menus.ENCOUNTER:
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

    temp_screen.fill((20,20,50))
    if Menus.current_menu == Menus.PORT:
        for shipgirl in available_shipgirls:
            shipgirl.draw(temp_screen)
        PortMenu.open_select_sortie_menu_button.draw(temp_screen, font)
    elif Menus.current_menu == Menus.EQUIPMENT:
        if EquipmentMenu.selected_shipgirl is not None:
            # shipgirl chibi
            EquipmentMenu.selected_shipgirl.draw(temp_screen)
            # shipgirl stats
            for stat, rect in enumerate(stat_rects):
                if selected_equipment == Equipment.WEAPON:
                    preview_weapon = hovered_equipment
                else:
                    preview_weapon = None
                font_rect = font.render(
                    temp_screen,
                    str(get_stat(EquipmentMenu.selected_shipgirl, stat)),
                    rect.center,
                    (255,255,255),
                    1,
                    style="topleft",
                    outline_color=(10,10,10)
                )
                stat_delta = get_stat_delta(EquipmentMenu.selected_shipgirl, stat)
                if stat_delta > 0:
                    center = pygame.Vector2(font_rect.left-10,font_rect.centery)
                    pygame.draw.polygon(temp_screen, (0,255,0),[
                        center+get_vec(5, math.radians(30)),
                        center+get_vec(5, math.radians(150)),
                        center+get_vec(5, math.radians(270))
                    ])
                elif stat_delta < 0:
                    center = pygame.Vector2(font_rect.left-10,font_rect.centery)
                    pygame.draw.polygon(temp_screen, (255,0,0),[
                        center+get_vec(5, math.radians(90)),
                        center+get_vec(5, math.radians(210)),
                        center+get_vec(5, math.radians(330))
                    ])
            # shipgirl equipment
            for i, (equipment, rect) in enumerate(zip(EquipmentMenu.selected_shipgirl.battle_component.equipment, equipped_rects)):
                if selected_equipment == i:
                    pygame.draw.rect(temp_screen, (255,255,255), rect, width=4)
                else:
                    pygame.draw.rect(temp_screen, (255,255,255), rect, width=2)
                if equipment is not None:
                    _ = font.render(temp_screen, equipment, rect.center, (255,255,255), 1, style="center", outline_color=(10,10,10))
            # equippable equipment
            if selected_equipment == Equipment.WEAPON:
                equippable = [
                    weapon_name for weapon_name, weapon_info in weapon_data.items()
                    if weapon_info["equippable_by"] == EquipmentMenu.selected_shipgirl.battle_component.hull_type
                ]
            else:
                equippable = auxiliary_item_data
            for equipment, rect in zip(equippable, equippable_rects):
                pygame.draw.rect(temp_screen, (255,255,255), rect, width=2)
                _ = font.render(temp_screen, equipment, rect.center, (255,255,255), 1, style="center", outline_color=(10,10,10))
        # exit button
        EquipmentMenu.exit_equipment_menu_button.draw(temp_screen, font)
    elif Menus.current_menu == Menus.SORTIE_SELECTION:
        SortieSelectionMenu.exit_sortie_selection_menu_button.draw(temp_screen, font)

        for sortie_button in SortieSelectionMenu.sortie_buttons:
            sortie_button.draw(temp_screen, font)
    elif Menus.current_menu == Menus.FLEET_SELECTION:
        player_fleet.draw(temp_screen)
        FleetSelectionMenu.start_encounter_button.draw(temp_screen, font)

        for shipgirl, rect in zip(available_shipgirls, available_shipgirl_rects):
            pygame.draw.rect(temp_screen, (255,255,255), rect, width=2)
            font.render(temp_screen, shipgirl.name, rect.center, (255,255,255), 1, style="center", outline_color=(10,10,10))

        for i, shipgirl in enumerate(player_fleet.shipgirls):
            if shipgirl is None:
                x = 75*(1-i) + 0.25*TEMP_SCREEN_SIZE[0]
                rect = get_rect(width=50, height=50, centerx=x, centery=0.5*TEMP_SCREEN_SIZE[1])
                pygame.draw.rect(temp_screen, (255,255,255), rect, width=2)
        
        mpos = pygame.mouse.get_pos()
        if mouse_start_drag is not None:
            pygame.draw.line(temp_screen, (255,255,255), mouse_start_drag, mpos, width=2)
    elif Menus.current_menu == Menus.ENCOUNTER:
        player_fleet.draw(temp_screen)
        siren_fleet.draw(temp_screen)
        EncounterMenu.next_encounter_button.draw(temp_screen, font)
        EncounterMenu.return_to_port_button.draw(temp_screen, font)
        
        if EncounterMenu.return_to_port_button.active:
            if not player_fleet.afloat:
                font.render(
                    temp_screen,
                    "you lose",
                    EncounterMenu.end_encounter_rect.center,
                    (255,255,255),
                    1,
                    style="center",
                    outline_color=(10,10,10)
                )
            elif not siren_fleet.afloat:
                font.render(
                    temp_screen,
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
                        if siren == siren_fleet.front:
                            pygame.draw.circle(temp_screen, (50,200,50), pygame.Vector2(mpos) + pygame.Vector2(30, 30), 25)
                        else:
                            pygame.draw.circle(temp_screen, (200,50,50), pygame.Vector2(mpos) + pygame.Vector2(30, 30), 25)
                    else:
                        pygame.draw.circle(temp_screen, (50,200,50), pygame.Vector2(mpos) + pygame.Vector2(30, 30), 25)
    screen.blit(pygame.transform.scale(temp_screen, screen.get_size()), (0,0))
    pygame.display.flip()

pygame.quit()