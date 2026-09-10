from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from engine.types import ColorType, CoordinateType
    from engine.font import Font

import pygame

from engine.util import get_vec


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

    def draw( self, surface: pygame.Surface, font_registry: dict[str, Font]):
        """Draw the vfx."""


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
        self.spark_dir = get_vec(1, self.spark_angle)
        self.spark_perp = pygame.Vector2(-self.spark_dir.y, self.spark_dir.x)

    def draw(self, surface: pygame.Surface, font_registry: dict[str, Font]):
        """Draw the spark."""
        if self.delay > 0:
            return
        
        t = min(1, self.lifetime / self.duration)
        quadratic_ease = 1 - (t - 1) ** 2
        linear_decay = 1 - t
        spark_length = self.size[0] * linear_decay
        spark_width = self.size[1] * linear_decay
        spark_pos = self.pos + self.spark_dir * self.fly_distance * quadratic_ease
        spark_polygon = [
            spark_pos + self.spark_dir * spark_length,
            spark_pos + self.spark_perp * spark_width,
            spark_pos - self.spark_dir * spark_length,
            spark_pos - self.spark_perp * spark_width
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
        self.direction = get_vec(1, self.angle)
        self.smoke_surf = pygame.Surface((self.size, self.size))
        self.smoke_surf.set_colorkey((255, 0, 0))
        self.smoke_rect = self.smoke_surf.get_rect()
        self.smoke_center = pygame.Vector2(self.smoke_rect.center)

    def draw(self, surface: pygame.Surface, font_registry: dict[str, Font]):
        """Draw the smoke."""
        if self.delay > 0:
            return
        
        self.smoke_surf.fill((255, 0, 0))
        pygame.draw.circle(
            self.smoke_surf, self.color, self.smoke_center, self.size / 2
        )

        t = min(1, self.lifetime / self.duration)
        offset_circle_pos = (
            self.smoke_center
            + self.direction * (-self.size / 2 + self.size / 2 * t)
        )
        offset_circle_size = self.size / 1.5 * t
        pygame.draw.circle(self.smoke_surf, (255, 0, 0), offset_circle_pos, offset_circle_size)

        smoke_pos = self.pos + self.direction * self.drift_distance * t
        self.smoke_rect.center = smoke_pos
        return surface.blit(self.smoke_surf, self.smoke_rect)


class BaseVFXManager:
    def __init__(self):
        self.effects: list[VFX] = []

    def clear(self):
        """Clear the vfx."""
        self.effects = []

    def update(self, dt: float):
        """Update the vfx."""
        for effect in self.effects:
            effect.update(dt)
        self.effects = [effect for effect in self.effects if not effect.expired]

    def draw(self, surface: pygame.Surface, font_registry: dict[str, Font]):
        """Draw the vfx."""
        for effect in self.effects:
            effect.draw(surface, font_registry)
