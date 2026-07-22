import argparse
import json
import os
import sys

import pygame

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from live2d.live2d import LAYER_SIZE, PART_NAMES, Live2D


COLORKEY = [255, 0, 0]
WAVES = [None, "one_plus_sint", "sint_sq", "sint"]
EDIT_WAVES = ["one_plus_sint", "sint_sq", "sint"]
GRID_COLUMNS = 5
PANEL_WIDTH = 360
PADDING = 12
PREVIEW_SCALE = 3
ANIMATIONS = [
    (Live2D.IDLE_ANIMATION, "idle"),
    (Live2D.WALK_ANIMATION, "walk"),
    (Live2D.ATTACK_ANIMATION, "attack"),
    (Live2D.SINK_ANIMATION, "sink"),
]
ANIMATION_KEYS = [animation_key for _, animation_key in ANIMATIONS]


def model_path_for(shipgirl):
    return os.path.join("live2d", f"{shipgirl}.json")


def spritesheet_path_for(shipgirl):
    return os.path.join("live2d", f"{shipgirl}.png")


def default_part():
    part = {"pivot": [0, 0]}
    for animation_key in ANIMATION_KEYS:
        part[animation_key] = [0, None]
    return part


def default_model(shipgirl):
    model = {
        "spritesheet": spritesheet_path_for(shipgirl).replace("\\", "/"),
        "colorkey": COLORKEY[:],
    }
    for part in PART_NAMES:
        model[part] = default_part()
    return model


def normalize_model(model, shipgirl):
    model.setdefault("spritesheet", spritesheet_path_for(shipgirl).replace("\\", "/"))
    model.setdefault("colorkey", COLORKEY[:])

    for part in PART_NAMES:
        part_data = model.setdefault(part, default_part())
        part_data.setdefault("pivot", [0, 0])
        for animation_key in ANIMATION_KEYS:
            part_data.setdefault(animation_key, [0, None])
    return model


def load_or_create_model(shipgirl):
    model_path = model_path_for(shipgirl)
    if os.path.exists(model_path):
        with open(model_path, "r") as f:
            model = normalize_model(json.load(f), shipgirl)
    else:
        model = default_model(shipgirl)
        save_model(model_path, model)
    return model_path, model


def save_model(model_path, model):
    with open(model_path, "w") as f:
        json.dump(model, f, indent=4)
        f.write("\n")


