from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from engine.types import CoordinateType

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


def _animation_keyframes(animation: str) -> dict:
    """Get the keyframes of an animation.
    
    The keyframes are a mapping of indices to keyframe objects.
    Each keyframe object is a mapping of live2d part names to part data,
    which has a rotation and offset.
    """
    return animation.get(KEYFRAMES_KEY, {})


def _resolve_animation_copies(keyframes: dict) -> dict:
    """Resolve copied keyframes.
    
    Some keyframes may be defined instead by a single key `copy` whose
    value is a keyframe index. In this case, it means that the keyframe
    is a copy of that existing keyframe. This function will resolve copied
    keyframes by injecting the full keyframe into that index.
    """
    resolved_keyframes = {}

    def _resolve_keyframe(keyframe_index: str, seen: set[str] | None = None) -> dict:
        """Resolve the keyframe.
        
        If the keyframe is a copy of another keyframe, deepcopy that referenced keyframe.
        Otherwise, return a deepcopy of this keyframe.
        """
        if keyframe_index in resolved_keyframes:
            return deepcopy(resolved_keyframes[keyframe_index])

        # Infinite loop guard.
        if seen is None:
            seen = set()
        if keyframe_index in seen:
            return {}
        seen.add(keyframe_index)

        keyframe = keyframes.get(keyframe_index, {})
        if (copy_index := keyframe.get("copy")) is not None:
            # Check if this keyframe is a copy of another keyframe, and in that case,
            # deepcopy that keyframe into this keyframe, then return this keyframe.
            resolved_keyframes[keyframe_index] = _resolve_keyframe(copy_index, seen)
        else:
            # This is a regular keyframe.
            # Assign it as normal and return a copy of it.
            resolved_keyframes[keyframe_index] = deepcopy(keyframe)
        return deepcopy(resolved_keyframes[keyframe_index])

    for keyframe_index in keyframes:
        _resolve_keyframe(keyframe_index)
    return resolved_keyframes


def _merge_animations(shared_animation: dict, model_animation: dict) -> dict:
    """Merge the shared and model-override animations.
    
    The shared animation serves as the base and is the default animation. Each
    model can optionally override animation metadata and the animations itself,
    at a part in keyframe granularity.
    """
    merged_keyframes = _resolve_animation_copies(_animation_keyframes(shared_animation))
    resolved_model_keyframes = _resolve_animation_copies(_animation_keyframes(model_animation))
    merged_animation = {KEYFRAMES_KEY: merged_keyframes}

    # Override meta keys.
    for meta_keys in [NO_LOOP_KEY, NEXT_ANIMATION_KEY, KEYFRAME_DURATION_KEY, FACIAL_EXPRESSION_KEY]:
        if meta_keys in shared_animation:
            merged_animation[meta_keys] = shared_animation[meta_keys]
        if meta_keys in model_animation:
            merged_animation[meta_keys] = model_animation[meta_keys]

    for keyframe_index, model_keyframe in resolved_model_keyframes.items():
        # The model overrides may defined a keyframe that doesn't exist in the
        # shared animation.
        merged_keyframe = merged_keyframes.setdefault(keyframe_index, {})
        for part, part_animation in model_keyframe.items():
            # Override the animation of this part in this particular keyframe.
            merged_keyframe[part] = deepcopy(part_animation)

    return merged_animation


def _model_parts(model_dict: dict) -> dict:
    """Get the parts definition in the model dict.
    
    The parts definition in a model is a mapping of parts to a pivot, which
    is where the part rotates from.
    """
    parts = model_dict.get("parts", {})
    if isinstance(parts, dict):
        return parts
    return {}


def _merge_model_parts(shared_parts: dict, model_specific_parts: dict) -> dict:
    """Merge the shared and model override parts data.
    
    The shared model will define default pivots for the live2d and the
    specific model can optionally override those default pivots for specific
    parts.
    """
    merged_parts = {}
    for part in PART_NAMES:
        part_data = {"pivot": [0, 0]}
        part_data.update(deepcopy(shared_parts.get(part, {})))
        part_data.update(deepcopy(model_specific_parts.get(part, {})))
        merged_parts[part] = part_data
    return merged_parts


