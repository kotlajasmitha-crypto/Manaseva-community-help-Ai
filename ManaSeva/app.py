from __future__ import annotations

import json
import os
import re
import sqlite3
import urllib.error
import urllib.request
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import streamlit as st


APP_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("MANASEVA_DATA_DIR", str(APP_DIR / "data")))
REPORTS_DB = DATA_DIR / "issue_reports.sqlite3"
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "gemma3:1b")
REQUEST_TIMEOUT = 90
UNVERIFIED_LINK_PATTERN = re.compile(
    r"(?i)(?:\b(?:https?|ftp|javascript|data):\S+|\bwww\.[^\s<>\"')\]]+|"
    r"\b(?:[a-z0-9-]+\.)+(?:gov\.in|nic\.in|co\.in|ac\.in|edu\.in|in|gov|com|"
    r"org|net|edu|info|io|us|uk|site|app|ai|xyz|online)\b)"
)
MARKDOWN_LINK_PATTERN = re.compile(r"\[[^\]]+\]\([^)]*\)")
PHONE_NUMBER_PATTERN = re.compile(r"(?<!\w)\+?\d[\d\s().-]{5,}\d(?!\w)")
SCHEME_LOOKUP_PATTERN = re.compile(
    r"(?i)\b(?:scheme|schemes|eligibility|eligible|qualify|qualified|yojana)\b|పథక|అర్హత"
)
SCHOLARSHIP_LOOKUP_PATTERN = re.compile(r"(?i)\b(?:scholarship|scholarships|grant|grants)\b|స్కాలర్")

CATEGORIES = {
    "Health services": "ఆరోగ్య సేవలు",
    "Education": "విద్య",
    "Government schemes": "ప్రభుత్వ పథకాలు",
    "Sanitation": "పరిశుభ్రత",
    "Public services": "ప్రజా సేవలు",
    "General help": "సాధారణ సహాయం",
}

REPORT_CATEGORIES = {
    "Garbage or waste": "చెత్త లేదా వ్యర్థాలు",
    "Water shortage": "నీటి కొరత",
    "Damaged road": "దెబ్బతిన్న రహదారి",
    "Streetlight": "వీధి దీపం",
    "Other": "ఇతర సమస్య",
}

