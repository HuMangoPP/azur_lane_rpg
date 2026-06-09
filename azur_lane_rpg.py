import pygame
import json

pygame.init()
SCREEN_SIZE = pygame.Vector2(1120, 630)
screen = pygame.display.set_mode(SCREEN_SIZE)

pygame.mixer.init()

from engine.font import Font

from src.constants import TEMP_SCREEN_SIZE, FPS, DataFiles
from src.menus.menu_manager import MenuManager

display = pygame.Surface(TEMP_SCREEN_SIZE)
clock = pygame.Clock()
font = Font(font_path="engine/big_font.png")

menu_manager = MenuManager()

# setup encounter immediately for testing
menu_manager.encounter_menu.current_sortie = 0
menu_manager.encounter_menu.current_encounter = 0
menu_manager.player_fleet.clear_fleet()
menu_manager.siren_fleet.clear_fleet()

menu_manager.current_menu = menu_manager.encounter_menu
menu_manager.player_fleet.shipgirls = [
    menu_manager.available_shipgirls[0],
    None,
    menu_manager.available_shipgirls[1]
]
for i, shipgirl in enumerate(menu_manager.player_fleet.shipgirls):
    if shipgirl is None:
        continue
    shipgirl.rect.center = menu_manager.fleet_selection_menu.fleet_slots[i].center
menu_manager.player_fleet.begin_sortie()
menu_manager.encounter_menu.begin_sortie()

DataFiles.bgm["lofi_loop"].play(loops=-1, fade_ms=10000)
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

    menu_manager.current_menu.update(dt, events)

    for quest in menu_manager.quest_manager.started_quests.values():
        quest.completed = quest.completed or quest.completion_criteria(menu_manager)

    display.fill((50,20,20)) # TODO
    menu_manager.current_menu.draw(display, font)
    for quest in menu_manager.quest_manager.started_quests.values():
        if quest.started and not quest.completed:
            quest.tutorial_draw(menu_manager, display, font)
    screen.blit(pygame.transform.scale(display, screen.get_size()), (0,0))
    pygame.display.flip()

DataFiles.bgm["lofi_loop"].stop()
pygame.quit()

for shipgirl in menu_manager.available_shipgirls:
    DataFiles.save_file["shipgirls"][shipgirl.name]["exp"] = shipgirl.battle_component.exp

save_file = input("Save file? ")
if save_file == "y":
    with open("data/save_file.json", "w") as f:
        json.dump(DataFiles.save_file, f, indent=4)