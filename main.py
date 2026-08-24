from direct.showbase.ShowBase import ShowBase
from noclipCamera import NoclipCamera
from chunkManager import ChunkManager
from sys import exit


class MyGame(ShowBase):
    def __init__(self):
        # Initialize the Panda3D window and engine
        super().__init__()
        self.set_background_color(0.5, 0.10, 0.12, 1)

        self.player = NoclipCamera(self, start_pos=(0, -10, 3))

        self.worldManager = ChunkManager(self)

        #self.worldManager.loadChunkCoordinate(0,0,0)
        #self.worldManager.loadChunkCoordinate(0, 1, 0)
        #self.worldManager.loadChunkCoordinate(1, 1, 0)
        #self.worldManager.loadChunkCoordinate(1, 0, 0)
        #self.testStress()

        self.setFrameRateMeter(True)

        # Accept keyboard events for movement and exiting
        #self.taskMgr.add(self.update, "update")
        self.accept("escape", exit)
        self.accept("b", self.doChunkLoadTest)
        self.accept("v", self.doChunkLoadTestNoThread)
        self.accept("n", self.clumpTest)

    def clumpTest(self):
        node1 = self.worldManager.chunks.get((0,0,0))
        node2 = self.worldManager.chunks.get((0, 1, 0))
        if node1.node_path != None and node2.node_path != None:
            node2.node_path.reparentTo(node1.node_path)
            node1.node_path.clearModelNodes()
            node1.node_path.flatten_strong()

    def update(self, task):
        #print("test")
        return task.cont

    def testStress(self):
        for x in range(16):
            for y in range(16):
                for z in range(4):
                    self.worldManager.loadChunkCoordinate(x,y,z, False)

    def doChunkLoadTest(self):
        self.worldManager.loadChunkCoordinate(0, 0, 0,True)

    def doChunkLoadTestNoThread(self):
        self.worldManager.loadChunkCoordinate(0, 0, 0,False)


if __name__ == "__main__":
    app = MyGame()
    app.run()
