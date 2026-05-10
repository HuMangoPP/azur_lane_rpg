import pygame

class Button:
    def __init__(self, rect, callback, active=True, background_styling={}, text_styling={}):
        self.active = active
        self.rect = rect
        self.callback = callback

        self.background_color = background_styling.get("background_color")
        self.background_img = background_styling.get("background_img")
        self.background_img_align = background_styling.get("background_img_align")
        if self.background_img is not None and self.background_img_align is None:
            self.background_img_align = (1/2, 1/2)
        self.outline_color = background_styling.get("outline_color")
        self.outline_width = background_styling.get("outline_width")
        self.opacity = background_styling.get("opacity")
        
        self.text = text_styling.get("text")
        self.text_align = text_styling.get("text_align")
        if self.text is not None and self.text_align is None:
            self.text_align = (1/2, 1/2)
        self.text_color = text_styling.get("text_color")
    
    def click(self, mpos):
        if not self.active:
            return
        
        if not self.rect.collidepoint(mpos):
            return
        
        self.callback()

    def draw(self, surface, font):
        if not self.active:
            return
        
        if self.background_color is not None:
            background = pygame.Surface(self.rect.size)
            background.fill(self.background_color)
            if self.opacity is not None:
                background.set_alpha(self.opacity)
            surface.blit(background, self.rect)
        
        if self.outline_color is not None:
            pygame.draw.rect(surface, self.outline_color, self.rect, self.outline_width)

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
            font.render(surface, self.text, text_pos, self.text_color, 1, style="center")