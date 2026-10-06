"""
Unit tests for the Sagan format (app/features/rule/rule_format/available_format/sagan_format.py).

See docs/design/suricata_sagan_rework.md — written for
https://github.com/rulezet/rulezet-core/issues/61. Sagan and Suricata share
the same header/option grammar (both parse fine with suricataparser), so
SaganRule.detect() must positively identify Sagan-specific evidence rather
than accept anything Suricata-shaped.
"""
from __future__ import annotations

from app.features.rule.rule_format.available_format.sagan_format import SaganRule

SAGAN_SYSLOG_RULE = (
    'alert syslog $EXTERNAL_NET any -> $HOME_NET any '
    '(msg:"[OSSEC] Ossec started"; content:"Ossec started"; '
    'classtype:system-event; program:ossec; sid:5000287; rev:1;)'
)

SAGAN_ANY_RULE = (
    'alert any $EXTERNAL_NET any -> $HOME_NET any '
    '(msg:"[CISCO-SDEE] Data Base TNS Connection"; content:"SID: 7000 ,"; '
    'parse_src_ip:1; parse_dst_ip:2; parse_port; program:qdee; sid:6107000; rev:4;)'
)


def test_sagan_validates_syslog_protocol_rule():
    result = SaganRule().validate(SAGAN_SYSLOG_RULE)
    assert result.ok is True
    assert result.errors == []


def test_sagan_validates_any_protocol_rule():
    result = SaganRule().validate(SAGAN_ANY_RULE)
    assert result.ok is True
    assert result.errors == []


def test_sagan_detect_accepts_both_examples():
    s = SaganRule()
    assert s.detect(SAGAN_SYSLOG_RULE) is True
    assert s.detect(SAGAN_ANY_RULE) is True


def test_sagan_detect_rejects_a_real_suricata_rule():
    """A plain Suricata rule (no Sagan-only protocol/keyword) is not Sagan."""
    s = SaganRule()
    rule = 'alert tcp $HOME_NET any -> $EXTERNAL_NET 22 (msg:"SSH test"; sid:1000099; rev:1;)'
    assert s.detect(rule) is False


def test_sagan_parse_metadata_extracts_msg_sid_rev():
    result = SaganRule().validate(SAGAN_ANY_RULE)
    metadata = SaganRule().parse_metadata(SAGAN_ANY_RULE, {"license": "MIT"}, result)
    assert metadata['format'] == 'sagan'
    assert metadata['title'] == '[CISCO-SDEE] Data Base TNS Connection'
    assert metadata['original_uuid'] == '6107000'
    assert metadata['version'] == '4'


def test_sagan_rejects_a_genuinely_invalid_protocol():
    """Sagan's protocol set is Suricata's real set plus any/syslog — not
    an unlimited free-for-all."""
    rule = 'alert altemplate any any -> any any (msg:"t"; sid:1; rev:1;)'
    result = SaganRule().validate(rule)
    assert result.ok is False
