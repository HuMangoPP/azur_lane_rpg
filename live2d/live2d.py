import json
import math
import os
from copy import deepcopy
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
    "right_thigh",
    "left_thigh",
    "left_hair",
    "back_torso",
    "back_hair",
    "headpiece",
    "left_leg",
    "right_leg",
    "neutral",
    "dizzy",
    "focused",
    "sleepy"
]
FACIAL_EXPRESSION_PART_NAMES = ["neutral", "dizzy", "focused", "sleepy"]

SHARED_MODEL_FILE = os.path.join(os.path.dirname(__file__), "shared_model.json")
SHARED_ANIMATIONS_FILE = os.path.join(os.path.dirname(__file__), "shared_animations.json")
KEYFRAME_DURATION_KEY = "keyframe_duration"
KEYFRAMES_KEY = "keyframes"
NO_LOOP_KEY = "no_loop"
NEXT_ANIMATION_KEY = "next_animation"
FACIAL_EXPRESSION_KEY = "facial_expression"


def animation_keyframes(animation):
    return animation.get(KEYFRAMES_KEY, {})


def resolve_animation_copies(keyframes):
    resolved_keyframes = {}

    def resolve_keyframe(keyframe_index, seen=None):
        if keyframe_index in resolved_keyframes:
            return deepcopy(resolved_keyframes[keyframe_index])

        # Infinite loop guard
        if seen is None:
            seen = set()
        if keyframe_index in seen:
            return {}
        seen.add(keyframe_index)

        keyframe = keyframes.get(keyframe_index, {})
        if (copy_index := keyframe.get("copy")) is not None:
            resolved_keyframes[keyframe_index] = resolve_keyframe(copy_index, seen)
        else:
            resolved_keyframes[keyframe_index] = deepcopy(keyframe)
        return deepcopy(resolved_keyframes[keyframe_index])

    for keyframe_index in keyframes:
        resolve_keyframe(keyframe_index)
    return resolved_keyframes


def merge_animations(shared_animation, model_animation):
    merged_keyframes = resolve_animation_copies(animation_keyframes(shared_animation))
    resolved_model_keyframes = resolve_animation_copies(animation_keyframes(model_animation))
    merged_animation = {KEYFRAMES_KEY: merged_keyframes}

    for meta_keys in [NO_LOOP_KEY, NEXT_ANIMATION_KEY, KEYFRAME_DURATION_KEY, FACIAL_EXPRESSION_KEY]:
        if meta_keys in shared_animation:
            merged_animation[meta_keys] = shared_animation[meta_keys]
        if meta_keys in model_animation:
            merged_animation[meta_keys] = model_animation[meta_keys]

    for keyframe_index, model_keyframe in resolved_model_keyframes.items():
        merged_keyframe = merged_keyframes.setdefault(keyframe_index, {})
        for part, part_animation in model_keyframe.items():
            merged_keyframe[part] = deepcopy(part_animation)

    return merged_animation


def model_parts(model_dict):
    parts = model_dict.get("parts", {})
    if isinstance(parts, dict):
        return parts
    return {}


def merge_model_parts(shared_parts, model_specific_parts):
    merged_parts = {}
    for part in PART_NAMES:
        part_data = {"pivot": [0, 0]}
        part_data.update(deepcopy(shared_parts.get(part, {})))
        part_data.update(deepcopy(model_specific_parts.get(part, {})))
        merged_parts[part] = part_data
    return merged_parts


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

    def get_pivot_offset(self):
        if self.parent_part is None:
            return self.pivot + self.offset

        parent_pivot_offset = self.parent_part.get_pivot_offset()
        parent_rotation = self.parent_part.get_rotation()
        parent_relative_pivot = self.pivot - self.parent_part.pivot + self.offset
        return parent_pivot_offset + parent_relative_pivot.rotate(-parent_rotation)

    def draw(self, surface, root_pos, flipx):
        rotation = self.get_rotation()
        rotated = pygame.transform.rotate(self.image, rotation)
        rotated_pivot = self.pivot.rotate(-rotation)
        draw_offset = self.get_pivot_offset() - rotated_pivot
        if flipx:
            rotated = pygame.transform.flip(rotated, True, False)
            draw_offset.x = -draw_offset.x
        rect = rotated.get_rect()
        rect.center = root_pos + draw_offset
        surface.blit(rotated, rect)

    def draw_with_part_transform(self, surface, root_pos, flipx, transform_part):
        rotation = transform_part.get_rotation()
        rotated = pygame.transform.rotate(self.image, rotation)
        rotated_pivot = transform_part.pivot.rotate(-rotation)
        draw_offset = transform_part.get_pivot_offset() - rotated_pivot
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
        self.shared_model_parts = None
        self.shared_animations = None

    def get_shared_model_parts(self):
        if self.shared_model_parts is not None:
            return self.shared_model_parts

        if not os.path.exists(SHARED_MODEL_FILE):
            self.shared_model_parts = {}
            return self.shared_model_parts

        with open(SHARED_MODEL_FILE) as f:
            shared_model = json.load(f)
        self.shared_model_parts = model_parts(shared_model) or shared_model
        return self.shared_model_parts

    def get_shared_animations(self):
        if self.shared_animations is not None:
            return self.shared_animations

        if not os.path.exists(SHARED_ANIMATIONS_FILE):
            self.shared_animations = {}
            return self.shared_animations

        with open(SHARED_ANIMATIONS_FILE) as f:
            self.shared_animations = json.load(f)
        return self.shared_animations

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

    def get_resolved_model_parts(self, model_file):
        model_dict = self.get_model_dict(model_file)
        return merge_model_parts(self.get_shared_model_parts(), model_parts(model_dict))

