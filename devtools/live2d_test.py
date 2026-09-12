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

    if args.shipgirl == "all":
        l2ds = [
            Live2D(f"live2d/{filename[:-4]}.json")
            for filename in os.listdir("live2d/")
            if filename.endswith(".png")
        ]
    else:
        l2ds = [Live2D(f"live2d/{args.shipgirl}.json")]
    shipgirl_index = 0
    l2d = l2ds[shipgirl_index]

    if args.animation_key == "all":
        animation_keys = [
            Live2D.IDLE_ANIMATION,
            Live2D.BOUNCE_ANIMATION,
            Live2D.DRAG_ANIMATION,
            Live2D.WALK_ANIMATION,
            Live2D.SAIL_ANIMATION,
            Live2D.ATTACK_ANIMATION,
            Live2D.SINK_ANIMATION,
            Live2D.SLEEP_ANIMATION,
            Live2D.SIT_ANIMATION,
        ]
    else:
        animation_keys = [args.animation_key]
    animation_key_index = 0
    animation_key = animation_keys[animation_key_index]
    l2d.set_animation(animation_key)

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
                l2d.set_animation(animation_key)
                l2d.t = 0
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

                if event.key == pygame.K_r:
                    l2d.t = 0

                if event.key == pygame.K_LEFT:
                    shipgirl_index = (shipgirl_index - 1) % len(l2ds)
                    l2d = l2ds[shipgirl_index]
                    l2d.set_animation(animation_key)
                if event.key == pygame.K_RIGHT:
                    shipgirl_index = (shipgirl_index + 1) % len(l2ds)
                    l2d = l2ds[shipgirl_index]
                    l2d.set_animation(animation_key)

                if event.key == pygame.K_UP:
                    animation_key_index = (animation_key_index - 1) % len(animation_keys)
                    animation_key = animation_keys[animation_key_index]
                    l2d.set_animation(animation_key)
                if event.key == pygame.K_DOWN:
                    animation_key_index = (animation_key_index + 1) % len(animation_keys)
                    animation_key = animation_keys[animation_key_index]
                    l2d.set_animation(animation_key)

        l2d.update(dt)

        screen.fill((255,0,0))
        l2d.draw(screen, 0.5*screen.get_width(), 0.5*screen.get_height(), False)
        pygame.display.flip()

    pygame.quit()
                