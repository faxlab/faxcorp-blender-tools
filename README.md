# FaxCorp Blender Tools

One tidy Blender add-on containing FaxCorp utility tools.

## Tools

| Tool | Area | What it does |
| --- | --- | --- |
| All FaxCorp Tools | Menu | Opens one menu containing every tool in the suite. |
| Axis Mesh Clipper | Mesh | Opens a menu for clipping selected meshes by local axis. |
| Rename to Material | Naming | Renames selected mesh objects from their material names, with optional split-by-material behavior. |
| Align UV Islands by Longest Edge | UV | Rotates each UV island so its longest UV edge becomes horizontal. |
| Clear Split Normals | Mesh | Clears custom split normals on selected mesh objects. |
| Layout Objects | Object | Places selected objects end-to-end along X, Y, or Z with a configurable gap. |
| Rename by Collection | Naming | Renames selected objects from their first collection name. |

## Install In Blender

1. Open Blender 5.1.1 or newer.
2. Go to `Edit > Preferences > Get Extensions`.
3. Open the menu in the top-right corner.
4. Choose `Install from Disk...`.
5. Select `dist/faxcorp_blender_tools-1.0.1.zip`.
6. Enable `FaxCorp Blender Tools`.

## Usage

- Open the 3D View sidebar and use the `FaxCorp Tools` tab.
- Click `All FaxCorp Tools` to open one menu with every tool.
- Use native menus for common entries where useful, such as object and UV menu commands.
- Set optional shortcuts in the add-on preferences. All shortcuts are blank by default.

## Shortcuts

Every shortcut is optional and disabled by default. In the add-on preferences, set a key and any modifier toggles for:

- All FaxCorp Tools
- Axis Mesh Clipper
- Rename to Material
- Rename by Collection
- Layout Objects
- Clear Split Normals
- Align UV Islands

The key field expects Blender key event names such as `C`, `X`, `F5`, `SPACE`, or `TAB`. Leave the key field blank to remove that shortcut.

## Axis Mesh Clipper Behavior

- `X-`: removes geometry with local X below `0`, keeping the positive-X side.
- `X+`: removes geometry with local X above `0`, keeping the negative-X side.
- `Y-`, `Y+`, `Z-`, and `Z+` follow the same pattern.
- Clipping uses each object's local origin and local axes.

## Packaging

Run this from the repo root:

```powershell
.\tools\package_addon.ps1
```

The script creates:

```text
dist/faxcorp_blender_tools-1.0.1.zip
```

The zip is arranged for Blender's `Install from Disk...` flow.

## Source Notes

This suite collects and reorganizes tools from older standalone scripts and add-ons. The original folders are left untouched.

## License

GPL-3.0-or-later. See `LICENSE`.
