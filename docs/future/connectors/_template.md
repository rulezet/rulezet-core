# <Format> connector

> Status: idea | in design | in progress | shipped — and what exists already.

## How the format is used in real life

- Which tool(s) run these rules, where (sensor, SIEM, endpoint, scanner…).
- How rules get there today (files, update tool, API, package manager).
- How the tool tells you a rule loaded / failed / fired.

## What Rulezet already offers for it

- Export / download / feed / API endpoints that already exist.
- Validation, health checks, deep validation available for this format.

## Connector levels

Ordered from the smallest useful step to the most ambitious.

### 1. Deliver
How a curated bundle / release / workspace reaches the tool natively.

### 2. Verify
How the tool checks what was deployed, and how that comes back to Rulezet.

### 3. Learn
Which production signals (aggregate, anonymous) could flow back, and what
Rulezet does with them.

## Value added

Why a user would use this rather than copying rules by hand.

## Risks and open questions

Security (credentials, private rules), privacy (feedback), compatibility
(tool versions), identifier conflicts, load on rulezet.org.

## First step to build

The smallest piece worth shipping, with the files it touches.