TEXT = {
    "English": {
        "subtitle": "Friendly, local-first help for your community.",
        "intro": "Ask a question, find official resources, or privately report a local issue.",
        "language": "Choose language / భాషను ఎంచుకోండి",
        "category": "Choose a help category",
        "chat_title": "Ask ManaSeva",
        "clear_chat": "Clear chat",
        "chat_intro": "Ask in simple English or Telugu. Please do not share names, phone numbers, or other private details.",
        "chat_placeholder": "For example: Where can I find official scholarship information?",
        "you": "You",
        "assistant": "ManaSeva",
        "ai_source": "Answered by your local Ollama model.",
        "demo_source": "Showing a safe offline demo answer because the local AI is unavailable.",
        "verified_source": "Showing checked, general guidance. Use the official links below to confirm current eligibility.",
        "unsafe_answer": "The AI suggested an unverified link or phone number, so its reply was replaced with checked general guidance. Use the official links below.",
        "fallback_title": "Offline demo is ready",
        "fallback_body": "Ollama is not ready for this model right now. You can still try the basic demo; install or start Ollama to get AI-generated replies.",
        "report_title": "Report a community issue",
        "report_intro": "Reports are stored privately on this computer. They are not published or shown to other visitors.",
        "report_category": "Issue type",
        "location": "Area or nearby landmark",
        "location_hint": "Use a general area, not your home address.",
        "description": "What is happening?",
        "description_hint": "Describe the issue without adding names, phone numbers, or personal details.",
        "submit": "Save private report",
        "report_success": "Your report was saved privately on this computer. It has not been sent to a government office.",
        "report_error": "The report could not be saved. Check that the project folder is writable and try again.",
        "report_validation": "Please choose an issue type and add an area and description.",
        "resources_title": "Trusted websites & emergency help",
        "resources_intro": "These links point to official Indian government websites. Check the local authority's website for services in your area.",
        "warning_title": "Important safety note",
        "warning_body": "AI can make mistakes. Check important information with an official source. In an emergency in India, call 112 or use the official 112 India website. Do not wait for an AI reply.",
        "privacy_title": "Privacy first",
        "privacy_body": "Do not enter personal or sensitive information. Chat messages stay in this browser session. Reports are kept only in this project's local database and are not displayed publicly.",
        "ollama_ready": "Local AI model is ready",
        "ollama_missing": "Ollama is running, but the selected model is not installed.",
        "ollama_offline": "Ollama is not reachable. The offline demo still works.",
        "model_setting": "Model",
        "empty_location": "Please enter a general area or nearby landmark.",
        "empty_description": "Please describe the issue before saving.",
        "resource_health": "Health information from the Ministry of Health and Family Welfare",
        "resource_emergency": "Official Government of India emergency response service. Call 112 in an emergency.",
        "resource_schemes": "Search government schemes and check eligibility with official details.",
        "resource_scholarships": "Government scholarship information and applications.",
        "resource_services": "Find government services and official service portals.",
        "resource_grievances": "Official Centralized Public Grievance Redress and Monitoring System.",
    },
    "తెలుగు": {
        "subtitle": "మీ సమాజానికి సులభమైన, స్థానిక సహాయం.",
        "intro": "ప్రశ్న అడగండి, అధికారిక సమాచారం చూడండి లేదా స్థానిక సమస్యను ప్రైవేట్‌గా నమోదు చేయండి.",
        "language": "భాషను ఎంచుకోండి / Choose language",
        "category": "సహాయ వర్గాన్ని ఎంచుకోండి",
        "chat_title": "ManaSevaను అడగండి",
        "clear_chat": "చాట్‌ను తొలగించండి",
        "chat_intro": "సులభమైన తెలుగు లేదా ఆంగ్లంలో అడగండి. పేర్లు, ఫోన్ నంబర్లు లేదా వ్యక్తిగత వివరాలు పంచుకోవద్దు.",
        "chat_placeholder": "ఉదాహరణ: స్కాలర్‌షిప్‌ల అధికారిక సమాచారం ఎక్కడ దొరుకుతుంది?",
        "you": "మీరు",
        "assistant": "ManaSeva",
        "ai_source": "మీ స్థానిక Ollama మోడల్ సమాధానం ఇచ్చింది.",
        "demo_source": "స్థానిక AI అందుబాటులో లేదు; సురక్షిత ఆఫ్‌లైన్ డెమో సమాధానం చూపిస్తున్నాం.",
        "verified_source": "తనిఖీ చేసిన సాధారణ సమాచారం చూపిస్తున్నాం. తాజా అర్హత కోసం కింద ఉన్న అధికారిక లింకులను చూడండి.",
        "unsafe_answer": "AI ధృవీకరించని లింక్ లేదా ఫోన్ నంబర్ సూచించినందున ఆ సమాధానాన్ని మార్చాం. కింద ఉన్న అధికారిక లింకులను చూడండి.",
        "fallback_title": "ఆఫ్‌లైన్ డెమో సిద్ధంగా ఉంది",
        "fallback_body": "ప్రస్తుతం ఈ మోడల్ కోసం Ollama సిద్ధంగా లేదు. ప్రాథమిక డెమోను ఉపయోగించవచ్చు; AI సమాధానాల కోసం Ollamaను ప్రారంభించండి.",
        "report_title": "సమాజ సమస్యను నివేదించండి",
        "report_intro": "నివేదికలు ఈ కంప్యూటర్‌లో ప్రైవేట్‌గా నిల్వ ఉంటాయి. అవి ప్రచురించబడవు లేదా ఇతరులకు చూపబడవు.",
        "report_category": "సమస్య రకం",
        "location": "ప్రాంతం లేదా దగ్గరి గుర్తింపు స్థలం",
        "location_hint": "సాధారణ ప్రాంతాన్ని ఇవ్వండి; మీ ఇంటి చిరునామా వద్దు.",
        "description": "ఏమి జరుగుతోంది?",
        "description_hint": "పేర్లు, ఫోన్ నంబర్లు లేదా వ్యక్తిగత వివరాలు లేకుండా సమస్యను వివరించండి.",
        "submit": "ప్రైవేట్ నివేదికను భద్రపరచండి",
        "report_success": "మీ నివేదిక ఈ కంప్యూటర్‌లో ప్రైవేట్‌గా భద్రపరచబడింది. అది ప్రభుత్వ కార్యాలయానికి పంపబడలేదు.",
        "report_error": "నివేదికను భద్రపరచలేకపోయాం. ప్రాజెక్ట్ ఫోల్డర్‌లో రాయగలిగే అనుమతి ఉందో చూసి మళ్లీ ప్రయత్నించండి.",
        "report_validation": "సమస్య రకాన్ని ఎంచుకుని, ప్రాంతం మరియు వివరణను నమోదు చేయండి.",
        "resources_title": "నమ్మకమైన వెబ్‌సైట్లు మరియు అత్యవసర సహాయం",
        "resources_intro": "ఈ లింకులు భారత ప్రభుత్వ అధికారిక వెబ్‌సైట్లకు తీసుకెళ్తాయి. మీ ప్రాంత సేవల కోసం స్థానిక అధికారిక వెబ్‌సైట్‌ను చూడండి.",
        "warning_title": "ముఖ్యమైన భద్రతా సూచన",
        "warning_body": "AI తప్పులు చేయవచ్చు. ముఖ్యమైన సమాచారాన్ని అధికారిక వనరుతో నిర్ధారించండి. భారతదేశంలో అత్యవసర పరిస్థితిలో 112కు కాల్ చేయండి లేదా అధికారిక 112 India వెబ్‌సైట్‌ను చూడండి. AI సమాధానం కోసం వేచి ఉండకండి.",
        "privacy_title": "మీ గోప్యత ముఖ్యం",
        "privacy_body": "వ్యక్తిగత లేదా సున్నితమైన సమాచారాన్ని నమోదు చేయవద్దు. చాట్ సందేశాలు ఈ బ్రౌజర్ సెషన్‌లో ఉంటాయి. నివేదికలు ఈ ప్రాజెక్ట్ స్థానిక డేటాబేస్‌లో మాత్రమే ఉంటాయి; బహిరంగంగా చూపబడవు.",
        "ollama_ready": "స్థానిక AI మోడల్ సిద్ధంగా ఉంది",
        "ollama_missing": "Ollama నడుస్తోంది, కానీ ఎంచుకున్న మోడల్ ఇన్‌స్టాల్ కాలేదు.",
        "ollama_offline": "Ollamaను చేరుకోలేకపోతున్నాం. ఆఫ్‌లైన్ డెమో పనిచేస్తుంది.",
        "model_setting": "మోడల్",
        "empty_location": "సాధారణ ప్రాంతం లేదా దగ్గరి గుర్తింపు స్థలాన్ని నమోదు చేయండి.",
        "empty_description": "భద్రపరచడానికి ముందు సమస్యను వివరించండి.",
        "resource_health": "ఆరోగ్య మరియు కుటుంబ సంక్షేమ మంత్రిత్వ శాఖ సమాచారం",
        "resource_emergency": "భారత ప్రభుత్వ అధికారిక అత్యవసర సేవ. అత్యవసరంలో 112కు కాల్ చేయండి.",
        "resource_schemes": "ప్రభుత్వ పథకాలు మరియు అర్హతను అధికారిక వివరాలతో చూడండి.",
        "resource_scholarships": "ప్రభుత్వ స్కాలర్‌షిప్ సమాచారం మరియు దరఖాస్తులు.",
        "resource_services": "ప్రభుత్వ సేవలు మరియు అధికారిక సేవా పోర్టల్‌లను కనుగొనండి.",
        "resource_grievances": "కేంద్ర ప్రభుత్వ అధికారిక ప్రజా ఫిర్యాదుల పరిష్కార పోర్టల్.",
    },
}

