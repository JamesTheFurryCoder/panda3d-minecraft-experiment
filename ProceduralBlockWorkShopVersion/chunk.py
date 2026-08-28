from panda3d.core import (
    GeomVertexFormat, GeomVertexData,
    Geom, GeomTriangles, GeomVertexWriter,
    GeomNode
)
from collections import deque
from concurrent.futures import ProcessPoolExecutor
from direct.task import Task
from queue import Empty, Queue
import atexit
import time

import numpy as np

from ProceduralGeometryWorkshop import *

### testing blockID UV stuff
proceduralControl = ProceduralGeometryWorkshop()
_BLOCK_ID_1_FACE_UVS = (
    (0.0, 0.0),
    (1.0, 0.0),
    (1.0, 1.0),
    (0.0, 1.0),
)
proceduralControl.addBlockOrMesh(
    "occluded",
    top=_BLOCK_ID_1_FACE_UVS,
    bottom=_BLOCK_ID_1_FACE_UVS,
    left=_BLOCK_ID_1_FACE_UVS,
    right=_BLOCK_ID_1_FACE_UVS,
    back=_BLOCK_ID_1_FACE_UVS,
    front=_BLOCK_ID_1_FACE_UVS,
)

_BLOCK_ID_2_FACE_UVS = (
    (0.0, 0.0),
    (1.0, 0.0),
    (1.0, 1.0),
    (0.0, 1.0),
)

_BLOCK_ID_2_FACE_UVS_TOP = (
    (0.0, 0.0),
    (0.5, 0.0),
    (0.5, 0.5),
    (0.0, 0.5),
)

_BLOCK_ID_2_FACE_UVS_BOTTOM = (
    (0.5, 0.5),
    (1.0, 0.5),
    (1.0, 1.0),
    (0.5, 1.0),
)

proceduralControl.addBlockOrMesh(
    "occluded",
    top=_BLOCK_ID_2_FACE_UVS_TOP,
    bottom=_BLOCK_ID_2_FACE_UVS_BOTTOM,
    left=_BLOCK_ID_2_FACE_UVS,
    right=_BLOCK_ID_2_FACE_UVS,
    back=_BLOCK_ID_2_FACE_UVS,
    front=_BLOCK_ID_2_FACE_UVS,
)

### END OF testing blockID UV stuff

_INDEX_DTYPES = {
    Geom.NT_uint8: np.uint8,
    Geom.NT_uint16: np.uint16,
    Geom.NT_uint32: np.uint32,
}


class _BlockRegionView:
    def __init__(self, world_shape, region_origin, region_data):
        self.shape = world_shape
        self.region_origin = region_origin
        self.region_data = region_data

    def __getitem__(self, key):
        x, y, z = key
        return self.region_data[
            x - self.region_origin[0],
            y - self.region_origin[1],
            z - self.region_origin[2],
        ]


