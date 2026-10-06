import http.server, json, os, urllib.parse, hashlib, datetime, base64, urllib.request, secrets, time, shutil, zipfile, io
BASE   = '/data'
PASS = 'REPLACE_ME'
PORT   = 8181
DEVLOG      = '/data/DEVLOG.md'
UPLOAD_ROOT = '/home/clearcrow/Needpedia_Nexus/master_uploads'
HOME_ROOT   = '/home/clearcrow'
DRIVE_CAP   = 0.80
OR_KEY        = 'REPLACE_ME'

# --- N39c: web research tools (server-side; model decides when to search)
WEB_SYS = {
    'role': 'system',
    'content': ('You have web search, a web page reader, and a clock '
                'available as tools. Use them for anything time-sensitive, '
                'for facts you are not certain of, and whenever you are '
                'asked to research something. Do not search for casual '
                'conversation or questions about yourself. Cite sources as '
                'markdown links.')
}
WEB_TOOLS = [
    {'type': 'openrouter:web_search',
     'parameters': {'engine': 'parallel', 'mode': 'turbo',
                    'max_results': 5, 'max_uses': 3,
                    'max_total_results': 10}},
    {'type': 'openrouter:web_fetch'},
    {'type': 'openrouter:datetime'},
]
# --- end N39c
VOL_KEY = 'REPLACE_ME'

ADMIN_CONVS   = '/home/clearcrow/admin-convs'
ACTIVITY_JSON = '/home/clearcrow/Nexus_private/data/activity.json'
CAPTURE_TOKEN = 'REPLACE_ME'
# In-memory admin tokens: token -> expiry timestamp
_admin_tokens = {}
def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()
def load_volunteers():
    path = os.path.join(BASE, 'volunteers.json')
    try:
        with open(path) as f:
            return json.load(f)
    except:
        return []
def issue_token():
    tok = secrets.token_hex(32)
    _admin_tokens[tok] = time.time() + 86400  # 24 hours
    return tok
def valid_token(tok):
    if not tok or tok not in _admin_tokens:
        return False
    if time.time() > _admin_tokens[tok]:
        del _admin_tokens[tok]
        return False
    return True
STORAGE_CAP = 5 * 1024 * 1024 * 1024
def dir_size(path):
    total = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            try:
                total += os.path.getsize(os.path.join(dirpath, f))
            except:
                pass
    return total

# --- botcouncil (JOHN thread, session John 7, 4 Oct 2026) ---
import re as _bcre
BC_NEXUS  = '/home/clearcrow/Needpedia_Nexus'
BC_PINNED = ['BC']          # always at the top of the thread list, in this order
BC_MARKER = '== ENTRIES BELOW =='
BC_CAP    = 150000          # most characters of any one document sent to the AI

def _bc_read(path):
    try:
        with open(path, encoding='utf-8', errors='replace') as f:
            return f.read()
    except Exception:
        return ''

def _bc_unread(name):
    t = _bc_read(os.path.join(BC_NEXUS, 'public', 'UPDATES-' + name + '.md'))
    return t.split(BC_MARKER, 1)[1].strip() if BC_MARKER in t else ''

def _bc_index():
    try:
        with open(os.path.join(ADMIN_CONVS, 'index.json')) as f:
            return json.load(f)
    except Exception:
        return []

def _bc_threads():
    names = sorted(f[3:-4] for f in os.listdir(BC_NEXUS)
                   if _bcre.fullmatch(r'PA-[A-Z0-9]+\.txt', f))
    idx = _bc_index()
    out = []
    for n in names:
        mine = [x for x in idx if x.get('thread') == n]
        out.append({'name': n, 'sessions': len(mine),
                    'last': max((x.get('updated_at', '') for x in mine), default=''),
                    'unread': len(_bcre.findall(r'^----- added ', _bc_unread(n), _bcre.M)),
                    'pinned': n in BC_PINNED})
    pinned = [t for p in BC_PINNED for t in out if t['name'] == p]
    rest = sorted([t for t in out if not t['pinned']],
                  key=lambda t: (t['sessions'], t['last']), reverse=True)
    return pinned + rest

def _bc_system(name):
    name = str(name or '').upper()
    if not _bcre.fullmatch(r'[A-Z0-9]+', name):
        return None
    pa = _bc_read(os.path.join(BC_NEXUS, 'PA-' + name + '.txt'))
    if not pa:
        return None
    post = _bc_read(os.path.join(BC_NEXUS, 'working-with-tony.txt'))
    if not post:
        post = _bcre.sub(r'<[^>]+>', ' ', _bc_read(os.path.join(BC_NEXUS, 'working-with-tony.html')))
    upd = _bc_unread(name) or '(none)'
    head = lambda s: s if len(s) <= BC_CAP else s[:BC_CAP] + '\n[... the rest is cut]'
    tail = lambda s: s if len(s) <= BC_CAP else '[... the oldest part is cut]\n' + s[-BC_CAP:]
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    text = ('You are the AI for the ' + name + ' thread in Tony Brasher\'s botcouncil system, '
            'a chat window on his Nexus. The documents below were read fresh from his '
            'computer at ' + now + ', so they are current; you do not need to fetch them.\n'
            '1. The botskill post: how to work with Tony. Follow it.\n'
            '2. The ' + name + ' thread\'s prompt accomplice: its standing facts, rules and loose ends.\n'
            '3. Unread updates from other threads for ' + name + '. Read them first and act on them.\n'
            'This window shows code in boxes with a Copy button, and can hand Tony files to download. Code: put it in a fenced block (three backticks). A file: a line ===FILE: name.ext===, then the contents, then a line ===END===; it shows as a Download button and lands in his Downloads folder. '
            'Then give him the terminal command that puts the file where it goes.\n\n'
            '===== 1. BOTSKILL POST =====\n' + head(post) +
            '\n\n===== 2. PROMPT ACCOMPLICE: ' + name + ' =====\n' + tail(pa) +
            '\n\n===== 3. UNREAD UPDATES FOR ' + name + ' =====\n' + tail(upd))
    return {'role': 'system', 'content': text}

def _bc_search(q, mode, limit):
    q = (q or '').strip().lower()
    if not q:
        return []
    terms = [q] if mode == 'phrase' else [w for w in q.split() if w][:12]
    pad = 160 if mode == 'phrase' else 400
    meta = {x.get('id'): x for x in _bc_index()}
    hits = []
    for fn in os.listdir(ADMIN_CONVS):
        if not fn.endswith('.json') or fn == 'index.json':
            continue
        try:
            with open(os.path.join(ADMIN_CONVS, fn)) as f:
                conv = json.load(f)
        except Exception:
            continue
        text = '\n'.join(str(m.get('content', '')) for m in conv.get('messages', []))
        low = text.lower()
        found = [t for t in terms if t in low]
        if not found:
            continue
        snips = []
        for t in found[:3]:
            i = low.find(t)
            a, b = max(0, i - pad), min(len(text), i + len(t) + pad)
            snips.append(('...' if a else '') + ' '.join(text[a:b].split()) + ('...' if b < len(text) else ''))
        cid = conv.get('id', fn[:-5])
        m = meta.get(cid, {})
        hits.append({'id': cid, 'title': conv.get('title', m.get('title', 'Untitled')),
                     'thread': conv.get('thread', m.get('thread', '')),
                     'updated_at': conv.get('updated_at', m.get('updated_at', '')),
                     'score': len(found), 'snippets': snips})
    hits.sort(key=lambda h: (h['score'], h['updated_at']), reverse=True)
    try:
        limit = max(1, min(int(limit), 100))
    except Exception:
        limit = 50
    return hits[:limit]

def _bc_op(action, body):
    if action == 'bc-threads':
        return {'threads': _bc_threads()}
    if action == 'bc-search':
        return {'results': _bc_search(body.get('q', ''), body.get('mode', 'phrase'), body.get('limit', 50))}
    return {'error': 'unknown action: ' + action}
# --- botcouncil council (JOHN thread, session John 8, 5 Oct 2026) ---
# Threads messaging each other. When a thread's AI writes a block
#   ===TO THREADS: ALL===   (or names, like ===TO THREADS: NEXUS, PC===)
#   ...message...
#   ===END===
# the server adds the message to each named thread's updates post, then
# asks each one's AI to read it and reply briefly. Everything is logged in
# ADMIN_CONVS/council/council-log.json, which the chat window shows on
# the right.
import threading as _bcth
BC_COUNCIL_DIR  = os.path.join(ADMIN_CONVS, 'council')
BC_COUNCIL_LOG  = os.path.join(BC_COUNCIL_DIR, 'council-log.json')
BC_COUNCIL_KEEP = 300
BC_MODEL        = 'deepseek/deepseek-v4-pro-0813'
BC_OR_URL       = 'https://openrouter.ai/api/v1/chat/completions'
_bc_lock        = _bcth.Lock()
_BC_BLOCK = _bcre.compile(r'^\s*===\s*TO THREADS?\s*:\s*([^=\n]+?)\s*===[ \t]*\n(.*?)\n\s*===\s*END\s*===',
                          _bcre.M | _bcre.S | _bcre.I)
BC_HOWTO = (
    '\n\n===== 4. TALKING TO OTHER THREADS (botcouncil) =====\n'
    'When Tony asks you to tell, update or message other threads, put the message in a block '
    'like this, each marker on its own line:\n'
    '===TO THREADS: ALL===\n'
    'tags: two or three, plain words, someone would search for\n'
    'From the {NAME} thread (botcouncil). To every thread. {DATE}.\n'
    'The message itself. Write it complete and plain: the reader has not seen this chat.\n'
    '===END===\n'
    'Instead of ALL you can name threads, separated by commas, for example '
    '===TO THREADS: NEXUS, PC=== (then say those names on the From line instead of "every thread").\n'
    'The botcouncil adds the message to each of those threads\' updates posts and asks each '
    'thread\'s AI to read it and reply. Tony watches their replies appear in the thread list on '
    'the right. Write a block only when Tony asks you to, and never repeat one you already sent.\n'
    'Thread names: {THREADS}.')

def _bc_now():
    return datetime.datetime.utcnow().isoformat() + 'Z'

def _bc_log_load():
    try:
        with open(BC_COUNCIL_LOG) as f:
            return json.load(f)
    except Exception:
        return []

def _bc_log_save(items):
    os.makedirs(BC_COUNCIL_DIR, exist_ok=True)
    tmp = BC_COUNCIL_LOG + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(items[-BC_COUNCIL_KEEP:], f, indent=1)
    os.replace(tmp, BC_COUNCIL_LOG)

def _bc_log_update(bid, fn):
    with _bc_lock:
        items = _bc_log_load()
        for b in items:
            if b.get('id') == bid:
                fn(b)
        _bc_log_save(items)

def _bc_post_update(name, text):
    p = os.path.join(BC_NEXUS, 'public', 'UPDATES-' + name + '.md')
    if not os.path.isfile(p):
        return 'no updates post'
    with _bc_lock:
        cur = _bc_read(p)
        if text.strip() in cur:
            return 'already in its updates post'
        add = (('' if cur.endswith('\n') else '\n') + '\n----- added ' +
               datetime.date.today().isoformat() + ' -----\n' + text.strip() + '\n')
        try:
            with open(p, 'a', encoding='utf-8') as f:
                f.write(add)
        except Exception as e:
            return 'could not write its updates post: ' + str(e)[:200]
    return 'posted'

_bc_system_v3 = _bc_system
def _bc_system(name):
    s = _bc_system_v3(name)
    if not s:
        return s
    names = ', '.join(t['name'] for t in _bc_threads())
    s = dict(s)
    s['content'] += (BC_HOWTO.replace('{NAME}', str(name).upper())
                     .replace('{THREADS}', names)
                     .replace('{DATE}', datetime.date.today().strftime('%d %B %Y')))
    return s

def _bc_set_reply(bid, name, r):
    def f(b):
        b.setdefault('replies', {})[name] = r
    _bc_log_update(bid, f)

def _bc_ask_thread(bid, name, sender, text):
    sysmsg = _bc_system_v3(name)
    if not sysmsg:
        _bc_set_reply(bid, name, {'status': 'error', 'reply': 'No prompt accomplice for this thread.', 'ts': _bc_now()})
        return
    ask = ('MESSAGE FROM THE ' + sender + ' THREAD, sent to you through the botcouncil just now. '
           'It is also the newest entry in your unread updates (section 3 above).\n\n' + text + '\n\n'
           'Reply in one or two short sentences, for Tony to read at a glance. If it needs nothing '
           'from your thread, just say "updated". Otherwise say plainly what it changes for your '
           'thread or what you need. Do not write messages to other threads from here.')
    payload = json.dumps({'model': BC_MODEL, 'usage': {'include': True},
                          'messages': [sysmsg, {'role': 'user', 'content': ask}]}).encode()
    req = urllib.request.Request(BC_OR_URL, data=payload, headers={
        'Content-Type': 'application/json', 'Authorization': 'Bearer ' + OR_KEY,
        'HTTP-Referer': 'https://nexus.needpedia.org', 'X-Title': 'Needpedia Botcouncil'})
    cost = None
    try:
        data = json.loads(urllib.request.urlopen(req, timeout=240).read())
        msg = ((data.get('choices') or [{}])[0].get('message') or {})
        reply = msg.get('content') or ('[no reply: ' + json.dumps(data.get('error', ''))[:300] + ']')
        cost = (data.get('usage') or {}).get('cost')
        st = 'done'
    except urllib.error.HTTPError as e:
        reply, st = '[error ' + str(e.code) + ': ' + e.read()[:300].decode('utf-8', 'replace') + ']', 'error'
    except Exception as e:
        reply, st = '[error: ' + str(e)[:300] + ']', 'error'
    _bc_set_reply(bid, name, {'status': st, 'reply': reply.strip(), 'ts': _bc_now(), 'cost': cost})

