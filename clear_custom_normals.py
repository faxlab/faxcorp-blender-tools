import bpy
from bpy.types import Operator

from .utils import (
    append_menu,
    mode_to_restore,
    register_classes,
    remove_menu,
    restore_selection_and_mode,
    unregister_classes,
)


menu_state = {"appended": False}


class MESH_OT_faxcorp_clear_split_normals(Operator):
    bl_idname = "mesh.faxcorp_clear_split_normals"
    bl_label = "Clear Split Normals"
    bl_description = "Clear custom split normals on selected mesh objects"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return any(obj.type == "MESH" for obj in context.selected_objects)

    def execute(self, context):
        selected_objects = list(context.selected_objects)
        selected_meshes = [obj for obj in selected_objects if obj.type == "MESH"]
        active_object = context.active_object
        restore_mode = mode_to_restore(context)

        if context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")

        cleared = 0
        for obj in selected_meshes:
            context.view_layer.objects.active = obj
            try:
                bpy.ops.mesh.customdata_custom_splitnormals_clear()
            except RuntimeError as exc:
                self.report({"WARNING"}, f"Could not clear {obj.name}: {exc}")
                continue
            cleared += 1

        restore_selection_and_mode(context, active_object, selected_objects, restore_mode)

        if cleared == 0:
            self.report({"WARNING"}, "No custom split normals were cleared")
            return {"CANCELLED"}

        self.report({"INFO"}, f"Cleared split normals on {cleared} mesh object(s)")
        return {"FINISHED"}


def menu_func(self, context):
    self.layout.operator(MESH_OT_faxcorp_clear_split_normals.bl_idname, icon="NORMALS_VERTEX")


classes = (MESH_OT_faxcorp_clear_split_normals,)


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
