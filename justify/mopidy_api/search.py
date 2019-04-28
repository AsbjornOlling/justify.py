
# std lib
from itertools import chain
from typing import List

# deps
from loguru import logger

# app imports
from .jsonrpc import mopidy_post
from .types import (
    deserialize_mopidy,
    printable_tracks,
    Track,
    SearchResult
)


def search_tracks(**kwargs) -> List[Track]:
    """ Call the mopidy search function.
    Kwargs could be one of:
        - artist="death grips"
        - song="get got"
        - any="Sound of Silver"
    """
    logger.info(f"Searching for {str(kwargs)}")

    # get results from mopidy api
    sresult: List[dict] = mopidy_post('core.library.search', **kwargs)

    # deserialize into tree of named tuples
    results: List[SearchResult] = deserialize_mopidy(sresult)

    # concatenate lists of tracks
    if results:
        tracks = chain(*[r.tracks for r in results if r.tracks is not None])
    else:
        return []

    # make printable (format everything to strings)
    ptracks = printable_tracks(tracks)
    return ptracks