def _bc_broadcast(sender, targets_raw, text):
    names = [t['name'] for t in _bc_threads()]
    if sender not in names:
        return None
    raw = targets_raw.strip().upper()
    if raw in ('ALL', 'EVERYONE', 'ALL THREADS', 'EVERY THREAD'):
        to = [n for n in names if n != sender]
    else:
        to = []
        for x in _bcre.split(r'[,\s]+', raw):
            if x and x in names and x != sender and x not in to:
                to.append(x)
    text = text.strip()
    if not to or not text:
        return None
    if not _bcre.match(r'tags\s*:', text, _bcre.I):
        text = 'tags: botcouncil, from-' + sender.lower() + '\n' + text
    with _bc_lock:
        items = _bc_log_load()
        if any(b.get('from') == sender and b.get('text') == text for b in items):
            return None
        bid = 'bc' + str(int(time.time() * 1000)) + secrets.token_hex(2)
        items.append({'id': bid, 'ts': _bc_now(), 'from': sender, 'to': to, 'text': text,
                      'delivered': {}, 'replies': {n: {'status': 'working', 'ts': _bc_now()} for n in to}})
        _bc_log_save(items)
    delivered = {n: _bc_post_update(n, text) for n in to}
    _bc_log_update(bid, lambda b: b.update({'delivered': delivered}))
    for n in to:
        _bcth.Thread(target=_bc_ask_thread, args=(bid, n, sender, text), daemon=True).start()
    return {'id': bid, 'to': to}

def _bc_after_reply(thread, raw):
    try:
        data = json.loads(raw)
        content = data['choices'][0]['message']['content'] or ''
    except Exception:
        return raw
    sender = str(thread or '').upper()
    sent = []
    for m in _BC_BLOCK.finditer(content):
        try:
            r = _bc_broadcast(sender, m.group(1), m.group(2))
        except Exception as e:
            r = {'error': str(e)}
        if r:
            sent.append(r)
    if not sent:
        return raw
    data['botcouncil'] = sent
    return json.dumps(data).encode()

_bc_op_v3 = _bc_op
def _bc_op(action, body):
    if action == 'bc-council':
        with _bc_lock:
            items = _bc_log_load()
        return {'council': items[-60:], 'now': _bc_now()}
    if action == 'bc-unread':
        n = str(body.get('name', '')).upper()
        if not _bcre.fullmatch(r'[A-Z0-9]+', n):
            return {'error': 'bad thread name'}
        return {'name': n, 'text': _bc_unread(n)}
    return _bc_op_v3(action, body)
# --- botcouncil jobs (JOHN thread, session John 8, 5 Oct 2026) ---
# Long AI answers: the window sends {"async": true}, gets {"job": id} back
# at once, then asks admin-ops "bc-job" until the answer is ready. Nothing
# waits on an open connection, so no web server or Cloudflare time limit
# can cut it off. Jobs live in memory; a server restart loses unfinished ones.
_bc_jobs = {}

def _bc_job_run(jid, req, thread):
    try:
        raw = urllib.request.urlopen(req, timeout=900).read()
        if thread:
            raw = _bc_after_reply(thread, raw)
        data = json.loads(raw)
    except urllib.error.HTTPError as e:
        try:
            data = json.loads(e.read())
        except Exception:
            data = {'error': 'AI service answered with code ' + str(e.code)}
    except Exception as e:
        data = {'error': str(e)}
    _bc_jobs[jid] = {'status': 'done', 'data': data, 't': time.time()}

def _bc_job_start(req, thread):
    now = time.time()
    for k in [k for k, v in list(_bc_jobs.items()) if now - v.get('t', now) > 3600]:
        _bc_jobs.pop(k, None)
    jid = 'job' + secrets.token_hex(8)
    _bc_jobs[jid] = {'status': 'working', 't': now}
    _bcth.Thread(target=_bc_job_run, args=(jid, req, thread), daemon=True).start()
    return jid

_bc_op_v4 = _bc_op
def _bc_op(action, body):
    if action == 'bc-job':
        j = _bc_jobs.get(str(body.get('id', '')))
        if not j:
            return {'status': 'missing'}
        return {'status': j['status'], 'data': j.get('data')}
    return _bc_op_v4(action, body)
# --- botcouncil sessions (JOHN thread, session John 8, 5 Oct 2026) ---
# Marks window sessions in the thread's prompt accomplice, so an AI on
# claude.ai can see a thread was continued here. The first answer in a new
# window session adds a STARTED line with a link to that session; an answer
# holding a closing handoff (a line starting "HANDOFF PROMPT -") adds a
# CLOSED line. Sessions seen are kept in ADMIN_CONVS/council/sessions.json.
BC_SESS_FILE = os.path.join(BC_COUNCIL_DIR, 'sessions.json')
BC_PAGE_URL  = 'https://nexus.needpedia.org/botcouncil.html'
_BC_HANDOFF  = _bcre.compile(r'^[#\s>*`]*HANDOFF PROMPT\s*-', _bcre.M)

def _bc_sess_load():
    try:
        with open(BC_SESS_FILE) as f:
            return json.load(f)
    except Exception:
        return {}

def _bc_sess_save(d):
    os.makedirs(BC_COUNCIL_DIR, exist_ok=True)
    tmp = BC_SESS_FILE + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(d, f, indent=1)
    os.replace(tmp, BC_SESS_FILE)

def _bc_pa_append(name, text):
    p = os.path.join(BC_NEXUS, 'PA-' + name + '.txt')
    if not os.path.isfile(p):
        return False
    try:
        cur = _bc_read(p)
        with open(p, 'a', encoding='utf-8') as f:
            f.write(('' if cur.endswith('\n') else '\n') + '\n' + text.rstrip() + '\n')
        return True
    except Exception:
        return False

def _bc_session_mark(thread, sid, title, reply_text):
    name = str(thread or '').upper()
    sid = _bcre.sub(r'[^A-Za-z0-9_\-]', '', str(sid or ''))[:80]
    title = ' '.join(str(title or 'Untitled').split())[:120]
    if not sid or not _bcre.fullmatch(r'[A-Z0-9]+', name):
        return
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    link = BC_PAGE_URL + '?thread=' + name + '&session=' + sid
    with _bc_lock:
        d = _bc_sess_load()
        s = d.get(sid)
        if s is None:
            s = {'thread': name, 'started': now, 'closed': '', 'title': title}
            d[sid] = s
            _bc_pa_append(name,
                '----- BOTCOUNCIL SESSION STARTED ' + now + ' -----\n'
                'This thread was continued in Tony\'s botcouncil window on his Nexus. '
                'Session: "' + title + '".\n'
                'Open it (Tony\'s admin login): ' + link + '\n'
                'AI on another site: if this line is newer than your handoff and no '
                'BOTCOUNCIL SESSION CLOSED line for it follows, tell Tony before anything '
                'else and give him that link. He wraps the session up there and brings its '
                'closing handoff back.')
        if not s.get('closed') and reply_text and _BC_HANDOFF.search(reply_text):
            s['closed'] = now
            _bc_pa_append(name,
                '----- BOTCOUNCIL SESSION CLOSED ' + now + ' -----\n'
                'Session "' + s.get('title', title) + '" wrote its closing handoff, the last '
                'message of that session: ' + link)
        _bc_sess_save(d)

def _bc_job_run(jid, req, thread, sess=None):
    try:
        raw = urllib.request.urlopen(req, timeout=900).read()
        if thread:
            raw = _bc_after_reply(thread, raw)
        data = json.loads(raw)
        if thread and sess and sess.get('id'):
            try:
                msg = ((data.get('choices') or [{}])[0].get('message') or {})
                _bc_session_mark(thread, sess.get('id'), sess.get('title'), msg.get('content') or '')
            except Exception:
                pass
    except urllib.error.HTTPError as e:
        try:
            data = json.loads(e.read())
        except Exception:
            data = {'error': 'AI service answered with code ' + str(e.code)}
    except Exception as e:
        data = {'error': str(e)}
    _bc_jobs[jid] = {'status': 'done', 'data': data, 't': time.time()}

def _bc_job_start(req, thread, body=None):
    now = time.time()
    for k in [k for k, v in list(_bc_jobs.items()) if now - v.get('t', now) > 3600]:
        _bc_jobs.pop(k, None)
    sess = None
    if body and body.get('session'):
        sess = {'id': body.get('session'), 'title': body.get('title', '')}
    jid = 'job' + secrets.token_hex(8)
    _bc_jobs[jid] = {'status': 'working', 't': now}
    _bcth.Thread(target=_bc_job_run, args=(jid, req, thread, sess), daemon=True).start()
    return jid
# --- botcouncil step 1 (JOHN thread, session John 9, 5 Oct 2026) ---
# What this adds, in plain words:
# - Nothing lost: the server saves each window conversation itself, when a
#   message is sent (marked "pending") and again when the answer arrives.
#   Closing the window mid-answer loses nothing.
# - Cost: each answer carries its cost and how much of it got the repeat
#   discount. Action "bc-key" reports money left on the AI key.
# - Cheaper repeats: the time moves out of the thread instructions into the
#   newest message, and each session sends a session label (session_id) so
#   OpenRouter keeps using the provider that holds the discount.
# - Thread messages: ===TO THREADS=== now only leaves news in the other
#   threads' updates posts; nobody replies live (Tony, 5 Oct 2026).
#   ===ASK THREAD: NAME=== shows Tony a box in the window; only when he
#   clicks Send does action "bc-ask" put the question to that thread's AI.
# - Action "bc-close-session" writes a CLOSED line without a handoff.
# Later definitions replace earlier ones of the same name; nothing above
# this block was edited.
_bc_conv_lock = _bcth.Lock()
_bc_key_cache = {'t': 0, 'data': None}

BC_HOWTO = (
    '\n\n===== 4. OTHER THREADS (botcouncil) =====\n'
    'There are two ways to reach other threads. Each marker goes on its own line.\n\n'
    'A. NEWS, the usual way. When Tony asks you to tell, update or message other threads:\n'
    '===TO THREADS: ALL===\n'
    'tags: two or three plain words someone would search for\n'
    'From the {NAME} thread (botcouncil). To every thread. {DATE}.\n'
    'The message itself, complete and plain: the reader has not seen this chat.\n'
    '===END===\n'
    'Instead of ALL you can name threads, separated by commas, for example '
    '===TO THREADS: NEXUS, PC=== (then name them on the From line instead of "every thread"). '
    'The botcouncil leaves it in each of those threads\' updates posts, and each thread reads '
    'it the next time Tony opens it. Nobody replies now. Write a block only when Tony asks, '
    'and never repeat one you already sent.\n\n'
    'B. A LIVE QUESTION. Only when you are pretty sure an answer from another thread is needed '
    'now, to help Tony or to keep things running smoothly:\n'
    '===ASK THREAD: JOBS===\n'
    'The question, complete and plain: that thread has not seen this chat.\n'
    '===END===\n'
    'One thread per block. Tony sees it as a box with Send and Skip buttons, and nothing goes '
    'out until he clicks Send. The answer then appears in this chat for you.\n\n'
    'Thread names: {THREADS}.')

_bc_system_john8 = _bc_system
def _bc_system(name):
    s = _bc_system_john8(name)
    if not s:
        return s
    s = dict(s)
    # The time used to sit near the top, so the start of every message
    # differed and no message got the repeat discount. It now goes into the
    # newest message instead (see _bc_job_start).
    s['content'] = _bcre.sub(r'computer at \d{4}-\d{2}-\d{2} \d{2}:\d{2}, so',
                             'computer for every message, so', s['content'], count=1)
    return s

def _bc_label(s, n=100):
    return _bcre.sub(r'[^A-Za-z0-9_\-]', '', str(s or ''))[:n]

def _bc_conv_load(cid):
    cid = _bc_label(cid)
    if not cid:
        return None
    try:
        with open(os.path.join(ADMIN_CONVS, cid + '.json')) as f:
            return json.load(f)
    except Exception:
        return None

def _bc_conv_write(conv):
    cid = _bc_label(conv.get('id'))
    if not cid:
        return False
    with _bc_conv_lock:
        os.makedirs(ADMIN_CONVS, exist_ok=True)
        now = datetime.datetime.utcnow().isoformat() + 'Z'
        conv['id'] = cid
        conv['updated_at'] = now
        conv.setdefault('created_at', now)
        p = os.path.join(ADMIN_CONVS, cid + '.json')
        with open(p + '.tmp', 'w') as f:
            json.dump(conv, f, indent=2)
        os.replace(p + '.tmp', p)
        idx = os.path.join(ADMIN_CONVS, 'index.json')
        try:
            with open(idx) as f:
                index = json.load(f)
        except Exception:
            index = []
        info = {'title': conv.get('title', 'Untitled'), 'model': conv.get('model', ''),
                'thread': conv.get('thread', ''), 'updated_at': now}
        e = next((x for x in index if x.get('id') == cid), None)
        if e:
            e.update(info)
        else:
            index.insert(0, dict({'id': cid, 'created_at': conv['created_at']}, **info))
        with open(idx + '.tmp', 'w') as f:
            json.dump(index, f, indent=2)
        os.replace(idx + '.tmp', idx)
    return True

