from PIL import Image, ImageDraw

class GridWorld:
    def __init__(self, size=10):
        self.size = size
        # Simulated exploration state
        self.grid = [[False for _ in range(size)] for _ in range(size)]
        self.grid[0][0] = True
        self.grid[1][0] = True
        self.grid[2][0] = True
        self.grid[2][1] = True
        self.grid[3][1] = True
        self.grid[4][1] = True  # Example path

    def step(self):
        # Placeholder step logic
        return {"complete": False, "message": "Step taken"}

    def render_tile_map(self):
        tile_size = 20
        img_size = self.size * tile_size
        img = Image.new("RGB", (img_size, img_size), color="black")
        draw = ImageDraw.Draw(img)

        for y in range(self.size):
            for x in range(self.size):
                top_left = (x * tile_size, y * tile_size)
                bottom_right = ((x + 1) * tile_size, (y + 1) * tile_size)

                color = "#00ff00" if self.grid[y][x] else "#333333"
                draw.rectangle([top_left, bottom_right], fill=color, outline="gray")

        return img
