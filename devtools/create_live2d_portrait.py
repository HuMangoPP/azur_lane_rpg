import sys
import pygame

from ..engine.util import get_rect
from ..live2d.live2d import Live2D

pygame.init()
screen = pygame.display.set_mode((100,100))

shipgirl = sys.argv[1]
live2d = Live2D(f"live2d/{shipgirl}.json")

sprite_size = 96
sprite = pygame.Surface((sprite_size,sprite_size))
sprite.fill((255,0,0))
live2d.draw(sprite, sprite_size/2, sprite_size/2, False)
portrait_size = 64
crop = get_rect(width=portrait_size, height=portrait_size, centerx=sprite_size/2, top=0)
portrait = sprite.subsurface(crop)

pygame.image.save(portrait, f"live2d/{shipgirl}_portrait.png")
