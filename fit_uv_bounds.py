import bmesh
import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, PointerProperty
from bpy.types import Operator, Panel, PropertyGroup
from mathutils import Vector

from .constants import SIDEBAR_CATEGORY
from .utils import append_menu, register_classes, remove_menu, unregister_classes


menu_state = {"appended": False}
SETTINGS_ATTR = "faxcorp_uv_fit_bounds_settings"
EPSILON = 1.0e-9


ISLAND_FILTER_ITEMS = (
    (
        "AUTO",
        "Auto",
        "Use selected UV or mesh islands in Edit Mode; otherwise use every island on selected mesh objects",
    ),
    ("SELECTED", "Selected Islands", "Only transform islands touched by selected UVs or mesh elements"),
    ("ALL", "All Islands", "Transform every UV island on selected mesh objects"),
)

SCOPE_ITEMS = (
    ("SELECTION", "Together", "Treat all target islands as one combined bounds"),
    ("ISLANDS", "Each Island", "Fit or align every target island independently"),
)

TARGET_ITEMS = (
    ("CANVAS", "Canvas 0-1", "Use the default UV canvas from 0 to 1"),
    ("CUSTOM", "Custom Bounds", "Use custom U and V bounds"),
)

SCALE_MODE_ITEMS = (
    ("NONE", "Move Only", "Move bounds without scaling"),
    ("UNIFORM_FIT", "Fit Inside", "Uniformly scale until the bounds fit inside the target"),
    ("UNIFORM_FILL", "Fill Target", "Uniformly scale until the bounds cover the target"),
    ("UNIFORM_WIDTH", "Fit Width", "Uniformly scale until U width matches the target"),
    ("UNIFORM_HEIGHT", "Fit Height", "Uniformly scale until V height matches the target"),
    ("STRETCH", "Stretch All", "Scale U and V independently to match the target"),
    ("STRETCH_WIDTH", "Stretch Width", "Scale U only to match the target width"),
    ("STRETCH_HEIGHT", "Stretch Height", "Scale V only to match the target height"),
)

ALIGN_U_ITEMS = (
    ("KEEP", "Keep", "Keep current U position after scaling"),
    ("MIN", "Left", "Align minimum U to the target"),
    ("CENTER", "Center", "Align U center to the target"),
    ("MAX", "Right", "Align maximum U to the target"),
)

ALIGN_V_ITEMS = (
    ("KEEP", "Keep", "Keep current V position after scaling"),
    ("MIN", "Bottom", "Align minimum V to the target"),
    ("CENTER", "Center", "Align V center to the target"),
    ("MAX", "Top", "Align maximum V to the target"),
)

SETTING_NAMES = (
    "island_filter",
    "transform_scope",
    "target",
    "scale_mode",
    "align_u",
    "align_v",
    "padding",
    "custom_min_u",
    "custom_min_v",
    "custom_max_u",
    "custom_max_v",
)


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


def mesh_loop_selected(loop):
    return bool(loop.face.select or loop.vert.select or loop.edge.select)


def island_has_uv_selection(island, uv_layer):
    for face in island:
        for loop in face.loops:
            if uv_loop_selected(loop, uv_layer):
                return True
    return False


def island_has_mesh_selection(island):
    for face in island:
        for loop in face.loops:
            if mesh_loop_selected(loop):
                return True
    return False


def selected_island_loops(bm, respect_selection, use_mesh_selection):
    uv_layer = active_uv_layer(bm)
    all_island_loops = []
    uv_selected_loops = []
    mesh_selected_loops = []
    combined_selected_loops = []

    for island in build_islands(bm):
        loops = []
        for face in island:
            loops.extend(face.loops)
        all_island_loops.append(loops)
        has_uv_selection = island_has_uv_selection(island, uv_layer)
        has_mesh_selection = island_has_mesh_selection(island)
        if has_uv_selection:
            uv_selected_loops.append(loops)
        if has_mesh_selection:
            mesh_selected_loops.append(loops)
        if has_uv_selection or (use_mesh_selection and has_mesh_selection):
            combined_selected_loops.append(loops)

    if not respect_selection:
        return uv_layer, all_island_loops
    if use_mesh_selection:
        return uv_layer, combined_selected_loops
    if uv_selected_loops:
        return uv_layer, uv_selected_loops
    return uv_layer, mesh_selected_loops


