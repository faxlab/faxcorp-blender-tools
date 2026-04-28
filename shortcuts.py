import bpy

from .constants import AXIS_CLIPPER_MENU_IDNAME, TOOLBOX_MENU_IDNAME


addon_keymaps = []


SHORTCUT_ACTIONS = (
    ("toolbox", "All FaxCorp Tools", "wm.call_menu", {"name": TOOLBOX_MENU_IDNAME}),
    ("axis_clipper", "Axis Mesh Clipper", "wm.call_menu", {"name": AXIS_CLIPPER_MENU_IDNAME}),
    ("rename_material", "Rename to Material", "object.faxcorp_rename_to_material", {}),
    ("rename_collection", "Rename by Collection", "object.faxcorp_rename_by_collection", {}),
    ("layout_objects", "Layout Objects", "object.faxcorp_pack_on_axis", {}),
    ("set_pivot", "Set Pivot", "object.faxcorp_set_pivot", {}),
    ("clear_normals", "Clear Split Normals", "mesh.faxcorp_clear_split_normals", {}),
    ("align_uv", "Align UV Islands", "uv.faxcorp_align_by_longest_edge", {}),
)


def remove_keymaps():
    for keymap, item in addon_keymaps:
        try:
            keymap.keymap_items.remove(item)
        except Exception:
            pass
    addon_keymaps.clear()


def shortcut_key(prefs, prefix):
    if prefs is None:
        return ""
    return getattr(prefs, f"{prefix}_shortcut_key", "").strip().upper()


def shortcut_modifiers(prefs, prefix):
    if prefs is None:
        return {
            "ctrl": False,
            "shift": False,
            "alt": False,
            "oskey": False,
        }
    return {
        "ctrl": getattr(prefs, f"{prefix}_shortcut_ctrl", False),
        "shift": getattr(prefs, f"{prefix}_shortcut_shift", False),
        "alt": getattr(prefs, f"{prefix}_shortcut_alt", False),
        "oskey": getattr(prefs, f"{prefix}_shortcut_oskey", False),
    }


def register_keymaps():
    remove_keymaps()

    window_manager = bpy.context.window_manager
    keyconfig = window_manager.keyconfigs.addon
    if keyconfig is None:
        return

    from .preferences import get_preferences

    prefs = get_preferences()
    enabled_actions = []
    for prefix, label, idname, properties in SHORTCUT_ACTIONS:
        key_type = shortcut_key(prefs, prefix)
        if key_type:
            enabled_actions.append((prefix, label, idname, properties, key_type))

    if not enabled_actions:
        return

    keymap = keyconfig.keymaps.new(
        name="3D View",
        space_type="VIEW_3D",
        region_type="WINDOW",
    )

    added_items = 0
    for prefix, label, idname, properties, key_type in enabled_actions:
        try:
            item = keymap.keymap_items.new(
                idname,
                type=key_type,
                value="PRESS",
                **shortcut_modifiers(prefs, prefix),
            )
        except Exception as exc:
            print(f"FaxCorp Blender Tools: invalid shortcut for {label} '{key_type}': {exc}")
            continue

        for property_name, property_value in properties.items():
            setattr(item.properties, property_name, property_value)

        addon_keymaps.append((keymap, item))
        added_items += 1

    if added_items == 0:
        try:
            keyconfig.keymaps.remove(keymap)
        except Exception:
            pass


def register():
    register_keymaps()


def unregister():
    remove_keymaps()
