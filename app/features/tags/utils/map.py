_GALAXY_ICON_MAP = {
    'android':           'fab fa-android',
    'battery-full':      'fas fa-battery-full',
    'btc':               'fab fa-btc',
    'bug':               'fas fa-bug',
    'bullseye':          'fas fa-bullseye',
    'cart-arrow-down':   'fas fa-cart-arrow-down',
    'certificate':       'fas fa-certificate',
    'chess-pawn':        'fas fa-chess-pawn',
    'cloud':             'fas fa-cloud',
    'database':          'fas fa-database',
    'dollar-sign':       'fas fa-dollar-sign',
    'door-open':         'fas fa-door-open',
    'eye':               'fas fa-eye',
    'file-code':         'fas fa-file-code',
    'fire':              'fas fa-fire',
    'gavel':             'fas fa-gavel',
    'globe':             'fas fa-globe',
    'globe-europe':      'fas fa-globe-europe',
    'industry':          'fas fa-industry',
    'internet-explorer': 'fab fa-internet-explorer',
    'key':               'fas fa-key',
    'layer-group':       'fas fa-layer-group',
    'link':              'fas fa-link',
    'map':               'fas fa-map',
    'mobile':            'fas fa-mobile',
    'optin-monster':     'fab fa-optin-monster',
    'plane':             'fas fa-plane',
    'shield-alt':        'fas fa-shield-alt',
    'shield-virus':      'fas fa-shield-virus',
    'sitemap':           'fas fa-sitemap',
    'skull-crossbones':  'fas fa-skull-crossbones',
    'user-ninja':        'fas fa-user-ninja',
    'user-secret':       'fas fa-user-secret',
    'user-shield':       'fas fa-user-shield',
    'wheelchair':        'fas fa-wheelchair',
    'tag':               'fas fa-tag',
    'atom':              'fas fa-atom',
    'list':              'fas fa-list',
}
 
def _resolve_galaxy_icon(raw_icon):
    """Return the full FA class for a MISP galaxy icon name."""
    if not raw_icon:
        return 'fas fa-atom'
    key = raw_icon.strip().lower()
    return _GALAXY_ICON_MAP.get(key, f'fas fa-{key}')
