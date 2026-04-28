bl_info = {
    "name": "FaxCorp Blender Tools",
    "author": "faxlab3d",
    "version": (1, 0, 0),
    "blender": (5, 1, 1),
    "location": "View3D > Sidebar > FaxLab Tools",
    "description": "A tidy toolbox of FaxLab Blender utilities",
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
)


modules = (
    preferences,
    axis_mesh_clipper,
    rename_to_material,
    align_uv_islands,
    clear_custom_normals,
    layout_objects,
    rename_by_collection,
    panels,
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
                print(f"FaxCorp Blender Tools: cleanup failed for {module.__name__}: {exc}")
        raise


def unregister():
    for module in reversed(modules):
        try:
            module.unregister()
        except Exception as exc:
            print(f"FaxCorp Blender Tools: unregister failed for {module.__name__}: {exc}")


if __name__ == "__main__":
    register()
