import re
from typing import Dict, List, Optional, Tuple

# Red-flag clinical emergency condition categories and trigger phrases
RED_FLAG_PATTERNS = {
    "cardiac": [
        r"\bchest pain\b",
        r"\bchest pressure\b",
        r"\bcrushing chest\b",
        r"\bsqueezing chest\b",
        r"\bheart attack\b",
        r"\bpain radiating to (?:left arm|jaw|neck|back)\b",
        r"\bchest tightness with (?:sweat|cold sweat|breathlessness|vomiting)\b",
        r"\bangina\b",
    ],
    "cerebrovascular": [
        r"\bface drooping\b",
        r"\bfacial droop\b",
        r"\bslurred speech\b",
        r"\barm weakness\b",
        r"\bsudden weakness in (?:arm|leg|one side)\b",
        r"\bsudden numbness in (?:arm|leg|one side|face)\b",
        r"\bloss of speech\b",
        r"\bcannot speak clearly\b",
        r"\bstroke\b",
        r"\btransient ischemic attack\b",
        r"\bsudden loss of vision\b",
    ],
    "anaphylaxis": [
        r"\banaphylaxis\b",
        r"\bthroat closing\b",
        r"\bswelling in (?:throat|tongue) after\b",
        r"\ballergic reaction cannot breathe\b",
    ],
    "respiratory_failure": [
        r"\bgasping for (?:breath|air)\b",
        r"\bunable to breathe\b",
        r"\bcannot breathe\b",
        r"\bsevere breathlessness\b",
        r"\bsevere difficulty breathing\b",
        r"\bturning blue\b",
        r"\bcyanosis\b",
        r"\bbluish (?:lips|fingers|face)\b",
        r"\bchoking\b",
        r"\bstridor\b",
        r"\bacute asthma attack cannot speak\b",
    ],
    "hemorrhage": [
        r"\bcoughing (?:up )?blood\b",
        r"\bhemoptysis\b",
        r"\bvomiting blood\b",
        r"\bhematemesis\b",
        r"\buncontrolled bleeding\b",
        r"\bmassive bleeding\b",
        r"\bspurting blood\b",
        r"\bprofuse blood loss\b",
    ],
    "neurological_altered_mental": [
        r"\bunconscious\b",
        r"\blost consciousness\b",
        r"\bpassed out\b",
        r"\bunresponsive\b",
        r"\bconvulsions\b",
        r"\bseizure lasting\b",
        r"\bstatus epilepticus\b",
        r"\bhead injury with (?:vomiting|loss of consciousness|seizure)\b",
        r"\bsudden severe thunderclap headache\b",
    ],
    "psychiatric_crisis": [
        r"\bsuicid(?:e|al)\b",
        r"\bkill myself\b",
        r"\bwant to die\b",
        r"\bend my life\b",
        r"\bself harm\b",
        r"\bhurt myself\b",
    ],
}

EMERGENCY_HELPLINES = [
    "108 - Free Emergency Ambulance & Medical Response (Tamil Nadu & National)",
    "112 - National Unified Emergency Service (India)",
    "Nearest Hospital Emergency Room (ER/Casualty)",
]

EMERGENCY_INSTRUCTIONS = (
    "CRITICAL MEDICAL ALERT: Your symptoms may indicate an acute, life-threatening medical emergency. "
    "DO NOT wait for an outpatient appointment or delay seeking care. "
    "Please call 108 or 112 immediately, or proceed to the nearest hospital Emergency Department (Casualty) right away."
)


def check_red_flags(text: str) -> Tuple[bool, List[str], Optional[str]]:
    """
    Evaluates patient input text against deterministic red-flag emergency patterns.
    Returns:
        (is_red_flag: bool, matched_patterns: List[str], primary_category: Optional[str])
    """
    if not text:
        return False, [], None

    clean_text = text.lower()
    matched_conditions = []
    first_category = None

    for category, patterns in RED_FLAG_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, clean_text, re.IGNORECASE):
                condition_label = pattern.replace(r"\b", "").replace(r"(?:", "").replace(r")", "")
                matched_conditions.append(f"{category}: {condition_label}")
                if first_category is None:
                    first_category = category

    is_emergency = len(matched_conditions) > 0
    return is_emergency, matched_conditions, first_category
