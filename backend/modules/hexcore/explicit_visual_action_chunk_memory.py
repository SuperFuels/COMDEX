"""Auditable RGB keypoints and recovery-capable action-chunk memory.

Training labels may calibrate the visual keypoint, but runtime lookup accepts
only RGB, bounded proprioception, phase, and the public mission contract.
"""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np
from scipy.spatial import cKDTree

from backend.modules.hexcore.object_centric_action_chunk_policy import project_world


@dataclass(frozen=True)
class ChromaKeypoint:
    prototype: np.ndarray
    affine: np.ndarray
    roi: tuple[int, int, int, int]
    top_pixels: int = 16

    @staticmethod
    def _normalise(rgb: np.ndarray) -> np.ndarray:
        value = rgb.astype(np.float32) + 1.0
        return value / np.linalg.norm(value, axis=-1, keepdims=True).clip(1e-6)

    @classmethod
    def fit(cls, rgb: np.ndarray, object_world: np.ndarray) -> "ChromaKeypoint":
        truth, _ = project_world(object_world)
        samples = []
        for image, (u, v) in zip(rgb, truth):
            x, y = int(round(float(u))), int(round(float(v)))
            patch = image[max(0, y - 6):min(image.shape[0], y + 7),
                          max(0, x - 6):min(image.shape[1], x + 7)]
            unit = cls._normalise(patch)
            # The manipulated cube is the locally most yellow/cyan chromatic
            # object. The score is learned only inside label-authorised crops.
            score = (unit[..., 0] + unit[..., 1]) * .5 - unit[..., 2]
            samples.append(unit.reshape(-1, 3)[int(score.argmax())])
        prototype = np.mean(samples, axis=0)
        prototype /= np.linalg.norm(prototype)
        margin = 12
        x0 = max(0, int(np.floor(truth[:, 0].min())) - margin)
        x1 = min(rgb.shape[2], int(np.ceil(truth[:, 0].max())) + margin + 1)
        y0 = max(0, int(np.floor(truth[:, 1].min())) - margin)
        y1 = min(rgb.shape[1], int(np.ceil(truth[:, 1].max())) + margin + 1)
        raw = cls(prototype, np.eye(2, 3, dtype=np.float32), (x0, y0, x1, y1)).detect(rgb)
        design = np.column_stack((raw, np.ones(len(raw), dtype=np.float32)))
        affine = np.linalg.lstsq(design, truth, rcond=None)[0].T.astype(np.float32)
        return cls(prototype.astype(np.float32), affine, (x0, y0, x1, y1))

    def detect(self, rgb: np.ndarray) -> np.ndarray:
        images = np.asarray(rgb)
        single = images.ndim == 3
        if single:
            images = images[None]
        x0, y0, x1, y1 = self.roi
        yy, xx = np.mgrid[y0:y1, x0:x1]
        points = np.column_stack((xx.ravel(), yy.ravel())).astype(np.float32)
        output = []
        for image in images:
            unit = self._normalise(image[y0:y1, x0:x1]).reshape(-1, 3)
            distance = np.square(unit - self.prototype).sum(-1)
            count = min(self.top_pixels, len(distance))
            selected = np.argpartition(distance, count - 1)[:count]
            confidence = np.exp(-distance[selected] * 40.0)
            raw = np.average(points[selected], axis=0, weights=confidence)
            output.append(self.affine @ np.array([raw[0], raw[1], 1.0], np.float32))
        result = np.asarray(output, np.float32)
        return result[0] if single else result

    def state_dict(self) -> dict:
        return {"prototype": self.prototype.tolist(), "affine": self.affine.tolist(),
                "roi": list(self.roi), "top_pixels": self.top_pixels}


class ActionChunkMemory:
    """Nearest coherent recovery chunks under a development-selected metric."""

    def __init__(self, features: np.ndarray, chunks: np.ndarray, weights: np.ndarray,
                 mean: np.ndarray, scale: np.ndarray, neighbours: int):
        self.weights = np.asarray(weights, np.float32)
        self.mean = np.asarray(mean, np.float32)
        self.scale = np.asarray(scale, np.float32)
        self.features = np.asarray(features, np.float32)
        self.chunks = np.asarray(chunks, np.float32)
        self.neighbours = int(neighbours)
        self.tree = cKDTree(self._transform(self.features))

    def _transform(self, values: np.ndarray) -> np.ndarray:
        return ((values - self.mean) / self.scale) * self.weights

    def predict(self, values: np.ndarray) -> np.ndarray:
        distance, index = self.tree.query(
            self._transform(np.asarray(values)), k=self.neighbours, workers=-1
        )
        if self.neighbours == 1:
            return self.chunks[index]
        distance = np.asarray(distance)
        index = np.asarray(index)
        weight = 1.0 / np.maximum(distance, 1e-4)
        return (self.chunks[index] * weight[..., None, None]).sum(-3) / weight.sum(-1)[..., None, None]


def make_features(proprio: np.ndarray, uv: np.ndarray, step: np.ndarray) -> np.ndarray:
    phase = np.asarray(step, np.float32) / 250.0 * np.pi * 2.0
    return np.column_stack((proprio[:, :9], proprio[:, 9:18], uv / [128.0, 96.0],
                            np.sin(phase), np.cos(phase))).astype(np.float32)


def feature_weights(groups: tuple[float, float, float, float]) -> np.ndarray:
    joint, velocity, visual, phase = groups
    return np.asarray([joint] * 9 + [velocity] * 9 + [visual] * 2 + [phase] * 2, np.float32)
