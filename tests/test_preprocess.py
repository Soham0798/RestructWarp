import random

import cv2
import numpy as np
import pytest

from app.services.vision import preprocess
from tests.test_synth import synth


@pytest.fixture(scope="module")
def sketch():
    return synth.make_sketch(random.Random(5)).img


def test_rejects_non_images():
    with pytest.raises(ValueError):
        preprocess.load_image(b"definitely not a png")


def test_large_photos_are_shrunk():
    big = np.full((4000, 3000, 3), 255, np.uint8)
    img, scale = preprocess.resize(big)
    assert max(img.shape[:2]) == preprocess.MAX_SIDE
    assert scale == pytest.approx(0.4)


def test_shadow_is_removed(sketch):
    h, w = sketch.shape[:2]
    shadow = np.tile(np.linspace(0.55, 1.0, w), (h, 1))[..., None]
    dark = (sketch * shadow).astype(np.uint8)
    paper = lambda img: cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)[:, :40]  # left strip: mostly paper
    assert paper(preprocess.remove_shadows(dark)).mean() > paper(dark).mean() + 40


def test_straight_sketches_are_not_rotated():
    rng = random.Random(42)
    angles = [preprocess.clean(synth.make_sketch(rng).img).angle for _ in range(20)]
    assert angles.count(0.0) >= 19  # diagonals in images/arrows must not fool the deskew


@pytest.mark.parametrize("tilt", [-6.0, 4.0])
def test_tilted_photo_is_straightened(sketch, tilt):
    tilted = preprocess.rotate(sketch, -tilt)
    result = preprocess.clean(tilted)
    assert result.angle == pytest.approx(tilt, abs=1.0)
