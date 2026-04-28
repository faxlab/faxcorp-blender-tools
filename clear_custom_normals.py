import bpy
from bpy.types import Operator


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

        for obj in selected_objects:
            if obj.name in bpy.data.objects:
                obj.select_set(True)
        if active_object and active_object.name in bpy.data.objects:
            context.view_layer.objects.active = active_object

        if cleared == 0:
            self.report({"WARNING"}, "No custom split normals were cleared")
            return {"CANCELLED"}

        self.report({"INFO"}, f"Cleared split normals on {cleared} mesh object(s)")
        return {"FINISHED"}


def menu_func(self, context):
    self.layout.operator(MESH_OT_faxcorp_clear_split_normals.bl_idname, icon="NORMALS_VERTEX")


classes = (MESH_OT_faxcorp_clear_split_normals,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.VIEW3D_MT_object.append(menu_func)


def unregister():
    bpy.types.VIEW3D_MT_object.remove(menu_func)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
