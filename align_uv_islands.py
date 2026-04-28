import bmesh
import bpy
import math
from mathutils import Vector
from bpy.types import Operator


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
        point_a = Vector((uv1.x, uv1.y))
        point_b = Vector((uv2.x, uv2.y))
        if (point_a.x, point_a.y) < (point_b.x, point_b.y):
            key = (point_a.x, point_a.y, point_b.x, point_b.y)
        else:
            key = (point_b.x, point_b.y, point_a.x, point_a.y)
        keys.append(key)
    return keys


def build_islands(bm, respect_selection):
    uv = active_uv_layer(bm)
    faces = [face for face in bm.faces if face.select or not respect_selection]
    if not faces:
        return []

    edge_map = {}
    for face in faces:
        for key in face_uv_edge_keys(face, uv):
            edge_map.setdefault(key, []).append(face)

    neighbors = {face: set() for face in faces}
    for linked_faces in edge_map.values():
        if len(linked_faces) > 1:
            for i, face_a in enumerate(linked_faces):
                for face_b in linked_faces[i + 1:]:
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


def island_longest_edge_uv(island_faces, uv_layer):
    max_length = -1.0
    best = (Vector((0.0, 0.0)), Vector((1.0, 0.0)))
    seen_keys = set()
    for face in island_faces:
        loops = face.loops
        loop_count = len(loops)
        for index in range(loop_count):
            point_a = Vector(loops[index][uv_layer].uv)
            point_b = Vector(loops[(index + 1) % loop_count][uv_layer].uv)
            key = tuple(sorted(((point_a.x, point_a.y), (point_b.x, point_b.y))))
            if key in seen_keys:
                continue
            seen_keys.add(key)
            delta = point_b - point_a
            length = delta.length
            if length > max_length:
                max_length = length
                best = (point_a.copy(), point_b.copy())
    return best


def island_centroid_uv(island_faces, uv_layer):
    unique_uvs = {}
    for face in island_faces:
        for loop in face.loops:
            uv = loop[uv_layer].uv
            unique_uvs[(uv.x, uv.y)] = uv
    if not unique_uvs:
        return Vector((0.0, 0.0))
    total = Vector((0.0, 0.0))
    for uv in unique_uvs.values():
        total.x += uv.x
        total.y += uv.y
    scale = 1.0 / len(unique_uvs)
    return Vector((total.x * scale, total.y * scale))


def rotate_island(island_faces, uv_layer, angle_rad, pivot):
    cos_angle = math.cos(angle_rad)
    sin_angle = math.sin(angle_rad)
    for face in island_faces:
        for loop in face.loops:
            uv = loop[uv_layer].uv
            x = uv.x - pivot.x
            y = uv.y - pivot.y
            uv.x = (x * cos_angle - y * sin_angle) + pivot.x
            uv.y = (x * sin_angle + y * cos_angle) + pivot.y


def align_islands_in_bmesh(bm, respect_selection):
    uv = active_uv_layer(bm)
    islands = build_islands(bm, respect_selection)
    total = 0
    for island in islands:
        point_a, point_b = island_longest_edge_uv(island, uv)
        delta = point_b - point_a
        if delta.length_squared == 0.0:
            continue
        angle = -math.atan2(delta.y, delta.x)
        pivot = island_centroid_uv(island, uv)
        rotate_island(island, uv, angle, pivot)
        total += 1
    return total


def groups_by_mesh(objects):
    groups = {}
    for obj in objects:
        if obj.type == "MESH":
            groups.setdefault(obj.data.as_pointer(), []).append(obj)
    return list(groups.values())


def process_object(obj, respect_selection):
    if obj.type != "MESH":
        return 0

    if obj.mode == "EDIT":
        bm = bmesh.from_edit_mesh(obj.data)
        bm.faces.ensure_lookup_table()
        count = align_islands_in_bmesh(bm, respect_selection=True)
        bmesh.update_edit_mesh(obj.data, loop_triangles=False)
        return count

    mesh = obj.data
    bm = bmesh.new()
    try:
        bm.from_mesh(mesh)
        bm.faces.ensure_lookup_table()
        count = align_islands_in_bmesh(bm, respect_selection=False)
        bm.to_mesh(mesh)
        mesh.update()
        return count
    finally:
        bm.free()


class UV_OT_faxcorp_align_by_longest_edge(Operator):
    bl_idname = "uv.faxcorp_align_by_longest_edge"
    bl_label = "Align by Longest Edge"
    bl_description = "Rotate each UV island so its longest UV edge becomes horizontal"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        selected = [obj for obj in context.selected_objects if obj.type == "MESH"]
        if not selected:
            self.report({"ERROR"}, "Select at least one mesh object")
            return {"CANCELLED"}

        total_islands = 0
        processed_meshes = 0

        for group in groups_by_mesh(selected):
            representative = next((obj for obj in group if obj.mode == "EDIT"), group[0])
            try:
                total_islands += process_object(
                    representative,
                    respect_selection=(representative.mode == "EDIT"),
                )
            except RuntimeError as exc:
                self.report({"WARNING"}, f"Could not process {representative.name}: {exc}")
                continue
            processed_meshes += 1

        if processed_meshes == 0:
            return {"CANCELLED"}

        self.report(
            {"INFO"},
            f"Processed {processed_meshes} mesh(es). Islands aligned: {total_islands}",
        )
        return {"FINISHED"}


def menu_func(self, context):
    self.layout.operator(UV_OT_faxcorp_align_by_longest_edge.bl_idname, icon="UV")


classes = (UV_OT_faxcorp_align_by_longest_edge,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.IMAGE_MT_uvs.append(menu_func)


def unregister():
    bpy.types.IMAGE_MT_uvs.remove(menu_func)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
