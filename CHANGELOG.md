# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Known issues
- Multiple instances of the same Mesh combined with apply rotation or custom scale can create wrong scale/rotations
- Normal export with applied rotations is untested (esp. internal meshes)
- Normal export in combination with no UVs creates invalid AddMesh commands
- Normals are alway smooth shaded. Blender's "Shade Flat" command (flat shading in viewport) has no effect.

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