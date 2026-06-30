# HealthChecker/app/services/ai_service.py
"""
services/ai_service.py  –  Gemini API integration with key rotation.

Manages up to 5 API keys. If one returns 429 (rate limited) or fails,
it automatically rotates to the next available key. Uses asyncio semaphore
to limit concurrent calls and avoid flooding the API.

"""
import asyncio
import logging
import os
from pathlib import Path
import httpx
from dotenv import load_dotenv

# ── FIX 1: Robust .env Discovery for both Server & Background Worker ──
current_dir = Path(__file__).resolve().parent
for tier in [current_dir.parent, current_dir.parent.parent, current_dir.parent.parent.parent]:
    possible_env = tier / '.env'
    if possible_env.exists():
        load_dotenv(dotenv_path=possible_env)
        break
else:
    load_dotenv()

logger = logging.getLogger(__name__)

# ── FIX 2: Load, Strip Windows Spaces, and Validate Active Keys ──────────
_ALL_KEYS: list[str] = []
for i in range(1, 6):
    raw_key = os.getenv(f"GEMINI_API_KEY_{i}") or (os.getenv("GEMINI_API_KEY") if i == 1 else None)
    if raw_key:
        clean_key = raw_key.strip()
        if clean_key and "your-" not in clean_key:
            _ALL_KEYS.append(clean_key)

if not _ALL_KEYS:
    logger.warning("No valid Gemini API keys found in environment.")
else:
    logger.info(f"Successfully loaded {len(_ALL_KEYS)} Gemini key(s).")

# Semaphore is created lazily inside the running event loop
_semaphore: asyncio.Semaphore | None = None


def _get_semaphore() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(3)
    return _semaphore

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"

# Models tried in order. Flash has higher quality; Lite is the rate-limit fallback.
MODELS_IN_ORDER = ["gemini-2.5-flash", "gemini-2.5-flash-lite"]

# Retry settings for non-rate-limit errors (network, 5xx, parse failures)
MAX_ERROR_RETRIES = 3
BASE_BACKOFF_S = 1.5   # doubles each retry: 1.5 → 3 → 6
MAX_BACKOFF_S = 15.0

