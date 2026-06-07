import math
import random
import pygame

from engine.util import get_vec


SHELL_COLORS = {
    "normal": (255, 242, 97),
    "HE": (255, 0, 64),
    "AP": (0, 255, 255)
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


class VFX:
    def __init__(self, duration):
        self.lifetime = 0
        self.duration = duration
    
    @property
    def expired(self):
        return self.lifetime >= self.duration

    def update(self, dt):
        self.lifetime += dt


class Sparks(VFX):
    def __init__(self, pos, angle, shell_type, duration=0.3, num_sparks=3):
        super().__init__(duration)

        self.pos = pygame.Vector2(pos)
        self.color = SHELL_COLORS.get(shell_type, SHELL_COLORS["normal"])

        self.sparks = []
        for _ in range(num_sparks):
            t = random.random()
            spark_angle = angle + math.radians((2*t-1) * 15)
            s = 1 - abs(2*t-1)
            spark_scale = 0.66 + 0.33 * s
            self.sparks.append((spark_angle, spark_scale))

    def draw(self, surface):
        t = min(1, self.lifetime / self.duration)
        s = 1 - (2*t - 1)**2
        for spark_angle, spark_scale in self.sparks:
            spark_dir = get_vec(1, spark_angle)
            spark_perp = pygame.Vector2(-spark_dir.y, spark_dir.x)
            spark_length = 50 * s * spark_scale
            spark_width = 10 * s * spark_scale
            spark_pos = self.pos + spark_dir * 100 * t * spark_scale
            spark_polygon = [
                spark_pos + spark_dir * spark_length,
                spark_pos + spark_perp * spark_width,
                spark_pos - spark_dir * spark_length,
                spark_pos - spark_perp * spark_width
            ]
            pygame.draw.polygon(surface, self.color, spark_polygon)


class Boom(VFX):
    def __init__(self, pos, shell_type, duration=0.3):
        super().__init__(duration)

        self.pos = pos
        self.color = SHELL_COLORS.get(shell_type, SHELL_COLORS["normal"])
    
    def draw(self, surface):
        t = min(1, self.lifetime / self.duration)
        s = 1 - (t-1)**2
        boom_radius = 16 + 48 * s
        boom_width = int(2 + 16 * (1-s))
        pygame.draw.circle(surface, self.color, self.pos, boom_radius, width=boom_width)


class Impact(VFX):
    def __init__(self, pos, angle, shell_type, duration=0.5):
        super().__init__(duration)

        self.pos = pygame.Vector2(pos)
        self.direction = get_vec(1, angle)
        self.perpendicular = pygame.Vector2(-self.direction.y, self.direction.x)
        self.color = SHELL_COLORS.get(shell_type, SHELL_COLORS["normal"])

    def draw(self, surface):
        t = min(1, self.lifetime / self.duration)
        s = 1 - (2*t - 1)**2
        hit_pos = self.pos + 150 * (2*t-1) * self.direction
        hit_length = 100 * s
        hit_width = 10 * s
        hit_polygon = [
            hit_pos + self.direction * hit_length,
            hit_pos + self.perpendicular * hit_width,
            hit_pos - self.direction * hit_length,
            hit_pos - self.perpendicular * hit_width
        ]
        pygame.draw.polygon(surface, self.color, hit_polygon)


class GunFireVFXManager:
    def __init__(self):
        self.effects = []

    def clear(self):
        self.effects = []

    def spawn_muzzle_flash(self, pos, shell_render_angle, shell_type):
        self.effects.append(Sparks(pos, shell_render_angle, shell_type))
        self.effects.append(Boom(pos, shell_type))

    def spawn_impact(self, pos, shell_render_angle, shell_type):
        self.effects.append(Sparks(pos, shell_render_angle + math.radians(180), shell_type))
        self.effects.append(Boom(pos, shell_type))
        self.effects.append(Impact(pos, shell_render_angle, shell_type))

    def update(self, dt):
        for effect in self.effects:
            effect.update(dt)
        self.effects = [effect for effect in self.effects if not effect.expired]

    def draw(self, surface):
        overlay = pygame.Surface(surface.get_size(), flags=pygame.SRCALPHA)
        for effect in self.effects:
            effect.draw(overlay)
        surface.blit(overlay, (0, 0))