def _bc_reply_parts(data):
    msg = ((data.get('choices') or [{}])[0].get('message') or {}) if isinstance(data, dict) else {}
    content = msg.get('content') or ('[No response' + (': ' + json.dumps(data.get('error'))[:300]
                                     if isinstance(data, dict) and data.get('error') else '') + ']')
    out = {'role': 'assistant', 'content': content, 'model': BC_MODEL}
    u = (data.get('usage') or {}) if isinstance(data, dict) else {}
    if isinstance(u.get('cost'), (int, float)):
        out['cost'] = u['cost']
    pt = u.get('prompt_tokens')
    ct = (u.get('prompt_tokens_details') or {}).get('cached_tokens')
    if isinstance(pt, int) and pt > 0 and isinstance(ct, int):
        out['cached_pct'] = int(round(100.0 * ct / pt))
    return out

def _bc_job_run(jid, req, thread, sess=None, sid=''):
    try:
        raw = urllib.request.urlopen(req, timeout=900).read()
        if thread:
            raw = _bc_after_reply(thread, raw)
        data = json.loads(raw)
        if thread and sess and sess.get('id'):
            try:
                msg = ((data.get('choices') or [{}])[0].get('message') or {})
                _bc_session_mark(thread, sess.get('id'), sess.get('title'), msg.get('content') or '')
            except Exception:
                pass
    except urllib.error.HTTPError as e:
        try:
            data = json.loads(e.read())
        except Exception:
            data = {'error': 'AI service answered with code ' + str(e.code)}
    except Exception as e:
        data = {'error': str(e)}
    if thread and sid:
        try:
            conv = _bc_conv_load(sid)
            if conv is not None:
                conv.setdefault('messages', []).append(_bc_reply_parts(data))
                conv.pop('pending', None)
                _bc_conv_write(conv)
                data['bc_saved'] = True
        except Exception:
            pass
    _bc_jobs[jid] = {'status': 'done', 'data': data, 't': time.time()}

def _bc_job_start(req, thread, body=None):
    body = body or {}
    now = time.time()
    for k in [k for k, v in list(_bc_jobs.items()) if now - v.get('t', now) > 3600]:
        _bc_jobs.pop(k, None)
    jid = 'job' + secrets.token_hex(8)
    sid = _bc_label(body.get('session'))
    try:
        payload = json.loads(req.data)
        msgs = []
        for m in payload.get('messages', []):
            # an answer from another thread is stored as its own message;
            # some AI services refuse two user messages in a row, so join them
            if (msgs and m.get('role') == 'user' and msgs[-1].get('role') == 'user'
                    and isinstance(m.get('content'), str) and isinstance(msgs[-1].get('content'), str)):
                msgs[-1] = dict(msgs[-1], content=msgs[-1]['content'] + '\n\n' + m['content'])
            else:
                msgs.append(m)
        if thread:
            stamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
            for i in range(len(msgs) - 1, -1, -1):
                if msgs[i].get('role') == 'user' and isinstance(msgs[i].get('content'), str):
                    msgs[i] = dict(msgs[i], content=msgs[i]['content'] + '\n\n(Time now: ' + stamp + ')')
                    break
            payload['usage'] = {'include': True}
            if sid:
                payload['session_id'] = sid
        payload['messages'] = msgs
        req.data = json.dumps(payload).encode()
    except Exception:
        pass
    if thread and sid:
        try:
            conv = _bc_conv_load(sid) or {'id': sid}
            old = conv.get('messages', [])
            new = []
            src = [m for m in body.get('messages', []) if m.get('role') in ('user', 'assistant')]
            for i, m in enumerate(src):
                o = old[i] if i < len(old) else None
                if o and o.get('role') == m.get('role') and o.get('content') == m.get('content'):
                    new.append(o)          # keeps cost and other notes saved earlier
                else:
                    new.append({'role': m.get('role'), 'content': m.get('content', '')})
            conv.update({'messages': new, 'thread': str(thread).upper(), 'model': BC_MODEL,
                         'title': str(body.get('title') or conv.get('title') or 'New session')[:200],
                         'pending': {'since': _bc_now(), 'job': jid}})
            _bc_conv_write(conv)
        except Exception:
            sid = ''
    sess = {'id': body.get('session'), 'title': body.get('title', '')} if body.get('session') else None
    _bc_jobs[jid] = {'status': 'working', 't': now}
    _bcth.Thread(target=_bc_job_run, args=(jid, req, thread, sess, sid), daemon=True).start()
    return jid

def _bc_targets(sender, targets_raw):
    names = [t['name'] for t in _bc_threads()]
    if sender not in names:
        return None
    raw = str(targets_raw or '').strip().upper()
    if raw in ('ALL', 'EVERYONE', 'ALL THREADS', 'EVERY THREAD'):
        return [n for n in names if n != sender]
    to = []
    for x in _bcre.split(r'[,\s]+', raw):
        if x and x in names and x != sender and x not in to:
            to.append(x)
    return to

def _bc_broadcast(sender, targets_raw, text):
    # News only: left in each thread's updates post, no live replies.
    to = _bc_targets(sender, targets_raw)
    text = (text or '').strip()
    if not to or not text:
        return None
    if not _bcre.match(r'tags\s*:', text, _bcre.I):
        text = 'tags: botcouncil, from-' + sender.lower() + '\n' + text
    with _bc_lock:
        items = _bc_log_load()
        if any(b.get('from') == sender and b.get('text') == text for b in items):
            return None
        bid = 'bc' + str(int(time.time() * 1000)) + secrets.token_hex(2)
        items.append({'id': bid, 'ts': _bc_now(), 'kind': 'post', 'from': sender, 'to': to,
                      'text': text, 'delivered': {}, 'replies': {}})
        _bc_log_save(items)
    delivered = {n: _bc_post_update(n, text) for n in to}
    _bc_log_update(bid, lambda b: b.update({'delivered': delivered}))
    return {'id': bid, 'to': to}

def _bc_ask_live(bid, name, sender, question):
    sysmsg = _bc_system(name)
    if not sysmsg:
        _bc_set_reply(bid, name, {'status': 'error', 'reply': 'No prompt accomplice for this thread.', 'ts': _bc_now()})
        return
    ask = ('LIVE QUESTION FROM THE ' + sender + ' THREAD, sent through the botcouncil just now. '
           'Tony read it and clicked Send. Answer it plainly and completely from what your thread '
           'knows; the ' + sender + ' thread\'s AI will read your answer in its own chat. If you do '
           'not know, say so. Do not write messages to other threads from here.\n\n' + question +
           '\n\n(Time now: ' + datetime.datetime.now().strftime('%Y-%m-%d %H:%M') + ')')
    payload = json.dumps({'model': BC_MODEL, 'usage': {'include': True},
                          'messages': [sysmsg, {'role': 'user', 'content': ask}]}).encode()
    req = urllib.request.Request(BC_OR_URL, data=payload, headers={
        'Content-Type': 'application/json', 'Authorization': 'Bearer ' + OR_KEY,
        'HTTP-Referer': 'https://nexus.needpedia.org', 'X-Title': 'Needpedia Botcouncil'})
    cost = None
    try:
        data = json.loads(urllib.request.urlopen(req, timeout=600).read())
        part = _bc_reply_parts(data)
        reply, cost, st = part['content'], part.get('cost'), 'done'
    except urllib.error.HTTPError as e:
        reply, st = '[error ' + str(e.code) + ': ' + e.read()[:300].decode('utf-8', 'replace') + ']', 'error'
    except Exception as e:
        reply, st = '[error: ' + str(e)[:300] + ']', 'error'
    _bc_set_reply(bid, name, {'status': st, 'reply': reply.strip(), 'ts': _bc_now(), 'cost': cost})

def _bc_ask_start(body):
    sender = str(body.get('from', '')).upper()
    to = _bc_targets(sender, body.get('to', ''))
    q = str(body.get('question', '')).strip()
    if not to or len(to) != 1 or not q:
        return {'error': 'Needs one other thread and a question.'}
    name = to[0]
    with _bc_lock:
        items = _bc_log_load()
        bid = 'bc' + str(int(time.time() * 1000)) + secrets.token_hex(2)
        items.append({'id': bid, 'ts': _bc_now(), 'kind': 'ask', 'from': sender, 'to': [name],
                      'text': q, 'delivered': {}, 'replies': {name: {'status': 'working', 'ts': _bc_now()}}})
        _bc_log_save(items)
    _bcth.Thread(target=_bc_ask_live, args=(bid, name, sender, q), daemon=True).start()
    return {'id': bid, 'to': name}

def _bc_close_session(body):
    sid = _bc_label(body.get('session'), 80)
    if not sid:
        return {'status': 'no session given'}
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    with _bc_lock:
        d = _bc_sess_load()
        s = d.get(sid)
        if not s:
            return {'status': 'not marked as started, so nothing to close'}
        if s.get('closed'):
            return {'status': 'already closed ' + s['closed']}
        s['closed'] = now
        link = BC_PAGE_URL + '?thread=' + s.get('thread', '') + '&session=' + sid
        _bc_pa_append(s.get('thread', ''),
            '----- BOTCOUNCIL SESSION CLOSED ' + now + ' -----\n'
            'Tony marked session "' + s.get('title', '') + '" closed in the botcouncil window, '
            'without a handoff written there: ' + link)
        _bc_sess_save(d)
    return {'status': 'closed', 'thread': s.get('thread', '')}

def _bc_key_info():
    if _bc_key_cache['data'] and time.time() - _bc_key_cache['t'] < 60:
        return _bc_key_cache['data']
    req = urllib.request.Request('https://openrouter.ai/api/v1/key',
                                 headers={'Authorization': 'Bearer ' + OR_KEY})
    d = (json.loads(urllib.request.urlopen(req, timeout=20).read()) or {}).get('data') or {}
    limit, spent, left = d.get('limit'), d.get('usage'), d.get('limit_remaining')
    if left is None and isinstance(limit, (int, float)) and isinstance(spent, (int, float)):
        left = limit - spent
    out = {'limit': limit, 'spent': spent, 'left': left}
    _bc_key_cache.update({'t': time.time(), 'data': out})
    return out

_bc_op_john8 = _bc_op
def _bc_op(action, body):
    if action == 'bc-key':
        try:
            return _bc_key_info()
        except Exception as e:
            return {'error': str(e)[:200]}
    if action == 'bc-ask':
        return _bc_ask_start(body)
    if action == 'bc-close-session':
        return _bc_close_session(body)
    return _bc_op_john8(action, body)