def _chunk_geometry_payload(worker_chunk, max_faces_per_part):
    vertex_rows = worker_chunk.vdata.get_num_rows()
    index_rows = worker_chunk.tri.get_num_vertices()
    vertex_count = worker_chunk.vertex_count

    if vertex_count == 0 or vertex_rows == 0 or index_rows == 0:
        return {"vertex_count": 0, "parts": []}

    vertex_data = worker_chunk.vdata.get_array(0).get_handle().get_data()
    index_data = worker_chunk.tri.get_vertices().get_handle().get_data()
    index_type = worker_chunk.tri.get_index_type()

    # Chunk's face builders always write one quad as 4 vertices and 6 indices.
    if vertex_rows % 4 != 0 or index_rows % 6 != 0:
        return {
            "vertex_count": vertex_count,
            "parts": [{
                "vertex_rows": vertex_rows,
                "vertex_data": vertex_data,
                "index_rows": index_rows,
                "index_data": index_data,
                "index_type": index_type,
            }],
        }

    index_dtype = _INDEX_DTYPES.get(index_type)
    if index_dtype is None:
        raise ValueError(f"Unsupported Panda3D index type: {index_type}")

    vertex_stride = len(vertex_data) // vertex_rows
    index_stride = np.dtype(index_dtype).itemsize
    face_count = index_rows // 6
    max_faces_per_part = max(1, int(max_faces_per_part))
    parts = []

    for face_start in range(0, face_count, max_faces_per_part):
        part_face_count = min(max_faces_per_part, face_count - face_start)
        vertex_start = face_start * 4
        vertex_end = vertex_start + part_face_count * 4
        index_start = face_start * 6
        index_count = part_face_count * 6

        part_indices = np.frombuffer(
            index_data,
            dtype=index_dtype,
            count=index_count,
            offset=index_start * index_stride,
        ).copy()
        part_indices -= vertex_start

        parts.append({
            "vertex_rows": vertex_end - vertex_start,
            "vertex_data": vertex_data[vertex_start * vertex_stride:vertex_end * vertex_stride],
            "index_rows": index_count,
            "index_data": part_indices.tobytes(),
            "index_type": index_type,
        })

    return {"vertex_count": vertex_count, "parts": parts}


def _build_chunk_geometry_payload(
        position,
        chunk_size,
        chunk_height,
        world_shape,
        region_origin,
        region_data,
        max_faces_per_part,
):
    block_view = _BlockRegionView(world_shape, region_origin, region_data)
    worker_chunk = Chunk(position)
    worker_chunk.chunkSize = chunk_size
    worker_chunk.chunkSizeHeight = chunk_height
    worker_chunk.updateData(block_view)

    return _chunk_geometry_payload(worker_chunk, max_faces_per_part)


def _warm_process_worker():
    return True