cache = Cache()

class Live2D:
    DRAW_ORDER = [
        "back_hair",
        "back_torso",
        "left_thigh",
        "left_leg",
        "right_thigh",
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
        "left_thigh": "torso",
        "left_leg": "left_thigh",
        "right_thigh": "torso",
        "right_leg": "right_thigh",
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
    BOUNCE_ANIMATION = "bounce"
    DRAG_ANIMATION = "drag"
    WALK_ANIMATION = "walk"
    SAIL_ANIMATION = "sail"
    ATTACK_ANIMATION = "attack"
    SINK_ANIMATION = "sink"
    SLEEP_ANIMATION = "sleep"
    SIT_ANIMATION = "sit"

    ANIMATION_SPEED = 1.0
    NUM_FRAMES = 12
    KEYFRAME_DURATION = 0.3

    def __init__(self, model_file):
        self.t = 0
        self.parts = {}

        self.animation = self.IDLE_ANIMATION

        self.model_dict = cache.get_model_dict(model_file)
        self.model_parts = cache.get_resolved_model_parts(model_file)
        self.refresh_animations()

        self.parts = {}
        for part in PART_NAMES:
            part_data = self.model_parts[part]
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

    def animation_finished(self, animation=None):
        animation_name = animation or self.animation
        if self.animation != animation_name:
            return False

        animation_data = self.animations.get(animation_name, {})
        if not animation_data.get(NO_LOOP_KEY, False):
            return False

        keyframes = animation_keyframes(animation_data)
        if len(keyframes) <= 1:
            return True

        final_keyframe = max(int(index) for index in keyframes)
        keyframe_duration = animation_data.get(
            KEYFRAME_DURATION_KEY,
            self.KEYFRAME_DURATION,
        )
        return self.t >= final_keyframe * keyframe_duration

    def get_facial_expression(self):
        animation = self.animations.get(self.animation, {})
        expression = animation.get(FACIAL_EXPRESSION_KEY, FACIAL_EXPRESSION_PART_NAMES[0])
        if expression not in FACIAL_EXPRESSION_PART_NAMES:
            return FACIAL_EXPRESSION_PART_NAMES[0]
        return expression

    def update(self, dt):
        animation = self.animations.get(self.animation, {})
        keyframes = animation_keyframes(animation)
        if len(keyframes.keys()) <= 1:
            self.t = 0
        else:
            max_keyframe_index = max(int(keyframe_index) for keyframe_index in keyframes.keys())
            keyframe_duration = animation.get(KEYFRAME_DURATION_KEY, self.KEYFRAME_DURATION)
            duration = max_keyframe_index * keyframe_duration
            next_t = self.t + self.ANIMATION_SPEED * dt
            if animation.get(NO_LOOP_KEY, False) is True:
                self.t = min(next_t, duration)
            elif (new_animation := animation.get(NEXT_ANIMATION_KEY)) is not None:
                if next_t >= duration:
                    self.set_animation(new_animation)
                else:
                    self.t = next_t
            else:
                self.t = next_t % duration

    def refresh_animations(self):
        shared_animations = cache.get_shared_animations()
        model_animations = self.model_dict.get("animations", {})
        animations = {}
        for animation in set(shared_animations.keys()) | set(model_animations.keys()):
            animations[animation] = merge_animations(
                shared_animations.get(animation, {}),
                model_animations.get(animation, {})
            )
        self.animations = animations

    def update_offset_and_rotation(self):
        animation = self.animations.get(self.animation, {})
        master_keyframes = animation_keyframes(animation)
        
        for part in PART_NAMES:
            keyframes = {
                keyframe_index: keyframe
                for keyframe_index, keyframe in master_keyframes.items()
                if part in keyframe
            }
            if not keyframes:
                self.set_offset(part, [0, 0])
                self.set_rotation(part, 0)
                continue
            
            if "0" not in keyframes:
                keyframes["0"] = {part: {"offset": [0, 0], "rotation": 0}}

            keyframe_duration = animation.get(KEYFRAME_DURATION_KEY, self.KEYFRAME_DURATION)
            keyframe_t = self.t / keyframe_duration
            prev_keyframe_index = max(
                int(keyframe_index) for keyframe_index in keyframes.keys()
                if int(keyframe_index) <= keyframe_t
            )
            next_keyframe_index = min(
                (
                    int(keyframe_index) for keyframe_index in keyframes.keys()
                    if int(keyframe_index) >= keyframe_t
                ),
                default=prev_keyframe_index
            )
            if prev_keyframe_index == next_keyframe_index:
                keyframe = keyframes[str(prev_keyframe_index)]
                self.set_offset(part, keyframe[part]["offset"])
                self.set_rotation(part, keyframe[part]["rotation"])
            else:
                prev_keyframe = keyframes[str(prev_keyframe_index)]
                next_keyframe = keyframes[str(next_keyframe_index)]
                s = (
                    (keyframe_t - prev_keyframe_index)
                    / (next_keyframe_index - prev_keyframe_index)
                )
                s = (1 + math.sin(math.radians(180) * (s - 0.5))) / 2
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
                if part == "head":
                    expression = self.get_facial_expression()
                    self.parts[expression].draw_with_part_transform(sprite_surf, root, flipx, self.parts["head"])

        sprite_surf.set_alpha(alpha)
        sprite_rect = sprite_surf.get_rect()
        sprite_rect.center = (x, y)
        surface.blit(sprite_surf, sprite_rect)
