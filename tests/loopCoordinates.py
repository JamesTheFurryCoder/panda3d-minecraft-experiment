def get_cylinder_coords(x, y, z, r, h):
    coords = set()

    for dy in range(-h, h + 1):
        for dx in range(-r, r + 1):
            for dz in range(-r, r + 1):

                # Check if (dx, dz) is inside the circle
                if dx * dx + dz * dz <= r * r:
                    coords.add((
                        x + dx,
                        y + dy,
                        z + dz
                    ))

    return coords