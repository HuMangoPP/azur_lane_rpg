import math
import pygame

def get_rect(width, height, left=None, centerx=None, right=None, top=None, centery=None, bottom=None, center=None):
    rect = pygame.Rect(0,0,width,height)
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

def get_vec(length, angle):
    return length * pygame.Vector2(math.cos(angle), math.sin(angle))

def draw_annulus(surface, color, center, inner_radius, outer_radius, start_angle, stop_angle, resolution=10):
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
        annulus.fill((0,0,0))
        pygame.draw.polygon(annulus, color, points)
        pygame.draw.circle(annulus, (0,0,0), (outer_radius, outer_radius), inner_radius)
        annulus.set_colorkey((0,0,0))
        annulus_rect = annulus.get_rect()
        annulus_rect.center = center
        surface.blit(annulus, annulus_rect)

def hex_to_pixel(q, r, size):
    x = size * (math.sqrt(3) * q + math.sqrt(3)/2 * r)
    y = size * (3/2 * r)
    return (x, y)

def hex_round(q, r):

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

def pixel_to_hex(x, y, size):

    q = (math.sqrt(3)/3 * x - 1/3 * y) / size
    r = (2/3 * y) / size

    return hex_round(q, r)

def hex_corners(x, y, size):
    corners = []
    for i in range(6):
        angle = math.radians(60 * i - 30)  # pointy top
        cx = round(x + size * math.cos(angle), 2)
        cy = round(y + size * math.sin(angle), 2)
        corners.append((cx, cy))
    return corners

HEX_DIRECTIONS = [(1,0), (0,1), (-1,1), (-1,0), (0,-1), (1,-1)]

def get_cluster_edges(cluster_hexes, size):

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