# -----------------------------------------------------------------------
# 
#  Copyright 2019 Roomle GmbH. All Rights Reserved.
# 
#  This Software is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND.
# 
#  NOTICE: All information contained herein is, and remains
#  the property of Roomle. The intellectual and technical concepts contained
#  herein are proprietary to Roomle and are protected by copyright law.
#  Dissemination of this information or reproduction of this material
#  is strictly forbidden unless prior written permission is obtained
#  from Roomle.
# -----------------------------------------------------------------------

import bpy
import bmesh
from mathutils import Vector,Matrix

def is_zero(vector):
	return not any(f!=0 for f in vector)

def get_scene_bounding_box():
	return get_bounding_box(bpy.context.scene.objects)

def get_bounding_box( objects ):

	scene_min = Vector( [float('inf')]*3 )
	scene_max = Vector( [float('-inf')]*3 )

	for obj in objects:
		if obj.type !='MESH':
			continue
		for vert in obj.data.vertices:
			v = obj.matrix_world @ vert.co
			for i in range(3):
				scene_min[i] = min(scene_min[i],v[i])
				scene_max[i] = max(scene_max[i],v[i])

	center = (scene_min+scene_max)*0.5
	dimensions = scene_max-scene_min
	return center,dimensions

def frame_object_bounding_box( camera, objects ):

	points = list()

	center,dimensions = get_bounding_box( objects )

	extends = dimensions*0.5

	for i in range(8):
		e = extends.copy()
		if (i & 1) > 0:
			e.x *= -1
		if (i & 1<<1) > 0:
			e.y *= -1
		if (i & 1<<2) > 0:
			e.z *= -1

		#print(e)

		p = center+e
		points += p.to_tuple()

	pos = camera.camera_fit_coords( bpy.context.scene, points )

	camera.location = pos[0]

def frame_object( camera, objects ):

	points = list()

	for obj in objects:
		if obj.type !='MESH':
			continue
		for vert in obj.data.vertices:
			points += (obj.matrix_world @ vert.co).to_tuple()
			
	# print('found {} points'.format(len(points)))
	pos = camera.camera_fit_coords( bpy.context.scene, points )

	camera.location = pos[0]

def remove_loose_vertices( obj ):
	messages = []

	me = obj.data

	# Get a BMesh representation
	bm = bmesh.new()
	bm.from_mesh(me)

	# Find vertices without faces and remove them
	removed_count = 0
	for v in bm.verts:
		l=len(v.link_faces)
		if l<1:
			removed_count += 1
			bm.verts.remove(v)
	if removed_count>0:
		messages.append( 'Object {}: Removed {} loose vertices'.format(obj.name,removed_count) )
		# Show the updates in the viewport
		# and recalculate n-gon tessellation.
		bm.to_mesh(me)
		bm.free()

	return messages
	
def get_root_objects(scene):
	root_objects = []
	for obj in scene.objects:
		if not obj.parent:
			root_objects.append(obj)
	return root_objects

def move_all( delta ):
	objects = get_root_objects(bpy.context.scene)
	for obj in objects:
		obj.location += delta

def reset_transform(obj):

	messages = []

	mat = obj.matrix_basis.copy()

	if mat == Matrix():
		return messages

	me = obj.data

	# Get a BMesh representation
	bm = bmesh.new()
	bm.from_mesh(me)

	for v in bm.verts:
		v.co = mat @ v.co
	
	messages.append( 'Object {}: applied transform {}'.format(obj.name,mat) )

	# Show the updates in the viewport
	# and recalculate n-gon tessellation.
	bm.to_mesh(me)
	bm.free()

	obj.matrix_basis = Matrix() # identity

	for child in obj.children:
		child.matrix_basis = mat @ child.matrix_basis

	return messages

def optimize_scene( center_scene=True, reset_transforms=True ):
	messages = []
	for obj in bpy.context.scene.objects:
		if obj.type!='MESH':
			continue
		messages += remove_loose_vertices(obj)

	if center_scene:
		c,d = get_scene_bounding_box()

		delta = -c
		delta.z += d.z/2

		if not is_zero(delta):
			messages.append( 'Scene is not centered (delta: {})'.format(delta) )
			move_all( delta )

	if reset_transforms:
		for obj in bpy.context.scene.objects:
			if obj.type!='MESH':
				continue
			messages += reset_transform(obj)

	for msg in messages:
		print(msg)

if __name__ == "__main__":

	optimize_scene()