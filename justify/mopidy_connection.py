""" Maintains a connection to mopidy
encpasulates the mopidy object.
"""

# deps
from typing import List, Set
from mopidyapi import MopidyAPI
from loguru import logger
from flask import current_app as app

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
    MPHOST, MPPORT = app.config['MOPIDY_HOST'].split(':')
    mp = MopidyAPI(host=MPHOST, port=int(MPPORT),
                   logger=logger, flask_object=app)
except ConnectionError:
    logger.error("Fatal error: could not establish connection to Mopidy."
                 " Are you sure Mopidy is running and accessible?")
    quit(1)


@mp.on_event('track_playback_ended')
def track_playback_ended(event):
    """ Removes track from votelist and records of user votes,
    when mopidy finishes playing it.
    """
    logger.debug(f"Track playback ended: {event}")
    remove_from_votelist(event.tl_track.track.uri)
    clear_uservotes(event.tl_track.track.uri)


@mp.on_event('options_changed')
def fix_mopidy_options(event):
    """ Sets the necessary playback options in Mopidy.
    Since setting an option triggers the 'options_changed'
    event, we have to check the option first, to avoid an
    infinite loop.
    To avoid doing a lot of duplicate checks (because of the event trigger)
    the function terminates after setting just one option.
    """
    # remove track from playlist after playing
    if mp.tracklist.get_consume() is not True:
        mp.tracklist.set_consume(True)
        return

    # obviously shuffle won't make sense
    if mp.tracklist.get_random() is not False:
        mp.tracklist.set_random(False)
        return

    # dont loop tracks
    if mp.tracklist.get_repeat() is not False:
        mp.tracklist.set_repeat(False)
        return

    # dont stop playing after each track
    if mp.tracklist.get_single() is not False:
        mp.tracklist.set_single(False)
        return


def remove_tracks(uris: List[str]):
    """ Removes track from Mopidy, and from justify.
    This function should be used in place of
    mp.tracklist.remove() - to avoid weird conflicting states.
    """
    # remove from mopidy
    mp.tracklist.remove({'uri': uris})
    for uri in uris:
        # remove from justify
        clear_uservotes(uri)
        remove_from_votelist(uri)


def sync_state():
    """ 1. Remove all tracks before the currently playing track
        2. Ensure votelist and Mopidy tracklist contain only the same tracks.
        3. Sort tracklist based on votes.
    This function is called on every vote,
    (TODO should probably be called on some other mopidy event).
    """
    logger.info("Running Mopidy state sync.")
    force_play()
    remove_before_current()
    sync_votelist()
    sort_mopidy()


def force_play():
    """ If mopidy isn't playing, make it play.
    TODO: this is broken in Mopidy 2.2.2 on Arch.
    """
    state = mp.playback.get_state()
    if state.lower() != 'playing':
        logger.debug(f"Playing state was {state}. Playing...")
        mp.playback.set_state('playing')
    else:
        logger.debug(f"Playback state was {state}. Leaving be.")


def remove_before_current():
    """ Remove all tracks before the currentlly
    playing track from Mopidy.
    This ensures that the currently playing track
    is always track 0, without changing playback.
    """
    tltracks = mp.tracklist.get_tl_tracks()
    if len(tltracks) == 0:
        logger.debug("Tracklist empty. Aborting track removals.")
        return

    # index of currently playing track
    current = tltracks[0]
    curridx = mp.tracklist.index(tlid=current.tlid)

    # remove tracks if necessary
    if curridx != 0:
        logger.warning(f"Current track is at idx: {curridx}"
                       "Removing all tracks before it.")
        tracks = mp.tracklist.get_tracks()
        remuris = [t.uri for t in tracks[:curridx]]
        logger.debug(f"Removing tracks: {remuris}")
        remove_tracks(remuris)


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
    This could involve quite a lot of Mopidy calls.
    XXX: this is likely not the most clean / efficient
         implementation possible.
    """
    logger.debug("Sorting Mopidy...")

    vlist: List[str] = get_votelist()            # list of uris in vote order
    tllist: list = mp.tracklist.get_tl_tracks()  # TlTracks in playlist order
    if len(tllist) == 0:
        logger.debug("No tracks in tracklist. Aborting sort.")
        return

    # remove currently playing track from both lists
    vlist.remove(tllist[0].track.uri)
    del tllist[0]

    # sort TlTracks in desc. vote order (desired state)
    tlsorted = sorted(tllist, reverse=True,
                      key=lambda t: vlist.index(t.track.uri))

    if [str(t.track.uri) for t in tllist] == vlist:
        # abort if no change in order
        logger.debug("Songs already in order. Aborting sort.")
        return

    # move all tracks into place (except currently playing)
    for dst, tltrack in enumerate(tlsorted, start=1):
        src = mp.tracklist.index(tl_track=tltrack)
        if src != dst:
            # move track to destination spot on tracklist
            logger.debug(f"Moving track {tltrack.track.uri} to {dst}.")
            mp.tracklist.move(src, src+1, dst)

    # check resulting mopidy order
    finalorder = [str(t.uri) for t in mp.tracklist.get_tracks()]
    if finalorder != vlist:
        # run again, if sort failed
        logger.error("Sort result seems unsuccessful. Not running again tho.")
        logger.debug(f"Final: {finalorder}")
        logger.debug(f"Vlist: {vlist}")
