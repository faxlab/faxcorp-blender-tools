import bpy
from bpy.props import EnumProperty, FloatProperty, PointerProperty
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


class FAXCORP_LayoutObjectsSettings(PropertyGroup):
    axis: EnumProperty(
        name="Axis",
        items=[("X", "X", ""), ("Y", "Y", ""), ("Z", "Z", "")],
        default="X",
    )
    gap: FloatProperty(
        name="Distance",
        description="Gap between objects",
        default=0.1,
        min=0.0,
    )
    sort_method: EnumProperty(
        name="Sort by",
        items=[
            ("NAME", "Name", "Sort by name"),
            ("VOLUME", "Volume", "Sort by bounding box volume"),
        ],
        default="VOLUME",
    )


class OBJECT_OT_faxcorp_pack_on_axis(Operator):
    bl_idname = "object.faxcorp_pack_on_axis"
    bl_label = "Layout Selected"
    bl_description = "Layout selected objects end-to-end along X, Y, or Z"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        settings = context.scene.faxcorp_layout_objects_settings
        objects = list(context.selected_objects)
        active_object = context.active_object
        restore_mode = mode_to_restore(context)

        if len(objects) < 2:
            self.report({"WARNING"}, "Select at least two objects")
            return {"CANCELLED"}

        if context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")

        try:
            if settings.sort_method == "NAME":
                objects.sort(key=lambda obj: obj.name)
            elif settings.sort_method == "VOLUME":
                objects.sort(
                    key=lambda obj: obj.dimensions.x * obj.dimensions.y * obj.dimensions.z,
                    reverse=True,
                )

            axis_index = "XYZ".index(settings.axis)
            previous_center = objects[0].location[axis_index]
            previous_half = objects[0].dimensions[axis_index] / 2.0
            previous_end = previous_center + previous_half

            for obj in objects[1:]:
                half = obj.dimensions[axis_index] / 2.0
                new_center = previous_end + settings.gap + half
                location = obj.location.copy()
                location[axis_index] = new_center
                obj.location = location
                previous_end = new_center + half
        finally:
            restore_selection_and_mode(context, active_object, objects, restore_mode)

        self.report({"INFO"}, f"Laid out {len(objects)} object(s)")
        return {"FINISHED"}


def menu_func(self, context):
    self.layout.operator(OBJECT_OT_faxcorp_pack_on_axis.bl_idname, icon="EMPTY_ARROWS")


classes = (
    FAXCORP_LayoutObjectsSettings,
    OBJECT_OT_faxcorp_pack_on_axis,
)


def register():
    register_classes(classes)
    try:
        bpy.types.Scene.faxcorp_layout_objects_settings = PointerProperty(
            type=FAXCORP_LayoutObjectsSettings
        )
        append_menu(bpy.types.VIEW3D_MT_object, menu_func, menu_state)
    except Exception:
        if hasattr(bpy.types.Scene, "faxcorp_layout_objects_settings"):
            del bpy.types.Scene.faxcorp_layout_objects_settings
        unregister_classes(classes)
        raise


def unregister():
    remove_menu(bpy.types.VIEW3D_MT_object, menu_func, menu_state)
    if hasattr(bpy.types.Scene, "faxcorp_layout_objects_settings"):
        del bpy.types.Scene.faxcorp_layout_objects_settings
    unregister_classes(classes)
