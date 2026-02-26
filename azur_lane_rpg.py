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
    ENCOUNTER = 2

current_menu = Menus.PORT

EDGE_PADDING = 20

def open_build_menu():
    ...

open_build_menu_button = Button(
    get_rect(100, 50, centerx=0.25*TEMP_SCREEN_SIZE[0], bottom=TEMP_SCREEN_SIZE[1]-EDGE_PADDING),
    (100,100,150),
    "build",
    (255,255,255),
    open_build_menu
)

def start_sortie():
    global current_menu
    current_menu = Menus.ENCOUNTER

    global current_encounter
    current_encounter = -1

    next_encounter_button.active = False
    return_to_port_button.active = False

    player_fleet.begin_sortie()
    next_encounter()

sortie_button = Button(
    get_rect(100, 50, centerx=0.5*TEMP_SCREEN_SIZE[0], bottom=TEMP_SCREEN_SIZE[1]-EDGE_PADDING),
    (100,100,150),
    "sortie",
    (255,255,255),
    start_sortie
)

selected_shipgirl = None
def exit_equipment_menu():
    global current_menu
    current_menu = Menus.PORT

    global selected_shipgirl
    selected_shipgirl.pos.x = 0.5*TEMP_SCREEN_SIZE[0]
    selected_shipgirl.pos.y = 0.5*TEMP_SCREEN_SIZE[1]
    selected_shipgirl = None

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

current_sortie = 0
current_encounter = -1
def next_encounter():
    global current_encounter
    current_encounter += 1
    siren_fleet_data = sorties[current_sortie][current_encounter]
    siren_fleet.shipgirls = [
        Shipgirl(siren_name) if siren_name else None
        for siren_name in siren_fleet_data
    ]
    front_shipgirl = [shipgirl for shipgirl in player_fleet.shipgirls if shipgirl is not None][0]
    for siren in siren_fleet.shipgirls:
        if siren is not None:
            siren.battle_component.target = front_shipgirl
    player_fleet.begin_encounter()
    siren_fleet.begin_encounter()

    next_encounter_button.active = False

next_encounter_button = Button(
    get_rect(50, 50, right=TEMP_SCREEN_SIZE[0]-EDGE_PADDING, centery=0.5*TEMP_SCREEN_SIZE[1]),
    (100,100,150),
    "next",
    (255,255,255),
    next_encounter
)
next_encounter_button.active = False

def return_to_port():
    player_fleet.end_sortie()
    global current_menu
    current_menu = Menus.PORT

    return_to_port_button.active = False

return_to_port_button = Button(
    get_rect(50, 50, right=TEMP_SCREEN_SIZE[0]-EDGE_PADDING, centery=0.5*TEMP_SCREEN_SIZE[1]),
    (100,100,150),
    "back to port",
    (255,255,255),
    return_to_port
)
return_to_port_button.active = False

class ShipgirlBattleComponent:
    def __init__(self, shipgirl_data):
        self.active = False

        self.base_max_hp = shipgirl_data["max_hp"]
        self.base_evasion = shipgirl_data["evasion"]
        self.base_firepower = shipgirl_data["firepower"]
        self.base_reload = shipgirl_data["reload"]
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
                self.target.battle_component.hp -= self.firepower()
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

        self.battle_component.update(dt)

    def draw(self, screen):
        if self.sprite:
            pass
        else:
            pygame.draw.rect(screen, (255,255,255), self.rect, width=2)
            _ = font.render(screen, self.name, self.pos, (255,255,255), 1, style="center", outline_color=(10,10,10))

        self.battle_component.draw(screen, self.rect)

class Fleet:
    def __init__(self, is_player):
        self.is_player = is_player
        self.shipgirls = [None, None, None]
    
    def begin_sortie(self):
        for shipgirl in self.shipgirls:
            if shipgirl is not None:
                shipgirl.battle_component.reset()

    def begin_encounter(self):
        for i, shipgirl in enumerate(self.shipgirls):
            if shipgirl is not None:
                shipgirl.battle_component.active = True
                if self.is_player:
                    shipgirl.pos.x = 0.25*TEMP_SCREEN_SIZE[0] + (i-1)*75
                    shipgirl.pos.y = 0.5*TEMP_SCREEN_SIZE[1]
                else:
                    shipgirl.pos.x = 0.75*TEMP_SCREEN_SIZE[0] + (1-i)*75
                    shipgirl.pos.y = 0.5*TEMP_SCREEN_SIZE[1]

    def end_encounter(self):
        for shipgirl in self.shipgirls:
            if shipgirl is not None:
                shipgirl.battle_component.active = False

    def end_sortie(self):
        for shipgirl in self.shipgirls:
            if shipgirl is not None:
                shipgirl.pos.x = 0.5*TEMP_SCREEN_SIZE[0]
                shipgirl.pos.y = 0.5*TEMP_SCREEN_SIZE[1]

    def update(self, dt):
        for shipgirl in self.shipgirls:
            if shipgirl is not None:
                if shipgirl.battle_component.hp <= 0:
                    shipgirl.battle_component.active = False
                shipgirl.update(dt)

    def draw(self, screen):
        for shipgirl in self.shipgirls:
            if shipgirl is not None:
                shipgirl.draw(screen)

