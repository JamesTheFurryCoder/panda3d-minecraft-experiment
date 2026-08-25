import numpy as np
from collections import deque
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
        self.MAX_CHUNK_LOADS_PER_FRAME = 2
        self.MAX_CHUNK_UNLOADS_PER_FRAME = 16
        self.MAX_THREADED_CHUNK_BUILDS = 8

        self.xLimitChunk = int(XBLOCKS / CHUNKSIZE)
        self.yLimitChunk = int(YBLOCKS / CHUNKSIZE)
        self.zLimitChunk = int(ZBLOCKS / CHUNKHEIGHT)

        self.emptyChunkSet = set()
        self.loadedChunkSet = set()
        self.targetChunkSet = set()
        self.chunkLoadQueue = deque()
        self.chunkUnloadQueue = deque()

        self.makeWorld(self.Showbase)
        self.cameraChunkPosition = self.getCameraChunkPosition()
        self.updateChunkLoadingTarget(self.cameraChunkPosition)
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

        self.processChunkUnloadQueue()
        self.processChunkLoadQueue()

        return task.cont

    def cameraChunkPositionChanged(self, previousCameraChunkPosition, cameraChunkPosition):
        if self.debug_chunk_changes:
            print(f"Camera chunk changed from {previousCameraChunkPosition} to {cameraChunkPosition}")

        self.updateChunkLoadingTarget(cameraChunkPosition)

    def chunkCoordinateInBounds(self, x, y, z):
        return (
            0 <= x < self.xLimitChunk
            and 0 <= y < self.yLimitChunk
            and 0 <= z < self.zLimitChunk
        )

    def getCylinderChunkCoordinates(self, center, radius=None, height=None):
        if radius is None:
            radius = self.RENDER_RADIUS
        if height is None:
            height = self.RENDER_HEIGHT

        radius = max(0, int(radius))
        height = max(0, int(height))

        center_x, center_y, center_z = center
        radius_squared = radius * radius
        coordinates = []

        for dz in range(-height, height + 1):
            z = center_z + dz
            if not 0 <= z < self.zLimitChunk:
                continue

            for dx in range(-radius, radius + 1):
                x = center_x + dx
                if not 0 <= x < self.xLimitChunk:
                    continue

                for dy in range(-radius, radius + 1):
                    if dx * dx + dy * dy > radius_squared:
                        continue

                    y = center_y + dy
                    if not 0 <= y < self.yLimitChunk:
                        continue

                    # Sort nearest chunks first so the visible area fills in around the player.
                    distance = dx * dx + dy * dy + dz * dz
                    coordinates.append((distance, abs(dz), (x, y, z)))

        coordinates.sort()
        return [coordinate for _, _, coordinate in coordinates]

    def updateChunkLoadingTarget(self, cameraChunkPosition):
        target_chunks = self.getCylinderChunkCoordinates(
            cameraChunkPosition,
            self.RENDER_RADIUS,
            self.RENDER_HEIGHT,
        )
        self.targetChunkSet = set(target_chunks)

        self.chunkLoadQueue = deque(
            coordinate
            for coordinate in target_chunks
            if coordinate not in self.loadedChunkSet
        )

        self.chunkUnloadQueue = deque(
            coordinate
            for coordinate in self.loadedChunkSet
            if coordinate not in self.targetChunkSet
        )

        if self.debug_chunk_changes:
            print(
                "Chunk target updated: "
                f"{len(self.targetChunkSet)} target, "
                f"{len(self.chunkLoadQueue)} queued load, "
                f"{len(self.chunkUnloadQueue)} queued unload"
            )

    def processChunkLoadQueue(self):
        loads_started = 0
        pending_threaded_builds = self.countPendingThreadedChunkBuilds()

        while (
                self.chunkLoadQueue
                and loads_started < self.MAX_CHUNK_LOADS_PER_FRAME
                and pending_threaded_builds < self.MAX_THREADED_CHUNK_BUILDS
        ):
            coordinate = self.chunkLoadQueue.popleft()
            if coordinate not in self.targetChunkSet or coordinate in self.loadedChunkSet:
                continue

            if self.loadChunkCoordinate(*coordinate, threaded=True):
                loads_started += 1
                pending_threaded_builds += 1

    def countPendingThreadedChunkBuilds(self):
        pending_builds = 0

        for coordinate in self.loadedChunkSet:
            chunk = self.chunks.get(coordinate)
            if chunk and chunk._threaded_update_pending:
                pending_builds += 1

        return pending_builds

    def processChunkUnloadQueue(self):
        unloads_completed = 0

        while self.chunkUnloadQueue and unloads_completed < self.MAX_CHUNK_UNLOADS_PER_FRAME:
            coordinate = self.chunkUnloadQueue.popleft()
            if coordinate in self.targetChunkSet:
                continue

            self.unloadChunkCoordinate(*coordinate)
            unloads_completed += 1

    def makeWorld(self,Showbase):
        print(int(ZBLOCKS/CHUNKHEIGHT))
        for x in range(int(XBLOCKS/CHUNKSIZE)):
            for y in range(int(YBLOCKS/CHUNKSIZE)):
                for z in range(int(ZBLOCKS/CHUNKHEIGHT)):
                    self.chunks[(x, y, z)] = Chunk((x, y, z))


    def unloadChunkCoordinate(self,x,y,z):
        coord = (x, y, z)
        self.emptyChunkSet.discard(coord)
        self.loadedChunkSet.discard(coord)
        chunk = self.chunks.get(coord)
        if chunk:
            chunk.stopDisplaying()


    def loadChunkCoordinate(self,x,y,z, threaded=True):
        coord = (x, y, z)

        chunk = self.chunks.get(coord)
        if chunk:

            if threaded:
                load_started = chunk.updateDataAndDisplayThreaded(blockWorldIDS, self.Showbase, self.texture)
                if load_started:
                    self.loadedChunkSet.add(coord)
                return load_started

            chunk.updateData(blockWorldIDS)
            chunk.display(self.Showbase, self.texture)
            self.loadedChunkSet.add(coord)
            return True

        return False