def groups_by_mesh(objects):
    groups = {}
    for obj in objects:
        if obj.type == "MESH":
            groups.setdefault(obj.data.as_pointer(), []).append(obj)
    return list(groups.values())


def representative_for_group(group):
    return next((obj for obj in group if obj.mode == "EDIT"), group[0])


def collect_target(obj, respect_selection, use_mesh_selection):
    if obj.mode == "EDIT":
        bm = bmesh.from_edit_mesh(obj.data)
        bm.faces.ensure_lookup_table()
        uv_layer, island_loops = selected_island_loops(
            bm,
            respect_selection=respect_selection,
            use_mesh_selection=use_mesh_selection,
        )
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
        uv_layer, island_loops = selected_island_loops(
            bm,
            respect_selection=respect_selection,
            use_mesh_selection=use_mesh_selection,
        )
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


def free_owned_targets(targets):
    for target in targets:
        if target["owned"]:
            target["bm"].free()


def write_target(target):
    if target["owned"]:
        target["bm"].to_mesh(target["mesh"])
        target["mesh"].update()
    else:
        bmesh.update_edit_mesh(target["mesh"], loop_triangles=False)


def combined_island_count(targets):
    return sum(target["island_count"] for target in targets)


def uv_bounds(loops, uv_layer):
    if not loops:
        return None

    min_uv = Vector((float("inf"), float("inf")))
    max_uv = Vector((float("-inf"), float("-inf")))
    for loop in loops:
        uv = loop[uv_layer].uv
        min_uv.x = min(min_uv.x, uv.x)
        min_uv.y = min(min_uv.y, uv.y)
        max_uv.x = max(max_uv.x, uv.x)
        max_uv.y = max(max_uv.y, uv.y)

    return min_uv, max_uv


def total_bounds(targets):
    all_min = Vector((float("inf"), float("inf")))
    all_max = Vector((float("-inf"), float("-inf")))
    has_values = False

    for target in targets:
        uv_layer = target["uv_layer"]
        for loops in target["island_loops"]:
            bounds = uv_bounds(loops, uv_layer)
            if bounds is None:
                continue
            min_uv, max_uv = bounds
            all_min.x = min(all_min.x, min_uv.x)
            all_min.y = min(all_min.y, min_uv.y)
            all_max.x = max(all_max.x, max_uv.x)
            all_max.y = max(all_max.y, max_uv.y)
            has_values = True

    if not has_values:
        return None
    return all_min, all_max


def collect_operation_targets(objects, island_filter, use_mesh_selection):
    targets = []
    warnings = []
    for group in groups_by_mesh(objects):
        representative = representative_for_group(group)
        respect_selection = island_filter == "SELECTED" or (
            island_filter == "AUTO" and representative.mode == "EDIT"
        )

        try:
            target = collect_target(
                representative,
                respect_selection=respect_selection,
                use_mesh_selection=use_mesh_selection,
            )
        except RuntimeError as exc:
            warnings.append((representative, exc))
            continue

        if target["island_loops"]:
            targets.append(target)
            continue

        if target["owned"]:
            target["bm"].free()

        if island_filter != "AUTO" or not respect_selection:
            continue

        try:
            target = collect_target(
                representative,
                respect_selection=False,
                use_mesh_selection=use_mesh_selection,
            )
        except RuntimeError as exc:
            warnings.append((representative, exc))
            continue

        if target["island_loops"]:
            targets.append(target)
        elif target["owned"]:
            target["bm"].free()

    return targets, warnings


def sorted_bounds(min_uv, max_uv):
    return (
        Vector((min(min_uv.x, max_uv.x), min(min_uv.y, max_uv.y))),
        Vector((max(min_uv.x, max_uv.x), max(min_uv.y, max_uv.y))),
    )