RESOURCES = [
    ("Emergency help — 112 India", "https://112.gov.in/", "resource_emergency"),
    ("Ministry of Health and Family Welfare", "https://mohfw.gov.in/", "resource_health"),
    ("MyScheme — Government schemes", "https://www.myscheme.gov.in/", "resource_schemes"),
    ("National Scholarship Portal", "https://scholarships.gov.in/", "resource_scholarships"),
    ("National Government Services Portal", "https://services.india.gov.in/", "resource_services"),
    ("CPGRAMS — Public grievances", "https://pgportal.gov.in/", "resource_grievances"),
]

OFFLINE_ANSWERS = {
    "English": {
        "Health services": (
            "For an emergency in India, call 112 now; do not wait for this demo. For non-emergency health questions, "
            "speak with a qualified health professional and use the Ministry of Health's official website. "
            "This demo cannot diagnose illness or recommend treatment."
        ),
        "Education": (
            "For education and scholarship information, check the official National Scholarship Portal and confirm "
            "application dates and eligibility there. Ask your school or college office if you need help applying."
        ),
        "Government schemes": (
            "Scheme rules depend on the scheme and your state. Search the official MyScheme website, read the eligibility "
            "and document list on the linked government website, and confirm details with the relevant government office. "
            "This demo cannot confirm that you qualify."
        ),
        "Sanitation": (
            "For a sanitation or waste problem, note the general area and report it to your municipal or local-body office "
            "using that office's official website. Do not share a home address or personal details here."
        ),
        "Public services": (
            "Use the National Government Services Portal to find official services. The service and requirements can vary "
            "by state, so check the linked department's official website before applying."
        ),
        "General help": (
            "I can point you to official information, but I cannot confirm local rules or replace professional advice. "
            "Choose a category or open one of the verified government resources below. For an emergency in India, call 112."
        ),
    },
    "తెలుగు": {
        "Health services": (
            "భారతదేశంలో అత్యవసర పరిస్థితి అయితే వెంటనే 112కు కాల్ చేయండి; ఈ డెమో సమాధానం కోసం వేచి ఉండకండి. "
            "సాధారణ ఆరోగ్య ప్రశ్నలకు అర్హత కలిగిన ఆరోగ్య నిపుణుడిని సంప్రదించి, ఆరోగ్య మంత్రిత్వ శాఖ అధికారిక వెబ్‌సైట్‌ను చూడండి. "
            "ఈ డెమో వ్యాధిని నిర్ధారించదు లేదా చికిత్సను సూచించదు."
        ),
        "Education": (
            "విద్య మరియు స్కాలర్‌షిప్ వివరాల కోసం అధికారిక National Scholarship Portalను చూడండి. "
            "దరఖాస్తు తేదీలు, అర్హతను అక్కడ నిర్ధారించండి. దరఖాస్తు సహాయం కోసం మీ పాఠశాల లేదా కళాశాల కార్యాలయాన్ని అడగండి."
        ),
        "Government schemes": (
            "పథకం నియమాలు, మీ రాష్ట్రం ఆధారంగా మారవచ్చు. అధికారిక MyScheme వెబ్‌సైట్‌లో వెతికి, "
            "అర్హత మరియు పత్రాల జాబితాను సంబంధిత ప్రభుత్వ వెబ్‌సైట్‌లో నిర్ధారించండి. మీరు అర్హులని ఈ డెమో నిర్ధారించలేదు."
        ),
        "Sanitation": (
            "పరిశుభ్రత లేదా చెత్త సమస్యకు సాధారణ ప్రాంతాన్ని నమోదు చేసి, మీ మున్సిపాలిటీ లేదా స్థానిక సంస్థ అధికారిక వెబ్‌సైట్‌లో ఫిర్యాదు చేయండి. "
            "ఇక్కడ ఇంటి చిరునామా లేదా వ్యక్తిగత వివరాలు పంచుకోవద్దు."
        ),
        "Public services": (
            "అధికారిక సేవలను కనుగొనడానికి National Government Services Portalను ఉపయోగించండి. "
            "సేవ మరియు అవసరాలు రాష్ట్రం ఆధారంగా మారవచ్చు; దరఖాస్తుకు ముందు సంబంధిత శాఖ అధికారిక వెబ్‌సైట్‌ను చూడండి."
        ),
        "General help": (
            "అధికారిక సమాచారాన్ని కనుగొనడంలో సహాయపడతాను; కానీ స్థానిక నియమాలను నిర్ధారించలేను లేదా నిపుణుల సలహాకు బదులు కాను. "
            "ఒక వర్గాన్ని ఎంచుకోండి లేదా కింద ఉన్న అధికారిక ప్రభుత్వ వనరులను చూడండి. భారతదేశంలో అత్యవసరానికి 112కు కాల్ చేయండి."
        ),
    },
}


