import bpy
from mathutils import Matrix, Vector
from bpy.props import EnumProperty, PointerProperty
from bpy.types import Operator, PropertyGroup

from .utils import (
    append_menu,
    mode_to_restore,
    register_classes,
    remove_menu,
    restore_selection_and_mode,
    unregister_classes,
)


menu_state = {"appended": False}

PIVOT_MODE_ITEMS = (
    ("MIN", "Min", "Use the minimum local bound on this axis"),
    ("MIDDLE", "Middle", "Use the midpoint between local min and max on this axis"),
    ("MAX", "Max", "Use the maximum local bound on this axis"),
    ("KEEP", "Keep", "Keep the current origin position on this axis"),
)


class FAXCORP_SetPivotSettings(PropertyGroup):
    x_mode: EnumProperty(
        name="X",
        items=PIVOT_MODE_ITEMS,
        default="MIDDLE",
    )
    y_mode: EnumProperty(
        name="Y",
        items=PIVOT_MODE_ITEMS,
        default="MIDDLE",
    )
    z_mode: EnumProperty(
        name="Z",
        items=PIVOT_MODE_ITEMS,
        default="MIN",
    )


def mesh_bounds(mesh):
    if not mesh.vertices:
        return None

    first = mesh.vertices[0].co.copy()
    min_bound = first.copy()
    max_bound = first.copy()

    for vertex in mesh.vertices[1:]:
        co = vertex.co
        min_bound.x = min(min_bound.x, co.x)
        min_bound.y = min(min_bound.y, co.y)
        min_bound.z = min(min_bound.z, co.z)
        max_bound.x = max(max_bound.x, co.x)
        max_bound.y = max(max_bound.y, co.y)
        max_bound.z = max(max_bound.z, co.z)

    return min_bound, max_bound


def axis_target(mode, axis_index, min_bound, max_bound):
    if mode == "MIN":
        return min_bound[axis_index]
    if mode == "MIDDLE":
        return (min_bound[axis_index] + max_bound[axis_index]) * 0.5
    if mode == "MAX":
        return max_bound[axis_index]
    return 0.0


def target_from_settings(settings, min_bound, max_bound):
    return Vector((
        axis_target(settings.x_mode, 0, min_bound, max_bound),
        axis_target(settings.y_mode, 1, min_bound, max_bound),
        axis_target(settings.z_mode, 2, min_bound, max_bound),
    ))


def offset_mesh_data(mesh, delta):
    if mesh.shape_keys:
        for key_block in mesh.shape_keys.key_blocks:
            for point in key_block.data:
                point.co -= delta
    else:
        for vertex in mesh.vertices:
            vertex.co -= delta
    mesh.update()


def set_object_pivot(obj, target_local):
    if target_local.length_squared == 0.0:
        return False, False

    copied_mesh = False
    child_matrices = [(child, child.matrix_world.copy()) for child in obj.children]
    old_matrix_world = obj.matrix_world.copy()

    if obj.data.users > 1:
        obj.data = obj.data.copy()
        copied_mesh = True

    offset_mesh_data(obj.data, target_local)
    obj.matrix_world = old_matrix_world @ Matrix.Translation(target_local)

    for child, matrix_world in child_matrices:
        child.matrix_world = matrix_world

    return True, copied_mesh


class OBJECT_OT_faxcorp_set_pivot(Operator):
    bl_idname = "object.faxcorp_set_pivot"
    bl_label = "Set Pivot"
    bl_description = "Set selected mesh object pivots from local bounds"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return any(obj.type == "MESH" for obj in context.selected_objects)

    def execute(self, context):
        settings = context.scene.faxcorp_set_pivot_settings
        selected_objects = list(context.selected_objects)
        selected_meshes = [obj for obj in selected_objects if obj.type == "MESH" and obj.data]
        active_object = context.active_object
        restore_mode = mode_to_restore(context)

        if not selected_meshes:
            self.report({"WARNING"}, "No selected mesh objects found")
            return {"CANCELLED"}

        if context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")

        changed = 0
        skipped_empty = 0
        copied_meshes = 0

        try:
            for obj in selected_meshes:
                bounds = mesh_bounds(obj.data)
                if bounds is None:
                    skipped_empty += 1
                    continue

                target_local = target_from_settings(settings, bounds[0], bounds[1])
                did_change, copied_mesh = set_object_pivot(obj, target_local)
                if did_change:
                    changed += 1
                if copied_mesh:
                    copied_meshes += 1
        finally:
            restore_selection_and_mode(context, active_object, selected_objects, restore_mode)

        if changed == 0:
            self.report({"WARNING"}, "No pivots were changed")
            return {"CANCELLED"}

        message = f"Set pivot on {changed} mesh object(s)"
        if skipped_empty:
            message += f", skipped {skipped_empty} empty mesh(es)"
        if copied_meshes:
            message += f", made {copied_meshes} linked mesh copy/copies"
        self.report({"INFO"}, message)
        return {"FINISHED"}


def menu_func(self, context):
    self.layout.operator(OBJECT_OT_faxcorp_set_pivot.bl_idname)


classes = (
    FAXCORP_SetPivotSettings,
    OBJECT_OT_faxcorp_set_pivot,
)


def register():
    register_classes(classes)
    try:
        bpy.types.Scene.faxcorp_set_pivot_settings = PointerProperty(
            type=FAXCORP_SetPivotSettings
        )
        append_menu(bpy.types.VIEW3D_MT_object, menu_func, menu_state)
    except Exception:
        remove_menu(bpy.types.VIEW3D_MT_object, menu_func, menu_state)
        if hasattr(bpy.types.Scene, "faxcorp_set_pivot_settings"):
            del bpy.types.Scene.faxcorp_set_pivot_settings
        unregister_classes(classes)
        raise


def unregister():
    remove_menu(bpy.types.VIEW3D_MT_object, menu_func, menu_state)
    if hasattr(bpy.types.Scene, "faxcorp_set_pivot_settings"):
        del bpy.types.Scene.faxcorp_set_pivot_settings
    unregister_classes(classes)
