import math
import random
import pygame

from engine.util import get_vec


SHELL_COLORS = {
    "normal": {
        "core": (255, 248, 180),
        "hot": (255, 206, 72),
        "edge": (255, 128, 32),
        "smoke": (100, 96, 86),
    },
    "HE": {
        "core": (255, 238, 170),
        "hot": (255, 80, 28),
        "edge": (220, 20, 44),
        "smoke": (112, 78, 64),
    },
    "AP": {
        "core": (225, 255, 255),
        "hot": (75, 234, 255),
        "edge": (46, 132, 255),
        "smoke": (78, 98, 112),
    },
}


HULL_FLASH_SCALE = {
    "DD": 0.75,
    "CL": 0.9,
    "CA": 1.05,
    "BB": 1.3,
}

SHELL_SCALE = 1/1000

def shell_position(start_pos, target_pos, t):
    relpos = target_pos - start_pos
    distance = relpos.length()
    scale = distance * SHELL_SCALE
    shell_y = scale * distance * t * (t - 1)
    return start_pos + relpos * t + pygame.Vector2(0, shell_y)


class MuzzleFlashEffect:
    DURATION = 1.0

    def __init__(self, start_pos, target_pos, shell_type, hull_type):
        self.pos = pygame.Vector2(start_pos)
        self.direction = (pygame.Vector2(target_pos) - self.pos).normalize()
        self.palette = SHELL_COLORS.get(shell_type, SHELL_COLORS["normal"])
        self.scale = HULL_FLASH_SCALE.get(hull_type, 1)
        self.age = 0

    @property
    def expired(self):
        return self.age >= self.DURATION

    def update(self, dt):
        self.age += dt

    def draw(self, surface):
        t = min(1, self.age / self.DURATION)
        fade = 1 - t
        radius = (18 + 16 * t) * self.scale
        core_radius = max(2, radius * 0.35)
        angle = math.atan2(self.direction.y, self.direction.x)

        for offset, length_scale in [(-0.45, 0.75), (0, 1.15), (0.45, 0.75)]:
            end = self.pos + get_vec(radius * length_scale, angle + offset)
            pygame.draw.line(
                surface,
                (*self.palette["edge"], int(180 * fade)),
                self.pos,
                end,
                max(2, int(5 * self.scale * fade)),
            )

        pygame.draw.circle(surface, (*self.palette["hot"], int(150 * fade)), self.pos, radius, width=2)
        pygame.draw.circle(surface, (*self.palette["core"], int(230 * fade)), self.pos, core_radius)


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
            width = max(1, int(8 * fade))
            pygame.draw.line(
                surface,
                (*self.palette["hot"], alpha),
                start,
                end,
                width,
            )


class ImpactEffect:
    DURATION = 0.34

    def __init__(self, pos, shell_type, hit):
        self.pos = pygame.Vector2(pos)
        if not hit:
            self.pos += pygame.Vector2(random.uniform(-18, 18), random.uniform(-12, 12))
        self.palette = SHELL_COLORS.get(shell_type, SHELL_COLORS["normal"])
        self.hit = hit
        self.age = 0
        self.sparks = []

        spark_count = 12 if hit else 6
        spark_speed = 170 if hit else 95
        for _ in range(spark_count):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(spark_speed * 0.35, spark_speed)
            self.sparks.append({
                "pos": self.pos.copy(),
                "vel": get_vec(speed, angle),
                "life": random.uniform(0.12, self.DURATION),
            })

    @property
    def expired(self):
        return self.age >= self.DURATION

    def update(self, dt):
        self.age += dt
        for spark in self.sparks:
            spark["pos"] += spark["vel"] * dt
            spark["vel"] *= max(0, 1 - 4 * dt)

    def draw(self, surface):
        t = min(1, self.age / self.DURATION)
        fade = 1 - t
        center = (int(self.pos.x), int(self.pos.y))
        radius = int((12 if self.hit else 8) + (34 if self.hit else 18) * t)

        ring_color = self.palette["edge"] if self.hit else (220, 248, 255)
        pygame.draw.circle(surface, (*ring_color, int(180 * fade)), center, radius, width=2)
        pygame.draw.circle(surface, (*self.palette["core"], int(140 * fade)), center, max(2, radius // 3))

        smoke_radius = int((10 if self.hit else 6) + 20 * t)
        pygame.draw.circle(surface, (*self.palette["smoke"], int(70 * fade)), center, smoke_radius)

        for spark in self.sparks:
            spark_fade = max(0, 1 - self.age / spark["life"])
            if spark_fade <= 0:
                continue
            pos = spark["pos"]
            pygame.draw.circle(
                surface,
                (*self.palette["hot"], int(210 * spark_fade)),
                (int(pos.x), int(pos.y)),
                max(1, int(3 * spark_fade)),
            )


class GunFireVFXManager:
    def __init__(self):
        self.effects = []

    def clear(self):
        self.effects = []

    def spawn_muzzle_flash(self, start_pos, target_pos, shell_type, hull_type):
        self.effects.append(MuzzleFlashEffect(start_pos, target_pos, shell_type, hull_type))

    def spawn_tracer(self, start_pos, target_pos, shell_type, shell_speed):
        self.effects.append(TracerEffect(start_pos, target_pos, shell_type, shell_speed))

    def spawn_impact(self, pos, shell_type, hit):
        self.effects.append(ImpactEffect(pos, shell_type, hit))

    def update(self, dt):
        for effect in self.effects:
            effect.update(dt)
        self.effects = [effect for effect in self.effects if not effect.expired]

    def draw(self, surface):
        overlay = pygame.Surface(surface.get_size(), flags=pygame.SRCALPHA)
        for effect in self.effects:
            effect.draw(overlay)
        surface.blit(overlay, (0, 0))
