import math
import random
import pygame

from engine.util import get_vec
from src.constants import Color


SHELL_COLORS = {
    "normal": [(255, 249, 181), (209, 119, 0), (26, 8, 0), (222, 180, 11), (247, 77, 111)],
    "HE": [(112, 83, 0), (212, 165, 30), (255, 242, 97)],
    "AP": [(112, 83, 0), (212, 165, 30), (255, 242, 97)],
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


class Spark(VFX):
    def __init__(self, pos, angle, color, duration=0.3, fly_distance=64, size=(12,4)):
        super().__init__(duration)

        self.pos = pygame.Vector2(pos)
        self.color = color
        self.size = size
        self.fly_distance = fly_distance
        self.spark_angle = angle
        self.spark_scale = random.uniform(0.8, 1.2)

    def draw(self, surface):
        t = min(1, self.lifetime / self.duration)
        quadratic_ease = 1 - (t-1)**2
        linear_decay = 1 - t
        spark_dir = get_vec(1, self.spark_angle)
        spark_perp = pygame.Vector2(-spark_dir.y, spark_dir.x)
        spark_length = self.size[0] * linear_decay * self.spark_scale
        spark_width = self.size[1] * linear_decay * self.spark_scale
        spark_pos = self.pos + spark_dir * self.fly_distance * quadratic_ease * self.spark_scale
        spark_polygon = [
            spark_pos + spark_dir * spark_length,
            spark_pos + spark_perp * spark_width,
            spark_pos - spark_dir * spark_length,
            spark_pos - spark_perp * spark_width
        ]
        pygame.draw.polygon(surface, self.color, spark_polygon)


class Ring(VFX):
    def __init__(self, pos, color, duration=0.3, radius=64):
        super().__init__(duration)

        self.pos = pygame.Vector2(pos)
        self.radius = radius
        self.color = color
    
    def draw(self, surface):
        t = min(1, self.lifetime / self.duration)
        quadratic_ease = 1 - (t-1)**2
        boom_radius = self.radius * quadratic_ease
        boom_width = 2 + 16 * (1 - quadratic_ease)
        boom_width = int(min(boom_radius, boom_width))
        pygame.draw.circle(surface, self.color, self.pos, boom_radius, width=boom_width)


class Slash(VFX):
    def __init__(self, pos, angle, color, duration=0.2):
        super().__init__(duration)

        self.pos = pygame.Vector2(pos)
        self.direction = get_vec(1, angle)
        self.perpendicular = pygame.Vector2(-self.direction.y, self.direction.x)
        self.color = color

    def draw(self, surface):
        t = min(1, self.lifetime / self.duration)
        linear_decay = 1 - t
        steep_rise = 2*t - 1
        hit_pos = self.pos + 100 * steep_rise * self.direction
        hit_length = 100 + 50 * linear_decay
        hit_width = 5 + 2 * linear_decay
        hit_polygon = [
            hit_pos + self.direction * hit_length,
            hit_pos + self.perpendicular * hit_width,
            hit_pos - self.direction * hit_length,
            hit_pos - self.perpendicular * hit_width
        ]
        pygame.draw.polygon(surface, self.color, hit_polygon)


class Drops(VFX):
    COLORS = [
        (81, 149, 245),
        (36, 115, 227),
        (14, 81, 176),
    ]

    def __init__(self, pos, duration=1, num_drops=(8,10)):
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
        quadratic_decay = 1 - t**2
        drop_alpha = int(255 * quadratic_decay)
        drop_radius = 16 * linear_decay + 2
        for traj_width, traj_height, drop_color in self.drops:
            drop_pos = self.pos + pygame.Vector2(
                traj_width * t,
                -traj_height * 4 * t * linear_decay
            )
            pygame.draw.circle(surface, (*drop_color, drop_alpha), drop_pos, drop_radius)


class VFXManager:
    def __init__(self):
        self.effects = []

    def clear(self):
        self.effects = []

    def spawn_muzzle_flash(self, pos, shell_render_angle, shell_type):
        pos = pygame.Vector2(pos) + get_vec(20, shell_render_angle)
        colors = SHELL_COLORS.get(shell_type, SHELL_COLORS["normal"])
        for i in range(3):
            self.effects.append(Ring(pos, colors[i], duration=0.5-0.1*i, radius=32*(i+1)))
        for _ in range(random.randint(18,22)):
            spark_angle = math.radians(random.randint(0, 359))
            spark_color = random.choice(colors)
            spark_duration = random.uniform(0.3, 0.5)
            spark_distance = random.randint(64, 128)
            spark_size = (random.randint(16, 27), random.randint(4, 9))
            self.effects.append(Spark(
                pos, spark_angle, spark_color, duration=spark_duration, fly_distance=spark_distance, size=spark_size
            ))

    def spawn_impact(self, pos, shell_render_angle, shell_type):
        color = SHELL_COLORS.get(shell_type, SHELL_COLORS["normal"])[0]
        for _ in range(random.randint(2,4)):
            spark_angle = shell_render_angle + math.radians(180 + random.randint(-30, 30))
            spark_duration = random.uniform(0.2, 0.4)
            spark_distance = random.randint(80, 110)
            spark_size = (random.randint(30, 40), random.randint(6, 10))
            self.effects.append(Spark(
                pos, spark_angle, color, duration=spark_duration, fly_distance=spark_distance, size=spark_size
            ))
        self.effects.append(Slash(pos, shell_render_angle, color))

    def spawn_miss(self, pos):
        pos = pygame.Vector2(pos) + pygame.Vector2(0, 32)
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
