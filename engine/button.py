import pygame

class Button:
    def __init__(self, rect, callback, active=True, background_styling={}, text_styling={}, hover_styling={}):
        self.active = active
        self.rect = rect
        self.callback = callback

        self.background_color = background_styling.get("background_color")
        self.background_img = background_styling.get("background_img")
        self.background_img_align = background_styling.get("background_img_align", (1/2, 1/2))
        self.outline_color = background_styling.get("outline_color")
        self.outline_width = background_styling.get("outline_width", 2)
        self.opacity = background_styling.get("opacity")
        
        self.text = text_styling.get("text")
        self.text_align = text_styling.get("text_align", (1/2, 1/2))
        self.text_color = text_styling.get("text_color", (0, 0, 0))
        self.text_size = text_styling.get("text_size", 1)
        self.text_margins = text_styling.get("text_margins", 8)

        self.hover_background_color = hover_styling.get("background_color", self.background_color)
        self.hover_outline_color = hover_styling.get("outline_color", self.outline_color)
        self.hover_outline_width = hover_styling.get("outline_width", self.outline_width)
        self.hover_opacity = hover_styling.get("opacity", self.opacity)
        self.hovered = False
    
    def hover(self, mpos):
        if not self.active:
            self.hovered = False
        elif not self.rect.collidepoint(mpos):
            self.hovered = False
        else:
            self.hovered = True
        return self.hovered

    def click(self, mpos):
        if not self.active:
            return False
        
        if not self.rect.collidepoint(mpos):
            return False
        
        self.callback()
        return True

    def draw(self, surface, font):
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
            font.render(
                surface,
                self.text,
                text_pos,
                self.text_color,
                self.text_size,
                style="center",
                box_width=self.rect.width - 2*self.text_margins
            )