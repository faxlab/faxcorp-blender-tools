bl_info = {
    "name": "Faxcorp Blender Tools",
    "author": "faxcorp",
    "version": (1, 0, 4),
    "blender": (5, 1, 1),
    "location": "View3D > Sidebar > Faxcorp Tools",
    "description": "A tidy toolbox of Faxcorp Blender utilities",
    "category": "3D View",
}

from . import (
    align_uv_islands,
    axis_mesh_clipper,
    clear_custom_normals,
    layout_objects,
    panels,
    preferences,
    rename_by_collection,
    rename_to_material,
    shortcuts,
    set_pivot,
    strip_dots_numbers,
    toolbox_menu,
)


modules = (
    preferences,
    axis_mesh_clipper,
    rename_to_material,
    align_uv_islands,
    clear_custom_normals,
    layout_objects,
    rename_by_collection,
    strip_dots_numbers,
    set_pivot,
    toolbox_menu,
    panels,
    shortcuts,
)


def register():
    started_modules = []
    try:
        for module in modules:
            started_modules.append(module)
            module.register()
    except Exception:
        for module in reversed(started_modules):
            try:
                module.unregister()
            except Exception as exc:
                print(f"Faxcorp Blender Tools: cleanup failed for {module.__name__}: {exc}")
        raise


def unregister():
    for module in reversed(modules):
        try:
            module.unregister()
        except Exception as exc:
            print(f"Faxcorp Blender Tools: unregister failed for {module.__name__}: {exc}")


if __name__ == "__main__":
    register()
