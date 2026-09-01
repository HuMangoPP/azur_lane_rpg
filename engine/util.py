from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from engine.types import CoordinateType, ColorType

import math
import pygame


def get_rect(
    width: float,
    height: float,
    left: float | None = None,
    centerx: float | None = None,
    right: float | None = None,
    top: float | None = None,
    centery: float | None = None,
    bottom: float | None = None,
    center: CoordinateType | None = None
) -> pygame.Rect:
    """Return a rect with the inputted sizing and positioning."""
    rect = pygame.Rect(0, 0, width, height)
    if left is not None:
        rect.left = left
    if centerx is not None:
        rect.centerx = centerx
    if right is not None:
        rect.right = right
    if top is not None:
        rect.top = top
    if centery is not None:
        rect.centery = centery
    if bottom is not None:
        rect.bottom = bottom
    if center is not None:
        rect.center = center
    return rect

def get_vec(length: float, angle: float) -> pygame.Vector2:
    """Return a vector computed from the inputted length and angle."""
    return length * pygame.Vector2(math.cos(angle), math.sin(angle))

def draw_annulus(
    surface: pygame.Surface,
    color: ColorType,
    center: CoordinateType,
    inner_radius: float,
    outer_radius: float,
    start_angle: float,
    stop_angle: float,
    resolution: float = 10
):
    """Draw an annulus with the given parameters."""
    points = [pygame.Vector2(outer_radius, outer_radius)]
    current_angle = start_angle
    angles = []
    while current_angle < stop_angle:
        angles.append(current_angle)
        current_angle += resolution
    angles.append(stop_angle)
    if len(angles) > 2:
        for angle in angles:
            vec = get_vec(outer_radius, math.radians(angle))
            points.append(points[0] + vec)
        
        annulus = pygame.Surface((2*outer_radius, 2*outer_radius))
        annulus.fill((0, 0, 0))
        pygame.draw.polygon(annulus, color, points)
        pygame.draw.circle(annulus, (0, 0, 0), (outer_radius, outer_radius), inner_radius)
        annulus.set_colorkey((0, 0, 0))
        annulus_rect = annulus.get_rect()
        annulus_rect.center = center
        surface.blit(annulus, annulus_rect)

def hex_to_pixel(q: int, r: int, size: float) -> CoordinateType:
    """Compute the pixel position given a hex tile position."""
    x = size * (math.sqrt(3) * q + math.sqrt(3) / 2 * r)
    y = size * (3 / 2 * r)
    return (x, y)

def hex_round(q: float, r: float) -> CoordinateType:
    """Round decimal hex coordinates into integral hex-coordinates."""
    x = q
    z = r
    y = -x - z

    rx = round(x)
    ry = round(y)
    rz = round(z)

    dx = abs(rx - x)
    dy = abs(ry - y)
    dz = abs(rz - z)

    if dx > dy and dx > dz:
        rx = -ry - rz
    elif dy > dz:
        ry = -rx - rz
    else:
        rz = -rx - ry

    return rx, rz

def pixel_to_hex(x: float, y: float, size: float) -> CoordinateType:
    """Compute the coordinates of the hex containing the input point."""
    q = (math.sqrt(3)/3 * x - 1/3 * y) / size
    r = (2/3 * y) / size

    return hex_round(q, r)

def hex_corners(x: float, y: float, size: float) -> list[CoordinateType]:
    """Generate the corners of a hexagon with a pointy top."""
    corners = []
    for i in range(6):
        angle = math.radians(60 * i - 30)
        cx = round(x + size * math.cos(angle), 2)
        cy = round(y + size * math.sin(angle), 2)
        corners.append((cx, cy))
    return corners

HEX_DIRECTIONS = [(1, 0), (0, 1), (-1, 1), (-1, 0), (0, -1), (1, -1)]

def get_cluster_edges(cluster_hexes: list[CoordinateType], size: float) -> list[CoordinateType]:
    """Compute the vertices of a cluster of hexes."""
    cluster_set = set(cluster_hexes)
    edges = {}

    for q, r in cluster_hexes:

        x, y = hex_to_pixel(q, r, size)
        corners = hex_corners(x, y, size)

        for i, (dq, dr) in enumerate(HEX_DIRECTIONS):

            neighbor = (q + dq, r + dr)

            if neighbor not in cluster_set:
                c1 = corners[i]
                c2 = corners[(i + 1) % 6]

                edges[c1] = c2

    c = c1
    polygon = [c]
    while edges[c] not in polygon:
        c = edges[c]
        polygon.append(c)

    return polygon

def adjacent_hexes(q: int, r: int, steps: int) -> set[CoordinateType]:
    """Compute the set of hexes adjacent to the inputted hex, at most step tiles away."""
    adjacent = {(q, r)}
    if steps <= 0:
        return adjacent
    for dq, dr in HEX_DIRECTIONS:
        adjacent |= adjacent_hexes(q + dq, r + dr, steps-1)
    return adjacent

def draw_dashed_rect(
    surface: pygame.Surface,
    color: ColorType,
    rect: pygame.Rect,
    dash_length: int,
    gap_length: int,
    width: int,
):
    """Draw a rectangle with a dashed border."""
    right = rect.right - 1
    bottom = rect.bottom - 1
    dash_step = dash_length + gap_length

    for x in range(rect.left, right + 1, dash_step):
        dash_right = min(x + dash_length, right)
        pygame.draw.line(surface, color, (x, rect.top), (dash_right, rect.top), width)
        pygame.draw.line(surface, color, (x, bottom), (dash_right, bottom), width)

    for y in range(rect.top, bottom + 1, dash_step):
        dash_bottom = min(y + dash_length, bottom)
        pygame.draw.line(surface, color, (rect.left, y), (rect.left, dash_bottom), width)
        pygame.draw.line(surface, color, (right, y), (right, dash_bottom), width)
