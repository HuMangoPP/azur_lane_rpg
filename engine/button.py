from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from collections.abc import Callable
    from engine.font import Font

import math
import pygame

from engine.util import get_vec, draw_annulus


class Button:
    def __init__(self, active: bool, callback: Callable):
        self.active = active
        self.callback = callback

        self.hovered = False

    def hover(self, mpos: tuple[float, float]) -> bool:
        """Abstract hover method."""
        pass

    def click(self, mpos: tuple[float, float]) -> bool:
        """Abstract click method."""
        pass

    def draw(self, surface: pygame.Surface, font_registry: dict[str, Font]):
        """Abstract draw method."""
        pass


class RectangularButton(Button):
    def __init__(
            self,
            rect: pygame.Rect,
            callback: Callable,
            active: bool = True,
            background_styling: dict | None = None,
            text_styling: dict | None = None,
            hover_styling: dict | None = None
        ):
        super().__init__(active, callback)

        self.rect = rect

        background_styling = background_styling or {}
        self.background_color: tuple[int, int, int] | None = background_styling.get("background_color")
        self.background_img: pygame.Surface | None = background_styling.get("background_img")
        self.background_img_align: tuple[float, float] = background_styling.get("background_img_align", (1/2, 1/2))
        self.outline_color: tuple[int, int, int] | None = background_styling.get("outline_color")
        self.outline_width: int = background_styling.get("outline_width", 2)
        self.opacity: int | None = background_styling.get("opacity")

        text_styling = text_styling or {}
        self.text: str | None = text_styling.get("text")
        self.text_align: tuple[float, float] = text_styling.get("text_align", (1/2, 1/2))
        self.text_font: str = text_styling.get("text_font", "big_pixel")
        self.text_color: tuple[int, int, int] = text_styling.get("text_color", (255, 255, 255))
        self.text_size: int = text_styling.get("text_size", 1)
        self.text_margins: float = text_styling.get("text_margins", 8)

        hover_styling = hover_styling or {}
        self.hover_background_color: tuple[int, int, int] | None = hover_styling.get("background_color", self.background_color)
        self.hover_outline_color: tuple[int, int, int] | None = hover_styling.get("outline_color", self.outline_color)
        self.hover_outline_width: int = hover_styling.get("outline_width", self.outline_width)
        self.hover_opacity: int | None = hover_styling.get("opacity", self.opacity)
    
    def hover(self, mpos: tuple[int, int]) -> bool:
        """Check if the mouse is hovering over this button."""
        if not self.active:
            self.hovered = False
        elif not self.rect.collidepoint(mpos):
            self.hovered = False
        else:
            self.hovered = True
        return self.hovered

    def click(self, mpos: tuple[int, int]) -> bool:
        """Check if the mouse has clicked this button, and call the callback if so."""
        if not self.active:
            return False
        
        if not self.rect.collidepoint(mpos):
            return False
        
        self.callback()
        return True

    def draw(self, surface: pygame.Surface, font_registry: dict[str, Font]):
        "Draw this button."
        if not self.active:
            return
        
        background_color = self.hover_background_color if self.hovered else self.background_color
        opacity = self.hover_opacity if self.hovered else self.opacity
        if background_color is not None:
            background = pygame.Surface(self.rect.size)
            background.fill(background_color)
            if opacity is not None:
                background.set_alpha(opacity)
            surface.blit(background, self.rect)
        
        outline_color = self.hover_outline_color if self.hovered else self.outline_color
        outline_width = self.hover_outline_width if self.hovered else self.outline_width
        if outline_color is not None:
            pygame.draw.rect(surface, outline_color, self.rect, outline_width)

        if self.background_img is not None:
            img_rect = self.background_img.get_rect()
            img_rect.center = (
                self.rect.left + self.rect.width * self.background_img_align[0],
                self.rect.top + self.rect.height * self.background_img_align[1]
            )
            surface.blit(self.background_img, img_rect)
    
        if self.text is not None:
            text_pos = (
                self.rect.left + self.rect.width * self.text_align[0],
                self.rect.top + self.rect.height * self.text_align[1]
            )
            font_registry[self.text_font].render(
                surface,
                self.text,
                text_pos,
                self.text_color,
                self.text_size,
                style="center",
                box_width=self.rect.width - 2*self.text_margins
            )


class AnnularSectorButton(Button):
    ANGLE_PADDING = 1
    
    def __init__(
        self,
        inner_radius: float,
        outer_radius: float,
        angle_width: float,
        callback: Callable,
        active: bool = True,
        background_styling: dict | None = None,
        hover_styling: dict | None = None,
    ):
        super().__init__(active, callback)

        self.center = pygame.Vector2(0, 0)
        self.angle = 0
        self.angle_width = angle_width
        self.inner_radius = round(inner_radius)
        self.outer_radius = round(outer_radius)

        background_styling = background_styling or {}
        self.background_color = background_styling.get("background_color")
        self.background_img = background_styling.get("background_img")
        self.opacity = background_styling.get("opacity")

        hover_styling = hover_styling or {}
        self.hover_background_color = hover_styling.get("background_color", self.background_color)
        self.hover_opacity = hover_styling.get("opacity", self.opacity)
        self.hovered = False

    def contains_point(self, mpos: tuple[int, int]) -> bool:
        """Check if the mouse position is contained within the annular sector."""
        relpos = pygame.Vector2(mpos) - self.center
        distance = relpos.length()
        if distance < self.inner_radius or distance > self.outer_radius:
            return False

        point_angle = math.atan2(relpos.y, relpos.x)
        angle_delta = (point_angle - self.angle + math.pi) % (2 * math.pi) - math.pi
        return abs(angle_delta) <= self.angle_width / 2

    def hover(self, mpos: tuple[int, int]) -> bool:
        """Check if the mouse is hovering over this button."""
        self.hovered = self.active and self.contains_point(mpos)
        return self.hovered

    def click(self, mpos: tuple[int, int]) -> bool:
        """Check if the mouse has clicked this button, and call the callback if so."""
        if not self.active or not self.contains_point(mpos):
            return False

        self.callback()
        return True

    def get_wedge_centroid(self) -> pygame.Vector2:
        return self.center + get_vec((self.inner_radius + self.outer_radius) / 2, self.angle)

    def draw(self, surface: pygame.Surface, font_registry: dict[str, Font]):
        "Draw this button."
        if not self.active:
            return

        background_color = self.hover_background_color if self.hovered else self.background_color
        opacity = self.hover_opacity if self.hovered else self.opacity
        if background_color is not None:
            wedge_surface = pygame.Surface((2 * self.outer_radius, 2 * self.outer_radius))
            draw_annulus(
                wedge_surface,
                background_color,
                (self.outer_radius, self.outer_radius),
                self.inner_radius,
                self.outer_radius,
                math.degrees(self.angle - self.angle_width / 2) + self.ANGLE_PADDING,
                math.degrees(self.angle + self.angle_width / 2) - self.ANGLE_PADDING,
                resolution=4
            )
            if opacity is not None:
                wedge_surface.set_alpha(opacity)
            wedge_surface.set_colorkey((0, 0, 0))
            wedge_rect = wedge_surface.get_rect(center=self.center)
            surface.blit(wedge_surface, wedge_rect)

        if self.background_img is not None:
            img_rect = self.background_img.get_rect()
            img_rect.center = self.get_wedge_centroid()
            surface.blit(self.background_img, img_rect)
