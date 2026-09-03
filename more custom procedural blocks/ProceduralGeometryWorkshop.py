class OccludedblockDefinition():
    def __init__(self,top,bottom,left,right,back,front):
        #emptyList for all variables like this [(x,y),(x1,y1),(x2,y2),(x3,y3)]
        self.topUvCoordinates = top
        self.leftUvCoordinates = left
        self.rightUvCoordinates = right
        self.bottomUvCoordinates = bottom
        self.backUvCoordinates = back
        self.frontUvCoordinates = front


class OccludedWedgeBlockDefinition(OccludedblockDefinition):
    def __init__(self, top, bottom, left, right, back, front, direction):
        super().__init__(top, bottom, left, right, back, front)
        self.direction = OcclusionWedgeOperations.normalizeDirection(direction)


class OccludedSlabBlockDefinition(OccludedblockDefinition):
    def __init__(self, top, bottom, left, right, back, front, slabPosition):
        super().__init__(top, bottom, left, right, back, front)
        self.slabPosition = OcclusionSlabOperations.normalizeSlabPosition(slabPosition)


class CustomMeshBlockDefinition():
    def __init__(self, vertexOffsets, textureOffsets=None, triOffsets=None, occludes=False):
        self.vertexOffsets = tuple(
            (float(vertex[0]), float(vertex[1]), float(vertex[2]))
            for vertex in vertexOffsets
        )

        if textureOffsets is None:
            self.textureOffsets = tuple((0.0, 0.0) for _ in self.vertexOffsets)
        else:
            self.textureOffsets = tuple(
                (float(texture[0]), float(texture[1]))
                for texture in textureOffsets
            )

        if triOffsets is None:
            self.triOffsets = tuple(range(len(self.vertexOffsets)))
        else:
            self.triOffsets = tuple(int(index) for index in triOffsets)

        if len(self.vertexOffsets) != len(self.textureOffsets):
            raise ValueError("Custom mesh vertexOffsets and textureOffsets must have the same length")
        if len(self.triOffsets) % 3 != 0:
            raise ValueError("Custom mesh triOffsets must contain complete triangles")
        for index in self.triOffsets:
            if index < 0 or index >= len(self.vertexOffsets):
                raise ValueError("Custom mesh triOffsets contains an out-of-range vertex index")

        self.occludes = bool(occludes)


class CustomMeshOperations():
    def __init__(self):
        pass

    def _addCustomMesh(self, chunkClass, x, y, z, customMeshBlock):
        face_start = chunkClass.vertex_count

        for vertex, texture in zip(customMeshBlock.vertexOffsets, customMeshBlock.textureOffsets):
            chunkClass.vertex.add_data3(x + vertex[0], y + vertex[1], z + vertex[2])
            chunkClass.texcoord.add_data2(texture[0], texture[1])

        for indexPosition, vertexIndex in enumerate(customMeshBlock.triOffsets):
            chunkClass.tri.add_vertex(face_start + vertexIndex)
            if (indexPosition + 1) % 3 == 0:
                chunkClass.tri.close_primitive()

        chunkClass.vertex_count += len(customMeshBlock.vertexOffsets)


