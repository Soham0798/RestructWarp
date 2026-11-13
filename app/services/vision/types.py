"""The shape every vision step passes along: one detected box."""
from dataclasses import dataclass


@dataclass
class Detection:
    cls: str      # one of shared/detector_classes.json
    x1: float
    y1: float
    x2: float
    y2: float
    conf: float = 1.0
    text: str = ""  # filled by ocr.py

    @property
    def area(self) -> float:
        return max(0.0, self.x2 - self.x1) * max(0.0, self.y2 - self.y1)

    @property
    def center(self) -> tuple[float, float]:
        return (self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2

    def contains(self, other: "Detection", margin: float = 4) -> bool:
        cx, cy = other.center
        return (self.x1 - margin <= cx <= self.x2 + margin and self.y1 - margin <= cy <= self.y2 + margin
                and other.area < self.area)

    def distance_to(self, other: "Detection") -> float:
        """Gap between two boxes (0 when they touch or overlap)."""
        dx = max(other.x1 - self.x2, self.x1 - other.x2, 0)
        dy = max(other.y1 - self.y2, self.y1 - other.y2, 0)
        return (dx * dx + dy * dy) ** 0.5
