from sigma.collection import SigmaCollection
from sigma.backends.splunk import SplunkBackend
from sigma.backends.elasticsearch import EqlBackend
from sigma.backends.kusto import KustoBackend
from sigma.pipelines.sentinelasim import sentinel_asim_pipeline
from sigma.pipelines.microsoftxdr import microsoft_xdr_pipeline
from sigma.backends.sumologic import SumoLogicCSERuleBackend
from sigma.backends.secops import SecOpsBackend
from sigma.backends.loki import LogQLBackend
from sigma.exceptions import SigmaError
import re

SIGMA_CONVERT_TARGETS = {
    'splunk':    {'label': 'Splunk (SPL)',            'extension': 'spl'},
    'elastic':   {'label': 'Elastic (EQL)',            'extension': 'eql'},
    'xdr':       {'label': 'Microsoft XDR (KQL)',      'extension': 'kql'},
    'sentinel':  {'label': 'Microsoft Sentinel (KQL)', 'extension': 'kql'},
    'sumologic': {'label': 'Sumo Logic (CSE)',         'extension': 'json'},
    'secops':    {'label': 'Google SecOps (UDM)',      'extension': 'txt'},
    'loki':      {'label': 'Grafana Loki (LogQL)',     'extension': 'logql'},
}


class SigmaConversionUnavailable(ValueError):
    """The rule is valid but can't be expressed for this target (a field the
    target doesn't know, a logsource with no mapping…) — an expected outcome,
    shown to the visitor as is, not an application error."""


_FIELD_RE = re.compile(r'Invalid SigmaDetectionItem field name encountered: ([^.\s]+)')


def _unavailable_message(target: str, error: Exception) -> str:
    """Short, readable reason from a pySigma error (whose own message can be
    a multi-paragraph list of every field the pipeline knows)."""
    label = SIGMA_CONVERT_TARGETS[target]['label']
    text = str(error)
    field = _FIELD_RE.search(text)
    if field:
        return (f"This rule uses the field '{field.group(1)}', which {label} doesn't have for this "
                f"rule's log source — conversion isn't available for this rule.")
    if 'hash algo' in text.lower():
        return (f"This rule's hashes use an algorithm {label} doesn't support (MD5, SHA1, SHA256 only) — "
                f"conversion isn't available for this rule.")
    if 'Unable to determine table name' in text:
        return (f"This rule's logsource isn't mapped to a {label} table yet — "
                f"conversion isn't available for this rule.")
    first_line = text.strip().splitlines()[0] if text.strip() else type(error).__name__
    return f"{label} can't express this rule: {first_line[:200]}"


def _backend_for(target: str):
    if target == 'splunk':
        return SplunkBackend()
    if target == 'elastic':
        return EqlBackend()
    if target == 'xdr':
        return KustoBackend(processing_pipeline=microsoft_xdr_pipeline())
    if target == 'sentinel':
        return KustoBackend(processing_pipeline=sentinel_asim_pipeline())
    if target == 'sumologic':
        return SumoLogicCSERuleBackend()
    if target == 'secops':
        return SecOpsBackend()
    if target == 'loki':
        return LogQLBackend()
    raise ValueError(f"Unknown Sigma conversion target: {target}")


def convert_sigma_rule(rule, target: str) -> str:
    """Convert a Sigma rule's raw content into the given target query language via pySigma."""
    if target not in SIGMA_CONVERT_TARGETS:
        raise ValueError(f"Unknown Sigma conversion target: {target}")
    try:
        collection = SigmaCollection.from_yaml(rule.to_string)
        queries = _backend_for(target).convert(collection)
    except Exception as e:
        # Errors of pySigma and of its backends / pipelines (some don't derive from SigmaError, e.g.
        # the Kusto pipelines' InvalidHashAlgorithmError) mean "this rule can't be converted for this
        # target" — shown to the visitor, never logged as an application error. Anything else is a bug.
        if not (isinstance(e, SigmaError) or type(e).__module__.split('.')[0] == 'sigma'):
            raise
        # pySigma refusing a rule for a target is expected — e.g. the Sentinel
        # ASIM pipeline only knows the fields of its tables and only maps some
        # logsources to a table; it raises rather than guessing, and so do we:
        # a guessed query would look valid while matching nothing.
        raise SigmaConversionUnavailable(_unavailable_message(target, e)) from e
    return '\n\n'.join(queries)
