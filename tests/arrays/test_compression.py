from __future__ import annotations

import io
from typing import TYPE_CHECKING, Any

import numpy as np
from hypothesis import given
from hypothesis.extra import numpy as numpy_strategies

from package_utils.arrays import compress_array, decompress_array

if TYPE_CHECKING:
    from numpy.typing import NDArray

dtypes = (
    numpy_strategies.integer_dtypes()
    | numpy_strategies.unsigned_integer_dtypes()
    | numpy_strategies.floating_dtypes()
)
arrays = numpy_strategies.arrays(dtype=dtypes, shape=numpy_strategies.array_shapes())


@given(array=arrays)
def test_roundtrip_preserves_array(array: NDArray[Any]) -> None:
    restored = decompress_array(compress_array(array))
    assert restored.dtype == array.dtype
    assert restored.shape == array.shape
    np.testing.assert_array_equal(restored, array)


def test_beats_uncompressed_storage() -> None:
    embeddings = np.cumsum(
        np.random.default_rng(0).standard_normal((256, 768)).astype(np.float32),
        axis=1,
    )
    buffer = io.BytesIO()
    np.save(buffer, embeddings)
    assert len(compress_array(embeddings)) < len(buffer.getvalue())