# --- end botcouncil step 1 ---
# --- end botcouncil ---

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Admin-Token')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.end_headers()
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path   = parsed.path
        params = urllib.parse.parse_qs(parsed.query)
        if path == '/admin-devlog':
            self._handle_devlog_get(params)
        elif path == '/admin-browse':
            self._handle_admin_browse(params)
        elif path == '/admin-file':
            self._handle_admin_file(params)
        elif path == '/admin-convs':
            self._handle_admin_convs_get(params)
        elif path == '/admin-conv':
            self._handle_admin_conv_get(params)
        elif path == '/admin-activity':
            self._handle_admin_activity(params)
        elif path == '/volunteer-convs':
            self._handle_volunteer_convs_get(params)
        elif path == '/volunteer-conv':
            self._handle_volunteer_conv_get(params)
        else:
            self.send_response(404)
            self.end_headers()
    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path   = parsed.path
        length = int(self.headers.get('Content-Length', 0))
        if path == '/folder-upload':
            raw = self.rfile.read(length)
            self._handle_folder_upload(raw, parsed.query)
            return
        body   = json.loads(self.rfile.read(length))

        if path == '/save-order':
            self._handle_save_order(body)
        elif path == '/volunteer-auth':
            self._handle_auth(body)
        elif path == '/volunteer-log':
            self._handle_log(body)
        elif path == '/save-text':
            self._handle_save_text(body)
        elif path == '/save-image':
            self._handle_save_image(body)
        elif path == '/admin-auth':
            self._handle_admin_auth(body)
        elif path == '/admin-ops':
            self._handle_admin_ops(body)
        elif path == '/admin-delete':
            self._handle_admin_delete(body)
        elif path == '/admin-chat-proxy':
            self._handle_admin_chat_proxy(body)
        elif path == '/volunteer-chat-proxy':
            self._handle_volunteer_chat_proxy(body)
        elif path == '/admin-convs':
            self._handle_admin_convs_post(body)
        elif path == '/admin-import':
            self._handle_admin_import(body)
        elif path == '/admin-conv-delete':
            self._handle_admin_conv_delete(body)
        elif path == '/admin-conv-rename':
            self._handle_admin_conv_rename(body)
        elif path == '/capture':
            self._handle_capture(body)
        else:
            self.send_response(404)
            self.end_headers()
    def _handle_admin_auth(self, body):
        pw = body.get('password', '')
        if pw == PASS:
            tok = issue_token()
            self.send_response(200)
            self._cors()
            self.end_headers()
            self.wfile.write(json.dumps({'success': True, 'token': tok}).encode())
        else:
            self.send_response(401)
            self._cors()
            self.end_headers()
            self.wfile.write(json.dumps({'success': False, 'error': 'Invalid password'}).encode())

    def _handle_devlog_get(self, params):
        tok = self.headers.get('X-Admin-Token', '')
        pw  = params.get('password', [''])[0]
        if not valid_token(tok) and pw != PASS:
            self.send_response(403)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(b'Unauthorized')
            return
        try:
            with open(DEVLOG, 'r') as f:
                content = f.read().encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(str(e).encode())

    def _handle_admin_activity(self, params):
        tok = self.headers.get('X-Admin-Token', '')
        if not valid_token(tok):
            self.send_response(403); self._cors(); self.end_headers()
            self.wfile.write(b'{"error":"Unauthorized"}')
            return
        try:
            with open(ACTIVITY_JSON, 'rb') as f:
                data = f.read()
            self.send_response(200); self._cors()
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(data)
        except FileNotFoundError:
            self.send_response(404); self._cors(); self.end_headers()
            self.wfile.write(b'{"ok":false,"error":"no data yet"}')
        except Exception as e:
            self.send_response(500); self._cors(); self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())

    def _handle_admin_ops(self, body):
        tok = self.headers.get('X-Admin-Token', '')
        if not valid_token(tok):
            self.send_response(401)
            self._cors()
            self.end_headers()
            self.wfile.write(b'{"error":"Unauthorized"}')
            return
        action = body.get('action', '')
        if action.startswith('bc-'):
            try:
                result = _bc_op(action, body)
                self.send_response(200); self._cors(); self.end_headers()
                self.wfile.write(json.dumps(result).encode())
            except Exception as e:
                self.send_response(500); self._cors(); self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode())
            return
        self.send_response(200)
        self._cors()
        self.end_headers()
        self.wfile.write(json.dumps({'result': f'Ops not yet wired up (action: {action}). Coming in a future session.'}).encode())

    def _handle_admin_delete(self, body):
        tok = self.headers.get('X-Admin-Token', '')
        if not valid_token(tok):
            self.send_response(401); self._cors(); self.end_headers()
            self.wfile.write(b'{"error":"Unauthorized"}')
            return
        target    = body.get('path', '')
        real_path = os.path.realpath(target)
        if not real_path.startswith(os.path.realpath(HOME_ROOT)):
            self.send_response(403); self._cors(); self.end_headers()
            self.wfile.write(b'{"error":"Path not allowed"}')
            return
        if real_path == os.path.realpath(HOME_ROOT) or real_path == os.path.realpath(UPLOAD_ROOT):
            self.send_response(403); self._cors(); self.end_headers()
            self.wfile.write(b'{"error":"Cannot delete root folders"}')
            return
        try:
            if os.path.isdir(real_path):
                shutil.rmtree(real_path)
            elif os.path.isfile(real_path):
                os.remove(real_path)
            else:
                self.send_response(404); self._cors(); self.end_headers()
                self.wfile.write(b'{"error":"Not found"}')
                return
            self.send_response(200); self._cors(); self.end_headers()
            self.wfile.write(json.dumps({'ok': True, 'deleted': real_path}).encode())
        except Exception as e:
            self.send_response(500); self._cors(); self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())

    def _handle_folder_upload(self, raw, query_string):
        tok = self.headers.get('X-Admin-Token', '')
        if not valid_token(tok):
            self.send_response(401); self._cors(); self.end_headers()
            self.wfile.write(b'{"error":"Unauthorized"}')
            return
        params      = urllib.parse.parse_qs(query_string)
        target      = params.get('path', [UPLOAD_ROOT])[0]
        real_target = os.path.realpath(target)
        if not real_target.startswith(os.path.realpath(HOME_ROOT)):
            self.send_response(403); self._cors(); self.end_headers()
            self.wfile.write(b'{"error":"Path not allowed"}')
            return
        usage = shutil.disk_usage('/')
        if len(raw) > 0 and (usage.used + len(raw)) / usage.total > DRIVE_CAP:
            self.send_response(507); self._cors(); self.end_headers()
            self.wfile.write(b'{"error":"Drive cap reached"}')
            return
        try:
            os.makedirs(real_target, exist_ok=True)
            extracted = []
            with zipfile.ZipFile(io.BytesIO(raw)) as zf:
                for member in zf.namelist():
                    member_clean = os.path.normpath(member)
                    if member_clean.startswith('..'):
                        continue
                    dest = os.path.realpath(os.path.join(real_target, member_clean))
                    if not dest.startswith(real_target):
                        continue
                    zf.extract(member, real_target)
                    if not member.endswith('/'):
                        extracted.append(member)
            self.send_response(200); self._cors(); self.end_headers()
            self.wfile.write(json.dumps({'ok': True, 'files': extracted, 'count': len(extracted), 'target': real_target}).encode())
        except Exception as e:
            self.send_response(500); self._cors(); self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())

    def _handle_admin_browse(self, params):
        tok = self.headers.get('X-Admin-Token', '')
        if not valid_token(tok):
            self.send_response(403); self._cors(); self.end_headers()
            self.wfile.write(b'{"error":"Unauthorized"}')
            return
        browse_path = params.get('path', [UPLOAD_ROOT])[0]
        real_path   = os.path.realpath(browse_path)
        if not real_path.startswith(os.path.realpath(HOME_ROOT)):
            self.send_response(403); self._cors(); self.end_headers()
            self.wfile.write(b'{"error":"Path not allowed"}')
            return
        if not os.path.isdir(real_path):
            self.send_response(404); self._cors(); self.end_headers()
            self.wfile.write(b'{"error":"Not a directory"}')
            return
        entries = []
        try:
            for name in sorted(os.listdir(real_path)):
                full = os.path.join(real_path, name)
                try:
                    stat = os.stat(full)
                    entries.append({
                        'name':     name,
                        'type':     'dir' if os.path.isdir(full) else 'file',
                        'size':     stat.st_size,
                        'modified': datetime.datetime.utcfromtimestamp(stat.st_mtime).isoformat() + 'Z',
                        'path':     full
                    })
                except Exception:
                    pass
        except Exception as e:
            self.send_response(500); self._cors(); self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
            return
        parent = str(os.path.dirname(real_path))
        self.send_response(200); self._cors(); self.end_headers()
        self.wfile.write(json.dumps({'path': real_path, 'parent': parent, 'entries': entries}).encode())

    def _handle_admin_file(self, params):
        tok = self.headers.get('X-Admin-Token', '')
        if not valid_token(tok):
            self.send_response(403); self._cors(); self.end_headers()
            self.wfile.write(b'{"error":"Unauthorized"}')
            return
        file_path = params.get('path', [''])[0]
        real_path = os.path.realpath(file_path)
        if not real_path.startswith(os.path.realpath(HOME_ROOT)):
            self.send_response(403); self._cors(); self.end_headers()
            self.wfile.write(b'{"error":"Path not allowed"}')
            return
        if not os.path.isfile(real_path):
            self.send_response(404); self._cors(); self.end_headers()
            self.wfile.write(b'{"error":"Not found"}')
            return
        try:
            with open(real_path, 'rb') as fh:
                data = fh.read()
            filename = os.path.basename(real_path)
            self.send_response(200)
            self.send_header('Content-Type', 'application/octet-stream')
            self.send_header('Content-Disposition', 'attachment; filename="' + filename + '"')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Admin-Token')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            self.send_response(500); self._cors(); self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())

    def _handle_save_order(self, body):
        if body.get('password') != PASS:
            self.send_response(403)
            self._cors()
            self.end_headers()
            self.wfile.write(b'{"error":"bad password"}')
            return
        folder = body.get('folder', '').strip('/').replace('..', '')
        order  = body.get('order', [])
        target = os.path.join(BASE, folder, '_order.json')
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, 'w') as f:
            json.dump(order, f)
        self.send_response(200)
        self._cors()
        self.end_headers()
        self.wfile.write(b'{"ok":true}')

    def _handle_auth(self, body):
        username   = body.get('username', '').strip()
        password   = body.get('password', '')
        volunteers = load_volunteers()
        hashed     = hash_pw(password)
        match = next((v for v in volunteers if v['username'] == username and v['password_hash'] == hashed), None)
        if match:
            self.send_response(200)
            self._cors()
            self.end_headers()
            self.wfile.write(json.dumps({'ok': True, 'username': username}).encode())
        else:
            self.send_response(403)
            self._cors()
            self.end_headers()
            self.wfile.write(b'{"error":"invalid credentials"}')

    def _handle_save_image(self, body):
        username   = body.get('username', '').strip().replace('..', '').replace('/', '')
        session_id = body.get('session_id', '').strip().replace('..', '').replace('/', '').replace(' ', '_')
        if not username or not session_id:
            self.send_response(400); self._cors(); self.end_headers()
            self.wfile.write(b'{"error":"missing username or session_id"}')
            return

        log_root = os.path.join(BASE, 'volunteer-logs')
        if dir_size(log_root) > STORAGE_CAP:
            self.send_response(507); self._cors(); self.end_headers()
            self.wfile.write(b'{"error":"storage cap reached"}')
            return

        sess_dir = os.path.join(log_root, username, 'image-sessions')
        os.makedirs(sess_dir, exist_ok=True)

        now   = datetime.datetime.utcnow().isoformat() + 'Z'
        entry = {
            'timestamp': now,
            'model':     body.get('model', ''),
            'prompt':    body.get('prompt', ''),
            'img_url':   body.get('img_url', '')
        }

        img_url      = entry.get('img_url', '')
        img_filename = None
        img_index    = len([f for f in os.listdir(sess_dir) if f.startswith(session_id) and f.endswith('.png')]) + 1
        img_filename = session_id + '_' + str(img_index).zfill(2) + '.png'
        img_path     = os.path.join(sess_dir, img_filename)
        try:
            if img_url.startswith('data:image'):
                header, b64data = img_url.split(',', 1)
                img_bytes = base64.b64decode(b64data)
                with open(img_path, 'wb') as f:
                    f.write(img_bytes)
            elif img_url.startswith('http'):
                req       = urllib.request.urlopen(img_url, timeout=30)
                img_bytes = req.read()
                with open(img_path, 'wb') as f:
                    f.write(img_bytes)
            else:
                img_filename = None
        except Exception:
            img_filename = None

        if img_filename:
            entry['local_file'] = img_filename
        entry.pop('img_url', None)

        sess_file = os.path.join(sess_dir, session_id + '.json')
        session   = []
        if os.path.exists(sess_file):
            try:
                with open(sess_file) as f:
                    session = json.load(f)
            except:
                session = []
        session.append(entry)
        with open(sess_file, 'w') as f:
            json.dump(session, f, indent=2)

        index_file = os.path.join(log_root, username, 'index.json')
        index      = []
        if os.path.exists(index_file):
            try:
                with open(index_file) as f:
                    index = json.load(f)
            except:
                index = []
        existing = next((x for x in index if x.get('session_id') == session_id), None)
        if existing:
            existing['last_updated'] = now
            existing['image_count']  = len(session)
        else:
            index.insert(0, {
                'type':         'image',
                'session_id':   session_id,
                'title':        body.get('prompt', '')[:60],
                'started_at':   now,
                'last_updated': now,
                'image_count':  1
            })
        with open(index_file, 'w') as f:
            json.dump(index, f, indent=2)

        self.send_response(200); self._cors(); self.end_headers()
        self.wfile.write(b'{"ok":true}')

    def _handle_save_text(self, body):
        username = body.get('username', '').strip().replace('..', '').replace('/', '')
        convo_id = body.get('convo_id', '').strip().replace('..', '').replace('/', '').replace(' ', '_')
        if not username or not convo_id:
            self.send_response(400); self._cors(); self.end_headers()
            self.wfile.write(b'{"error":"missing username or convo_id"}')
            return

        log_root   = os.path.join(BASE, 'volunteer-logs')
        total_size = dir_size(log_root)
        if total_size > STORAGE_CAP:
            self.send_response(507); self._cors(); self.end_headers()
            self.wfile.write(b'{"error":"storage cap reached"}')
            return

        convo_dir  = os.path.join(log_root, username, 'convos')
        os.makedirs(convo_dir, exist_ok=True)

        convo_file = os.path.join(convo_dir, convo_id + '.jsonl')
        now        = datetime.datetime.utcnow().isoformat() + 'Z'
        entry      = {
            'timestamp': now,
            'model':     body.get('model', ''),
            'user_msg':  body.get('user_msg', ''),
            'reply':     body.get('reply', '')
        }
        with open(convo_file, 'a') as f:
            f.write(json.dumps(entry) + '\n')

        index_file = os.path.join(log_root, username, 'index.json')
        index      = []
        if os.path.exists(index_file):
            try:
                with open(index_file) as f:
                    index = json.load(f)
            except:
                index = []
        existing = next((x for x in index if x.get('convo_id') == convo_id), None)
        if existing:
            existing['last_updated'] = now
            existing['title']        = body.get('title', existing.get('title', 'Untitled'))
        else:
            index.insert(0, {
                'convo_id':    convo_id,
                'title':       body.get('title', 'Untitled'),
                'started_at':  now,
                'last_updated': now
            })
        with open(index_file, 'w') as f:
            json.dump(index, f, indent=2)

        self.send_response(200); self._cors(); self.end_headers()
        self.wfile.write(b'{"ok":true}')

    def _handle_log(self, body):
        username = body.get('username', '').strip().replace('..', '').replace('/', '')
        if not username:
            self.send_response(400); self.end_headers(); return
        entry              = body.get('entry', {})
        entry['timestamp'] = datetime.datetime.utcnow().isoformat() + 'Z'
        log_path           = os.path.join(BASE, 'volunteer-logs', username + '.json')
        logs               = []
        if os.path.exists(log_path):
            try:
                with open(log_path) as f:
                    logs = json.load(f)
            except:
                logs = []
        logs.append(entry)
        with open(log_path, 'w') as f:
            json.dump(logs, f, indent=2)
        self.send_response(200)
        self._cors()
        self.end_headers()
        self.wfile.write(b'{"ok":true}')

    def _handle_admin_chat_proxy(self, body):
        tok = self.headers.get('X-Admin-Token', '')
        if not valid_token(tok):
            self.send_response(401); self._cors(); self.end_headers()
            self.wfile.write(b'{"error":"Unauthorized"}'); return
        if body.get('thread'):
            _sys = _bc_system(body.get('thread'))
            if _sys:
                body['messages'] = [_sys] + [m for m in body.get('messages', []) if m.get('role') != 'system']
                body['model'] = 'deepseek/deepseek-v4-pro-0813'
        payload = json.dumps({
            'model':    body.get('model', 'deepseek/deepseek-v4-pro-0813'),
            'messages': (([WEB_SYS] + body.get('messages', []))
                         if body.get('web') else body.get('messages', [])),
            **({'tools': WEB_TOOLS, 'max_tool_calls': 6}
               if body.get('web') else {})
        }).encode()
        req = urllib.request.Request(
            'https://openrouter.ai/api/v1/chat/completions',
            data=payload,
            headers={
                'Content-Type':  'application/json',
                'Authorization': 'Bearer ' + OR_KEY,
                'HTTP-Referer':  'https://nexus.needpedia.org',
                'X-Title':       'Needpedia Admin Chat',
            }
        )
        if body.get('async'):
            jid = _bc_job_start(req, body.get('thread'), body)
            self.send_response(200); self._cors(); self.end_headers()
            self.wfile.write(json.dumps({'job': jid}).encode())
            return
        try:
            resp = urllib.request.urlopen(req, timeout=120)
            raw = resp.read()
            if body.get('thread'):
                raw = _bc_after_reply(body.get('thread'), raw)
            self.send_response(200); self._cors(); self.end_headers()
            self.wfile.write(raw)
        except urllib.error.HTTPError as e:
            self.send_response(e.code); self._cors(); self.end_headers()
            self.wfile.write(e.read())
        except Exception as e:
            self.send_response(500); self._cors(); self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())

    def _handle_volunteer_chat_proxy(self, body):
        payload = json.dumps({
            'model':    body.get('model', 'qwen/qwen3-235b-a22b-2507'),
            'messages': (([WEB_SYS] + body.get('messages', []))
                         if body.get('web') else body.get('messages', [])),
            **({'tools': WEB_TOOLS, 'max_tool_calls': 6}
               if body.get('web') else {}),
            'stream': True
        }).encode()
        req = urllib.request.Request(
            'https://openrouter.ai/api/v1/chat/completions',
            data=payload,
            headers={
                'Content-Type':  'application/json',
                'Authorization': 'Bearer ' + VOL_KEY,
                'HTTP-Referer':  'https://nexus.needpedia.org',
                'X-Title':       'Needpedia Volunteer Text Studio',
            }
        )
        try:
            resp = urllib.request.urlopen(req, timeout=300)
        except urllib.error.HTTPError as e:
            self.send_response(e.code); self._cors(); self.end_headers()
            self.wfile.write(e.read())
            return
        except Exception as e:
            self.send_response(500); self._cors(); self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
            return
        self.send_response(200); self._cors()
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('X-Accel-Buffering', 'no')
        self.end_headers()
        try:
            for line in resp:
                self.wfile.write(line)
                self.wfile.flush()
        except Exception as e:
            try:
                msg = json.dumps({'error': {'message': str(e)}})
                self.wfile.write(('data: ' + msg + '\n\n').encode())
                self.wfile.flush()
            except Exception:
                pass

    def _handle_admin_convs_get(self, params):
        tok = self.headers.get('X-Admin-Token', '')
        if not valid_token(tok):
            self.send_response(403); self._cors(); self.end_headers()
            self.wfile.write(b'{"error":"Unauthorized"}'); return
        os.makedirs(ADMIN_CONVS, exist_ok=True)
        idx = os.path.join(ADMIN_CONVS, 'index.json')
        data = []
        if os.path.exists(idx):
            try:
                with open(idx) as f: data = json.load(f)
            except: pass
        self.send_response(200); self._cors(); self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _handle_admin_conv_get(self, params):
        tok = self.headers.get('X-Admin-Token', '')
        if not valid_token(tok):
            self.send_response(403); self._cors(); self.end_headers()
            self.wfile.write(b'{"error":"Unauthorized"}'); return
        cid = params.get('id', [''])[0].replace('..', '').replace('/', '')
        if not cid:
            self.send_response(400); self._cors(); self.end_headers()
            self.wfile.write(b'{"error":"Missing id"}'); return
        p = os.path.join(ADMIN_CONVS, cid + '.json')
        if not os.path.exists(p):
            self.send_response(404); self._cors(); self.end_headers()
            self.wfile.write(b'{"error":"Not found"}'); return
        with open(p) as f: raw = f.read()
        self.send_response(200); self._cors(); self.end_headers()
        self.wfile.write(raw.encode())

    def _handle_admin_convs_post(self, body):
        tok = self.headers.get('X-Admin-Token', '')
        if not valid_token(tok):
            self.send_response(401); self._cors(); self.end_headers()
            self.wfile.write(b'{"error":"Unauthorized"}'); return
        conv = body.get('conversation', {})
        cid  = conv.get('id', '').replace('..', '').replace('/', '').replace(' ', '_')
        if not cid:
            self.send_response(400); self._cors(); self.end_headers()
            self.wfile.write(b'{"error":"Missing conversation.id"}'); return
        os.makedirs(ADMIN_CONVS, exist_ok=True)
        now = datetime.datetime.utcnow().isoformat() + 'Z'
        conv['updated_at'] = now
        if 'created_at' not in conv: conv['created_at'] = now
        with open(os.path.join(ADMIN_CONVS, cid + '.json'), 'w') as f:
            json.dump(conv, f, indent=2)
        idx = os.path.join(ADMIN_CONVS, 'index.json')
        index = []
        if os.path.exists(idx):
            try:
                with open(idx) as f: index = json.load(f)
            except: pass
        entry = next((x for x in index if x.get('id') == cid), None)
        if entry:
            entry.update({'title': conv.get('title', 'Untitled'),
                          'model': conv.get('model', ''), 'updated_at': now,
                          'thread': conv.get('thread', '')})
        else:
            index.insert(0, {'id': cid, 'title': conv.get('title', 'Untitled'),
                             'model': conv.get('model', ''),
                             'thread': conv.get('thread', ''),
                             'created_at': now, 'updated_at': now})
        with open(idx, 'w') as f: json.dump(index, f, indent=2)
        self.send_response(200); self._cors(); self.end_headers()
        self.wfile.write(b'{"ok":true}')

    def _handle_volunteer_convs_get(self, params):
        user = params.get('user', [''])[0].strip().replace('..', '').replace('/', '')
        if not user:
            self.send_response(400); self._cors(); self.end_headers()
            self.wfile.write(b'{"error":"Missing user"}'); return
        idx  = os.path.join(BASE, 'volunteer-logs', user, 'index.json')
        data = []
        if os.path.exists(idx):
            try:
                with open(idx) as f: data = json.load(f)
            except: pass
        data = [x for x in data if x.get('convo_id')]
        self.send_response(200); self._cors(); self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _handle_volunteer_conv_get(self, params):
        user = params.get('user', [''])[0].strip().replace('..', '').replace('/', '')
        cid  = params.get('id',   [''])[0].strip().replace('..', '').replace('/', '')
        if not user or not cid:
            self.send_response(400); self._cors(); self.end_headers()
            self.wfile.write(b'{"error":"Missing user or id"}'); return
        p = os.path.join(BASE, 'volunteer-logs', user, 'convos', cid + '.jsonl')
        if not os.path.exists(p):
            self.send_response(404); self._cors(); self.end_headers()
            self.wfile.write(b'{"error":"Not found"}'); return
        msgs = []
        with open(p) as f:
            for line in f:
                line = line.strip()
                if not line: continue
                try: e = json.loads(line)
                except: continue
                if e.get('user_msg'):
                    msgs.append({'role': 'user', 'content': e.get('user_msg', '')})
                if e.get('reply'):
                    msgs.append({'role': 'assistant', 'content': e.get('reply', '')})
        self.send_response(200); self._cors(); self.end_headers()
        self.wfile.write(json.dumps({'convo_id': cid, 'messages': msgs}).encode())

    def _handle_capture(self, body):
        tok = self.headers.get('X-Capture-Token', '')
        if tok != CAPTURE_TOKEN:
            self.send_response(401); self._cors(); self.end_headers()
            self.wfile.write(b'{"error":"Unauthorized"}'); return
        claude_id = str(body.get('claude_id', '')).replace('..', '').replace('/', '')
        if not claude_id:
            self.send_response(400); self._cors(); self.end_headers()
            self.wfile.write(b'{"error":"Missing claude_id"}'); return
        cid = 'cap' + claude_id
        incoming_msgs = body.get('messages', [])
        title = body.get('title', 'Untitled')
        os.makedirs(ADMIN_CONVS, exist_ok=True)
        path = os.path.join(ADMIN_CONVS, cid + '.json')
        now = datetime.datetime.utcnow().isoformat() + 'Z'
        if os.path.exists(path):
            try:
                with open(path) as f: conv = json.load(f)
            except:
                conv = {}
        else:
            conv = {}
        stored_msgs = conv.get('messages', [])
        existing_keys = set((m.get('role',''), m.get('content','')) for m in stored_msgs)
        merged = list(stored_msgs)
        for m in incoming_msgs:
            key = (m.get('role',''), m.get('content',''))
            if key not in existing_keys:
                merged.append(m)
                existing_keys.add(key)
        conv['id'] = cid
        conv['title'] = title
        conv['model'] = 'deepseek/deepseek-v4-pro-0813'
        conv['messages'] = merged
        conv['updated_at'] = now
        if 'created_at' not in conv:
            conv['created_at'] = now
        with open(path, 'w') as f:
            json.dump(conv, f, indent=2)
        idx = os.path.join(ADMIN_CONVS, 'index.json')
        index = []
        if os.path.exists(idx):
            try:
                with open(idx) as f: index = json.load(f)
            except: pass
        entry = next((x for x in index if x.get('id') == cid), None)
        if entry:
            entry.update({'title': title, 'model': 'deepseek/deepseek-v4-pro-0813', 'updated_at': now})
        else:
            index.insert(0, {'id': cid, 'title': title, 'model': 'deepseek/deepseek-v4-pro-0813',
                              'created_at': now, 'updated_at': now})
        with open(idx, 'w') as f: json.dump(index, f, indent=2)
        self.send_response(200); self._cors(); self.end_headers()
        self.wfile.write(b'{"ok":true}')

    def _handle_admin_conv_delete(self, body):
        tok = self.headers.get('X-Admin-Token', '')
        if not valid_token(tok):
            self.send_response(401); self._cors(); self.end_headers()
            self.wfile.write(b'{"error":"Unauthorized"}'); return
        cid = body.get('id', '').replace('..', '').replace('/', '')
        if not cid:
            self.send_response(400); self._cors(); self.end_headers()
            self.wfile.write(b'{"error":"Missing id"}'); return
        p = os.path.join(ADMIN_CONVS, cid + '.json')
        if os.path.exists(p):
            os.remove(p)
        idx = os.path.join(ADMIN_CONVS, 'index.json')
        index = []
        if os.path.exists(idx):
            try:
                with open(idx) as f: index = json.load(f)
            except: pass
        index = [x for x in index if x.get('id') != cid]
        with open(idx, 'w') as f: json.dump(index, f, indent=2)
        self.send_response(200); self._cors(); self.end_headers()
        self.wfile.write(b'{"success":true}')

    def _handle_admin_conv_rename(self, body):
        tok = self.headers.get('X-Admin-Token', '')
        if not valid_token(tok):
            self.send_response(401); self._cors(); self.end_headers()
            self.wfile.write(b'{"error":"Unauthorized"}'); return
        cid = body.get('id', '').replace('..', '').replace('/', '')
        title = (body.get('title') or '').strip()
        if not cid or not title:
            self.send_response(400); self._cors(); self.end_headers()
            self.wfile.write(b'{"error":"Missing id or title"}'); return
        p = os.path.join(ADMIN_CONVS, cid + '.json')
        if os.path.exists(p):
            try:
                with open(p) as f: conv = json.load(f)
                conv['title'] = title
                with open(p, 'w') as f: json.dump(conv, f, indent=2)
            except: pass
        idx = os.path.join(ADMIN_CONVS, 'index.json')
        index = []
        if os.path.exists(idx):
            try:
                with open(idx) as f: index = json.load(f)
            except: pass
        for x in index:
            if x.get('id') == cid:
                x['title'] = title
        with open(idx, 'w') as f: json.dump(index, f, indent=2)
        self.send_response(200); self._cors(); self.end_headers()
        self.wfile.write(b'{"success":true}')

    def _handle_admin_import(self, body):
        tok = self.headers.get('X-Admin-Token', '')
        if not valid_token(tok):
            self.send_response(401); self._cors(); self.end_headers()
            self.wfile.write(b'{"error":"Unauthorized"}'); return
        raw   = body.get('raw', '')
        title = body.get('title', '').strip()
        if not raw.strip():
            self.send_response(400); self._cors(); self.end_headers()
            self.wfile.write(b'{"error":"Empty paste"}'); return
        import re as _re
        # Strip known claude.ai UI artifacts line-by-line
        junk = {'show more','pasted','copy','retry','edit','share'}
        raw_lines = []
        prev = None
        for ln in raw.split('\n'):
            s = ln.strip()
            if s.lower() in junk:
                continue
            if s and s == prev:  # drop consecutive duplicate lines
                continue
            raw_lines.append(ln)
            if s:
                prev = s
        cleaned = '\n'.join(raw_lines)
        # Look for explicit turn markers at line start
        marker = _re.compile(r'^\s*(ME|YOU|USER|HUMAN|AI|ASSISTANT|CLAUDE)\s*:',
                             _re.IGNORECASE)
        user_words = {'me','you','user','human'}
        messages = []
        has_markers = any(marker.match(l) for l in cleaned.split('\n'))
        if has_markers:
            cur_role = 'user'
            cur_buf = []
            for line in cleaned.split('\n'):
                m = marker.match(line)
                if m:
                    if cur_buf:
                        messages.append({'role': cur_role,
                                         'content': '\n'.join(cur_buf).strip()})
                        cur_buf = []
                    tag = m.group(1).lower()
                    cur_role = 'user' if tag in user_words else 'assistant'
                    rest = line[m.end():].strip()
                    if rest:
                        cur_buf.append(rest)
                else:
                    cur_buf.append(line)
            if cur_buf:
                messages.append({'role': cur_role,
                                 'content': '\n'.join(cur_buf).strip()})
        else:
            # Fallback: blank-line blocks, alternating (imperfect)
            blocks = [b.strip() for b in cleaned.split('\n\n') if b.strip()]
            role = 'user'
            for b in blocks:
                messages.append({'role': role, 'content': b})
                role = 'assistant' if role == 'user' else 'user'
        messages = [m for m in messages if m['content']]
        if not messages:
            messages = [{'role': 'user', 'content': raw.strip()}]
        now = datetime.datetime.utcnow().isoformat() + 'Z'
        cid = 'adm_' + str(int(time.time())) + '_' + secrets.token_hex(3)
        conv = {
            'id':         cid,
            'title':      title or (messages[0]['content'][:55] if messages else 'Imported'),
            'model':      'imported',
            'messages':   messages,
            'created_at': now,
            'updated_at': now
        }
        os.makedirs(ADMIN_CONVS, exist_ok=True)
        with open(os.path.join(ADMIN_CONVS, cid + '.json'), 'w') as f:
            json.dump(conv, f, indent=2)
        idx = os.path.join(ADMIN_CONVS, 'index.json')
        index = []
        if os.path.exists(idx):
            try:
                with open(idx) as f: index = json.load(f)
            except: pass
        index.insert(0, {'id': cid, 'title': conv['title'],
                         'model': 'imported', 'created_at': now, 'updated_at': now})
        with open(idx, 'w') as f: json.dump(index, f, indent=2)
        self.send_response(200); self._cors(); self.end_headers()
        self.wfile.write(json.dumps({'ok': True, 'id': cid,
                         'message_count': len(messages)}).encode())

    def _cors(self):
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Admin-Token')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')


