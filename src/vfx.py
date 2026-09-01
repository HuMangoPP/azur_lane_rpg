from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from engine.types import CoordinateType, ColorType
    from engine.font import Font

import math
import random
import pygame

from engine.util import get_vec
from src.constants import Equipment


SHELL_COLORS = {
    "normal": [(255, 249, 181), (209, 119, 0), (28, 9, 0), (222, 180, 11), (247, 77, 111)],
    "HE": [(255, 249, 181), (209, 119, 0), (28, 9, 0), (222, 180, 11), (247, 77, 111)],
    "AP": [(255, 249, 181), (209, 119, 0), (28, 9, 0), (222, 180, 11), (247, 77, 111)],
}
FIRE_COLORS = [
    (255, 244, 128),
    (255, 164, 42),
    (238, 76, 34),
]
FIRE_SMOKE_COLORS = [
    (44, 35, 31),
    (77, 68, 62),
]
AIRCRAFT_LAUNCH_RING_COLORS = [
    (232, 236, 238),
    (126, 134, 140),
    (44, 50, 56),
]
AIRCRAFT_LAUNCH_SMOKE_COLORS = [
    (226, 230, 232),
    (198, 204, 208),
    (170, 178, 184),
]
TORPEDO_WAKE_COLORS = [
    (230, 246, 255),
    (191, 224, 255),
    (158, 208, 255),
    (107, 183, 255),
]
TORPEDO_LAUNCH_COLORS = [
    (245, 252, 255),
    (78, 192, 255),
    (18, 96, 190),
]
DAMAGE_COUNTER_COLORS = {
    "normal": ((255, 246, 126), (90, 65, 16)),
    "HE": ((255, 94, 124), (88, 8, 31)),
    "AP": ((105, 255, 255), (0, 76, 90)),
    "torpedo": ((158, 208, 255), (18, 60, 102)),
}

SHELL_SCALE = 1 / 1000

# TODO Not useful enough for common, but there is likely a better place for this function.
def shell_path(start_pos: pygame.Vector2, target_pos: pygame.Vector2, t: float) -> pygame.Vector2:
    """Compute a parabolic shell path from start to target, parametrized by t."""
    relpos = target_pos - start_pos
    distance = relpos.length()
    scale = distance * SHELL_SCALE
    shell_y = scale * distance * t * (t - 1)
    return start_pos + relpos * t + pygame.Vector2(0, shell_y)


class VFX:
    def __init__(self, duration: float, delay: float):
        self.lifetime = 0
        self.duration = duration
        self.delay = delay
    
    @property
    def expired(self) -> bool:
        """Check if the vfx is expired."""
        return self.lifetime >= self.duration

    def update(self, dt: float):
        """Update the vfx."""
        if self.delay > 0:
            self.delay -= dt
            return
        self.lifetime += (dt + abs(self.delay))
        self.delay = 0

    def draw(self, surface: pygame.Surface, font_registry: dict[str, Font]):
        """Draw the vfx."""
        pass


class Spark(VFX):
    def __init__(
        self,
        pos: CoordinateType,
        angle: float,
        color: ColorType,
        duration: float = 0.3,
        delay: float = 0,
        fly_distance: float = 64,
        size: CoordinateType = (12, 4)
    ):
        super().__init__(duration, delay)

        self.pos = pygame.Vector2(pos)
        self.color = color
        self.size = size
        self.fly_distance = fly_distance
        self.spark_angle = angle

    def draw(self, surface: pygame.Surface, font_registry: dict[str, Font]):
        """Draw the spark."""
        if self.delay > 0:
            return
        
        t = min(1, self.lifetime / self.duration)
        quadratic_ease = 1 - (t - 1) ** 2
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
    def __init__(
        self,
        pos: CoordinateType,
        color: ColorType,
        duration: float = 0.3,
        delay: float = 0,
        radius: float = 64
    ):
        super().__init__(duration, delay)

        self.pos = pygame.Vector2(pos)
        self.radius = radius
        self.color = color
    
    def draw(self, surface: pygame.Surface, font_registry: dict[str, Font]):
        """Draw the ring."""
        if self.delay > 0:
            return
        
        t = min(1, self.lifetime / self.duration)
        quadratic_ease = 1 - (t - 1) ** 2
        boom_radius = self.radius * quadratic_ease
        boom_width = 2 + 16 * (1 - quadratic_ease)
        boom_width = int(min(boom_radius, boom_width))
        pygame.draw.circle(surface, self.color, self.pos, boom_radius, width=boom_width)


