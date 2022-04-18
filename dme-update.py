#!/usr/bin/env python3

import hmac
import hashlib
import json
import os
import os.path
import logging
import requests
import telegram
from time import strftime, gmtime, sleep

# --- To be passed in to container ---
IPADDR_SRC = os.getenv('IPADDR_SRC', 'https://ipv4.icanhazip.com/')
INTERVAL = os.getenv('INTERVAL', 300)
APIKEY = os.getenv('APIKEY')
SECRETKEY = os.getenv('SECRETKEY')
DMEZONEID = str(os.getenv('DMEZONEID'))
RECORDS = os.getenv('RECORDS')
TTL = os.getenv('TTL', 1800)
USETELEGRAM = int(os.getenv('USETELEGRAM', 0))
CHATID = int(os.getenv('CHATID', 0))
MYTOKEN = os.getenv('MYTOKEN', 'none')
SITENAME = os.getenv('SITENAME', 'mysite')
DEBUG = int(os.getenv('DEBUG', 0))

# --- Globals ---
HTTP_DATE_STRING = '%a, %d %b %Y %H:%M:%S GMT'
# Breakup passed list of records, strip any spaces
# Setup dict to be populated to map recordName
# DME's record ID value.
my_records = dict.fromkeys([record.strip() for record in RECORDS.split(',')], 'id')  # noqa E501

VER = '1.7'
USER_AGENT = f"dme-update.py{VER}"

# Cache Location
IPCACHE = "/config/ip.cache.txt"

# Setup logger
logger = logging.getLogger()
ch = logging.StreamHandler()
if DEBUG:
    logger.setLevel(logging.DEBUG)
    ch.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)
    ch.setLevel(logging.INFO)

formatter = logging.Formatter('[%(levelname)s] %(asctime)s %(message)s',
                              datefmt='[%d %b %Y %H:%M:%S %Z]')
ch.setFormatter(formatter)
logger.addHandler(ch)


def get_current_ip(ip_url: str) -> str:
    return requests.get(ip_url).text.rstrip('\n')


def send_notification(msg: str, chat_id: int, token: str) -> None:
    bot = telegram.Bot(token=token)
    bot.sendMessage(chat_id=chat_id, text=msg)
    logger.info('Telegram Group Message Sent')


def createHmac(msg: str, key: str) -> str:
    key = bytes(key, 'UTF-8')
    msg = bytes(msg, 'UTF-8')
    digester = hmac.new(key, msg, hashlib.sha1)
    return digester.hexdigest()


def create_dme_headers(api_key: str, secret_key: str) -> dict:
    now_str = strftime(HTTP_DATE_STRING, gmtime())
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': USER_AGENT,
        'X-dnsme-apiKey': api_key,
        'X-dnsme-hmac': createHmac(now_str, secret_key),
        'X-dnsme-requestDate': now_str
    }
    return headers


def create_dme_get_req(url: str, api_key: str,
                       secret_key: str) -> requests.Response:
    headers = create_dme_headers(api_key, secret_key)
    return requests.get(url, headers=headers)


def get_dme_domain_name(zone_id: str, api_key: str, secret_key: str) -> str:
    url = f"https://api.dnsmadeeasy.com/V2.0/dns/managed/{zone_id}"
    r = create_dme_get_req(url, api_key, secret_key)
    # Locate and return the zone's name
    return r.json()['name']


def get_dme_record_id(zone_id: str, record_name: str, api_key: str,
                      secret_key: str) -> str:
    url = f"https://api.dnsmadeeasy.com/V2.0/dns/managed/{zone_id}/records?recordName={record_name}"  # noqa: E501
    r = create_dme_get_req(url, api_key, secret_key)
    # Locate and return the record's record ID
    return str(r.json()['data'][0]['id'])


def update_dme_record(zone_id: str, record: list, ip: str, api_key: str,
                      secret_key: str) -> requests.Response:
    url = f"https://api.dnsmadeeasy.com/V2.0/dns/managed/{zone_id}/records/{record[1]}"  # noqa: E501
    body = {
        "name": record[0],
        "type": "A",
        "value": ip,
        "id": record[1],
        "gtdLocation": "DEFAULT",
        "ttl": TTL
    }
    headers = create_dme_headers(api_key, secret_key)
    return requests.put(url, headers=headers, data=json.dumps(body))


def ip_changed(ip: str) -> bool:
    with open(IPCACHE, "r") as f:
        cached_ip = f.read()
        if cached_ip == ip:
            return False
        else:
            return True


def update_cache(ip: str) -> int:
    with open(IPCACHE, "w+") as f:
        f.write(ip)
    return 0


def send_updates(zone_id: str, records: dict, ip: str, domain: str,
                 api_key: str, secret_key: str) -> None:
    for record in records.items():
        update_dme_record(zone_id, record, ip, api_key, secret_key)
        if USETELEGRAM:
            notification_text = "".join(
                ["[", SITENAME, "] ", record[0],
                 ".", domain, " changed on ",
                 strftime("%B %d, %Y at %H:%M. New IP == "), ip]
            )
            send_notification(notification_text, CHATID, MYTOKEN)


def main():
    my_domain = get_dme_domain_name(DMEZONEID, APIKEY, SECRETKEY)

    # Load dict with record IDs
    for record_name, id in my_records.items():
        my_records[record_name] = get_dme_record_id(DMEZONEID, record_name, APIKEY, SECRETKEY)  # noqa E501

    while True:
        # Grab current IP
        current_ip = get_current_ip(IPADDR_SRC)

        # check to see if cache file exists and take action
        if os.path.exists(IPCACHE):
            if ip_changed(current_ip):
                update_cache(current_ip)
                logger.info(f"IP changed to {current_ip}")
                # Update DNS & Check Telegram
                send_updates(DMEZONEID, my_records, current_ip, my_domain, APIKEY, SECRETKEY)  # noqa E501
            else:
                logger.info('No change in IP, no action taken.')
        else:
            # No cache exists, create file
            update_cache(current_ip)
            logger.info(f"No cached IP, setting to {current_ip}")
            # Update DNS & Check Telegram
            send_updates(DMEZONEID, my_records, current_ip, my_domain, APIKEY, SECRETKEY)  # noqa E501

        sleep(INTERVAL)


if __name__ == "__main__":
    main()
