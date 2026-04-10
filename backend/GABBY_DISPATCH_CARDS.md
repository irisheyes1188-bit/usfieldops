# FieldOps Dispatch Cards
## Gabby Front-of-House Guide

This guide is for routing contact-related work to the correct backend skill.

Use these cards to decide:
- which lane the work belongs to
- which action type to use
- what inputs Chuck needs
- what kind of output to expect

---

## Card 1 - L2 Lead Investigation / Contact Mapping

### Use This When
The ask is:
- "Find out who these people are"
- "Figure out who matters here"
- "Investigate this business, property, or project"
- "See if this is a real lead worth pursuing"

### Do Not Use This When
- the contacts are already known
- the work is post-conference cleanup
- the main goal is bulk outreach prep

### Lane
- `L2`

### Action Type
- `lead_investigation`

### Best Mission Shape
```text
FIELDOPS MISSION DISPATCH
------------------------------------------------
Agent: Chuck
Mission: Investigate potential L2 lead
Mission Class: execution
Action Type: lead_investigation
Status: queued
Priority: HIGH
Lane: L2
Source Context: mirrored_from_gabby
Parent Mission ID:
------------------------------------------------

OBJECTIVE:
Investigate the target using public, legitimate sources and identify likely operational decision-makers.

INPUTS:
Target Name:
Address:
City / State:
Website:
Known Person:
Known Phone:
Known Email:
Lead Context:
Desired Contact Type:

DELIVERY:
Channel: local_file
Destination:
Send Mode: log_only
Subject:

EXPECTED OUTPUT:
Return:
- verified entity
- public source trail
- likely decision-makers
- contact ladder
- confidence notes
- recommendation on whether to pursue

ARTIFACTS:
Document Link:
Document File Name:

REPORTING:
Count As: research
Tags:
- l2
- lead-investigation
------------------------------------------------
```

### What Good Inputs Look Like
- company name
- property or business address
- why the lead matters in L2
- any known public clue
- the type of person we want to find

### What Chuck Should Return
- verified entity
- public source trail
- likely decision-makers
- contact ladder
- confidence
- pursue / not pursue recommendation

### Quick Route Rule
If the job is discovery + qualification, send it here.

---

## Card 2 - L1 Rolodex Builder / Bulk Outreach Prep

### Use This When
The ask is:
- "We already met these people"
- "Clean these contacts up"
- "Load these conference names into the Rolodex"
- "Prepare outreach from known contacts"

### Do Not Use This When
- the main problem is figuring out who matters
- the entity is still unclear
- the contact list is speculative

### Lane
- `L1`

### Action Type
- `bulk_outreach_prep`
or
- `rolodex_insert`

### Best Mission Shape
```text
FIELDOPS MISSION DISPATCH
------------------------------------------------
Agent: Chuck
Mission: Clean conference contacts into Rolodex
Mission Class: execution
Action Type: bulk_outreach_prep
Status: queued
Priority: HIGH
Lane: L1
Source Context: mirrored_from_gabby
Parent Mission ID:
------------------------------------------------

OBJECTIVE:
Standardize known contacts into clean Rolodex records for follow-up and outreach prep.

INPUTS:
Contact Set:
Conference / Event Name:
Date Met:
How We Know Them:
Source Material:

DELIVERY:
Channel: notion
Destination: Work Contacts Rolodex
Send Mode: log_only
Subject:

EXPECTED OUTPUT:
Return:
- standardized contact records
- source notes
- outreach-ready entries
- records needing review

ARTIFACTS:
Document Link:
Document File Name:

REPORTING:
Count As: outreach
Tags:
- l1
- rolodex
- bulk-outreach
------------------------------------------------
```

### What Good Inputs Look Like
- known conference contacts
- attendee lists
- business card notes
- outreach spreadsheets
- existing names with known org/context

### What Chuck Should Return
- clean contact records
- duplicates flagged
- weak records flagged
- outreach-ready subset

### Quick Route Rule
If the job is records + standardization + follow-up prep, send it here.

---

## Shared Rules

### Public / Legitimate Sources Only
No shady behavior.
No pretending certainty.
No invented data.

### Species Rule
If it should execute backend work:
- use `FIELDOPS MISSION DISPATCH`

If it is just something to track:
- use `FIELDOPS TASK`

### Lane Rule
Lane does not determine species.
Lane determines reporting and operational context.

### Handoff Rule
- `L2` may feed `L1`
- `L1` should not impersonate `L2`

Meaning:
- L2 can discover and qualify leads
- L1 can organize and prepare known contacts for outreach

---

## Fast Routing Test

Ask:

### Is the question:
"Who is this and who matters?"
Route to:
- `L2 lead_investigation`

### Is the question:
"We already know these people - clean them up and prep outreach."
Route to:
- `L1 bulk_outreach_prep`

---

## Suggested Next Artifact
After this guide, the next Phase 1 artifact should be:
- `ROLODEX_SCHEMA_V1.md`
