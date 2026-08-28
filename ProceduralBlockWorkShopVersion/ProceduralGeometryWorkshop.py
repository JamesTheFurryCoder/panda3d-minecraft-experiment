class OccludedblockDefinition():
    def __init__(self,top,bottom,left,right,back,front):
        #emptyList for all variables like this [(x,y),(x1,y1),(x2,y2),(x3,y3)]
        self.topUvCoordinates = top
        self.leftUvCoordinates = left
        self.rightUvCoordinates = right
        self.bottomUvCoordinates = bottom
        self.backUvCoordinates = back
        self.frontUvCoordinates = front



class ProceduralGeometryWorkshop():
    def __init__(self):
        self.id = 0
        self.idBlockDefinitions = {}

    def _occludedNotEmpty(self,top,bottom,left,right,back,front):
        return top != None and bottom != None and left != None and right != None and back != None and front != None

    def addBlockOrMesh(self,type,top=None,bottom=None,left=None,right=None,back=None,front=None):
        self.id += 1
        if type == "occluded" and self._occludedNotEmpty(top,bottom,left,right,back,front):
            self.idBlockDefinitions[self.id] = OccludedblockDefinition(top,bottom,left,right,back,front)

    def doBlockIdOperation(self,chunkClass,x,y,z,blockIds):
        blockId = int(blockIds[x, y, z])
        idDefinition = self.idBlockDefinitions.get(blockId)
        if idDefinition is None:
            return

        if isinstance(idDefinition,OccludedblockDefinition):
            self.OcclusionOperation(chunkClass,x,y,z,blockIds,idDefinition)

    def OcclusionOperation(self,chunkClass,x,y,z,blockIDS,Occludedblock):
        if chunkClass.coordinateBlockOutOfBoundsOrAir(x - 1, y, z, blockIDS):
            self._addLeftFace(chunkClass,x, y, z,Occludedblock)

        if chunkClass.coordinateBlockOutOfBoundsOrAir(x + 1, y, z, blockIDS):
            self._addRightFace(chunkClass,x, y, z,Occludedblock)

        if chunkClass.coordinateBlockOutOfBoundsOrAir(x, y - 1, z, blockIDS):
            self._addFrontFace(chunkClass,x, y, z,Occludedblock)

        if chunkClass.coordinateBlockOutOfBoundsOrAir(x, y + 1, z, blockIDS):
            self._addBackFace(chunkClass,x, y, z,Occludedblock)

        if chunkClass.coordinateBlockOutOfBoundsOrAir(x, y, z + 1, blockIDS):
            self._addTopFace(chunkClass,x, y, z,Occludedblock)

        if chunkClass.coordinateBlockOutOfBoundsOrAir(x, y, z - 1, blockIDS):
            self._addBottomFace(chunkClass,x, y, z,Occludedblock)


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



