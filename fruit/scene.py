import os

from panda3d.core import LQuaternionf, loadPrcFileData

from . import FruitConfigParser

class Scene(object):
    def create_scene(self, directory):
        loadPrcFileData("", "model-path %s" % directory)
        scene = FruitConfigParser()
        scene.read(directory + os.path.sep + "scene.cfg")
        for thing in scene.get("scene", "things").split(" "):
            egg = scene.get(thing, "egg")
            egg = self.loader.loadModel(egg)
            egg.reparentTo(self.render)

            egg.setPos(*scene.getfloats(thing, "location"))
            egg.setQuat(LQuaternionf(*scene.getfloats(thing, "rotation")))
            egg.setScale(*scene.getfloats(thing, "scale"))
