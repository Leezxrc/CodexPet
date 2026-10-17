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
    'chibi': Appearance('圆脸 Q 版 · 上下弹', 'pet-chibi.png', (70, 12, 160, 120), 'bounce'),
}
PAT_DURATION = 1.4


def pat_transform(appearance, age):
    """Return vertical offset and degrees. Three decaying, above-ground hops."""
    if not 0 <= age < PAT_DURATION:
        return 0.0, 0.0
    progress = age / PAT_DURATION
    if APPEARANCES[appearance].pat_style == 'bounce':
        return -15 * abs(math.sin(3 * math.pi * progress)) * (1 - progress), 0.0
    return 0.0, math.sin(age * 10) * 3 * (1 - progress)
