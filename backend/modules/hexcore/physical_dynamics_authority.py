"""Independent black-box authority for Arena v8 physical-control evaluation.

The evaluator owns hidden dynamics and renders observations.  AION's benchmark
may call reset/observe/step but receives no parameter or state accessors.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from io import BytesIO
import random
from typing import Any

from PIL import Image, ImageDraw


@dataclass(frozen=True)
class HiddenDynamics:
    gain: float
    drag: float
    delay: int
    changed_gain: float | None = None
    change_step: int | None = None
    nonlinear_deadzone: float = 0.0


class PixelDynamicsAuthority:
    """Render-only, bounded one-dimensional dynamics with delayed actuation."""

    def __init__(self, *, dynamics: HiddenDynamics, seed: int, target: float) -> None:
        self.__dynamics = dynamics
        self.__rng = random.Random(seed)
        self.__target = target
        self.__x = self.__rng.uniform(-0.62, -0.28)
        self.__v = 0.0
        self.__step = 0
        self.__queue: deque[float] = deque([0.0] * dynamics.delay)

    def _gain(self) -> float:
        d = self.__dynamics
        if d.change_step is not None and self.__step >= d.change_step and d.changed_gain is not None:
            return d.changed_gain
        return d.gain

    def observe(self) -> dict[str, Any]:
        image = Image.new("RGB", (256, 96), "white")
        draw = ImageDraw.Draw(image)
        draw.line((16, 55, 240, 55), fill=(80, 80, 80), width=2)
        target_px = int(round(128 + self.__target * 104))
        draw.line((target_px, 25, target_px, 76), fill=(20, 90, 220), width=3)
        object_px = int(round(128 + self.__x * 104))
        draw.ellipse((object_px - 6, 49, object_px + 6, 61), fill=(220, 25, 35))
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        return {
            "png": buffer.getvalue(),
            "noisy_velocity_sensor": self.__v + self.__rng.gauss(0.0, 0.007),
            "timestamp": self.__step,
        }

    def step(self, action: float) -> dict[str, Any]:
        action = max(-1.0, min(1.0, float(action)))
        if self.__queue:
            self.__queue.append(action)
            applied = self.__queue.popleft()
        else:
            applied = action
        d = self.__dynamics
        if abs(applied) < d.nonlinear_deadzone:
            applied = 0.0
        dt = 0.25
        self.__v = (1.0 - d.drag * dt) * self.__v + self._gain() * applied * dt
        self.__x += self.__v * dt
        if self.__x < -1.0 or self.__x > 1.0:
            self.__x = max(-1.0, min(1.0, self.__x))
            self.__v *= -0.25
        self.__step += 1
        return self.observe()

    def score(self) -> dict[str, float | bool]:
        error = abs(self.__x - self.__target)
        return {"goal_error": error, "goal_reached": error <= 0.09}

