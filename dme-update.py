#!/usr/bin/env python3

import hmac
import hashlib
import json
import os
import os.path
import requests
import telegram
from time import strftime, gmtime, localtime

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

IPCACHE = "/config/ip.cache.txt"


# --- Globals ---
httpDateString = '%a, %d %b %Y %H:%M:%S GMT'
# Breakup passed list of records, strip any spaces
# Setup dict to be populated to map recordName
# DME's record ID value.
myRecords = dict.fromkeys([record.strip() for record in RECORDS.split(',')], 'id')  # noqa E501


def getCurrentIP(ipURL):
    return requests.get(ipURL).text.rstrip('\n')


def writeLogEntry(message, status):
    print(strftime("[%d %b %Y %H:%M:%S %Z]",
          localtime()) + " {}: {}".format(message, status))


def sendNotification(msg, chat_id, token):
    bot = telegram.Bot(token=token)
    bot.sendMessage(chat_id=chat_id, text=msg)
    writeLogEntry("Telegram Group Message Sent", "")


def createHmac(msg, key):
    key = bytes(key, 'UTF-8')
    msg = bytes(msg, 'UTF-8')
    digester = hmac.new(key, msg, hashlib.sha1)
    return digester.hexdigest()


def createDmeHeaders(apiKey, secretKey):
    nowStr = strftime(httpDateString, gmtime())
    headers = {
        'Content-Type': 'application/json',
        'X-dnsme-apiKey': apiKey,
        'X-dnsme-hmac': createHmac(nowStr, secretKey), # noqa E501
        'X-dnsme-requestDate': nowStr
    }
    return headers


def createDmeGetReq(url, apiKey, secretKey):
    headers = createDmeHeaders(apiKey, secretKey)
    # print("Debug: headers=={}".format(headers))
    return requests.get(url, headers=headers)


def getDmeRecordID(zoneID, recordName, apiKey, secretKey):
    url = "".join(
        ('https://api.dnsmadeeasy.com/V2.0/dns/managed/',
         zoneID,
         '/records?recordName=',
         recordName)
    )
    # print("Debug: URL=={}".format(url))
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
    # print("Debug: URL=={}".format(url))
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


for recordName, id in myRecords.items():
    myRecords[recordName] = getDmeRecordID(DMEZONEID, recordName, APIKEY, SECRETKEY)  # noqa E501

myIP = getCurrentIP(IPADDR_SRC)

for record in myRecords.items():
    r = updateDmeRecord(DMEZONEID, record, myIP, APIKEY, SECRETKEY)
    print("Debug: {}".format(r.text))