class OcclusionOperations():
    def __init__(self):
        pass

    def _addFrontFace(self,chunkClass,x,y,z,Occludedblock):
        # 2. Add 4 vertices for a flat quad with respective (U, V) coordinates
        # Bottom-left vertex
        chunkClass.vertex.add_data3(x, y, z)
        tex = Occludedblock.frontUvCoordinates

        tex1 = tex[0]
        chunkClass.texcoord.add_data2(tex1[0], tex1[1])

        # Bottom-right vertex
        tex2 = tex[1]
        chunkClass.vertex.add_data3(x + 1.0, y, z)
        chunkClass.texcoord.add_data2(tex2[0], tex2[1])

        # Top-right vertex
        tex3 = tex[2]
        chunkClass.vertex.add_data3(x + 1.0, y, z + 1.0)
        chunkClass.texcoord.add_data2(tex3[0], tex3[1])

        # Top-left vertex
        tex4 = tex[3]
        chunkClass.vertex.add_data3(x, y, z + 1.0)
        chunkClass.texcoord.add_data2(tex4[0], tex4[1])

        face_start = chunkClass.vertex_count

        # First triangle (bottom-left, bottom-right, top-right)
        chunkClass.tri.add_vertex(face_start + 0)
        chunkClass.tri.add_vertex(face_start + 1)
        chunkClass.tri.add_vertex(face_start + 2)
        chunkClass.tri.close_primitive()

        # Second triangle (bottom-left, top-right, top-left)
        chunkClass.tri.add_vertex(face_start + 0)
        chunkClass.tri.add_vertex(face_start + 2)
        chunkClass.tri.add_vertex(face_start + 3)
        chunkClass.tri.close_primitive()
        chunkClass.vertex_count += 4

    def _addBackFace(self,chunkClass, x, y, z,Occludedblock):
        # 2. Add 4 vertices for a flat quad with respective (U, V) coordinates
        # Bottom-left vertex
        chunkClass.vertex.add_data3(x + 1.0, y + 1.0, z)
        tex = Occludedblock.backUvCoordinates

        tex1 = tex[0]
        chunkClass.texcoord.add_data2(tex1[0], tex1[1])

        # Bottom-right vertex
        tex2 = tex[1]
        chunkClass.vertex.add_data3(x, y + 1.0, z)
        chunkClass.texcoord.add_data2(tex2[0], tex2[1])

        # Top-right vertex
        tex3 = tex[2]
        chunkClass.vertex.add_data3(x, y + 1.0, z + 1.0)
        chunkClass.texcoord.add_data2(tex3[0], tex3[1])

        # Top-left vertex
        tex4 = tex[3]
        chunkClass.vertex.add_data3(x + 1.0, y + 1.0, z + 1.0)
        chunkClass.texcoord.add_data2(tex4[0], tex4[1])

        face_start = chunkClass.vertex_count

        # First triangle (bottom-left, bottom-right, top-right)
        chunkClass.tri.add_vertex(face_start + 0)
        chunkClass.tri.add_vertex(face_start + 1)
        chunkClass.tri.add_vertex(face_start + 2)
        chunkClass.tri.close_primitive()

        # Second triangle (bottom-left, top-right, top-left)
        chunkClass.tri.add_vertex(face_start + 0)
        chunkClass.tri.add_vertex(face_start + 2)
        chunkClass.tri.add_vertex(face_start + 3)
        chunkClass.tri.close_primitive()
        chunkClass.vertex_count += 4

    def _addRightFace(self,chunkClass, x, y, z,Occludedblock):
        # 2. Add 4 vertices for a flat quad with respective (U, V) coordinates
        # Bottom-left vertex
        chunkClass.vertex.add_data3(x + 1.0, y, z)
        tex = Occludedblock.rightUvCoordinates

        tex1 = tex[0]
        chunkClass.texcoord.add_data2(tex1[0], tex1[1])

        # Bottom-right vertex
        tex2 = tex[1]
        chunkClass.vertex.add_data3(x + 1.0, y + 1.0, z)
        chunkClass.texcoord.add_data2(tex2[0], tex2[1])

        # Top-right vertex
        tex3 = tex[2]
        chunkClass.vertex.add_data3(x + 1.0, y + 1.0, z + 1.0)
        chunkClass.texcoord.add_data2(tex3[0], tex3[1])

        # Top-left vertex
        tex4 = tex[3]
        chunkClass.vertex.add_data3(x + 1.0, y, z + 1.0)
        chunkClass.texcoord.add_data2(tex4[0], tex4[1])

        face_start = chunkClass.vertex_count

        # First triangle (bottom-left, bottom-right, top-right)
        chunkClass.tri.add_vertex(face_start + 0)
        chunkClass.tri.add_vertex(face_start + 1)
        chunkClass.tri.add_vertex(face_start + 2)
        chunkClass.tri.close_primitive()

        # Second triangle (bottom-left, top-right, top-left)
        chunkClass.tri.add_vertex(face_start + 0)
        chunkClass.tri.add_vertex(face_start + 2)
        chunkClass.tri.add_vertex(face_start + 3)
        chunkClass.tri.close_primitive()
        chunkClass.vertex_count += 4

    def _addLeftFace(self, chunkClass, x, y, z, Occludedblock):
        # 2. Add 4 vertices for a flat quad with respective (U, V) coordinates
        # Bottom-left vertex
        chunkClass.vertex.add_data3(x, y + 1.0, z)
        tex = Occludedblock.leftUvCoordinates

        tex1 = tex[0]
        chunkClass.texcoord.add_data2(tex1[0], tex1[1])

        # Bottom-right vertex
        tex2 = tex[1]
        chunkClass.vertex.add_data3(x, y, z)
        chunkClass.texcoord.add_data2(tex2[0], tex2[1])

        # Top-right vertex
        tex3 = tex[2]
        chunkClass.vertex.add_data3(x, y, z + 1.0)
        chunkClass.texcoord.add_data2(tex3[0], tex3[1])

        # Top-left vertex
        tex4 = tex[3]
        chunkClass.vertex.add_data3(x, y + 1.0, z + 1.0)
        chunkClass.texcoord.add_data2(tex4[0], tex4[1])

        face_start = chunkClass.vertex_count

        # First triangle (bottom-left, bottom-right, top-right)
        chunkClass.tri.add_vertex(face_start + 0)
        chunkClass.tri.add_vertex(face_start + 1)
        chunkClass.tri.add_vertex(face_start + 2)
        chunkClass.tri.close_primitive()

        # Second triangle (bottom-left, top-right, top-left)
        chunkClass.tri.add_vertex(face_start + 0)
        chunkClass.tri.add_vertex(face_start + 2)
        chunkClass.tri.add_vertex(face_start + 3)
        chunkClass.tri.close_primitive()
        chunkClass.vertex_count += 4

    def _addBottomFace(self, chunkClass, x, y, z, Occludedblock):
        # 2. Add 4 vertices for a flat quad with respective (U, V) coordinates
        # Bottom-left vertex
        chunkClass.vertex.add_data3(x, y + 1.0, z)
        tex = Occludedblock.bottomUvCoordinates

        tex1 = tex[0]
        chunkClass.texcoord.add_data2(tex1[0], tex1[1])

        # Bottom-right vertex
        tex2 = tex[1]
        chunkClass.vertex.add_data3(x + 1.0, y + 1.0, z)
        chunkClass.texcoord.add_data2(tex2[0], tex2[1])

        # Top-right vertex
        tex3 = tex[2]
        chunkClass.vertex.add_data3(x + 1.0, y, z)
        chunkClass.texcoord.add_data2(tex3[0], tex3[1])

        # Top-left vertex
        tex4 = tex[3]
        chunkClass.vertex.add_data3(x, y, z)
        chunkClass.texcoord.add_data2(tex4[0], tex4[1])

        face_start = chunkClass.vertex_count

        # First triangle (bottom-left, bottom-right, top-right)
        chunkClass.tri.add_vertex(face_start + 0)
        chunkClass.tri.add_vertex(face_start + 1)
        chunkClass.tri.add_vertex(face_start + 2)
        chunkClass.tri.close_primitive()

        # Second triangle (bottom-left, top-right, top-left)
        chunkClass.tri.add_vertex(face_start + 0)
        chunkClass.tri.add_vertex(face_start + 2)
        chunkClass.tri.add_vertex(face_start + 3)
        chunkClass.tri.close_primitive()
        chunkClass.vertex_count += 4

    def _addTopFace(self, chunkClass, x, y, z,Occludedblock):
        # 2. Add 4 vertices for a flat quad with respective (U, V) coordinates
        # Bottom-left vertex
        chunkClass.vertex.add_data3(x, y, z + 1.0)
        tex = Occludedblock.topUvCoordinates

        tex1 = tex[0]
        chunkClass.texcoord.add_data2(tex1[0], tex1[1])

        # Bottom-right vertex
        tex2 = tex[1]
        chunkClass.vertex.add_data3(x + 1.0, y, z + 1.0)
        chunkClass.texcoord.add_data2(tex2[0], tex2[1])

        # Top-right vertex
        tex3 = tex[2]
        chunkClass.vertex.add_data3(x + 1.0, y + 1.0, z + 1.0)
        chunkClass.texcoord.add_data2(tex3[0], tex3[1])

        # Top-left vertex
        tex4 = tex[3]
        chunkClass.vertex.add_data3(x, y + 1.0, z + 1.0)
        chunkClass.texcoord.add_data2(tex4[0], tex4[1])

        face_start = chunkClass.vertex_count

        # First triangle (bottom-left, bottom-right, top-right)
        chunkClass.tri.add_vertex(face_start + 0)
        chunkClass.tri.add_vertex(face_start + 1)
        chunkClass.tri.add_vertex(face_start + 2)
        chunkClass.tri.close_primitive()

        # Second triangle (bottom-left, top-right, top-left)
        chunkClass.tri.add_vertex(face_start + 0)
        chunkClass.tri.add_vertex(face_start + 2)
        chunkClass.tri.add_vertex(face_start + 3)
        chunkClass.tri.close_primitive()
        chunkClass.vertex_count += 4

