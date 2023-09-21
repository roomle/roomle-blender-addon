import bpy
from typing import Iterable, List, Union

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

def get_socket_origin( material: bpy.types.Material, socket: bpy.types.NodeSocket)  -> Union[bpy.types.Node,None]:
    """find the attached node to a given socket
    the socket is expected to be single input

    Args:
        socket (bpy.types.NodeSocket): given socket

    Returns:
        bpy.types.Node: the connected node
    """
    try:
        links = material.node_tree.links

        assert not socket.is_multi_input
        assert socket.is_linked

        return [e.from_node for e in links if e.to_socket == socket][0]
    except Exception as e:
        print(e)
        return None


def get_enabled_inputs(node: bpy.types.ShaderNode) -> List[bpy.types.NodeSocket]:
    return [i for i in node.inputs if i.enabled]

#TODO: use named tuple for type hinting

def get_mix_shader_sockets(node: bpy.types.ShaderNodeMix) -> tuple[bpy.types.NodeSocket]:

    # Blender 3.6 hides basically multiple socket connectors depending on the type of input

    assert isinstance(node, bpy.types.ShaderNodeMix)
    
    active_inputs = get_enabled_inputs(node)
    
    factor,a,b = (None,)*3
    for input in active_inputs:
        id = input.identifier
        if "Factor" in id :
            factor = input
        if "A" in id :
            a = input
        if "B" in id :
            b = input

    return (factor,a,b)
