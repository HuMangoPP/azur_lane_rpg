import math
import json
import pygame
from engine.font import Font
from engine.button import Button
from engine.util import get_rect, draw_slice

with open("data/sorties.json") as f:
    sorties = json.load(f)

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
    ENCOUNTER = 1

current_menu = Menus.PORT

def start_sortie():
    global current_menu
    current_menu = Menus.ENCOUNTER

    global current_encounter
    current_encounter = -1

    next_encounter()

sortie_button = Button(
    get_rect(100, 50, centerx=0.5*TEMP_SCREEN_SIZE[0], bottom=TEMP_SCREEN_SIZE[1]-20),
    (100,100,150),
    "sortie",
    (255,255,255),
    start_sortie
)

current_sortie = 0
current_encounter = -1
def next_encounter():
    global current_encounter
    current_encounter += 1
    sortie_data = sorties[current_sortie]
    if current_encounter >= len(sortie_data):
        player_fleet.end_encounter()
        siren_fleet.end_encounter()
        global current_menu
        current_menu = Menus.PORT
    else:
        siren_fleet_data = sortie_data[current_encounter]
        siren_fleet.shipgirls = [
            Shipgirl(siren_name) if siren_name else None
            for siren_name in siren_fleet_data
        ]
        player_fleet.begin_encounter()
        siren_fleet.begin_encounter()

next_encounter_button = Button(
    get_rect(50, 50, right=TEMP_SCREEN_SIZE[0]-20, centery=0.5*TEMP_SCREEN_SIZE[1]),
    (100,100,150),
    "next",
    (255,255,255),
    next_encounter
)
next_encounter_button.active = False

SHIPGIRL_DATA = {
    "laffey": {
        "max_hp": 10,
        "weapon_cooldown": 3,
        "firepower": 1,
    },
    "siren": {
        "max_hp": 5,
        "weapon_cooldown": 5,
        "firepower": 1,
    },
}

class ShipgirlBattleComponent:
    def __init__(self, shipgirl_data):
        self.active = False

        self.max_hp = shipgirl_data["max_hp"]
        self.hp = self.max_hp

        self.weapon_cooldown = shipgirl_data["weapon_cooldown"]
        self.cooldown_timer = self.weapon_cooldown
        self.firepower = shipgirl_data["firepower"]
        self.target = None
    
    def reset(self):
        self.hp = self.max_hp
        self.cooldown_timer = self.weapon_cooldown

    def update(self, dt):
        if not self.active:
            return

        if self.hp <= 0:
            return

        if self.target is not None and self.target.battle_component.hp <= 0:
            self.target = None
        
        self.cooldown_timer = max(0, self.cooldown_timer - dt)
        if self.target is not None and self.cooldown_timer <= 0:
            self.target.battle_component.hp -= self.firepower
            self.cooldown_timer = self.weapon_cooldown

    def draw(self, screen, rect):
        if not self.active:
            return
        
        bar_background = get_rect(100, 10, centerx=rect.centerx, top=rect.bottom+20)
        bar_fill = get_rect(100*self.hp/self.max_hp, 10, left=bar_background.left, top=bar_background.top)
        pygame.draw.rect(screen, (50,50,50), bar_background)
        pygame.draw.rect(screen, (255,255,255), bar_fill)

        center = pygame.Vector2(rect.centerx, rect.top-50)
        radius = 30
        start_angle = -90
        end_angle = start_angle + 360 * (1 - self.cooldown_timer/self.weapon_cooldown)
        color = (50,200,50) if self.target is not None else (200,50,50)
        draw_slice(screen, color, center, radius, start_angle, end_angle)
        pygame.draw.circle(screen, (255,255,255), center, radius, width=2)


class Shipgirl:
    def __init__(self, name):
        self.name = name
        self.sprite = None
    
        self.pos = pygame.Vector2(0,0)
        self.rect = get_rect(50, 50, centerx=self.pos.x, centery=self.pos.y)

        self.battle_component = ShipgirlBattleComponent(SHIPGIRL_DATA[self.name])

    def update(self, dt):
        self.rect.center = self.pos

        self.battle_component.update(dt)

    def draw(self, screen):
        if self.sprite:
            pass
        else:
            pygame.draw.rect(screen, (255,255,255), self.rect, width=2)
            font.render(screen, self.name, self.pos, (255,255,255), 1, style="center", outline_color=(10,10,10))

        self.battle_component.draw(screen, self.rect)

class Fleet:
    def __init__(self, is_player):
        self.is_player = is_player
        self.shipgirls = [None, None, None]
    
    def begin_encounter(self):
        for i, shipgirl in enumerate(self.shipgirls):
            if shipgirl is not None:
                if self.is_player:
                    shipgirl.pos.x = 0.25*TEMP_SCREEN_SIZE[0] + (i-1)*75
                    shipgirl.pos.y = 0.5*TEMP_SCREEN_SIZE[1]
                else:
                    shipgirl.pos.x = 0.75*TEMP_SCREEN_SIZE[0] + (1-i)*75
                    shipgirl.pos.y = 0.5*TEMP_SCREEN_SIZE[1]
                shipgirl.battle_component.active = True
                shipgirl.battle_component.reset()

    def end_encounter(self):
        for shipgirl in self.shipgirls:
            if shipgirl is not None:
                if self.is_player:
                    shipgirl.pos.x = 0.5*TEMP_SCREEN_SIZE[0]
                shipgirl.battle_component.active = False

    def update(self, dt):
        for shipgirl in self.shipgirls:
            if shipgirl is not None:
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
                sortie_button.click(event.pos)
        
        laffey.update(dt)
    elif current_menu == Menus.ENCOUNTER:
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_start_drag = event.pos
            if event.type == pygame.MOUSEBUTTONUP:
                mouse_end_drag = event.pos
                if mouse_start_drag is not None and laffey.rect.collidepoint(mouse_start_drag):
                    for siren in siren_fleet.shipgirls:
                        if siren is not None and  siren.rect.collidepoint(mouse_end_drag):
                            laffey.battle_component.target = siren
                            break
                    else:
                        laffey.battle_component.target = None
                mouse_start_drag = None

                next_encounter_button.click(event.pos)
        
        player_fleet.update(dt)
        siren_fleet.update(dt)
        sirens_defeated = all(
            siren is None or siren.battle_component.hp <= 0
            for siren in siren_fleet.shipgirls
        )
        if sirens_defeated:
            next_encounter_button.active = True

    temp_screen.fill((20,20,50))
    if current_menu == Menus.PORT:
        laffey.draw(temp_screen)
        sortie_button.draw(temp_screen, font)
    elif current_menu == Menus.ENCOUNTER:
        player_fleet.draw(temp_screen)
        siren_fleet.draw(temp_screen)
        next_encounter_button.draw(temp_screen, font)

        mpos = pygame.mouse.get_pos()
        if mouse_start_drag is not None:
            pygame.draw.line(temp_screen, (255,255,255), mouse_start_drag, mpos, width=2)
    screen.blit(pygame.transform.scale(temp_screen, screen.get_size()), (0,0))
    pygame.display.flip()

pygame.quit()