import pygame

class Button:
    def __init__(self, rect, color=None, sprite=None, text=None, text_color=None, callback=None, active=True):
        self.active = active
        self.rect = rect
        self.sprite = sprite
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
        if self.sprite is not None:
            screen.blit(self.sprite, self.rect)
        if self.text is not None:
            font.render(screen, self.text, self.rect.center, self.text_color, 1, style="center")