import math
import random
import pygame

from src.constants import DataFiles, screen_x, screen_y

class Cloud:
    SHADOW_OFFSET = pygame.Vector2(4, 8)

    def __init__(self, index, x, y, speed):
        self.sprite = DataFiles.sprites["background"][f"cloud{index}"]
        self.shadow = DataFiles.sprites["background"][f"cloud_shadow{index}"]
        self.x = x
        self.y = y
        self.speed = speed
    
    def update(self, dt):
        self.x = self.x + self.speed * dt
    
    def draw(self, surface):
        shadow_rect = self.shadow.get_rect()
        shadow_rect.centerx = self.x + self.SHADOW_OFFSET.x
        shadow_rect.top = self.y + self.SHADOW_OFFSET.y
        surface.blit(self.shadow, shadow_rect, special_flags=pygame.BLEND_RGB_SUB)

        rect = self.sprite.get_rect()
        rect.centerx = self.x
        rect.top = self.y
        surface.blit(self.sprite, rect)

class Background:
    Y_GAP = 48
    def __init__(self):
        num_waves = DataFiles.sprites["background"]["num_waves"]
        self.wave_ys = [
            screen_y(0.5) + self.Y_GAP*(i-num_waves/2)
            for i in range(num_waves)
        ]
        self.wave_timers = [
            math.radians(360)*random.random()
            for _ in range(num_waves)
        ]

        self.cloud_timer = 0
        self.cloud_spawn_time = 0
        self.clouds = []
    
    def update(self, dt):
        num_waves = DataFiles.sprites["background"]["num_waves"]
        self.wave_timers = [
            (wave_timer + (i+1)/num_waves*dt)%math.radians(360)
            for i, wave_timer in enumerate(self.wave_timers)
        ]

        for cloud in self.clouds:
            cloud.update(dt)
        self.clouds = [
            cloud for cloud in self.clouds
            if cloud.x >= -128
            and cloud.x <= screen_x(1) + 128
        ]

        self.cloud_timer += dt
        if self.cloud_timer > self.cloud_spawn_time:
            move_right = random.random() > 0.5
            self.clouds.append(Cloud(
                random.randint(1, DataFiles.sprites["background"]["num_clouds"])-1,
                0 if move_right else screen_x(1),
                random.uniform(-64, 64),
                random.uniform(32, 64) * (1 if move_right else -1)
            ))
            self.cloud_timer = 0
            self.cloud_spawn_time = random.uniform(5, 10)
    
    def draw(self, surface, font, shipgirl=None, player_fleet=None, siren_fleet=None):
        sky_surf = DataFiles.sprites["background"]["sky"]
        sky_surf_rect = sky_surf.get_rect()
        sky_surf_rect.top = 0
        num_sky_reps = 9
        sky_rep_offset = (num_sky_reps-1)/2
        for i in range(num_sky_reps):
            sky_surf_rect.centerx = screen_x(0.5) + sky_surf_rect.width * (i-sky_rep_offset)
            surface.blit(sky_surf, sky_surf_rect)

        for cloud in self.clouds:
            cloud.draw(surface)

        if siren_fleet is not None:
            siren_draw_indices = siren_fleet.get_draw_indices()
        else:
            siren_draw_indices = None

        num_waves = DataFiles.sprites["background"]["num_waves"]
        num_wave_reps = 5
        wave_rep_offset = (num_wave_reps-1)/2
        for i, (wave_y, wave_timer) in enumerate(zip(self.wave_ys, self.wave_timers)):
            if i == (num_waves-1)/2:
                if shipgirl is not None:
                    shipgirl.draw(surface, font)
                if player_fleet is not None:
                    player_fleet.draw_shipgirl(surface, font)
            
            if siren_draw_indices is not None:
                for draw_index, siren in siren_draw_indices:
                    if i == draw_index:
                        siren.draw(surface, font) 

            wave = DataFiles.sprites["background"][f"wave{i}"]
            wave_rect = wave.get_rect()
            wave_rect.top = wave_y + 8 * math.sin(2*wave_timer)
            centerx = 64 * math.sin(wave_timer) + screen_x(0.5)
            for j in range(num_wave_reps):
                wave_rect.centerx = centerx + wave_rect.width * (j-wave_rep_offset)
                surface.blit(wave, wave_rect)