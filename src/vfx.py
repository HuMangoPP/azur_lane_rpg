import math
import random
import pygame

from engine.util import get_vec
from src.constants import Color


SHELL_COLORS = {
    "normal": [(255, 249, 181), (209, 119, 0), (28, 9, 0), (222, 180, 11), (247, 77, 111)],
    "HE": [(112, 83, 0), (212, 165, 30), (255, 242, 97)],
    "AP": [(112, 83, 0), (212, 165, 30), (255, 242, 97)],
}

SHELL_SCALE = 1/1000

def shell_position(start_pos, target_pos, t):
    relpos = target_pos - start_pos
    distance = relpos.length()
    scale = distance * SHELL_SCALE
    shell_y = scale * distance * t * (t - 1)
    return start_pos + relpos * t + pygame.Vector2(0, shell_y)


class VFX:
    def __init__(self, duration, delay):
        self.lifetime = 0
        self.duration = duration
        self.delay = delay
    
    @property
    def expired(self):
        return self.lifetime >= self.duration

    def update(self, dt):
        if self.delay > 0:
            self.delay -= dt
            return
        self.lifetime += (dt + abs(self.delay))
        self.delay = 0


class Spark(VFX):
    def __init__(self, pos, angle, color, duration=0.3, delay=0, fly_distance=64, size=(12,4)):
        super().__init__(duration, delay)

        self.pos = pygame.Vector2(pos)
        self.color = color
        self.size = size
        self.fly_distance = fly_distance
        self.spark_angle = angle

    def draw(self, surface):
        if self.delay > 0:
            return
        
        t = min(1, self.lifetime / self.duration)
        quadratic_ease = 1 - (t-1)**2
        linear_decay = 1 - t
        spark_dir = get_vec(1, self.spark_angle)
        spark_perp = pygame.Vector2(-spark_dir.y, spark_dir.x)
        spark_length = self.size[0] * linear_decay
        spark_width = self.size[1] * linear_decay
        spark_pos = self.pos + spark_dir * self.fly_distance * quadratic_ease
        spark_polygon = [
            spark_pos + spark_dir * spark_length,
            spark_pos + spark_perp * spark_width,
            spark_pos - spark_dir * spark_length,
            spark_pos - spark_perp * spark_width
        ]
        pygame.draw.polygon(surface, self.color, spark_polygon)


class Ring(VFX):
    def __init__(self, pos, color, duration=0.3, delay=0, radius=64):
        super().__init__(duration, delay)

        self.pos = pygame.Vector2(pos)
        self.radius = radius
        self.color = color
    
    def draw(self, surface):
        if self.delay > 0:
            return
        
        t = min(1, self.lifetime / self.duration)
        quadratic_ease = 1 - (t-1)**2
        boom_radius = self.radius * quadratic_ease
        boom_width = 2 + 16 * (1 - quadratic_ease)
        boom_width = int(min(boom_radius, boom_width))
        pygame.draw.circle(surface, self.color, self.pos, boom_radius, width=boom_width)


class Slash(VFX):
    def __init__(self, pos, angle, color, delay=0, duration=0.2):
        super().__init__(duration, delay)

        self.pos = pygame.Vector2(pos)
        self.direction = get_vec(1, angle)
        self.perpendicular = pygame.Vector2(-self.direction.y, self.direction.x)
        self.color = color

    def draw(self, surface):
        if self.delay > 0:
            return
        
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