## A NOTE TO CHATGPT: _addFace should now deal with a new additional argument made for directions such as "west", "north" "east", "south".
class OcclusionWedgeOperations():
    _DIRECTION_ALIASES = {
        "west": "west",
        "left": "west",
        "north": "north",
        "back": "north",
        "east": "east",
        "right": "east",
        "south": "south",
        "front": "south",
    }

    _FACE_UV_NAMES = {
        "top": "topUvCoordinates",
        "bottom": "bottomUvCoordinates",
        "left": "leftUvCoordinates",
        "right": "rightUvCoordinates",
        "back": "backUvCoordinates",
        "front": "frontUvCoordinates",
    }

    _OPPOSITE_FACE_NAMES = {
        "left": "right",
        "right": "left",
        "front": "back",
        "back": "front",
        "top": "bottom",
        "bottom": "top",
    }

    _VERTICAL_FACE_PROJECTION_AXES = {
        "left": (1, 2),
        "right": (1, 2),
        "front": (0, 2),
        "back": (0, 2),
    }

    _BOTTOM_FACE_OFFSETS = (
        (0.0, 1.0, 0.0),
        (1.0, 1.0, 0.0),
        (1.0, 0.0, 0.0),
        (0.0, 0.0, 0.0),
    )

    _FACE_OFFSETS_BY_DIRECTION = {
        "east": {
            "top": (
                (0.0, 0.0, 0.0),
                (1.0, 0.0, 1.0),
                (1.0, 1.0, 1.0),
                (0.0, 1.0, 0.0),
            ),
            "bottom": _BOTTOM_FACE_OFFSETS,
            "right": (
                (1.0, 0.0, 0.0),
                (1.0, 1.0, 0.0),
                (1.0, 1.0, 1.0),
                (1.0, 0.0, 1.0),
            ),
            "front": (
                (0.0, 0.0, 0.0),
                (1.0, 0.0, 0.0),
                (1.0, 0.0, 1.0),
            ),
            "back": (
                (1.0, 1.0, 0.0),
                (0.0, 1.0, 0.0),
                (1.0, 1.0, 1.0),
            ),
        },
        "west": {
            "top": (
                (1.0, 1.0, 0.0),
                (0.0, 1.0, 1.0),
                (0.0, 0.0, 1.0),
                (1.0, 0.0, 0.0),
            ),
            "bottom": _BOTTOM_FACE_OFFSETS,
            "left": (
                (0.0, 1.0, 0.0),
                (0.0, 0.0, 0.0),
                (0.0, 0.0, 1.0),
                (0.0, 1.0, 1.0),
            ),
            "front": (
                (0.0, 0.0, 0.0),
                (1.0, 0.0, 0.0),
                (0.0, 0.0, 1.0),
            ),
            "back": (
                (1.0, 1.0, 0.0),
                (0.0, 1.0, 0.0),
                (0.0, 1.0, 1.0),
            ),
        },
        "north": {
            "top": (
                (0.0, 0.0, 0.0),
                (1.0, 0.0, 0.0),
                (1.0, 1.0, 1.0),
                (0.0, 1.0, 1.0),
            ),
            "bottom": _BOTTOM_FACE_OFFSETS,
            "back": (
                (1.0, 1.0, 0.0),
                (0.0, 1.0, 0.0),
                (0.0, 1.0, 1.0),
                (1.0, 1.0, 1.0),
            ),
            "left": (
                (0.0, 1.0, 0.0),
                (0.0, 0.0, 0.0),
                (0.0, 1.0, 1.0),
            ),
            "right": (
                (1.0, 0.0, 0.0),
                (1.0, 1.0, 0.0),
                (1.0, 1.0, 1.0),
            ),
        },
        "south": {
            "top": (
                (0.0, 1.0, 0.0),
                (0.0, 0.0, 1.0),
                (1.0, 0.0, 1.0),
                (1.0, 1.0, 0.0),
            ),
            "bottom": _BOTTOM_FACE_OFFSETS,
            "front": (
                (0.0, 0.0, 0.0),
                (1.0, 0.0, 0.0),
                (1.0, 0.0, 1.0),
                (0.0, 0.0, 1.0),
            ),
            "left": (
                (0.0, 1.0, 0.0),
                (0.0, 0.0, 0.0),
                (0.0, 0.0, 1.0),
            ),
            "right": (
                (1.0, 0.0, 0.0),
                (1.0, 1.0, 0.0),
                (1.0, 0.0, 1.0),
            ),
        },
    }

    def __init__(self):
        pass

    @classmethod
    def normalizeDirection(cls, direction):
        if direction is None:
            return "north"

        normalized = cls._DIRECTION_ALIASES.get(str(direction).lower())
        if normalized is None:
            valid_directions = ", ".join(("west", "north", "east", "south"))
            raise ValueError(f"Unsupported wedge direction '{direction}'. Expected one of: {valid_directions}")

        return normalized

    @classmethod
    def oppositeFaceName(cls, faceName):
        oppositeFaceName = cls._OPPOSITE_FACE_NAMES.get(faceName)
        if oppositeFaceName is None:
            valid_faces = ", ".join(cls._OPPOSITE_FACE_NAMES.keys())
            raise ValueError(f"Unsupported wedge face '{faceName}'. Expected one of: {valid_faces}")

        return oppositeFaceName

    @classmethod
    def getFaceOffsets(cls, direction, faceName):
        normalized_direction = cls.normalizeDirection(direction)
        return cls._FACE_OFFSETS_BY_DIRECTION[normalized_direction].get(faceName)

    @classmethod
    def _projectFaceOffsets(cls, faceOffsets, axes):
        return {
            (offset[axes[0]], offset[axes[1]])
            for offset in faceOffsets
        }

    @classmethod
    def wedgeFaceOccludes(cls, visibleDirection, visibleFaceName, occludingDirection, occludingFaceName):
        visibleFaceOffsets = cls.getFaceOffsets(visibleDirection, visibleFaceName)
        occludingFaceOffsets = cls.getFaceOffsets(occludingDirection, occludingFaceName)
        if visibleFaceOffsets is None or occludingFaceOffsets is None:
            return False

        if (
                visibleFaceName not in cls._VERTICAL_FACE_PROJECTION_AXES
                or occludingFaceName not in cls._VERTICAL_FACE_PROJECTION_AXES
        ):
            return False

        visibleFaceAxes = cls._VERTICAL_FACE_PROJECTION_AXES[visibleFaceName]
        occludingFaceAxes = cls._VERTICAL_FACE_PROJECTION_AXES[occludingFaceName]
        if visibleFaceAxes != occludingFaceAxes:
            return False

        visibleFaceProjection = cls._projectFaceOffsets(visibleFaceOffsets, visibleFaceAxes)
        occludingFaceProjection = cls._projectFaceOffsets(occludingFaceOffsets, visibleFaceAxes)
        return visibleFaceProjection.issubset(occludingFaceProjection)

    def _addFace(self, chunkClass, vertices, uvCoordinates, direction):
        self.normalizeDirection(direction)

        if len(vertices) == 3:
            vertices = (vertices[0], vertices[1], vertices[2], vertices[2])
            uvCoordinates = (
                uvCoordinates[0],
                uvCoordinates[1],
                uvCoordinates[2],
                uvCoordinates[2],
            )

        if len(vertices) != 4:
            raise ValueError("Occlusion wedge faces must have 3 or 4 vertices")

        for vertex, tex in zip(vertices, uvCoordinates):
            chunkClass.vertex.add_data3(vertex[0], vertex[1], vertex[2])
            chunkClass.texcoord.add_data2(tex[0], tex[1])

        face_start = chunkClass.vertex_count

        chunkClass.tri.add_vertex(face_start + 0)
        chunkClass.tri.add_vertex(face_start + 1)
        chunkClass.tri.add_vertex(face_start + 2)
        chunkClass.tri.close_primitive()

        chunkClass.tri.add_vertex(face_start + 0)
        chunkClass.tri.add_vertex(face_start + 2)
        chunkClass.tri.add_vertex(face_start + 3)
        chunkClass.tri.close_primitive()
        chunkClass.vertex_count += 4

    def _addWedgeFace(self, chunkClass, x, y, z, Occludedblock, faceName, direction):
        normalized_direction = self.normalizeDirection(direction)
        face_offsets = self._FACE_OFFSETS_BY_DIRECTION[normalized_direction].get(faceName)
        if face_offsets is None:
            return

        vertices = tuple(
            (x + offset[0], y + offset[1], z + offset[2])
            for offset in face_offsets
        )
        uvCoordinates = getattr(Occludedblock, self._FACE_UV_NAMES[faceName])
        self._addFace(chunkClass, vertices, uvCoordinates, normalized_direction)

    def _addFrontFace(self, chunkClass, x, y, z, Occludedblock, direction):
        self._addWedgeFace(chunkClass, x, y, z, Occludedblock, "front", direction)

    def _addBackFace(self, chunkClass, x, y, z, Occludedblock, direction):
        self._addWedgeFace(chunkClass, x, y, z, Occludedblock, "back", direction)

    def _addRightFace(self, chunkClass, x, y, z, Occludedblock, direction):
        self._addWedgeFace(chunkClass, x, y, z, Occludedblock, "right", direction)

    def _addLeftFace(self, chunkClass, x, y, z, Occludedblock, direction):
        self._addWedgeFace(chunkClass, x, y, z, Occludedblock, "left", direction)

    def _addBottomFace(self, chunkClass, x, y, z, Occludedblock, direction):
        self._addWedgeFace(chunkClass, x, y, z, Occludedblock, "bottom", direction)

    def _addTopFace(self, chunkClass, x, y, z, Occludedblock, direction):
        self._addWedgeFace(chunkClass, x, y, z, Occludedblock, "top", direction)


