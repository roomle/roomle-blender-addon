# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added
- Unit test scripts
### Known issues
- Multiple instances of the same Mesh combined with apply rotation or custom scale can create wrong scale/rotations (Assets0/bacon-x#7)
- Normal export with applied rotations is untested (esp. internal meshes)
- Normal export in combination with no UVs creates invalid AddMesh commands (Assets0/bacon-x#6)

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