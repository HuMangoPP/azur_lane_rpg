import json
import math
import pygame

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


class Live2D:
    DRAW_ORDER = [
        "back_hair",
        "torso_back",
        "left_leg",
        "right_leg",
        "left_arm",
        "torso",
        "right_arm",
        "head",
        "face",
        "top_of_head",
        "left_hair",
        "left_bangs",
        "right_hair",
        "right_bangs",
        "bangs",
    ]

    CONNECTIONS = {
        "back_hair": "head",
        "torso_back": "torso",
        "left_leg": "torso",
        "right_leg": "torso",
        "torso": None,
        "left_arm": "torso",
        "head": "torso",
        "face": "head",
        "top_of_head": "head",
        "left_hair": "head",
        "left_bangs": "head",
        "right_hair": "head",
        "right_bangs": "head",
        "bangs": "head",
        "right_arm": "torso",
    }

    IDLE_ANIMATION = 0
    WALK_ANIMATION = 1

    def __init__(self, model_file):
        self.t = 0
        self.parts = {}

        self.animation = self.IDLE_ANIMATION

        with open(model_file) as f:
            self.model_dict = json.load(f)
        
        scale = 1
        for part, part_data in self.model_dict.items():
            image = pygame.transform.scale_by(pygame.image.load(part_data["path"]).convert_alpha(), scale)
            image.set_colorkey((255,0,0))
            live2d_part = Live2DPart(image, scale*pygame.Vector2(part_data["pivot"]))
            self.parts[part] = live2d_part
        
        for part, parent_part in self.CONNECTIONS.items():
            if parent_part is not None:
                live2d_part = self.parts[part]
                live2d_part.parent_part = self.parts[parent_part]

    def set_rotation(self, part, angle):
        if part in self.parts:
            self.parts[part].rotation = angle
    
    def set_offset(self, part, offset):
        if part in self.parts:
            self.parts[part].offset = offset
    
    def set_animation(self, animation):
        if self.animation != animation:
            self.animation = animation
            self.t = 0

    def update(self, dt):
        self.t += dt
        if self.animation == self.IDLE_ANIMATION:
            t = math.radians(270 * self.t)
            one_plus_sint = 0.5 * (1 + math.sin(t))
            anim_t = {"one_plus_sint": one_plus_sint}
            for part, part_data in self.model_dict.items():
                idle_animation = part_data["idle"]
                if idle_animation[1] is None:
                    continue
                self.set_rotation(part, idle_animation[0] * anim_t[idle_animation[1]])
            self.set_offset("torso", pygame.Vector2(0, 5 * one_plus_sint))
        elif self.animation == self.WALK_ANIMATION:
            t = math.radians(270 * self.t)
            sint = math.sin(t)
            sint_sq = sint ** 2
            anim_t = {"sint": sint, "sint_sq": sint_sq}
            for part, part_data in self.model_dict.items():
                walk_animation = part_data["walk"]
                if walk_animation[1] is None:
                    continue
                self.set_rotation(part, walk_animation[0] * anim_t[walk_animation[1]])
            self.set_offset("torso", pygame.Vector2(0, 5 * sint_sq))

    def draw(self, surface, x, y, flipx):
        root = pygame.Vector2(x, y)

        for part in self.DRAW_ORDER:
            if part in self.parts:
                self.parts[part].draw(surface, root, flipx)