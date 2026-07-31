import os
import sys
import math
import pygame

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from live2d.live2d import LAYER_SIZE, PART_NAMES

pygame.init()

screen = pygame.display.set_mode((100,100))

num_layers_per_row = 4
spritesheet = pygame.Surface((LAYER_SIZE * num_layers_per_row, LAYER_SIZE * math.ceil(len(PART_NAMES) / num_layers_per_row)))
spritesheet.fill((255,0,0))
for i, part in enumerate(PART_NAMES):
    x = (i % num_layers_per_row) * LAYER_SIZE
    y = (i // num_layers_per_row) * LAYER_SIZE
    layer = pygame.image.load(f"assets/l2d_files/{part}.png").convert()
    spritesheet.blit(layer, (x, y))

shipgirl = sys.argv[1]
pygame.image.save(spritesheet, f"live2d/{shipgirl}.png")