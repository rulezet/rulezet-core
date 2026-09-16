"""
_snort_family_common.py — Shared logic for Suricata and Sagan.

Both formats descend from the same Snort-style rule grammar (action
protocol src_ip src_port -> dst_ip dst_port (options...)), parse fine with
the same `suricataparser` grammar-only parser, and share identical
`msg:`/`sid:`/`rev:` option syntax — hence this shared module instead of
duplicating that parsing in both *_format.py files.

What actually tells them apart is semantic, not structural: Sagan targets
log lines (not packets) and allows a protocol/keyword vocabulary Suricata's
real engine rejects outright. See docs/design/suricata_sagan_rework.md for
the full rationale (written for
https://github.com/rulezet/rulezet-core/issues/61).
"""
import re
from typing import Optional, Tuple

from suricataparser import parse_rule

# Canonical Suricata protocol/app-layer values (`suricata --list-rule-protos`
# on a recent Suricata 7/8 build). Keep this in sync with Suricata's own
# docs when new app-layer parsers are added — an incomplete list here false-
# rejects legitimate rules using a protocol this set just doesn't know about
# yet, which is exactly the failure mode this allowlist must avoid.
SURICATA_PROTOCOLS = {
    # Network layer
    'ip', 'ip4', 'ipv4', 'ip6', 'ipv6', 'tcp', 'tcp-pkt', 'tcp-stream',
    'udp', 'icmp', 'icmpv4', 'icmpv6', 'ether', 'arp', 'pkthdr',
    # Application layer
    'http', 'http1', 'http2', 'tls', 'ssl', 'quic', 'ftp', 'ftp-data',
    'smb', 'dns', 'doh2', 'mdns', 'dcerpc', 'ldap', 'dhcp', 'ssh', 'smtp',
    'imap', 'pop3', 'modbus', 'dnp3', 'enip', 'nfs', 'ike', 'ikev2', 'krb5',
    'bittorrent-dht', 'mqtt', 'ntp', 'rfb', 'rdp', 'snmp', 'tftp', 'sip',
    'telnet', 'websocket', 'pgsql', 'msn',
}

# Protocol tokens Sagan allows on top of Suricata's own set — Sagan matches
# arbitrary log lines, not network packets, so "any" (no protocol) and
# "syslog" (a syslog-fed log source) are valid headers there.
SAGAN_ONLY_PROTOCOLS = {'any', 'syslog'}

# Option keywords that only exist in Sagan, never in real Suricata (ref
# issue #61's failure breakdown: 'parse_src_ip'/'program' alone account for
# 412 + a chunk of the 6,686 protocol failures).
SAGAN_ONLY_KEYWORDS = {
    'program', 'meta_content', 'meta_nocase', 'parse_src_ip', 'parse_dst_ip',
    'parse_port', 'bro-intel', 'after', 'normalize', 'flexbits',
}


def get_header_protocol(content: str) -> Optional[str]:
    """First token of the rule's header (the protocol) — e.g. 'tcp', 'any',
    'syslog'. Returns None if the content doesn't parse as a single rule."""
    try:
        clean_content = content
        for line in content.splitlines():
            if line.strip() and not line.strip().startswith('#'):
                clean_content = line
                break
        rule = parse_rule(clean_content)
        if not rule or not rule.header:
            return None
        parts = rule.header.split()
        return parts[0].lower() if parts else None
    except Exception:
        return None


def get_option_names(content: str) -> set:
    """Lowercased set of every option keyword used across all rules in
    content (usually just one rule, but tolerant of a multi-rule file)."""
    from suricataparser import parse_rules
    try:
        rules = parse_rules(content)
    except Exception:
        return set()
    names = set()
    for rule in rules:
        for opt in rule.options:
            names.add(opt.name.lower())
    return names


def looks_like_sagan(content: str) -> bool:
    """True when content shows Sagan-specific evidence: a Sagan-only
    protocol token, or a Sagan-only option keyword. Used by both
    SuricataRule.detect() (returns the negation) and SaganRule.detect()."""
    protocol = get_header_protocol(content)
    if protocol in SAGAN_ONLY_PROTOCOLS:
        return True
    return bool(get_option_names(content) & SAGAN_ONLY_KEYWORDS)


def extract_msg_sid_rev(content: str) -> Tuple[str, str, str]:
    """(msg, sid, rev) — same regex-with-suricataparser-refinement approach
    both formats' parse_metadata() need. Falls back to plain regex on the
    raw content when the grammar parse itself fails, so a rule that's
    invalid enough to reject at validate() can still surface a readable
    title/identifier in the bad-rule review UI instead of "Unknown"."""
    msg_match = re.search(r'msg\s*:\s*"(.*?)"', content)
    sid_match = re.search(r'sid\s*:\s*(\d+)', content)
    rev_match = re.search(r'rev\s*:\s*(\d+)', content)

    fallback_msg = msg_match.group(1).strip() if msg_match else None
    fallback_sid = sid_match.group(1) if sid_match else None
    fallback_rev = rev_match.group(1) if rev_match else '1'

    try:
        clean_content = content
        for line in content.splitlines():
            if line.strip() and not line.strip().startswith('#'):
                clean_content = line
                break
        rule = parse_rule(clean_content)
        msg = rule.msg or fallback_msg
        sid = str(rule.sid) if rule.sid else fallback_sid
        rev = str(rule.rev) if rule.rev else fallback_rev
        return msg, sid, rev
    except Exception:
        return fallback_msg, fallback_sid, fallback_rev
