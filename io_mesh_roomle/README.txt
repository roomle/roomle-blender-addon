Changelog

# known issues
* Multiple instances of the same Mesh combined with apply rotation or custom scale can create wrong scale/rotations (Assets0/bacon-x#7)
* Normal export with applied rotations is untested (esp. internal meshes)
* Normal export in combination with no UVs creates invalid AddMesh commands (Assets0/bacon-x#6)

# 0.4.0-beta
* Support for per object scale. It gets applied to mesh data
* Support for applying rotations in mesh data
* Added operator for optimizing scene
* Added Roomle Gitlab as tracker URL

# 0.3.0
* Fixed bounding box calculation for AddExternMesh command
* Extern mesh files now have the exported script name as a prefix
* Advanced export options that can be acccessed via checkbox
* Script size optimization by smart quantization of floats for UVs and normals. Also can be tweaked via advanced settings entries.
* Meshes can be forced to be internal (via AddMesh command) or external (via AddExternMesh command and separate file)
