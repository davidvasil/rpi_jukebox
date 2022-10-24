import argparse
import sys
import time

from soco import SoCo
from tendo import singleton
from typing import Dict
from util.defaults import (CONFIG_PATH, PROG_NAME)
from util.helpers import (GracefulKiller, load_jukebox_config, load_rfid_csv,
                          setup_logging)
import RPi.GPIO as GPIO  # type: ignore

from pn532 import *


# connect to sonos and play requested item
def process_jukebox_request(config: Dict, sonos_uri: str) -> None:
    ''' play the requested sonos URI on the system specified within
        the config
        
    :param config: Configuration options
    :type config: Dict
    :param sonos_uri: URI to play
    :type sonos_uri: String
    :return: None
    :rtype: None
    '''
    try:
        sonos_vol = config['sonos_vol']
        sonos_controller = SoCo(config['sonos_ip'])
        sonos_controller.play_mode = 'NORMAL'
        if sonos_uri.split(':')[0] == 'x-SONOSFAV':
            fav_name = ':'.join(sonos_uri.split(':')[2:])
            fav_opts = sonos_uri.split(':')[1].split(',')
            fav_list = sonos_controller.music_library.get_sonos_favorites()
            fav_ref = None
            for fav in fav_list:
                if fav.reference.title == fav_name:
                    fav_ref = fav.reference
                    break
            if fav_ref is None:
                logger.info(f'No favorite to play found matching {fav_name}')
                return None
            else:
                sonos_controller.unjoin()
                sonos_controller.clear_queue()
                sonos_controller.add_to_queue(fav_ref)
                # Shuffle favorites
                if 'SHUF' in fav_opts:
                    sonos_controller.shuffle = True
                fav_vol = next((x for x in fav_opts if x.startswith('VOL')), \
                    None)
                if fav_vol is not None:
                    try:
                        sonos_vol = int(fav_vol.lstrip('VOL'))
                    except:
                        logger.warn(f'Failed to set volume by fav {fav_vol}.')
        else:
            # force unjoin before clearing queue fixes below exception
            # Caught Exception: The method or property "clear_queue" can
            # only be called/used on the coordinator in a group
            sonos_controller.unjoin()
            sonos_controller.clear_queue()
            sonos_controller.add_uri_to_queue(uri=sonos_uri)
    except Exception as e:
        raise Exception(e)

    sonos_controller.ramp_to_volume(sonos_vol, ramp_type='AUTOPLAY_RAMP_TYPE')
    sonos_controller.play_from_queue(index=0)
    # sleep for a bit so that we do not spam the sonos_controller with play
    # requests
    time.sleep(config['debounce_time'])

    return None

# initialize rfid reader and listen for cards
if __name__ == '__main__':
    killer = GracefulKiller()
    ap = argparse.ArgumentParser()
    ap.add_argument('-c', '--config_file', action='store', dest='config_file',
                    default=CONFIG_PATH)
    args = ap.parse_args()
    config_file = args.config_file
    config = load_jukebox_config(config_file)
    logger = setup_logging(config['log_host'], config['log_port'])

    logger.info(f'Starting {PROG_NAME}')
    try:
        runner = singleton.SingleInstance()
    except:
        logger.error(f'An instance of {PROG_NAME} is already running')
        sys.exit(-1)

    try:
        jukebox = load_rfid_csv(config['jukebox_file'])
    except OSError:
        logger.error(f'Unable to load jukebox file {config["jukebox_file"]}.')
    
    try:
        # use I2C to communicate with the NFC reader
        pn532 = PN532_I2C(debug=False, reset=20, req=16)
        ic, ver, rev, support = pn532.get_firmware_version()
        logger.info(f'Found PN532 with firmware version: {ver}.{rev}')

        # Configure PN532 to communicate with MiFare cards
        pn532.SAM_configuration()

        logger.info('Waiting for jukebox requests...')
        while not killer.kill_now:
            # Check if a card is available to read
            # TODO gracefully handle exception:
            #   Caught Exception: Did not receive expected ACK from PN532!
            try:
                uid = pn532.read_passive_target(timeout=0.5)
            except RuntimeError as e:
                logger.error('Caught runtime error while waiting to read from '
                             f'PN532: {e}')
                continue

            # Try again if no card is available.
            if uid is None:
                time.sleep(0.1)
                continue

            uidhex = uid.hex()
            if uidhex in jukebox:
                song_desc = jukebox[uidhex]['media_desc']
                logger.info(f'Received request for "{song_desc}" '
                            f'via card UID: {uidhex}')
                process_jukebox_request(config, jukebox[uidhex]['sonos_uri'])
            else:
                # if we see a card that is not in the map file, print it to the
                # log so it can be added later
                logger.info(f'Unregistered card UID: {uidhex}')
                time.sleep(1)
        logger.warning('Caught signal to terminate...')
    except Exception as e:
        logger.error(f'Caught exception: {e}')
    finally:
        logger.info(f'Cleaning up and exiting {PROG_NAME}')
        GPIO.cleanup()