def load_layers(spritesheet_path, colorkey):
    spritesheet = pygame.image.load(spritesheet_path).convert()
    spritesheet.set_colorkey(colorkey)
    num_layers_in_row = spritesheet.get_width() // LAYER_SIZE
    layers = {}

    for i, part in enumerate(PART_NAMES):
        crop = pygame.Rect(
            (i % num_layers_in_row) * LAYER_SIZE,
            (i // num_layers_in_row) * LAYER_SIZE,
            LAYER_SIZE,
            LAYER_SIZE,
        )
        layers[part] = spritesheet.subsurface(crop).copy()

    return layers


def set_live2d_pivot(live2d, part, pivot):
    live2d.parts[part].pivot = pygame.Vector2(pivot) - 0.5 * pygame.Vector2(
        live2d.parts[part].image.get_size()
    )


def cycle_wave(animation, direction):
    current = animation[1]
    try:
        index = WAVES.index(current)
    except ValueError:
        index = 0

    animation[1] = WAVES[(index + direction) % len(WAVES)]
    if animation[1] is None:
        animation[0] = 0
    elif animation[0] == 0:
        animation[0] = 5


def change_amplitude(animation, delta):
    animation[0] = int(animation[0]) + delta
    if animation[0] == 0:
        animation[1] = None
    elif animation[1] is None:
        animation[1] = EDIT_WAVES[0]


def animation_key(preview_animation):
    for animation, key in ANIMATIONS:
        if preview_animation == animation:
            return key
    return "idle"


def next_animation(preview_animation):
    animations = [animation for animation, _ in ANIMATIONS]
    try:
        index = animations.index(preview_animation)
    except ValueError:
        index = 0
    return animations[(index + 1) % len(animations)]


def draw_text(surface, font, text, x, y, color=(230, 230, 230)):
    surface.blit(font.render(text, True, color), (x, y))


def draw_layer_grid(surface, layers, selected_index, font):
    for i, part in enumerate(PART_NAMES):
        col = i % GRID_COLUMNS
        row = i // GRID_COLUMNS
        x = PADDING + col * (LAYER_SIZE + PADDING)
        y = PADDING + row * (LAYER_SIZE + 30)
        rect = pygame.Rect(x, y, LAYER_SIZE, LAYER_SIZE)

        pygame.draw.rect(surface, (42, 42, 48), rect)
        surface.blit(layers[part], rect)

        border = (250, 220, 80) if i == selected_index else (90, 90, 100)
        pygame.draw.rect(surface, border, rect, 2)
        draw_text(surface, font, part, x, y + LAYER_SIZE + 4, border)


def draw_selected_layer(surface, layer, part_data, panel_x, panel_y, font):
    scaled_size = LAYER_SIZE * PREVIEW_SCALE
    rect = pygame.Rect(panel_x, panel_y, scaled_size, scaled_size)
    scaled = pygame.transform.scale(layer, (scaled_size, scaled_size))
    surface.blit(scaled, rect)
    pygame.draw.rect(surface, (120, 120, 132), rect, 2)

    pivot = part_data["pivot"]
    pivot_pos = pygame.Vector2(panel_x + pivot[0] * PREVIEW_SCALE, panel_y + pivot[1] * PREVIEW_SCALE)
    pygame.draw.line(surface, (255, 236, 90), (pivot_pos.x - 8, pivot_pos.y), (pivot_pos.x + 8, pivot_pos.y), 2)
    pygame.draw.line(surface, (255, 236, 90), (pivot_pos.x, pivot_pos.y - 8), (pivot_pos.x, pivot_pos.y + 8), 2)

    draw_text(surface, font, "Click enlarged layer to set pivot", panel_x, panel_y + scaled_size + 10)
    return rect


def draw_status(surface, font, shipgirl, selected_part, part_data, preview_animation, panel_x, panel_y):
    current_animation = animation_key(preview_animation)
    lines = [
        f"Shipgirl: {shipgirl}",
        f"Layer: {selected_part}",
        f"Pivot: {part_data['pivot']}",
        f"Preview: {current_animation}",
    ]
    for key in ANIMATION_KEYS:
        animation = part_data[key]
        lines.append(f"{key.title()}: amp {animation[0]}, wave {animation[1]}")
    lines += [
        "",
        "Left/Right or Tab: layer",
        "Space: preview idle/walk/attack/sink",
        "Q/E: preview amplitude -/+5",
        "W: preview wave, R: clear preview",
        "Ctrl+S: save, Esc: quit",
    ]

    y = panel_y
    for line in lines:
        draw_text(surface, font, line, panel_x, y)
        y += 22


def main():
    parser = argparse.ArgumentParser(description="Create and edit a Live2D model JSON.")
    parser.add_argument("shipgirl", help="Shipgirl name, matching live2d/<shipgirl>.png")
    args = parser.parse_args()

    spritesheet_path = spritesheet_path_for(args.shipgirl)
    if not os.path.exists(spritesheet_path):
        raise FileNotFoundError(f"Could not find spritesheet: {spritesheet_path}")

    pygame.init()
    grid_rows = (len(PART_NAMES) + GRID_COLUMNS - 1) // GRID_COLUMNS
    grid_width = PADDING + GRID_COLUMNS * (LAYER_SIZE + PADDING)
    grid_height = PADDING + grid_rows * (LAYER_SIZE + 30)
    width = grid_width + PANEL_WIDTH + 200
    height = max(grid_height + PADDING, LAYER_SIZE * PREVIEW_SCALE + 300) + 200
    screen = pygame.display.set_mode((width, height))
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 20)

    model_path, model = load_or_create_model(args.shipgirl)
    save_model(model_path, model)

    layers = load_layers(model["spritesheet"], model["colorkey"])
    live2d = Live2D(model_path)
    live2d.model_dict = model
    preview_animation = Live2D.IDLE_ANIMATION
    live2d.set_animation(preview_animation)
    selected_index = 0
    selected_layer_rect = None
    running = True

    while running:
        dt = clock.tick(60) / 1000
        selected_part = PART_NAMES[selected_index]
        selected_part_data = model[selected_part]

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                changed = False
                mods = pygame.key.get_mods()

                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_RIGHT or event.key == pygame.K_TAB and not mods & pygame.KMOD_SHIFT:
                    selected_index = (selected_index + 1) % len(PART_NAMES)
                elif event.key == pygame.K_LEFT or event.key == pygame.K_TAB and mods & pygame.KMOD_SHIFT:
                    selected_index = (selected_index - 1) % len(PART_NAMES)
                elif event.key == pygame.K_SPACE:
                    preview_animation = next_animation(preview_animation)
                    live2d.set_animation(preview_animation)
                elif event.key == pygame.K_e:
                    change_amplitude(selected_part_data[animation_key(preview_animation)], 5)
                    changed = True
                elif event.key == pygame.K_q:
                    change_amplitude(selected_part_data[animation_key(preview_animation)], -5)
                    changed = True
                elif event.key == pygame.K_w:
                    cycle_wave(selected_part_data[animation_key(preview_animation)], 1)
                    changed = True
                elif event.key == pygame.K_r:
                    selected_part_data[animation_key(preview_animation)] = [0, None]
                    changed = True
                elif event.key == pygame.K_s and mods & pygame.KMOD_CTRL:
                    save_model(model_path, model)

                if changed:
                    save_model(model_path, model)

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and selected_layer_rect:
                if selected_layer_rect.collidepoint(event.pos):
                    local = pygame.Vector2(event.pos) - pygame.Vector2(selected_layer_rect.topleft)
                    pivot = [
                        max(0, min(LAYER_SIZE, round(local.x / PREVIEW_SCALE))),
                        max(0, min(LAYER_SIZE, round(local.y / PREVIEW_SCALE))),
                    ]
                    selected_part_data["pivot"] = pivot
                    set_live2d_pivot(live2d, selected_part, pivot)
                    save_model(model_path, model)

        selected_part = PART_NAMES[selected_index]
        selected_part_data = model[selected_part]
        live2d.update(dt)

        screen.fill((24, 24, 28))
        draw_layer_grid(screen, layers, selected_index, font)

        panel_x = grid_width + PADDING
        selected_layer_rect = draw_selected_layer(
            screen, layers[selected_part], selected_part_data, panel_x, PADDING, font
        )

        preview_y = PADDING + LAYER_SIZE * PREVIEW_SCALE + 56
        pygame.draw.rect(screen, (18, 18, 22), (panel_x, preview_y, LAYER_SIZE * 2, LAYER_SIZE * 2))
        live2d.draw(screen, panel_x + LAYER_SIZE, preview_y + LAYER_SIZE, False)
        pygame.draw.rect(screen, (90, 90, 100), (panel_x, preview_y, LAYER_SIZE * 2, LAYER_SIZE * 2), 1)

        draw_status(
            screen,
            font,
            args.shipgirl,
            selected_part,
            selected_part_data,
            preview_animation,
            panel_x + LAYER_SIZE * 2 + 18,
            preview_y,
        )

        pygame.display.set_caption(f"Live2D model editor - {args.shipgirl} - {selected_part}")
        pygame.display.flip()

    save_model(model_path, model)
    pygame.quit()


if __name__ == "__main__":
    main()
