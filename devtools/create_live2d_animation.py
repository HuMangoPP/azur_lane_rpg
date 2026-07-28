import argparse
import json
import math
import os
import sys
from pathlib import Path

import pygame

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from live2d.live2d import LAYER_SIZE, PART_NAMES, Live2D
from migrate_live2d_models import migrate_file


ANIMATIONS = [
    Live2D.IDLE_ANIMATION,
    Live2D.WALK_ANIMATION,
    Live2D.ATTACK_ANIMATION,
    Live2D.SINK_ANIMATION,
]

WINDOW_SIZE = (640, 480)
MODEL_SCALE = 3
BACKGROUND_COLOR = (24, 24, 28)
TEXT_COLOR = (230, 230, 230)
MUTED_TEXT_COLOR = (150, 150, 160)
TIMELINE_MARGIN = 40
TIMELINE_Y_OFFSET = 58
KEYFRAME_RADIUS = 7
SELECTED_KEYFRAME_RADIUS = 10
TIMELINE_COLOR = (80, 80, 90)
KEYFRAME_COLOR = (180, 180, 190)
SELECTED_KEYFRAME_COLOR = (250, 220, 80)
PLAYHEAD_COLOR = (90, 210, 255)
CURSOR_COLOR = (245, 245, 245)
PIVOT_COLOR = (255, 90, 120)


def model_path_for(shipgirl):
    return os.path.join("live2d", f"{shipgirl}.json")


def default_keyframe_animation():
    return {"keyframes": {"0": {}}}


def default_part_animation():
    return {"offset": [0, 0], "rotation": 0}


def save_model(model_path, model):
    with open(model_path, "w") as f:
        json.dump(model, f, indent=4)
        f.write("\n")


def next_animation_index(index, direction=1):
    return (index + direction) % len(ANIMATIONS)


def next_layer_index(index, direction=1):
    return (index + direction) % len(Live2D.DRAW_ORDER)


def keyframe_time(keyframe_index):
    return keyframe_index * Live2D.KEYFRAME_DURATION


def timeline_end_time():
    return keyframe_time(Live2D.NUM_FRAMES - 1)


