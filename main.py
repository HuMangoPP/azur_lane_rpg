from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from engine.types import CoordinateType

import ctypes
import sys

if sys.platform == "win32":
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
        "manguino.azurlanerpg.1"
    )

import asyncio
import json
import os
import pygame

from engine.paths import SAVE_FILE_PATH, resource_path

pygame.mixer.pre_init(44100, -16, 2, 4096)
pygame.init()
pygame.display.set_icon(pygame.image.load(resource_path("assets", "tb_icon.png")))
pygame.display.set_caption("Azur Lane RPG")
screen = pygame.display.set_mode()

pygame.mixer.init()

from engine.profiler import profile, print_execution_times
from engine.font import Font

from src.constants import TEMP_SCREEN_SIZE, FPS, DataFiles, Color
from live2d.live2d import PreRenderLive2D, get_live2d_model_file
from src.menus.menu_manager import MenuManager

# Rendering will be done on this display, then scaled up to the window display.
display = pygame.Surface(TEMP_SCREEN_SIZE)

# Monkeypatch pygame.mouse.get_pos() to map from true screen space to temp surface space.
mouse_scale = (
    TEMP_SCREEN_SIZE.x / screen.get_width(),
    TEMP_SCREEN_SIZE.y / screen.get_height(),
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

with resource_path("engine", "fonts.json").open() as f:
    fonts = json.load(f)
    font_registry = {
        font: Font(font, charset)
        for font, charset in fonts.items()
    }


async def _pre_render_startup_models() -> bool:
    """Pre-render saved shipgirls while displaying a loading screen."""
    model_files = (
        get_live2d_model_file(shipgirl_name)
        for shipgirl_name in DataFiles.save_file["shipgirls"]
    )
    pre_render_task = PreRenderLive2D.cache.create_pre_render_task(model_files)

    while not pre_render_task.finished:
        clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return False

        pre_render_task.update()

        display.fill(Color.BLACK)
        center_x = TEMP_SCREEN_SIZE.x / 2
        font_registry["big_pixel"].render(
            display,
            "loading live2d sprites",
            (center_x, TEMP_SCREEN_SIZE.y * 0.4),
            Color.WHITE,
            scale=2,
            style="center",
        )

        model_name = ""
        if pre_render_task.current_model_file is not None:
            model_name = os.path.splitext(
                os.path.basename(pre_render_task.current_model_file)
            )[0]
        model_number = min(
            pre_render_task.completed_models + 1,
            pre_render_task.total_models,
        )
        loading_detail = (
            f"model {model_number}/{pre_render_task.total_models}: {model_name}  "
            f"frame {pre_render_task.current_frame}/{pre_render_task.current_total_frames}"
        )
        font_registry["big_pixel"].render(
            display,
            loading_detail,
            (center_x, TEMP_SCREEN_SIZE.y * 0.52),
            Color.WHITE,
            scale=1,
            style="center",
        )

        progress_bar = pygame.Rect(0, 0, TEMP_SCREEN_SIZE.x / 2, 12)
        progress_bar.center = (center_x, TEMP_SCREEN_SIZE.y * 0.6)
        pygame.draw.rect(display, Color.WHITE, progress_bar, width=2)
        progress_fill = progress_bar.inflate(-6, -6)
        progress_fill.width = round(progress_fill.width * pre_render_task.progress)
        if progress_fill.width > 0:
            pygame.draw.rect(display, Color.WHITE, progress_fill)

        screen.blit(pygame.transform.scale(display, screen.get_size()))
        pygame.display.flip()
        await asyncio.sleep(0)

    return True


def _write_to_save_file(menu_manager: MenuManager):
    # TODO Make the exp saved directly to the save file, which prevents needing this block of code
    # and also could potentially eliminate the need for the exp attribute in the battle component.
    for shipgirl in menu_manager.available_shipgirls:
        DataFiles.save_file["shipgirls"][shipgirl.name]["exp"] = shipgirl.battle_component.exp

    with SAVE_FILE_PATH.open("w") as f:
        json.dump(DataFiles.save_file, f, indent=4)
    print("Successfully wrote save file.")


async def main():
    if not await _pre_render_startup_models():
        pygame.quit()
        return None

    
    menu_manager = MenuManager()
    try:
        running = True
        while running:
            dt = clock.tick(FPS) / 1000
            fps = int(clock.get_fps())

            events = []
            for event in pygame.event.get():
                # Convert event mouse positions from screen space to temporary
                # display space as well.
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

            # Clear the previous frame. Each menu can draw its own background over this.
            display.fill(Color.BLACK)
            menu_manager.current_menu.draw(display, font_registry)
            if not menu_manager.encounter_menu.transition_active:
                for quest in menu_manager.quest_manager.started_quests.values():
                    if quest.started and not quest.completed:
                        quest.tutorial_draw(menu_manager, display, font_registry)

            fps_margin = 4
            font_registry["pixel"].render(
                display,
                f"fps: {fps}",
                (fps_margin, TEMP_SCREEN_SIZE[1] - 2 * fps_margin),
                Color.WHITE,
                scale=1,
                style="centerleft",
                outline_color=Color.BLACK
            )
            screen.blit(pygame.transform.scale(display, screen.get_size()))
            pygame.display.flip()
            await asyncio.sleep(0)
    except Exception as e:
        print(f"Game crashed due to exception {e}")
    finally:
        DataFiles.bgm["lofi_loop"].stop()
        pygame.quit()

        _write_to_save_file(menu_manager)


asyncio.run(main())

print_execution_times()
