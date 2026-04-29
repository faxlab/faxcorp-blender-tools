import re

import bpy
from bpy.types import Operator

from .utils import append_menu, register_classes, remove_menu, unregister_classes


menu_state = {"appended": False}

STRIP_PATTERN = re.compile(r"[.\d]+")


def cleaned_name(name):
    cleaned = STRIP_PATTERN.sub("", name).strip()
    return cleaned or "Object"


class OBJECT_OT_faxcorp_strip_dots_numbers(Operator):
    bl_idname = "object.faxcorp_strip_dots_numbers"
    bl_label = "Strip Dots and Numbers"
    bl_description = "Remove dots and digits from selected object names"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return bool(context.selected_objects)

    def execute(self, context):
        renamed = 0

        for obj in context.selected_objects:
            new_name = cleaned_name(obj.name)
            if obj.name == new_name:
                continue
            obj.name = new_name
            renamed += 1

        if renamed == 0:
            self.report({"INFO"}, "No selected object names contained dots or numbers")
            return {"FINISHED"}

        self.report({"INFO"}, f"Cleaned {renamed} object name(s)")
        return {"FINISHED"}


def menu_func(self, context):
    self.layout.operator(OBJECT_OT_faxcorp_strip_dots_numbers.bl_idname, icon="FILE_TEXT")


classes = (OBJECT_OT_faxcorp_strip_dots_numbers,)


def register():
    register_classes(classes)
    try:
        append_menu(bpy.types.VIEW3D_MT_object, menu_func, menu_state)
    except Exception:
        unregister_classes(classes)
        raise


def unregister():
    remove_menu(bpy.types.VIEW3D_MT_object, menu_func, menu_state)
    unregister_classes(classes)
