from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from engine.types import CoordinateType, ColorType
    from engine.font import Font

import math
import random
import pygame

from engine.vfx import VFX, BaseVFXManager, Spark, Ring, Slash, Smoke
from engine.util import get_vec
from src.constants import Equipment


SHELL_COLORS = {
    Equipment.NORMAL_SHELL: [(255, 249, 181), (209, 119, 0), (28, 9, 0), (222, 180, 11), (247, 77, 111)],
    Equipment.HE_SHELL: [(255, 249, 181), (209, 119, 0), (28, 9, 0), (222, 180, 11), (247, 77, 111)],
    Equipment.AP_SHELL: [(255, 249, 181), (209, 119, 0), (28, 9, 0), (222, 180, 11), (247, 77, 111)],
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
DAMAGE_COUNTER_COLORS = {
    Equipment.NORMAL_SHELL: ((255, 246, 126), (90, 65, 16)),
    Equipment.HE_SHELL: ((255, 94, 124), (88, 8, 31)),
    Equipment.AP_SHELL: ((105, 255, 255), (0, 76, 90)),
    Equipment.TORPEDO: ((158, 208, 255), (18, 60, 102)),
}


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
            DAMAGE_COUNTER_COLORS[Equipment.NORMAL_SHELL],
        )
        self.float_distance = 48
        self.font_registry_scale = 3 if crit else 2
        self.text_surf: pygame.Surface | None = None

    def draw(self, surface: pygame.Surface, font_registry: dict[str, Font]):
        """Draw the damage counter."""
        if self.delay > 0:
            return

        t = min(1, self.lifetime / self.duration)
        alpha = int(255 * min(1, (1 - t) * 1.5))
        y_offset = self.float_distance * (1 - (t - 1) ** 2)
        text_pos = self.pos - pygame.Vector2(0, y_offset)

        if self.text_surf is None:
            outline_padding = 2
            self.text_surf = pygame.Surface((
                font_registry["big_pixel"].get_width(
                    self.text, self.font_registry_scale, 0
                ) + outline_padding,
                font_registry["big_pixel"].get_height(
                    self.text, self.font_registry_scale, 0
                ) + outline_padding,
            ))
            self.text_surf.set_colorkey((0, 0, 0))
            font_registry["big_pixel"].render(
                self.text_surf,
                self.text,
                pygame.Vector2(self.text_surf.get_rect().center),
                self.color,
                self.font_registry_scale,
                style="center",
                outline_color=self.outline_color,
            )
        self.text_surf.set_alpha(alpha)

        rect = self.text_surf.get_rect(center=text_pos)
        surface.blit(self.text_surf, rect)


class VFXManager(BaseVFXManager):
    def __init__(self):
        super().__init__()
        self.wave_colors: list[ColorType] | None = None

    def spawn_muzzle_flash(self, pos: CoordinateType, shell_render_angle: float, shell_type: str):
        """Spawn a muzzle flash vfx group."""
        muzzle_flash_distance_from_pos = 20
        pos = pygame.Vector2(pos) + get_vec(muzzle_flash_distance_from_pos, shell_render_angle)
        colors = SHELL_COLORS.get(shell_type, SHELL_COLORS[Equipment.NORMAL_SHELL])
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
        for i, color in enumerate(self.wave_colors):
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
        colors = SHELL_COLORS.get(shell_type, SHELL_COLORS[Equipment.NORMAL_SHELL])
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
        if self.wave_colors is None:
            return

        vertical_offset_to_feet = pygame.Vector2(0, 32)
        pos = pygame.Vector2(pos) + vertical_offset_to_feet
        horizontal_spark_spawn_offset = pygame.Vector2(16, 0)
        # These sparks travel to the right, diagonally upward.
        spark_pos = pos + horizontal_spark_spawn_offset
        num_sparks = random.randint(4, 6)
        for _ in range(num_sparks):
            spark_angle = math.radians(random.randint(300, 330))
            spark_color = random.choice(self.wave_colors)
            spark_duration = random.uniform(0.4, 0.6)
            spark_distance = random.randint(60, 80)
            spark_size = (random.randint(24, 30), random.randint(6, 10))
            self.effects.append(Spark(spark_pos, spark_angle, spark_color, duration=spark_duration, fly_distance=spark_distance, size=spark_size))
        # These sparks travel to the left, diagonally upward.
        spark_pos = pos - horizontal_spark_spawn_offset
        num_sparks = random.randint(4, 6)
        for _ in range(num_sparks):
            spark_angle = math.radians(random.randint(210, 240))
            spark_color = random.choice(self.wave_colors)
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
            spark_color = random.choice(self.wave_colors)
            spark_duration = random.uniform(0.4, 0.6)
            spark_distance = 120 - abs(t)
            spark_size = (random.randint(30, 40), random.randint(6, 10))
            self.effects.append(Spark(spark_pos, spark_angle, spark_color, duration=spark_duration, fly_distance=spark_distance, size=spark_size))

        num_smokes = random.randint(4, 6)
        for _ in range(num_smokes):
            smoke_angle = math.radians(random.uniform(210, 330))
            smoke_color = random.choice(self.wave_colors)
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

        wake_colors = wake_colors or self.wave_colors
        if wake_colors is None:
            return

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
