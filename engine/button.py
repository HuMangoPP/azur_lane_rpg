import pygame

class Button:
    def __init__(self, rect, color, text, text_color, callback, active=True):
        self.active = active
        self.rect = rect
        self.color = color
        self.text = text
        self.text_color = text_color
        self.callback = callback
    
    def click(self, mpos):
        if not self.active:
            return
        
        if not self.rect.collidepoint(mpos):
            return
        
        self.callback()

    def draw(self, screen, font):
        if not self.active:
            return
        
        pygame.draw.rect(screen, self.color, self.rect)
        font.render(screen, self.text, self.rect.center, self.text_color, 2, style="center")