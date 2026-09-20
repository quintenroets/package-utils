from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

import blosc2

if TYPE_CHECKING:
    from numpy.typing import NDArray

COMPRESSION_PARAMS = {
    "codec": blosc2.Codec.ZSTD,
    "filters": [blosc2.Filter.BITSHUFFLE],
    "clevel": 5,
}
"""Zstandard with a bitshuffle prefilter, the sweet spot for numerical arrays.

The bitshuffle filter regroups the bytes of each element so the correlated
high-order bytes of nearby values cluster into long runs before the entropy
coder sees them. A plain deflate codec (`np.savez_compressed`, zip) has no such
filter and leaves most of that redundancy on the table for float arrays.
"""


def compress_array(value: NDArray[Any]) -> bytes:
    return cast("bytes", blosc2.pack_tensor(value, cparams=COMPRESSION_PARAMS))


def decompress_array(value: bytes) -> NDArray[Any]:
    return cast("NDArray[Any]", blosc2.unpack_tensor(value))
