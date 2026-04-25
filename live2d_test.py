import sys
import math
import pygame

from live2d.live2d import Live2D

pygame.init()
screen = pygame.display.set_mode((300,300))
temp_screen = pygame.Surface((300,300))
clock = pygame.time.Clock()

shipgirl = sys.argv[1]
l2d = Live2D(f"live2d/{shipgirl}.json")
l2d.set_animation(Live2D.IDLE_ANIMATION)

NUM_FRAMES = 8

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
        
        if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
            if l2d.animation == Live2D.IDLE_ANIMATION:
                l2d.set_animation(Live2D.WALK_ANIMATION)
            elif l2d.animation == Live2D.WALK_ANIMATION:
                l2d.set_animation(Live2D.IDLE_ANIMATION)
        
    l2d.update(dt)

    temp_screen.fill((255,0,0))
    l2d.draw(temp_screen, 0.5*temp_screen.get_width(), 0.5*temp_screen.get_height(), False)
    screen.blit(pygame.transform.scale(temp_screen, screen.get_size()), (0,0))
    pygame.display.flip()

pygame.quit()
            