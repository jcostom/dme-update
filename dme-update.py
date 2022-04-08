#!/usr/bin/env python3

import hmac
import hashlib
import json
import logging
import os
import os.path
import requests
import telegram
from time import strftime, gmtime, localtime, sleep

# --- To be passed in to container ---
IPADDR_SRC = os.getenv('IPADDR_SRC', 'https://ipv4.icanhazip.com/')
INTERVAL = os.getenv('INTERVAL', 300)
APIKEY = os.getenv('APIKEY')
SECRETKEY = os.getenv('SECRETKEY')
DMEZONEID = str(os.getenv('DMEZONEID'))
RECORDS = os.getenv('RECORDS')
TTL = os.getenv('TTL', 1800)
USETELEGRAM = os.getenv('USETELEGRAM', 0)
CHATID = int(os.getenv('CHATID', 0))
MYTOKEN = os.getenv('MYTOKEN', 'none')
SITENAME = os.getenv('SITENAME', 'mysite')
DEBUG = int(os.getenv('DEBUG', 0))

# --- Globals ---
httpDateString = '%a, %d %b %Y %H:%M:%S GMT'
# Breakup passed list of records, strip any spaces
# Setup dict to be populated to map recordName
# DME's record ID value.
myRecords = dict.fromkeys([record.strip() for record in RECORDS.split(',')], 'id')  # noqa E501
VER = '1.0.1'
USER_AGENT = "/".join(['dme-update.py', VER])

# Cache Location
IPCACHE = "/config/ip.cache.txt"

logging.basicConfig(format='%(levelname)s %(asctime)s %(message)s', datefmt='[%d %b %Y %H:%M:%S %Z]')


def getCurrentIP(ipURL):
    return requests.get(ipURL).text.rstrip('\n')


def writeLogEntry(message, status):
    print(strftime("[%d %b %Y %H:%M:%S %Z]",
          localtime()) + " {}: {}".format(message, status))


def sendNotification(msg, chat_id, token):
    bot = telegram.Bot(token=token)
    bot.sendMessage(chat_id=chat_id, text=msg)
    # writeLogEntry("Telegram Group Message Sent", "")
    logging.info('Telegram Group Message Sent')


def createHmac(msg, key):
    key = bytes(key, 'UTF-8')
    msg = bytes(msg, 'UTF-8')
    digester = hmac.new(key, msg, hashlib.sha1)
    return digester.hexdigest()


def createDmeHeaders(apiKey, secretKey):
    nowStr = strftime(httpDateString, gmtime())
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': USER_AGENT,
        'X-dnsme-apiKey': apiKey,
        'X-dnsme-hmac': createHmac(nowStr, secretKey),
        'X-dnsme-requestDate': nowStr
    }
    return headers


def createDmeGetReq(url, apiKey, secretKey):
    headers = createDmeHeaders(apiKey, secretKey)
    return requests.get(url, headers=headers)


def getDmeDomainName(zoneID, apiKey, secretKey):
    url = "".join(('https://api.dnsmadeeasy.com/V2.0/dns/managed/', zoneID))
    r = createDmeGetReq(url, apiKey, secretKey)
    # Locate and return the zone's name
    return r.json()['name']


def getDmeRecordID(zoneID, recordName, apiKey, secretKey):
    url = "".join(
        ('https://api.dnsmadeeasy.com/V2.0/dns/managed/',
         zoneID,
         '/records?recordName=',
         recordName)
    )
    r = createDmeGetReq(url, apiKey, secretKey)
    # Locate and return the record's record ID
    return str(r.json()['data'][0]['id'])


def updateDmeRecord(zoneID, record, ip, apiKey, secretKey):
    url = "".join(
        ('https://api.dnsmadeeasy.com/V2.0/dns/managed/',
         zoneID,
         '/records/',
         record[1])
    )
    body = {
        "name": record[0],
        "type": "A",
        "value": ip,
        "id": record[1],
        "gtdLocation": "DEFAULT",
        "ttl": TTL
    }
    headers = headers = createDmeHeaders(apiKey, secretKey)
    return requests.put(url, headers=headers, data=json.dumps(body))


def ipChanged(ip):
    with open(IPCACHE, "r") as f:
        cachedIP = f.read()
        if cachedIP == ip:
            return False
        else:
            return True


def updateCache(ip):
    with open(IPCACHE, "w+") as f:
        f.write(ip)
    return 0


def doUpdates(zoneID, records, ip, domain, apiKey, secretKey):
    for record in records.items():
        updateDmeRecord(zoneID, record, ip, apiKey, secretKey)
        if USETELEGRAM == "1":
            notificationText = "".join(
                ["[", SITENAME, "] ", record[0],
                 ".", domain, " changed on ",
                 strftime("%B %d, %Y at %H:%M. New IP == "), ip]
            )
            sendNotification(notificationText, CHATID, MYTOKEN)


def main():
    myDomain = getDmeDomainName(DMEZONEID, APIKEY, SECRETKEY)

    # Load dict with record IDs
    for recordName, id in myRecords.items():
        myRecords[recordName] = getDmeRecordID(DMEZONEID, recordName, APIKEY, SECRETKEY)  # noqa E501

    while True:
        # Grab current IP
        myIP = getCurrentIP(IPADDR_SRC)

        # check to see if cache file exists and take action
        if os.path.exists(IPCACHE):
            if ipChanged(myIP):
                updateCache(myIP)
                # writeLogEntry('IP changed to', myIP)
                logging.info('IP changed to %s', myIP)
                # Update DNS & Check Telegram
                doUpdates(DMEZONEID, myRecords, myIP, myDomain, APIKEY, SECRETKEY) # noqa E501
            else:
                # writeLogEntry('No change in IP, no action taken', '')
                logging.info('No change in IP, no action taken')
        else:
            # No cache exists, create file
            updateCache(myIP)
            # writeLogEntry('No cached IP, setting to', myIP)
            logging.info('No cached IP, setting to %s', myIP)
            # Update DNS & Check Telegram
            doUpdates(DMEZONEID, myRecords, myIP, myDomain, APIKEY, SECRETKEY)

        sleep(INTERVAL)


if __name__ == "__main__":
    main()
