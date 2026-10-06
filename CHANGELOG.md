# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added
- "Output Format" export option: OBJ (default), Corto, RLCS and RLCS with materials. For the RLCS formats the file is saved into the catalog folder `content/<catalog id>/` and the meshes are written next to it as `meshes/<mesh id>/crt_50.crt`, the materials as `materials/<material id>/data.json` with their textures, like the Rubens Local Content Server serves them. The catalog id is the name of that folder
- Warning for mesh ids ending with a Blender number suffix like `.001`
- "File Name as Prefix" export option: on (default) keeps the mesh ids `<file name>_<object>`, off uses the object names only
### Changed
- The "Use Corto" checkbox is replaced by the Corto output format; scripts calling the export with `use_corto=True` still get Corto files
- "Export Materials" is shown for the OBJ and Corto formats only, the RLCS formats choose the materials by the format
- Output Format is the first export option; the Catalog ID field is shown for the OBJ and Corto formats only
- "Force Extern" is the default mesh export method, all meshes are exported as separate files
- corto is searched on the PATH and in common install folders on export, when the location in the add-on preferences is empty or doesn't exist
### Fixed
- A corto location saved as "corto not found!" kept corto disabled after installing it
- Material export failed when objects were in excluded collections
- "Export Materials" exported mesh ids with the `.001` suffixes of its scene copy; the mesh ids are the same with and without it now
- Parts of objects split by material get the material name in their mesh id and their own material in `SetObjSurface`
- "Export Materials" changed the custom normals of objects with one material (wrong shading); only objects using several materials are split now
- The export cleared the selection, so a second export of the selected objects failed
### Known issues
- Splitting objects with several materials in "Export Materials" can change their custom normals
- Corto runs with `-v 12` and its defaults for the rest (`-n 10 -u 12 -N border`). Earlier versions intended `-v 12 -n 9 -u 10 -N delta`, but passed it as a single argument, so only `-v 12` was ever applied. The output is kept unchanged until the settings of the Roomle backend are confirmed.
- Multiple instances of the same Mesh combined with apply rotation or custom scale can create wrong scale/rotations
- Normal export with applied rotations is untested (esp. internal meshes)
- Normal export in combination with no UVs creates invalid AddMesh commands
- Normals are alway smooth shaded. Blender's "Shade Flat" command (flat shading in viewport) has no effect.

## [3.1.0] - 2026-10-05
### Added
- "Scale" export option, which was fixed to 1000 before. The default stays 1000; set it to 1 for scenes modelled in millimeters
- Export errors and warnings (e.g. missing or failing corto) are reported in the UI and printed to the console
### Changed
- The "Use Corto" tooltip explains that a corto executable is needed and where to set it
### Fixed
- Bounding box of external meshes of scaled objects was scaled twice
- Export errors were swallowed: the operator reported success, but no script was written
- Empty export wrote a script with only the header comment instead of reporting an error
- Material export failed without a window context (e.g. when run by Blender MCP from a timer)
- Failed material export left the copied export scene behind
- Unlinked Metallic socket was exported as 1.0 instead of its value
- Swapped tooltips of the "Force Extern" and "Force Intern" mesh export methods

## [3.0.0] - 2026-04-21
### BREAKING CHANGE
- Made compabible with Blender 5.1.0

## [2.1.0] - 2020-04-01
### Changed
- Normals are exported by default now
- External meshes are exported as Wavefront OBJ now
### Fixed
- Correct export of custom normals when using external meshes
- External meshes in PLY format now contain only its object's geometry, not others as well
- Meshes with n-gons as internal meshes

## [2.0.0] - 2019-06-05
### Fixed
- Ported "Optimize Roomle static" operator to Blender 2.80 (wasn't registered at all before).

## [2.0.0] - beta
### Changed
- Update to Blender 2.80
- In some cases less vertices are exported (when loop index differs, but UVs are actually identical)

## [1.0.1] - 2019-03-23
### Fixed
- Temporary meshes that are generated during script export are now properly removed.
- Loose vertices (not assigned to a face) are not exported anymore

## [1.0.0] - 2019-03-19
### Added
- Unit test scripts

## [0.4.0-beta] - 2018-11-18
### Added
- Support for per object scale. It gets applied to mesh data
- Support for applying rotations in mesh data
- Added operator for optimizing scene
- Added Roomle Gitlab as tracker URL

## [0.3.0-beta] - 2018-08-30
### Added
- Advanced export options that can be acccessed via checkbox
- Meshes can be forced to be internal (via AddMesh command) or external (via AddExternMesh command and separate file)
### Fixed
- Fixed bounding box calculation for AddExternMesh command
### Changed
- Extern mesh files now have the exported script name as a prefix
- Script size optimization by smart quantization of floats for UVs and normals. Also can be tweaked via advanced settings entries.