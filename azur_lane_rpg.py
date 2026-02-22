import math
import pygame
from engine.font import Font
from engine.button import Button
from engine.util import get_rect, draw_slice

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

    laffey.pos = pygame.Vector2(
        0.25*TEMP_SCREEN_SIZE[0],
        0.5*TEMP_SCREEN_SIZE[1]
    )
    laffey.battle_component.active = True
    siren.battle_component.active = True
    siren.battle_component.target = laffey

sortie_button = Button(
    get_rect(100, 50, centerx=0.5*TEMP_SCREEN_SIZE[0], bottom=TEMP_SCREEN_SIZE[1]-20),
    (100,100,150),
    "sortie",
    (255,255,255),
    start_sortie
)

num_encounters = 3
def next_encounter():
    global num_encounters
    num_encounters -= 1

    if num_encounters > 0:
        laffey.battle_component.reset()
        siren.battle_component.reset()
    else:
        laffey.pos = pygame.Vector2(
            0.5*TEMP_SCREEN_SIZE[0],
            0.5*TEMP_SCREEN_SIZE[1]
        )
        laffey.battle_component.active = False
        siren.battle_component.active = False
        global current_menu
        current_menu = Menus.PORT

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

laffey = Shipgirl("laffey")
laffey.pos = pygame.Vector2(
    0.5*TEMP_SCREEN_SIZE[0],
    0.5*TEMP_SCREEN_SIZE[1]
)
siren = Shipgirl("siren")
siren.pos = pygame.Vector2(
    0.75*TEMP_SCREEN_SIZE[0],
    0.5*TEMP_SCREEN_SIZE[1]
)

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
                    if siren.rect.collidepoint(mouse_end_drag):
                        laffey.battle_component.target = siren
                    else:
                        laffey.battle_component.target = None
                mouse_start_drag = None

                next_encounter_button.click(event.pos)
        
        laffey.update(dt)
        siren.update(dt)
        if siren.battle_component.hp <= 0:
            next_encounter_button.active = True

    temp_screen.fill((20,20,50))
    if current_menu == Menus.PORT:
        laffey.draw(temp_screen)
        sortie_button.draw(temp_screen, font)
    elif current_menu == Menus.ENCOUNTER:
        laffey.draw(temp_screen)
        siren.draw(temp_screen)
        next_encounter_button.draw(temp_screen, font)

        mpos = pygame.mouse.get_pos()
        if mouse_start_drag is not None:
            pygame.draw.line(temp_screen, (255,255,255), mouse_start_drag, mpos, width=2)
    screen.blit(pygame.transform.scale(temp_screen, screen.get_size()), (0,0))
    pygame.display.flip()

pygame.quit()