class OllamaError(Exception):
    """Raised when the local Ollama service cannot return a usable answer."""


class UnsafeAIResponseError(OllamaError):
    """Raised when an AI reply includes a link or phone number the app cannot verify."""


def requires_official_lookup(question: str, category: str) -> bool:
    return official_lookup_category(question, category) is not None


def official_lookup_category(question: str, category: str) -> str | None:
    if category == "Government schemes":
        return category
    if SCHOLARSHIP_LOOKUP_PATTERN.search(question):
        return "Education"
    if SCHEME_LOOKUP_PATTERN.search(question):
        return "Government schemes"
    return None


def check_ollama_status() -> tuple[str, bool]:
    request = urllib.request.Request(f"{OLLAMA_URL}/api/tags", method="GET")
    try:
        with urllib.request.urlopen(request, timeout=3) as response:
            payload: Any = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, UnicodeDecodeError):
        return "ollama_offline", False

    if not isinstance(payload, dict):
        return "ollama_offline", False
    installed = {
        model.get("name")
        for model in payload.get("models", [])
        if isinstance(model, dict) and isinstance(model.get("name"), str)
    }
    if OLLAMA_MODEL in installed:
        return "ollama_ready", True
    return "ollama_missing", False


def ask_ollama(
    question: str,
    category: str,
    language: str,
    previous_messages: list[dict[str, str]] | None = None,
) -> str:
    language_instruction = "simple English" if language == "English" else "simple Telugu (తెలుగు)"
    system_message = (
        "You are ManaSeva, a kind community information assistant for people in India. "
        f"Reply in {language_instruction}, using short, clear sentences. "
        "Use the selected category to understand the question, but only state facts you are confident about. "
        "Never invent scheme rules, eligibility, contact numbers, addresses, or services. "
        "Do not include URLs, website domains, Markdown links, or phone numbers in your answer. "
        "Point to the official resource cards shown below for changing or local information. "
        "Do not diagnose illness, prescribe treatment, or replace a professional. "
        "For an emergency, tell the user to call 112 in India now and not wait for an AI response. "
        "For scheme or scholarship eligibility, never guess or list schemes; direct the user to an official resource. "
        "Do not ask for names, phone numbers, home addresses, or other sensitive personal information. "
        "If you do not know, say so plainly and suggest how to verify using an official source."
    )
    messages: list[dict[str, str]] = [{"role": "system", "content": system_message}]
    for item in (previous_messages or [])[-8:]:
        if item.get("role") in {"user", "assistant"} and isinstance(item.get("content"), str):
            messages.append({"role": item["role"], "content": item["content"]})
    messages.append({"role": "user", "content": f"Category: {category}\nQuestion: {question}"})

    request = urllib.request.Request(
        f"{OLLAMA_URL}/api/chat",
        data=json.dumps(
            {
                "model": OLLAMA_MODEL,
                "messages": messages,
                "stream": False,
                "options": {"temperature": 0.2, "num_predict": 300},
            }
        ).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            payload: Any = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        try:
            details = error.read().decode("utf-8", errors="replace")[:300]
        finally:
            error.close()
        raise OllamaError(f"Ollama returned HTTP {error.code}: {details}") from error
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, UnicodeDecodeError) as error:
        raise OllamaError(f"Could not get a reply from local Ollama: {error}") from error

    message = payload.get("message") if isinstance(payload, dict) else None
    answer = message.get("content") if isinstance(message, dict) else None
    if not isinstance(answer, str) or not answer.strip():
        raise OllamaError("Ollama returned an empty or invalid answer.")
    answer = answer.strip()
    if MARKDOWN_LINK_PATTERN.search(answer) or UNVERIFIED_LINK_PATTERN.search(answer):
        raise UnsafeAIResponseError(
            "The AI suggested an unverified website. Use the official resource links shown in the app."
        )
    for phone_number in PHONE_NUMBER_PATTERN.findall(answer):
        if len(re.sub(r"\D", "", phone_number)) >= 7:
            raise UnsafeAIResponseError(
                "The AI suggested an unverified phone number. Use the emergency information shown in the app."
            )
    return answer


