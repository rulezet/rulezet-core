"""Static descriptions of the rule formats Rulezet knows, shown on the public
"Rule formats" page (/rule/formats) and linked from every format chip.

`logo` is a file in static/images/formats/ (the project's own logo, taken
from its official site or GitHub organisation); `icon` is the Font Awesome
fallback when there is none.

Keyed by the lowercase format name stored in Rule.format / FormatRule.name.
A format an admin creates that isn't listed here still appears on the page,
just with a generic description and no official link — add an entry here to
document it.
"""

FORMAT_CATALOG = {
    "yara": {
        "title": "YARA",
        "maintainer": "VirusTotal",
        "category": "Files & memory",
        "icon": "fa-file-shield",
        "logo": "yara.png",
        "description": (
            "Pattern-matching language for identifying and classifying malware. A rule combines "
            "text, hex and regex strings with a boolean condition, and is run against files, "
            "processes or memory dumps."
        ),
        "extensions": [".yar", ".yara"],
        "official_url": "https://virustotal.github.io/yara/",
        "docs_url": "https://yara.readthedocs.io/",
    },
    "sigma": {
        "title": "Sigma",
        "maintainer": "SigmaHQ",
        "category": "Logs & SIEM",
        "icon": "fa-wave-square",
        "logo": "sigma.svg",
        "description": (
            "Generic, vendor-neutral signature format for log events, written in YAML. A Sigma rule "
            "describes suspicious log entries once and is converted into the query language of "
            "any SIEM (Splunk, Elastic, Microsoft Sentinel, …)."
        ),
        "extensions": [".yml", ".yaml"],
        "official_url": "https://sigmahq.io/",
        "docs_url": "https://sigmahq.io/docs/basics/rules.html",
    },
    "suricata": {
        "title": "Suricata",
        "maintainer": "OISF",
        "category": "Network",
        "icon": "fa-network-wired",
        "logo": "suricata.png",
        "description": (
            "Signatures for the Suricata network IDS/IPS engine. Each rule has an action, a header "
            "(protocol, addresses, ports, direction) and options that inspect packets, flows and "
            "application-layer protocols."
        ),
        "extensions": [".rules"],
        "official_url": "https://suricata.io/",
        "docs_url": "https://docs.suricata.io/en/latest/rules/index.html",
    },
    "zeek": {
        "title": "Zeek",
        "maintainer": "Zeek Project",
        "category": "Network",
        "icon": "fa-tower-broadcast",
        "logo": "zeek.png",
        "description": (
            "Scripts and signatures for the Zeek network security monitor, which turns traffic into "
            "rich, structured logs and lets detections react to network events."
        ),
        "extensions": [".zeek", ".sig"],
        "official_url": "https://zeek.org/",
        "docs_url": "https://docs.zeek.org/",
    },
    "sagan": {
        "title": "Sagan",
        "maintainer": "Quadrant Information Security",
        "category": "Logs & SIEM",
        "icon": "fa-scroll",
        "logo": "sagan.png",
        "description": (
            "Rules for the Sagan real-time log analysis engine. The grammar is close to Suricata's, "
            "but rules match log lines (syslog, …) instead of network packets."
        ),
        "extensions": [".rules"],
        "official_url": "https://github.com/quadrantsec/sagan",
        "docs_url": "https://sagan.readthedocs.io/",
    },
    "crs": {
        "title": "OWASP CRS",
        "maintainer": "OWASP",
        "category": "Web application",
        "icon": "fa-globe",
        "logo": "crs.png",
        "description": (
            "OWASP Core Rule Set: generic attack-detection rules for web application firewalls "
            "compatible with ModSecurity (ModSecurity, Coraza, …), covering SQL injection, XSS, "
            "remote code execution and more."
        ),
        "extensions": [".conf"],
        "official_url": "https://coreruleset.org/",
        "docs_url": "https://coreruleset.org/docs/",
    },
    "nse": {
        "title": "Nmap NSE",
        "maintainer": "Nmap Project",
        "category": "Scanning",
        "icon": "fa-satellite-dish",
        "logo": "nse.png",
        "description": (
            "Lua scripts for the Nmap Scripting Engine, used to detect services, vulnerabilities "
            "and misconfigurations while scanning hosts."
        ),
        "extensions": [".nse"],
        "official_url": "https://nmap.org/book/nse.html",
        "docs_url": "https://nmap.org/nsedoc/",
    },
    "nova": {
        "title": "NOVA",
        "maintainer": "NOVA Framework",
        "category": "AI / LLM prompts",
        "icon": "fa-robot",
        "logo": "nova.png",
        "description": (
            "Prompt pattern-matching rules for hunting malicious or abusive prompts sent to LLMs, "
            "combining keyword, semantic and LLM-based matching in a YARA-like syntax."
        ),
        "extensions": [".nov"],
        "official_url": "https://novahunting.ai/",
        "docs_url": "https://github.com/fr0gger/nova-framework",
    },
    "atr": {
        "title": "ATR",
        "maintainer": "Agent Threat Rules project",
        "category": "AI agents",
        "icon": "fa-robot",
        "logo": "atr.svg",
        "description": (
            "Agent Threat Rules: an open YAML detection format for threats against AI agents — "
            "prompt injection, tool poisoning, skill compromise, context exfiltration and more, "
            "each rule identified as ATR-YYYY-NNNNN."
        ),
        "extensions": [".yaml", ".yml"],
        "official_url": "https://agentthreatrule.org/",
        "docs_url": "https://github.com/Agent-Threat-Rule/agent-threat-rules",
    },
    "wazuh": {
        "title": "Wazuh",
        "maintainer": "Wazuh",
        "category": "Logs & SIEM",
        "icon": "fa-shield-halved",
        "logo": "wazuh.png",
        "description": (
            "XML rules for the Wazuh XDR/SIEM platform. Rules match decoded log events and raise "
            "alerts with a level, groups and compliance mappings."
        ),
        "extensions": [".xml"],
        "official_url": "https://wazuh.com/",
        "docs_url": "https://documentation.wazuh.com/current/user-manual/ruleset/index.html",
    },
    "kql": {
        "title": "KQL",
        "maintainer": "Microsoft",
        "category": "Logs & SIEM",
        "icon": "fa-magnifying-glass-chart",
        "logo": "kql.png",
        "description": (
            "Kusto Query Language queries, used as hunting and analytics rules in Microsoft "
            "Sentinel, Microsoft Defender XDR and Azure Data Explorer."
        ),
        "extensions": [".kql"],
        "official_url": "https://learn.microsoft.com/en-us/kusto/query/",
        "docs_url": None,
    },
    "splunk": {
        "title": "Splunk SPL",
        "maintainer": "Splunk",
        "category": "Logs & SIEM",
        "icon": "fa-chart-line",
        "logo": "splunk.png",
        "description": (
            "Searches written in Splunk's Search Processing Language, used as correlation searches "
            "and detections in Splunk Enterprise Security."
        ),
        "extensions": [".spl"],
        "official_url": "https://research.splunk.com/",
        "docs_url": "https://docs.splunk.com/Documentation/Splunk/latest/SearchReference",
    },
    "elastic": {
        "title": "Elastic",
        "maintainer": "Elastic",
        "category": "Logs & SIEM",
        "icon": "fa-magnifying-glass",
        "logo": "elastic.png",
        "description": (
            "Detection rules for Elastic Security, stored as TOML with an EQL, KQL, Lucene or ES|QL "
            "query that runs against an Elasticsearch cluster."
        ),
        "extensions": [".toml"],
        "official_url": "https://github.com/elastic/detection-rules",
        "docs_url": "https://www.elastic.co/guide/en/security/current/detection-engine-overview.html",
    },
    "kunai": {
        "title": "Kunai",
        "maintainer": "Kunai Project",
        "category": "Endpoint (Linux)",
        "icon": "fa-linux",
        "logo": "kunai.svg",
        "icon_style": "fa-brands",
        "description": (
            "YAML detection and filtering rules for Kunai, an eBPF-based Linux threat-hunting agent "
            "that records process, file and network events."
        ),
        "extensions": [".yml", ".yaml"],
        "official_url": "https://why.kunai.rocks/",
        "docs_url": "https://github.com/kunai-project/kunai",
    },
    "plum": {
        "title": "Plum Island",
        "maintainer": "D4 Project (CIRCL)",
        "category": "Internet scanning",
        "icon": "fa-binoculars",
        "logo": "plum.png",
        "description": (
            "Queries (\"antibodies\") matched against Plum Island's own Internet-scan index to "
            "spot exposed or compromised services."
        ),
        "extensions": [],
        "official_url": "https://github.com/D4-project/Plum-Antibodies",
        "docs_url": "https://github.com/D4-project/Plum-Island",
    },
    "no format": {
        "title": "No format",
        "maintainer": None,
        "category": "Other",
        "icon": "fa-question",
        "description": (
            "Rules whose format isn't one of the above — kept on Rulezet as plain text, "
            "without format-specific validation."
        ),
        "extensions": [],
        "official_url": None,
        "docs_url": None,
    },
}


def get_format_info(name: str) -> dict:
    """Catalog entry for a format name, or a generic one for an unknown format."""
    key = (name or "").strip().lower()
    info = FORMAT_CATALOG.get(key)
    if info:
        return dict(info, key=key)
    return {
        "key": key,
        "title": (name or "?").upper(),
        "maintainer": None,
        "category": "Other",
        "icon": "fa-file-code",
        "logo": None,
        "description": "No description for this format yet.",
        "extensions": [],
        "official_url": None,
        "docs_url": None,
    }