# --- botcouncil spaces (JOHN thread, session John 11, 6 Oct 2026) ---
# A space is a BotCouncil of its own for someone other than Tony, opened at
#   https://nexus.needpedia.org/botcouncil.html?space=NAME
# with one password. Where things live:
#   settings, private threads, welcome: /home/clearcrow/BC_private/spaces/NAME/
#     (space.json holds the password's fingerprint, the AI key file, the threads)
#   public thread files and library:    /home/clearcrow/Needpedia_Nexus/spaces/NAME/
#   conversations (never on the web):   ADMIN_CONVS/spaces/NAME/
# A space login reaches only its own space. Tony's admin login reaches any
# space when the page names it. The space's AI acts through marked blocks
# (ADD TO, NEW THREAD, TO THREADS, LOG, OPEN THREAD); see the space's GUIDE.txt.
# News a thread has read moves to its ARCHIVE file after each answer.
# Hooked into the Handler from below its class; nothing above was edited.
SP_PRIV = '/home/clearcrow/BC_private/spaces'
SP_PUB  = '/home/clearcrow/Needpedia_Nexus/spaces'
SP_CONV = os.path.join(ADMIN_CONVS, 'spaces')
SP_DAYS = 30
SP_MARK = '== ENTRIES BELOW =='
_sp_tokens = {}
_sp_lock = _bcth.Lock()
_sp_key_cache = {}
_SP_BLOCK = _bcre.compile(r'^[ \t]*===[ \t]*(ADD TO|NEW THREAD|TO THREADS?|LOG|OPEN THREAD)[ \t]*:?[ \t]*([^=\n]*?)[ \t]*===[ \t]*\n(.*?)\n[ \t]*===[ \t]*END[ \t]*===',
                          _bcre.M | _bcre.S | _bcre.I)

