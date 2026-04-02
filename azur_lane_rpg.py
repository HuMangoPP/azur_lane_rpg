import pygame

pygame.init()
SCREEN_SIZE = pygame.Vector2(1120, 630)
screen = pygame.display.set_mode(SCREEN_SIZE)

from engine.font import Font
from engine.util import get_rect

from src.constants import TEMP_SCREEN_SIZE, FPS, DataFiles, Box, screen_x, screen_y
from src.menus import Menus
from src.shipgirls import Shipgirl, PlayerFleet, SirenFleet

temp_screen = pygame.Surface(TEMP_SCREEN_SIZE)
clock = pygame.Clock()
font = Font(font_path="engine/big_font.png")

mouse_start_drag = None

available_shipgirls = [Shipgirl(shipgirl_name, True) for shipgirl_name in DataFiles.save_file["shipgirls"]]
available_shipgirl_rects = [
    get_rect( # TODO
        width=Box.WIDTH, height=Box.HEIGHT,
        centerx=(Box.WIDTH+Box.PADDING)*(i%4-1.5) + screen_x(0.75),
        centery=(Box.HEIGHT+Box.PADDING)*(i//4-1.5) + screen_y(0.5)
    ) for i in range(4)
]
player_fleet = PlayerFleet()
siren_fleet = SirenFleet()

running = True
while running:
    clock.tick(FPS)
    dt = clock.get_time() / 1000
    pygame.display.set_caption(f"{clock.get_fps()}")

    events = pygame.event.get()
    for event in events:
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            running = False
    
    tutorial = Menus.tutorial
    if tutorial is not None:
        events = [
            event for event in events
            if event.type != pygame.MOUSEBUTTONUP
            or tutorial.check_completion({"mouseup": event.pos})
        ]

    Menus.current_menu.update(dt, events)

    if tutorial is not None:
        if tutorial.completed:
            tutorial.on_complete()

    temp_screen.fill((50,20,20)) # TODO
    Menus.current_menu.draw(temp_screen, font)
    screen.blit(pygame.transform.scale(temp_screen, screen.get_size()), (0,0))
    pygame.display.flip()

pygame.quit()

for shipgirl in available_shipgirls:
    DataFiles.save_file["shipgirls"][shipgirl.name]["exp"] = shipgirl.battle_component.exp

# with open("data/save_file.json", "w") as f:
#     json.dump(save_file, f, indent=4)