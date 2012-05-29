import os, re, shutil, subprocess, sys, urllib.parse
from configparser import ConfigParser

import bpy

def encode_floats(floats):
    return " ".join(["%3.3f" % n for n in floats])

class TextureProcessor:
    def __init__(self):
        self.__objects = set()
        self.__materials = set()
        self.__nodes = set()
        self.__textures = set()
        self.__files = set()

    def process_object(self, obj):
        if obj in self.__objects: return
        self.__objects.add(obj)

        for material_slot in obj.material_slots:
            self.process_material(material_slot.material)

    def process_material(self, material):
        if material in self.__materials: return
        self.__materials.add(material)

        if material.use_nodes:
            for link in material.node_tree.links:
                self.process_node(link.from_node)
                self.process_node(link.to_node)

        for texture_slot in material.texture_slots:
            if texture_slot is not None: self.process_texture(texture_slot.texture)

    def process_node(self, node):
        if node in self.__nodes: return
        self.__nodes.add(node)

        if isinstance(node, bpy.types.ShaderNodeTexture):
            self.process_texture(node.texture)
        elif isinstance(node, bpy.types.ShaderNodeMaterial):
            self.process_material(node.material)

    def process_texture(self, texture):
        if texture in self.__textures: return
        self.__textures.add(texture)

        if isinstance(texture, bpy.types.ImageTexture):
            self.__files.add(texture.image.filepath)

    @property
    def files(self):
        return self.__files

config = ConfigParser()
# Don't convert option names to lower case:
config.optionxform = str

scene = bpy.data.scenes[0]
print("Using scene '%s'..." % scene.name)
config["scene"] = {}
config["scene"]["url"] = scene["url"]
config["scene"]["prefix"] = scene["prefix"]

things = []
texture_processor = TextureProcessor()
eggs = set()
for obj in scene.objects:
    texture_processor.process_object(obj)
    if obj.dupli_group is not None:
        for referenced_obj in obj.dupli_group.objects:
            texture_processor.process_object(referenced_obj)

    if "egg" in obj:
        print()
        print("Found '%s' with egg file '%s'." % (obj.name, obj["egg"]))
        print("  location:", obj.location)
        print("  rotation:", obj.matrix_world.to_quaternion())
        print("  scale:", obj.scale)

        internal_name = "t-" + urllib.parse.quote_plus(obj.name)
        things.append(internal_name)
        eggs.add(obj["egg"])

        config[internal_name] = {}
        section = config[internal_name]
        section["egg"] = obj["egg"]
        section["location"] = encode_floats(obj.location)
        section["rotation"] = encode_floats(obj.matrix_world.to_quaternion())
        section["scale"] = encode_floats(obj.scale)

config["scene"]["things"] = " ".join(things)

textures = texture_processor.files
textures = [re.sub(r"//", "", texture) for texture in textures]
textures.sort()
config["textures"] = {}
for i, texture in enumerate(textures):
    config["textures"]["texture.%d" % (i + 1)] = texture

output_dir = sys.argv[-1]
config["compression"] = {}

print()
for filename in eggs | set(textures):
    dest_dir = os.path.join(output_dir, os.path.dirname(filename))
    if not os.path.exists(dest_dir): os.makedirs(dest_dir)
    shutil.copy2(filename, dest_dir)

    if re.search(r"\.(egg|bam)$", filename):
        sys.stdout.write("Compressing %s with xz...  " % os.path.basename(filename))
        sys.stdout.flush()
        subprocess.call(["xz", "-9", dest_dir + filename])
        config["compression"][filename] = "xz"
        print("done.")

with open(output_dir + os.path.sep + "scene.cfg", "w") as handle:
    config.write(handle)
