import numpy as np
from math import floor
from chunk import Chunk


XBLOCKS = 1024
YBLOCKS = 1024
ZBLOCKS = 128

CHUNKSIZE = 32
CHUNKHEIGHT = 32


class CheckerboardBlockWorld:
    def __init__(self, shape):
        self.shape = shape
        self.ndim = 3
        self.dtype = np.dtype(np.uint8)

    def __getitem__(self, key):
        if not isinstance(key, tuple) or len(key) != 3:
            raise IndexError("CheckerboardBlockWorld expects x, y, z indexes")

        axes = []
        scalar_axes = []

        for axis, index in enumerate(key):
            if isinstance(index, slice):
                start, stop, step = index.indices(self.shape[axis])
                axes.append(np.arange(start, stop, step, dtype=np.uint32))
                scalar_axes.append(False)
                continue

            if isinstance(index, (int, np.integer)):
                normalized = int(index)
                if normalized < 0:
                    normalized += self.shape[axis]
                if normalized < 0 or normalized >= self.shape[axis]:
                    raise IndexError("checkerboard block index out of range")
                axes.append(np.array([normalized], dtype=np.uint32))
                scalar_axes.append(True)
                continue

            raise TypeError(f"Unsupported checkerboard index type: {type(index).__name__}")

        data = (
            axes[0][:, None, None]
            + axes[1][None, :, None]
            + axes[2][None, None, :]
        )
        data = np.bitwise_and(data, 1).astype(np.uint8, copy=False)

        if all(scalar_axes):
            return np.uint8(data[0, 0, 0])

        if any(scalar_axes):
            return data[tuple(0 if scalar else slice(None) for scalar in scalar_axes)]

        return data


# Worst-case stress test world: every solid block is isolated by air.
# This keeps the checkerboard without allocating the full 1024 x 1024 x 128 array.
blockWorldIDS = CheckerboardBlockWorld((XBLOCKS, YBLOCKS, ZBLOCKS))

# casual case scenario world
#blockWorldIDS = np.ones((XBLOCKS, YBLOCKS, ZBLOCKS), dtype=np.uint8)


class ChunkManager():

    def __init__(
            self,
            Showbase,
            debug_chunk_changes=False,
    ):
        self.chunks = {}
        self.Showbase = Showbase
        self.texture = self.Showbase.loader.load_texture("blockTexture.png")
        self.debug_chunk_changes = debug_chunk_changes
        Chunk.configureThreading(
            self.Showbase,
            worker_count=2,
            max_displays_per_frame=1,
            max_display_seconds_per_frame=0.003,
            max_faces_per_display_geom=4096,
            use_process_workers=True,
        )


        self.RENDER_RADIUS = 16
        self.RENDER_HEIGHT = 5

        self.xLimitChunk = int(XBLOCKS / CHUNKSIZE)
        self.yLimitChunk = int(YBLOCKS / CHUNKSIZE)
        self.zLimitChunk = int(ZBLOCKS / CHUNKHEIGHT)

        self.makeWorld(self.Showbase)
        self.cameraChunkPosition = self.getCameraChunkPosition()
        self.Showbase.taskMgr.add(self.update, "chunk-manager-update")

    def getCameraChunkPosition(self):
        camera_position = self.Showbase.camera.get_pos(self.Showbase.render)
        return (
            floor(camera_position.x / CHUNKSIZE),
            floor(camera_position.y / CHUNKSIZE),
            floor(camera_position.z / CHUNKHEIGHT),
        )

    def update(self, task):
        # check current camera position, converted to chunk coordinate
        cameraChunkPosition = self.getCameraChunkPosition()
        if cameraChunkPosition != self.cameraChunkPosition:
            previousCameraChunkPosition = self.cameraChunkPosition
            self.cameraChunkPosition = cameraChunkPosition
            self.cameraChunkPositionChanged(previousCameraChunkPosition, cameraChunkPosition)

        return task.cont

    def cameraChunkPositionChanged(self, previousCameraChunkPosition, cameraChunkPosition):
        if self.debug_chunk_changes:
            print(f"Camera chunk changed from {previousCameraChunkPosition} to {cameraChunkPosition}")

    def makeWorld(self,Showbase):
        for x in range(int(XBLOCKS/CHUNKSIZE)):
            for y in range(int(YBLOCKS/CHUNKSIZE)):
                for z in range(int(ZBLOCKS/CHUNKHEIGHT)):
                    self.chunks[(x, y, z)] = Chunk((x, y, z))


    def unloadChunkCoordinate(self,x,y,z):
        self.emptyChunkSet.discard((x, y, z))
        chunk = self.chunks.get((x, y, z))
        if chunk:
            chunk.stopDisplaying()


    def loadChunkCoordinate(self,x,y,z, threaded=True):
        coord = (x, y, z)

        chunk = self.chunks.get(coord)
        if chunk:

            if threaded:
                return chunk.updateDataAndDisplayThreaded(blockWorldIDS, self.Showbase, self.texture)

            chunk.updateData(blockWorldIDS)
            chunk.display(self.Showbase, self.texture)
            return True

        return False