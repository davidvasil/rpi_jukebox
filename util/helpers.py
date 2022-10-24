import configparser
import csv
import json
import logging
import logging.handlers
import signal
import sys

from typing import (Dict, Optional)
from util.defaults import (PROG_NAME, CONFIG_PATH)


class GracefulKiller:
    kill_now = False
    def __init__(self):
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)

    def exit_gracefully(self, *args):
        self.kill_now = True


class CustomJsonFormatter(logging.Formatter):
    ''' Custom logging class format for writing JSON formatted logs'''
    def format(self, record: logging.LogRecord) -> str:
        super(CustomJsonFormatter, self).format(record)
        output = {k: str(v) for k, v in record.__dict__.items()}
        return json.dumps(output)


def load_jukebox_config(config_file: Optional[str]=CONFIG_PATH) -> Dict:
    '''  Load the config for the jukebox

    :param config_file: Config file to load
    :type config_file: Str
    :return config: Dictionary of config values
    :rtype: Dict
    '''
    config = {}
    cfg_parser = configparser.RawConfigParser()
    cfg_parser.read(config_file)
    try:
        jukebox_file = cfg_parser.get(PROG_NAME, 'jukebox_file')
        debounce_time = cfg_parser.get(PROG_NAME, 'debounce_time')
        log_host = cfg_parser.get(PROG_NAME, 'log_host')
        log_port = cfg_parser.get(PROG_NAME, 'log_port')
        sonos_ip = cfg_parser.get(PROG_NAME, 'sonos_ip')
        sonos_vol = cfg_parser.get(PROG_NAME, 'sonos_vol')
        config = {'jukebox_file': jukebox_file,
                  'debounce_time': int(debounce_time),
                  'log_host': log_host,
                  'log_port': int(log_port),
                  'sonos_ip': sonos_ip,
                  'sonos_vol': int(sonos_vol)}
    except configparser.NoSectionError:
        raise NameError(f'Could not find {PROG_NAME} in config file '
                        f'{config_file}')
    except configparser.NoOptionError:
        raise NameError('Cound not find a required option in the config file'
                        f' {config_file}')

    return config        


def setup_logging(log_host: str=None, log_port: int=514) -> logging.Logger:
    ''' Set up logging, preferably to a loghost but will
        default to stderr if no host is set
    
    :param log_host: IP address to send syslog to
    :type log_host: str
    :param log_port: port number 
    :type log_port: int
    :return logger: Logging instance
    :rtype: logging.Logger
    '''
    logger = logging.getLogger(PROG_NAME)
    logger.setLevel(logging.DEBUG)

    # syslog handler
    json_formatter = CustomJsonFormatter()
    if log_host is not None:
        log_address = (log_host, log_port)
        syslog_handler = logging.handlers.SysLogHandler(address=log_address)
    else:
        syslog_handler = logging.StreamHandler()
    syslog_handler.setFormatter(json_formatter)
    syslog_handler.setLevel(logging.DEBUG)

    # console handler
    console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.DEBUG)

    logger.addHandler(console_handler)
    logger.addHandler(syslog_handler)

    return logger


# load rfid csv file
def load_rfid_csv(rfid_csv: str=None) -> Dict:
    ''' load the CSV file into a dictionary that specifies the 
        NFC UID and target Sonos URI
        
    :param rfid_csv: File to load
    :type rfid_csv: str
    :return: rfid_lookup
    :rtype: Dict
    '''
    rfid_lookup = {}
    try:
        with open(rfid_csv, 'r') as csvf:
            reader = csv.DictReader(csvf)
            for row in reader:
                rfid_uid = row.get('rfid_uid', None)
                media_desc = row.get('media_desc', None)
                sonos_uri = row.get('sonos_uri', None)
                if rfid_uid not in rfid_lookup:
                    rfid_lookup[rfid_uid] = {
                        'media_desc': media_desc,
                        'sonos_uri': sonos_uri
                    }
    except OSError:
        raise OSError
    
    return rfid_lookup
