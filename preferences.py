import bpy
from bpy.props import BoolProperty, StringProperty
from bpy.types import AddonPreferences

from .constants import ADDON_ID
from .utils import register_classes, unregister_classes


SHORTCUT_ROWS = (
    ("toolbox", "All FaxCorp Tools"),
    ("axis_clipper", "Axis Mesh Clipper"),
    ("rename_material", "Rename to Material"),
    ("rename_collection", "Rename by Collection"),
    ("layout_objects", "Layout Objects"),
    ("set_pivot", "Set Pivot"),
    ("clear_normals", "Clear Split Normals"),
    ("align_uv", "Align UV Islands"),
)


def update_shortcuts(self, context):
    from . import shortcuts

    shortcuts.register_keymaps()


def key_property(label):
    return StringProperty(
        name=f"{label} Key",
        description="Blender key event name, for example C, X, F5, SPACE, or TAB. Leave blank to disable.",
        default="",
        update=update_shortcuts,
    )


def modifier_property(label):
    return BoolProperty(
        name=label,
        default=False,
        update=update_shortcuts,
    )


def shortcut_label(prefs, prefix):
    key = getattr(prefs, f"{prefix}_shortcut_key", "").strip().upper()
    if not key:
        return "Not assigned"

    parts = []
    if getattr(prefs, f"{prefix}_shortcut_ctrl", False):
        parts.append("Ctrl")
    if getattr(prefs, f"{prefix}_shortcut_shift", False):
        parts.append("Shift")
    if getattr(prefs, f"{prefix}_shortcut_alt", False):
        parts.append("Alt")
    if getattr(prefs, f"{prefix}_shortcut_oskey", False):
        parts.append("OSKey")
    parts.append(key)
    return "+".join(parts)


def draw_shortcut(layout, prefs, prefix, label):
    split = layout.split(factor=0.28, align=True)
    split.label(text=label)

    row = split.row(align=True)
    row.prop(prefs, f"{prefix}_shortcut_key", text="")
    row.prop(prefs, f"{prefix}_shortcut_ctrl", text="Ctrl", toggle=True)
    row.prop(prefs, f"{prefix}_shortcut_shift", text="Shift", toggle=True)
    row.prop(prefs, f"{prefix}_shortcut_alt", text="Alt", toggle=True)
    row.prop(prefs, f"{prefix}_shortcut_oskey", text="OS", toggle=True)


class FAXCORP_AddonPreferences(AddonPreferences):
    bl_idname = ADDON_ID

    toolbox_shortcut_key: key_property("All FaxCorp Tools")
    toolbox_shortcut_ctrl: modifier_property("Ctrl")
    toolbox_shortcut_shift: modifier_property("Shift")
    toolbox_shortcut_alt: modifier_property("Alt")
    toolbox_shortcut_oskey: modifier_property("OSKey")

    axis_clipper_shortcut_key: key_property("Axis Mesh Clipper")
    axis_clipper_shortcut_ctrl: modifier_property("Ctrl")
    axis_clipper_shortcut_shift: modifier_property("Shift")
    axis_clipper_shortcut_alt: modifier_property("Alt")
    axis_clipper_shortcut_oskey: modifier_property("OSKey")

    rename_material_shortcut_key: key_property("Rename to Material")
    rename_material_shortcut_ctrl: modifier_property("Ctrl")
    rename_material_shortcut_shift: modifier_property("Shift")
    rename_material_shortcut_alt: modifier_property("Alt")
    rename_material_shortcut_oskey: modifier_property("OSKey")

    rename_collection_shortcut_key: key_property("Rename by Collection")
    rename_collection_shortcut_ctrl: modifier_property("Ctrl")
    rename_collection_shortcut_shift: modifier_property("Shift")
    rename_collection_shortcut_alt: modifier_property("Alt")
    rename_collection_shortcut_oskey: modifier_property("OSKey")

    layout_objects_shortcut_key: key_property("Layout Objects")
    layout_objects_shortcut_ctrl: modifier_property("Ctrl")
    layout_objects_shortcut_shift: modifier_property("Shift")
    layout_objects_shortcut_alt: modifier_property("Alt")
    layout_objects_shortcut_oskey: modifier_property("OSKey")

    set_pivot_shortcut_key: key_property("Set Pivot")
    set_pivot_shortcut_ctrl: modifier_property("Ctrl")
    set_pivot_shortcut_shift: modifier_property("Shift")
    set_pivot_shortcut_alt: modifier_property("Alt")
    set_pivot_shortcut_oskey: modifier_property("OSKey")

    clear_normals_shortcut_key: key_property("Clear Split Normals")
    clear_normals_shortcut_ctrl: modifier_property("Ctrl")
    clear_normals_shortcut_shift: modifier_property("Shift")
    clear_normals_shortcut_alt: modifier_property("Alt")
    clear_normals_shortcut_oskey: modifier_property("OSKey")

    align_uv_shortcut_key: key_property("Align UV Islands")
    align_uv_shortcut_ctrl: modifier_property("Ctrl")
    align_uv_shortcut_shift: modifier_property("Shift")
    align_uv_shortcut_alt: modifier_property("Alt")
    align_uv_shortcut_oskey: modifier_property("OSKey")

    def draw(self, context):
        layout = self.layout
        layout.label(text="Shortcuts")
        layout.label(text="Leave the key field blank to disable a shortcut.")
        layout.separator()

        for prefix, label in SHORTCUT_ROWS:
            draw_shortcut(layout, self, prefix, label)

        layout.label(text="Use Blender key event names such as C, X, F5, SPACE, TAB.")


classes = (FAXCORP_AddonPreferences,)


def get_preferences(context=None):
    context = context or bpy.context
    addon = context.preferences.addons.get(ADDON_ID)
    return addon.preferences if addon else None


def register():
    register_classes(classes)


def unregister():
    unregister_classes(classes)
