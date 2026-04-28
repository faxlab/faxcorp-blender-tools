import bpy


def register_classes(classes):
    registered = []
    try:
        for cls in classes:
            bpy.utils.register_class(cls)
            registered.append(cls)
    except Exception:
        unregister_classes(registered)
        raise


def unregister_classes(classes):
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass


def append_menu(menu_type, callback, state):
    menu_type.append(callback)
    state["appended"] = True


def remove_menu(menu_type, callback, state):
    if not state.get("appended", False):
        return
    try:
        menu_type.remove(callback)
    except Exception:
        pass
    state["appended"] = False


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


def restore_selection_and_mode(context, active_object, selected_objects, restore_mode):
    restore_selection(context, active_object, selected_objects)
    if restore_mode != "OBJECT":
        try:
            bpy.ops.object.mode_set(mode=restore_mode)
        except RuntimeError:
            pass
