""" Maintains a connection to mopidy
Encpasulates the mopidy object.
TODO: handle tracks added from another front-end
TODO: handle connecting to mopidy with non-empty playlist
"""

# deps
from mopidyapi import MopidyAPI
from loguru import logger
from flask import current_app as app
from typing import List, Set

# app imports
from .users import clear_uservotes
from .votelist import (
    remove_from_votelist,
    get_votelist,
    vote
)

# MopidyAPI
# provides functions and event listeners
# defaults to connecting to localhost
try:
    # get address and port from config
    mphost, mpport = app.config['MOPIDY_HOST'].split(':')
    mp = MopidyAPI(host=mphost, port=int(mpport), logger=logger)
except ConnectionError:
    logger.error("Fatal error: could not establish connection to Mopidy."
                 " Are you sure Mopidy is running and accessible?")
    quit(1)


@mp.on_event('track_playback_ended')
def track_playback_ended(event):
    """ Removes track from votelist and records of user votes,
    when mopidy finishes playing it.
    """
    logger.debug(f"Track playback ended: {event.track.name}")
    remove_from_votelist(event.track.uri)
    clear_uservotes(event.track.uri)


@mp.on_event('tracklist_changed')
def tracklist_changed(event):
    logger.debug(f"Trackist changed: {event}")
    # app context needed to get redis obj
    # set explicitly, b/c this is called from thread
    with app.app_context():
        sync_votelist()
        sort_mopidy()


def sync_votelist():
    """ Checks for discrepencies between votelist,
    and the current Mopidy tracklist.
    Modifies votelist to match Mopidy if necessary.
    """
    vlist: Set[str] = set(get_votelist(withscores=False))
    tlist: Set[str] = {str(t.uri) for t in mp.tracklist.get_tracks()}

    vlistonly: Set[str] = vlist - tlist
    for songuri in vlistonly:
        logger.warning(f"Removing orphaned song: {songuri}")
        remove_from_votelist(songuri)
        clear_uservotes(songuri)

    tlistonly: Set[str] = tlist - vlist
    for songuri in tlistonly:
        logger.warning(f"Adding unknown song to votelist: {songuri}")
        vote(songuri)


def sort_mopidy():
    """ Ensure that the Mopidy playlist is ordered
    according to the Justify-controlled votelist.
    This could involve quite a lot of mopidy calls.
    """
    logger.debug("Sorting Mopidy...")

    # list of TlTracks in current mopidy tracklist
    # (leave currently playing track in place)
    tls = mp.tracklist.get_tl_tracks()[1:]

    # list of uris sorted by no of votes
    vlist: List[str] = get_votelist()

    # loop through tracks in vote order ([1:] skips currently plying)
    for dst, songuri in enumerate(vlist)[1:]:
        # get TlTrack that matches uri
        tltrack = next(tl for tl in tls if tl.track.uri == songuri)
        tlpos = mp.tracklist.index(tl_track=tltrack)

        if tlpos != dst:
            # move track to destination spot on tracklist
            logger.debug(f"Moving track {songuri} to {dst}")
            mp.tracklist.move(tlpos, tlpos+1, dst)

    # check final ordering from mopidy
    finalorder = [str(t.uri) for t in mp.tracklist.get_tracks()]
    if finalorder != vlist:
        # run again, if order is bad
        # (likely because something happened while it was sorting)
        logger.warning("Running sort again, b/c result wasn't as expected.")
        sort_mopidy()