class Slash(VFX):
    def __init__(
        self,
        pos: CoordinateType,
        angle: float,
        color: ColorType,
        delay: float = 0,
        duration: float = 0.2
    ):
        super().__init__(duration, delay)

        self.pos = pygame.Vector2(pos)
        self.direction = get_vec(1, angle)
        self.perpendicular = pygame.Vector2(-self.direction.y, self.direction.x)
        self.color = color

    def draw(self, surface: pygame.Surface, font_registry: dict[str, Font]):
        """Draw the slash."""
        if self.delay > 0:
            return
        
        t = min(1, self.lifetime / self.duration)
        linear_decay = 1 - t
        steep_rise = 2 * t - 1
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
    def __init__(
        self,
        pos: CoordinateType,
        angle: float,
        color: ColorType,
        duration: float = 0.3,
        delay: float = 0,
        size: float = 50,
        drift_distance: float = 70
    ):
        super().__init__(duration, delay)

        self.pos = pygame.Vector2(pos)
        self.angle = angle
        self.color = color
        self.size = int(size)
        self.drift_distance = drift_distance

    def draw(self, surface: pygame.Surface, font_registry: dict[str, Font]):
        """Draw the smoke."""
        if self.delay > 0:
            return
        
        smoke_surf = pygame.Surface((self.size, self.size))
        smoke_surf.set_colorkey((0, 0, 0))
        rect = smoke_surf.get_rect()
        pygame.draw.circle(smoke_surf, self.color, rect.center, self.size / 2)

        t = min(1, self.lifetime / self.duration)
        offset_circle_pos = pygame.Vector2(rect.center) + get_vec(-self.size / 2 + self.size / 2 * t, self.angle)
        offset_circle_size = self.size / 1.5 * t
        pygame.draw.circle(smoke_surf, (0, 0, 0), offset_circle_pos, offset_circle_size)

        smoke_pos = self.pos + get_vec(self.drift_distance * t, self.angle)
        rect.center = smoke_pos
        surface.blit(smoke_surf, rect)


class DamageCounter(VFX):
    def __init__(
        self,
        pos: CoordinateType,
        text: str,
        shell_type: str,
        crit: bool = False,
        duration: float = 2,
        delay: float = 0
    ):
        super().__init__(duration, delay)

        self.pos = pygame.Vector2(pos)
        self.text = text
        if crit:
            self.text += "!"
        self.color, self.outline_color = DAMAGE_COUNTER_COLORS.get(
            shell_type,
            DAMAGE_COUNTER_COLORS["normal"],
        )
        self.float_distance = 48
        self.font_registry_scale = 3 if crit else 2

    def draw(self, surface: pygame.Surface, font_registry: dict[str, Font]):
        """Draw the damage counter."""
        if self.delay > 0:
            return

        t = min(1, self.lifetime / self.duration)
        alpha = int(255 * min(1, (1 - t) * 1.5))
        y_offset = self.float_distance * (1 - (t - 1) ** 2)
        text_pos = self.pos - pygame.Vector2(0, y_offset)

        # TODO Consider implementing alpha capabilities directly into Font instead of using this workaround.
        outline_padding = 2
        text_surf = pygame.Surface((
            font_registry["big_pixel"].get_width(self.text, self.font_registry_scale, 0) + outline_padding,
            font_registry["big_pixel"].get_height(self.text, self.font_registry_scale, 0) + outline_padding,
        ))
        text_surf.set_colorkey((0, 0, 0))
        font_registry["big_pixel"].render(
            text_surf,
            self.text,
            pygame.Vector2(text_surf.get_rect().center),
            self.color,
            self.font_registry_scale,
            style="center",
            outline_color=self.outline_color,
        )
        text_surf.set_alpha(alpha)

        rect = text_surf.get_rect(center=text_pos)
        surface.blit(text_surf, rect)


