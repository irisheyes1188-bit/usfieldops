from __future__ import annotations

from datetime import datetime
import re
from calendar_oauth import (
    CalendarAuthRequiredError,
    CalendarDependencyError,
    create_calendar_event,
)
from gmail_oauth import (
    GmailAuthRequiredError,
    GmailDependencyError,
    create_gmail_draft,
)
from lead_investigation import LeadInvestigationError, investigate_public_lead
from models import Mission


def classify_mission(mission: Mission) -> dict:
    if mission.actionType:
        supported_actions = {
            "gmail_create_draft",
            "calendar_create_event",
            "lead_investigation",
            "generate_word_report",
            "email_deliverable",
            "log_deliverable",
            "document_completed_work",
            "fallback_handoff_email",
        }
        if mission.actionType in supported_actions:
            return {"execution_type": "action", "action_type": mission.actionType}
    parts = [
        mission.title or "",
        mission.objective or "",
        mission.inputs or "",
        mission.expectedOutput or "",
        mission.prompt or "",
    ]
    text = " ".join(parts).lower()
    raw_text = "\n".join(parts)
    calendar_field_hits = sum(
        1
        for pattern in [
            r"(?im)^date:\s*",
            r"(?im)^start time:\s*",
            r"(?im)^end time:\s*",
            r"(?im)^time zone:\s*",
            r"(?im)^calendar:\s*",
        ]
        if re.search(pattern, raw_text)
    )
    calendar_like = any(word in text for word in ("calendar", "calander"))
    email_like = "email" in text or re.search(r"(?im)^to:\s*\S*", raw_text)
    if (
        (
            ("gmail" in text and "draft" in text)
            or (
                email_like
                and re.search(r"\b(draft|email)\b", text)
                and re.search(r"\b(create|save|draft|write|send)\b", text)
            )
        )
    ):
        return {"execution_type": "action", "action_type": "gmail_create_draft"}
    if (
        calendar_like
        and "event" in text
        and re.search(r"\b(create|schedule|add)\b", text)
        and calendar_field_hits >= 2
    ):
        return {"execution_type": "action", "action_type": "calendar_create_event"}
    if (
        any(
            phrase in text
            for phrase in (
                "lead investigation",
                "decision-maker mapping",
                "decision maker mapping",
                "investigate the target",
                "investigate this business",
                "investigate this company",
            )
        )
        or (
            "investigate" in text
            and "lead" in text
            and (mission.lane or "").strip().upper() == "L2"
        )
        or (
            (mission.missionClass or "").strip().lower() == "investigation"
            and (mission.lane or "").strip().upper() == "L2"
            and "investigate" in text
        )
    ):
        return {"execution_type": "action", "action_type": "lead_investigation"}
    if (
        ("comparison table" in text or "comparison report" in text or "word-format comparison report" in text)
        and re.search(r"\b(create|generate|build|compare)\b", text)
    ):
        return {"execution_type": "action", "action_type": "fallback_handoff_email"}
    if (
        ("structured summary" in text or "grouped by follow-up priority" in text or "grouped by priority" in text)
        and re.search(r"\b(generate|organize|build|create)\b", text)
    ):
        return {"execution_type": "action", "action_type": "fallback_handoff_email"}
    if (
        ("action list" in text or "task list" in text or "work plan" in text)
        and re.search(r"\b(build|generate|organize|create)\b", text)
    ):
        return {"execution_type": "action", "action_type": "fallback_handoff_email"}
    if (
        ("word report" in text or "comparison report" in text or "action list" in text)
        and re.search(r"\b(create|generate|build|organize|compare)\b", text)
    ):
        return {"execution_type": "action", "action_type": "fallback_handoff_email"}
    if (
        any(
            phrase in text
            for phrase in (
                "word-format work memo",
                "work memo",
                "memo",
                "word document",
                "word-format",
                "deliverable type: word_report",
                "document type: work_memo",
                "output format: word document",
            )
        )
        and re.search(r"\b(create|generate|build|draft|write|prepare)\b", text)
    ):
        return {"execution_type": "action", "action_type": "fallback_handoff_email"}
    return {"execution_type": "result", "action_type": ""}


