from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from engine.types import CoordinateType, ColorType

import pygame


class Font:
    def __init__(self, font_name: str, charset: str):
        self.font = pygame.image.load(f"engine/{font_name}.png").convert_alpha()
        self.chars = list(charset)
        self.font_width = self.font.get_width() // len(self.chars)
        self.font_height = self.font.get_height()
        self.padding = 4
        self._load_font()

    def _load_font(self):
        """Load the font char map."""
        self.char_map = {}
        for i, char in enumerate(self.chars):
            letter = pygame.Surface((self.font_width, self.font_height))
            letter.blit(self.font, (-i * self.font_width, 0))
            self.char_map[char] = letter
    
    def _get_lines(self, text: str, scale: float, box_width: float) -> list[str]:
        """Split the text into a list of lines.
        
        If box width <= 0, then return a list with text directly.
        If box width > 0, then return a list of lines such that each line's
        total render width does not exceed box width, except if the line is
        only a single word and that word's render width exceeds the box width.
        """
        if box_width <= 0:
            return [text]
        else:
            char_width = self.font_width * scale
            max_chars_per_line = box_width // char_width
            lines = []
            line = ""
            words = text.split()
            for word in words:
                if len(line) > 0 and len(line) + len(word) > max_chars_per_line:
                    lines.append(line.strip())
                    line = word + " "
                else:
                    line = line + word + " "
            lines.append(line.strip())
            return lines

    def get_width(self, text: str, scale: float, box_width: float) -> float:
        """Get the render width of this text.
        
        If box width <= 0, get the render width of text directly.
        If box width > 0, get the render width of the longest line.
        """
        char_width = scale * self.font_width
        lines = self._get_lines(text, char_width, box_width)
        return max(len(line) for line in lines) * char_width

    def get_height(self, text: str, scale: float, box_width: float) -> float:
        """Get the render height of this text.
        
        If box width <= 0, this is simply the height of the font.
        If box width > 0, then this is the render height of all of the lines
        plus vertical padding in between.
        """
        char_width = scale * self.font_width
        char_height = scale * self.font_height
        lines = self._get_lines(text, char_width, box_width)
        return len(lines) * char_height + (len(lines) - 1) * self.padding

    @staticmethod
    def _recolor_text(text_surf: pygame.Surface, color: ColorType) -> pygame.Surface:
        """Recolor the text to the desired color.
        
        The text surface always has white text on a black background. The colorkey
        of the text surface is white.
        """
        colored_text_surf = pygame.Surface(text_surf.get_size())
        colored_text_surf.fill(color)
        colored_text_surf.blit(text_surf)
        colored_text_surf.set_colorkey((0, 0, 0))
        return colored_text_surf

    def render(
        self,
        surface: pygame.Surface,
        text: str,
        xy: CoordinateType,
        color: ColorType,
        scale: float,
        style: str = "topleft",
        outline_color: ColorType | None = None,
        box_width: float = 0
    ):
        text = text.lower()
        text_width = self.get_width(text, scale, box_width)
        text_height = self.get_height(text, scale, box_width)
        text_surf = pygame.Surface((text_width, text_height))
        text_surf.fill((0, 0, 0))

        y = 0
        char_width = self.font_width * scale
        char_height = self.font_height * scale
        lines = self._get_lines(text, scale, box_width)
        for line in lines:
            # Based on the styling, either horizontally center the text
            # or have it flush against the left.
            if style == "center":
                line_width = char_width * len(line)
                x = text_surf.get_width() / 2 - line_width / 2
            elif style in ["topleft", "centerleft"]:
                x = 0

            for char in line:
                if char != " ":
                    # Get the char image and fall back to ? if it does not exist.
                    letter = pygame.transform.scale_by(
                        self.char_map.get(char, self.char_map["?"]),
                        scale
                    )
                    text_surf.blit(letter, (x, y))
                x += char_width
            y += (char_height + self.padding)
    
        text_surf.set_colorkey((255, 255, 255))
        colored_text_surf = self._recolor_text(text_surf, color)
        
        if style == "center":
            text_rect = colored_text_surf.get_rect()
            text_rect.center = xy
        elif style == "centerleft":
            text_rect = colored_text_surf.get_rect()
            text_rect.midleft = xy
        elif style == "topleft":
            text_rect = colored_text_surf.get_rect()
            text_rect.topleft = xy

        if outline_color is not None:
            outline_text_surf = self._recolor_text(text_surf, outline_color)
            for offset in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                outline_rect = outline_text_surf.get_rect()
                outline_rect.topleft = pygame.Vector2(text_rect.topleft) + offset
                surface.blit(outline_text_surf, outline_rect)

        surface.blit(colored_text_surf, text_rect)
