import json
import math
import pygame

LAYER_SIZE = 96
PART_NAMES = [
    "bangs",
    "right_bangs",
    "right_hair",
    "left_bangs",
    "top_head",
    "head",
    "right_arm",
    "torso",
    "left_arm",
    "right_leg",
    "left_leg",
    "left_hair",
    "back_torso",
    "back_hair",
    "headpiece"
]

ANIMATION_NAMES = ["idle", "walk", "attack", "sink"]


class Live2DPart:
    def __init__(self, image, pivot):
        self.image = image

        self.pivot = pygame.Vector2(pivot) - 0.5*pygame.Vector2(image.get_size()) 
        self.parent_part = None
        self.rotation = 0

        self.offset = pygame.Vector2(0,0)

    def get_rotation(self):
        if self.parent_part is None:
            return self.rotation
        else:
            return self.rotation + self.parent_part.get_rotation()

    def get_offset(self):
        if self.parent_part is None:
            return self.offset
        else:
            return self.offset + self.parent_part.get_offset()

    def rotate_on_pivot(self):
        rotation = self.get_rotation()
        rotated = pygame.transform.rotate(self.image, rotation)
        rotated_pivot = self.pivot.rotate(-rotation)
        return rotated, self.pivot - rotated_pivot

    def align_to_parent(self):
        if self.parent_part is None:
            return pygame.Vector2(0,0)
        else:
            parent_rel = self.pivot - self.parent_part.pivot
            rotated_parent_rel = parent_rel.rotate(-self.parent_part.get_rotation())
            return rotated_parent_rel - parent_rel

    def draw(self, surface, root_pos, flipx):
        rotated, rotation_offset = self.rotate_on_pivot()
        parent_offset = self.align_to_parent()
        draw_offset = rotation_offset + parent_offset + self.get_offset()
        if flipx:
            rotated = pygame.transform.flip(rotated, True, False)
            draw_offset.x = -draw_offset.x
        rect = rotated.get_rect()
        rect.center = root_pos + draw_offset
        surface.blit(rotated, rect)

