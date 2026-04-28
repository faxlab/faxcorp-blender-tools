import bmesh
import bpy
from mathutils import Vector
from bpy.props import EnumProperty
from bpy.types import Menu, Operator

from .preferences import get_preferences


MENU_IDNAME = "VIEW3D_MT_faxcorp_axis_mesh_clipper"
EPSILON = 1.0e-6

addon_keymaps = []


AXIS_ITEMS = (
    ("X_NEG", "X-", "Remove geometry on the negative local X side"),
    ("X_POS", "X+", "Remove geometry on the positive local X side"),
    ("Y_NEG", "Y-", "Remove geometry on the negative local Y side"),
    ("Y_POS", "Y+", "Remove geometry on the positive local Y side"),
    ("Z_NEG", "Z-", "Remove geometry on the negative local Z side"),
    ("Z_POS", "Z+", "Remove geometry on the positive local Z side"),
)


def remove_keymap():
    for keymap, item in addon_keymaps:
        try:
            keymap.keymap_items.remove(item)
        except ReferenceError:
            pass
    addon_keymaps.clear()


def register_keymap():
    remove_keymap()

    window_manager = bpy.context.window_manager
    keyconfig = window_manager.keyconfigs.addon
    if keyconfig is None:
        return

    prefs = get_preferences()
    key_type = (prefs.axis_shortcut_key if prefs else "C").strip().upper() or "C"
    ctrl = prefs.axis_shortcut_ctrl if prefs else True
    shift = prefs.axis_shortcut_shift if prefs else True
    alt = prefs.axis_shortcut_alt if prefs else False
    oskey = prefs.axis_shortcut_oskey if prefs else False

    keymap = keyconfig.keymaps.new(
        name="3D View",
        space_type="VIEW_3D",
        region_type="WINDOW",
    )

    try:
        item = keymap.keymap_items.new(
            "wm.call_menu",
            type=key_type,
            value="PRESS",
            ctrl=ctrl,
            shift=shift,
            alt=alt,
            oskey=oskey,
        )
    except Exception as exc:
        try:
            keyconfig.keymaps.remove(keymap)
        except Exception:
            pass
        print(f"FaxCorp Blender Tools: invalid axis clipper shortcut '{key_type}': {exc}")
        return

    item.properties.name = MENU_IDNAME
    addon_keymaps.append((keymap, item))


def mode_to_restore(context):
    if context.mode == "EDIT_MESH":
        return "EDIT"
    active = context.active_object
    if active is not None and active.mode != "OBJECT":
        return active.mode
    return "OBJECT"


def restore_selection(context, active_object, selected_objects):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in selected_objects:
        if obj.name in bpy.data.objects:
            obj.select_set(True)
    if active_object and active_object.name in bpy.data.objects:
        context.view_layer.objects.active = active_object


def axis_settings(axis):
    axis_name, side = axis.split("_")
    axis_index = {"X": 0, "Y": 1, "Z": 2}[axis_name]
    normal = Vector((0.0, 0.0, 0.0))
    normal[axis_index] = 1.0
    remove_negative = side == "NEG"
    return axis_index, normal, remove_negative


def clip_mesh(mesh, axis):
    axis_index, normal, remove_negative = axis_settings(axis)

    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()

    if not bm.verts:
        bm.free()
        return False

    geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
    bmesh.ops.bisect_plane(
        bm,
        geom=geom,
        dist=EPSILON,
        plane_co=Vector((0.0, 0.0, 0.0)),
        plane_no=normal,
        clear_outer=False,
        clear_inner=False,
    )

    if remove_negative:
        verts_to_delete = [vert for vert in bm.verts if vert.co[axis_index] < -EPSILON]
    else:
        verts_to_delete = [vert for vert in bm.verts if vert.co[axis_index] > EPSILON]

    if not verts_to_delete:
        bm.free()
        return False

    bmesh.ops.delete(bm, geom=verts_to_delete, context="VERTS")
    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    return True


class MESH_OT_faxcorp_axis_mesh_clip(Operator):
    bl_idname = "mesh.faxcorp_axis_mesh_clip"
    bl_label = "Axis Mesh Clip"
    bl_description = "Clip selected meshes along a local object axis"
    bl_options = {"REGISTER", "UNDO"}

    axis: EnumProperty(
        name="Axis",
        description="Local axis side to remove",
        items=AXIS_ITEMS,
        default="X_NEG",
    )

    @classmethod
    def poll(cls, context):
        return any(obj.type == "MESH" for obj in context.selected_objects)

    def execute(self, context):
        active_object = context.active_object
        selected_objects = list(context.selected_objects)
        restore_mode = mode_to_restore(context)

        if context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")

        selected_meshes = [obj for obj in selected_objects if obj.type == "MESH" and obj.data]
        if not selected_meshes:
            self.report({"WARNING"}, "No selected mesh objects found")
            restore_selection(context, active_object, selected_objects)
            return {"CANCELLED"}

        changed = 0
        skipped_linked = 0
        processed_meshes = set()

        for obj in selected_meshes:
            mesh = obj.data
            mesh_key = mesh.as_pointer()
            if mesh_key in processed_meshes:
                skipped_linked += 1
                continue

            try:
                if clip_mesh(mesh, self.axis):
                    changed += 1
            except RuntimeError as exc:
                self.report({"WARNING"}, f"Could not clip {obj.name}: {exc}")

            processed_meshes.add(mesh_key)

        restore_selection(context, active_object, selected_objects)
        if restore_mode != "OBJECT":
            try:
                bpy.ops.object.mode_set(mode=restore_mode)
            except RuntimeError:
                pass

        if changed == 0:
            self.report({"WARNING"}, "No geometry was clipped")
            return {"CANCELLED"}

        message = f"Clipped {changed} mesh datablock(s)"
        if skipped_linked:
            message += f", skipped {skipped_linked} linked duplicate(s)"
        self.report({"INFO"}, message)
        return {"FINISHED"}


class VIEW3D_MT_faxcorp_axis_mesh_clipper(Menu):
    bl_idname = MENU_IDNAME
    bl_label = "Axis Mesh Clipper"

    def draw(self, context):
        layout = self.layout
        for axis, label, description in AXIS_ITEMS:
            operator = layout.operator(
                MESH_OT_faxcorp_axis_mesh_clip.bl_idname,
                text=label,
            )
            operator.axis = axis


def draw_menu_button(layout):
    layout.menu(VIEW3D_MT_faxcorp_axis_mesh_clipper.bl_idname, text="Axis Mesh Clipper")


classes = (
    MESH_OT_faxcorp_axis_mesh_clip,
    VIEW3D_MT_faxcorp_axis_mesh_clipper,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    register_keymap()


def unregister():
    remove_keymap()
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