def offline_demo_answer(category: str, language: str) -> str:
    answers = OFFLINE_ANSWERS.get(language, OFFLINE_ANSWERS["English"])
    return answers.get(category, answers["General help"])


def save_issue_report(
    category: str,
    location: str,
    description: str,
    db_path: Path = REPORTS_DB,
) -> None:
    if category not in REPORT_CATEGORIES:
        raise ValueError("Choose a valid issue category.")
    if not location.strip() or not description.strip():
        raise ValueError("Add a general area and a description.")

    db_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(db_path)) as connection:
        with connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS issue_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    location TEXT NOT NULL,
                    description TEXT NOT NULL,
                    created_at_utc TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                INSERT INTO issue_reports (category, location, description, created_at_utc)
                VALUES (?, ?, ?, ?)
                """,
                (
                    category,
                    location.strip(),
                    description.strip(),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )


def render_resources(text: dict[str, str]) -> None:
    st.subheader(text["resources_title"])
    st.write(text["resources_intro"])
    columns = st.columns(2, gap="medium")
    for index, (name, url, description_key) in enumerate(RESOURCES):
        with columns[index % 2]:
            st.markdown(
                f"""
                <div class="resource-card">
                    <div class="resource-icon">↗</div>
                    <a href="{url}" target="_blank" rel="noopener noreferrer">{name}</a>
                    <p>{text[description_key]}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_app() -> None:
    st.set_page_config(
        page_title="ManaSeva — Community Help AI",
        page_icon="🌱",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(
        """
        <style>
        .stApp { background: #F5F8F6; }
        [data-testid="stSidebar"] { background: #EAF3EE; }
        .hero {
            background: linear-gradient(115deg, #164D43, #247F70);
            border-radius: 22px; color: white; padding: 2rem 2.15rem;
            margin: 0.4rem 0 1.5rem; box-shadow: 0 10px 26px #164d4322;
        }
        .hero h1 { color: white; font-size: clamp(1.8rem, 4vw, 2.65rem); margin: 0 0 0.4rem; }
        .hero p { color: #E3F2EC; font-size: 1.04rem; margin: 0; }
        .resource-card {
            background: white; border: 1px solid #E1EBE5; border-radius: 16px;
            padding: 1rem 1.1rem; margin: 0 0 0.8rem; min-height: 128px;
            box-shadow: 0 3px 12px #173e3210;
        }
        .resource-card a { color: #166355; font-weight: 700; font-size: 1rem; text-decoration: none; }
        .resource-card a:hover { text-decoration: underline; }
        .resource-card p { color: #51645D; font-size: 0.9rem; margin: 0.45rem 0 0; }
        .resource-icon { color: #247F70; font-size: 1.2rem; margin-bottom: 0.35rem; }
        .privacy-note { color: #52665F; font-size: 0.9rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    language = st.selectbox(
        "Choose language / భాషను ఎంచుకోండి",
        ["English", "తెలుగు"],
        key="language_picker",
        help="Choose English or తెలుగు to change the language used on this page.",
    )
    text = TEXT[language]
    category_names = list(CATEGORIES)
    selected_category = st.sidebar.selectbox(
        text["category"],
        category_names,
        format_func=lambda name: name if language == "English" else CATEGORIES[name],
    )
    st.sidebar.caption(f"{text['model_setting']}: `{OLLAMA_MODEL}`")
    st.sidebar.caption("A smaller model needs less memory. No model is downloaded by this app.")

    status_key, model_available = check_ollama_status()
    if status_key == "ollama_ready":
        st.sidebar.success(text[status_key])
    elif status_key == "ollama_missing":
        st.sidebar.warning(text[status_key])
    else:
        st.sidebar.info(text[status_key])

    st.markdown(
        f"""
        <div class="hero">
            <h1>🌱 ManaSeva — Community Help AI</h1>
            <p>{text["subtitle"]}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.write(text["intro"])
    st.warning(f"**{text['warning_title']}** — {text['warning_body']}")

    if not model_available:
        st.info(f"**{text['fallback_title']}** — {text['fallback_body']}")

    chat_column, privacy_column = st.columns([1.75, 1], gap="large")
    with chat_column:
        title_column, clear_column = st.columns([3, 1])
        title_column.subheader(text["chat_title"])
        if clear_column.button(text["clear_chat"], use_container_width=True):
            st.session_state.messages = []
            st.rerun()
        st.caption(text["chat_intro"])
        if "messages" not in st.session_state:
            st.session_state.messages = []
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(f"**{text['you'] if message['role'] == 'user' else text['assistant']}**")
                st.write(message["content"])
                if message["role"] == "assistant":
                    source_label = {
                        "ai": text["ai_source"],
                        "demo": text["demo_source"],
                        "verified": text["verified_source"],
                    }
                    st.caption(source_label[message["source"]])

        question = st.chat_input(text["chat_placeholder"])
        if question:
            st.session_state.messages.append(
                {"role": "user", "content": question, "source": "user"}
            )
            lookup_category = official_lookup_category(question, selected_category)
            if lookup_category is not None:
                answer = offline_demo_answer(lookup_category, language)
                source = "verified"
            else:
                try:
                    answer = ask_ollama(
                        question,
                        selected_category,
                        language,
                        st.session_state.messages[:-1],
                    )
                    source = "ai"
                except UnsafeAIResponseError:
                    st.warning(text["unsafe_answer"])
                    answer = offline_demo_answer(selected_category, language)
                    source = "verified"
                except OllamaError as error:
                    st.warning(f"{text['fallback_body']} ({error})")
                    answer = offline_demo_answer(selected_category, language)
                    source = "demo"
            st.session_state.messages.append(
                {"role": "assistant", "content": answer, "source": source}
            )
            st.rerun()

    with privacy_column:
        st.subheader(text["privacy_title"])
        st.markdown(f'<p class="privacy-note">{text["privacy_body"]}</p>', unsafe_allow_html=True)
        st.subheader(text["report_title"])
        st.caption(text["report_intro"])
        with st.form("community_issue_form", clear_on_submit=True):
            report_category = st.selectbox(
                text["report_category"],
                list(REPORT_CATEGORIES),
                format_func=lambda name: name if language == "English" else REPORT_CATEGORIES[name],
            )
            location = st.text_input(text["location"], help=text["location_hint"])
            description = st.text_area(text["description"], help=text["description_hint"], max_chars=1000)
            submitted = st.form_submit_button(text["submit"], type="primary", use_container_width=True)
            if submitted:
                if not location.strip() or not description.strip():
                    st.error(text["report_validation"])
                else:
                    try:
                        save_issue_report(report_category, location, description)
                    except (OSError, sqlite3.Error, ValueError) as error:
                        st.error(f"{text['report_error']} ({error})")
                    else:
                        st.success(text["report_success"])

    st.divider()
    render_resources(text)
    st.caption("ManaSeva is a student demo. Government websites control their own content and availability.")


if __name__ == "__main__":
    render_app()
