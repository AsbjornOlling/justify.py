"""
Reads an validates configuration variables,
either from environment variables, a (WIP) config file,
or from a default, defined in this module's CONFVARS dict.
TODO: prefix env vars with JUSTIFY_
"""

# std lib
from os import getenv

# deps
from loguru import logger


def _validate_REDIS_HOST(REDIS_HOST: str):
    """ Validator for REDIS_HOST """
    noneerr = f"REDIS_HOST not set."
    assert REDIS_HOST is not None, noneerr

    formerr = f"REDIS_HOST must be in format <host>:<port> Got: {REDIS_HOST}"
    assert ':' in REDIS_HOST, formerr

    try:  # check portnum
        port = int(REDIS_HOST.split(':')[-1])
        assert port <= 2**16, "REDIS_HOST: {port} is an invalid port number"
    except ValueError:
        raise AssertionError(formerr)


def _validate_SECRET_KEY(SECRET_KEY):
    """ Warn if user hasn't set a key (used for cookie signing). """
    errmsg = (
        "SECRET_KEY not set. Will use default key for cookie signing."
        " You should fix this by setting the SECRET_KEY config option,"
        " if you care about users tampering with your session cookies."
    )
    assert SECRET_KEY is not None, errmsg


def _validate_MOPIDY_HOST(MOPIDY_HOST: str):
    """ Format of MOPIDY_HOST string. """
    assert MOPIDY_HOST is not None, "MOPIDY_HOST not set."

    # check format
    formerr = "MOPIDY_HOST should be in format: 'host:port'"
    assert len(MOPIDY_HOST.split(':')) == 2, formerr


CONFVARS = {
    'REDIS_HOST':     ('localhost:6379', _validate_REDIS_HOST),
    'SECRET_KEY':     ('changeme-you-fool', _validate_SECRET_KEY),
    'MOPIDY_HOST':    ('localhost:6680', _validate_MOPIDY_HOST)
}


def read_env() -> dict:
    """ Read tracked environment variables into dict """
    logger.info("Reading environment variables...")
    return {k: getenv(k) for k in CONFVARS.keys()}


def read_configfile() -> dict:
    """ TODO: Read config file into dict."""
    logger.info("(Not) Reading config file...")
    return {}


def load_config() -> dict:
    """ Read configurations from
    environment varibles and from config file.
    Then validate it all, defaulting if necessary.
    """
    # read confs
    logger.info("Reading configuration...")
    envconf: dict = read_env()
    # fileconf: dict = read_configfile()

    # let file overwrite env
    # readconf = {**envconf, **fileconf}
    readconf = {**envconf}
    assert isinstance(readconf, dict)

    # validate
    finalconf = {}
    for k in CONFVARS.keys():
        # read default value and validator function
        default, validator = CONFVARS[k]

        try:  # validate
            logger.debug(f"Validating {k}...")
            validator(readconf[k])
            finalconf[k] = readconf[k]
        except AssertionError as e:
            errmsg = f"When configuring {k}: {e}"
            defmsg = f"Defaulting to {k}={default}"
            logger.warning(errmsg)
            logger.info(defmsg)
            # use default value from CONFVARS
            finalconf[k] = default
        except Exception as e:
            logger.error(f"Something happened: {e}")

    logger.info("Finished reading configuration.")
    return finalconf