def _sp_slug(s):
    s = str(s or '').strip().lower()
    return s if _bcre.fullmatch(r'[a-z0-9][a-z0-9\-]{0,39}', s) else ''

def _sp_cfg(slug):
    slug = _sp_slug(slug)
    if not slug:
        return None
    try:
        with open(os.path.join(SP_PRIV, slug, 'space.json')) as f:
            c = json.load(f)
    except Exception:
        return None
    c['slug'] = slug
    return c

def _sp_save_cfg(c):
    d = dict(c)
    d.pop('slug', None)
    p = os.path.join(SP_PRIV, c['slug'], 'space.json')
    with open(p + '.tmp', 'w') as f:
        json.dump(d, f, indent=1)
    os.replace(p + '.tmp', p)

def _sp_now():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M')

def _sp_dir(c, code):
    priv = (c.get('threads', {}).get(code) or {}).get('private')
    return os.path.join(SP_PRIV if priv else SP_PUB, c['slug'])

def _sp_file(c, code, kind):
    return os.path.join(_sp_dir(c, code), kind + '-' + code + '.txt')

def _sp_cdir(c):
    return os.path.join(SP_CONV, c['slug'])

def _sp_visible(c):
    th = c.get('threads', {})
    rev = set(c.get('revealed', []))
    return [k for k in th if not th[k].get('hidden') or k in rev]

def _sp_append(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    cur = _bc_read(path)
    with open(path, 'a', encoding='utf-8') as f:
        f.write(('' if (not cur or cur.endswith('\n')) else '\n') + text.rstrip() + '\n')

def _sp_unread(c, code):
    t = _bc_read(_sp_file(c, code, 'UPDATES'))
    return t.split(SP_MARK, 1)[1].strip() if SP_MARK in t else ''

def _sp_conv_load(c, cid):
    cid = _bc_label(cid)
    if not cid:
        return None
    try:
        with open(os.path.join(_sp_cdir(c), cid + '.json')) as f:
            return json.load(f)
    except Exception:
        return None

def _sp_conv_write(c, conv):
    cid = _bc_label(conv.get('id'))
    if not cid:
        return False
    d = _sp_cdir(c)
    with _bc_conv_lock:
        os.makedirs(d, exist_ok=True)
        now = _bc_now()
        conv['id'] = cid
        conv['updated_at'] = now
        conv.setdefault('created_at', now)
        p = os.path.join(d, cid + '.json')
        with open(p + '.tmp', 'w') as f:
            json.dump(conv, f, indent=2)
        os.replace(p + '.tmp', p)
        idx = os.path.join(d, 'index.json')
        try:
            with open(idx) as f:
                index = json.load(f)
        except Exception:
            index = []
        info = {'title': conv.get('title', 'Untitled'), 'model': conv.get('model', ''),
                'thread': conv.get('thread', ''), 'updated_at': now}
        e = next((x for x in index if x.get('id') == cid), None)
        if e:
            e.update(info)
        else:
            index.insert(0, dict({'id': cid, 'created_at': conv['created_at']}, **info))
        with open(idx + '.tmp', 'w') as f:
            json.dump(index, f, indent=2)
        os.replace(idx + '.tmp', idx)
    return True

def _sp_conv_delete(c, cid):
    cid = _bc_label(cid)
    d = _sp_cdir(c)
    with _bc_conv_lock:
        p = os.path.join(d, cid + '.json')
        if cid and os.path.exists(p):
            os.remove(p)
        idx = os.path.join(d, 'index.json')
        try:
            with open(idx) as f:
                index = json.load(f)
        except Exception:
            index = []
        index = [x for x in index if x.get('id') != cid]
        if os.path.isdir(d):
            with open(idx + '.tmp', 'w') as f:
                json.dump(index, f, indent=2)
            os.replace(idx + '.tmp', idx)

def _sp_welcome(c):
    # The first time a space is opened, its welcome (WELCOME.txt in its private
    # folder) becomes the first session of its starting thread.
    d = _sp_cdir(c)
    if os.path.exists(os.path.join(d, 'index.json')):
        return
    w = _bc_read(os.path.join(SP_PRIV, c['slug'], 'WELCOME.txt')).strip()
    start = c.get('start', '')
    if not w or start not in c.get('threads', {}):
        return
    _sp_conv_write(c, {'id': 'bc_welcome', 'thread': start, 'model': BC_MODEL,
                       'title': c['threads'][start].get('name', start) + ' · Welcome',
                       'messages': [{'role': 'user', 'kind': 'hidden',
                                     'content': '(The person just opened this space for the first time.)'},
                                    {'role': 'assistant', 'content': w}]})

def _sp_index(c):
    _sp_welcome(c)
    try:
        with open(os.path.join(_sp_cdir(c), 'index.json')) as f:
            return json.load(f)
    except Exception:
        return []

def _sp_threads(c):
    idx = _sp_index(c)
    th = c.get('threads', {})
    start = c.get('start', '')
    out = []
    for k in _sp_visible(c):
        mine = [x for x in idx if x.get('thread') == k]
        out.append({'name': k, 'full': th[k].get('name', k), 'sessions': len(mine),
                    'last': max((x.get('updated_at', '') for x in mine), default=''),
                    'unread': len(_bcre.findall(r'^----- added ', _sp_unread(c, k), _bcre.M)),
                    'pinned': k == start, 'private': bool(th[k].get('private'))})
    out.sort(key=lambda t: (not t['pinned'], th[t['name']].get('order', 50), t['full'].lower()))
    return out

def _sp_system(c, code):
    th = c.get('threads', {})
    if code not in th:
        return None
    tail = lambda s: s if len(s) <= BC_CAP else '[... the oldest part is cut]\n' + s[-BC_CAP:]
    guide = _bc_read(os.path.join(SP_PUB, c['slug'], 'GUIDE.txt'))
    howto = _bc_read(_sp_file(c, 'HOWTO', 'PA')) if 'HOWTO' in th else ''
    names = '; '.join(k + ' = ' + th[k].get('name', k) for k in _sp_visible(c))
    text = ('You are the AI for the "' + th[code].get('name', code) + '" thread (code ' + code + ') in a '
            'BotCouncil space on Tony Brasher\'s Nexus. The documents below are read fresh for every '
            'message, so they are current; you do not need to fetch them.\n'
            '1. The space guide: how this space works. Follow it.\n'
            '2. How to help me: the person\'s own notes on how they want AI to help them.\n'
            '3. This thread\'s notes.\n'
            '4. News other threads left for this thread. Act on it.\n\n'
            '===== 1. SPACE GUIDE =====\n' + guide +
            '\n\n===== 2. HOW TO HELP ME =====\n' + tail(howto))
    if code != 'HOWTO':
        text += '\n\n===== 3. THIS THREAD\'S NOTES (' + code + ') =====\n' + tail(_bc_read(_sp_file(c, code, 'PA')))
    text += ('\n\n===== 4. NEWS FOR ' + code + ' =====\n' + (tail(_sp_unread(c, code)) or '(none)') +
             '\n\nThreads in this space: ' + names + '.')
    return {'role': 'system', 'content': text}

def _sp_council(c):
    try:
        with open(os.path.join(_sp_cdir(c), 'council.json')) as f:
            return json.load(f)
    except Exception:
        return []

def _sp_council_add(c, entry):
    items = _sp_council(c)
    items.append(entry)
    d = _sp_cdir(c)
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, 'council.json')
    with open(p + '.tmp', 'w') as f:
        json.dump(items[-300:], f, indent=1)
    os.replace(p + '.tmp', p)

def _sp_new_thread(c, arg, purpose, sender):
    code, _, full = arg.partition('|')
    code = _bcre.sub(r'[^A-Z0-9]', '', code.upper())[:12]
    full = ' '.join(full.split())[:60] or code
    if len(code) < 2 or code in c.get('threads', {}):
        return None
    c.setdefault('threads', {})[code] = {'name': full, 'order': 50}
    _sp_save_cfg(c)
    os.makedirs(_sp_dir(c, code), exist_ok=True)
    with open(_sp_file(c, code, 'PA'), 'w', encoding='utf-8') as f:
        f.write('NOTES - ' + full + ' (' + code + ')\n'
                'This thread\'s prompt accomplice: its standing notes, read by its AI with every message.\n'
                'Public: nothing private goes in here. Started ' + _sp_now() + ' from the ' + sender + ' thread.\n\n'
                + purpose.strip() + '\n')
    with open(_sp_file(c, code, 'UPDATES'), 'w', encoding='utf-8') as f:
        f.write('UPDATES - ' + full + ' (' + code + ')\nNews other threads left for this thread. Its AI reads '
                'them with its next answer; then they move to ARCHIVE-' + code + '.txt.\n\n' + SP_MARK + '\n')
    _sp_append(_sp_file(c, code, 'LOG'), '----- ' + _sp_now() + ' -----\nThread started from the ' + sender + ' thread.')
    return code

