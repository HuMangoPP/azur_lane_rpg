from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import pygame
    from engine.font import Font
    from src.menus.menu_manager import MenuManager


# TODO Consider whether this should be moved to the engine.
class Menu:
    def __init__(self, menu_manager: MenuManager):
        pass

    def update(self, dt: float, events: list[pygame.Event]):
        """Abstract menu update method."""
        pass

    def draw(self, surface: pygame.Surface, font_registry: dict[str, Font]):
        """Abstract menu draw method."""
        pass