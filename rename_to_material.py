import bpy
from bpy.props import EnumProperty, StringProperty
from bpy.types import Operator

from .utils import append_menu, register_classes, remove_menu, unregister_classes


menu_state = {"appended": False}


def material_names_in_use(obj):
    if obj.type != "MESH" or obj.data is None:
        return []

    used_indices = set()
    for poly in obj.data.polygons:
        if 0 <= poly.material_index < len(obj.material_slots):
            used_indices.add(poly.material_index)

    if used_indices:
        return [
            slot.material.name
            for index, slot in enumerate(obj.material_slots)
            if index in used_indices and slot.material
        ]

    return [slot.material.name for slot in obj.material_slots if slot.material]


def cleaned_name(material_name, find_text, replace_text):
    if find_text:
        candidate = material_name.replace(find_text, replace_text)
        if candidate:
            return candidate
    return material_name


def separate_by_material(context, obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    context.view_layer.objects.active = obj

    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.separate(type="MATERIAL")
    bpy.ops.object.mode_set(mode="OBJECT")

    return [item for item in context.selected_objects if item.type == "MESH"]


class OBJECT_OT_faxcorp_rename_to_material(Operator):
    bl_idname = "object.faxcorp_rename_to_material"
    bl_label = "Rename to Material"
    bl_description = "Rename selected mesh objects using their material names"
    bl_options = {"REGISTER", "UNDO"}

    multi_material_mode: EnumProperty(
        name="If Multiple Materials",
        description="How to handle objects that use more than one material",
        items=[
            ("FIRST", "Use First", "Rename using the first material in use"),
            ("SPLIT", "Split", "Separate by material, then rename each new object"),
        ],
        default="SPLIT",
    )
    find_text: StringProperty(
        name="Find",
        description="Text to replace in the material name",
        default="MI_",
    )
    replace_text: StringProperty(
        name="Replace",
        description="Replacement text used when renaming objects",
        default="",
    )

    @classmethod
    def poll(cls, context):
        return any(obj.type == "MESH" for obj in context.selected_objects)

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "multi_material_mode")
        layout.prop(self, "find_text")
        layout.prop(self, "replace_text")

    def execute(self, context):
        if context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")

        selected_meshes = [obj for obj in context.selected_objects if obj.type == "MESH"]
        if not selected_meshes:
            self.report({"WARNING"}, "No selected mesh objects found")
            return {"CANCELLED"}

        renamed = 0
        skipped = 0
        result_objects = []

        for obj in list(selected_meshes):
            material_names = material_names_in_use(obj)
            if not material_names:
                skipped += 1
                continue

            if self.multi_material_mode == "SPLIT" and len(material_names) > 1:
                try:
                    objects_to_rename = separate_by_material(context, obj)
                except RuntimeError as exc:
                    self.report({"WARNING"}, f"Could not split {obj.name}: {exc}")
                    skipped += 1
                    continue
            else:
                objects_to_rename = [obj]

            for part in objects_to_rename:
                part_materials = material_names_in_use(part)
                if not part_materials:
                    skipped += 1
                    continue

                source_name = part_materials[0]
                part.name = cleaned_name(source_name, self.find_text, self.replace_text)
                result_objects.append(part)
                renamed += 1

        bpy.ops.object.select_all(action="DESELECT")
        for obj in result_objects:
            if obj.name in bpy.data.objects:
                obj.select_set(True)

        if result_objects:
            context.view_layer.objects.active = result_objects[0]

        if renamed == 0:
            self.report({"WARNING"}, "No objects were renamed")
            return {"CANCELLED"}

        message = f"Renamed {renamed} object(s)"
        if skipped:
            message += f", skipped {skipped}"
        self.report({"INFO"}, message)
        return {"FINISHED"}


def menu_func(self, context):
    self.layout.operator(OBJECT_OT_faxcorp_rename_to_material.bl_idname, icon="MATERIAL")


classes = (OBJECT_OT_faxcorp_rename_to_material,)


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
