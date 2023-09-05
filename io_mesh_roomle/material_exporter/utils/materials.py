import bpy


from typing import Iterable, List


def get_all_used_nodes(material:bpy.types.Material) -> Iterable:
        """find only the used nodes in material's node tree.
        staring at the output node and walking all nodes backwards
        """
        def find_incoming_nodes(base_node, links) -> List:
            """recursive sub function"""
            connected_nodes = [
                edge.from_node for edge in links if edge.to_node == base_node]
            for node in connected_nodes:
                connected_nodes += find_incoming_nodes(node, links)
            return connected_nodes

        # TODO: find the active material output node if multiple are given

        # Find the output node of the material as the starting point
        material_output = [node for node in material.node_tree.nodes if isinstance(
            node, bpy.types.ShaderNodeOutputMaterial)]

        # We only expect one output node for an imported glb
        assert len(material_output) == 1

        # list of used nodes in the definition, passed through a `set` to avoid duplicates
        used_nodes = list(set(
            material_output +
            find_incoming_nodes(
                base_node=material_output[0],
                links=material.node_tree.links
            )
        ))
        return used_nodes


def get_principled_bsdf_node(material:bpy.types.Material) -> bpy.types.ShaderNodeBsdfPrincipled:
    """all used texture nodes in material's node tree"""
    princilpled_nodes = [node for node in get_all_used_nodes(material) if isinstance(node, bpy.types.ShaderNodeBsdfPrincipled)]
    assert len(princilpled_nodes) > 0, 'no principled bsdf node found'
    assert len(princilpled_nodes) < 2, 'multiple principled bsdf nodes found'
    return princilpled_nodes[0]


def get_used_texture_nodes(material:bpy.types.Material) -> list[bpy.types.ShaderNodeTexImage]:
    """all used texture nodes in material's node tree"""
    return [node for node in get_all_used_nodes(material) if isinstance(node, bpy.types.ShaderNodeTexImage)]