import bpy
from bpy.types import Menu

from . import (
    align_uv_islands,
    axis_mesh_clipper,
    clear_custom_normals,
    layout_objects,
    rename_by_collection,
    rename_to_material,
    set_pivot,
)
from .constants import TOOLBOX_MENU_IDNAME
from .utils import register_classes, unregister_classes


class VIEW3D_MT_faxcorp_tools(Menu):
    bl_idname = TOOLBOX_MENU_IDNAME
    bl_label = "FaxCorp Tools"

    def draw(self, context):
        layout = self.layout
        layout.menu(axis_mesh_clipper.VIEW3D_MT_faxcorp_axis_mesh_clipper.bl_idname)
        layout.separator()
        layout.operator(
            rename_to_material.OBJECT_OT_faxcorp_rename_to_material.bl_idname,
            icon="MATERIAL",
        )
        layout.operator(
            rename_by_collection.OBJECT_OT_faxcorp_rename_by_collection.bl_idname,
            icon="OUTLINER_COLLECTION",
        )
        layout.separator()
        layout.operator(
            layout_objects.OBJECT_OT_faxcorp_pack_on_axis.bl_idname,
            icon="EMPTY_ARROWS",
        )
        row = layout.row()
        row.operator_context = "INVOKE_DEFAULT"
        row.operator(set_pivot.OBJECT_OT_faxcorp_set_pivot_dialog.bl_idname)
        layout.operator(
            clear_custom_normals.MESH_OT_faxcorp_clear_split_normals.bl_idname,
            icon="NORMALS_VERTEX",
        )
        layout.operator(
            align_uv_islands.UV_OT_faxcorp_align_by_longest_edge.bl_idname,
            icon="UV",
        )


def draw_menu_button(layout):
    layout.menu(VIEW3D_MT_faxcorp_tools.bl_idname, text="All FaxCorp Tools")


classes = (VIEW3D_MT_faxcorp_tools,)


def register():
    register_classes(classes)


def unregister():
    unregister_classes(classes)
