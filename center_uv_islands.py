import bmesh
import bpy
from bpy.props import BoolProperty
from mathutils import Vector
from bpy.types import Operator, Panel

from .utils import append_menu, register_classes, remove_menu, unregister_classes
from .constants import SIDEBAR_CATEGORY


menu_state = {"appended": False}
UV_CENTER = Vector((0.5, 0.5))
SCENE_INDIVIDUALLY_PROP = "faxcorp_center_uv_individually"


def active_uv_layer(bm):
    uv = bm.loops.layers.uv.active
    if uv is None:
        raise RuntimeError("No active UV layer")
    return uv


def face_uv_edge_keys(face, uv_layer):
    keys = []
    loops = face.loops
    loop_count = len(loops)
    for index in range(loop_count):
        uv1 = loops[index][uv_layer].uv
        uv2 = loops[(index + 1) % loop_count][uv_layer].uv
        point_a = (uv1.x, uv1.y)
        point_b = (uv2.x, uv2.y)
        keys.append(tuple(sorted((point_a, point_b))))
    return keys


def build_islands(bm):
    uv_layer = active_uv_layer(bm)
    faces = list(bm.faces)
    if not faces:
        return []

    edge_map = {}
    for face in faces:
        for key in face_uv_edge_keys(face, uv_layer):
            edge_map.setdefault(key, []).append(face)

    neighbors = {face: set() for face in faces}
    for linked_faces in edge_map.values():
        if len(linked_faces) < 2:
            continue
        for index, face_a in enumerate(linked_faces):
            for face_b in linked_faces[index + 1:]:
                neighbors[face_a].add(face_b)
                neighbors[face_b].add(face_a)

    islands = []
    seen = set()
    for face in faces:
        if face in seen:
            continue
        stack = [face]
        island = set()
        seen.add(face)
        while stack:
            current = stack.pop()
            island.add(current)
            for neighbor in neighbors[current]:
                if neighbor not in seen:
                    seen.add(neighbor)
                    stack.append(neighbor)
        islands.append(island)
    return islands


def uv_loop_selected(loop, uv_layer):
    uv_data = loop[uv_layer]
    return bool(getattr(uv_data, "select", False) or getattr(uv_data, "select_edge", False))


def island_is_selected(island, uv_layer):
    for face in island:
        if face.select:
            return True
        for loop in face.loops:
            if uv_loop_selected(loop, uv_layer):
                return True
    return False


def selected_island_loops(bm, respect_selection):
    uv_layer = active_uv_layer(bm)
    all_island_loops = []
    selected_island_loops = []

    for island in build_islands(bm):
        loops = []
        for face in island:
            for loop in face.loops:
                loops.append(loop)
        all_island_loops.append(loops)
        if island_is_selected(island, uv_layer):
            selected_island_loops.append(loops)

    if not all_island_loops:
        return uv_layer, []

    if not respect_selection or not selected_island_loops:
        return uv_layer, all_island_loops

    return uv_layer, selected_island_loops


def groups_by_mesh(objects):
    groups = {}
    for obj in objects:
        if obj.type == "MESH":
            groups.setdefault(obj.data.as_pointer(), []).append(obj)
    return list(groups.values())


def representative_for_group(group):
    return next((obj for obj in group if obj.mode == "EDIT"), group[0])


def collect_target(obj, respect_selection):
    if obj.mode == "EDIT":
        bm = bmesh.from_edit_mesh(obj.data)
        bm.faces.ensure_lookup_table()
        uv_layer, island_loops = selected_island_loops(bm, respect_selection=True)
        return {
            "mesh": obj.data,
            "bm": bm,
            "uv_layer": uv_layer,
            "island_loops": island_loops,
            "island_count": len(island_loops),
            "owned": False,
        }

    bm = bmesh.new()
    try:
        bm.from_mesh(obj.data)
        bm.faces.ensure_lookup_table()
        uv_layer, island_loops = selected_island_loops(bm, respect_selection=respect_selection)
        return {
            "mesh": obj.data,
            "bm": bm,
            "uv_layer": uv_layer,
            "island_loops": island_loops,
            "island_count": len(island_loops),
            "owned": True,
        }
    except Exception:
        bm.free()
        raise


def uv_bounds(loops, uv_layer):
    if not loops:
        return None, None

    min_uv = Vector((float("inf"), float("inf")))
    max_uv = Vector((float("-inf"), float("-inf")))
    for loop in loops:
        uv = loop[uv_layer].uv
        min_uv.x = min(min_uv.x, uv.x)
        min_uv.y = min(min_uv.y, uv.y)
        max_uv.x = max(max_uv.x, uv.x)
        max_uv.y = max(max_uv.y, uv.y)

    return min_uv, max_uv


def apply_island_offset(uv_layer, loops, offset):
    for loop in loops:
        loop[uv_layer].uv += offset


def write_target(target):
    if target["owned"]:
        target["bm"].to_mesh(target["mesh"])
        target["mesh"].update()
    else:
        bmesh.update_edit_mesh(target["mesh"], loop_triangles=False)


def combined_island_count(targets):
    return sum(target["island_count"] for target in targets)