def _sp_actions(c, sender, content):
    done = {'saved': [], 'new': [], 'news': [], 'log': False, 'open': ''}
    with _sp_lock:
        for m in _SP_BLOCK.finditer(content):
            kind = ' '.join(m.group(1).upper().split())
            arg, body = m.group(2).strip(), m.group(3).strip()
            th = c.get('threads', {})
            if not body:
                continue
            if kind == 'ADD TO':
                t = arg.upper()
                if t in th:
                    _sp_append(_sp_file(c, t, 'PA'), '\n----- added ' + _sp_now() + ' by the ' + sender + ' thread -----\n' + body)
                    _sp_append(_sp_file(c, t, 'LOG'), '----- ' + _sp_now() + ' -----\nAdded to its notes, from the ' + sender + ' thread.')
                    done['saved'].append(t)
            elif kind == 'NEW THREAD':
                code = _sp_new_thread(c, arg, body, sender)
                if code:
                    done['new'].append(code)
            elif kind.startswith('TO THREAD'):
                vis = _sp_visible(c)
                raw = arg.upper()
                if raw in ('ALL', 'EVERY THREAD', 'ALL THREADS', 'EVERYONE'):
                    to = [k for k in vis if k != sender]
                else:
                    to = []
                    for k in _bcre.split(r'[,\s]+', raw):
                        if k in vis and k != sender and k not in to:
                            to.append(k)
                for k in to:
                    _sp_append(_sp_file(c, k, 'UPDATES'), '\n----- added ' + datetime.date.today().isoformat() + ' -----\n'
                               'From the ' + sender + ' thread, ' + _sp_now() + '.\n' + body)
                if to:
                    _sp_council_add(c, {'id': 'bc' + str(int(time.time() * 1000)) + secrets.token_hex(2),
                                        'ts': _bc_now(), 'kind': 'post', 'from': sender, 'to': to, 'text': body,
                                        'delivered': {k: 'posted' for k in to}, 'replies': {}})
                    done['news'].append(to)
            elif kind == 'LOG':
                _sp_append(_sp_file(c, sender, 'LOG'), '----- ' + _sp_now() + ' -----\n' + body)
                done['log'] = True
            elif kind == 'OPEN THREAD':
                t = arg.upper()
                if t in th:
                    if th[t].get('hidden') and t not in c.get('revealed', []):
                        c.setdefault('revealed', []).append(t)
                        _sp_save_cfg(c)
                    done['open'] = t
    return done

def _sp_archive(c, code, snap):
    if not snap:
        return
    with _sp_lock:
        p = _sp_file(c, code, 'UPDATES')
        cur = _bc_read(p)
        if SP_MARK not in cur:
            return
        head, rest = cur.split(SP_MARK, 1)
        if snap not in rest:
            return
        rest = rest.replace(snap, '', 1).strip()
        with open(p + '.tmp', 'w', encoding='utf-8') as f:
            f.write(head + SP_MARK + '\n' + (rest + '\n' if rest else ''))
        os.replace(p + '.tmp', p)
        _sp_append(_sp_file(c, code, 'ARCHIVE'), '\n----- read ' + _sp_now() + ' -----\n' + snap)

def _sp_key(c):
    t = _bc_read(c.get('key_file', ''))
    m = _bcre.search(r'sk-or-[A-Za-z0-9_\-]+', t)
    return m.group(0) if m else t.strip()

def _sp_key_info(c):
    hit = _sp_key_cache.get(c['slug'])
    if hit and time.time() - hit[0] < 60:
        return hit[1]
    req = urllib.request.Request('https://openrouter.ai/api/v1/key',
                                 headers={'Authorization': 'Bearer ' + _sp_key(c)})
    d = (json.loads(urllib.request.urlopen(req, timeout=20).read()) or {}).get('data') or {}
    limit, spent, left = d.get('limit'), d.get('usage'), d.get('limit_remaining')
    if left is None and isinstance(limit, (int, float)) and isinstance(spent, (int, float)):
        left = limit - spent
    out = {'limit': limit, 'spent': spent, 'left': left}
    _sp_key_cache[c['slug']] = (time.time(), out)
    return out

def _sp_search(c, q, mode, limit):
    q = (q or '').strip().lower()
    if not q:
        return []
    terms = [q] if mode == 'phrase' else [w for w in q.split() if w][:12]
    pad = 160 if mode == 'phrase' else 400
    d = _sp_cdir(c)
    meta = {x.get('id'): x for x in _sp_index(c)}
    hits = []
    try:
        names = os.listdir(d)
    except Exception:
        names = []
    for fn in names:
        if not fn.endswith('.json') or fn in ('index.json', 'council.json'):
            continue
        try:
            with open(os.path.join(d, fn)) as f:
                conv = json.load(f)
        except Exception:
            continue
        text = '\n'.join(str(m.get('content', '')) for m in conv.get('messages', []) if m.get('kind') != 'hidden')
        low = text.lower()
        found = [t for t in terms if t in low]
        if not found:
            continue
        snips = []
        for t in found[:3]:
            i = low.find(t)
            a, b = max(0, i - pad), min(len(text), i + len(t) + pad)
            snips.append(('...' if a else '') + ' '.join(text[a:b].split()) + ('...' if b < len(text) else ''))
        cid = conv.get('id', fn[:-5])
        m = meta.get(cid, {})
        hits.append({'id': cid, 'title': conv.get('title', m.get('title', 'Untitled')),
                     'thread': conv.get('thread', m.get('thread', '')),
                     'updated_at': conv.get('updated_at', m.get('updated_at', '')),
                     'score': len(found), 'snippets': snips})
    hits.sort(key=lambda h: (h['score'], h['updated_at']), reverse=True)
    try:
        limit = max(1, min(int(limit), 100))
    except Exception:
        limit = 50
    return hits[:limit]

def _sp_op(c, action, body):
    if action == 'bc-threads':
        return {'threads': _sp_threads(c)}
    if action == 'bc-unread':
        n = str(body.get('name', '')).upper()
        if n not in c.get('threads', {}):
            return {'error': 'no such thread'}
        return {'name': n, 'text': _sp_unread(c, n)}
    if action == 'bc-council':
        return {'council': _sp_council(c)[-60:], 'now': _bc_now()}
    if action == 'bc-key':
        try:
            return _sp_key_info(c)
        except Exception as e:
            return {'error': str(e)[:200]}
    if action == 'bc-job':
        j = _bc_jobs.get(str(body.get('id', '')))
        if not j:
            return {'status': 'missing'}
        return {'status': j['status'], 'data': j.get('data')}
    if action == 'bc-search':
        return {'results': _sp_search(c, body.get('q', ''), body.get('mode', 'phrase'), body.get('limit', 50))}
    return {'error': 'not available in a space: ' + str(action)}

def _sp_run(jid, c, thread, req, sid, snap):
    try:
        data = json.loads(urllib.request.urlopen(req, timeout=900).read())
    except urllib.error.HTTPError as e:
        try:
            data = json.loads(e.read())
        except Exception:
            data = {'error': 'AI service answered with code ' + str(e.code)}
    except Exception as e:
        data = {'error': str(e)}
    if not isinstance(data, dict):
        data = {'error': 'unexpected answer from the AI service'}
    try:
        content = ((data.get('choices') or [{}])[0].get('message') or {}).get('content') or ''
    except Exception:
        content = ''
    if content:
        try:
            c2 = _sp_cfg(c['slug']) or c
            acts = _sp_actions(c2, thread, content)
            data['space'] = acts
            if acts['news']:
                data['botcouncil'] = acts['news']
            _sp_archive(c2, thread, snap)
        except Exception as e:
            data['space'] = {'error': str(e)[:200]}
    if sid:
        try:
            conv = _sp_conv_load(c, sid)
            if conv is not None:
                conv.setdefault('messages', []).append(_bc_reply_parts(data))
                conv.pop('pending', None)
                _sp_conv_write(c, conv)
                data['bc_saved'] = True
        except Exception:
            pass
    _bc_jobs[jid] = {'status': 'done', 'data': data, 't': time.time()}

def _sp_chat(c, body):
    key = _sp_key(c)
    if not key:
        return 500, {'error': 'This space has no AI key.'}
    url = 'https://openrouter.ai/api/v1/chat/completions'
    headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key,
               'HTTP-Referer': 'https://nexus.needpedia.org', 'X-Title': 'Needpedia BotCouncil space'}
    thread = str(body.get('thread') or '').upper()
    src = [m for m in body.get('messages', []) if isinstance(m, dict) and m.get('role') in ('system', 'user', 'assistant')]
    if not thread:
        # a plain question, such as the Ask assistant button: passed on as it is
        msgs = [{'role': m['role'], 'content': str(m.get('content', ''))} for m in src]
        req = urllib.request.Request(url, data=json.dumps({'model': BC_MODEL, 'messages': msgs}).encode(), headers=headers)
        try:
            return 200, json.loads(urllib.request.urlopen(req, timeout=120).read())
        except urllib.error.HTTPError as e:
            try:
                return e.code, json.loads(e.read())
            except Exception:
                return e.code, {'error': 'AI service answered with code ' + str(e.code)}
        except Exception as e:
            return 500, {'error': str(e)}
    sysmsg = _sp_system(c, thread)
    if not sysmsg:
        return 400, {'error': 'No such thread in this space.'}
    snap = _sp_unread(c, thread)
    now = time.time()
    for k in [k for k, v in list(_bc_jobs.items()) if now - v.get('t', now) > 3600]:
        _bc_jobs.pop(k, None)
    jid = 'job' + secrets.token_hex(8)
    sid = _bc_label(body.get('session'))
    talk = [m for m in src if m['role'] in ('user', 'assistant')]
    if sid:
        conv = _sp_conv_load(c, sid) or {'id': sid}
        old = conv.get('messages', [])
        new = []
        for i, m in enumerate(talk):
            o = old[i] if i < len(old) else None
            if o and o.get('role') == m.get('role') and o.get('content') == m.get('content'):
                new.append(o)
            else:
                e = {'role': m['role'], 'content': str(m.get('content', ''))}
                if m.get('kind') in ('hidden', 'answer'):
                    e['kind'] = m['kind']
                new.append(e)
        conv.update({'messages': new, 'thread': thread, 'model': BC_MODEL,
                     'title': str(body.get('title') or conv.get('title') or 'New session')[:200],
                     'pending': {'since': _bc_now(), 'job': jid}})
        _sp_conv_write(c, conv)
    msgs = []
    for m in talk:
        e = {'role': m['role'], 'content': str(m.get('content', ''))}
        if msgs and e['role'] == 'user' and msgs[-1]['role'] == 'user':
            msgs[-1] = {'role': 'user', 'content': msgs[-1]['content'] + '\n\n' + e['content']}
        else:
            msgs.append(e)
    for i in range(len(msgs) - 1, -1, -1):
        if msgs[i]['role'] == 'user':
            msgs[i] = {'role': 'user', 'content': msgs[i]['content'] + '\n\n(Time now: ' + _sp_now() + ')'}
            break
    payload = {'model': BC_MODEL, 'usage': {'include': True},
               'messages': [sysmsg] + ([WEB_SYS] if body.get('web') else []) + msgs}
    if body.get('web'):
        payload.update({'tools': WEB_TOOLS, 'max_tool_calls': 6})
    if sid:
        payload['session_id'] = sid
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers)
    _bc_jobs[jid] = {'status': 'working', 't': now}
    _bcth.Thread(target=_sp_run, args=(jid, c, thread, req, sid, snap), daemon=True).start()
    return 200, {'job': jid}

def _sp_reply(h, code, obj):
    h.send_response(code)
    h._cors()
    h.end_headers()
    h.wfile.write(json.dumps(obj).encode())

def _sp_ctx(h, hint):
    # (True, space) for a space login, or Tony's login on a page naming a space.
    # (True, None) for a space login that has run out. (False, None): not a space request.
    tok = h.headers.get('X-Admin-Token', '')
    v = _sp_tokens.get(tok) if tok else None
    if v:
        if time.time() > v[1]:
            _sp_tokens.pop(tok, None)
            return True, None
        return True, _sp_cfg(v[0])
    if _sp_slug(hint) and valid_token(tok):
        return True, _sp_cfg(hint)
    return False, None

def _sp_h_ops(h, c, body):
    _sp_reply(h, 200, _sp_op(c, str(body.get('action', '')), body))

def _sp_h_chat(h, c, body):
    code, obj = _sp_chat(c, body)
    _sp_reply(h, code, obj)

def _sp_h_convs_get(h, c, params):
    _sp_reply(h, 200, _sp_index(c))

def _sp_h_conv_get(h, c, params):
    conv = _sp_conv_load(c, (params.get('id') or [''])[0])
    if conv is None:
        _sp_reply(h, 404, {'error': 'Not found'})
    else:
        _sp_reply(h, 200, conv)

def _sp_h_convs_post(h, c, body):
    conv = body.get('conversation') or {}
    if not isinstance(conv, dict) or not _bc_label(conv.get('id')):
        return _sp_reply(h, 400, {'error': 'Missing conversation.id'})
    _sp_conv_write(c, conv)
    _sp_reply(h, 200, {'ok': True})

def _sp_h_conv_delete(h, c, body):
    _sp_conv_delete(c, body.get('id'))
    _sp_reply(h, 200, {'success': True})

