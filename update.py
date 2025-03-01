#!/usr/bin/env python

"""Update CloudFlare DNS entries to point at your current public IP"""

import argparse
import json
import logging
import os
import socket
import stat
import sys

import requests


def get_public_ip():
    """Return your current public IP address"""
    response = requests.get('https://api.ipify.org/', timeout=15)
    response.raise_for_status()
    return response.text.strip()

def update_record(token, zone_id, record):
    """Update a DNS record"""

    response = requests.put(
        f'https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{record["id"]}',
        headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'},
        data=json.dumps(record),
        timeout=15
    )
    response.raise_for_status()
    return response.json().get('success')

def get_a_record_details(token, zone_id, name):
    """Get current DNS A record details"""

    response = requests.get(
        f'https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/?name={name}&type=A',
        headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'},
        timeout=15
    )
    response.raise_for_status()
    if response.status_code == 200 and response.json().get('success'):
        return response.json()['result'][0]
    return None

def get_zone_id(token, zone_name):
    """Get the 32 character zone identifier for a given zone"""

    response = requests.get(
        f'https://api.cloudflare.com/client/v4/zones?name={zone_name}',
        headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'},
        timeout=15
    )
    response.raise_for_status()
    if response.status_code == 200 and response.json().get('success'):
        return response.json()['result'][0]['id']
    return None

def ask_for_config():
    """Prompt for configuration details"""

    token = input('Auth token: ')
    zone = input('Zone name: ')
    try:
        zone_id = get_zone_id(token, zone)
    except requests.exceptions.HTTPError:
        logging.error('Invalid token')
        sys.exit(1)
    except IndexError:
        logging.error('Unable to find zone "%s"', zone)
        sys.exit(2)

    record = input('A record name: ')
    try:
        get_a_record_details(token, zone_id, record)
    except IndexError:
        logging.error('Invalid or missing A record "%s"', record)
        sys.exit(3)
    return {'token': token, 'zone': zone, 'record': record}

def save_config(config, path):
    """Save config values to a file for future use"""
    try:
        with open(path, 'w', encoding='utf-8') as config_data:
            config_data.write(json.dumps(config, indent=2))
        # Note: file permissions will be ignored on windows
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    except IOError:
        logging.error('Failed to create: %s', path)

def get_config(config_path):
    """Load or prompt for configuration"""
    try:
        with open(config_path, 'r', encoding='utf-8') as config_data:
            config = json.load(config_data)
    except IOError:
        logging.debug('Config file missing: %s', config_path)
        config = ask_for_config()
        logging.info('Saving new config to %s', config_path)
        save_config(config, config_path)
    return config


def check_and_update(target_ip, record, zone, token):
    """Check and if required update a CloudFlare A record"""
    current_ip = socket.gethostbyname(record)
    logging.debug('%s currently points to %s', record, current_ip)
    if current_ip == target_ip:
        logging.info('%s already points to %s, nothing to do', record, target_ip)
        return

    logging.debug('Fetching Zone ID for %s', zone)
    zone_id = get_zone_id(token, zone)
    logging.debug('Zone ID: %s', zone_id)
    logging.debug('Fetching record details for %s', record)
    record_details = get_a_record_details(token, zone_id, record)
    logging.debug('Record ID: %s', record_details['id'])
    del record_details['created_on']
    del record_details['modified_on']
    record_details['content'] = target_ip
    logging.debug('Updating %s to point to %s', record, target_ip)
    if update_record(token, zone_id, record_details):
        logging.info('Updated %s (%s)', record, target_ip)
    else:
        logging.warning('Failed to update %s', record)


def do_updates(config):
    """Update DNS A record(s) based on current public IP address"""
    public_ip = get_public_ip()
    logging.debug('Public ip is: %s', public_ip)

    if 'records' in config:
        for entry in config['records']:
            check_and_update(public_ip, entry['record'], entry['zone'], config['token'])
    else:
        check_and_update(public_ip, config['record'], config['zone'], config['token'])


def main():
    """Parse args and do check/update"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('--config', dest='config', action='store', type=str,
                        default='cloudflare-dynamic-dns.json',
                        help='Config file with token and target record info')
    args = parser.parse_args()

    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
            format='%(asctime)s %(levelname)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            level=log_level)

    config = get_config(args.config)
    do_updates(config)

if __name__ == '__main__':
    main()