def target_bounds_from_props(props):
    if props.target == "CUSTOM":
        target_min, target_max = sorted_bounds(
            Vector((props.custom_min_u, props.custom_min_v)),
            Vector((props.custom_max_u, props.custom_max_v)),
        )
    else:
        target_min = Vector((0.0, 0.0))
        target_max = Vector((1.0, 1.0))

    padding = max(0.0, props.padding)
    target_min += Vector((padding, padding))
    target_max -= Vector((padding, padding))

    if target_min.x > target_max.x:
        center_u = (target_min.x + target_max.x) * 0.5
        target_min.x = center_u
        target_max.x = center_u
    if target_min.y > target_max.y:
        center_v = (target_min.y + target_max.y) * 0.5
        target_min.y = center_v
        target_max.y = center_v

    return target_min, target_max


def dimension(bounds, axis):
    min_uv, max_uv = bounds
    return max_uv[axis] - min_uv[axis]


def scale_for_bounds(source_bounds, target_bounds, scale_mode):
    source_width = dimension(source_bounds, 0)
    source_height = dimension(source_bounds, 1)
    target_width = dimension(target_bounds, 0)
    target_height = dimension(target_bounds, 1)
    scale = Vector((1.0, 1.0))
    skipped_axes = set()

    def axis_scale(source_size, target_size, axis_name):
        if abs(source_size) <= EPSILON:
            skipped_axes.add(axis_name)
            return 1.0
        return target_size / source_size

    if scale_mode == "NONE":
        return scale, skipped_axes
    if scale_mode == "UNIFORM_WIDTH":
        uniform = axis_scale(source_width, target_width, "U")
        return Vector((uniform, uniform)), skipped_axes
    if scale_mode == "UNIFORM_HEIGHT":
        uniform = axis_scale(source_height, target_height, "V")
        return Vector((uniform, uniform)), skipped_axes
    if scale_mode in {"UNIFORM_FIT", "UNIFORM_FILL"}:
        candidates = []
        if abs(source_width) > EPSILON:
            candidates.append(target_width / source_width)
        else:
            skipped_axes.add("U")
        if abs(source_height) > EPSILON:
            candidates.append(target_height / source_height)
        else:
            skipped_axes.add("V")
        if not candidates:
            return scale, skipped_axes
        uniform = min(candidates) if scale_mode == "UNIFORM_FIT" else max(candidates)
        return Vector((uniform, uniform)), skipped_axes
    if scale_mode == "STRETCH":
        scale.x = axis_scale(source_width, target_width, "U")
        scale.y = axis_scale(source_height, target_height, "V")
    elif scale_mode == "STRETCH_WIDTH":
        scale.x = axis_scale(source_width, target_width, "U")
    elif scale_mode == "STRETCH_HEIGHT":
        scale.y = axis_scale(source_height, target_height, "V")

    return scale, skipped_axes


def aligned_offset(scaled_bounds, target_bounds, align_u, align_v):
    source_min, source_max = scaled_bounds
    target_min, target_max = target_bounds
    source_center = (source_min + source_max) * 0.5
    target_center = (target_min + target_max) * 0.5
    offset = Vector((0.0, 0.0))

    def axis_offset(axis, mode):
        if mode == "KEEP":
            return 0.0
        if mode == "MIN":
            return target_min[axis] - source_min[axis]
        if mode == "CENTER":
            return target_center[axis] - source_center[axis]
        if mode == "MAX":
            return target_max[axis] - source_max[axis]
        return 0.0

    offset.x = axis_offset(0, align_u)
    offset.y = axis_offset(1, align_v)
    return offset


def transformed_bounds(source_bounds, pivot, scale):
    source_min, source_max = source_bounds
    scaled_min = Vector(
        (
            pivot.x + (source_min.x - pivot.x) * scale.x,
            pivot.y + (source_min.y - pivot.y) * scale.y,
        )
    )
    scaled_max = Vector(
        (
            pivot.x + (source_max.x - pivot.x) * scale.x,
            pivot.y + (source_max.y - pivot.y) * scale.y,
        )
    )
    return sorted_bounds(scaled_min, scaled_max)


