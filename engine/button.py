import pygame

class Button:
    def __init__(self, rect=None, color=None, sprite=None, text=None, text_pos=None, text_color=None, callback=None, active=True):
        self.active = active
        self.rect = rect
        self.sprite = sprite
        self.color = color
        self.text = text
        if text_pos is None:
            self.text_pos = self.rect.center
        else:
            self.text_pos = (
                self.rect.width * text_pos[0],
                self.rect.height * text_pos[1]
            )
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
        
        if self.color is not None:
            pygame.draw.rect(screen, self.color, self.rect)
        if self.sprite is not None:
            screen.blit(self.sprite, self.rect)
        if self.text is not None:
            text_pos = pygame.Vector2(self.rect.topleft) + pygame.Vector2(self.text_pos)
            font.render(screen, self.text, text_pos, self.text_color, 1, style="center")