class OcclusionSlabOperations():
    _SLAB_POSITION_ALIASES = {
        "bottom": "bottom",
        "lower": "bottom",
        "down": "bottom",
        "top": "top",
        "upper": "top",
        "up": "top",
    }

    def __init__(self):
        pass

    @classmethod
    def normalizeSlabPosition(cls, slabPosition):
        if slabPosition is None:
            return "bottom"

        normalized = cls._SLAB_POSITION_ALIASES.get(str(slabPosition).lower())
        if normalized is None:
            valid_positions = ", ".join(("bottom", "top"))
            raise ValueError(f"Unsupported slab position '{slabPosition}'. Expected one of: {valid_positions}")

        return normalized

    @classmethod
    def slabFaceOccludesWedgeFace(cls, slabPosition, slabFaceName, wedgeFaceName):
        if wedgeFaceName != "bottom":
            return False

        return cls.normalizeSlabPosition(slabPosition) == "top" and slabFaceName == "top"

    def _getSlabZRange(self, z, slabPosition):
        if self.normalizeSlabPosition(slabPosition) == "top":
            return z + 0.5, z + 1.0

        return z, z + 0.5

    def _addFrontFace(self, chunkClass, x, y, z, Occludedblock, slabPosition):
        slabBottomZ, slabTopZ = self._getSlabZRange(z, slabPosition)
        # 2. Add 4 vertices for a flat quad with respective (U, V) coordinates
        # Bottom-left vertex
        chunkClass.vertex.add_data3(x, y, slabBottomZ)
        tex = Occludedblock.frontUvCoordinates

        tex1 = tex[0]
        chunkClass.texcoord.add_data2(tex1[0], tex1[1])

        # Bottom-right vertex
        tex2 = tex[1]
        chunkClass.vertex.add_data3(x + 1.0, y, slabBottomZ)
        chunkClass.texcoord.add_data2(tex2[0], tex2[1])

        # Top-right vertex
        tex3 = tex[2]
        chunkClass.vertex.add_data3(x + 1.0, y, slabTopZ)
        chunkClass.texcoord.add_data2(tex3[0], tex3[1])

        # Top-left vertex
        tex4 = tex[3]
        chunkClass.vertex.add_data3(x, y, slabTopZ)
        chunkClass.texcoord.add_data2(tex4[0], tex4[1])

        face_start = chunkClass.vertex_count

        # First triangle (bottom-left, bottom-right, top-right)
        chunkClass.tri.add_vertex(face_start + 0)
        chunkClass.tri.add_vertex(face_start + 1)
        chunkClass.tri.add_vertex(face_start + 2)
        chunkClass.tri.close_primitive()

        # Second triangle (bottom-left, top-right, top-left)
        chunkClass.tri.add_vertex(face_start + 0)
        chunkClass.tri.add_vertex(face_start + 2)
        chunkClass.tri.add_vertex(face_start + 3)
        chunkClass.tri.close_primitive()
        chunkClass.vertex_count += 4

    def _addBackFace(self, chunkClass, x, y, z, Occludedblock, slabPosition):
        slabBottomZ, slabTopZ = self._getSlabZRange(z, slabPosition)
        # 2. Add 4 vertices for a flat quad with respective (U, V) coordinates
        # Bottom-left vertex
        chunkClass.vertex.add_data3(x + 1.0, y + 1.0, slabBottomZ)
        tex = Occludedblock.backUvCoordinates

        tex1 = tex[0]
        chunkClass.texcoord.add_data2(tex1[0], tex1[1])

        # Bottom-right vertex
        tex2 = tex[1]
        chunkClass.vertex.add_data3(x, y + 1.0, slabBottomZ)
        chunkClass.texcoord.add_data2(tex2[0], tex2[1])

        # Top-right vertex
        tex3 = tex[2]
        chunkClass.vertex.add_data3(x, y + 1.0, slabTopZ)
        chunkClass.texcoord.add_data2(tex3[0], tex3[1])

        # Top-left vertex
        tex4 = tex[3]
        chunkClass.vertex.add_data3(x + 1.0, y + 1.0, slabTopZ)
        chunkClass.texcoord.add_data2(tex4[0], tex4[1])

        face_start = chunkClass.vertex_count

        # First triangle (bottom-left, bottom-right, top-right)
        chunkClass.tri.add_vertex(face_start + 0)
        chunkClass.tri.add_vertex(face_start + 1)
        chunkClass.tri.add_vertex(face_start + 2)
        chunkClass.tri.close_primitive()

        # Second triangle (bottom-left, top-right, top-left)
        chunkClass.tri.add_vertex(face_start + 0)
        chunkClass.tri.add_vertex(face_start + 2)
        chunkClass.tri.add_vertex(face_start + 3)
        chunkClass.tri.close_primitive()
        chunkClass.vertex_count += 4

    def _addRightFace(self, chunkClass, x, y, z, Occludedblock, slabPosition):
        slabBottomZ, slabTopZ = self._getSlabZRange(z, slabPosition)
        # 2. Add 4 vertices for a flat quad with respective (U, V) coordinates
        # Bottom-left vertex
        chunkClass.vertex.add_data3(x + 1.0, y, slabBottomZ)
        tex = Occludedblock.rightUvCoordinates

        tex1 = tex[0]
        chunkClass.texcoord.add_data2(tex1[0], tex1[1])

        # Bottom-right vertex
        tex2 = tex[1]
        chunkClass.vertex.add_data3(x + 1.0, y + 1.0, slabBottomZ)
        chunkClass.texcoord.add_data2(tex2[0], tex2[1])

        # Top-right vertex
        tex3 = tex[2]
        chunkClass.vertex.add_data3(x + 1.0, y + 1.0, slabTopZ)
        chunkClass.texcoord.add_data2(tex3[0], tex3[1])

        # Top-left vertex
        tex4 = tex[3]
        chunkClass.vertex.add_data3(x + 1.0, y, slabTopZ)
        chunkClass.texcoord.add_data2(tex4[0], tex4[1])

        face_start = chunkClass.vertex_count

        # First triangle (bottom-left, bottom-right, top-right)
        chunkClass.tri.add_vertex(face_start + 0)
        chunkClass.tri.add_vertex(face_start + 1)
        chunkClass.tri.add_vertex(face_start + 2)
        chunkClass.tri.close_primitive()

        # Second triangle (bottom-left, top-right, top-left)
        chunkClass.tri.add_vertex(face_start + 0)
        chunkClass.tri.add_vertex(face_start + 2)
        chunkClass.tri.add_vertex(face_start + 3)
        chunkClass.tri.close_primitive()
        chunkClass.vertex_count += 4

    def _addLeftFace(self, chunkClass, x, y, z, Occludedblock, slabPosition):
        slabBottomZ, slabTopZ = self._getSlabZRange(z, slabPosition)
        # 2. Add 4 vertices for a flat quad with respective (U, V) coordinates
        # Bottom-left vertex
        chunkClass.vertex.add_data3(x, y + 1.0, slabBottomZ)
        tex = Occludedblock.leftUvCoordinates

        tex1 = tex[0]
        chunkClass.texcoord.add_data2(tex1[0], tex1[1])

        # Bottom-right vertex
        tex2 = tex[1]
        chunkClass.vertex.add_data3(x, y, slabBottomZ)
        chunkClass.texcoord.add_data2(tex2[0], tex2[1])

        # Top-right vertex
        tex3 = tex[2]
        chunkClass.vertex.add_data3(x, y, slabTopZ)
        chunkClass.texcoord.add_data2(tex3[0], tex3[1])

        # Top-left vertex
        tex4 = tex[3]
        chunkClass.vertex.add_data3(x, y + 1.0, slabTopZ)
        chunkClass.texcoord.add_data2(tex4[0], tex4[1])

        face_start = chunkClass.vertex_count

        # First triangle (bottom-left, bottom-right, top-right)
        chunkClass.tri.add_vertex(face_start + 0)
        chunkClass.tri.add_vertex(face_start + 1)
        chunkClass.tri.add_vertex(face_start + 2)
        chunkClass.tri.close_primitive()

        # Second triangle (bottom-left, top-right, top-left)
        chunkClass.tri.add_vertex(face_start + 0)
        chunkClass.tri.add_vertex(face_start + 2)
        chunkClass.tri.add_vertex(face_start + 3)
        chunkClass.tri.close_primitive()
        chunkClass.vertex_count += 4

    def _addBottomFace(self, chunkClass, x, y, z, Occludedblock, slabPosition):
        slabBottomZ = self._getSlabZRange(z, slabPosition)[0]
        # 2. Add 4 vertices for a flat quad with respective (U, V) coordinates
        # Bottom-left vertex
        chunkClass.vertex.add_data3(x, y + 1.0, slabBottomZ)
        tex = Occludedblock.bottomUvCoordinates

        tex1 = tex[0]
        chunkClass.texcoord.add_data2(tex1[0], tex1[1])

        # Bottom-right vertex
        tex2 = tex[1]
        chunkClass.vertex.add_data3(x + 1.0, y + 1.0, slabBottomZ)
        chunkClass.texcoord.add_data2(tex2[0], tex2[1])

        # Top-right vertex
        tex3 = tex[2]
        chunkClass.vertex.add_data3(x + 1.0, y, slabBottomZ)
        chunkClass.texcoord.add_data2(tex3[0], tex3[1])

        # Top-left vertex
        tex4 = tex[3]
        chunkClass.vertex.add_data3(x, y, slabBottomZ)
        chunkClass.texcoord.add_data2(tex4[0], tex4[1])

        face_start = chunkClass.vertex_count

        # First triangle (bottom-left, bottom-right, top-right)
        chunkClass.tri.add_vertex(face_start + 0)
        chunkClass.tri.add_vertex(face_start + 1)
        chunkClass.tri.add_vertex(face_start + 2)
        chunkClass.tri.close_primitive()

        # Second triangle (bottom-left, top-right, top-left)
        chunkClass.tri.add_vertex(face_start + 0)
        chunkClass.tri.add_vertex(face_start + 2)
        chunkClass.tri.add_vertex(face_start + 3)
        chunkClass.tri.close_primitive()
        chunkClass.vertex_count += 4

    def _addTopFace(self, chunkClass, x, y, z, Occludedblock, slabPosition):
        slabTopZ = self._getSlabZRange(z, slabPosition)[1]
        # 2. Add 4 vertices for a flat quad with respective (U, V) coordinates
        # Bottom-left vertex
        chunkClass.vertex.add_data3(x, y, slabTopZ)
        tex = Occludedblock.topUvCoordinates

        tex1 = tex[0]
        chunkClass.texcoord.add_data2(tex1[0], tex1[1])

        # Bottom-right vertex
        tex2 = tex[1]
        chunkClass.vertex.add_data3(x + 1.0, y, slabTopZ)
        chunkClass.texcoord.add_data2(tex2[0], tex2[1])

        # Top-right vertex
        tex3 = tex[2]
        chunkClass.vertex.add_data3(x + 1.0, y + 1.0, slabTopZ)
        chunkClass.texcoord.add_data2(tex3[0], tex3[1])

        # Top-left vertex
        tex4 = tex[3]
        chunkClass.vertex.add_data3(x, y + 1.0, slabTopZ)
        chunkClass.texcoord.add_data2(tex4[0], tex4[1])

        face_start = chunkClass.vertex_count

        # First triangle (bottom-left, bottom-right, top-right)
        chunkClass.tri.add_vertex(face_start + 0)
        chunkClass.tri.add_vertex(face_start + 1)
        chunkClass.tri.add_vertex(face_start + 2)
        chunkClass.tri.close_primitive()

        # Second triangle (bottom-left, top-right, top-left)
        chunkClass.tri.add_vertex(face_start + 0)
        chunkClass.tri.add_vertex(face_start + 2)
        chunkClass.tri.add_vertex(face_start + 3)
        chunkClass.tri.close_primitive()
        chunkClass.vertex_count += 4