def transform_from_bounds(source_bounds, target_bounds, props):
    source_min, source_max = source_bounds
    pivot = (source_min + source_max) * 0.5
    scale, skipped_axes = scale_for_bounds(source_bounds, target_bounds, props.scale_mode)
    scaled_bounds = transformed_bounds(source_bounds, pivot, scale)
    offset = aligned_offset(scaled_bounds, target_bounds, props.align_u, props.align_v)
    return pivot, scale, offset, skipped_axes


def apply_transform(uv_layer, loops, pivot, scale, offset):
    for loop in loops:
        uv = loop[uv_layer].uv
        uv.x = pivot.x + (uv.x - pivot.x) * scale.x + offset.x
        uv.y = pivot.y + (uv.y - pivot.y) * scale.y + offset.y


def transform_targets(targets, target_bounds, props):
    skipped_scale_groups = 0

    if props.transform_scope == "SELECTION":
        bounds = total_bounds(targets)
        if bounds is None:
            return 0, 0
        pivot, scale, offset, skipped_axes = transform_from_bounds(bounds, target_bounds, props)
        if skipped_axes and props.scale_mode != "NONE":
            skipped_scale_groups += 1
        for target in targets:
            uv_layer = target["uv_layer"]
            for loops in target["island_loops"]:
                apply_transform(uv_layer, loops, pivot, scale, offset)
        return 1, skipped_scale_groups

    transformed_groups = 0
    for target in targets:
        uv_layer = target["uv_layer"]
        for loops in target["island_loops"]:
            bounds = uv_bounds(loops, uv_layer)
            if bounds is None:
                continue
            pivot, scale, offset, skipped_axes = transform_from_bounds(bounds, target_bounds, props)
            if skipped_axes and props.scale_mode != "NONE":
                skipped_scale_groups += 1
            apply_transform(uv_layer, loops, pivot, scale, offset)
            transformed_groups += 1

    return transformed_groups, skipped_scale_groups


def copy_settings(source, target):
    for name in SETTING_NAMES:
        setattr(target, name, getattr(source, name))


def scene_settings(context):
    return getattr(context.scene, SETTINGS_ATTR)


def assign_operator_from_settings(operator, settings, save_settings=True):
    operator.use_scene_settings = False
    operator.save_settings = save_settings
    copy_settings(settings, operator)
    return operator


def draw_shared_options(layout, props):
    layout.prop(props, "island_filter", text="Selection")
    layout.prop(props, "transform_scope", text="Treat As")
    layout.prop(props, "target")
    if props.target == "CUSTOM":
        row = layout.row(align=True)
        row.prop(props, "custom_min_u", text="Min U")
        row.prop(props, "custom_max_u", text="Max U")
        row = layout.row(align=True)
        row.prop(props, "custom_min_v", text="Min V")
        row.prop(props, "custom_max_v", text="Max V")
    layout.prop(props, "padding")


def draw_fit_bounds_properties(layout, props):
    draw_shared_options(layout, props)
    layout.separator()
    layout.prop(props, "scale_mode", text="Scale")
    row = layout.row(align=True)
    row.prop(props, "align_u", text="U")
    row.prop(props, "align_v", text="V")


def add_preset_operator(layout, settings, text, scale_mode, align_u="CENTER", align_v="CENTER"):
    operator = layout.operator(UV_OT_faxcorp_fit_uv_bounds.bl_idname, text=text)
    assign_operator_from_settings(operator, settings, save_settings=False)
    operator.scale_mode = scale_mode
    operator.align_u = align_u
    operator.align_v = align_v
    return operator


