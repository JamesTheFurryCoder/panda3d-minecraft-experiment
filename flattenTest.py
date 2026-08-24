from direct.showbase.ShowBase import ShowBase


class MyApp(ShowBase):
    def __init__(self):
        super().__init__()

        # 1. Create a root container for a static sub-assembly
        # (e.g., a cluster of static props or trees)
        self.assembly_root = self.render.attachNewNode("StaticPropsGroup")

        # 2. Populate the assembly with multiple individual models
        for i in range(5):
            # Load a model (using Panda3D's standard placeholder box)
            prop = self.loader.loadModel("models/box")
            prop.reparentTo(self.assembly_root)

            # Position them uniquely to create a complex scene graph
            prop.setPos(i * 3, 0, 0)
            prop.setScale(0.5)

        # 3. Print the scene graph structure BEFORE flattening
        print("--- Before Optimization ---")
        self.assembly_root.ls()

        # 4. Strip model protective flags so flatten can modify them
        self.assembly_root.clearModelNodes()

        # 5. Apply flattenMedium to bake transforms and collapse empty nodes
        # Python snake_case: flatten_medium()
        # C++ camelCase: flattenMedium()
        self.assembly_root.flatten_strong()

        # 6. Print the scene graph structure AFTER flattening
        print("\n--- After flattenMedium ---")
        self.assembly_root.ls()


app = MyApp()
app.run()