class Live2DPart:
    def __init__(self, image: pygame.Surface, pivot: CoordinateType):
        self.image = image

        self.pivot = pygame.Vector2(pivot) - 0.5 * pygame.Vector2(image.get_size()) 
        self.parent_part: Live2DPart | None = None
        self.rotation = 0

        self.offset = pygame.Vector2(0, 0)

    def get_rotation(self) -> float:
        """Get the total rotation of this part, including rotation from parent parts."""
        if self.parent_part is None:
            return self.rotation
        else:
            return self.rotation + self.parent_part.get_rotation()

    def get_pivot_offset(self) -> pygame.Vector2:
        """Get the total pivot offset of this part, including pivot offsets from parent parts."""
        if self.parent_part is None:
            return self.pivot + self.offset

        parent_pivot_offset = self.parent_part.get_pivot_offset()
        parent_rotation = self.parent_part.get_rotation()
        parent_relative_pivot = self.pivot - self.parent_part.pivot + self.offset
        return parent_pivot_offset + parent_relative_pivot.rotate(-parent_rotation)

    def draw(self, surface: pygame.Surface, root_pos: pygame.Vector2, flipx: bool):
        """Draw this part with rotation and offset."""
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


class Cache:
    def __init__(self):
        self.model_dicts = {}
        self.part_sprites: dict[str, dict[str, pygame.Surface]] = {}

        self.shared_model_parts: dict | None = None
        self._load_shared_model_parts()

        self.shared_animations: dict | None = None

    def _load_shared_model_parts(self):
        """Load the parts data of the shared model."""
        if not os.path.exists(SHARED_MODEL_FILE):
            self.shared_model_parts = {}
            return

        with open(SHARED_MODEL_FILE) as f:
            shared_model = json.load(f)
        self.shared_model_parts = _model_parts(shared_model) or shared_model

    def load_shared_animations(self):
        """Load the shared animations."""
        if not os.path.exists(SHARED_ANIMATIONS_FILE):
            self.shared_animations = {}
            return
        
        with open(SHARED_ANIMATIONS_FILE) as f:
            self.shared_animations = json.load(f)

    def get_model_dict(self, model_file: str) -> dict:
        """Get the specific model dict.
        
        If the model has already been loaded, then retrieve it from
        cache. Otherwise, load the model file.
        """
        if model_file in self.model_dicts:
            return self.model_dicts[model_file]
    
        with open(model_file) as f:
            model_dict = json.load(f)
            self.model_dicts[model_file] = model_dict

        # Load the part sprites from the model spritesheet.
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
        self.part_sprites[model_file] = parts

        return model_dict


