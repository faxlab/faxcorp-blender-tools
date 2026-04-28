import bpy
from bpy.types import Panel

from . import (
    align_uv_islands,
    axis_mesh_clipper,
    clear_custom_normals,
    layout_objects,
    rename_by_collection,
    rename_to_material,
    set_pivot,
    toolbox_menu,
)
from .constants import SIDEBAR_CATEGORY
from .utils import register_classes, unregister_classes


class FAXCORP_PT_tools_base:
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = SIDEBAR_CATEGORY


class FAXCORP_PT_mesh_tools(FAXCORP_PT_tools_base, Panel):
    bl_label = "Mesh"
    bl_idname = "FAXCORP_PT_mesh_tools"

    def draw(self, context):
        layout = self.layout
        toolbox_menu.draw_menu_button(layout)
        layout.separator()
        axis_mesh_clipper.draw_menu_button(layout)
        layout.operator(
            clear_custom_normals.MESH_OT_faxcorp_clear_split_normals.bl_idname,
            icon="NORMALS_VERTEX",
        )


class FAXCORP_PT_object_layout_tools(FAXCORP_PT_tools_base, Panel):
    bl_label = "Object Layout"
    bl_idname = "FAXCORP_PT_object_layout_tools"

    def draw(self, context):
        layout = self.layout
        settings = context.scene.faxcorp_layout_objects_settings
        layout.prop(settings, "axis")
        layout.prop(settings, "gap")
        layout.prop(settings, "sort_method")
        layout.separator()
        layout.operator(layout_objects.OBJECT_OT_faxcorp_pack_on_axis.bl_idname)


class FAXCORP_PT_set_pivot_tools(FAXCORP_PT_tools_base, Panel):
    bl_label = "Set Pivot"
    bl_idname = "FAXCORP_PT_set_pivot_tools"

    def draw(self, context):
        layout = self.layout
        settings = context.scene.faxcorp_set_pivot_settings
        row = layout.row(align=True)
        row.prop(settings, "x_mode", text="X")
        row.prop(settings, "y_mode", text="Y")
        row.prop(settings, "z_mode", text="Z")
        row = layout.row(align=True)
        row.operator(set_pivot.OBJECT_OT_faxcorp_set_pivot.bl_idname)
        row.operator_context = "INVOKE_DEFAULT"
        row.operator(set_pivot.OBJECT_OT_faxcorp_set_pivot_dialog.bl_idname, text="Options...")


class FAXCORP_PT_uv_tools(FAXCORP_PT_tools_base, Panel):
    bl_label = "UV"
    bl_idname = "FAXCORP_PT_uv_tools"

    def draw(self, context):
        self.layout.operator(
            align_uv_islands.UV_OT_faxcorp_align_by_longest_edge.bl_idname,
            icon="UV",
        )


class FAXCORP_PT_naming_tools(FAXCORP_PT_tools_base, Panel):
    bl_label = "Naming"
    bl_idname = "FAXCORP_PT_naming_tools"

    def draw(self, context):
        layout = self.layout
        layout.operator(
            rename_to_material.OBJECT_OT_faxcorp_rename_to_material.bl_idname,
            icon="MATERIAL",
        )
        layout.operator(
            rename_by_collection.OBJECT_OT_faxcorp_rename_by_collection.bl_idname,
            icon="OUTLINER_COLLECTION",
        )


classes = (
    FAXCORP_PT_mesh_tools,
    FAXCORP_PT_object_layout_tools,
    FAXCORP_PT_set_pivot_tools,
    FAXCORP_PT_uv_tools,
    FAXCORP_PT_naming_tools,
)


def register():
    register_classes(classes)


def unregister():
    unregister_classes(classes)
