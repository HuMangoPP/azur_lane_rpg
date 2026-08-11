import argparse
import os
import sys

import pygame

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from live2d.live2d import Live2D

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Preview a shipgirl Live2D animation.")
    parser.add_argument("shipgirl", help="Shipgirl name, matching live2d/<shipgirl>.json")
    parser.add_argument("animation_key", help="Animation key, one of [idle, bounce, drag, walk, attack, sink]")
    args = parser.parse_args()

    pygame.init()
    screen = pygame.display.set_mode((200,200))
    clock = pygame.time.Clock()

    index = 0
    if args.shipgirl == "all":
        l2ds = [
            Live2D(f"live2d/{filename[:-4]}.json")
            for filename in os.listdir("live2d/")
            if filename.endswith(".png")
        ]
        for l2d in l2ds:
            l2d.set_animation(args.animation_key)
    else:
        l2ds = [Live2D(f"live2d/{args.shipgirl}.json")]
        l2ds[0].set_animation(args.animation_key)
    l2d = l2ds[index]

    running = True
    while running:
        clock.tick()
        dt = clock.get_time() / 1000

        pygame.display.set_caption(f"{clock.get_fps()}")

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                l2d.set_animation(args.animation_key)
                l2d.t = 0
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                if event.key == pygame.K_r:
                    l2d.t = 0
                if event.key == pygame.K_LEFT:
                    index = (index - 1) % len(l2ds)
                    l2d = l2ds[index]
                if event.key == pygame.K_RIGHT:
                    index = (index + 1) % len(l2ds)
                    l2d = l2ds[index]
            
        l2d.update(dt)

        screen.fill((255,0,0))
        l2d.draw(screen, 0.5*screen.get_width(), 0.5*screen.get_height(), False)
        pygame.display.flip()

    pygame.quit()
                