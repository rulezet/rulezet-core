"""starfield_core.py — storing and reading Starfield runs (see
app/core/db_class/starfield.py). The score is computed in the browser, so
everything sent is checked and bounded here; it can still be forged by a
determined player — fine for an easter egg, keep it in mind when reading it.
"""
import datetime
import re

from sqlalchemy import func

from app import db
from app.core.db_class.starfield import StarfieldRun
from app.core.db_class.user import User

MODES = ('level', 'endless')
SHIPS = ('yara', 'suricata', 'sigma', 'zeek')
DIFFICULTIES = ('analyst', 'hunter', 'redteam')
CONTROLS = ('classic', 'twin')
MAX_SCORE = 50_000_000
MIN_SECONDS_BETWEEN_RUNS = 3

_ID_RE = re.compile(r'^[A-Za-z0-9-]{8,36}$')
_KEY_RE = re.compile(r'^[a-z0-9_-]{1,32}$')


def _int(value, low=0, high=10_000_000):
    try:
        return max(low, min(high, int(value)))
    except (TypeError, ValueError):
        return low


def _text(value, length):
    return str(value)[:length] if value not in (None, '') else None


def _choice(value, allowed):
    return value if value in allowed else None


def _counts(value, max_keys=40):
    """{short key: count} — e.g. shots per weapon, kills per malware type."""
    if not isinstance(value, dict):
        return {}
    out = {}
    for k, v in list(value.items())[:max_keys]:
        if isinstance(k, str) and _KEY_RE.match(k):
            out[k] = _int(v, 0, 1_000_000)
    return out


def _details(data):
    stats = data.get('stats') if isinstance(data.get('stats'), dict) else {}
    crit = data.get('crit') if isinstance(data.get('crit'), list) else []
    return {
        'crit': [{'label': _text(c.get('label'), 120), 'ok': bool(c.get('ok'))} for c in crit[:6] if isinstance(c, dict)],
        'hp_left': _int(data.get('hpLeft'), 0, 50),
        'max_hp': _int(data.get('maxHp'), 0, 50),
        'bombs_left': _int(data.get('bombsLeft'), 0, 50),
        'boss_name': _text(data.get('bossName'), 60),
        'upgrades': _counts(data.get('upgrades')),
        'weapons': [w for w in (data.get('weapons') or [])[:8] if isinstance(w, str) and _KEY_RE.match(w)],
        'assist': bool(data.get('assist')),
        'campaign_stars': _int(data.get('campaignStars'), 0, 1000),
        'campaign_bytes': _int(data.get('campaignBytes')),
        'shots': _counts(stats.get('shots')),
        'dashes': _int(stats.get('dashes')),
        'bombs': _int(stats.get('bombs')),
        'specials': _int(stats.get('specials')),
        'weapon_switches': _int(stats.get('weaponSwitches')),
        'pickups': _counts(stats.get('pickups')),
        'kills_by': _counts(stats.get('killsBy')),
    }


def record_run(data, user_id=None):
    """Store one finished run. Returns (run, error)."""
    if not isinstance(data, dict):
        return None, 'Invalid payload.'
    player_id = data.get('player')
    if not isinstance(player_id, str) or not _ID_RE.match(player_id):
        return None, 'Invalid player id.'
    mode = _choice(data.get('mode'), MODES)
    if not mode:
        return None, 'Invalid mode.'
    score = _int(data.get('score'), 0, MAX_SCORE + 1)
    if score > MAX_SCORE:
        return None, 'Score out of range.'

    last = (StarfieldRun.query.filter_by(player_id=player_id)
            .order_by(StarfieldRun.created_at.desc()).first())
    if last and last.created_at:
        last_at = last.created_at if last.created_at.tzinfo else last.created_at.replace(tzinfo=datetime.timezone.utc)
        if (datetime.datetime.now(tz=datetime.timezone.utc) - last_at).total_seconds() < MIN_SECONDS_BETWEEN_RUNS:
            return None, 'Too many runs.'

    run = StarfieldRun(
        user_id=user_id,
        player_id=player_id,
        mode=mode,
        world=_int(data.get('world'), 0, 10) if mode == 'level' else None,
        level_index=_int(data.get('levelIndex'), 0, 10) if mode == 'level' else None,
        level_name=_text(data.get('levelName'), 80),
        level_kind=_text(data.get('levelKind'), 20),
        won=bool(data.get('won')),
        reason=_text(data.get('reason'), 120),
        score=score,
        stars=_int(data.get('stars'), 0, 3),
        wave=_int(data.get('wave'), 0, 10_000),
        kills=_int(data.get('kills')),
        hits=_int(data.get('hits')),
        max_combo=_int(data.get('maxCombo')),
        bytes=_int(data.get('bytes')),
        time_s=_int(data.get('time'), 0, 86_400),
        ship=_choice(data.get('ship'), SHIPS),
        difficulty=_choice(data.get('difficulty'), DIFFICULTIES),
        controls=_choice(data.get('controls'), CONTROLS),
        details=_details(data),
    )
    db.session.add(run)
    db.session.commit()
    if user_id:
        # Badges are evaluated on the profile's gamification row — make sure a
        # player who never contributed has one, so the hidden badges can unlock.
        from app.features.account.account_core import get_or_create_gamification_profile
        get_or_create_gamification_profile(user_id)
    return run, None


