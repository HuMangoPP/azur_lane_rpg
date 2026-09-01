from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from engine.types import CoordinateType

import pygame
import json

if __name__ == "__main__":
    pygame.init()
    # SCREEN_SIZE = pygame.Vector2(1920, 1080)
    SCREEN_SIZE = pygame.Vector2(960, 540)
    screen = pygame.display.set_mode(SCREEN_SIZE)

    pygame.mixer.init()

    from engine.font import Font

    from src.constants import TEMP_SCREEN_SIZE, FPS, DataFiles, Color
    from src.menus.menu_manager import MenuManager

    # Rendering will be done on this display, then scaled up to the window display.
    display = pygame.Surface(TEMP_SCREEN_SIZE)

    # Monkeypatch pygame.mouse.get_pos() to map from true screen space to temp surface space.
    mouse_scale = (
        TEMP_SCREEN_SIZE.x / SCREEN_SIZE.x,
        TEMP_SCREEN_SIZE.y / SCREEN_SIZE.y,
    )

    get_physical_mouse_pos = pygame.mouse.get_pos

    def _get_scaled_mouse_pos() -> CoordinateType:
        """Get the mouse cursor position in the actual game screen space.

        Monkeypatch of pygame.mouse.get_pos(), which scales the true mouse position
        on screen so that it lives in the actual game screen space.
        """
        mouse_pos = get_physical_mouse_pos()
        return (
            mouse_pos[0] * mouse_scale[0],
            mouse_pos[1] * mouse_scale[1],
        )

    pygame.mouse.get_pos = _get_scaled_mouse_pos

    clock = pygame.Clock()

    with open("engine/fonts.json") as f:
        fonts = json.load(f)
        font_registry = {
            font: Font(font, charset)
            for font, charset in fonts.items()
        }

    menu_manager = MenuManager()

    DataFiles.bgm["lofi_loop"].play(loops=-1, fade_ms=10000)
    running = True
    while running:
        clock.tick(FPS)
        dt = clock.get_time() / 1000
        fps = int(clock.get_fps())

        events = []
        for event in pygame.event.get():
            if hasattr(event, "pos"):
                event.pos = (
                    event.pos[0] * mouse_scale[0],
                    event.pos[1] * mouse_scale[1],
                )
            if hasattr(event, "rel"):
                event.rel = (
                    event.rel[0] * mouse_scale[0],
                    event.rel[1] * mouse_scale[1],
                )

            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

            events.append(event)

        menu_manager.current_menu.update(dt, events)

        # TODO update background so it is not a flat value
        display.fill(Color.BLACK)
        menu_manager.current_menu.draw(display, font_registry)
        if not menu_manager.encounter_menu.transition_active:
            for quest in menu_manager.quest_manager.started_quests.values():
                if quest.started and not quest.completed:
                    quest.tutorial_draw(menu_manager, display, font_registry)
        font_registry["big_pixel"].render(
            display,
            str(fps),
            (32, TEMP_SCREEN_SIZE[1]-32),
            Color.WHITE,
            2,
            style="center",
            outline_color=Color.BLACK
        )
        screen.blit(pygame.transform.scale(display, screen.get_size()))
        pygame.display.flip()

    DataFiles.bgm["lofi_loop"].stop()
    pygame.quit()

    # TODO can the exp be saved directly to the save file without the need to keeping track
    # of it separately in BattleComponent?
    for shipgirl in menu_manager.available_shipgirls:
        DataFiles.save_file["shipgirls"][shipgirl.name]["exp"] = shipgirl.battle_component.exp

    save_file = input("Save file? ")
    if save_file == "y":
        with open("data/save_file.json", "w") as f:
            json.dump(DataFiles.save_file, f, indent=4)
