import os
import re
import sys

import requests
from langchain_ollama import ChatOllama

# Inside Docker Compose the service name "api" is used.
# For local runs: API_URL=http://localhost:8000
API_URL = os.getenv("API_URL", "http://localhost:8000")
TIMEOUT = 10  # seconds


def api_get(path: str, params: dict | None = None):
    response = requests.get(f"{API_URL}{path}", params=params, timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()


# 1. RETRIEVAL FUNCTIONS (read-only; run by the code on every inquiry)

def get_services() -> list[dict]:
    """Service table: name, price, duration."""
    return api_get("/api/services")


def get_studio_info() -> dict:
    """Opening hours, cancellation policy, referral policy."""
    return api_get("/api/studio_info")


def build_facts(services: list[dict], info: dict) -> str:
    lines = ["Services (name: price, duration):"]
    lines += [
        f"- {s['name']}: €{s['price_eur']}, {s['duration_min']} minutes"
        for s in services
    ]
    lines.append("")
    lines.append(f"Opening hours: {info.get('opening_hours', 'not available')}")
    lines.append(f"Cancellation: {info.get('cancellation_policy', 'not available')}")
    lines.append(f"Referral policy: {info.get('referral_policy', 'not available')}")
    return "\n".join(lines)


# 2. SAFETY CHECK: medical questions and complaints are never answered by the model.
# Deliberately simple (keyword list). The system prompt and the output check
# are further layers.
ESCALATION_KEYWORDS = [
    # medical
    "burn", "rash", "allerg", "infect", "swollen", "swelling", "bleed", "blister",
    "irritat", "redness", "skin reaction", "pain", "doctor", "medic", "pregnan",
    "brennt", "ausschlag", "allergi", "entzünd", "geschwollen",
    # complaints
    "complain", "complaint", "unhappy", "disappointed", "not satisfied", "refund",
    "terrible", "worst", "angry", "beschwerde", "unzufrieden",
]

SIGN_OFF = "Kind regards,\nYour Studio Team"

ESCALATION_REPLY = (
    "Hello,\n\n"
    "Thank you for getting in touch, and I'm sorry to hear this. "
    "I can't give medical advice or handle complaints here, so please contact our "
    "studio team directly. They can look at your situation personally and help you "
    "best. If your symptoms are severe or getting worse, please seek medical help "
    "right away.\n\n" + SIGN_OFF
)

FALLBACK_REPLY = (
    "Hello,\n\n"
    "Thank you for your message. I can't answer this reliably here, so please "
    "contact our studio team directly. They will be happy to help.\n\n" + SIGN_OFF
)


def needs_escalation(inquiry: str) -> bool:
    text = inquiry.lower()
    return any(keyword in text for keyword in ESCALATION_KEYWORDS)


# 3. LLM (writes only the body of the reply)
SYSTEM_PROMPT = """You write the BODY of a short, friendly reply to a customer of a beauty studio (test environment).
Write 2 to 5 sentences. Do not write a greeting or a sign-off; those are added automatically.

Rules:
1. Use ONLY the information under FACTS. Never invent services, prices, durations, opening hours, discounts, policies, phone numbers or e-mail addresses.
2. If the customer asks about price, duration or booking but does not name one of the listed treatments, do not guess. Ask which treatment they mean and list the treatments with their prices.
3. If the customer asks about something that is not in FACTS (for example a service that is not listed), say that you do not have information about it and that the studio team can help. Do not say or imply that the studio offers it.
4. You only draft replies. You cannot book, cancel or send anything, and you never say that you did. If the customer wants to book, say that the studio team will arrange it.
5. Reply in the customer's language."""

llm = ChatOllama(model="llama3.2", temperature=0)


def clean_body(text: str) -> str:
    """Remove a greeting or sign-off if the model added one anyway."""
    text = text.strip()
    text = re.sub(r"(?i)^(hello|hi|dear)[^\n]*\n+", "", text)
    text = re.sub(r"(?is)\n+\s*(kind regards|best regards|regards)\b.*$", "", text)
    return text.strip()


def reply_is_grounded(body: str, services: list[dict]) -> bool:
    """Every price and duration mentioned must exist in the service table."""
    allowed_prices = {str(s["price_eur"]) for s in services}
    allowed_minutes = {str(s["duration_min"]) for s in services}
    prices = re.findall(r"€\s*(\d+)", body) + re.findall(
        r"(\d+)\s*(?:€|euros?\b)", body, flags=re.I
    )
    minutes = re.findall(r"(\d+)\s*(?:minutes|min)\b", body, flags=re.I)
    return all(p in allowed_prices for p in prices) and all(
        m in allowed_minutes for m in minutes
    )


def draft_reply(inquiry: str):
    """Returns (draft text, steps taken). Nothing is sent or booked."""
    if needs_escalation(inquiry):
        return ESCALATION_REPLY, ["escalation check (no model call)"]

    try:
        services = get_services()
        info = get_studio_info()
    except requests.RequestException as e:
        return (f"[Studio data is not available right now: {e}]", ["retrieval failed"])

    steps = ["get_services", "get_studio_info"]
    facts = build_facts(services, info)
    prompt = f"FACTS:\n{facts}\n\nCUSTOMER INQUIRY:\n{inquiry}"

    for _ in range(2):  # one retry if the model answers badly
        response = llm.invoke([("system", SYSTEM_PROMPT), ("user", prompt)])
        body = clean_body(str(response.content))
        if len(body) >= 30 and reply_is_grounded(body, services):
            return f"Hello,\n\n{body}\n\n{SIGN_OFF}", steps + ["llm draft"]

    return FALLBACK_REPLY, steps + ["fallback (model reply failed the checks)"]


def run(inquiry: str):
    print("\n" + "=" * 60)
    print(f"CUSTOMER INQUIRY: {inquiry}")
    reply, steps = draft_reply(inquiry)
    print(f"STEPS: {' -> '.join(steps)}")
    print("--- DRAFT REPLY (not sent) ---")
    print(reply)


TEST_INQUIRIES = [
    "How much does underarm waxing cost, and how long does it take?",
    "How much does a treatment cost?",
    "Do you offer massages?",
    "My skin has been burning since my treatment. What should I do?",
]

if __name__ == "__main__":
    args = sys.argv[1:]

    if args and args[0] == "--test":
        # python agent.py --test
        for inquiry in TEST_INQUIRIES:
            run(inquiry)
    elif args:
        # python agent.py "your inquiry"
        run(" ".join(args))
    else:
        # python agent.py  (interactive; empty line quits)
        print("Studio assistant (drafts only, nothing is sent or booked).")
        while True:
            try:
                inquiry = input("\nCustomer inquiry (empty line to quit): ").strip()
            except EOFError:
                break
            if not inquiry:
                break
            run(inquiry)