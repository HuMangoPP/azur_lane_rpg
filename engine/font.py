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
        self.char_map = {}
        for i, char in enumerate(self.chars):
            letter = pygame.Surface((self.font_width, self.font_height))
            letter.blit(self.font, (-i * self.font_width, 0))
            self.char_map[char] = letter
    
    def _get_lines(self, text, char_width, box_width):
        if box_width == 0:
            return [text]
        else:
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

    def get_width(self, text, scale, box_width):
        char_width = scale * self.font_width
        lines = self._get_lines(text, char_width, box_width)
        return max(len(line.strip()) for line in lines) * char_width

    def get_height(self, text, scale, box_width):
        char_width = scale * self.font_width
        char_height = scale * self.font_height
        lines = self._get_lines(text, char_width, box_width)
        return len(lines)*char_height + (len(lines)-1)*self.padding

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
        text = text.lower()
        char_width = scale * self.font_width
        char_height = scale * self.font_height
        lines = self._get_lines(text, char_width, box_width)
        text_width = max(len(line.strip()) for line in lines) * char_width
        if box_width == 0:
            text_surf = pygame.Surface((text_width, char_height))
        else:
            text_surf = pygame.Surface((text_width, len(lines)*char_height + (len(lines)-1)*self.padding))

        y = 0
        for line in lines:
            if style == "center":
                line_width = char_width * len(line)
                x = text_surf.get_width() / 2 - line_width / 2
            elif style in ["topleft", "centerleft"]:
                x = 0
            for char in line:
                if char != " ":
                    letter = pygame.transform.scale_by(
                        self.char_map.get(char, self.char_map["?"]),
                        scale
                    )
                    text_surf.blit(letter, (x, y))
                x += char_width
            y += (char_height + self.padding)
    
        text_surf.set_colorkey((255, 255, 255))

        colored_text_surf = pygame.Surface(text_surf.get_size())
        colored_text_surf.fill(color)
        colored_text_surf.blit(text_surf, (0, 0))
        colored_text_surf.set_colorkey((0, 0, 0))
        
        if style == "center":
            rect = colored_text_surf.get_rect()
            rect.center = xy
        elif style == "centerleft":
            rect = colored_text_surf.get_rect()
            rect.left = xy[0]
            rect.centery = xy[1]
        elif style == "topleft":
            rect = colored_text_surf.get_rect()
            rect.topleft = xy
        if outline_color is not None:
            self._outline(surface, text_surf, rect.topleft, outline_color)
        surface.blit(colored_text_surf, rect)
