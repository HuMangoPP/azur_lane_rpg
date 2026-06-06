import math
import random
import pygame

from engine.util import get_vec


SHELL_COLORS = {
    "normal": {
        "plume": (115, 109, 45),
        "core": (255, 248, 180),
        "hot": (255, 206, 72),
        "edge": (255, 128, 32),
        "smoke": (100, 96, 86),
    },
    "HE": {
        "plume": (112, 0, 28),
        "core": (255, 238, 170),
        "hot": (255, 80, 28),
        "edge": (220, 20, 44),
        "smoke": (112, 78, 64),
    },
    "AP": {
        "plume": (0, 110, 110),
        "core": (225, 255, 255),
        "hot": (75, 234, 255),
        "edge": (46, 132, 255),
        "smoke": (78, 98, 112),
    },
}


HULL_FLASH_SCALE = {
    "DD": 1.00,
    "CL": 1.05,
    "CA": 1.10,
    "BB": 1.20,
}

SHELL_SCALE = 1/1000

def shell_position(start_pos, target_pos, t):
    relpos = target_pos - start_pos
    distance = relpos.length()
    scale = distance * SHELL_SCALE
    shell_y = scale * distance * t * (t - 1)
    return start_pos + relpos * t + pygame.Vector2(0, shell_y)


class MuzzleFlashEffect:
    DURATION = 0.2

    def __init__(self, start_pos, shell_render_angle, shell_type, hull_type):
        self.start_pos = pygame.Vector2(start_pos)
        self.palette = SHELL_COLORS.get(shell_type, SHELL_COLORS["normal"])
        self.lifetime = 0

        num_sparks = 3
        self.sparks = []
        for _ in range(num_sparks):
            t = random.random()
            spark_angle = shell_render_angle + math.radians((2*t-1) * 15)
            spark_scale = (
                t + 1/2 if t <= 1/2
                else 3/2 - t
            )
            self.sparks.append((spark_angle, spark_scale))

    @property
    def expired(self):
        return self.lifetime >= self.DURATION

    def update(self, dt):
        self.lifetime += dt

    def draw(self, surface):
        t = min(1, self.lifetime / self.DURATION)
        s = 1 - (2*t - 1)**2
        for spark_angle, spark_scale in self.sparks:
            spark_dir = get_vec(1, spark_angle)
            spark_perp = pygame.Vector2(-spark_dir.y, spark_dir.x)
            spark_length = 100 * s * spark_scale
            spark_width = 20 * s * spark_scale
            spark_pos = self.start_pos + spark_dir * 150 * t
            spark_polygon = [
                spark_pos + spark_dir * spark_length*0.66,
                spark_pos + spark_perp * spark_width*0.5,
                spark_pos - spark_dir * spark_length*0.33,
                spark_pos - spark_perp * spark_width*0.5
            ]
            pygame.draw.polygon(surface, self.palette["core"], spark_polygon)


class TracerEffect:
    def __init__(self, start_pos, target_pos, shell_type, shell_speed):
        self.start_pos = pygame.Vector2(start_pos)
        self.target_pos = pygame.Vector2(target_pos)
        self.palette = SHELL_COLORS.get(shell_type, SHELL_COLORS["normal"])
        distance = (self.target_pos - self.start_pos).length()
        self.duration = max(0.05, distance / shell_speed)
        self.age = 0
        self.trail = []

    @property
    def expired(self):
        return self.age >= self.duration

    def update(self, dt):
        self.age += dt
        t = min(1, self.age / self.duration)
        self.trail.append(shell_position(self.start_pos, self.target_pos, t))
        self.trail = self.trail[-8:]

    def draw(self, surface):
        if len(self.trail) < 2:
            return

        for i, (start, end) in enumerate(zip(self.trail, self.trail[1:])):
            fade = (i + 1) / len(self.trail)
            alpha = int(105 * fade)
            width = max(2, int(16 * fade))
            pygame.draw.line(
                surface,
                (*self.palette["hot"], alpha),
                start,
                end,
                width=width,
            )


class ImpactEffect:
    DURATION = 0.3

    def __init__(self, pos, shell_render_angle, shell_type):
        self.pos = pygame.Vector2(pos)
        self.palette = SHELL_COLORS.get(shell_type, SHELL_COLORS["normal"])
        self.lifetime = 0
        
        num_sparks = 3
        self.sparks = []
        for _ in range(num_sparks):
            t = random.random()
            spark_angle = shell_render_angle + math.radians((2*t-1) * 30 + 180)
            spark_scale = (
                t + 1/2 if t <= 1/2
                else 3/2 - t
            )
            self.sparks.append((spark_angle, spark_scale))

    @property
    def expired(self):
        return self.lifetime >= self.DURATION

    def update(self, dt):
        self.lifetime += dt

    def draw(self, surface):
        t = min(1, self.lifetime / self.DURATION)
        s = 1 - (2*t - 1)**2
        for spark_angle, spark_scale in self.sparks:
            spark_dir = get_vec(1, spark_angle)
            spark_perp = pygame.Vector2(-spark_dir.y, spark_dir.x)
            spark_length = 100 * s * spark_scale
            spark_width = 20 * s * spark_scale
            spark_pos = self.pos + spark_dir * 100 * t
            spark_polygon = [
                spark_pos + spark_dir * spark_length*0.66,
                spark_pos + spark_perp * spark_width*0.5,
                spark_pos - spark_dir * spark_length*0.33,
                spark_pos - spark_perp * spark_width*0.5
            ]
            pygame.draw.polygon(surface, self.palette["core"], spark_polygon)

class GunFireVFXManager:
    def __init__(self):
        self.effects = []

    def clear(self):
        self.effects = []

    def spawn_muzzle_flash(self, start_pos, shell_render_angle, shell_type, hull_type):
        self.effects.append(MuzzleFlashEffect(start_pos, shell_render_angle, shell_type, hull_type))

    def spawn_tracer(self, start_pos, target_pos, shell_type, shell_speed):
        self.effects.append(TracerEffect(start_pos, target_pos, shell_type, shell_speed))

    def spawn_impact(self, pos, shell_render_angle, shell_type):
        self.effects.append(ImpactEffect(pos, shell_render_angle, shell_type))

    def update(self, dt):
        for effect in self.effects:
            effect.update(dt)
        self.effects = [effect for effect in self.effects if not effect.expired]

    def draw(self, surface):
        overlay = pygame.Surface(surface.get_size(), flags=pygame.SRCALPHA)
        for effect in self.effects:
            effect.draw(overlay)
        surface.blit(overlay, (0, 0))