laffey = Shipgirl("laffey")
laffey.pos = pygame.Vector2(
    0.5*TEMP_SCREEN_SIZE[0],
    0.5*TEMP_SCREEN_SIZE[1]
)
player_fleet = Fleet(True)
player_fleet.shipgirls = [None, None, laffey]

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

    if current_menu == Menus.PORT:
        for event in events:
            if event.type == pygame.MOUSEBUTTONUP:
                if laffey.rect.collidepoint(event.pos):
                    selected_shipgirl = laffey
                    selected_shipgirl.pos.x = 0.25*TEMP_SCREEN_SIZE[0]
                    selected_shipgirl.pos.y = 0.5*TEMP_SCREEN_SIZE[1]
                    current_menu = Menus.EQUIPMENT

                sortie_button.click(event.pos)
        
        laffey.update(dt)
    elif current_menu == Menus.EQUIPMENT:
        for event in events:
            if event.type == pygame.MOUSEBUTTONUP:
                for i, rect in enumerate(equipped_rects):
                    if rect.collidepoint(event.pos):
                        selected_equipment = i

                if selected_equipment == Equipment.WEAPON:
                    equippable = weapon_data
                else:
                    equippable = auxiliary_item_data
                for equipment, rect in zip(equippable, equippable_rects):
                    if rect.collidepoint(event.pos):
                        selected_shipgirl.battle_component.equipment[selected_equipment] = equipment
            
                exit_equipment_menu_button.click(event.pos)
            if event.type == pygame.MOUSEMOTION:
                for equipment, rect in zip(equippable, equippable_rects):
                    if rect.collidepoint(event.pos):
                        hovered_equipment = equipment
                        break
                else:
                    hovered_equipment = None
        if selected_shipgirl is not None:
            selected_shipgirl.update(dt)
    elif current_menu == Menus.ENCOUNTER:
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN:
                if laffey.rect.collidepoint(event.pos):
                    mouse_start_drag = event.pos
                    laffey.battle_component.target = None
            if event.type == pygame.MOUSEBUTTONUP:
                mouse_end_drag = event.pos
                if mouse_start_drag is not None and laffey.rect.collidepoint(mouse_start_drag):
                    for siren in siren_fleet.shipgirls:
                        if siren is not None and  siren.rect.collidepoint(mouse_end_drag):
                            laffey.battle_component.target = siren
                mouse_start_drag = None

                next_encounter_button.click(event.pos)
                return_to_port_button.click(event.pos)
        
        player_fleet.update(dt)
        siren_fleet.update(dt)
        sirens_defeated = all(
            siren is None or siren.battle_component.hp <= 0
            for siren in siren_fleet.shipgirls
        )
        if sirens_defeated:
            player_fleet.end_encounter()
            if current_encounter+1 < len(sorties[current_sortie]):
                next_encounter_button.active = True
            else:
                return_to_port_button.active = True

    temp_screen.fill((20,20,50))
    if current_menu == Menus.PORT:
        laffey.draw(temp_screen)
        sortie_button.draw(temp_screen, font)
    elif current_menu == Menus.EQUIPMENT:
        if selected_shipgirl is not None:
            # shipgirl chibi
            selected_shipgirl.draw(temp_screen)
            # shipgirl stats
            for stat, rect in enumerate(stat_rects):
                if selected_equipment == Equipment.WEAPON:
                    preview_weapon = hovered_equipment
                else:
                    preview_weapon = None
                font_rect = font.render(
                    temp_screen,
                    str(get_stat(selected_shipgirl, stat)),
                    rect.center,
                    (255,255,255),
                    1,
                    style="topleft",
                    outline_color=(10,10,10)
                )
                stat_delta = get_stat_delta(selected_shipgirl, stat)
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
            for i, (equipment, rect) in enumerate(zip(selected_shipgirl.battle_component.equipment, equipped_rects)):
                if selected_equipment == i:
                    pygame.draw.rect(temp_screen, (255,255,255), rect, width=4)
                else:
                    pygame.draw.rect(temp_screen, (255,255,255), rect, width=2)
                if equipment is not None:
                    _ = font.render(temp_screen, equipment, rect.center, (255,255,255), 1, style="center", outline_color=(10,10,10))
            # equippable equipment
            if selected_equipment == Equipment.WEAPON:
                equippable = weapon_data
            else:
                equippable = auxiliary_item_data
            for equipment, rect in zip(equippable, equippable_rects):
                pygame.draw.rect(temp_screen, (255,255,255), rect, width=2)
                _ = font.render(temp_screen, equipment, rect.center, (255,255,255), 1, style="center", outline_color=(10,10,10))
        # exit button
        exit_equipment_menu_button.draw(temp_screen, font)
    elif current_menu == Menus.ENCOUNTER:
        player_fleet.draw(temp_screen)
        siren_fleet.draw(temp_screen)
        next_encounter_button.draw(temp_screen, font)
        return_to_port_button.draw(temp_screen, font)

        mpos = pygame.mouse.get_pos()
        if mouse_start_drag is not None:
            pygame.draw.line(temp_screen, (255,255,255), mouse_start_drag, mpos, width=2)
    screen.blit(pygame.transform.scale(temp_screen, screen.get_size()), (0,0))
    pygame.display.flip()

pygame.quit()