# ── Admin views ──────────────────────────────────────────────────────────────

def _player_key(run):
    return f'user:{run.user_id}' if run.user_id else f'anon:{run.player_id}'


def _user_names(user_ids):
    users = User.query.filter(User.id.in_(user_ids)).all() if user_ids else []
    return {u.id: (u.username or f'{u.first_name} {u.last_name}'.strip() or f'User {u.id}') for u in users}


def list_players():
    """One row per player — a logged-in user (all browsers together) or an
    anonymous browser — with a summary of their runs, most recent first."""
    runs = StarfieldRun.query.order_by(StarfieldRun.created_at.asc()).all()
    players = {}
    for r in runs:
        key = _player_key(r)
        p = players.setdefault(key, {
            'key': key, 'user_id': r.user_id, 'player_id': None if r.user_id else r.player_id,
            'runs': 0, 'wins': 0, 'kills': 0, 'time_s': 0, 'first_played': r.created_at, 'last_played': r.created_at,
            'best_level_stars': {}, 'best_endless': None, 'ships': {}, 'difficulties': {},
        })
        p['runs'] += 1
        p['wins'] += 1 if r.won else 0
        p['kills'] += r.kills or 0
        p['time_s'] += r.time_s or 0
        p['last_played'] = r.created_at
        if r.ship:
            p['ships'][r.ship] = p['ships'].get(r.ship, 0) + 1
        if r.difficulty:
            p['difficulties'][r.difficulty] = p['difficulties'].get(r.difficulty, 0) + 1
        if r.mode == 'level' and r.won:
            k = f'{r.world}-{r.level_index}'
            p['best_level_stars'][k] = max(p['best_level_stars'].get(k, 0), r.stars or 0)
        if r.mode == 'endless' and (p['best_endless'] is None or r.score > p['best_endless']['score']):
            p['best_endless'] = {'score': r.score, 'wave': r.wave}

    names = _user_names([p['user_id'] for p in players.values() if p['user_id']])
    out = []
    for p in players.values():
        out.append({
            'key': p['key'],
            'name': names.get(p['user_id']) if p['user_id'] else 'Anonymous',
            'user_id': p['user_id'],
            'player_id': p['player_id'],
            'runs': p['runs'],
            'wins': p['wins'],
            'win_rate': round(100 * p['wins'] / p['runs']) if p['runs'] else 0,
            'kills': p['kills'],
            'time_s': p['time_s'],
            'levels_cleared': len(p['best_level_stars']),
            'stars': sum(p['best_level_stars'].values()),
            'best_endless': p['best_endless'],
            'favorite_ship': max(p['ships'], key=p['ships'].get) if p['ships'] else None,
            'difficulty': max(p['difficulties'], key=p['difficulties'].get) if p['difficulties'] else None,
            'first_played': p['first_played'].isoformat() if p['first_played'] else None,
            'last_played': p['last_played'].isoformat() if p['last_played'] else None,
        })
    out.sort(key=lambda p: p['last_played'] or '', reverse=True)
    return out


def player_runs(key, limit=500):
    """Every run of one player (key = 'user:<id>' or 'anon:<player id>'), newest first."""
    kind, _, value = (key or '').partition(':')
    query = StarfieldRun.query
    if kind == 'user' and value.isdigit():
        query = query.filter(StarfieldRun.user_id == int(value))
    elif kind == 'anon' and _ID_RE.match(value):
        query = query.filter(StarfieldRun.user_id.is_(None), StarfieldRun.player_id == value)
    else:
        return None
    return [r.to_json() for r in query.order_by(StarfieldRun.created_at.desc()).limit(limit).all()]


def overview():
    total = db.session.query(func.count(StarfieldRun.id)).scalar() or 0
    top_endless = (StarfieldRun.query.filter_by(mode='endless')
                   .order_by(StarfieldRun.score.desc()).limit(10).all())
    names = _user_names([r.user_id for r in top_endless if r.user_id])
    return {
        'runs': total,
        'top_endless': [dict(r.to_json(), name=names.get(r.user_id) if r.user_id else 'Anonymous',
                             key=_player_key(r)) for r in top_endless],
    }
