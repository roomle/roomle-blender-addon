import bpy
from dataclasses import dataclass
import logging



logging.basicConfig(
    level= logging.DEBUG
)

root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
root_handler = root_logger.handlers[0]
root_handler.setFormatter(logging.Formatter('%(funcName)s | %(lineno)d > %(message)s'))


log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)



class ShaderNodeSetup():
    def __init__(self, material) -> None:
        if not material.use_nodes:
            log.error('material not using nodes')
        self.material: bpy.types.Material = material
    
    @property
    def used_nodes(self) -> list:

        def find_incoming_nodes(base_node, links) -> list:
            """recursive sub function"""
            connected_nodes = [
                edge.from_node for edge in links if edge.to_node == base_node]
            for node in connected_nodes:
                connected_nodes += find_incoming_nodes(node, links)
            return connected_nodes

        # TODO: find the active material output node if multiple are given

        # Find the output node of the material as the starting point
        material_output = [node for node in self.material.node_tree.nodes if isinstance(
            node, bpy.types.ShaderNodeOutputMaterial)]

        # We only expect one output node for an imported glb
        assert len(material_output) == 1

        # list of used nodes in the definition, passed through a `set` to avoid duplicates
        used_nodes = list(set(
            material_output +
            find_incoming_nodes(
                base_node=material_output[0],
                links=self.material.node_tree.links
            )
        ))
        return used_nodes

    
    def find_nodes(self,start_socket, node_type):
        


class PrincipledSetup(ShaderNodeSetup):
    def __init__(self, node_tree) -> None:
        super().__init__(node_tree)
        if self.material.use_nodes:
            p = self.principled
            pass

    
    @property
    def principled(self):
        principled = [node for node in self.used_nodes if isinstance(
            node, bpy.types.ShaderNodeBsdfPrincipled)]
        
        return principled[0]



@dataclass
class PBRAnalyzer():
    material: bpy.types.Material

    def execute(self):

        log.debug(f'analyzing {self.material.name}')

        if not self.material.use_nodes:
            log.warning('material should use nodes')
            return
        
        PBRAnalyzer.analyze_node_tree(self.material)
    
    @staticmethod
    def analyze_node_tree(tree):
        pass



def find_nodes(node_tree):
    pass
    

    



def MAIN():
    for mat in bpy.data.materials:
        PrincipledSetup(mat)


if __name__ == '__main__':
    MAIN()