def _build_prompt(
    glucose: float,
    haemoglobin: float,
    cholesterol: float,
    age: int,
) -> str:
    hb_status = (
        "LOW" if (haemoglobin < 12.0)
        else "HIGH" if haemoglobin > 17.5
        else "NORMAL"
    )
    glucose_stage = (
        "CRITICAL — severe hyperglycaemia" if glucose >= 300
        else "HIGH — consistent with uncontrolled diabetes" if glucose >= 200
        else "HIGH — consistent with diabetes" if glucose >= 126
        else "BORDERLINE — prediabetic range" if glucose >= 100
        else "CRITICAL — severe hypoglycaemia" if glucose < 55
        else "LOW — hypoglycaemia" if glucose < 70
        else "NORMAL"
    )
    chol_stage = (
        "HIGH" if cholesterol >= 240
        else "BORDERLINE HIGH" if cholesterol >= 200
        else "DESIRABLE"
    )

    return f"""You are a consultant physician with 20 years of clinical experience, writing a formal Blood Test Assessment Report. This report will be filed in the patient's medical record and reviewed by their treating physician. It must meet the standard of a real clinical document.

═══════════════════════════════════════════
PATIENT BLOOD TEST DATA
═══════════════════════════════════════════
Age: {age} years 

  Fasting Glucose:   {glucose} mg/dL   → {glucose_stage}
                     Reference: 70–99 mg/dL (fasting)

  Haemoglobin:       {haemoglobin} g/dL   → {hb_status}
                     Reference: 12.0–17.5 g/dL

  Total Cholesterol: {cholesterol} mg/dL   → {chol_stage}
                     Reference: <200 mg/dL desirable, ≥240 mg/dL high
═══════════════════════════════════════════

Write a complete, unabbreviated clinical assessment using EXACTLY the five section headers below, in order. Each section must be thorough. Do not truncate any section.

FINDINGS:
Provide a precise quantitative interpretation of each value. State the absolute deviation from the reference range. Classify severity (mild / moderate / severe / critical). Note which values are within range and confirm them explicitly — do not skip normal values. If all values are within normal range, state this clearly and do not manufacture concerns. Use clinical terminology with plain-language parenthetical explanations where needed.

RISK ASSESSMENT:
Perform a multi-factor clinical risk analysis. Do not assess values in isolation — reason about how they interact. Specifically:
- If both glucose and cholesterol are elevated, evaluate for metabolic syndrome criteria and cardiovascular risk compounding.
- Assign a qualitative overall cardiovascular risk tier (low / moderate / high / very high) with justification.
- Name all probable primary diagnoses and differential conditions this panel is consistent with.
- Note any conditions that are less likely but cannot be excluded without further investigation.
- For each identified probable diagnosis, assign a confidence level in percentage with a one-line justification based solely on the available panel values.
- Consider the patient's age in your risk stratification.

IMMEDIATE ACTIONS:
List exactly 5 numbered, specific, time-bound actions the patient should take within the next 2–4 weeks. Each action must name a specific specialist, test, dietary change, or medication class where appropriate. Generic statements like "eat healthy" or "see a doctor" are not acceptable — every action must be specific enough that the patient knows exactly what to do. Include at minimum: one specialist referral with reason, one specific diagnostic test to order next, one immediate dietary restriction, one physical activity guideline with frequency and intensity, and one monitoring instruction (e.g. self-monitoring glucose frequency).

LIFESTYLE MODIFICATIONS:
Provide 4 evidence-based, long-term lifestyle recommendations tailored precisely to this patient's values and age. Reference specific targets where possible (e.g. target HbA1c, LDL target, BMI range, weekly activity minutes). These should reflect current clinical guidelines (ADA, ACC/AHA, WHO).

RECOMMENDATION:
Write a 3–4 sentence formal clinical summary in the style of a consultant's letter to a GP. Use appropriate ICD-10 aligned terminology. Summarise the key findings, the most probable diagnoses, and the recommended clinical pathway. This section may use full medical terminology without plain-language simplification.

═══════════════════════════════════════════
FORMATTING RULES — STRICTLY ENFORCED:
- Begin your response with the exact text: FINDINGS:
- Do not write anything before FINDINGS: — no greeting, no preamble, no title
- Do not add any text after the RECOMMENDATION section ends
- Do not use markdown, asterisks, bullet symbols, or bold formatting — use plain text only
- Write each section fully — incomplete sections are not acceptable
- Be highly concise and compact. Keep paragraphs short and descriptions tight.
- Ensure the entire five-section report is fully completed and stays under 350 words total.
═══════════════════════════════════════════"""