def draw_live2d_scaled(surface, live2d, center, selected_layer, edit_mode):
    model_size = LAYER_SIZE * 2
    model_surface = pygame.Surface((model_size, model_size))
    model_surface.fill((255, 0, 0))
    model_surface.set_colorkey((255, 0, 0))

    alpha = 128 if edit_mode is not None else 255
    root = pygame.Vector2(model_size // 2, model_size // 2)
    live2d.draw(model_surface, root.x, root.y, False, alpha)
    if edit_mode is not None and selected_layer in live2d.parts:
        live2d.parts[selected_layer].draw(model_surface, root, False)

    scaled_size = model_size * MODEL_SCALE
    scaled = pygame.transform.scale(model_surface, (scaled_size, scaled_size))
    rect = scaled.get_rect(center=center)
    surface.blit(scaled, rect)


def get_live2d_rect(surface):
    scaled_size = LAYER_SIZE * 2 * MODEL_SCALE
    rect = pygame.Rect(0, 0, scaled_size, scaled_size)
    rect.center = surface.get_rect().center
    return rect


def screen_to_model_pos(surface, pos):
    live2d_rect = get_live2d_rect(surface)
    return (pygame.Vector2(pos) - pygame.Vector2(live2d_rect.topleft)) / MODEL_SCALE


def get_part_pivot_model_pos(live2d, part_name):
    part = live2d.parts[part_name]
    root = pygame.Vector2(LAYER_SIZE, LAYER_SIZE)
    return root + part.get_pivot_offset()


def get_part_pivot_pos(surface, live2d, part_name):
    model_pos = get_part_pivot_model_pos(live2d, part_name)
    live2d_rect = get_live2d_rect(surface)
    return pygame.Vector2(live2d_rect.topleft) + model_pos * MODEL_SCALE


def angle_to_pivot(surface, live2d, part_name, pos):
    delta = screen_to_model_pos(surface, pos) - get_part_pivot_model_pos(live2d, part_name)
    if delta.length_squared() == 0:
        return 0
    return -math.degrees(math.atan2(delta.y, delta.x))


def draw_part_pivot(surface, live2d, selected_layer, edit_mode):
    if edit_mode != "rotate" or selected_layer not in live2d.parts:
        return

    pivot_pos = get_part_pivot_pos(surface, live2d, selected_layer)
    pygame.draw.circle(surface, PIVOT_COLOR, pivot_pos, 7, 2)
    pygame.draw.line(surface, PIVOT_COLOR, (pivot_pos.x - 10, pivot_pos.y), (pivot_pos.x + 10, pivot_pos.y), 2)
    pygame.draw.line(surface, PIVOT_COLOR, (pivot_pos.x, pivot_pos.y - 10), (pivot_pos.x, pivot_pos.y + 10), 2)


def current_animation_key(animation_index):
    return ANIMATIONS[animation_index]


def get_or_create_keyframe(live2d, part, animation_key, keyframe_index):
    animation = live2d.model_dict["animations"].setdefault(animation_key, default_keyframe_animation())
    keyframes = animation.setdefault("keyframes", {"0": {}})

    if str(keyframe_index) in keyframes:
        keyframe = keyframes[str(keyframe_index)].setdefault(part, default_part_animation())
        live2d.refresh_animations()
        return keyframe[part]

    keyframe = {part: default_part_animation()}
    keyframes[str(keyframe_index)] = keyframe
    live2d.refresh_animations()
    return keyframe[part]


def reset_keyframe(live2d, part, animation_key, selected_keyframe_index, edit_mode):
    animation = live2d.model_dict["animations"].setdefault(animation_key, default_keyframe_animation())
    keyframes = animation.setdefault("keyframes", {"0": {}})

    if edit_mode == "rotate":
        keyframe = get_or_create_keyframe(live2d, part, animation_key, selected_keyframe_index)
        keyframe["rotation"] = 0
    elif edit_mode == "translate":
        keyframe = get_or_create_keyframe(live2d, part, animation_key, selected_keyframe_index)
        keyframe["offset"] = [0, 0]
    elif selected_keyframe_index == 0:
        keyframe = keyframes["0"]
        keyframe.pop(part)
    else:
        animation["keyframes"] = {
            keyframe_index: keyframe for keyframe_index, keyframe in keyframes.items()
            if keyframe_index != selected_keyframe_index
        }
        if not animation["keyframes"]:
            animation["keyframes"] = {"0": {}}
    live2d.refresh_animations()


def set_part_keyframe_offset(live2d, part, keyframe, offset):
    keyframe.setdefault(part, default_part_animation())
    keyframe[part]["offset"] = [offset.x, offset.y]
    live2d.refresh_animations()


def set_part_keyframe_rotation(live2d, part, keyframe, rotation):
    keyframe.setdefault(part, default_part_animation())
    keyframe[part]["rotation"] = rotation
    live2d.refresh_animations()


def draw_text(surface, font, text, pos, color=TEXT_COLOR):
    surface.blit(font.render(text, True, color), pos)


def draw_cursor(surface, edit_mode):
    x, y = pygame.mouse.get_pos()

    if edit_mode == "translate":
        pygame.draw.line(surface, CURSOR_COLOR, (x - 12, y), (x + 12, y), 2)
        pygame.draw.line(surface, CURSOR_COLOR, (x, y - 12), (x, y + 12), 2)
    elif edit_mode == "rotate":
        pygame.draw.circle(surface, CURSOR_COLOR, (x, y), 12, 2)
    else:
        pygame.draw.polygon(surface, CURSOR_COLOR, [(x, y), (x, y + 18), (x + 12, y + 12)])
        pygame.draw.polygon(surface, (20, 20, 24), [(x + 3, y + 5), (x + 3, y + 14), (x + 9, y + 11)])


def get_timeline_points(surface):
    y = surface.get_height() - TIMELINE_Y_OFFSET
    start_x = TIMELINE_MARGIN
    end_x = surface.get_width() - TIMELINE_MARGIN
    frame_count = Live2D.NUM_FRAMES

    if frame_count <= 1:
        return [(surface.get_width() // 2, y)]

    spacing = (end_x - start_x) / (frame_count - 1)
    return [(round(start_x + i * spacing), y) for i in range(frame_count)]


def keyframe_at_pos(surface, pos):
    for i, point in enumerate(get_timeline_points(surface)):
        if pygame.Vector2(pos).distance_to(point) <= SELECTED_KEYFRAME_RADIUS:
            return i
    return None


def get_playhead_pos(points, live2d_time):
    start_x, y = points[0]
    end_x = points[-1][0]
    end_time = timeline_end_time()

    if end_time <= 0:
        return start_x, y

    progress = min(live2d_time / end_time, 1)
    return round(start_x + (end_x - start_x) * progress), y


def draw_timeline(surface, font, selected_keyframe_index, live2d_time):
    points = get_timeline_points(surface)
    if len(points) > 1:
        pygame.draw.line(surface, TIMELINE_COLOR, points[0], points[-1], 3)

    playhead_x, playhead_y = get_playhead_pos(points, live2d_time)
    pygame.draw.line(surface, PLAYHEAD_COLOR, (playhead_x, playhead_y - 24), (playhead_x, playhead_y + 12), 2)
    pygame.draw.polygon(
        surface,
        PLAYHEAD_COLOR,
        [
            (playhead_x, playhead_y - 28),
            (playhead_x - 6, playhead_y - 18),
            (playhead_x + 6, playhead_y - 18),
        ],
    )

    for i, point in enumerate(points):
        selected = i == selected_keyframe_index
        color = SELECTED_KEYFRAME_COLOR if selected else KEYFRAME_COLOR
        radius = SELECTED_KEYFRAME_RADIUS if selected else KEYFRAME_RADIUS
        pygame.draw.circle(surface, color, point, radius)

    animation_time = keyframe_time(selected_keyframe_index)
    draw_text(surface, font, f"Animation Time: {animation_time:.2f}s", (TIMELINE_MARGIN, points[0][1] + 18))
    draw_text(surface, font, f"Live2D t: {live2d_time:.2f}s", (TIMELINE_MARGIN + 180, points[0][1] + 18))


def main():
    parser = argparse.ArgumentParser(description="Edit a shipgirl Live2D animation.")
    parser.add_argument("shipgirl", help="Shipgirl name, matching live2d/<shipgirl>.json")
    args = parser.parse_args()

    model_path = model_path_for(args.shipgirl)
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Could not find Live2D model: {model_path}")

    migrate_file(Path(model_path))

    pygame.init()
    screen = pygame.display.set_mode(WINDOW_SIZE)
    pygame.mouse.set_visible(False)
    clock = pygame.time.Clock()
    title_font = pygame.font.SysFont(None, 28)
    font = pygame.font.SysFont(None, 22)

    live2d = Live2D(model_path)
    animation_index = 0
    selected_layer_index = len(Live2D.DRAW_ORDER) - 1
    selected_keyframe_index = 0
    is_playing = False
    edit_mode = None
    translate_drag = None
    rotate_drag = None
    live2d.set_animation(ANIMATIONS[animation_index])

    running = True
    while running:
        dt = clock.tick(60) / 1000

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_TAB:
                    direction = -1 if pygame.key.get_mods() & pygame.KMOD_SHIFT else 1
                    animation_index = next_animation_index(animation_index, direction)
                    live2d.set_animation(ANIMATIONS[animation_index])
                elif event.key == pygame.K_SPACE:
                    is_playing = not is_playing
                    if not is_playing:
                        live2d.t = keyframe_time(selected_keyframe_index)
                elif event.key == pygame.K_q:
                    selected_layer_index = next_layer_index(selected_layer_index, -1)
                    translate_drag = None
                    rotate_drag = None
                elif event.key == pygame.K_w:
                    selected_layer_index = next_layer_index(selected_layer_index)
                    translate_drag = None
                    rotate_drag = None
                elif event.key == pygame.K_a:
                    edit_mode = None
                    translate_drag = None
                    rotate_drag = None
                elif event.key == pygame.K_r:
                    edit_mode = "rotate"
                    translate_drag = None
                    rotate_drag = None
                elif event.key == pygame.K_t:
                    edit_mode = "translate"
                    rotate_drag = None
                elif event.key == pygame.K_s:
                    save_model(model_path, live2d.model_dict)
                elif event.key == pygame.K_d:
                    selected_layer = Live2D.DRAW_ORDER[selected_layer_index]
                    reset_keyframe(
                        live2d,
                        selected_layer,
                        current_animation_key(animation_index),
                        selected_keyframe_index,
                        edit_mode,
                    )

                if event.key != pygame.K_SPACE:
                    is_playing = False
                    live2d.t = keyframe_time(selected_keyframe_index)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                keyframe_index = keyframe_at_pos(screen, event.pos)
                if keyframe_index is not None:
                    selected_keyframe_index = keyframe_index
                    live2d.t = keyframe_time(selected_keyframe_index)
                    translate_drag = None
                    rotate_drag = None
                elif edit_mode == "translate" and get_live2d_rect(screen).collidepoint(event.pos):
                    selected_layer = Live2D.DRAW_ORDER[selected_layer_index]
                    animation_key = current_animation_key(animation_index)
                    keyframe = get_or_create_keyframe(
                        live2d,
                        selected_layer,
                        animation_key,
                        selected_keyframe_index,
                    )
                    is_playing = False
                    live2d.t = keyframe_time(selected_keyframe_index)
                    translate_drag = {
                        "keyframe": keyframe,
                        "part": selected_layer,
                        "start_mouse": pygame.Vector2(event.pos),
                        "start_offset": pygame.Vector2(keyframe["offset"]),
                    }
                    rotate_drag = None
                elif edit_mode == "rotate" and get_live2d_rect(screen).collidepoint(event.pos):
                    selected_layer = Live2D.DRAW_ORDER[selected_layer_index]
                    animation_key = current_animation_key(animation_index)
                    keyframe = get_or_create_keyframe(
                        live2d,
                        selected_layer,
                        animation_key,
                        selected_keyframe_index,
                    )
                    is_playing = False
                    live2d.t = keyframe_time(selected_keyframe_index)
                    rotate_drag = {
                        "keyframe": keyframe,
                        "part": selected_layer,
                        "start_angle": angle_to_pivot(screen, live2d, selected_layer, event.pos),
                        "start_rotation": keyframe["rotation"],
                    }
                    translate_drag = None
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                translate_drag = None
                rotate_drag = None
            elif event.type == pygame.MOUSEMOTION and translate_drag is not None:
                mouse_delta = (pygame.Vector2(event.pos) - translate_drag["start_mouse"]) / MODEL_SCALE
                offset = translate_drag["start_offset"] + mouse_delta
                set_part_keyframe_offset(
                    live2d,
                    translate_drag["part"],
                    translate_drag["keyframe"],
                    offset,
                )
            elif event.type == pygame.MOUSEMOTION and rotate_drag is not None:
                angle = angle_to_pivot(screen, live2d, rotate_drag["part"], event.pos)
                rotation = rotate_drag["start_rotation"] + angle - rotate_drag["start_angle"]
                set_part_keyframe_rotation(
                    live2d,
                    rotate_drag["part"],
                    rotate_drag["keyframe"],
                    rotation,
                )

        if is_playing:
            live2d.update(dt)

        screen.fill(BACKGROUND_COLOR)
        selected_layer = Live2D.DRAW_ORDER[selected_layer_index]
        draw_live2d_scaled(screen, live2d, screen.get_rect().center, selected_layer, edit_mode)

        animation_name = ANIMATIONS[animation_index].upper()
        pygame.display.set_caption(f"Live2D animation viewer - {args.shipgirl} - {animation_name}")
        draw_text(screen, title_font, f"{args.shipgirl}: {animation_name}", (16, 14))
        draw_text(screen, font, f"Layer: {selected_layer}", (16, 44))
        draw_text(screen, font, f"State: {'Playing' if is_playing else 'Paused'}", (16, 70))
        draw_text(
            screen,
            font,
            "Space: play/pause    Tab: animation    Q/W: layer    D: reset    Esc: quit",
            (16, 96),
            MUTED_TEXT_COLOR,
        )
        draw_timeline(screen, font, selected_keyframe_index, live2d.t)
        draw_part_pivot(screen, live2d, selected_layer, edit_mode)
        draw_cursor(screen, edit_mode)

        pygame.display.flip()

    save_model(model_path, live2d.model_dict)
    pygame.quit()


if __name__ == "__main__":
    main()