def draw_fit_bounds_controls(layout, scene, show_title=True):
    settings = getattr(scene, SETTINGS_ATTR)
    if show_title:
        layout.label(text="Fit UV Bounds")

    layout.label(text="Quick Actions")
    row = layout.row(align=True)
    add_preset_operator(row, settings, "Center", "NONE")
    add_preset_operator(row, settings, "Fit Inside", "UNIFORM_FIT")
    row = layout.row(align=True)
    add_preset_operator(row, settings, "Fit Width", "UNIFORM_WIDTH")
    add_preset_operator(row, settings, "Fit Height", "UNIFORM_HEIGHT")
    row = layout.row(align=True)
    add_preset_operator(row, settings, "Stretch Width", "STRETCH_WIDTH")
    add_preset_operator(row, settings, "Stretch Height", "STRETCH_HEIGHT")
    row = layout.row(align=True)
    add_preset_operator(row, settings, "Stretch All", "STRETCH")

    layout.separator()
    layout.label(text="Options")
    draw_shared_options(layout, settings)

    layout.separator()
    layout.label(text="Custom Transform")
    layout.prop(settings, "scale_mode", text="Scale")
    row = layout.row(align=True)
    row.prop(settings, "align_u", text="U")
    row.prop(settings, "align_v", text="V")
    operator = layout.operator(
        UV_OT_faxcorp_fit_uv_bounds.bl_idname,
        text="Apply Custom",
    )
    assign_operator_from_settings(operator, settings)


def draw_dialog_properties(layout, props):
    draw_fit_bounds_properties(layout, props)


class FAXCORP_UVFitBoundsSettings(PropertyGroup):
    island_filter: EnumProperty(
        name="Selection",
        items=ISLAND_FILTER_ITEMS,
        default="AUTO",
    )
    transform_scope: EnumProperty(
        name="Treat As",
        items=SCOPE_ITEMS,
        default="SELECTION",
    )
    target: EnumProperty(
        name="Target",
        items=TARGET_ITEMS,
        default="CANVAS",
    )
    scale_mode: EnumProperty(
        name="Scale",
        items=SCALE_MODE_ITEMS,
        default="UNIFORM_FIT",
    )
    align_u: EnumProperty(
        name="U Align",
        items=ALIGN_U_ITEMS,
        default="CENTER",
    )
    align_v: EnumProperty(
        name="V Align",
        items=ALIGN_V_ITEMS,
        default="CENTER",
    )
    padding: FloatProperty(
        name="Padding",
        description="Inset target bounds by this UV amount",
        default=0.0,
        min=0.0,
        soft_max=0.25,
        precision=4,
    )
    custom_min_u: FloatProperty(name="Min U", default=0.0, precision=4)
    custom_min_v: FloatProperty(name="Min V", default=0.0, precision=4)
    custom_max_u: FloatProperty(name="Max U", default=1.0, precision=4)
    custom_max_v: FloatProperty(name="Max V", default=1.0, precision=4)