async def get_health_prediction(
    glucose: float,
    haemoglobin: float,
    cholesterol: float,
    age: int,
) -> str:
    """
    Calls Gemini API with this priority order:
      1. gemini-2.5-flash, rotating through all keys
      2. gemini-2.5-flash-lite, rotating through all keys (rate-limit fallback only)

    Rate limit (429):      rotate to next key; if all keys exhausted, try next model.
    Other errors (5xx etc): exponential backoff, up to MAX_ERROR_RETRIES per key.
    If flash-lite keys are also all rate-limited: give up. No infinite loop.
    """
    if not _ALL_KEYS:
        raise RuntimeError("No Gemini API keys configured.")

    prompt = _build_prompt(glucose, haemoglobin, cholesterol, age)
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 1500,
            "topP": 0.9,
            "thinkingConfig": {"thinkingBudget": 512},  # Optimized to allocate more space for the final sections
        },
    }

    async with _get_semaphore():
        for model in MODELS_IN_ORDER:
            all_keys_rate_limited = True  # Assume true; disproved if any key gets a non-429 response

            for key in _ALL_KEYS:
                url = GEMINI_BASE_URL.format(model=model, key=key)

                for attempt in range(1, MAX_ERROR_RETRIES + 1):
                    try:
                        async with httpx.AsyncClient(timeout=30.0) as client:
                            response = await client.post(url, json=payload)

                        # ── Rate limited: stop retrying this key, move to next ──
                        if response.status_code == 429:
                            logger.warning(f"[{model}] Key ending …{key[-6:]} rate limited. Rotating key.")
                            break  # breaks the retry loop → moves to next key

                        # ── Server error: exponential backoff, then retry same key ──
                        if response.status_code >= 500:
                            all_keys_rate_limited = False
                            wait = min(BASE_BACKOFF_S * (2 ** (attempt - 1)), MAX_BACKOFF_S)
                            logger.warning(f"[{model}] HTTP {response.status_code} on attempt {attempt}/{MAX_ERROR_RETRIES}. Retrying in {wait:.1f}s…")
                            await asyncio.sleep(wait)
                            continue

                        # ── Any other 4xx (bad key, quota exhausted permanently, etc.) ──
                        response.raise_for_status()
                        all_keys_rate_limited = False

                        # ── Parse response ──
                        data = response.json()
                        candidates = data.get("candidates", [])
                        if not candidates:
                            raise ValueError("Gemini returned no candidates.")
                        if candidates[0].get("finishReason") == "SAFETY":
                            raise ValueError("Gemini blocked response for safety reasons.")
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if not parts or not parts[0].get("text"):
                            raise ValueError("Gemini returned empty content.")

                        raw_text = parts[0]["text"].strip()

                        # Salvage if model ignored FINDINGS: prefix
                        if not raw_text.upper().startswith("FINDINGS:"):
                            for line in raw_text.splitlines():
                                if line.upper().startswith("FINDINGS:"):
                                    raw_text = raw_text[raw_text.upper().index("FINDINGS:"):]
                                    break
                            else:
                                raw_text = f"FINDINGS: {raw_text}"

                        logger.info(f"[{model}] Success on key ending …{key[-6:]} (attempt {attempt}).")
                        return raw_text

                    except (httpx.TimeoutException, httpx.ConnectError) as e:
                        all_keys_rate_limited = False
                        wait = min(BASE_BACKOFF_S * (2 ** (attempt - 1)), MAX_BACKOFF_S)
                        logger.warning(f"[{model}] Network error attempt {attempt}/{MAX_ERROR_RETRIES}: {e}. Retrying in {wait:.1f}s…")
                        await asyncio.sleep(wait)

                    except ValueError as e:
                        all_keys_rate_limited = False
                        wait = min(BASE_BACKOFF_S * (2 ** (attempt - 1)), MAX_BACKOFF_S)
                        logger.warning(f"[{model}] Parse error attempt {attempt}/{MAX_ERROR_RETRIES}: {e}. Retrying in {wait:.1f}s…")
                        await asyncio.sleep(wait)

                    except httpx.HTTPStatusError as e:
                        all_keys_rate_limited = False
                        if e.response.status_code == 400:
                            # 400 can be key-specific (API not enabled for that project)
                            # Rotate to next key rather than aborting the model entirely
                            logger.warning(f"[{model}] 400 Bad Request on key …{key[-6:]}, rotating key.")
                            break  # breaks retry loop → next key
                        logger.error(f"[{model}] Non-retryable HTTP error: {e}")
                        raise RuntimeError(f"Gemini API request failed: {e}") from e

            # If we exhausted all keys and every single one was rate-limited,
            # try the next model. If it was non-429 failures, we already retried.
            if all_keys_rate_limited:
                logger.warning(f"[{model}] All keys rate-limited. Trying next model…")
            else:
                # All keys tried with proper retries, none succeeded for non-rate-limit reasons
                raise RuntimeError(f"[{model}] All keys failed with non-rate-limit errors.")

        # Reached here only if BOTH models had all keys rate-limited
        raise RuntimeError("All models and keys are rate-limited. Request aborted.")
