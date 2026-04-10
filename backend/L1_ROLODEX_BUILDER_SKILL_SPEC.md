# FieldOps Skill Spec
## L1 - Rolodex Builder / Bulk Outreach Prep

### Purpose
Take known conference contacts, outreach lists, existing records, or collected names and turn them into clean, standardized contact records for follow-up and future outreach.

This skill is for records-building and outreach preparation.

It is not:
- lead investigation
- speculative contact hunting
- decision-maker inference from weak clues
- private data gathering

### Lane
- `L1`

### Primary Action Types
- `rolodex_insert`
- `bulk_outreach_prep`

### Future Related Action Types
- `conference_contact_cleanup`
- `contact_record_standardization`

### Core Questions This Skill Answers
- How do we cleanly store these known contacts?
- How do we standardize them into durable Rolodex records?
- How do we prepare them for follow-up and future outreach?
- Which records are clean enough to hand into email draft generation?

### Typical Use Cases
- post-conference follow-up
- sponsor/contact cleanup
- known-contact import
- call-list building
- bulk outreach prep from existing names

### Required Inputs
- `Contact Set`
  One or more known people, companies, or contact rows.
- `How We Know Them`
  Example: conference contact, event attendee, partner intro, existing outreach list.

### Strongly Recommended Inputs
- `Conference / Event Name`
- `Date Met`
- `Organization`
- `Role / Title`
- `Known Email`
- `Known Phone`
- `Website`
- `Address`
- `Notes`
- `Source Material`
  Example: pasted contact sheet, notes, spreadsheet rows, conference roster

### Input Contract
The cleanest FieldOps mission shape for this skill is:

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
Standardize the known conference contacts into outreach-ready Rolodex records.

INPUTS:
Contact Set: NEEA Spring Conference contact notes
Conference / Event Name: NEEA Spring Conference
Date Met: 2026-04-08
How We Know Them: Conference follow-up
Source Material:
- Jane Smith, Example Mechanical, Program Manager, jane@example.com
- Mark Lopez, North Utility Group, Outreach Lead, mark@example.com

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
- conference-follow-up
------------------------------------------------
```

### Operational Rule
This skill works from known or approved contacts.

It may use:
- contacts you already met
- contacts already present in notes or lists
- contacts previously vetted by L2

It should not pretend to do L2 investigation.

### Backend Workflow
1. Normalize incoming contact material.
2. Group duplicates and near-duplicates.
3. Standardize fields.
4. Preserve source and context notes.
5. Flag missing or weak fields for review.
6. Prepare clean outreach-ready records.

### Rolodex Record Fields
Each record should aim to populate:
- `Full Name`
- `Organization`
- `Title / Role`
- `Email`
- `Phone`
- `Address`
- `Website`
- `Where We Met / How I Know Them`
- `Contact Source`
- `Source Date`
- `Notes`
- `Confidence`
- `Approved For Outreach`

### Field Rules
#### Full Name
Use real known names only.

#### Organization
Standardize spelling and format.

#### Title / Role
Use known title where provided.
If inferred from context, label clearly in notes.

#### Email / Phone
Use only known/publicly provided contact values from the source material.

#### Where We Met / How I Know Them
This is required whenever possible.

#### Contact Source
Examples:
- conference attendee list
- business card
- event notes
- L2 vetted lead handoff

#### Source Date
Date the contact was collected, met, or verified.

#### Confidence
Suggested scale:
- `High`
  Directly collected or clearly documented.
- `Medium`
  Mostly complete but one or more fields need confirmation.
- `Low`
  Record exists but needs human review before outreach.

#### Approved For Outreach
Boolean-style readiness flag:
- `Yes`
- `Needs Review`

### Expected Output Contract
Return a structured result with these sections:

#### 1. Clean Records
Standardized contact records ready for storage.

#### 2. Duplicates / Merges
Records that appear to be the same person or org.

#### 3. Missing Fields
Contacts that need review before outreach.

#### 4. Outreach-Ready Set
Contacts with enough information to support a draft email workflow.

### Success Criteria
This skill succeeds if it returns:
- standardized contact records
- preserved source context
- duplicates flagged
- weak records flagged
- a clearly identified outreach-ready subset

### Failure Modes
Return a clean non-mock failure if:
- the contact set is too incomplete to structure responsibly
- the source material is unreadable or too ambiguous
- there is no identifiable contact content in the input

Do not invent contact facts.

### Relation To L2 Lead Investigation
L2 may feed L1.
L1 should not impersonate L2.

Meaning:
- L2 can discover and verify likely contacts
- L1 can store, standardize, and prep outreach from known contacts

If the job is “find out who matters,” route to L2.
If the job is “clean up these known contacts and prep follow-up,” route to L1.

### Suggested Next Artifact
After this spec, the next Phase 1 artifact should be:
- `GABBY_DISPATCH_CARDS.md`