class ProceduralGeometryWorkshop():
    def __init__(self):
        self.id = 0
        self.idBlockDefinitions = {}
        self.customMeshOperations = CustomMeshOperations()
        self.occlusionBlockOperations = OcclusionOperations()
        self.occlusionWedgeBlockOperations = OcclusionWedgeOperations()
        self.occlusionSlabBlockOperations = OcclusionSlabOperations()

    def _normalizeMeshScale(self, meshScale):
        if isinstance(meshScale, (int, float)):
            scale = float(meshScale)
            return scale, scale, scale
        if len(meshScale) != 3:
            raise ValueError("meshScale must be a number or a 3-item sequence")

        return float(meshScale[0]), float(meshScale[1]), float(meshScale[2])

    def _normalizeMeshOffset(self, meshOffset):
        if len(meshOffset) != 3:
            raise ValueError("meshOffset must be a 3-item sequence")

        return float(meshOffset[0]), float(meshOffset[1]), float(meshOffset[2])

    def _normalizeMeshCoordinateSystem(self, meshCoordinateSystem):
        if meshCoordinateSystem is None:
            return "obj_y_up"

        normalized = str(meshCoordinateSystem).lower().replace("-", "_")
        coordinateSystemAliases = {
            "obj_y_up": "obj_y_up",
            "y_up": "obj_y_up",
            "blockbench": "obj_y_up",
            "raw": "raw",
            "block": "raw",
            "minecraft": "raw",
            "panda": "raw",
            "z_up": "raw",
        }

        coordinateSystem = coordinateSystemAliases.get(normalized)
        if coordinateSystem is None:
            validCoordinateSystems = ", ".join(("obj_y_up", "raw"))
            raise ValueError(
                f"Unsupported meshCoordinateSystem '{meshCoordinateSystem}'. Expected one of: {validCoordinateSystems}"
            )

        return coordinateSystem

    def _normalizeReverseWinding(self, reverseWinding, meshCoordinateSystem):
        if reverseWinding is not None:
            return bool(reverseWinding)

        return self._normalizeMeshCoordinateSystem(meshCoordinateSystem) == "obj_y_up"

    def _normalizeMeshAnchor(self, meshAnchor):
        if meshAnchor is None or meshAnchor is False:
            return "raw"
        if meshAnchor is True:
            return "bottom_center"

        normalized = str(meshAnchor).lower().replace("-", "_")
        meshAnchorAliases = {
            "raw": "raw",
            "none": "raw",
            "origin": "raw",
            "min": "min",
            "corner": "min",
            "bottom_left": "min",
            "bottom_center": "bottom_center",
            "bottomcenter": "bottom_center",
            "center_bottom": "bottom_center",
            "center": "center",
            "block_center": "center",
            "blockcenter": "center",
        }

        normalizedAnchor = meshAnchorAliases.get(normalized)
        if normalizedAnchor is None:
            validAnchors = ", ".join(("bottom_center", "center", "min", "raw"))
            raise ValueError(f"Unsupported meshAnchor '{meshAnchor}'. Expected one of: {validAnchors}")

        return normalizedAnchor

    def _convertObjVertexToBlockAxes(self, vertex, meshCoordinateSystem):
        if meshCoordinateSystem == "obj_y_up":
            return vertex[0], vertex[2], vertex[1]

        return vertex

    def _alignMeshVerticesToBlock(self, vertices, meshAnchor):
        meshAnchor = self._normalizeMeshAnchor(meshAnchor)
        if meshAnchor == "raw":
            return vertices

        minX = min(vertex[0] for vertex in vertices)
        minY = min(vertex[1] for vertex in vertices)
        minZ = min(vertex[2] for vertex in vertices)
        maxX = max(vertex[0] for vertex in vertices)
        maxY = max(vertex[1] for vertex in vertices)
        maxZ = max(vertex[2] for vertex in vertices)

        if meshAnchor == "min":
            offset = (-minX, -minY, -minZ)
        elif meshAnchor == "center":
            offset = (
                0.5 - ((minX + maxX) / 2.0),
                0.5 - ((minY + maxY) / 2.0),
                0.5 - ((minZ + maxZ) / 2.0),
            )
        else:
            offset = (
                0.5 - ((minX + maxX) / 2.0),
                0.5 - ((minY + maxY) / 2.0),
                -minZ,
            )

        return tuple(
            (
                vertex[0] + offset[0],
                vertex[1] + offset[1],
                vertex[2] + offset[2],
            )
            for vertex in vertices
        )

    def _prepareObjSourceVertices(
            self,
            sourceVertices,
            meshCoordinateSystem,
            meshScale,
            meshOffset,
            meshAnchor,
    ):
        meshCoordinateSystem = self._normalizeMeshCoordinateSystem(meshCoordinateSystem)

        convertedVertices = tuple(
            self._convertObjVertexToBlockAxes(vertex, meshCoordinateSystem)
            for vertex in sourceVertices
        )
        scaledVertices = tuple(
            (
                vertex[0] * meshScale[0],
                vertex[1] * meshScale[1],
                vertex[2] * meshScale[2],
            )
            for vertex in convertedVertices
        )
        alignedVertices = self._alignMeshVerticesToBlock(scaledVertices, meshAnchor)

        return tuple(
            (
                meshOffset[0] + vertex[0],
                meshOffset[1] + vertex[1],
                meshOffset[2] + vertex[2],
            )
            for vertex in alignedVertices
        )

    def _objIndexToListIndex(self, indexText, itemCount, lineNumber, indexType):
        try:
            objIndex = int(indexText)
        except ValueError:
            raise ValueError(f"Invalid OBJ {indexType} index '{indexText}' on line {lineNumber}")

        if objIndex == 0:
            raise ValueError(f"OBJ {indexType} indices are 1-based; got 0 on line {lineNumber}")

        if objIndex > 0:
            index = objIndex - 1
        else:
            index = itemCount + objIndex

        if index < 0 or index >= itemCount:
            raise ValueError(f"OBJ {indexType} index {objIndex} is out of range on line {lineNumber}")

        return index

    def _parseObjFaceVertex(self, faceVertex, vertexCount, textureCoordinateCount, lineNumber):
        faceVertexParts = faceVertex.split("/")
        if len(faceVertexParts) > 3 or faceVertexParts[0] == "":
            raise ValueError(f"Unsupported OBJ face vertex '{faceVertex}' on line {lineNumber}")

        vertexIndex = self._objIndexToListIndex(
            faceVertexParts[0],
            vertexCount,
            lineNumber,
            "vertex",
        )
        textureCoordinateIndex = None
        if len(faceVertexParts) > 1 and faceVertexParts[1] != "":
            textureCoordinateIndex = self._objIndexToListIndex(
                faceVertexParts[1],
                textureCoordinateCount,
                lineNumber,
                "texture coordinate",
            )

        return vertexIndex, textureCoordinateIndex

    def _loadObjMeshDefinition(
            self,
            objFilePath,
            meshScale=1.0,
            meshOffset=(0.0, 0.0, 0.0),
            flipV=False,
            occludes=False,
            meshCoordinateSystem="obj_y_up",
            meshAnchor="bottom_center",
            reverseWinding=None,
    ):
        if not str(objFilePath).lower().endswith(".obj"):
            raise ValueError("Only .obj custom mesh files are currently supported")

        reverseWinding = self._normalizeReverseWinding(reverseWinding, meshCoordinateSystem)
        meshScale = self._normalizeMeshScale(meshScale)
        meshOffset = self._normalizeMeshOffset(meshOffset)

        sourceVertices = []
        sourceTextureCoordinates = []
        sourceFaces = []
        meshVertices = []
        meshTextureCoordinates = []
        meshTriOffsets = []

        with open(objFilePath, "r", encoding="utf-8", errors="replace") as objFile:
            for lineNumber, line in enumerate(objFile, start=1):
                line = line.strip()
                if line == "" or line.startswith("#"):
                    continue

                lineParts = line.split()
                recordType = lineParts[0]

                if recordType == "v":
                    if len(lineParts) < 4:
                        raise ValueError(f"OBJ vertex on line {lineNumber} must include x, y, and z")
                    sourceVertices.append((
                        float(lineParts[1]),
                        float(lineParts[2]),
                        float(lineParts[3]),
                    ))
                elif recordType == "vt":
                    if len(lineParts) < 3:
                        raise ValueError(f"OBJ texture coordinate on line {lineNumber} must include u and v")
                    textureV = float(lineParts[2])
                    if flipV:
                        textureV = 1.0 - textureV
                    sourceTextureCoordinates.append((float(lineParts[1]), textureV))
                elif recordType == "f":
                    if len(lineParts) < 4:
                        raise ValueError(f"OBJ face on line {lineNumber} must include at least three vertices")

                    faceVertices = [
                        self._parseObjFaceVertex(
                            faceVertex,
                            len(sourceVertices),
                            len(sourceTextureCoordinates),
                            lineNumber,
                        )
                        for faceVertex in lineParts[1:]
                    ]
                    sourceFaces.append(faceVertices)

        if len(sourceVertices) == 0:
            raise ValueError(f"OBJ file '{objFilePath}' did not contain any vertices")

        sourceVertices = self._prepareObjSourceVertices(
            sourceVertices,
            meshCoordinateSystem,
            meshScale,
            meshOffset,
            meshAnchor,
        )

        for faceVertices in sourceFaces:
            for triangleIndex in range(1, len(faceVertices) - 1):
                triangleVertices = (
                    faceVertices[0],
                    faceVertices[triangleIndex],
                    faceVertices[triangleIndex + 1],
                )
                if reverseWinding:
                    triangleVertices = (
                        triangleVertices[0],
                        triangleVertices[2],
                        triangleVertices[1],
                    )

                for vertexIndex, textureCoordinateIndex in triangleVertices:
                    meshVertices.append(sourceVertices[vertexIndex])
                    if textureCoordinateIndex is None:
                        meshTextureCoordinates.append((0.0, 0.0))
                    else:
                        meshTextureCoordinates.append(sourceTextureCoordinates[textureCoordinateIndex])
                    meshTriOffsets.append(len(meshVertices) - 1)

        if len(meshVertices) == 0:
            raise ValueError(f"OBJ file '{objFilePath}' did not contain any renderable faces")

        return CustomMeshBlockDefinition(
            meshVertices,
            meshTextureCoordinates,
            meshTriOffsets,
            occludes=occludes,
        )

    def registerCustomMeshBlock(self, blockId, vertexOffsets, textureOffsets=None, triOffsets=None, occludes=False):
        blockId = int(blockId)
        if blockId <= 0:
            raise ValueError("Custom mesh blockId must be greater than 0")

        self.idBlockDefinitions[blockId] = CustomMeshBlockDefinition(
            vertexOffsets,
            textureOffsets,
            triOffsets,
            occludes=occludes,
        )
        self.id = max(self.id, blockId)
        return blockId

    def registerCustomMeshBlockFromFile(
            self,
            blockId,
            meshFilePath,
            meshScale=1.0,
            meshOffset=(0.0, 0.0, 0.0),
            flipV=False,
            occludes=False,
            meshCoordinateSystem="obj_y_up",
            meshAnchor="bottom_center",
            reverseWinding=None,
    ):
        if not str(meshFilePath).lower().endswith(".obj"):
            raise ValueError("Only .obj custom mesh files are currently supported")

        blockId = int(blockId)
        if blockId <= 0:
            raise ValueError("Custom mesh blockId must be greater than 0")

        self.idBlockDefinitions[blockId] = self._loadObjMeshDefinition(
            meshFilePath,
            meshScale=meshScale,
            meshOffset=meshOffset,
            flipV=flipV,
            occludes=occludes,
            meshCoordinateSystem=meshCoordinateSystem,
            meshAnchor=meshAnchor,
            reverseWinding=reverseWinding,
        )
        self.id = max(self.id, blockId)
        return blockId

    def registerCustomMeshBlockFromObjFile(
            self,
            blockId,
            objFilePath,
            meshScale=1.0,
            meshOffset=(0.0, 0.0, 0.0),
            flipV=False,
            occludes=False,
            meshCoordinateSystem="obj_y_up",
            meshAnchor="bottom_center",
            reverseWinding=None,
    ):
        return self.registerCustomMeshBlockFromFile(
            blockId,
            objFilePath,
            meshScale=meshScale,
            meshOffset=meshOffset,
            flipV=flipV,
            occludes=occludes,
            meshCoordinateSystem=meshCoordinateSystem,
            meshAnchor=meshAnchor,
            reverseWinding=reverseWinding,
        )

    def coordinateBlockOutOfBoundsOrAirNormalOccludedBlock(self, x, y, z, blockIDS):
        x_size, y_size, z_size = blockIDS.shape

        out_of_bounds = not (
                0 <= x < x_size
                and 0 <= y < y_size
                and 0 <= z < z_size
        )

        if out_of_bounds:
            return True

        individualBlockId = blockIDS[x, y, z]
        idDefinition = self.idBlockDefinitions.get(individualBlockId)
        isCustomMesh = isinstance(idDefinition,CustomMeshBlockDefinition)
        isSlab = isinstance(idDefinition,OccludedSlabBlockDefinition)
        isWedge = isinstance(idDefinition,OccludedWedgeBlockDefinition)
        if isCustomMesh and not idDefinition.occludes:
            return True
        if isSlab:
            return True
        if isWedge:
            return True

        return bool(individualBlockId == 0)

    def coordinateBlockOutOfBoundsOrAirSlabBlock(self, x, y, z, blockIDS):
        x_size, y_size, z_size = blockIDS.shape

        out_of_bounds = not (
                0 <= x < x_size
                and 0 <= y < y_size
                and 0 <= z < z_size
        )

        if out_of_bounds:
            return True

        individualBlockId = blockIDS[x, y, z]
        idDefinition = self.idBlockDefinitions.get(individualBlockId)
        if isinstance(idDefinition,CustomMeshBlockDefinition) and not idDefinition.occludes:
            return True

        return bool(individualBlockId == 0)

    def coordinateBlockOutOfBoundsOrAirWedgeBlock(self, x, y, z, blockIDS, faceName=None, direction=None):
        x_size, y_size, z_size = blockIDS.shape

        out_of_bounds = not (
                0 <= x < x_size
                and 0 <= y < y_size
                and 0 <= z < z_size
        )

        if out_of_bounds:
            return True

        individualBlockId = blockIDS[x, y, z]
        idDefinition = self.idBlockDefinitions.get(individualBlockId)

        if isinstance(idDefinition,CustomMeshBlockDefinition) and not idDefinition.occludes:
            return True

        if isinstance(idDefinition,OccludedSlabBlockDefinition) and faceName is not None:
            oppositeFaceName = self.occlusionWedgeBlockOperations.oppositeFaceName(faceName)
            return not self.occlusionSlabBlockOperations.slabFaceOccludesWedgeFace(
                idDefinition.slabPosition,
                oppositeFaceName,
                faceName,
            )

        if isinstance(idDefinition,OccludedWedgeBlockDefinition) and faceName is not None and direction is not None:
            oppositeFaceName = self.occlusionWedgeBlockOperations.oppositeFaceName(faceName)
            return not self.occlusionWedgeBlockOperations.wedgeFaceOccludes(
                direction,
                faceName,
                idDefinition.direction,
                oppositeFaceName,
            )

        return bool(individualBlockId == 0)


    def _occludedNotEmpty(self,top,bottom,left,right,back,front):
        return top != None and bottom != None and left != None and right != None and back != None and front != None

    def addBlockOrMesh(
            self,
            type,
            top=None,
            bottom=None,
            left=None,
            right=None,
            back=None,
            front=None,
            direction="north",
            slabPosition="bottom",
            meshFilePath=None,
            vertexOffsets=None,
            textureOffsets=None,
            triOffsets=None,
            meshScale=1.0,
            meshOffset=(0.0, 0.0, 0.0),
            flipV=False,
            occludes=False,
            meshCoordinateSystem="obj_y_up",
            meshAnchor="bottom_center",
            reverseWinding=None,
    ):
        self.id += 1
        if type == "occluded" and self._occludedNotEmpty(top,bottom,left,right,back,front):
            self.idBlockDefinitions[self.id] = OccludedblockDefinition(top,bottom,left,right,back,front)
        elif type in ("occludedWedge", "occlusionWedge", "wedge") and self._occludedNotEmpty(top,bottom,left,right,back,front):
            self.idBlockDefinitions[self.id] = OccludedWedgeBlockDefinition(top,bottom,left,right,back,front,direction)
        elif type in ("occludedSlab", "occlusionSlab", "slab") and self._occludedNotEmpty(top,bottom,left,right,back,front):
            self.idBlockDefinitions[self.id] = OccludedSlabBlockDefinition(top,bottom,left,right,back,front,slabPosition)
        elif type in ("customMesh", "customMeshFromFile", "mesh", "obj", "objMesh"):
            if meshFilePath is None and isinstance(top, str):
                meshFilePath = top

            if meshFilePath is not None:
                self.idBlockDefinitions[self.id] = self._loadObjMeshDefinition(
                    meshFilePath,
                    meshScale=meshScale,
                    meshOffset=meshOffset,
                    flipV=flipV,
                    occludes=occludes,
                    meshCoordinateSystem=meshCoordinateSystem,
                    meshAnchor=meshAnchor,
                    reverseWinding=reverseWinding,
                )
            elif vertexOffsets is not None:
                self.idBlockDefinitions[self.id] = CustomMeshBlockDefinition(
                    vertexOffsets,
                    textureOffsets,
                    triOffsets,
                    occludes=occludes,
                )
            else:
                raise ValueError("Custom mesh blocks require meshFilePath or vertexOffsets")

        return self.id

    def doBlockIdOperation(self,chunkClass,x,y,z,blockIds):
        blockId = int(blockIds[x, y, z])
        idDefinition = self.idBlockDefinitions.get(blockId)
        if idDefinition is None:
            return

        if isinstance(idDefinition,CustomMeshBlockDefinition):
            self.CustomMeshOperation(chunkClass,x,y,z,blockIds,idDefinition)
        elif isinstance(idDefinition,OccludedSlabBlockDefinition):
            self.OcclusionSlabOperation(chunkClass,x,y,z,blockIds,idDefinition)
        elif isinstance(idDefinition,OccludedWedgeBlockDefinition):
            self.OcclusionWedgeOperation(chunkClass,x,y,z,blockIds,idDefinition)
        elif isinstance(idDefinition,OccludedblockDefinition):
            self.OcclusionOperation(chunkClass,x,y,z,blockIds,idDefinition)

    def CustomMeshOperation(self,chunkClass,x,y,z,blockIDS,CustomMeshBlock):
        self.customMeshOperations._addCustomMesh(chunkClass,x,y,z,CustomMeshBlock)

    def OcclusionOperation(self,chunkClass,x,y,z,blockIDS,Occludedblock):
        if self.coordinateBlockOutOfBoundsOrAirNormalOccludedBlock(x - 1, y, z, blockIDS):
            self.occlusionBlockOperations._addLeftFace(chunkClass,x, y, z,Occludedblock)

        if self.coordinateBlockOutOfBoundsOrAirNormalOccludedBlock(x + 1, y, z, blockIDS):
            self.occlusionBlockOperations._addRightFace(chunkClass,x, y, z,Occludedblock)

        if self.coordinateBlockOutOfBoundsOrAirNormalOccludedBlock(x, y - 1, z, blockIDS):
            self.occlusionBlockOperations._addFrontFace(chunkClass,x, y, z,Occludedblock)

        if self.coordinateBlockOutOfBoundsOrAirNormalOccludedBlock(x, y + 1, z, blockIDS):
            self.occlusionBlockOperations._addBackFace(chunkClass,x, y, z,Occludedblock)

        if self.coordinateBlockOutOfBoundsOrAirNormalOccludedBlock(x, y, z + 1, blockIDS):
            self.occlusionBlockOperations._addTopFace(chunkClass,x, y, z,Occludedblock)

        if self.coordinateBlockOutOfBoundsOrAirNormalOccludedBlock(x, y, z - 1, blockIDS):
            self.occlusionBlockOperations._addBottomFace(chunkClass,x, y, z,Occludedblock)

    def OcclusionWedgeOperation(self,chunkClass,x,y,z,blockIDS,Occludedblock):
        direction = Occludedblock.direction

        if self.coordinateBlockOutOfBoundsOrAirWedgeBlock(x - 1, y, z, blockIDS, "left", direction):
            self.occlusionWedgeBlockOperations._addLeftFace(chunkClass,x, y, z,Occludedblock,direction)

        if self.coordinateBlockOutOfBoundsOrAirWedgeBlock(x + 1, y, z, blockIDS, "right", direction):
            self.occlusionWedgeBlockOperations._addRightFace(chunkClass,x, y, z,Occludedblock,direction)

        if self.coordinateBlockOutOfBoundsOrAirWedgeBlock(x, y - 1, z, blockIDS, "front", direction):
            self.occlusionWedgeBlockOperations._addFrontFace(chunkClass,x, y, z,Occludedblock,direction)

        if self.coordinateBlockOutOfBoundsOrAirWedgeBlock(x, y + 1, z, blockIDS, "back", direction):
            self.occlusionWedgeBlockOperations._addBackFace(chunkClass,x, y, z,Occludedblock,direction)

        #NOTE: PREVIOUS BUG WITH... if chunkClass.coordinateBlockOutOfBoundsOrAir(x, y, z + 1, blockIDS):
        #would otherwise inapproiately occlude, you always include the top no matter what
        self.occlusionWedgeBlockOperations._addTopFace(chunkClass,x, y, z,Occludedblock,direction)

        if self.coordinateBlockOutOfBoundsOrAirWedgeBlock(x, y, z - 1, blockIDS, "bottom", direction):
            self.occlusionWedgeBlockOperations._addBottomFace(chunkClass,x, y, z,Occludedblock,direction)

    def OcclusionSlabOperation(self,chunkClass,x,y,z,blockIDS,Occludedblock):
        slabPosition = Occludedblock.slabPosition

        if self.coordinateBlockOutOfBoundsOrAirSlabBlock(x - 1, y, z, blockIDS):
            self.occlusionSlabBlockOperations._addLeftFace(chunkClass,x, y, z,Occludedblock,slabPosition)

        if self.coordinateBlockOutOfBoundsOrAirSlabBlock(x + 1, y, z, blockIDS):
            self.occlusionSlabBlockOperations._addRightFace(chunkClass,x, y, z,Occludedblock,slabPosition)

        if self.coordinateBlockOutOfBoundsOrAirSlabBlock(x, y - 1, z, blockIDS):
            self.occlusionSlabBlockOperations._addFrontFace(chunkClass,x, y, z,Occludedblock,slabPosition)

        if self.coordinateBlockOutOfBoundsOrAirSlabBlock(x, y + 1, z, blockIDS):
            self.occlusionSlabBlockOperations._addBackFace(chunkClass,x, y, z,Occludedblock,slabPosition)

        if slabPosition == "top" and self.coordinateBlockOutOfBoundsOrAirSlabBlock(x, y, z + 1, blockIDS):
            self.occlusionSlabBlockOperations._addTopFace(chunkClass,x, y, z,Occludedblock,slabPosition)
        elif slabPosition == "bottom":
            self.occlusionSlabBlockOperations._addTopFace(chunkClass,x, y, z,Occludedblock,slabPosition)

        individualBlockId = blockIDS[x, y, z - 1]
        idDefinition = self.idBlockDefinitions.get(individualBlockId)
        isSlab = isinstance(idDefinition, OccludedSlabBlockDefinition)
        isWedge = isinstance(idDefinition, OccludedWedgeBlockDefinition)
        if slabPosition == "bottom" and self.coordinateBlockOutOfBoundsOrAirSlabBlock(x, y, z - 1, blockIDS) or (isSlab or isWedge):
            self.occlusionSlabBlockOperations._addBottomFace(chunkClass,x, y, z,Occludedblock,slabPosition)
        elif slabPosition == "top":
            self.occlusionSlabBlockOperations._addBottomFace(chunkClass,x, y, z,Occludedblock,slabPosition)
