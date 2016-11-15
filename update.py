#!/usr/bin/env python

"""Update a Cloudflare DNS entry to point at your current public IP"""

import json
import logging
import os
import socket
import stat
import sys

import requests


CONFIG_FILE = 'cloudflare-dynamic-dns.json'

def get_public_ip():
    """Return your current public IP address"""
    response = requests.get('https://api.ipify.org/')
    response.raise_for_status()
    return response.text.strip()

def update_record(key, email, record):
    """Update a DNS record"""
    url = 'https://api.cloudflare.com/client/v4/zones/%s/dns_records/%s' \
            % (record['zone_id'], record['id'])
    response = requests.put(url, headers={'Content-Type': 'application/json',
                                          'X-Auth-Email': email,
                                          'X-Auth-Key': key},
                            data=json.dumps(record))
    response.raise_for_status()
    return response.json().get('success')

def get_a_record_details(key, email, zone_id, name):
    """Get current DNS A record details"""
    url = 'https://api.cloudflare.com/client/v4/zones/%s/dns_records/?name=%s&type=A' \
            % (zone_id, name)
    response = requests.get(url, headers={'Content-Type': 'application/json',
                                          'X-Auth-Email': email,
                                          'X-Auth-Key': key})
    response.raise_for_status()
    if response.status_code == 200 and response.json().get('success'):
        return response.json()['result'][0]
    else:
        return None

def get_zone_id(key, email, zone_name):
    """Get the 32 character zone identifier for a given zone"""
    url = 'https://api.cloudflare.com/client/v4/zones?name=%s' % zone_name
    response = requests.get(url, headers={'Content-Type': 'application/json',
                                          'X-Auth-Email': email,
                                          'X-Auth-Key': key})
    response.raise_for_status()
    if response.status_code == 200 and response.json().get('success'):
        return response.json()['result'][0]['id']
    else:
        return None

def ask_for_config():
    """Prompt for configuration details"""
    email = input('CloudFlare registered email: ')
    key = input('Auth key: ')
    zone = input('Zone name: ')
    record = input('A record name: ')
    assert isinstance(email, str) and isinstance(key, str) \
            and isinstance(zone, str) and isinstance(record, str)
    return {'email': email, 'key': key, 'zone': zone, 'record': record}

def save_config(config, path):
    """Save config values to a file for future use"""
    try:
        with open(path, 'w') as config_data:
            config_data.write(json.dumps(config, indent=2))
        # Note: file permissions will be ignored on windows
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    except IOError:
        logging.error('Failed to create: %s', path)

def get_config():
    """Load or prompt for configuration"""
    config_path = os.path.join(os.path.dirname(sys.argv[0]), CONFIG_FILE)
    try:
        with open(config_path, 'r') as config_data:
            config = json.load(config_data)
    except IOError:
        logging.debug('Config file missing: %s', config_path)
        config = ask_for_config()
        logging.info('Saving new config to %s', config_path)
        save_config(config, config_path)
    return config

def main():
    """Update DNS A record based on current public IP address"""
    public_ip = get_public_ip()
    logging.debug('Public ip is: %s', public_ip)
    config = get_config()
    current_ip = socket.gethostbyname(config['record'])
    logging.debug('%s currently points to %s', config['record'], current_ip)
    if current_ip == public_ip:
        logging.info('%s already points to %s, nothing to do', config['record'], public_ip)
        return

    logging.debug('Fetching Zone ID for %s', config['zone'])
    zone_id = get_zone_id(config['key'], config['email'], config['zone'])
    logging.debug('Zone ID: %s', zone_id)
    logging.debug('Fetching record details for %s', config['record'])
    record = get_a_record_details(config['key'], config['email'], zone_id, config['record'])
    logging.debug('Record ID: %s', record['id'])
    del record['created_on']
    del record['modified_on']
    record['content'] = public_ip
    logging.debug('Updating %s to point to %s', config['record'], public_ip)
    if update_record(config['key'], config['email'], record):
        logging.info('Updated %s (%s)', config['record'], public_ip)
    else:
        logging.warning('Failed to update %s', config['record'])

# Treat input like raw_input in python 2.x
try:
    # pylint: disable=redefined-builtin, invalid-name
    input = raw_input
    # pylint: enable=redefined-builtin, invalid-name
except NameError:
    pass

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("requests").setLevel(logging.WARNING)
    main()
