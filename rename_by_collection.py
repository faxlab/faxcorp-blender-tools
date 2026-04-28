import bpy
from bpy.types import Operator

from .utils import append_menu, register_classes, remove_menu, unregister_classes


menu_state = {"appended": False}


class OBJECT_OT_faxcorp_rename_by_collection(Operator):
    bl_idname = "object.faxcorp_rename_by_collection"
    bl_label = "Rename by Collection"
    bl_description = "Rename selected objects by their first collection name"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return bool(context.selected_objects)

    def execute(self, context):
        renamed = 0
        for obj in context.selected_objects:
            collections = [col for col in obj.users_collection if col.name != "Scene Collection"]
            if collections:
                obj.name = collections[0].name
                renamed += 1

        if renamed == 0:
            self.report({"WARNING"}, "No collection names found")
            return {"CANCELLED"}

        self.report({"INFO"}, f"Renamed {renamed} object(s)")
        return {"FINISHED"}


def menu_func(self, context):
    self.layout.operator(OBJECT_OT_faxcorp_rename_by_collection.bl_idname, icon="OUTLINER_COLLECTION")


classes = (OBJECT_OT_faxcorp_rename_by_collection,)


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