def _extract_gmail_draft_fields(mission: Mission) -> dict:
    text = "\n".join(
        [
            mission.title or "",
            mission.objective or "",
            mission.inputs or "",
            mission.expectedOutput or "",
            mission.prompt or "",
        ]
    )
    inputs_text = mission.inputs or text
    subject = _extract_line_field(inputs_text, "Subject").strip()
    to_addr = _extract_line_field(inputs_text, "To").strip()
    cc_addr = _extract_line_field(inputs_text, "Cc").strip()
    bcc_addr = _extract_line_field(inputs_text, "Bcc").strip()
    body = _extract_multiline_field(
        inputs_text,
        "Body",
        following_labels=("Expected Output", "Delivery", "Artifacts", "Reporting"),
    ).strip()

    if not subject:
        subject = mission.title or "FieldOps Draft"
    if not body:
        objective = mission.objective or mission.inputs or mission.prompt or ""
        body = objective.strip() or "Draft generated by FieldOps."

    return {
        "to": to_addr,
        "cc": cc_addr,
        "bcc": bcc_addr,
        "subject": subject,
        "body": body,
    }


def _build_gmail_action_details(fields: dict, draft: dict | None = None) -> dict:
    details = {
        "provider": "gmail",
        "operation": "create_draft",
        "result_label": "Live Gmail draft",
        "subject": fields.get("subject", ""),
        "to": fields.get("to", ""),
        "cc": fields.get("cc", ""),
        "bcc": fields.get("bcc", ""),
        "body_preview": (fields.get("body", "") or "").strip()[:280],
    }
    if draft:
        details["draft_id"] = draft.get("draft_id", "")
        details["message_id"] = draft.get("message_id", "")
    return details


def _build_fallback_handoff_fields(mission: Mission) -> dict:
    requested_action = mission.actionType or "unsupported_deliverable"
    subject = f"Fallback Handoff — {mission.title or 'FieldOps Request'}"
    body = (
        "Hello,\n\n"
        "FieldOps received a request that the backend could not execute directly.\n\n"
        "Please use the request details below to complete the work manually.\n\n"
        f"Mission: {mission.title or 'Untitled Mission'}\n"
        f"Requested Action Type: {requested_action}\n"
        f"Mission Class: {mission.missionClass or 'execution'}\n"
        f"Priority: {(mission.priority or 'normal').upper()}\n"
        f"Lane: {(mission.lane or 'General Ops')}\n"
        f"Source Context: {mission.sourceContext or 'fieldops_native'}\n\n"
        "Objective:\n"
        f"{(mission.objective or '[none]').strip()}\n\n"
        "Inputs:\n"
        f"{(mission.inputs or '[none]').strip()}\n\n"
        "Expected Output:\n"
        f"{(mission.expectedOutput or '[none]').strip()}\n\n"
        "Reason for Handoff:\n"
        "Backend executor unavailable or unsupported for direct completion.\n\n"
        "Partial Notes:\n"
        f"{(mission.resultSummary or '[none]').strip()}\n\n"
        "Best,\n"
        "Chuck / FieldOps"
    )
    return {
        "to": "guyl@ncat.org",
        "subject": subject,
        "body": body,
    }