# TODO Consider whether or not a trimmed version of this (i.e. only clear, update, and draw APIs)
# and the VFX classes deserved to be in the engine.
# Then the project specific vfx.py module can extend VFXManager with the project-specific particle spawning APIs.
class VFXManager:
    def __init__(self):
        self.effects: list[VFX] = []

    def clear(self):
        """Clear the vfx."""
        self.effects = []

    def spawn_muzzle_flash(self, pos: CoordinateType, shell_render_angle: float, shell_type: str):
        """Spawn a muzzle flash vfx group."""
        muzzle_flash_distance_from_pos = 20
        pos = pygame.Vector2(pos) + get_vec(muzzle_flash_distance_from_pos, shell_render_angle)
        colors = SHELL_COLORS.get(shell_type, SHELL_COLORS["normal"])
        num_rings = 3
        for i in range(num_rings):
            ring_duration = 0.5 - 0.1 * i
            ring_radius = 32 * (i + 1)
            self.effects.append(Ring(pos, colors[i], duration=ring_duration, radius=ring_radius))

        num_sparks = random.randint(18, 22)
        for _ in range(num_sparks):
            spark_angle = math.radians(random.randint(0, 359))
            spark_color = random.choice(colors)
            spark_duration = random.uniform(0.3, 0.5)
            spark_distance = random.randint(64, 128)
            spark_size = (random.randint(16, 27), random.randint(4, 9))
            self.effects.append(Spark(pos, spark_angle, spark_color, duration=spark_duration, fly_distance=spark_distance, size=spark_size))

    def spawn_torpedo_launch(self, pos: CoordinateType):
        """Spawn a torpedo launch vfx group."""
        # TODO Update the torpedo launch colors to match the weather condition wave colors.
        for i, color in enumerate(TORPEDO_LAUNCH_COLORS):
            ring_duration = 0.45 - 0.08 * i
            ring_radius = 24 + 18 * i
            self.effects.append(Ring(pos, color, duration=ring_duration, radius=ring_radius))

    def spawn_aircraft_launch(self, pos: CoordinateType, launch_angle: float):
        """Spawn an aircraft launch vfx group."""
        for i, color in enumerate(AIRCRAFT_LAUNCH_RING_COLORS):
            ring_duration = 0.48 - 0.07 * i
            ring_radius = 36 + 22 * i
            self.effects.append(Ring(pos, color, duration=ring_duration, radius=ring_radius))

        exhaust_angle = launch_angle + math.pi
        num_smokes = random.randint(4, 6)
        for _ in range(num_smokes):
            smoke_angle = exhaust_angle + math.radians(random.uniform(-35, 35))
            smoke_color = random.choice(AIRCRAFT_LAUNCH_SMOKE_COLORS)
            smoke_duration = random.uniform(0.35, 0.55)
            smoke_delay = random.uniform(0, 0.08)
            smoke_distance = random.uniform(48, 64)
            smoke_size = random.randint(24, 38)
            self.effects.append(Smoke(pos, smoke_angle, smoke_color, duration=smoke_duration, delay=smoke_delay, drift_distance=smoke_distance, size=smoke_size))

    def spawn_shell_impact(self, pos: CoordinateType, shell_render_angle: float, shell_type: str):
        """Spawn a shell impact vfx group."""
        colors = SHELL_COLORS.get(shell_type, SHELL_COLORS["normal"])
        lightest_color = colors[0]
        darkest_color = colors[2]
        num_sparks = random.randint(2, 4)
        for _ in range(num_sparks):
            spark_angle = shell_render_angle + math.radians(180 + random.randint(-30, 30))
            spark_color = random.choice([lightest_color, darkest_color])
            spark_duration = random.uniform(0.3, 0.5)
            spark_distance = random.randint(80, 100)
            spark_size = (random.randint(40, 50), random.randint(8, 12))
            self.effects.append(Spark(pos, spark_angle, spark_color, duration=spark_duration, fly_distance=spark_distance, size=spark_size))
        num_smokes = random.randint(3,5)
        for _ in range(num_smokes):
            smoke_angle = math.radians(random.randint(210, 330))
            smoke_color = random.choice([lightest_color, darkest_color])
            smoke_delay = random.uniform(0, 0.1)
            smoke_duration = random.uniform(0.3, 0.5)
            smoke_distance = random.uniform(40, 60)
            smoke_size = random.uniform(40, 60)
            self.effects.append(Smoke(pos, smoke_angle, smoke_color, duration=smoke_duration, delay=smoke_delay, drift_distance=smoke_distance, size=smoke_size))
        # Lightest color.
        self.effects.append(Slash(pos, shell_render_angle, lightest_color))

    def spawn_splash_impact(self, pos: CoordinateType):
        """Spawn a splash impact vfx group."""
        # TODO These colors should be based on the weather condition wave colors.
        colors = [(191, 224, 255), (158, 208, 255), (107, 183, 255)]
        vertical_offset_to_feet = pygame.Vector2(0, 32)
        pos = pygame.Vector2(pos) + vertical_offset_to_feet
        horizontal_spark_spawn_offset = pygame.Vector2(16, 0)
        # These sparks travel to the right, diagonally upward.
        spark_pos = pos + horizontal_spark_spawn_offset
        num_sparks = random.randint(4, 6)
        for _ in range(num_sparks):
            spark_angle = math.radians(random.randint(300, 330))
            spark_color = random.choice(colors)
            spark_duration = random.uniform(0.4, 0.6)
            spark_distance = random.randint(60, 80)
            spark_size = (random.randint(24, 30), random.randint(6, 10))
            self.effects.append(Spark(spark_pos, spark_angle, spark_color, duration=spark_duration, fly_distance=spark_distance, size=spark_size))
        # These sparks travel to the left, diagonally upward.
        spark_pos = pos - horizontal_spark_spawn_offset
        num_sparks = random.randint(4, 6)
        for _ in range(num_sparks):
            spark_angle = math.radians(random.randint(210, 240))
            spark_color = random.choice(colors)
            spark_duration = random.uniform(0.4, 0.6)
            spark_distance = random.randint(60, 80)
            spark_size = (random.randint(24, 30), random.randint(6, 10))
            self.effects.append(Spark(spark_pos, spark_angle, spark_color, duration=spark_duration, fly_distance=spark_distance, size=spark_size))
        # These sparks travel verticall upward.
        num_sparks = random.randint(8, 12)
        for _ in range(num_sparks):
            t = random.randint(-32, 32)
            spark_pos = pos + pygame.Vector2(t, 0)
            spark_angle = math.radians(270)
            spark_color = random.choice(colors)
            spark_duration = random.uniform(0.4, 0.6)
            spark_distance = 120 - abs(t)
            spark_size = (random.randint(30, 40), random.randint(6, 10))
            self.effects.append(Spark(spark_pos, spark_angle, spark_color, duration=spark_duration, fly_distance=spark_distance, size=spark_size))

        num_smokes = random.randint(4, 6)
        for _ in range(num_smokes):
            smoke_angle = math.radians(random.uniform(210, 330))
            smoke_color = random.choice(colors)
            smoke_duration = random.uniform(0.4, 0.6)
            smoke_delay = random.uniform(0, 0.1)
            smoke_size = random.randint(40, 60)
            smoke_distance = random.randint(70, 90)
            self.effects.append(Smoke(pos, smoke_angle, smoke_color, duration=smoke_duration, delay=smoke_delay, size=smoke_size, drift_distance=smoke_distance))

    def spawn_wake(
        self,
        pos: CoordinateType,
        torpedo_angle: float,
        upward_bias: float = -0.35,
        spark_chance: float = 1.0,
        spark_duration_range: CoordinateType = (0.18, 0.28),
        spark_distance_range: CoordinateType = (14, 26),
        spark_length_range: CoordinateType = (8, 14),
        spark_width_range: CoordinateType = (2, 4),
        smoke_chance: float = 0.35,
        smoke_duration_range: CoordinateType = (0.25, 0.4),
        smoke_distance_range: CoordinateType = (10, 18),
        smoke_size_range: CoordinateType = (12, 20),
        wake_colors: list[ColorType] = None,
    ):
        """Spawn a wake vfx group."""
        if random.random() > spark_chance:
            return

        wake_colors = wake_colors or TORPEDO_WAKE_COLORS
        backward_dir = get_vec(1, torpedo_angle + math.pi)
        wake_dir = (backward_dir + pygame.Vector2(0, upward_bias)).normalize()
        wake_angle = math.atan2(wake_dir.y, wake_dir.x)

        spark_angle = wake_angle + math.radians(random.uniform(-12, 12))
        spark_color = random.choice(wake_colors)
        spark_duration = random.uniform(*spark_duration_range)
        spark_distance = random.uniform(*spark_distance_range)
        spark_size = (random.uniform(*spark_length_range), random.uniform(*spark_width_range))
        self.effects.append(Spark(pos, spark_angle, spark_color, duration=spark_duration, fly_distance=spark_distance, size=spark_size))

        if random.random() > smoke_chance:
            return
        smoke_angle = wake_angle + math.radians(random.uniform(-20, 20))
        smoke_color = random.choice(wake_colors)
        smoke_duration = random.uniform(*smoke_duration_range)
        smoke_distance = random.uniform(*smoke_distance_range)
        smoke_size = random.uniform(*smoke_size_range)
        self.effects.append(Smoke(pos, smoke_angle, smoke_color, duration=smoke_duration, drift_distance=smoke_distance, size=smoke_size))

    def spawn_fire(self, rect: pygame.Rect):
        """Spawn on-fire particle effects."""
        spark_angle = math.radians(random.uniform(240, 300))
        spark_dir = get_vec(1, spark_angle)
        x = rect.centerx
        spark_bandwidth = rect.width * 0.2
        if spark_dir.x > 0:
            x += random.uniform(0, spark_bandwidth)
        elif spark_dir.x < 0:
            x -= random.uniform(0, spark_bandwidth)
        y = rect.centery + random.uniform(-rect.height * 0.2, rect.height * 0.3)
        flame_origin = pygame.Vector2(x, y)
        spark_color = random.choice(FIRE_COLORS)
        spark_duration = random.uniform(0.25, 0.45)
        spark_distance = random.uniform(22, 46)
        spark_size = (random.uniform(14, 24), random.uniform(4, 8))
        self.effects.append(Spark(flame_origin, spark_angle, spark_color, duration=spark_duration, fly_distance=spark_distance, size=spark_size))

        if random.random() > 0.35:
            return
        smoke_angle = math.radians(random.uniform(245, 295))
        smoke_dir = get_vec(1, smoke_angle)
        x = rect.centerx
        smoke_bandwidth = rect.width * 0.25
        if smoke_dir.x > 0:
            x += random.uniform(0, smoke_bandwidth)
        elif smoke_dir.x < 0:
            x -= random.uniform(0, smoke_bandwidth)
        y = rect.centery + random.uniform(-rect.height * 0.3, rect.height * 0.2)
        smoke_origin = pygame.Vector2(x, y)
        smoke_color = random.choice(FIRE_SMOKE_COLORS)
        smoke_duration = random.uniform(0.45, 0.7)
        smoke_size = random.uniform(18, 30)
        smoke_distance = random.uniform(28, 48)
        self.effects.append(Smoke(
            smoke_origin, smoke_angle, smoke_color, duration=smoke_duration, size=smoke_size, drift_distance=smoke_distance
        ))

    def spawn_damage_counter(
        self, pos: CoordinateType, damage: float, shell_type: str, crit: bool = False
    ):
        """Spawn a damage counter."""
        self.effects.append(DamageCounter(pos, str(damage), shell_type, crit=crit))

    def spawn_miss_counter(self, pos: CoordinateType):
        """Spawn a miss counter."""
        self.effects.append(DamageCounter(pos, "miss", Equipment.TORPEDO))

    def update(self, dt: float):
        """Update the vfx."""
        for effect in self.effects:
            effect.update(dt)
        self.effects = [effect for effect in self.effects if not effect.expired]

    def draw(self, surface: pygame.Surface, font_registry: dict[str, Font]):
        """Draw the vfx."""
        overlay = pygame.Surface(surface.get_size(), flags=pygame.SRCALPHA)
        for effect in self.effects:
            effect.draw(overlay, font_registry)
        surface.blit(overlay, (0, 0))
