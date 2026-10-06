# Roomle Blender Addon

Addon, that allows you to export your scene into the Roomle Configurator Script format, accompanied by [external mesh files](#external-meshes).

## Download

Currently the addon is only provided as an installable zip file by Roomle directly for partners, clients and customers.

You can download a ready-to-install package from the [dist](dist/index.md) folder.

Advanced users can check out [Build](#build) to build it themselves.

- TODO: Apply `Rotation and Scale` on all elements (hierarchy of emties and objects)

## Install

- Open Blender 3.5 (or later)
- Navigate the main menu to "Edit" > "Preferences"
- On the left side, click the "Add-ons" tab
- Click the "Install…" button at the top right
![Preferences Window - Install](doc/images/01_prefs-install.png)
- Navigate to the downloaded roomle_blender_addon.zip file and install it
- Now the addon is installed and needs to be activated. It is called "Import-Export: Roomle Configurator Script" (Blender usually pre-filters the addon list after installing, so it's at right the top)
- Make sure the addon is activated by checking the checkbox left of its name.
- If you click "Save User Settings" on the lower left, you make sure the addon is activated the next time you start Blender.
![Preferences Window - Addon installed](doc/images/03_prefs-enable.png)

## How to export Roomle script

The export now can be found in the main menu at "File" > "Export" > "Roomle Script (txt)". For quicker access, it can also be found in the 
search menu.

![Export](doc/images/04_export.png)

On the lower left side of the file dialog, you can find some parameters for the export.
- [Catalog ID](#Catalog-ID)
- [Scale](#Scale)
- [Only Selected Objects](#Only-Selected-Objects)
- [Export Normals](#Export-Normals)
- [Apply Rotations](#Apply-Rotations)
- [Use Corto](#Use-Corto)
- [Folder layout](#Folder-layout)
- [Advanced settings](#Advanced-settings)

![Export options](doc/images/05_export-options.png)

### Catalog ID

Materials and external meshes are referenced by an identifier in Roomle Script, which consists of a Catalog ID and an mesh/material ID, separated by a colon (`:`). The catalog ID is provided by Roomle to you. If you happen to know it and provide it in this input field, all references will already have the correct catalog ID in the output script.

### Scale

Roomle Script uses millimeters. The scale multiplies all Blender coordinates on export: the script commands, the bounding boxes and the external mesh files. By default it is 1000, so a scene modelled in meters is exported in millimeters. If your scene is already modelled in millimeters, set it to 1 instead of downscaling the scene before the export.

### Only Selected Objects

By default, all objects containing meshes (so no cameras, lights, aramtures, etc.) in the scene are exported. If this option is enabled, only the currently selected objects will be exported.

### Export Normals

By default the mesh normals are not export, but (smooth) normals are calculated at run-time. To gain finer control of the normals, check this option.

Note: Shading something flat (via `Shade Flat` operator) in the Blender viewport has no effect yet on the output script. Please break edge connections whenever you want a hard shaded edge. The easiest way to do this is the [Edge Split](https://docs.blender.org/manual/en/latest/modeling/modifiers/generate/edge_split.html)  modifier.

### Apply Rotations

When this option is checked, rotations on objects will be applied into the geometry. This is the preferred way, since this calculation would otherwise be done at run-time (slower).

Only un-check this option if you plan to rotate the meshes in your script later on anyways.

### Use Corto

External meshes are compressed into Corto (`.crt`) files, which replace the OBJ files. This needs the `corto` executable, which is not part of the add-on: build it from [Roomle's corto repository](https://github.com/roomle/corto) and set its location in "Edit" > "Preferences" > "Add-ons" > "Roomle Configurator Script". If no location is set or the file doesn't exist, corto is searched on the PATH and in `~/.local/bin`, `/opt/homebrew/bin` and `/usr/local/bin`. Without corto, OBJ files are exported and a warning is shown.

### Folder layout

- **Upload** (default): meshes are exported as `<file name>/<file name>_<object>.crt` (or `.obj`) and materials as a CSV, ready to zip and upload to Rubens Admin.
- **RLCS catalog**: meshes are exported as `<file name>/meshes/<mesh id>/crt_50.crt` and materials (with "Export Materials") as `<file name>/materials/<material id>/data.json` with their textures. Copy the `meshes` and `materials` folders into a catalog folder of your content (`content/<catalog id>/`), so the Rubens Local Content Server loads them. Set the Catalog ID to the name of that catalog folder. The Rubens Local Content Server only loads corto files, so this layout needs [corto](#Use-Corto).

  Material textures are written as they are (PNG or JPEG), named by their mapping: `RGB`, `RGBA` (base color with transparency), `XYZ` (normal map) and `ORM`. Roomle uses UV coordinates in millimeters, so one texture repetition per UV unit (1 mm) shows the texture like Blender does; the scale of a Mapping node in front of a texture is converted into its size. Location and rotation of a Mapping node are not exported.

### Advanced settings

WARNING! Do not play with these settings if you are not 100% sure how they work.

Checking the *Advanced Settings* will unveil some more options.

#### Mesh export method

By default all meshes are exported as separate files ("Force extern", see [External meshes](#external-meshes) for detailed information).
"Automatic" exports smaller meshes as in-line `AddMesh` commands and bigger meshes as separate files, "Force intern" exports all meshes as `AddMesh` commands.
Warning: intern meshes create huge script files and become very slow to load at run-time.

## Roomle Script Output

### External meshes

In Roomle script there are two ways to add custom geometry.
1. Internal meshes: `AddMesh` command with all mesh data as in-line parameters.
2. External meshes: `AddExternalMesh` command, which loads an external, compressed mesh file.

In general external meshes are the preferred way, since they require a fraction of the space of their AddMesh counter-parts and load much faster and efficiently.

However, they require an additional network request at run-time. So for very simple objects (meshes with a with low triangles count) it makes more sense to include them in the script. The addon will automatically decide whether to make the mesh internal or external.

External meshes are expored in a subfolder which has the same name as the script file (.txt) itself. These are triangulated meshes, by default in Wavefront OBJ format. These files have to be uploaded to Roomle before they can be used.

#### Mesh compression

Upon upload, external mesh files are further compressed to become even smaller. This compression is lossy and can yield in artifacts. Feel free to report abnormities.

## Best practice for preparing the scene

- Try to apply rotation and scale on all objects, since these operations are otherwise calculated at run-time.

- The addon has (limited) support of re-using mesh data. So try to re-use mesh data blocks wherever you can and do not give them individual scale and rotation values. 

### Optimize scene operator

The addon also comes with a handy optimize operator, which does some of the best practice optimizations automatically.

You can find it only in the search menu, labeled as *Optimize Roomle static*. This operator will:
- Remove loose vertices (not attached to any face).
- Center your objects at the scene origin, so that the bounding box is in the middle.
- Reset all transforms and apply the rotation, scale and location into the mesh data.

## Issues

Please report any issues or bugs you experience in the [Roomle Servicedesk](https://servicedesk.roomle.com).

## Build

Advanced developers can build the addon themselves. Note that we cannot provide support for custom builds.

There's a script called `build.command`, that packages the addon into a zip file. This works on macOS and should also work on Linux.
- Double click at `build.command`
- The file `roomle_blender_addon.zip` is created.
