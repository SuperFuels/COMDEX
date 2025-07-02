import json
from pathlib import Path

STATE_PATH = Path("backend/modules/aion/grid_world_state.json")

class GridWorld:
    def __init__(self, size=10):
        self.size = size
        self.grid = [[False for _ in range(size)] for _ in range(size)]
        # Try to load saved state
        if STATE_PATH.exists():
            with open(STATE_PATH, "r") as f:
                saved = json.load(f)
                self.grid = saved.get("grid", self.grid)

    def save_state(self):
        with open(STATE_PATH, "w") as f:
            json.dump({"grid": self.grid}, f)

    def step(self):
        # Your logic here, mark cells explored, e.g.
        # self.grid[x][y] = True
        self.save_state()
        # Return status dict as needed
        return {"complete": False, "message": "Step taken"}

    def get_progress(self):
        total_tiles = self.size * self.size
        explored = sum(sum(1 for cell in row if cell) for row in self.grid)
        progress_percent = explored / total_tiles
        return {
            "explored_tiles": explored,
            "total_tiles": total_tiles,
            "progress": progress_percent
        }