class Smoke(VFX):
    def __init__(self, pos, angle, color, duration=0.3, delay=0, size=50, drift_distance=70):
        super().__init__(duration, delay)

        self.pos = pygame.Vector2(pos)
        self.angle = angle
        self.color = color
        self.size = size
        self.drift_distance = drift_distance

    def draw(self, surface):
        if self.delay > 0:
            return
        
        smoke_surf = pygame.Surface((self.size, self.size))
        smoke_surf.set_colorkey((0, 0, 0))
        rect = smoke_surf.get_rect()
        pygame.draw.circle(smoke_surf, self.color, rect.center, self.size/2)

        t = min(1, self.lifetime / self.duration)
        offset_circle_pos = pygame.Vector2(rect.center) + get_vec(-self.size/2 + self.size/2*t, self.angle)
        offset_circle_size = self.size/1.5 * t
        pygame.draw.circle(smoke_surf, (0, 0, 0), offset_circle_pos, offset_circle_size)

        smoke_pos = self.pos + get_vec(self.drift_distance * t, self.angle)
        rect.center = smoke_pos
        surface.blit(smoke_surf, rect)


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
        colors = SHELL_COLORS.get(shell_type, SHELL_COLORS["normal"])
        for _ in range(random.randint(2,4)):
            spark_angle = shell_render_angle + math.radians(180 + random.randint(-30, 30))
            spark_color = random.choice([colors[0], colors[2]])
            spark_duration = random.uniform(0.3, 0.5)
            spark_distance = random.randint(80, 100)
            spark_size = (random.randint(40, 50), random.randint(8, 12))
            self.effects.append(Spark(
                pos, spark_angle, spark_color, duration=spark_duration, fly_distance=spark_distance, size=spark_size
            ))
        for _ in range(random.randint(3,5)):
            smoke_angle = math.radians(random.randint(210, 330))
            smoke_color = random.choice([colors[0], colors[2]])
            smoke_delay = random.uniform(0, 0.1)
            smoke_duration = random.uniform(0.3, 0.5)
            smoke_distance = random.uniform(40, 60)
            smoke_size = random.uniform(40, 60)
            self.effects.append(Smoke(
                pos, smoke_angle, smoke_color, duration=smoke_duration, delay=smoke_delay, drift_distance=smoke_distance, size=smoke_size
            ))
        self.effects.append(Slash(pos, shell_render_angle, colors[0]))

    def spawn_miss(self, pos):
        colors = [(191, 224, 255), (158, 208, 255), (107, 183, 255)]
        pos = pygame.Vector2(pos) + pygame.Vector2(0, 32)
        spark_pos = pos + pygame.Vector2(16, 0)
        for _ in range(random.randint(4,6)):
            spark_angle = math.radians(random.randint(300, 330))
            spark_color = random.choice(colors)
            spark_duration = random.uniform(0.4, 0.6)
            spark_distance = random.randint(60, 80)
            spark_size = (random.randint(24, 30), random.randint(6, 10))
            self.effects.append(Spark(
                spark_pos, spark_angle, spark_color, duration=spark_duration, fly_distance=spark_distance, size=spark_size
            ))
        spark_pos = pos - pygame.Vector2(16, 0)
        for _ in range(random.randint(4,6)):
            spark_angle = math.radians(random.randint(210, 240))
            spark_color = random.choice(colors)
            spark_duration = random.uniform(0.4, 0.6)
            spark_distance = random.randint(60, 80)
            spark_size = (random.randint(24, 30), random.randint(6, 10))
            self.effects.append(Spark(
                spark_pos, spark_angle, spark_color, duration=spark_duration, fly_distance=spark_distance, size=spark_size
            ))
        for _ in range(random.randint(8,12)):
            t = random.randint(-32, 32)
            spark_pos = pos + pygame.Vector2(t, 0)
            spark_color = random.choice(colors)
            spark_duration = random.uniform(0.4, 0.6)
            spark_distance = 120 - abs(t)
            spark_size = (random.randint(30, 40), random.randint(6, 10))
            self.effects.append(Spark(
                spark_pos, math.radians(270), spark_color, duration=spark_duration, fly_distance=spark_distance, size=spark_size
            ))
        for _ in range(random.randint(4, 6)):
            smoke_angle = math.radians(random.uniform(210, 330))
            smoke_color = random.choice(colors)
            smoke_duration = random.uniform(0.4, 0.6)
            smoke_delay = random.uniform(0, 0.1)
            smoke_size = random.randint(40, 60)
            smoke_distance = random.randint(70, 90)
            self.effects.append(Smoke(
                pos, smoke_angle, smoke_color, duration=smoke_duration, delay=smoke_delay, size=smoke_size, drift_distance=smoke_distance
            ))

    def update(self, dt):
        for effect in self.effects:
            effect.update(dt)
        self.effects = [effect for effect in self.effects if not effect.expired]

    def draw(self, surface):
        overlay = pygame.Surface(surface.get_size(), flags=pygame.SRCALPHA)
        for effect in self.effects:
            effect.draw(overlay)
        surface.blit(overlay, (0, 0))
