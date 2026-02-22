import pygame

class Font:
    def __init__(self, font_path="engine/font.png"):
        self.font = pygame.image.load(font_path).convert_alpha()
        self.chars = list('abcdefghijklmnopqrstuvwxyz1234567890.,;-?!_:+[]')
        self.font_width = self.font.get_width() // len(self.chars)
        self.font_height = self.font.get_height()
        self._load_font()

    def _load_font(self):
        self.char_map = {}
        for i, char in enumerate(self.chars):
            letter = pygame.Surface((self.font_width, self.font_height))
            letter.blit(self.font, (-i * self.font_width, 0))
            self.char_map[char] = letter
    
    def _get_lines(self, text, width, box_width):
        if box_width <= 0:
            return [text]
        else:
            max_chars_per_line = box_width // width
            lines = []
            line = ""
            words = text.split()
            for word in words:
                if len(line) > 0 and len(line) + len(word) + 1 > max_chars_per_line:
                    lines.append(line)
                    line = word
                else:
                    line = f"{line} {word}"
            lines.append(line)
            return lines

    def _outline(self, surface, text_surf, xy, outline_color):
        outline_text_surf = pygame.Surface(text_surf.get_size())
        outline_text_surf.fill(outline_color)
        outline_text_surf.blit(text_surf, (0, 0))
        outline_text_surf.set_colorkey((0, 0, 0))

        surface.blit(outline_text_surf, pygame.Vector2(xy) + pygame.Vector2(1, 0))
        surface.blit(outline_text_surf, pygame.Vector2(xy) + pygame.Vector2(0, 1))
        surface.blit(outline_text_surf, pygame.Vector2(xy) + pygame.Vector2(-1, 0))
        surface.blit(outline_text_surf, pygame.Vector2(xy) + pygame.Vector2(0, -1))

    def render(self, surface, text, xy, color, scale, style="topleft", outline_color=None, box_width=0):
        padding = 4
        char_width = scale * self.font_width
        char_height = scale * self.font_height
        lines = self._get_lines(text, char_width, box_width)
        if box_width == 0:
            text_surf = pygame.Surface((char_width * len(lines[0]) + padding, char_height + padding))
        else:
            text_surf = pygame.Surface((box_width + padding, len(lines) * char_height + padding))

        y = padding / 2
        for line in lines:
            if style == "center":
                line_width = char_width * len(line)
                x = text_surf.get_width() / 2 - line_width / 2
            else:
                x = padding / 2
            for char in line:
                if char != " ":
                    letter = pygame.transform.scale_by(
                        self.char_map.get(char, self.char_map["?"]),
                        scale
                    )
                    text_surf.blit(letter, (x, y))
                x += char_width
            y += char_height
    
        text_surf.set_colorkey((255, 255, 255))

        colored_text_surf = pygame.Surface(text_surf.get_size())
        colored_text_surf.fill(color)
        colored_text_surf.blit(text_surf, (0, 0))
        colored_text_surf.set_colorkey((0, 0, 0))
        
        if style == "center":
            rect = colored_text_surf.get_rect()
            rect.center = xy
            if outline_color is not None:
                self._outline(surface, text_surf, rect.topleft, outline_color)
            surface.blit(colored_text_surf, rect)
        else:
            if outline_color is not None:
                self._outline(surface, text_surf, xy, outline_color)
            surface.blit(colored_text_surf, xy)