class Chunk():
    _thread_task_chain = "chunk-geometry-thread"
    _threaded_display_queue = Queue()
    _process_update_futures = []
    _pending_display_jobs = deque()
    _process_pool = None
    _use_process_workers = True
    _threading_configured = False
    _display_task_configured = False
    _max_displays_per_frame = 1
    _max_display_seconds_per_frame = 0.003
    _max_faces_per_display_geom = 4096

    def __init__(self, position=(0,0,0)):
        self.position = position
        self.chunkSize = 32
        self.chunkSizeHeight = 32

        self.format = GeomVertexFormat.get_v3t2()
        self.vdata = GeomVertexData("quad_data", self.format, Geom.UH_static)

        self.gnode = GeomNode("quad_gnode")

        # Writers for position and UV data
        self.vertex = GeomVertexWriter(self.vdata, "vertex")
        self.texcoord = GeomVertexWriter(self.vdata, "texcoord")
        # 3. Define triangles using vertex indices (two triangles make a quad)
        self.tri = GeomTriangles(Geom.UH_static)
        self.vertex_count = 0
        self.node_path = None
        self._threaded_update_pending = False
        self._threaded_update_version = 0
        self._threaded_update_error = None

    @classmethod
    def configureThreading(
            cls,
            Showbase,
            worker_count=2,
            max_displays_per_frame=1,
            max_display_seconds_per_frame=0.003,
            max_faces_per_display_geom=4096,
            use_process_workers=True,
    ):
        cls._max_displays_per_frame = max(1, int(max_displays_per_frame))
        cls._max_display_seconds_per_frame = max(0.0005, float(max_display_seconds_per_frame))
        cls._max_faces_per_display_geom = max(1, int(max_faces_per_display_geom))
        cls._use_process_workers = use_process_workers

        if not cls._threading_configured:
            Showbase.taskMgr.setupTaskChain(
                cls._thread_task_chain,
                numThreads=max(1, int(worker_count)),
                tickClock=False,
            )
            cls._threading_configured = True

        if cls._use_process_workers and cls._process_pool is None:
            try:
                cls._process_pool = ProcessPoolExecutor(max_workers=max(1, int(worker_count)))
                cls._process_pool.submit(_warm_process_worker)
                atexit.register(cls._shutdownProcessPool)
            except Exception as exc:
                cls._process_pool = None
                cls._use_process_workers = False
                print(f"Chunk process workers unavailable, falling back to threads: {exc}")

        if not cls._display_task_configured:
            Showbase.taskMgr.add(cls._displayThreadedUpdates, "chunk-display-threaded-updates")
            cls._display_task_configured = True

    @classmethod
    def _shutdownProcessPool(cls):
        if cls._process_pool is not None:
            cls._process_pool.shutdown(wait=False, cancel_futures=True)
            cls._process_pool = None

    def _resetGeometryData(self):
        self.vdata = GeomVertexData("quad_data", self.format, Geom.UH_static)
        self.vertex = GeomVertexWriter(self.vdata, "vertex")
        self.texcoord = GeomVertexWriter(self.vdata, "texcoord")
        self.tri = GeomTriangles(Geom.UH_static)
        self.vertex_count = 0

    def _getProperChunkCoordinate(self):
        return (
            self.position[0] * self.chunkSize,
            self.position[1] * self.chunkSize,
            self.position[2] * self.chunkSizeHeight,
        )

    def _getBlockRegionForWorker(self, blockIDS):
        x_size, y_size, z_size = blockIDS.shape
        chunk_x, chunk_y, chunk_z = self._getProperChunkCoordinate()

        start_x = max(0, chunk_x - 1)
        start_y = max(0, chunk_y - 1)
        start_z = max(0, chunk_z - 1)
        end_x = min(x_size, chunk_x + self.chunkSize + 1)
        end_y = min(y_size, chunk_y + self.chunkSize + 1)
        end_z = min(z_size, chunk_z + self.chunkSizeHeight + 1)

        region_data = np.asarray(
            blockIDS[start_x:end_x, start_y:end_y, start_z:end_z],
            dtype=np.uint8,
        ).copy()

        return blockIDS.shape, (start_x, start_y, start_z), region_data

    def _addFrontFace(self,x,y,z):
        # 2. Add 4 vertices for a flat quad with respective (U, V) coordinates
        # Bottom-left vertex
        self.vertex.add_data3(x, y, z)
        self.texcoord.add_data2(0.0, 0.0)

        # Bottom-right vertex
        self.vertex.add_data3(x + 1.0, y, z)
        self.texcoord.add_data2(1.0, 0.0)

        # Top-right vertex
        self.vertex.add_data3(x + 1.0, y, z + 1.0)
        self.texcoord.add_data2(1.0, 1.0)

        # Top-left vertex
        self.vertex.add_data3(x, y, z + 1.0)
        self.texcoord.add_data2(0.0, 1.0)

        face_start = self.vertex_count

        # First triangle (bottom-left, bottom-right, top-right)
        self.tri.add_vertex(face_start + 0)
        self.tri.add_vertex(face_start + 1)
        self.tri.add_vertex(face_start + 2)
        self.tri.close_primitive()

        # Second triangle (bottom-left, top-right, top-left)
        self.tri.add_vertex(face_start + 0)
        self.tri.add_vertex(face_start + 2)
        self.tri.add_vertex(face_start + 3)
        self.tri.close_primitive()
        self.vertex_count += 4

    def _addBackFace(self,x,y,z):
        # 2. Add 4 vertices for a flat quad with respective (U, V) coordinates
        # Bottom-left vertex
        self.vertex.add_data3(x + 1.0, y + 1.0, z)
        self.texcoord.add_data2(0.0, 0.0)

        # Bottom-right vertex
        self.vertex.add_data3(x, y + 1.0, z)
        self.texcoord.add_data2(1.0, 0.0)

        # Top-right vertex
        self.vertex.add_data3(x, y + 1.0, z + 1.0)
        self.texcoord.add_data2(1.0, 1.0)

        # Top-left vertex
        self.vertex.add_data3(x + 1.0, y + 1.0, z + 1.0)
        self.texcoord.add_data2(0.0, 1.0)

        face_start = self.vertex_count

        # First triangle (bottom-left, bottom-right, top-right)
        self.tri.add_vertex(face_start + 0)
        self.tri.add_vertex(face_start + 1)
        self.tri.add_vertex(face_start + 2)
        self.tri.close_primitive()

        # Second triangle (bottom-left, top-right, top-left)
        self.tri.add_vertex(face_start + 0)
        self.tri.add_vertex(face_start + 2)
        self.tri.add_vertex(face_start + 3)
        self.tri.close_primitive()
        self.vertex_count += 4

    def _addRightFace(self,x,y,z):
        # 2. Add 4 vertices for a flat quad with respective (U, V) coordinates
        # Bottom-left vertex
        self.vertex.add_data3(x + 1.0, y, z)
        self.texcoord.add_data2(0.0, 0.0)

        # Bottom-right vertex
        self.vertex.add_data3(x + 1.0, y + 1.0, z)
        self.texcoord.add_data2(1.0, 0.0)

        # Top-right vertex
        self.vertex.add_data3(x + 1.0, y + 1.0, z + 1.0)
        self.texcoord.add_data2(1.0, 1.0)

        # Top-left vertex
        self.vertex.add_data3(x + 1.0, y, z + 1.0)
        self.texcoord.add_data2(0.0, 1.0)

        face_start = self.vertex_count

        # First triangle (bottom-left, bottom-right, top-right)
        self.tri.add_vertex(face_start + 0)
        self.tri.add_vertex(face_start + 1)
        self.tri.add_vertex(face_start + 2)
        self.tri.close_primitive()

        # Second triangle (bottom-left, top-right, top-left)
        self.tri.add_vertex(face_start + 0)
        self.tri.add_vertex(face_start + 2)
        self.tri.add_vertex(face_start + 3)
        self.tri.close_primitive()
        self.vertex_count += 4

    def _addLeftFace(self,x,y,z):
        # 2. Add 4 vertices for a flat quad with respective (U, V) coordinates
        # Bottom-left vertex
        self.vertex.add_data3(x, y + 1.0, z)
        self.texcoord.add_data2(0.0, 0.0)

        # Bottom-right vertex
        self.vertex.add_data3(x, y, z)
        self.texcoord.add_data2(1.0, 0.0)

        # Top-right vertex
        self.vertex.add_data3(x, y, z + 1.0)
        self.texcoord.add_data2(1.0, 1.0)

        # Top-left vertex
        self.vertex.add_data3(x, y + 1.0, z + 1.0)
        self.texcoord.add_data2(0.0, 1.0)

        face_start = self.vertex_count

        # First triangle (bottom-left, bottom-right, top-right)
        self.tri.add_vertex(face_start + 0)
        self.tri.add_vertex(face_start + 1)
        self.tri.add_vertex(face_start + 2)
        self.tri.close_primitive()

        # Second triangle (bottom-left, top-right, top-left)
        self.tri.add_vertex(face_start + 0)
        self.tri.add_vertex(face_start + 2)
        self.tri.add_vertex(face_start + 3)
        self.tri.close_primitive()
        self.vertex_count += 4

    def _addBottomFace(self,x,y,z):
        # 2. Add 4 vertices for a flat quad with respective (U, V) coordinates
        # Bottom-left vertex
        self.vertex.add_data3(x, y + 1.0, z)
        self.texcoord.add_data2(0.0, 0.0)

        # Bottom-right vertex
        self.vertex.add_data3(x + 1.0, y + 1.0, z)
        self.texcoord.add_data2(1.0, 0.0)

        # Top-right vertex
        self.vertex.add_data3(x + 1.0, y, z)
        self.texcoord.add_data2(1.0, 1.0)

        # Top-left vertex
        self.vertex.add_data3(x, y, z)
        self.texcoord.add_data2(0.0, 1.0)

        face_start = self.vertex_count

        # First triangle (bottom-left, bottom-right, top-right)
        self.tri.add_vertex(face_start + 0)
        self.tri.add_vertex(face_start + 1)
        self.tri.add_vertex(face_start + 2)
        self.tri.close_primitive()

        # Second triangle (bottom-left, top-right, top-left)
        self.tri.add_vertex(face_start + 0)
        self.tri.add_vertex(face_start + 2)
        self.tri.add_vertex(face_start + 3)
        self.tri.close_primitive()
        self.vertex_count += 4

    def _addTopFace(self,x,y,z):
        # 2. Add 4 vertices for a flat quad with respective (U, V) coordinates
        # Bottom-left vertex
        self.vertex.add_data3(x, y, z + 1.0)
        self.texcoord.add_data2(0.0, 0.0)

        # Bottom-right vertex
        self.vertex.add_data3(x + 1.0, y, z + 1.0)
        self.texcoord.add_data2(1.0, 0.0)

        # Top-right vertex
        self.vertex.add_data3(x + 1.0, y + 1.0, z + 1.0)
        self.texcoord.add_data2(1.0, 1.0)

        # Top-left vertex
        self.vertex.add_data3(x, y + 1.0, z + 1.0)
        self.texcoord.add_data2(0.0, 1.0)

        face_start = self.vertex_count

        # First triangle (bottom-left, bottom-right, top-right)
        self.tri.add_vertex(face_start + 0)
        self.tri.add_vertex(face_start + 1)
        self.tri.add_vertex(face_start + 2)
        self.tri.close_primitive()

        # Second triangle (bottom-left, top-right, top-left)
        self.tri.add_vertex(face_start + 0)
        self.tri.add_vertex(face_start + 2)
        self.tri.add_vertex(face_start + 3)
        self.tri.close_primitive()
        self.vertex_count += 4

    def coordinateBlockOutOfBoundsOrAir(self, x, y, z, blockIDS):
        x_size, y_size, z_size = blockIDS.shape

        out_of_bounds = not (
                0 <= x < x_size
                and 0 <= y < y_size
                and 0 <= z < z_size
        )

        if out_of_bounds:
            return True

        return blockIDS[x, y, z] == 0

    def updateData(self, blockIDS):
        if len(blockIDS.shape) != 3:
            raise ValueError("blockIDS must be a 3D array")

        self._resetGeometryData()

        x_size, y_size, z_size = blockIDS.shape
        chunk_x, chunk_y, chunk_z = self._getProperChunkCoordinate()

        start_x = max(0, chunk_x)
        start_y = max(0, chunk_y)
        start_z = max(0, chunk_z)
        end_x = min(x_size, chunk_x + self.chunkSize)
        end_y = min(y_size, chunk_y + self.chunkSize)
        end_z = min(z_size, chunk_z + self.chunkSizeHeight)

        for x in range(start_x, end_x):
            for y in range(start_y, end_y):
                for z in range(start_z, end_z):
                    if blockIDS[x, y, z] == 0:
                        continue
                    """
                    #previous implementation without any block registry class.
                    if self.coordinateBlockOutOfBoundsOrAir(x - 1, y, z, blockIDS):
                        self._addLeftFace(x, y, z)

                    if self.coordinateBlockOutOfBoundsOrAir(x + 1, y, z, blockIDS):
                        self._addRightFace(x, y, z)

                    if self.coordinateBlockOutOfBoundsOrAir(x, y - 1, z, blockIDS):
                        self._addFrontFace(x, y, z)

                    if self.coordinateBlockOutOfBoundsOrAir(x, y + 1, z, blockIDS):
                        self._addBackFace(x, y, z)

                    if self.coordinateBlockOutOfBoundsOrAir(x, y, z + 1, blockIDS):
                        self._addTopFace(x, y, z)

                    if self.coordinateBlockOutOfBoundsOrAir(x, y, z - 1, blockIDS):
                        self._addBottomFace(x, y, z)
                    """
                    proceduralControl.doBlockIdOperation(self, x, y, z,blockIDS)

        #print("test")

    def updateDataAndDisplayThreaded(self, blockIDS, Showbase, texture=None):
        if self._threaded_update_pending:
            return False

        if not Chunk._threading_configured or not Chunk._display_task_configured:
            Chunk.configureThreading(Showbase)

        self._threaded_update_pending = True
        self._threaded_update_error = None
        self._threaded_update_version += 1
        version = self._threaded_update_version
        threaded_blockIDS = blockIDS
        worker_region_ready = False

        try:
            world_shape, region_origin, region_data = self._getBlockRegionForWorker(blockIDS)
            threaded_blockIDS = _BlockRegionView(world_shape, region_origin, region_data)
            worker_region_ready = True
        except Exception as exc:
            self._threaded_update_error = exc

        if worker_region_ready and Chunk._use_process_workers and Chunk._process_pool is not None:
            try:
                future = Chunk._process_pool.submit(
                    _build_chunk_geometry_payload,
                    self.position,
                    self.chunkSize,
                    self.chunkSizeHeight,
                    world_shape,
                    region_origin,
                    region_data,
                    Chunk._max_faces_per_display_geom,
                )
                Chunk._process_update_futures.append((future, self, Showbase, texture, version))
                return True
            except Exception as exc:
                self._threaded_update_error = exc

        Showbase.taskMgr.add(
            self._threadedUpdateDataTask,
            f"chunk-update-{self.position[0]}-{self.position[1]}-{self.position[2]}-{version}",
            extraArgs=[threaded_blockIDS, Showbase, texture, version],
            appendTask=True,
            taskChain=Chunk._thread_task_chain,
        )
        return True

    def _threadedUpdateDataTask(self, blockIDS, Showbase, texture, version, task):
        try:
            worker_chunk = Chunk(self.position)
            worker_chunk.chunkSize = self.chunkSize
            worker_chunk.chunkSizeHeight = self.chunkSizeHeight
            worker_chunk.updateData(blockIDS)
            geometry_data = _chunk_geometry_payload(worker_chunk, Chunk._max_faces_per_display_geom)
            error = None
        except Exception as exc:
            geometry_data = None
            error = exc

        Chunk._threaded_display_queue.put((self, Showbase, texture, version, geometry_data, error))
        return Task.done

    @classmethod
    def _applyThreadedUpdateResult(cls, chunk, Showbase, texture, version, geometry_data, error):
        if version != chunk._threaded_update_version:
            return False

        if error is not None:
            chunk._threaded_update_pending = False
            chunk._threaded_update_error = error
            print(f"Failed to update chunk {chunk.position}: {error}")
            return True

        chunk._threaded_update_error = None

        if isinstance(geometry_data, dict):
            if geometry_data.get("vertex_count", 0) > 0 and geometry_data.get("parts"):
                chunk._beginChunkedDisplay(Showbase, texture, version, geometry_data)
            else:
                chunk._threaded_update_pending = False
                chunk.stopDisplaying()
        else:
            chunk._threaded_update_pending = False
            chunk.vdata, chunk.tri, chunk.vertex_count = geometry_data
            chunk.vertex = None
            chunk.texcoord = None

            if chunk.vertex_count > 0:
                chunk.display(Showbase, texture)
            else:
                chunk.stopDisplaying()

        return True

    @classmethod
    def _consumeProcessUpdateResults(cls, max_results, deadline=None):
        processed = 0
        future_index = 0

        while processed < max_results and future_index < len(cls._process_update_futures):
            if deadline is not None and time.perf_counter() >= deadline:
                break

            future, chunk, Showbase, texture, version = cls._process_update_futures[future_index]
            if not future.done():
                future_index += 1
                continue

            cls._process_update_futures.pop(future_index)
            try:
                geometry_data = future.result()
                error = None
            except Exception as exc:
                geometry_data = None
                error = exc

            if cls._applyThreadedUpdateResult(chunk, Showbase, texture, version, geometry_data, error):
                processed += 1

        return processed

    @classmethod
    def _consumeThreadUpdateResults(cls, max_results, deadline=None):
        processed = 0
        checked_results = 0
        max_results_to_check = max_results * 8

        while processed < max_results and checked_results < max_results_to_check:
            if deadline is not None and time.perf_counter() >= deadline:
                break

            try:
                chunk, Showbase, texture, version, geometry_data, error = cls._threaded_display_queue.get_nowait()
            except Empty:
                break

            checked_results += 1

            if cls._applyThreadedUpdateResult(chunk, Showbase, texture, version, geometry_data, error):
                processed += 1

        return processed

    @classmethod
    def _displayThreadedUpdates(cls, task):
        deadline = time.perf_counter() + cls._max_display_seconds_per_frame
        cls._displayPendingGeometryParts(deadline)

        processed = cls._consumeProcessUpdateResults(cls._max_displays_per_frame, deadline)

        if processed < cls._max_displays_per_frame:
            cls._consumeThreadUpdateResults(cls._max_displays_per_frame - processed, deadline)

        cls._displayPendingGeometryParts(deadline)

        return Task.cont

    @classmethod
    def _displayPendingGeometryParts(cls, deadline):
        while cls._pending_display_jobs and time.perf_counter() < deadline:
            job = cls._pending_display_jobs.popleft()
            chunk = job["chunk"]

            if job["version"] != chunk._threaded_update_version:
                continue

            try:
                part = job["parts"].popleft()
                chunk._addGeometryPayloadPart(part)
            except Exception as exc:
                chunk._threaded_update_pending = False
                chunk._threaded_update_error = exc
                print(f"Failed to display chunk {chunk.position}: {exc}")
                continue

            if job["parts"]:
                cls._pending_display_jobs.append(job)
            else:
                chunk._threaded_update_pending = False
                chunk._threaded_update_error = None
                chunk.vertex = None
                chunk.texcoord = None

    def _beginChunkedDisplay(self, Showbase, texture, version, geometry_data):
        self.vertex_count = geometry_data["vertex_count"]
        self.vertex = None
        self.texcoord = None
        self.vdata = None
        self.tri = None

        self.gnode.remove_all_geoms()

        if self.node_path is None:
            self.node_path = Showbase.render.attach_new_node(self.gnode)

        if texture is None:
            texture = Showbase.loader.load_texture("blockTexture.png")

        if texture:
            self.node_path.set_texture(texture)

        Chunk._pending_display_jobs.append({
            "chunk": self,
            "version": version,
            "parts": deque(geometry_data["parts"]),
        })

    def _addGeometryPayloadPart(self, geometry_part):
        vdata = GeomVertexData("quad_data", self.format, Geom.UH_static)
        vdata.unclean_set_num_rows(geometry_part["vertex_rows"])
        vdata.modify_array(0).modify_handle().set_data(geometry_part["vertex_data"])

        tri = GeomTriangles(Geom.UH_static)
        tri.set_index_type(geometry_part["index_type"])
        tri.modify_vertices(geometry_part["index_rows"]).modify_handle().set_data(
            geometry_part["index_data"]
        )

        geom = Geom(vdata)
        geom.add_primitive(tri)
        self.gnode.add_geom(geom)

    def display(self, Showbase, texture=None):
        geom = Geom(self.vdata)
        geom.add_primitive(self.tri)

        self.gnode.remove_all_geoms()
        self.gnode.add_geom(geom)

        if self.node_path is None:
            self.node_path = Showbase.render.attach_new_node(self.gnode)

        #node_path.set_color(1, 1, 1, 1)

        if texture is None:
            # Optional: Load and apply a texture to see the UV mapping in action
            texture = Showbase.loader.load_texture("blockTexture.png")

        if texture:
            self.node_path.set_texture(texture)

        return self.node_path

    def stopDisplaying(self):
        self._threaded_update_version += 1
        self._threaded_update_pending = False

        if self.node_path is not None:
            self.node_path.remove_node()
            self.node_path = None