def _sp_h_conv_rename(h, c, body):
    conv = _sp_conv_load(c, body.get('id'))
    t = str(body.get('title') or '').strip()
    if conv is None or not t:
        return _sp_reply(h, 400, {'error': 'Missing id or title'})
    conv['title'] = t[:200]
    _sp_conv_write(c, conv)
    _sp_reply(h, 200, {'success': True})

def _sp_hook(name, impl, kind):
    orig = getattr(Handler, name)
    def wrapped(self, arg):
        if kind == 'body':
            hint = arg.get('space', '') if isinstance(arg, dict) else ''
        else:
            hint = (arg.get('space') or [''])[0] if isinstance(arg, dict) else ''
        hit, c = _sp_ctx(self, hint)
        if not hit:
            return orig(self, arg)
        if not c:
            return _sp_reply(self, 401, {'error': 'Unauthorized'})
        try:
            return impl(self, c, arg)
        except Exception as e:
            return _sp_reply(self, 500, {'error': str(e)[:300]})
    setattr(Handler, name, wrapped)

for _n, _f, _k in (('_handle_admin_ops', _sp_h_ops, 'body'),
                   ('_handle_admin_chat_proxy', _sp_h_chat, 'body'),
                   ('_handle_admin_convs_get', _sp_h_convs_get, 'params'),
                   ('_handle_admin_conv_get', _sp_h_conv_get, 'params'),
                   ('_handle_admin_convs_post', _sp_h_convs_post, 'body'),
                   ('_handle_admin_conv_delete', _sp_h_conv_delete, 'body'),
                   ('_handle_admin_conv_rename', _sp_h_conv_rename, 'body')):
    _sp_hook(_n, _f, _k)

_sp_orig_auth = Handler._handle_admin_auth
def _sp_auth(self, body):
    if isinstance(body, dict) and body.get('space'):
        c = _sp_cfg(body.get('space'))
        pw = str(body.get('password', '')).strip().lower()
        if c and c.get('password_sha256') and hashlib.sha256(pw.encode()).hexdigest() == c['password_sha256']:
            tok = 'sp' + secrets.token_hex(31)
            _sp_tokens[tok] = (c['slug'], time.time() + SP_DAYS * 86400)
            return _sp_reply(self, 200, {'success': True, 'token': tok, 'space': c['slug']})
        return _sp_reply(self, 401, {'success': False, 'error': 'Invalid password'})
    return _sp_orig_auth(self, body)
Handler._handle_admin_auth = _sp_auth
# --- end botcouncil spaces ---


# --- botcouncil piece 2 (JOHN thread, session John 11, 6 Oct 2026) ---
# - "Other" talks, not tied to a thread. The page sends {"other": true}. In
#   Tony's window the AI gets his botskill post; in a space it gets the space
#   guide and the person's How to help me.
# - Open-session warnings move out of prompt accomplices: a window session's
#   first answer leaves a note in the thread's updates post; closing the
#   session (a closing handoff, or "Mark session closed") takes it back out.
# - A space's welcome shows as written by the person who set the space up.
# - The window AI is told a file card shows exactly where it writes it.
# Later definitions replace earlier ones of the same name; nothing above was edited.
_BC_OTHER_HEAD = ('This is an "Other" talk in Tony Brasher\'s BotCouncil window on his Nexus: a talk not tied '
                  'to any thread. Below is his botskill post: how he wants AI to work with him. Follow it. If '
                  'something here belongs in a thread, say which one. This window shows code in boxes with a '
                  'Copy button. A file: a line ===FILE: name.ext===, then the contents, then a line ===END===; '
                  'it shows as a Download button exactly where you put it, so put it in the step that uses it.'
                  '\n\n===== BOTSKILL POST =====\n')

def _bc_other_system():
    post = _bc_read(os.path.join(BC_NEXUS, 'working-with-tony.txt'))
    return {'role': 'system', 'content': _BC_OTHER_HEAD + post[:BC_CAP]}

_bc_system_john11 = _bc_system
def _bc_system(name):
    s = _bc_system_john11(name)
    if s:
        s = dict(s)
        s['content'] = s['content'].replace(
            'lands in his Downloads folder. ',
            'lands in his Downloads folder. The card shows exactly where you put the block, so put each '
            'file in the step that uses it; never say it is at the bottom. ', 1)
    return s

def _bc_note_add(name, text):
    p = os.path.join(BC_NEXUS, 'public', 'UPDATES-' + name + '.md')
    if not os.path.isfile(p):
        return ''
    cur = _bc_read(p)
    block = (('' if (not cur or cur.endswith('\n')) else '\n') + '\n----- added ' +
             datetime.date.today().isoformat() + ' -----\n' + text.strip() + '\n')
    with open(p, 'a', encoding='utf-8') as f:
        f.write(block)
    return block

def _bc_note_remove(name, block):
    p = os.path.join(BC_NEXUS, 'public', 'UPDATES-' + str(name or '') + '.md')
    if not block or not os.path.isfile(p):
        return False
    cur = _bc_read(p)
    if block not in cur:
        return False
    with open(p, 'w', encoding='utf-8') as f:
        f.write(cur.replace(block, '', 1))
    return True

def _bc_session_note(name, title, link, now):
    return ('tags: botcouncil-session, open\n'
            'From the BotCouncil window. To the ' + name + ' thread. ' + now + '.\n'
            'BOTCOUNCIL SESSION OPEN: this thread was continued in Tony\'s BotCouncil window on his Nexus. '
            'Session: "' + title + '".\n'
            'Open it (Tony\'s admin login): ' + link + '\n'
            'AI on another site: tell Tony before anything else and give him that link. He wraps the '
            'session up there and brings its closing handoff back. This note is taken out when that '
            'session closes.')

def _bc_session_mark(thread, sid, title, reply_text):
    name = str(thread or '').upper()
    sid = _bcre.sub(r'[^A-Za-z0-9_\-]', '', str(sid or ''))[:80]
    title = ' '.join(str(title or 'Untitled').split())[:120]
    if not sid or not _bcre.fullmatch(r'[A-Z0-9]+', name):
        return
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    link = BC_PAGE_URL + '?thread=' + name + '&session=' + sid
    with _bc_lock:
        d = _bc_sess_load()
        s = d.get(sid)
        if s is None:
            s = {'thread': name, 'started': now, 'closed': '', 'title': title,
                 'note': _bc_note_add(name, _bc_session_note(name, title, link, now))}
            d[sid] = s
        if not s.get('closed') and reply_text and _BC_HANDOFF.search(reply_text):
            s['closed'] = now
            _bc_note_remove(s.get('thread', name), s.get('note', ''))
        _bc_sess_save(d)

def _bc_close_session(body):
    sid = _bc_label(body.get('session'), 80)
    if not sid:
        return {'status': 'no session given'}
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    with _bc_lock:
        d = _bc_sess_load()
        s = d.get(sid)
        if not s:
            return {'status': 'not marked as started, so nothing to close'}
        if s.get('closed'):
            return {'status': 'already closed ' + s['closed']}
        s['closed'] = now
        removed = _bc_note_remove(s.get('thread', ''), s.get('note', ''))
        _bc_sess_save(d)
    return {'status': 'closed' + ('' if removed else ' (it had no open-session note to take out)'),
            'thread': s.get('thread', '')}

_bc_proxy_john11 = Handler._handle_admin_chat_proxy
def _bc_proxy_other(self, body):
    if (isinstance(body, dict) and body.get('other') and not body.get('thread') and not body.get('space')
            and valid_token(self.headers.get('X-Admin-Token', ''))):
        body = dict(body)
        body['messages'] = [_bc_other_system()] + [
            {'role': m.get('role'), 'content': m.get('content', '')}
            for m in body.get('messages', []) if isinstance(m, dict) and m.get('role') in ('user', 'assistant')]
    return _bc_proxy_john11(self, body)
Handler._handle_admin_chat_proxy = _bc_proxy_other

_SP_WELCOME_HIDDEN = ('(The person just opened this space for the first time. The message below was written '
                      'to them by {WHO}, who set this space up, and shows in the window as from {WHO}. You are '
                      'the AI and come in after it.)')

def _sp_welcome(c):
    d = _sp_cdir(c)
    if os.path.exists(os.path.join(d, 'index.json')):
        return
    w = _bc_read(os.path.join(SP_PRIV, c['slug'], 'WELCOME.txt')).strip()
    start = c.get('start', '')
    if not w or start not in c.get('threads', {}):
        return
    who = c.get('welcome_from') or 'Tony'
    _sp_conv_write(c, {'id': 'bc_welcome', 'thread': start, 'model': BC_MODEL,
                       'title': c['threads'][start].get('name', start) + ' · Welcome',
                       'messages': [{'role': 'user', 'kind': 'hidden', 'content': _SP_WELCOME_HIDDEN.replace('{WHO}', who)},
                                    {'role': 'assistant', 'kind': 'note', 'from': who, 'content': w}]})

_sp_actions_john11 = _sp_actions
def _sp_actions(c, sender, content):
    if sender not in c.get('threads', {}):
        # an Other talk: it can save to threads and start them, but has no log of its own
        content = _bcre.sub(r'^[ \t]*===[ \t]*LOG[ \t]*===[ \t]*\n.*?\n[ \t]*===[ \t]*END[ \t]*===', '',
                            content, flags=_bcre.M | _bcre.S | _bcre.I)
        sender = 'OTHER'
    return _sp_actions_john11(c, sender, content)

def _sp_system_other(c):
    th = c.get('threads', {})
    tail = lambda s: s if len(s) <= BC_CAP else '[... the oldest part is cut]\n' + s[-BC_CAP:]
    guide = _bc_read(os.path.join(SP_PUB, c['slug'], 'GUIDE.txt'))
    howto = _bc_read(_sp_file(c, 'HOWTO', 'PA')) if 'HOWTO' in th else ''
    names = '; '.join(k + ' = ' + th[k].get('name', k) for k in _sp_visible(c))
    return {'role': 'system', 'content': (
        'You are the AI in an "Other" talk in a BotCouncil space on Tony Brasher\'s Nexus: a talk not tied '
        'to any thread. The documents below are read fresh for every message.\n'
        '1. The space guide: how this space works. Follow it.\n'
        '2. How to help me: the person\'s own notes on how they want AI to help them.\n'
        'If something here belongs in a thread, say which one; with their OK, save it there or start a '
        'new thread with the marked blocks.\n\n'
        '===== 1. SPACE GUIDE =====\n' + guide +
        '\n\n===== 2. HOW TO HELP ME =====\n' + tail(howto) +
        '\n\nThreads in this space: ' + names + '.')}

_sp_chat_john11 = _sp_chat
def _sp_chat(c, body):
    if body.get('thread') or not body.get('other'):
        return _sp_chat_john11(c, body)
    key = _sp_key(c)
    if not key:
        return 500, {'error': 'This space has no AI key.'}
    headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key,
               'HTTP-Referer': 'https://nexus.needpedia.org', 'X-Title': 'Needpedia BotCouncil space'}
    now = time.time()
    for k in [k for k, v in list(_bc_jobs.items()) if now - v.get('t', now) > 3600]:
        _bc_jobs.pop(k, None)
    jid = 'job' + secrets.token_hex(8)
    sid = _bc_label(body.get('session'))
    talk = [m for m in body.get('messages', []) if isinstance(m, dict) and m.get('role') in ('user', 'assistant')]
    if sid:
        conv = _sp_conv_load(c, sid) or {'id': sid}
        old = conv.get('messages', [])
        new = []
        for i, m in enumerate(talk):
            o = old[i] if i < len(old) else None
            if o and o.get('role') == m.get('role') and o.get('content') == m.get('content'):
                new.append(o)
            else:
                e = {'role': m['role'], 'content': str(m.get('content', ''))}
                if m.get('kind') in ('hidden', 'answer'):
                    e['kind'] = m['kind']
                new.append(e)
        conv.update({'messages': new, 'thread': '', 'model': BC_MODEL,
                     'title': str(body.get('title') or conv.get('title') or 'Other talk')[:200],
                     'pending': {'since': _bc_now(), 'job': jid}})
        _sp_conv_write(c, conv)
    msgs = []
    for m in talk:
        e = {'role': m['role'], 'content': str(m.get('content', ''))}
        if msgs and e['role'] == 'user' and msgs[-1]['role'] == 'user':
            msgs[-1] = {'role': 'user', 'content': msgs[-1]['content'] + '\n\n' + e['content']}
        else:
            msgs.append(e)
    for i in range(len(msgs) - 1, -1, -1):
        if msgs[i]['role'] == 'user':
            msgs[i] = {'role': 'user', 'content': msgs[i]['content'] + '\n\n(Time now: ' + _sp_now() + ')'}
            break
    payload = {'model': BC_MODEL, 'usage': {'include': True},
               'messages': [_sp_system_other(c)] + ([WEB_SYS] if body.get('web') else []) + msgs}
    if body.get('web'):
        payload.update({'tools': WEB_TOOLS, 'max_tool_calls': 6})
    if sid:
        payload['session_id'] = sid
    req = urllib.request.Request('https://openrouter.ai/api/v1/chat/completions',
                                 data=json.dumps(payload).encode(), headers=headers)
    _bc_jobs[jid] = {'status': 'working', 't': now}
    _bcth.Thread(target=_sp_run, args=(jid, c, '', req, sid, ''), daemon=True).start()
    return 200, {'job': jid}
# --- end botcouncil piece 2 ---


if __name__ == '__main__':
    print(f'Order server on :{PORT}')
    http.server.ThreadingHTTPServer(('', PORT), Handler).serve_forever()