class Cache:
    def __init__(self):
        self.model_dicts = {}
        self.parts = {}

    def get_model_dict(self, model_file):
        if model_file in self.model_dicts:
            return self.model_dicts[model_file]
    
        with open(model_file) as f:
            model_dict = json.load(f)
            self.model_dicts[model_file] = model_dict
        
        parts = {}
        spritesheet = pygame.image.load(model_dict["spritesheet"]).convert()
        spritesheet.set_colorkey(model_dict["colorkey"])
        num_layers_in_row = spritesheet.get_width() // LAYER_SIZE
        for i, part in enumerate(PART_NAMES):
            crop = pygame.Rect(
                (i % num_layers_in_row) * LAYER_SIZE,
                (i // num_layers_in_row) * LAYER_SIZE,
                LAYER_SIZE,
                LAYER_SIZE
            )
            image = spritesheet.subsurface(crop)
            parts[part] = image
        self.parts[model_file] = parts

        return model_dict

cache = Cache()

class Live2D:
    DRAW_ORDER = [
        "back_hair",
        "back_torso",
        "left_leg",
        "right_leg",
        "left_hair",
        "left_arm",
        "torso",
        "right_arm",
        "head",
        "top_head",
        "left_bangs",
        "right_hair",
        "right_bangs",
        "bangs",
        "headpiece",
    ]

    CONNECTIONS = {
        "back_hair": "head",
        "back_torso": "torso",
        "left_leg": "torso",
        "right_leg": "torso",
        "torso": None,
        "left_arm": "torso",
        "head": "torso",
        "top_head": "head",
        "left_hair": "head",
        "left_bangs": "head",
        "right_hair": "head",
        "right_bangs": "head",
        "bangs": "head",
        "right_arm": "torso",
        "headpiece": "head",
    }

    IDLE_ANIMATION = "idle"
    WALK_ANIMATION = "walk"
    ATTACK_ANIMATION = "attack"
    SINK_ANIMATION = "sink"

    ANIMATION_SPEED = 1.0
    NUM_FRAMES = 12
    KEYFRAME_DURATION = 0.25

    def __init__(self, model_file):
        self.t = 0
        self.parts = {}

        self.animation = self.IDLE_ANIMATION

        self.model_dict = cache.get_model_dict(model_file)

        self.parts = {}
        for part in PART_NAMES:
            part_data = self.model_dict["parts"][part]
            image = cache.parts[model_file][part]
            self.parts[part] = Live2DPart(image, part_data["pivot"])
        
        for part, parent_part in self.CONNECTIONS.items():
            if parent_part is not None:
                live2d_part = self.parts[part]
                live2d_part.parent_part = self.parts[parent_part]
        
    def set_rotation(self, part, angle):
        if part in self.parts:
            self.parts[part].rotation = angle
    
    def set_offset(self, part, offset):
        if part in self.parts:
            self.parts[part].offset = pygame.Vector2(offset)
    
    def set_animation(self, animation):
        if self.animation != animation:
            self.animation = animation
            self.t = 0

    def update(self, dt):
        keyframes = [keyframe for keyframe in self.model_dict["animations"][self.animation]]
        if len(keyframes) == 1:
            self.t = 0
        else:
            self.t = (
                (self.t + self.ANIMATION_SPEED * dt)
                % (keyframes[-1]["keyframe"] * self.KEYFRAME_DURATION)
            )

    def update_offset_and_rotation(self):
        for part in PART_NAMES:
            keyframes = [
                keyframe for keyframe in self.model_dict["animations"][self.animation]
                if part in keyframe
            ]
            if not keyframes:
                self.set_offset(part, [0, 0])
                self.set_rotation(part, 0)
                continue
            
            if keyframes[0]["keyframe"] != 0:
                keyframes = (
                    [{"keyframe": 0, part: {"offset": [0, 0], "rotation": 0}}]
                    + keyframes
                )

            keyframe_t = self.t / self.KEYFRAME_DURATION
            prev_keyframe_index = max(
                keyframe["keyframe"] for keyframe in keyframes
                if keyframe["keyframe"] <= keyframe_t
            )
            next_keyframe_index = min(
                keyframe["keyframe"] for keyframe in keyframes
                if keyframe["keyframe"] >= keyframe_t
            )
            if prev_keyframe_index == next_keyframe_index:
                keyframe = next(keyframe for keyframe in keyframes if keyframe["keyframe"] == prev_keyframe_index)
                self.set_offset(part, keyframe[part]["offset"])
                self.set_rotation(part, keyframe[part]["rotation"])
            else:
                prev_keyframe = next(keyframe for keyframe in keyframes if keyframe["keyframe"] == prev_keyframe_index)
                next_keyframe = next(keyframe for keyframe in keyframes if keyframe["keyframe"] == next_keyframe_index)
                s = (
                    (keyframe_t - prev_keyframe["keyframe"])
                    / (next_keyframe["keyframe"] - prev_keyframe["keyframe"])
                )
                self.set_offset(
                    part,
                    pygame.Vector2(prev_keyframe[part]["offset"]).lerp(pygame.Vector2(next_keyframe[part]["offset"]), s)
                )
                self.set_rotation(
                    part,
                    (1 - s) * prev_keyframe[part]["rotation"] + s * next_keyframe[part]["rotation"]
                )

    def draw(self, surface, x, y, flipx, alpha=255):
        self.update_offset_and_rotation()

        alpha = int(max(0, min(255, alpha)))
        root = pygame.Vector2(LAYER_SIZE, LAYER_SIZE)

        sprite_surf = pygame.Surface((2*LAYER_SIZE, 2*LAYER_SIZE))
        sprite_surf.fill((255, 0, 0))
        sprite_surf.set_colorkey((255, 0, 0))

        for part in self.DRAW_ORDER:
            if part in self.parts:
                self.parts[part].draw(sprite_surf, root, flipx)

        sprite_surf.set_alpha(alpha)
        sprite_rect = sprite_surf.get_rect()
        sprite_rect.center = (x, y)
        surface.blit(sprite_surf, sprite_rect)
