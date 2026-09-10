from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import pygame
    from engine.font import Font


class Menu:
    def __init__(self, menu_manager: BaseMenuManager):
        pass

    def update(self, dt: float, events: list[pygame.Event]):
        """Abstract menu update method."""
        pass

    def draw(self, surface: pygame.Surface, font_registry: dict[str, Font]):
        """Abstract menu draw method."""
        pass


class BaseMenuManager:
    def __init__(self):
        self.menu_register: dict[str, Menu] = {}

        self._current_menu: Menu | None = None

    def _register_menu(self, menu_key: str, menu: Menu):
        self.menu_register[menu_key] = menu

    @property
    def current_menu(self) -> Menu:
        return self._current_menu

    @current_menu.setter
    def current_menu(self, menu: Menu):
        """Set the current menu."""
        self._current_menu = menu