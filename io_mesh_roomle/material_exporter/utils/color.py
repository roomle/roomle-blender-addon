import math
import re


def linear_to_srgb(c:float) -> float:
    """convert linear color value to srgb

    Args:
        c (float): one of the color values (rgb)

    Returns:
        float: srgb representation
    """
    if c < 0.0031308:
        srgb = 0.0 if c < 0.0 else c * 12.92
    else:
        srgb = 1.055 * math.pow(c, 1.0 / 2.4) - 0.055
    return max(min(int(srgb * 255 + 0.5), 255), 0) / 255

