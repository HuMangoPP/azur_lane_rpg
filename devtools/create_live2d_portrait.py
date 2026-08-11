import argparse
import os
import sys
import pygame

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.util import get_rect
from live2d.live2d import Live2D, LAYER_SIZE

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Preview a shipgirl Live2D animation.")
    parser.add_argument("--shipgirls", nargs="+", type=str, help="Shipgirl names, matching live2d/<shipgirl>.json")
    args = parser.parse_args()

    pygame.init()
    screen = pygame.display.set_mode((100,100))

    from src.constants import Box

    num_shipgirls = len(args.shipgirls)
    if num_shipgirls == 0:
        sys.exit()

    portraits = pygame.Surface((Box.WIDTH * num_shipgirls, Box.HEIGHT))
    for i, shipgirl in enumerate(args.shipgirls):
        live2d = Live2D(f"live2d/{shipgirl}.json")
        sprite = pygame.Surface((LAYER_SIZE,LAYER_SIZE))
        sprite.fill((255,0,0))
        live2d.draw(sprite, LAYER_SIZE/2, LAYER_SIZE/2, False)
        crop = get_rect(
            width=Box.WIDTH, height=Box.HEIGHT,
            centerx=LAYER_SIZE/2, top=0
        )
        portrait = sprite.subsurface(crop)
        portraits.blit(portrait, (Box.WIDTH * i, 0))

    pygame.image.save(portraits, f"live2d/portraits.png")