def total_bounds(targets):
    all_min = Vector((float("inf"), float("inf")))
    all_max = Vector((float("-inf"), float("-inf")))
    has_values = False

    for target in targets:
        uv_layer = target["uv_layer"]
        for loops in target["island_loops"]:
            min_uv, max_uv = uv_bounds(loops, uv_layer)
            if min_uv is None or max_uv is None:
                continue
            all_min.x = min(all_min.x, min_uv.x)
            all_min.y = min(all_min.y, min_uv.y)
            all_max.x = max(all_max.x, max_uv.x)
            all_max.y = max(all_max.y, max_uv.y)
            has_values = True

    if not has_values:
        return None
    return all_min, all_max


def free_owned_targets(targets):
    for target in targets:
        if target["owned"]:
            target["bm"].free()


class UV_OT_faxcorp_center_selected_islands(Operator):
    bl_idname = "uv.faxcorp_center_selected_islands"
    bl_label = "Center Selected UV Islands"
    bl_description = "Center selected UV islands from selected mesh objects to UV space center"
    bl_options = {"REGISTER", "UNDO"}

    individually: BoolProperty(
        name="Individually",
        default=True,
        description="Center each selected UV island to the UV center individually",
    )

    def execute(self, context):
        selected = [obj for obj in context.selected_objects if obj.type == "MESH"]
        if not selected:
            self.report({"ERROR"}, "Select at least one mesh object")
            return {"CANCELLED"}

        targets = []
        try:
            for group in groups_by_mesh(selected):
                representative = representative_for_group(group)
                try:
                    target = collect_target(
                        representative,
                        respect_selection=(representative.mode == "EDIT"),
                    )
                except RuntimeError as exc:
                    self.report({"WARNING"}, f"Could not process {representative.name}: {exc}")
                    continue

                if target["island_loops"]:
                    targets.append(target)
                else:
                    if target["owned"]:
                        target["bm"].free()

            if not targets or combined_island_count(targets) == 0:
                self.report({"WARNING"}, "No UV islands found to center")
                return {"CANCELLED"}

            if self.individually:
                for target in targets:
                    uv_layer = target["uv_layer"]
                    for loops in target["island_loops"]:
                        bounds = uv_bounds(loops, uv_layer)
                        if bounds[0] is None:
                            continue
                        min_uv, max_uv = bounds
                        apply_island_offset(uv_layer, loops, UV_CENTER - (min_uv + max_uv) * 0.5)
                    write_target(target)
                island_count = combined_island_count(targets)
                self.report({"INFO"}, f"Centered {island_count} UV island(s) individually")
            else:
                bounds = total_bounds(targets)
                if bounds is None:
                    self.report({"WARNING"}, "No UV islands found to center")
                    return {"CANCELLED"}
                min_uv, max_uv = bounds
                offset = UV_CENTER - (min_uv + max_uv) * 0.5
                for target in targets:
                    uv_layer = target["uv_layer"]
                    for loops in target["island_loops"]:
                        apply_island_offset(uv_layer, loops, offset)
                    write_target(target)

                island_count = combined_island_count(targets)
                self.report({"INFO"}, f"Centered {island_count} UV island(s) as one selection")

            return {"FINISHED"}
        finally:
            free_owned_targets(targets)


def menu_func(self, context):
    menu_checkbox_and_operator(self.layout, context.scene)


class FAXCORP_PT_uv_editor_tools(Panel):
    bl_label = "UV"
    bl_idname = "FAXCORP_PT_uv_editor_tools"
    bl_space_type = "IMAGE_EDITOR"
    bl_region_type = "UI"
    bl_category = SIDEBAR_CATEGORY

    def draw(self, context):
        menu_checkbox_and_operator(self.layout, context.scene)


def menu_checkbox_and_operator(layout, scene):
    row = layout.row(align=True)
    split = row.split(factor=0.8, align=True)
    left = split.row(align=True)
    right = split.row(align=True)
    op = left.operator(UV_OT_faxcorp_center_selected_islands.bl_idname, icon="UV", text="Center UV")
    op.individually = getattr(scene, SCENE_INDIVIDUALLY_PROP)
    right.label(text="Ind")
    right.prop(scene, SCENE_INDIVIDUALLY_PROP, text="")
    return row


classes = (
    UV_OT_faxcorp_center_selected_islands,
    FAXCORP_PT_uv_editor_tools,
)


def register():
    try:
        if not hasattr(bpy.types.Scene, SCENE_INDIVIDUALLY_PROP):
            setattr(
                bpy.types.Scene,
                SCENE_INDIVIDUALLY_PROP,
                BoolProperty(
                    name="Individually",
                    default=True,
                    description="Center each selected UV island to the UV center individually",
                ),
            )

        register_classes(classes)
        append_menu(bpy.types.IMAGE_MT_uvs, menu_func, menu_state)
    except Exception:
        if hasattr(bpy.types.Scene, SCENE_INDIVIDUALLY_PROP):
            delattr(bpy.types.Scene, SCENE_INDIVIDUALLY_PROP)
        unregister_classes(classes)
        raise


def unregister():
    if hasattr(bpy.types.Scene, SCENE_INDIVIDUALLY_PROP):
        delattr(bpy.types.Scene, SCENE_INDIVIDUALLY_PROP)
    remove_menu(bpy.types.IMAGE_MT_uvs, menu_func, menu_state)
    unregister_classes(classes)
