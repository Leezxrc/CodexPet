"""Appearance definitions and local head-pat animation, in logical pixels."""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Appearance:
    label: str
    asset: str
    head_rect: tuple[float, float, float, float]
    pat_style: str


APPEARANCES = {
    'dragon': Appearance('白龙 · 轻晃', 'pet-v2.png', (92, 5, 116, 94), 'sway'),
    'chibi': Appearance('圆脸 Q 版 · 挤压回弹', 'pet-chibi.png', (70, 12, 160, 120), 'squash'),
}
PAT_DURATION = 1.4


def pat_transform(appearance, age):
    """Return horizontal scale, vertical scale and rotation around a fixed base."""
    if not 0 <= age < PAT_DURATION:
        return 1.0, 1.0, 0.0
    progress = age / PAT_DURATION
    if APPEARANCES[appearance].pat_style == 'squash':
        compression = 0.20 * math.sin(3 * math.pi * progress) ** 2 * (1 - progress)
        height = 1 - compression
        # Preserve area: a deeper press produces proportionally wider sides.
        return 1 / height, height, 0.0
    return 1.0, 1.0, math.sin(age * 10) * 3 * (1 - progress)
