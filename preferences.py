import bpy
from bpy.props import BoolProperty, StringProperty
from bpy.types import AddonPreferences

from .constants import ADDON_ID


def shortcut_label(prefs):
    parts = []
    if prefs.axis_shortcut_ctrl:
        parts.append("Ctrl")
    if prefs.axis_shortcut_shift:
        parts.append("Shift")
    if prefs.axis_shortcut_alt:
        parts.append("Alt")
    if prefs.axis_shortcut_oskey:
        parts.append("OSKey")
    parts.append(prefs.axis_shortcut_key.strip().upper() or "C")
    return "+".join(parts)


def update_axis_shortcut(self, context):
    from . import axis_mesh_clipper

    axis_mesh_clipper.register_keymap()


class FAXCORP_AddonPreferences(AddonPreferences):
    bl_idname = ADDON_ID

    axis_shortcut_key: StringProperty(
        name="Axis Clipper Key",
        description="Blender key event name, for example C, X, F5, SPACE, or TAB",
        default="C",
        update=update_axis_shortcut,
    )
    axis_shortcut_ctrl: BoolProperty(
        name="Ctrl",
        default=True,
        update=update_axis_shortcut,
    )
    axis_shortcut_shift: BoolProperty(
        name="Shift",
        default=True,
        update=update_axis_shortcut,
    )
    axis_shortcut_alt: BoolProperty(
        name="Alt",
        default=False,
        update=update_axis_shortcut,
    )
    axis_shortcut_oskey: BoolProperty(
        name="OSKey",
        default=False,
        update=update_axis_shortcut,
    )

    def draw(self, context):
        layout = self.layout
        layout.label(text="Axis Mesh Clipper")
        layout.label(text=f"Current shortcut: {shortcut_label(self)}")

        row = layout.row(align=True)
        row.prop(self, "axis_shortcut_ctrl", toggle=True)
        row.prop(self, "axis_shortcut_shift", toggle=True)
        row.prop(self, "axis_shortcut_alt", toggle=True)
        row.prop(self, "axis_shortcut_oskey", toggle=True)

        layout.prop(self, "axis_shortcut_key")
        layout.label(text="Use Blender key event names such as C, X, F5, SPACE, TAB.")


classes = (FAXCORP_AddonPreferences,)


def get_preferences(context=None):
    context = context or bpy.context
    addon = context.preferences.addons.get(ADDON_ID)
    return addon.preferences if addon else None


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
