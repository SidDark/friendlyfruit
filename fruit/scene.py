import os

from panda3d.core import GeoMipTerrain, LQuaternionf, loadPrcFileData, Texture, TextureStage

from . import FruitConfigParser

class Scene(object):
    def __path(self, filename):
        return self.__directory + os.path.sep + filename

    def __texture_path(self, texture):
        return self.__path(self.__scene.get("textures", texture))

    def __create_terrain(self):
        terrain = GeoMipTerrain("Terrain")
        terrain.setHeightfield(self.__texture_path(self.__scene.get("scene", "heightmap")))
        terrain.getRoot().reparentTo(self.render)
        terrain.generate()
        terrain.getRoot().setSx(1000.0 / 512)
        terrain.getRoot().setSy(1000.0 / 512)
        terrain.getRoot().setSz(74)
        terrain.getRoot().setPos(-500, -500, 0)

        black = self.loader.loadTexture(self.__texture_path(self.__scene.get("terrain", "black")))
        black.setMinfilter(Texture.FTLinearMipmapNearest)
        ts = TextureStage("stage-first")
        ts.setSort(0)
        ts.setMode(TextureStage.MReplace)
        ts.setSavedResult(True)
        terrain.getRoot().setTexture(ts, black)
        terrain.getRoot().setTexScale(ts, 250, 250)

        white = self.loader.loadTexture(self.__texture_path(self.__scene.get("terrain", "white")))
        white.setMinfilter(Texture.FTLinearMipmapNearest)
        ts = TextureStage("stage-second")
        ts.setSort(1)
        ts.setMode(TextureStage.MReplace)
        terrain.getRoot().setTexture(ts, white)
        terrain.getRoot().setTexScale(ts, 250, 250)

        stencil = self.loader.loadTexture(self.__texture_path(self.__scene.get("scene", "stencil")))
        ts = TextureStage("stage-stencil")
        ts.setSort(2)
        ts.setCombineRgb(TextureStage.CMInterpolate,
                         TextureStage.CSPrevious, TextureStage.COSrcColor,
                         TextureStage.CSLastSavedResult, TextureStage.COSrcColor,
                         TextureStage.CSTexture, TextureStage.COSrcColor)

        terrain.getRoot().setTexture(ts, stencil)

        ts = TextureStage("stage-vertexcolour")
        ts.setSort(3)
        ts.setCombineRgb(TextureStage.CMModulate, TextureStage.CSPrevious, TextureStage.COSrcColor,
                         TextureStage.CSPrimaryColor, TextureStage.COSrcColor)

        terrain.getRoot().setTexture(ts, "final")

    def __create_skybox(self):
        egg = self.loader.loadModel("media/skybox.egg")
        egg.reparentTo(self.render)
        sky = self.loader.loadTexture(self.__texture_path(self.__scene.get("scene", "skybox")))
        egg.setTexture(sky)

    def create_scene(self, directory):
        self.__directory = directory
        loadPrcFileData("", "model-path %s" % directory)
        self.__scene = FruitConfigParser()
        self.__scene.read(self.__path("scene.cfg"))
        for thing in self.__scene.get("scene", "things").split(" "):
            egg = self.__scene.get(thing, "egg")
            egg = self.loader.loadModel(egg)
            egg.reparentTo(self.render)

            egg.setPos(*self.__scene.getfloats(thing, "location"))
            egg.setQuat(LQuaternionf(*self.__scene.getfloats(thing, "rotation")))
            egg.setScale(*self.__scene.getfloats(thing, "scale"))

        if self.__scene.has_option("scene", "stencil"):
            self.__create_terrain()

        if self.__scene.has_option("scene", "skybox"):
            self.__create_skybox()