class UV_OT_faxcorp_fit_uv_bounds(Operator):
    bl_idname = "uv.faxcorp_fit_uv_bounds"
    bl_label = "Fit UV Bounds"
    bl_description = "Fit, scale, stretch, or align selected UV islands to target bounds"
    bl_options = {"REGISTER", "UNDO"}

    use_scene_settings: BoolProperty(
        default=True,
        options={"HIDDEN"},
    )
    save_settings: BoolProperty(
        default=True,
        options={"HIDDEN"},
    )
    island_filter: EnumProperty(
        name="Selection",
        items=ISLAND_FILTER_ITEMS,
        default="AUTO",
    )
    transform_scope: EnumProperty(
        name="Treat As",
        items=SCOPE_ITEMS,
        default="SELECTION",
    )
    target: EnumProperty(
        name="Target",
        items=TARGET_ITEMS,
        default="CANVAS",
    )
    scale_mode: EnumProperty(
        name="Scale",
        items=SCALE_MODE_ITEMS,
        default="UNIFORM_FIT",
    )
    align_u: EnumProperty(
        name="U Align",
        items=ALIGN_U_ITEMS,
        default="CENTER",
    )
    align_v: EnumProperty(
        name="V Align",
        items=ALIGN_V_ITEMS,
        default="CENTER",
    )
    padding: FloatProperty(
        name="Padding",
        description="Inset target bounds by this UV amount",
        default=0.0,
        min=0.0,
        soft_max=0.25,
        precision=4,
    )
    custom_min_u: FloatProperty(name="Min U", default=0.0, precision=4)
    custom_min_v: FloatProperty(name="Min V", default=0.0, precision=4)
    custom_max_u: FloatProperty(name="Max U", default=1.0, precision=4)
    custom_max_v: FloatProperty(name="Max V", default=1.0, precision=4)

    def invoke(self, context, event):
        copy_settings(scene_settings(context), self)
        self.use_scene_settings = False
        self.save_settings = True
        return context.window_manager.invoke_props_dialog(self, width=420)

    def draw(self, context):
        draw_dialog_properties(self.layout, self)

    def execute(self, context):
        if self.use_scene_settings:
            copy_settings(scene_settings(context), self)
        elif self.save_settings:
            copy_settings(self, scene_settings(context))

        selected = [obj for obj in context.selected_objects if obj.type == "MESH"]
        if not selected:
            self.report({"ERROR"}, "Select at least one mesh object")
            return {"CANCELLED"}

        targets = []
        try:
            use_mesh_selection = bool(getattr(context.tool_settings, "use_uv_select_sync", False))
            targets, warnings = collect_operation_targets(
                selected,
                island_filter=self.island_filter,
                use_mesh_selection=use_mesh_selection,
            )
            for representative, exc in warnings:
                self.report({"WARNING"}, f"Could not process {representative.name}: {exc}")

            island_count = combined_island_count(targets)
            if not targets or island_count == 0:
                self.report({"WARNING"}, "No UV islands found to transform")
                return {"CANCELLED"}

            transformed_groups, skipped_scale_groups = transform_targets(
                targets,
                target_bounds_from_props(self),
                self,
            )
            if transformed_groups == 0:
                self.report({"WARNING"}, "No UV bounds found to transform")
                return {"CANCELLED"}

            for target in targets:
                write_target(target)

            if skipped_scale_groups:
                self.report(
                    {"WARNING"},
                    f"Skipped scaling on {skipped_scale_groups} zero-size UV bound(s); aligned them",
                )

            scope_label = "as one selection" if self.transform_scope == "SELECTION" else "individually"
            self.report({"INFO"}, f"Transformed {island_count} UV island(s) {scope_label}")
            return {"FINISHED"}
        finally:
            free_owned_targets(targets)


class FAXCORP_PT_uv_editor_tools(Panel):
    bl_label = "Fit UV Bounds"
    bl_idname = "FAXCORP_PT_uv_editor_tools"
    bl_space_type = "IMAGE_EDITOR"
    bl_region_type = "UI"
    bl_category = SIDEBAR_CATEGORY

    def draw(self, context):
        draw_fit_bounds_controls(self.layout, context.scene, show_title=False)


def menu_func(self, context):
    previous_context = self.layout.operator_context
    self.layout.operator_context = "INVOKE_DEFAULT"
    self.layout.operator(UV_OT_faxcorp_fit_uv_bounds.bl_idname)
    self.layout.operator_context = previous_context


classes = (
    FAXCORP_UVFitBoundsSettings,
    UV_OT_faxcorp_fit_uv_bounds,
    FAXCORP_PT_uv_editor_tools,
)


def register():
    try:
        register_classes(classes)
        if not hasattr(bpy.types.Scene, SETTINGS_ATTR):
            setattr(
                bpy.types.Scene,
                SETTINGS_ATTR,
                PointerProperty(type=FAXCORP_UVFitBoundsSettings),
            )
        append_menu(bpy.types.IMAGE_MT_uvs, menu_func, menu_state)
    except Exception:
        remove_menu(bpy.types.IMAGE_MT_uvs, menu_func, menu_state)
        if hasattr(bpy.types.Scene, SETTINGS_ATTR):
            delattr(bpy.types.Scene, SETTINGS_ATTR)
        unregister_classes(classes)
        raise


def unregister():
    remove_menu(bpy.types.IMAGE_MT_uvs, menu_func, menu_state)
    if hasattr(bpy.types.Scene, SETTINGS_ATTR):
        delattr(bpy.types.Scene, SETTINGS_ATTR)
    unregister_classes(classes)
