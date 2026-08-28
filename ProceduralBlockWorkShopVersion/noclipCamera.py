from panda3d.core import ClockObject, Vec3, WindowProperties


class NoclipCamera:
    def __init__(
        self,
        showbase,
        start_pos=(0, -10, 3),
        start_hpr=(0, 0, 0),
        speed=8.0,
        sprint_multiplier=3.0,
        mouse_sensitivity=0.15,
    ):
        self.base = showbase
        self.camera = showbase.camera
        self.speed = speed
        self.sprint_multiplier = sprint_multiplier
        self.mouse_sensitivity = mouse_sensitivity

        self.keys = {
            "forward": False,
            "backward": False,
            "left": False,
            "right": False,
            "up": False,
            "down": False,
            "sprint": False,
        }
        self._center_mouse_next_frame = True

        self.base.disable_mouse()
        self.camera.set_pos(*start_pos)
        self.camera.set_hpr(*start_hpr)
        self._hide_cursor()
        self._bind_controls()

        self.base.taskMgr.add(self.update, "noclip-camera-update")

    def _hide_cursor(self):
        props = WindowProperties()
        props.set_cursor_hidden(True)
        self.base.win.request_properties(props)

    def _bind_controls(self):
        self._bind_key("forward", "w", "arrow_up")
        self._bind_key("backward", "s", "arrow_down")
        self._bind_key("left", "a", "arrow_left")
        self._bind_key("right", "d", "arrow_right")
        self._bind_key("up", "space", "e")
        self._bind_key("down", "control", "lcontrol", "rcontrol", "q")
        self._bind_key("sprint", "shift", "lshift", "rshift")

    def _bind_key(self, action, *buttons):
        for button in buttons:
            self.base.accept(button, self._set_key, [action, True])
            self.base.accept(f"{button}-up", self._set_key, [action, False])

    def _set_key(self, action, value):
        self.keys[action] = value

    def update(self, task):
        dt = ClockObject.get_global_clock().get_dt()
        self._update_mouse_look()
        self._update_position(dt)
        return task.cont

    def _update_mouse_look(self):
        if not self.base.mouseWatcherNode.has_mouse():
            self._center_mouse_next_frame = True
            return

        pointer = self.base.win.get_pointer(0)
        center_x = self.base.win.get_x_size() // 2
        center_y = self.base.win.get_y_size() // 2

        if self._center_mouse_next_frame:
            self.base.win.move_pointer(0, center_x, center_y)
            self._center_mouse_next_frame = False
            return

        delta_x = pointer.get_x() - center_x
        delta_y = pointer.get_y() - center_y

        if delta_x or delta_y:
            heading = self.camera.get_h() - delta_x * self.mouse_sensitivity
            pitch = self.camera.get_p() - delta_y * self.mouse_sensitivity
            self.camera.set_hpr(heading, max(-89, min(89, pitch)), 0)
            self.base.win.move_pointer(0, center_x, center_y)

    def _update_position(self, dt):
        move = Vec3(0, 0, 0)
        camera_quat = self.camera.get_quat(self.base.render)

        if self.keys["forward"]:
            move += camera_quat.get_forward()
        if self.keys["backward"]:
            move -= camera_quat.get_forward()
        if self.keys["right"]:
            move += camera_quat.get_right()
        if self.keys["left"]:
            move -= camera_quat.get_right()
        if self.keys["up"]:
            move += Vec3(0, 0, 1)
        if self.keys["down"]:
            move -= Vec3(0, 0, 1)

        if move.length_squared() == 0:
            return

        move.normalize()
        current_speed = self.speed
        if self.keys["sprint"]:
            current_speed *= self.sprint_multiplier

        self.camera.set_pos(self.camera.get_pos() + move * current_speed * dt)
