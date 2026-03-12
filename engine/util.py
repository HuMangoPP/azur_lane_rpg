import math
import pygame

def get_rect(width, height, left=None, centerx=None, right=None, top=None, centery=None, bottom=None):
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
    return rect

def get_vec(length, angle):
    return length * pygame.Vector2(math.cos(angle), math.sin(angle))

def draw_slice(screen, color, center, radius, start_angle, end_angle, width=0, resolution=10):
    points = [center]
    if end_angle > start_angle:
        current_angle = start_angle
        angles = []
        while current_angle < end_angle:
            angles.append(current_angle)
            current_angle += resolution
        angles.append(end_angle)
    else:
        current_angle = start_angle
        angles = []
        while current_angle > end_angle:
            angles.append(current_angle)
            current_angle -= resolution
        angles.append(end_angle)

    if len(angles) > 2:
        for angle in angles:
            vec = get_vec(radius, math.radians(angle))
            points.append(center + vec)
        
        pygame.draw.polygon(screen, color, points, width=width)

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
        cx = x + size * math.cos(angle)
        cy = y + size * math.sin(angle)
        corners.append((cx, cy))
    return corners