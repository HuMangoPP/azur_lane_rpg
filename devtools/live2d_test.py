import pygame

from live2d.live2d import Live2D

pygame.init()
screen = pygame.display.set_mode((200,200))
clock = pygame.time.Clock()

l2d = Live2D("live2d/laffey/model.json")
l2d.set_animation(Live2D.WALK_ANIMATION)

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
        
    l2d.update(dt)

    screen.fill((0,0,0))
    l2d.draw(screen, 0.5*screen.get_width(), 0.5*screen.get_height(), False)
    pygame.display.flip()

pygame.quit()
            