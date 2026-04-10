# FieldOps Schema
## Rolodex Schema V1

This schema defines the durable contact record model for the Work Contacts Rolodex.

It is intended to serve three aligned purposes:
- backend storage target
- Notion record structure
- outreach-ready source record

This schema is for known or approved contacts.

It is not a speculative lead scratchpad.

---

## Record Identity

### 1. Full Name
- Type: text
- Required: yes if known
- Purpose: primary human-readable identity field

### 2. Organization
- Type: text
- Required: yes if known
- Purpose: company, agency, nonprofit, or institution name

### 3. Title / Role
- Type: text
- Required: recommended
- Purpose: describe what the person does

### 4. Record Type
- Type: select
- Allowed values:
  - `conference_contact`
  - `partner`
  - `lead_contact`
  - `sponsor`
  - `vendor`
  - `general_contact`
- Purpose: top-level categorization for filtering and reporting

---

## Contact Methods

### 5. Email
- Type: text
- Required: no

### 6. Phone
- Type: text
- Required: no

### 7. Address
- Type: text
- Required: no

### 8. Website
- Type: text
- Required: no

### 9. Office / Location Notes
- Type: text
- Required: no
- Purpose: extra office detail, branch, city, or meeting location context

---

## Relationship / Context

### 10. Where We Met / How I Know Them
- Type: text
- Required: strongly recommended
- Purpose: preserve relational context and future recall

### 11. Conference / Event Name
- Type: text
- Required: optional
- Purpose: tie conference contacts to the relevant event

### 12. Source Context
- Type: select
- Allowed values:
  - `conference`
  - `event`
  - `public_record`
  - `partner_intro`
  - `website`
  - `existing_contact_list`
  - `l2_handoff`
  - `manual_entry`
- Purpose: high-level origin of the record

### 13. Source Detail
- Type: text
- Required: recommended
- Purpose: freeform explanation of the specific source material

### 14. Source Date
- Type: date or text date
- Required: recommended
- Purpose: when the contact was met, collected, or verified

---

## Qualification / Readiness

### 15. Confidence
- Type: select
- Allowed values:
  - `High`
  - `Medium`
  - `Low`
- Purpose: record quality/confidence

### 16. Confidence Notes
- Type: text
- Required: recommended
- Purpose: why the confidence level was assigned

### 17. Approved For Outreach
- Type: select
- Allowed values:
  - `Yes`
  - `Needs Review`
  - `No`
- Purpose: whether this record is safe to hand into outreach prep

### 18. Decision-Maker Relevance
- Type: text
- Required: optional
- Purpose: explain why this person matters or what role they likely play

---

## Notes / Ops Use

### 19. Notes
- Type: long text
- Required: no
- Purpose: freeform notes worth preserving

### 20. Follow-Up Notes
- Type: long text
- Required: no
- Purpose: future action context or reminders

### 21. Lane
- Type: select
- Allowed values:
  - `L1`
  - `L2`
  - `L3`
  - `L4`
  - `General Ops`
- Purpose: reporting and organizational context

### 22. Last Updated
- Type: date/time
- Required: recommended

### 23. Record Status
- Type: select
- Allowed values:
  - `active`
  - `review`
  - `duplicate`
  - `archived`
- Purpose: keep the Rolodex clean over time

---

## Minimal Required Record

The smallest acceptable Rolodex record should have:
- `Full Name` or a usable role/name placeholder
- `Organization`
- `Where We Met / How I Know Them`
- `Source Context`
- `Source Date` if known
- `Confidence`
- `Approved For Outreach`

If that minimum cannot be met, the record should be flagged for review instead of treated as outreach-ready.

---

## L1 vs L2 Interaction

### L1 Rolodex Builder
May create or standardize records in this schema when the contact is already known.

### L2 Lead Investigation
May produce candidate records that map into this schema, but should not automatically mark them as outreach-ready unless the evidence supports it.

Recommended handoff rule:
- L2 candidate -> `Approved For Outreach = Needs Review`
- L1 cleanup/review -> can move to `Yes`

---

## Notion Mapping Recommendation

Suggested Notion property mapping:
- `Name` -> Full Name
- `Organization` -> text
- `Title / Role` -> text
- `Record Type` -> select
- `Email` -> email or text
- `Phone` -> phone/text
- `Address` -> text
- `Website` -> URL
- `Where We Met / How I Know Them` -> text
- `Conference / Event Name` -> text
- `Source Context` -> select
- `Source Detail` -> text
- `Source Date` -> date
- `Confidence` -> select
- `Confidence Notes` -> text
- `Approved For Outreach` -> select
- `Decision-Maker Relevance` -> text
- `Notes` -> text
- `Follow-Up Notes` -> text
- `Lane` -> select
- `Last Updated` -> date
- `Record Status` -> select

---

## Success Rule

This schema is working if:
- contacts are easy to search later
- the source trail is preserved
- outreach-ready contacts can be filtered fast
- weak records are visible instead of hidden
- L1 and L2 can both use the same durable model without confusing their jobs

---

## Suggested Next Artifact
After this schema, the next Phase 1 move should be:
- a short `Phase 1 summary` tying all four artifacts together
