import re, sys, urllib.parse
from configparser import ConfigParser

import bpy

def encode_floats(floats):
    return " ".join(["%3.3f" % n for n in floats])

config = ConfigParser()
scene = bpy.data.scenes[0]
print("Using scene '%s'..." % scene.name)
config["scene"] = {}
config["scene"]["url"] = scene["url"]
config["scene"]["prefix"] = scene["prefix"]

things = []
for obj in scene.objects:
    if "egg" in obj:
        print()
        print("Found '%s' with egg file '%s'." % (obj.name, obj["egg"]))
        print("  location:", obj.location)
        print("  rotation:", obj.matrix_world.to_quaternion())
        print("  scale:", obj.scale)

        internal_name = "t-" + urllib.parse.quote_plus(obj.name)
        things.append(internal_name)

        config[internal_name] = {}
        section = config[internal_name]
        section["egg"] = obj["egg"]
        section["location"] = encode_floats(obj.location)
        section["rotation"] = encode_floats(obj.matrix_world.to_quaternion())
        section["scale"] = encode_floats(obj.scale)

config["scene"]["things"] = " ".join(things)

filename = sys.argv[-1]
filename = re.sub(r"\.[^.]+$", "", filename)
filename += ".sc"
with open(filename, "w") as handle:
    config.write(handle)
