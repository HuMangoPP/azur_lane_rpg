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

class BackgroundProp:
    def __init__(self, sprite_name, x, top, draw_index):
        self.sprite = DataFiles.sprites["background"][sprite_name]
        self.x = x
        self.top = top
        self.draw_index = draw_index

    def draw(self, surface):
        rect = self.sprite.get_rect()
        rect.centerx = self.x
        rect.top = self.top
        surface.blit(self.sprite, rect)

class Background:
    Y_GAP = 48
    PROP_COUNTS = {
        "island": 2,
        "rocks": 2,
    }

    def __init__(self):
        num_waves = DataFiles.sprites["background"]["num_waves"]
        self.wave_ys = [
            screen_y(0.5) + self.Y_GAP*(i-num_waves/2)
            for i in range(num_waves)
        ]
        self.wave_timers = [
            math.radians(random.randint(0, 359))
            for _ in range(num_waves)
        ]

        self.cloud_timer = 0
        self.cloud_spawn_time = 0
        self.clouds = []
        self.props = self.create_props(num_waves)

    def create_props(self, num_waves):
        prop_names = [
            prop_name
            for prop_name, count in self.PROP_COUNTS.items()
            for _ in range(count)
        ]
        random.shuffle(prop_names)

        edge_padding = 96
        width = screen_x(1)
        slot_width = width / len(prop_names)
        props = []
        for i, prop_name in enumerate(prop_names):
            draw_index = 0
            slot_center = slot_width * (i + 0.5)
            x = random.uniform(
                max(edge_padding, slot_center - slot_width * 0.35),
                min(width - edge_padding, slot_center + slot_width * 0.35)
            )
            top = self.wave_ys[draw_index] - 16
            props.append(BackgroundProp(prop_name, x, top, draw_index))

        return sorted(props, key=lambda prop: (prop.draw_index, prop.top))
    
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
            move_right = bool(random.randint(0, 1))
            self.clouds.append(Cloud(
                random.randint(1, DataFiles.sprites["background"]["num_clouds"])-1,
                0 if move_right else screen_x(1),
                random.uniform(-64, 64),
                random.uniform(32, 64) * (1 if move_right else -1)
            ))
            self.cloud_timer = 0
            self.cloud_spawn_time = random.uniform(5, 10)
    
    def draw(self, surface, font_registry, player_fleet=None, siren_fleet=None):
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
        
        if player_fleet is not None:
            shipgirl_draw_indices = player_fleet.get_draw_indices()
        else:
            shipgirl_draw_indices = None

        num_waves = DataFiles.sprites["background"]["num_waves"]
        num_wave_reps = 5
        wave_rep_offset = (num_wave_reps-1)/2
        for i, (wave_y, wave_timer) in enumerate(zip(self.wave_ys, self.wave_timers)):
            if shipgirl_draw_indices is not None:
                for draw_index, shipgirl in shipgirl_draw_indices:
                    if i == draw_index:
                        shipgirl.draw(surface, font_registry) 
            
            if siren_draw_indices is not None:
                for draw_index, siren in siren_draw_indices:
                    if i == draw_index:
                        siren.draw(surface, font_registry) 

            for prop in self.props:
                if i == prop.draw_index:
                    prop.draw(surface)

            wave = DataFiles.sprites["background"][f"wave{i}"]
            wave_rect = wave.get_rect()
            wave_rect.top = wave_y + 8 * math.sin(2*wave_timer)
            centerx = 64 * math.sin(wave_timer) + screen_x(0.5)
            for j in range(num_wave_reps):
                wave_rect.centerx = centerx + wave_rect.width * (j-wave_rep_offset)
                surface.blit(wave, wave_rect)
