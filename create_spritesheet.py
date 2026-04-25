import sys
import math
import pygame

parts = [
    "bangs",
    "right_bangs",
    "right_hair",
    "left_bangs",
    "top_head",
    "head",
    "right_arm",
    "torso",
    "left_arm",
    "right_leg",
    "left_leg",
    "left_hair",
    "back_torso",
    "back_hair"
]

pygame.init()

screen = pygame.display.set_mode((100,100))

layer_size = 96
num_layers_per_row = 4
spritesheet = pygame.Surface((layer_size * num_layers_per_row, layer_size * math.ceil(len(parts) / num_layers_per_row)))
for i, part in enumerate(parts):
    x = (i % num_layers_per_row) * layer_size
    y = (i // num_layers_per_row) * layer_size
    layer = pygame.image.load(f"assets/l2d_files/{part}.png").convert()
    spritesheet.blit(layer, (x, y))

shipgirl = sys.argv[1]
pygame.image.save(spritesheet, f"live2d/{shipgirl}.png")