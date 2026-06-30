# Task 1 Updated/app/services/risk_service.py
"""
services/risk_service.py  –  Rule-based (NON-AI) risk tagging + fallback remark text.

The risk_tag shown on every application is ALWAYS computed here, deterministically,
from the three blood values. It is never read from / inferred by the AI's free-text
output, and is recalculated on every create AND every edit.

Thresholds are intentionally conservative in the middle band — a value that is just
a hair outside the "normal" reference range is "slightly_abnormal", not "high".
"High" is reserved for values that are clearly, clinically abnormal.
"""
from app.models.models import RiskTag

# Reference ranges (gender-neutral, since this simplified system doesn't collect gender)
GLUCOSE_NORMAL = (70, 99)
GLUCOSE_SLIGHT = (60, 125)     # outside normal but inside this band => slightly abnormal
HB_NORMAL = (12.0, 17.5)
HB_SLIGHT = (10.5, 18.5)
CHOL_NORMAL = (0, 199)
CHOL_SLIGHT_MAX = 239


def _glucose_level(g: float) -> int:
    """0 = normal, 1 = slightly abnormal, 2 = high"""
    if GLUCOSE_NORMAL[0] <= g <= GLUCOSE_NORMAL[1]:
        return 0
    if GLUCOSE_SLIGHT[0] <= g <= GLUCOSE_SLIGHT[1]:
        return 1
    return 2


def _hb_level(h: float) -> int:
    if HB_NORMAL[0] <= h <= HB_NORMAL[1]:
        return 0
    if HB_SLIGHT[0] <= h <= HB_SLIGHT[1]:
        return 1
    return 2


def _chol_level(c: float) -> int:
    if c <= CHOL_NORMAL[1]:
        return 0
    if c <= CHOL_SLIGHT_MAX:
        return 1
    return 2


def compute_risk_tag(glucose: float, haemoglobin: float, cholesterol: float) -> RiskTag:
    levels = [_glucose_level(glucose), _hb_level(haemoglobin), _chol_level(cholesterol)]
    max_level = max(levels)
    high_count = levels.count(2)
    slight_count = levels.count(1)

    # Escalate to HIGH only if at least one value is clearly abnormal,
    # or two-plus values are simultaneously off (compounding risk).
    if max_level == 2:
        return RiskTag.high
    if high_count == 0 and slight_count >= 2:
        return RiskTag.high
    if slight_count >= 1:
        return RiskTag.slightly_abnormal
    return RiskTag.normal


def build_fallback_remark(glucose: float, haemoglobin: float, cholesterol: float) -> str:
    """Used ONLY as a last resort when the AI call fails entirely."""
    def tag(level: int, low_word="LOW", high_word="HIGH"):
        return {0: "NORMAL", 1: high_word, 2: high_word}.get(level, "NORMAL") if level else "NORMAL"

    g_lvl, h_lvl, c_lvl = _glucose_level(glucose), _hb_level(haemoglobin), _chol_level(cholesterol)
    g_word = "NORMAL" if g_lvl == 0 else ("ELEVATED" if glucose > GLUCOSE_NORMAL[1] else "LOW")
    h_word = "NORMAL" if h_lvl == 0 else ("HIGH" if haemoglobin > HB_NORMAL[1] else "LOW")
    c_word = "NORMAL" if c_lvl == 0 else ("ELEVATED" if cholesterol > CHOL_NORMAL[1] else "NORMAL")

    return (
        "FINDINGS:\n"
        f"Automated AI analysis could not be completed for this application. "
        f"Based on simple reference-range comparison only: Glucose is {g_word} "
        f"({glucose} mg/dL, reference 70-99 mg/dL fasting). Haemoglobin is {h_word} "
        f"({haemoglobin} g/dL, reference approx. 12.0-17.5 g/dL). Total Cholesterol is {c_word} "
        f"({cholesterol} mg/dL, reference <200 mg/dL desirable).\n\n"
        "RISK ASSESSMENT:\nNot available — this is an automated fallback notice, not a clinical assessment.\n\n"
        "IMMEDIATE ACTIONS:\nPlease have a qualified medical professional review these results directly, "
        "since the automated assessment service is temporarily unavailable.\n\n"
        "LIFESTYLE MODIFICATIONS:\nNot available in fallback mode.\n\n"
        "RECOMMENDATION:\nThis is a system-generated fallback notice, not an AI-generated clinical opinion. "
        "Please consult a physician to interpret these blood test values."
    )
