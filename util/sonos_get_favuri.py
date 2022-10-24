from soco import SoCo

import argparse
import sys
from soco import SoCo

sys.path.insert(1, './')
from util.helpers import load_jukebox_config

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('-c', '--config_file', action='store', dest='config_file')
    args = ap.parse_args()
    config_file = args.config_file
    if config_file:
        config = load_jukebox_config(config_file)
    else:
        config = load_jukebox_config()

    sonos_ip = config['sonos_ip']
    sonos_controller = SoCo(sonos_ip)

    sonos_fav = sonos_controller.music_library.get_sonos_favorites()
    for fav in sonos_fav:
        fref = fav.reference
        ft = fref.title
        try:
            fu = fref.get_uri()
        except IndexError:
            continue
        print(f'{ft} -- {fu}')