def _extract_field(text: str, label: str) -> str:
    label_pattern = re.escape(label)
    next_label = r"(?:[A-Z][A-Za-z /]+:|[\u2022\?\u2013-]\s*[A-Z][A-Za-z /]+:)"
    patterns = [
        rf"(?is){label_pattern}\s*:\s*[\u2022\?\u2013-]?\s*(.+?)(?=\n|$|\s+{next_label})",
        rf"(?im)^{label_pattern}\s*:\s*[\u2013-]?\s*(.+)$",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            value = match.group(1).strip()
            value = re.sub(r"^[\u2013\-]\s*", "", value).strip()
            return value
    return ""


def _extract_line_field(text: str, label: str) -> str:
    match = re.search(rf"(?im)^{re.escape(label)}:[ \t]*(.*)$", text)
    return (match.group(1).strip() if match else "").strip()


def _extract_multiline_field(text: str, label: str, following_labels: tuple[str, ...] = ()) -> str:
    if not text.strip():
        return ""
    lines = text.splitlines()
    label_prefix = f"{label.lower()}:"
    following_prefixes = tuple(f"{item.lower()}:" for item in following_labels)
    for index, raw_line in enumerate(lines):
        line = raw_line.strip()
        if not line.lower().startswith(label_prefix):
            continue
        first_value = line[len(label_prefix):].strip()
        collected: list[str] = []
        if first_value:
            collected.append(first_value)
        for next_line in lines[index + 1 :]:
            stripped = next_line.strip()
            if following_prefixes and stripped.lower().startswith(following_prefixes):
                break
            if stripped:
                collected.append(stripped)
            elif collected:
                collected.append("")
        return "\n".join(collected).strip()
    return ""


def _extract_calendar_fields(mission: Mission) -> dict:
    text = "\n".join(
        [
            mission.title or "",
            mission.objective or "",
            mission.inputs or "",
            mission.expectedOutput or "",
            mission.prompt or "",
        ]
    )
    inputs_text = mission.inputs or text
    title = (
        _extract_field(inputs_text, "Event Title")
        or _extract_field(inputs_text, "Title")
        or mission.title
        or "FieldOps Event"
    )
    date_str = _extract_field(inputs_text, "Date")
    start_time = _extract_field(inputs_text, "Start Time")
    end_time = _extract_field(inputs_text, "End Time")
    duration = _extract_field(inputs_text, "Duration")
    purpose = _extract_field(inputs_text, "Purpose") or mission.objective or ""
    timezone_str = _extract_field(inputs_text, "Time Zone") or _extract_field(inputs_text, "Timezone") or "America/Denver"
    calendar_id = _extract_field(inputs_text, "Calendar").lower()
    if not calendar_id or "default" in calendar_id or "primary" in calendar_id:
        calendar_id = "primary"

    def parse_local_datetime(date_value: str, time_value: str):
        candidate = f"{date_value} {time_value}".strip()
        for fmt in (
            "%A, %B %d, %Y %I:%M %p",
            "%Y-%m-%d %I:%M %p",
            "%m/%d/%Y %I:%M %p",
            "%m-%d-%Y %I:%M %p",
        ):
            try:
                return datetime.strptime(candidate, fmt)
            except ValueError:
                continue
        raise ValueError(f"time data '{candidate}' does not match supported date formats")

    start_local = None
    end_local = None
    if date_str and start_time:
        start_local = parse_local_datetime(date_str, start_time)
    if date_str and end_time:
        end_local = parse_local_datetime(date_str, end_time)
    elif start_local and duration:
        hours_match = re.search(r"(\d+)\s*hour", duration.lower())
        minutes_match = re.search(r"(\d+)\s*minute", duration.lower())
        delta_minutes = 0
        if hours_match:
            delta_minutes += int(hours_match.group(1)) * 60
        if minutes_match:
            delta_minutes += int(minutes_match.group(1))
        if delta_minutes:
            from datetime import timedelta
            end_local = start_local + timedelta(minutes=delta_minutes)

    if not start_local or not end_local:
        raise ValueError(
            "Calendar mission is missing parsable Date/Start Time/End Time fields."
        )

    return {
        "title": title,
        "start_local": start_local,
        "end_local": end_local,
        "description": purpose,
        "calendar_id": calendar_id,
        "timezone_str": timezone_str,
    }


def _extract_lead_investigation_fields(mission: Mission) -> dict:
    text = "\n".join(
        [
            mission.title or "",
            mission.objective or "",
            mission.inputs or "",
            mission.expectedOutput or "",
            mission.prompt or "",
        ]
    )
    inputs_text = mission.inputs or text
    target_name = _extract_field(inputs_text, "Target Name") or mission.title or ""
    address = _extract_field(inputs_text, "Address")
    city_state = _extract_field(inputs_text, "City / State")
    website = _extract_field(inputs_text, "Website")
    known_person = _extract_field(inputs_text, "Known Person")
    known_phone = _extract_field(inputs_text, "Known Phone")
    known_email = _extract_field(inputs_text, "Known Email")
    lead_context = _extract_field(inputs_text, "Lead Context")
    desired_contact_type = _extract_field(inputs_text, "Desired Contact Type")
    reason = lead_context or mission.objective or ""

    return {
        "target_name": target_name.strip(),
        "address": address.strip(),
        "city_state": city_state.strip(),
        "website": website.strip(),
        "known_person": known_person.strip(),
        "known_phone": known_phone.strip(),
        "known_email": known_email.strip(),
        "lead_context": lead_context.strip(),
        "desired_contact_type": desired_contact_type.strip(),
        "reason": reason.strip(),
    }


def _build_lead_investigation_result(mission: Mission) -> dict:
    fields = _extract_lead_investigation_fields(mission)
    if not fields["target_name"]:
        return {
            "status": "failed",
            "timestamp": datetime.now().isoformat(),
            "summary": "Lead investigation missing target name",
            "full_output": (
                "Action Type: lead_investigation\n\n"
                "FieldOps could not start L2 lead investigation because no Target Name "
                "was provided in the mission inputs."
            ),
            "follow_up_needed": True,
            "carry_forward": bool(mission.carry),
            "action_required": True,
            "action_type": "lead_investigation",
            "action_status": "missing_target_name",
            "action_completed": False,
        }

    contact_focus = fields["desired_contact_type"] or "operations lead or facilities decision-maker"
    try:
        investigation = investigate_public_lead(
            target_name=fields["target_name"],
            website=fields["website"],
            address=fields["address"],
            city_state=fields["city_state"],
            known_person=fields["known_person"],
            known_phone=fields["known_phone"],
            known_email=fields["known_email"],
            desired_contact_type=contact_focus,
            lead_context=fields["lead_context"],
        )
        verified_entity = investigation["verified_entity"]
        lead_relevance = investigation["lead_relevance"]
        investigation_profile = investigation.get("investigation_profile", {})
        best_contact = investigation.get("best_contact")
        decision_makers = investigation["decision_maker_map"]
        department_routes = investigation.get("department_routes", [])
        contact_ladder = investigation["contact_ladder"]
        source_trail = investigation["source_trail"]

        best_contact_lines = (
            "\n".join(
                [
                    f"- Name: {best_contact['full_name']}",
                    f"- Role: {best_contact['role']}",
                    f"- Confidence: {best_contact['confidence']}",
                    f"- Source: {best_contact.get('source_url', '[not recorded]')}",
                ]
            )
            if best_contact
            else "- No single best named contact could be confirmed from the public sources reviewed."
        )
        decision_lines = (
            "\n".join(
                f"- {item['full_name']} — {item['role']} ({item['confidence']})"
                for item in decision_makers[:5]
            )
            or "- No named decision-makers were extracted from the public pages reviewed."
        )
        department_lines = (
            "\n".join(
                f"- {item['department']} ({item['confidence']})"
                for item in department_routes[:5]
            )
            or "- No backup departments were inferred from the public sources reviewed."
        )
        ladder_lines = (
            "\n".join(
                f"- {item['label']}: {item['value']} ({item['confidence']})"
                for item in contact_ladder[:6]
            )
            or "- No public contact ladder items were found."
        )
        source_lines = (
            "\n".join(
                f"- {item['source']} [{item.get('source_type', 'public_source')}]"
                for item in source_trail[:6]
            )
            or "- No public sources recorded."
        )
        return {
            "status": "partial",
            "timestamp": datetime.now().isoformat(),
            "summary": "Lead investigation completed from public sources",
            "full_output": (
                "Action Type: lead_investigation\n\n"
                "FieldOps completed a broader public-source investigation using the provided website plus related public references.\n\n"
                "Verified Entity:\n"
                f"- Name: {verified_entity['name']}\n"
                f"- Website: {verified_entity['website']}\n"
                f"- Address: {verified_entity['address'] or '[not confirmed]'}\n"
<<<<<<< HEAD
                f"- City / State: {verified_entity['city_state'] or '[not confirmed]'}\n"
                f"- Entity Type: {verified_entity['entity_type']}\n\n"
                "Investigation Profile:\n"
                f"- Profile: {investigation_profile.get('label', '[not set]')}\n"
                f"- Strategy: {investigation_profile.get('strategy_summary', '[not set]')}\n\n"
=======
                f"- City / State: {verified_entity['city_state'] or '[not confirmed]'}\n\n"
>>>>>>> 0531c02 (Fix hosted auth and Gmail mission parsing)
                "Lead Relevance:\n"
                f"- Reason: {lead_relevance['reason']}\n"
                f"- Summary: {lead_relevance['summary']}\n"
                f"- Recommendation: {investigation['recommendation']}\n\n"
                "Best Contact Recommendation:\n"
                f"{best_contact_lines}\n\n"
                "Decision-Maker Map:\n"
                f"{decision_lines}\n\n"
                "Department Routing Backup:\n"
                f"{department_lines}\n\n"
                "Contact Ladder:\n"
                f"{ladder_lines}\n\n"
                "Public Source Trail:\n"
                f"{source_lines}\n\n"
                "Next Step:\n"
                "- Review the candidate contacts and, if they look usable, feed approved records into L1 Rolodex Builder.\n"
            ),
            "follow_up_needed": True,
            "carry_forward": bool(mission.carry),
            "action_required": False,
            "action_type": "lead_investigation",
            "action_status": "investigated",
            "action_completed": True,
            "action_details": investigation,
        }
    except LeadInvestigationError as exc:
        return {
            "status": "action_required",
            "timestamp": datetime.now().isoformat(),
            "summary": "Lead investigation needs more public-source input",
            "full_output": str(exc),
            "follow_up_needed": True,
            "carry_forward": bool(mission.carry),
            "action_required": True,
            "action_type": "lead_investigation",
            "action_status": "needs_input",
            "action_completed": False,
            "action_details": {
                "target_name": fields["target_name"],
                "website": fields["website"],
                "desired_contact_type": contact_focus,
            },
        }
    except Exception as exc:
        return {
            "status": "failed",
            "timestamp": datetime.now().isoformat(),
            "summary": "Lead investigation failed",
            "full_output": str(exc),
            "follow_up_needed": True,
            "carry_forward": bool(mission.carry),
            "action_required": True,
            "action_type": "lead_investigation",
            "action_status": "failed",
            "action_completed": False,
        }


def build_mock_result(mission: Mission) -> dict:
    lane = mission.lane.upper() if mission.lane else "GENERAL"
    title = mission.title or "Untitled Mission"
    objective = mission.objective or "No objective provided."

    return {
        "status": "complete",
        "timestamp": datetime.now().isoformat(),
        "summary": f"Mock backend result for {title}",
        "full_output": (
            f"Mission: {title}\n"
            f"Lane: {lane}\n"
            f"Objective: {objective}\n\n"
            "This is a safe Phase 1 mock execution result.\n"
            "Use it to verify the dispatch -> return -> display -> debrief loop."
        ),
        "follow_up_needed": mission.priority in ("high", "critical"),
        "carry_forward": bool(mission.carry),
        "findings": [
            "Backend dispatch path reached successfully.",
            "Persistent mission update path is ready for Phase 1 wiring.",
            "No live AI execution was invoked.",
        ],
        "next_steps": [
            "Review the returned mock result in the existing workflow.",
            "Debrief the mission to verify completed-state persistence.",
        ],
    }


def build_empty_payload_result(mission: Mission) -> dict:
    title = mission.title or "Untitled Mission"
    return {
        "status": "failed",
        "timestamp": datetime.now().isoformat(),
        "summary": "Mission missing actionable payload",
        "full_output": (
            f"Mission: {title}\n\n"
            "This mission was dispatched without an objective, inputs, expected output, "
            "or prompt payload. FieldOps blocked execution so it would not fabricate a result."
        ),
        "follow_up_needed": True,
        "carry_forward": bool(mission.carry),
        "action_required": True,
        "action_type": "",
        "action_status": "missing_payload",
        "action_completed": False,
    }


def build_action_result(mission: Mission, action_type: str) -> dict:
    if action_type == "gmail_create_draft":
        fields = _extract_gmail_draft_fields(mission)
        try:
            draft = create_gmail_draft(
                to=fields["to"],
                subject=fields["subject"],
                body=fields["body"],
                cc=fields["cc"],
                bcc=fields["bcc"],
            )
            return {
                "status": "complete",
                "timestamp": datetime.now().isoformat(),
                "summary": "Gmail draft created successfully",
                "full_output": (
                    "Action Type: gmail_create_draft\n"
                    f"Draft ID: {draft['draft_id']}\n"
                    f"Message ID: {draft['message_id']}\n"
                    f"Subject: {fields['subject']}\n"
                    f"To: {fields['to'] or '[blank]'}\n\n"
                    "A real Gmail draft was created successfully."
                ),
                "follow_up_needed": False,
                "carry_forward": bool(mission.carry),
                "action_required": False,
                "action_type": action_type,
                "action_status": "completed",
                "action_completed": True,
                "action_details": _build_gmail_action_details(fields, draft),
            }
        except (GmailAuthRequiredError, GmailDependencyError) as exc:
            return {
                "status": "action_required",
                "timestamp": datetime.now().isoformat(),
                "summary": "Gmail authorization required",
                "full_output": str(exc),
                "follow_up_needed": True,
                "carry_forward": bool(mission.carry),
                "action_required": True,
                "action_type": action_type,
                "action_status": "auth_required",
                "action_completed": False,
                "action_details": _build_gmail_action_details(fields),
            }
        except Exception as exc:
            return {
                "status": "failed",
                "timestamp": datetime.now().isoformat(),
                "summary": "Gmail draft creation failed",
                "full_output": str(exc),
                "follow_up_needed": True,
                "carry_forward": bool(mission.carry),
                "action_required": True,
                "action_type": action_type,
                "action_status": "failed",
                "action_completed": False,
                "action_details": _build_gmail_action_details(fields),
            }
    if action_type == "calendar_create_event":
        try:
            fields = _extract_calendar_fields(mission)
            event = create_calendar_event(
                title=fields["title"],
                start_local=fields["start_local"],
                end_local=fields["end_local"],
                timezone_str=fields["timezone_str"],
                description=fields["description"],
                calendar_id=fields["calendar_id"],
            )
            return {
                "status": "complete",
                "timestamp": datetime.now().isoformat(),
                "summary": "Google Calendar event created successfully",
                "full_output": (
                    "Action Type: calendar_create_event\n"
                    f"Event ID: {event['event_id']}\n"
                    f"Title: {event['title']}\n"
                    f"Start: {event['start']}\n"
                    f"End: {event['end']}\n"
                    f"Calendar: {event['calendar_id']}\n"
                    f"Time Zone: {event['timezone']}\n"
                    f"Event URL: {event['html_link']}\n\n"
                    "A real Google Calendar event was created successfully."
                ),
                "follow_up_needed": False,
                "carry_forward": bool(mission.carry),
                "action_required": False,
                "action_type": action_type,
                "action_status": "completed",
                "action_completed": True,
                "action_details": event,
            }
        except (CalendarAuthRequiredError, CalendarDependencyError) as exc:
            return {
                "status": "action_required",
                "timestamp": datetime.now().isoformat(),
                "summary": "Google Calendar authorization required",
                "full_output": str(exc),
                "follow_up_needed": True,
                "carry_forward": bool(mission.carry),
                "action_required": True,
                "action_type": action_type,
                "action_status": "auth_required",
                "action_completed": False,
            }
        except Exception as exc:
            return {
                "status": "failed",
                "timestamp": datetime.now().isoformat(),
                "summary": "Google Calendar event creation failed",
                "full_output": str(exc),
                "follow_up_needed": True,
                "carry_forward": bool(mission.carry),
                "action_required": True,
                "action_type": action_type,
                "action_status": "failed",
                "action_completed": False,
            }
    if action_type == "lead_investigation":
        return _build_lead_investigation_result(mission)
    if action_type in {
        "generate_word_report",
        "email_deliverable",
        "log_deliverable",
        "document_completed_work",
        "fallback_handoff_email",
    }:
        fields = _build_fallback_handoff_fields(mission)
        try:
            draft = create_gmail_draft(
                to=fields["to"],
                subject=fields["subject"],
                body=fields["body"],
            )
            return {
                "status": "partial",
                "timestamp": datetime.now().isoformat(),
                "summary": "Fallback handoff draft created for Guy",
                "full_output": (
                    "Action Type: fallback_handoff_email\n"
                    f"Original Requested Action: {mission.actionType or action_type}\n"
                    f"Draft ID: {draft['draft_id']}\n"
                    f"Message ID: {draft['message_id']}\n"
                    f"Subject: {fields['subject']}\n"
                    f"To: {fields['to']}\n\n"
                    "Unsupported work was packaged into a real Gmail handoff draft for Guy."
                ),
                "follow_up_needed": True,
                "carry_forward": bool(mission.carry),
                "action_required": False,
                "action_type": "fallback_handoff_email",
                "action_status": "handoff_created",
                "action_completed": True,
                "action_details": {
                    "draft_id": draft["draft_id"],
                    "message_id": draft["message_id"],
                    "subject": fields["subject"],
                    "to": fields["to"],
                    "requested_action_type": mission.actionType or action_type,
                },
            }
        except (GmailAuthRequiredError, GmailDependencyError) as exc:
            return {
                "status": "action_required",
                "timestamp": datetime.now().isoformat(),
                "summary": "Fallback handoff authorization required",
                "full_output": str(exc),
                "follow_up_needed": True,
                "carry_forward": bool(mission.carry),
                "action_required": True,
                "action_type": "fallback_handoff_email",
                "action_status": "auth_required",
                "action_completed": False,
            }
        except Exception as exc:
            return {
                "status": "failed",
                "timestamp": datetime.now().isoformat(),
                "summary": "Fallback handoff draft creation failed",
                "full_output": str(exc),
                "follow_up_needed": True,
                "carry_forward": bool(mission.carry),
                "action_required": True,
                "action_type": "fallback_handoff_email",
                "action_status": "failed",
                "action_completed": False,
            }
    return {
        "status": "failed",
        "timestamp": datetime.now().isoformat(),
        "summary": "Unsupported action type",
        "full_output": f"FieldOps does not have an executor for action type: {action_type or '[blank]'}",
        "follow_up_needed": True,
        "carry_forward": bool(mission.carry),
        "action_required": True,
        "action_type": action_type,
        "action_status": "unsupported_action_type",
        "action_completed": False,
    }


def mission_has_payload(mission: Mission) -> bool:
    return any(
        [
            (mission.objective or "").strip(),
            (mission.inputs or "").strip(),
            (mission.expectedOutput or "").strip(),
            (mission.prompt or "").strip(),
        ]
    )


def execute_mission(mission: Mission) -> dict:
    mission.status = "dispatched"
    classification = classify_mission(mission)
    mission.executionType = classification["execution_type"]
    mission.actionType = classification["action_type"]

    if not mission_has_payload(mission):
        result = build_empty_payload_result(mission)
        mission.actionStatus = result.get("action_status", "missing_payload")
        mission.actionDetails = result.get("action_details") or None
    elif mission.executionType == "action":
        result = build_action_result(mission, mission.actionType)
        mission.actionStatus = result.get("action_status", "pending_external")
        mission.actionDetails = result.get("action_details") or {
            "action_required": result.get("action_required", False),
            "action_type": result.get("action_type", mission.actionType),
            "action_completed": result.get("action_completed", False),
        }
    else:
        result = build_mock_result(mission)
        mission.actionStatus = ""
        mission.actionDetails = None

    mission.mockResult = result
    mission.resultSummary = result["summary"]
    mission.resultBody = result["full_output"]
    mission.followUp = result["follow_up_needed"]
    mission.carryForward = result["carry_forward"]
    mission.status = "waiting"
    return result
