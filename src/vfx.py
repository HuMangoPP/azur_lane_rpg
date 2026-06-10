import math
import random
import pygame

from engine.util import get_vec
from src.constants import Color


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
    def __init__(self, pos, angle, shell_type, duration=0.5, num_sparks=(3,5)):
        super().__init__(duration)

        self.pos = pygame.Vector2(pos)
        self.color = SHELL_COLORS.get(shell_type, SHELL_COLORS["normal"])

        self.sparks = []
        for _ in range(random.randint(*num_sparks)):
            spark_angle = angle + math.radians(random.randint(-45, 45))
            spark_scale = random.uniform(0.8, 1.2)
            self.sparks.append((spark_angle, spark_scale))

    def draw(self, surface):
        num_delays = 5
        for delay_index in range(num_delays):
            t_delay = delay_index / (num_delays-1)
            t = min(1, self.lifetime / self.duration) - (1-t_delay) / 10
            if t < 0:
                continue
            quadratic_ease = 1 - (t-1)**2
            linear_decay = 1 - t
            alpha = int(255 * t_delay)
            for spark_angle, spark_scale in self.sparks:
                spark_dir = get_vec(1, spark_angle)
                spark_perp = pygame.Vector2(-spark_dir.y, spark_dir.x)
                spark_width = 6 * linear_decay * spark_scale
                spark_length = 3 * spark_width
                spark_pos = self.pos + spark_dir * 150 * quadratic_ease * spark_scale
                spark_polygon = [
                    spark_pos + 2*spark_dir * spark_length,
                    spark_pos + spark_perp * spark_width,
                    spark_pos - spark_dir * spark_length,
                    spark_pos - spark_perp * spark_width
                ]
                pygame.draw.polygon(surface, (*Color.WHITE, alpha), spark_polygon)


class Boom(VFX):
    def __init__(self, pos, shell_type, duration=0.3):
        super().__init__(duration)

        self.pos = pos
        self.color = SHELL_COLORS.get(shell_type, SHELL_COLORS["normal"])
    
    def draw(self, surface):
        num_delays = 5
        for delay_index in range(num_delays):
            t_delay = delay_index / (num_delays-1)
            t = min(1, self.lifetime / self.duration) - (1-t_delay) / 7
            if t < 0:
                continue
            alpha = int(255 * t_delay)
            quadratic_ease = 1 - (t-1)**2
            boom_radius = 96 * quadratic_ease
            boom_width = 2 + 16 * (1 - quadratic_ease)
            boom_width = int(min(boom_radius, boom_width))
            pygame.draw.circle(surface, (*Color.WHITE, alpha), self.pos, boom_radius, width=boom_width)


class Impact(VFX):
    def __init__(self, pos, angle, shell_type, duration=0.5):
        super().__init__(duration)

        self.pos = pygame.Vector2(pos)
        self.direction = get_vec(1, angle)
        self.perpendicular = pygame.Vector2(-self.direction.y, self.direction.x)
        self.color = SHELL_COLORS.get(shell_type, SHELL_COLORS["normal"])

    def draw(self, surface):
        t = min(1, self.lifetime / self.duration)
        linear_decay = 1 - t
        steep_rise = 2*t - 1
        hit_pos = self.pos + 200 * steep_rise * self.direction
        hit_length = 150 * linear_decay
        hit_width = 10 * linear_decay
        hit_polygon = [
            hit_pos + self.direction * hit_length,
            hit_pos + self.perpendicular * hit_width,
            hit_pos - self.direction * hit_length,
            hit_pos - self.perpendicular * hit_width
        ]
        pygame.draw.polygon(surface, Color.WHITE, hit_polygon)


class Drops(VFX):
    COLORS = [
        (81, 149, 245),
        (36, 115, 227),
        (14, 81, 176),
    ]

    def __init__(self, pos, duration=1, num_drops=(6,8)):
        super().__init__(duration)

        self.pos = pygame.Vector2(pos)

        self.drops = []
        for _ in range(random.randint(*num_drops)):
            width = 64 * random.uniform(-1, 1)
            height = random.uniform(32, 64)
            color = random.choice(self.COLORS)
            self.drops.append((width, height, color))

    def draw(self, surface):
        t = min(1, self.lifetime / self.duration)
        linear_decay = 1 - t
        drop_radius = 16 * linear_decay + 2
        for traj_width, traj_height, drop_color in self.drops:
            drop_pos = self.pos + pygame.Vector2(
                traj_width * t,
                -traj_height * 4 * t * linear_decay
            )
            pygame.draw.circle(surface, drop_color, drop_pos, drop_radius)


class VFXManager:
    def __init__(self):
        self.effects = []

    def clear(self):
        self.effects = []

    def spawn_muzzle_flash(self, pos, shell_render_angle, shell_type):
        self.effects.append(Sparks(pos, shell_render_angle, shell_type))
        self.effects.append(Boom(pos, shell_type))

    def spawn_impact(self, pos, shell_render_angle, shell_type):
        self.effects.append(Sparks(pos, shell_render_angle + math.radians(180), shell_type))
        self.effects.append(Sparks(pos, shell_render_angle, shell_type, num_sparks=(2,3)))
        self.effects.append(Boom(pos, shell_type))
        self.effects.append(Impact(pos, shell_render_angle, shell_type))

    def spawn_miss(self, pos):
        self.effects.append(Drops(pos))

    def update(self, dt):
        for effect in self.effects:
            effect.update(dt)
        self.effects = [effect for effect in self.effects if not effect.expired]

    def draw(self, surface):
        overlay = pygame.Surface(surface.get_size(), flags=pygame.SRCALPHA)
        for effect in self.effects:
            effect.draw(overlay)
        surface.blit(overlay, (0, 0))
