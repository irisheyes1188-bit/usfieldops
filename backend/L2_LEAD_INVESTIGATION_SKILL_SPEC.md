# FieldOps Skill Spec
## L2 - Lead Investigation / Contact Mapping

### Purpose
Investigate a company, property, organization, or potential project lead using public, legitimate sources and return a source-backed contact map that helps decide whether the lead is worth pursuing.

This skill is for discovery and qualification.

It is not:
- bulk outreach prep
- conference contact cleanup
- speculative scraping
- private or shady data gathering

### Lane
- `L2`

### Primary Action Type
- `lead_investigation`

### Future Related Action Types
- `entity_verification`
- `decision_maker_mapping`

### Core Questions This Skill Answers
- Who is this company, property owner, or organization really?
- Is this lead real and relevant?
- Who likely matters operationally?
- What is the cleanest public contact ladder?
- Is this lead worth follow-up?

### Typical Use Cases
- rebate leads
- project identification
- commercial customer qualification
- facilities / operations decision-maker mapping
- lead qualification before outreach

### Required Inputs
- `Target Name`
  Company, property, organization, person, or project name.
- `Reason For Investigation`
  Why this lead matters in the L2 lane.

### Strongly Recommended Inputs
- `Address`
- `City / State`
- `Website`
- `Known Person`
- `Known Phone`
- `Known Email`
- `Lead Context`
  Example: "possible NWE rebate customer from event conversation"
- `Desired Contact Type`
  Example: owner, facilities lead, operations lead, office manager, rebate/compliance contact

### Input Contract
The cleanest FieldOps mission shape for this skill is:

```text
FIELDOPS MISSION DISPATCH
------------------------------------------------
Agent: Chuck
Mission: Investigate possible L2 rebate lead
Mission Class: execution
Action Type: lead_investigation
Status: queued
Priority: HIGH
Lane: L2
Source Context: direct_request
Parent Mission ID:
------------------------------------------------

OBJECTIVE:
Investigate the target and map likely operational decision-makers using public, legitimate sources.

INPUTS:
Target Name: Example Mechanical
Address: 123 Main St, Butte, MT
City / State: Butte, MT
Website:
Known Person:
Lead Context: Possible NWE rebate opportunity from onsite conversation
Desired Contact Type: operations lead

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

### Public Source Rule
Use public, legitimate, above-board sources only.

Allowed examples:
- official business registries
- secretary of state filings
- property and GIS records
- SAM
- SEC
- company websites
- public staff directories
- professional bios
- conference websites if public
- public contact pages

Not allowed:
- paywalled data the user has not provided access to
- private login-only content
- personal data harvesting
- shady scraping behavior
- pretending certainty where the source does not support it

### Backend Workflow
1. Verify the entity if possible.
2. Gather a source trail.
3. Identify likely decision-makers by role.
4. Build a contact ladder from strongest to weakest path.
5. Score confidence and note why.
6. Recommend whether the lead is worth pursuing.

### Expected Output Contract
Return a structured result with these sections:

#### 1. Verified Entity
- legal or public-facing entity name
- address or location if confirmed
- website if confirmed
- entity type if useful

#### 2. Lead Relevance
- why this target may matter in L2
- whether the lead appears viable

#### 3. Decision-Maker Map
Each candidate should include:
- `Full Name`
- `Role / Title`
- `Why Relevant`
- `Confidence`

#### 4. Contact Ladder
Return multiple paths where possible:
- main office
- local office
- department path
- public email if verified
- public phone if verified
- website contact path
- backup names

#### 5. Source Trail
For each major fact:
- `Source`
- `Source Type`
- `Source Date`
- `What It Supports`

#### 6. Recommendation
One of:
- `Pursue`
- `Pursue with caution`
- `Insufficient evidence`
- `Not worth pursuing`

### Confidence Rules
Confidence should be explicit and modest.

Suggested scale:
- `High`
  Supported directly by official or clearly attributable public source.
- `Medium`
  Supported by strong public clues, but not direct confirmation.
- `Low`
  Plausible inference only.

Every candidate should have a short "why" note.

### Success Criteria
The skill succeeds if it returns:
- a clearly identified target or best-effort clarification
- at least one usable public source trail
- at least one likely decision-maker or contact path
- a confidence-based recommendation

### Failure Modes
Return a clean non-mock failure if:
- target cannot be identified from public inputs
- sources are too weak to make a responsible contact recommendation
- source access is unavailable

Do not fake certainty.

### Relation To L1 Rolodex Builder
L2 may feed L1.

Meaning:
- this skill can produce vetted contact candidates
- approved contacts can later be handed to L1 Rolodex Builder

L2 should not directly behave like bulk outreach prep by default.

### Suggested Next Artifact
After this spec, the next Phase 1 artifact should be:
- `L1_ROLODEX_BUILDER_SKILL_SPEC.md`