class Live2D:
    cache = Cache()

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
        "neutral": "head",
        "dizzy": "head",
        "focused": "head",
        "sleepy": "head",
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

    KEYFRAME_DURATION = 0.3

    def __init__(self, model_file: str):
        self.t = 0

        self.animation = self.IDLE_ANIMATION

        self.model_dict = self.cache.get_model_dict(model_file)
        self.refresh_animations()

        # Create the Live2DPart objects and set their parents.
        model_parts = _merge_model_parts(
            self.cache.shared_model_parts,
            _model_parts(self.cache.get_model_dict(model_file))
        )
        self.parts: dict[str, Live2DPart] = {}
        for part in PART_NAMES:
            part_data = model_parts[part]
            image = self.cache.part_sprites[model_file][part]
            self.parts[part] = Live2DPart(image, part_data["pivot"])
        
        for part, parent_part in self.CONNECTIONS.items():
            if parent_part is not None:
                live2d_part = self.parts[part]
                live2d_part.parent_part = self.parts[parent_part]

    def refresh_animations(self):
        """Reload animations due to changes to the model dict.

        This API is exposed so devtools can make changes to the underlying
        model dict, and the animations can be reloaded from the updated model dict.
        """
        self.cache.load_shared_animations()
        shared_animations = self.cache.shared_animations
        model_animations = self.model_dict.get("animations", {})
        animations = {}
        for animation in set(shared_animations.keys()) | set(model_animations.keys()):
            animations[animation] = _merge_animations(
                shared_animations.get(animation, {}),
                model_animations.get(animation, {})
            )
        self.animations = animations

    def set_animation(self, animation: str):
        """Set the animation for this live2d sprite."""
        if animation not in self.animation:
            return
        
        if self.animation != animation:
            self.animation = animation
            self.t = 0

    def animation_finished(self, animation: str | None = None) -> bool:
        """Check if the current animation has finished."""
        animation_name = animation or self.animation
        if self.animation != animation_name:
            return False

        animation_data = self.animations.get(animation_name, {})
        if not animation_data.get(NO_LOOP_KEY, False):
            return False

        keyframes = _animation_keyframes(animation_data)
        if len(keyframes) <= 1:
            return True

        final_keyframe = max(int(index) for index in keyframes)
        keyframe_duration = animation_data.get(
            KEYFRAME_DURATION_KEY,
            self.KEYFRAME_DURATION,
        )
        return self.t >= final_keyframe * keyframe_duration

    def _set_rotation(self, part: str, angle: float):
        """Set the rotation of this part."""
        if part in self.parts:
            self.parts[part].rotation = angle
    
    def _set_offset(self, part: str, offset: CoordinateType):
        """Set the offset of this part."""
        if part in self.parts:
            self.parts[part].offset = pygame.Vector2(offset)
    

    def _update_offset_and_rotation(self):
        """Update the offset and rotation of all parts based on the animation."""
        animation = self.animations.get(self.animation, {})
        keyframe_duration = animation.get(KEYFRAME_DURATION_KEY, self.KEYFRAME_DURATION)
        master_keyframes = _animation_keyframes(animation)
        
        for part in PART_NAMES:
            keyframes = {
                keyframe_index: keyframe
                for keyframe_index, keyframe in master_keyframes.items()
                if part in keyframe
            }
            if not keyframes:
                self._set_offset(part, [0, 0])
                self._set_rotation(part, 0)
                continue

            # All animations have the initial keyframe.
            # All parts have zero offset and rotation in the initial keyframe by default.
            if "0" not in keyframes:
                keyframes["0"] = {part: {"offset": [0, 0], "rotation": 0}}

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
                # All keyframes containing this part have passed, so the offset
                # and rotation for this part remain fixed.
                keyframe = keyframes[str(prev_keyframe_index)]
                self._set_offset(part, keyframe[part]["offset"])
                self._set_rotation(part, keyframe[part]["rotation"])
            else:
                # The offset and rotation is interpolated between the offset and rotation
                # values for the two adjacent keyframes containing this part.
                # The interpolation is smoothed using the sine wave S shape.
                prev_keyframe = keyframes[str(prev_keyframe_index)]
                next_keyframe = keyframes[str(next_keyframe_index)]
                s = (
                    (keyframe_t - prev_keyframe_index)
                    / (next_keyframe_index - prev_keyframe_index)
                )
                s = (1 + math.sin(math.radians(180) * (s - 0.5))) / 2
                self._set_offset(
                    part,
                    pygame.Vector2(prev_keyframe[part]["offset"])
                    .lerp(pygame.Vector2(next_keyframe[part]["offset"]), s)
                )
                self._set_rotation(
                    part,
                    (1 - s) * prev_keyframe[part]["rotation"]
                    + s * next_keyframe[part]["rotation"]
                )

    def update(self, dt: float):
        """Update the live2d sprite."""
        animation = self.animations.get(self.animation, {})
        keyframes = _animation_keyframes(animation)
        if len(keyframes.keys()) <= 1:
            self.t = 0
        else:
            # Update the animation progress.
            max_keyframe_index = max(int(keyframe_index) for keyframe_index in keyframes.keys())
            keyframe_duration = animation.get(KEYFRAME_DURATION_KEY, self.KEYFRAME_DURATION)
            duration = max_keyframe_index * keyframe_duration
            next_t = self.t + dt
            if animation.get(NO_LOOP_KEY, False) is True:
                # This animation does not loop; keep the sprite at the final keyframe.
                self.t = min(next_t, duration)
            elif (new_animation := animation.get(NEXT_ANIMATION_KEY)) is not None:
                # This animation should go to the new animation when it is complete.
                if next_t >= duration:
                    self.set_animation(new_animation)
                else:
                    self.t = next_t
            else:
                # This animation loops.
                self.t = next_t % duration

        self._update_offset_and_rotation()

    def _get_facial_expression(self) -> str:
        """Get the facial expression of the current animation."""
        animation = self.animations.get(self.animation, {})
        expression = animation.get(FACIAL_EXPRESSION_KEY, FACIAL_EXPRESSION_PART_NAMES[0])
        if expression not in FACIAL_EXPRESSION_PART_NAMES:
            return FACIAL_EXPRESSION_PART_NAMES[0]
        return expression

    def draw(self, surface: pygame.Surface, x: float, y: float, flipx: bool, alpha: float = 255):
        """Draw the live2d sprite."""
        alpha = int(max(0, min(255, alpha)))
        root = pygame.Vector2(LAYER_SIZE, LAYER_SIZE)

        # Make the sprite surf larger to account for offsets and rotations.
        sprite_surf = pygame.Surface((2 * LAYER_SIZE, 2 * LAYER_SIZE))
        sprite_surf.fill((255, 0, 0))
        sprite_surf.set_colorkey((255, 0, 0))

        for part in self.DRAW_ORDER:
            if part in self.parts:
                self.parts[part].draw(sprite_surf, root, flipx)
                if part == "head":
                    expression = self._get_facial_expression()
                    self.parts[expression].draw(sprite_surf, root, flipx)

        sprite_surf.set_alpha(alpha)
        sprite_rect = sprite_surf.get_rect()
        sprite_rect.center = (x, y)
        surface.blit(sprite_surf, sprite_rect)
