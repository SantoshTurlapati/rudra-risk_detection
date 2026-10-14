from typing import Dict, Any, List
from fastapi import APIRouter
from app.schemas.all_schemas import CopilotMessageRequest, CopilotResponse

router = APIRouter(prefix="/copilot", tags=["Safety Copilot"])

TELUGU_RESPONSES = {
    "kyc": "బ్యాంకులు లేదా సర్వీస్ ప్రొవైడర్లు ఎప్పుడూ వాట్సాప్ లేదా SMS ద్వారా KYC అప్‌డేట్ చేయమని లింకులు పంపరు. మీ ఖాతా బ్లాక్ అవుతుందని బెదిరించే మెసేజ్‌లు నకిలీవి. ఎవరితోనూ OTP లేదా పాస్‌వర్డ్ పంచుకోవద్దు. వెంటనే 1930 లేదా cybercrime.gov.in లో ఫిర్యాదు చేయండి.",
    "link": "ఈ లింక్ అనుమానాస్పదంగా కనిపిస్తోంది. అధికారిక వెబ్‌సైట్ డొమైన్ పేరును జాగ్రత్తగా పరిశీలించండి. అక్షర దోషాలు (ఉదా. sbi-verify బదులు onlinesbi.sbi) ఉంటే అది ఫిషింగ్ సైట్ కావచ్చు. లింక్‌పై క్లిక్ చేయవద్దు.",
    "app": "అనధికారిక మూలాల నుండి లేదా వాట్సాప్ లో వచ్చిన APK ఫైళ్లను ఎప్పుడూ ఇన్‌స్టాల్ చేయవద్దు. గూగుల్ ప్లే స్టోర్‌లో డెవలపర్ పేరు మరియు ప్యాకేజీ ఐడీ అసలైనదో కాదో తనిఖీ చేయండి.",
    "default": "నమస్కారం! నేను రుద్ర, మీ సైబర్ భద్రతా మార్గదర్శిని. అనుమానాస్పద లింకులు, ఫేక్ ప్రొఫైల్స్, మోసపూరిత కాల్స్ లేదా యాప్‌ల గురించి అడగండి. ఈ మార్గదర్శకం సాధారణ భద్రతా సూచనలు ఇస్తుంది; మీ సందేశాన్ని లేదా లింక్‌ను స్వయంగా విశ్లేషించదు."
}

@router.post("/chat", response_model=CopilotResponse)
def copilot_chat(req: CopilotMessageRequest):
    msg = req.message.lower()
    lang = req.language.lower()

    if lang == "te":
        if "kyc" in msg or "ఖాతా" in msg or "బ్యాంక్" in msg:
            reply = TELUGU_RESPONSES["kyc"]
        elif "లింక్" in msg or "link" in msg or "url" in msg:
            reply = TELUGU_RESPONSES["link"]
        elif "app" in msg or "యాప్" in msg or "apk" in msg:
            reply = TELUGU_RESPONSES["app"]
        else:
            reply = TELUGU_RESPONSES["default"]

        return CopilotResponse(
            reply=f"ఇది సాధారణ భద్రతా మార్గదర్శకం మాత్రమే; మీ సందేశం లేదా లింక్ విశ్లేషించబడలేదు. {reply}",
            language="te",
            safety_tips=[
                "మీ బ్యాంక్ వివరాలు, OTP లేదా UPI పిన్ ఎవరితోనూ పంచుకోవద్దు.",
                "సైబర్ మోసానికి గురైతే వెంటనే హెల్ప్‌లైన్ 1930 కు కాల్ చేయండి.",
                "అధికారిక వెబ్‌సైట్‌లను మాత్రమే సందర్శించండి."
            ],
            suggested_actions=[
                "అనుమానాస్పద లింక్‌ను స్కాన్ చేయండి",
                "ఫేక్ ప్రొఫైల్‌ను నివేదించండి",
                "సైబర్ హెల్ప్‌లైన్ 1930 సమాచారం"
            ],
            risk_assessment=None
        )

    # English responses
    safety_tips = [
        "Official banks will never threaten instant suspension via SMS or ask for your OTP/PIN.",
        "Verify domain names carefully: look out for added hyphens (e.g. 'sbi-verify.net' vs 'onlinesbi.sbi').",
        "Never install APK files received through WhatsApp or Telegram."
    ]

    suggested_actions = [
        "Analyze a suspicious URL in Investigate tab",
        "Verify candidate social media handle",
        "Report cyber fraud to National Helpline (1930 / cybercrime.gov.in)"
    ]

    if "kyc" in msg or "block" in msg or "pan" in msg:
        reply = (
            "**KYC impersonation scams** often use synthetic urgency "
            "claiming your account or debit card will be frozen within 24 hours. Authentic financial institutions "
            "never solicit KYC submissions via arbitrary web forms or mobile links. "
            "Do not click the link or submit your Aadhaar, PAN, or OTP."
        )
    elif "app" in msg or "apk" in msg or "quickreward" in msg:
        reply = (
            "Installing untrusted APKs outside the official Google Play Store or Apple App Store is a critical risk. "
            "Fraudulent applications often use look-alike brand icons and request high-privilege permissions "
            "(such as reading SMS messages to intercept one-time banking passwords and OTPs). "
            "Always inspect the developer publisher name and package ID."
        )
    elif "link" in msg or "url" in msg or "http" in msg or "website" in msg:
        reply = (
            "Phishing domains often rely on typosquatting, deceptive subdomains, or low-cost TLDs (like .top, .xyz). "
            "For example, an attacker might register `sbi-login.support-portal.top` to trick you into believing "
            "it is an authentic State Bank of India portal. Check for valid SSL certificates, exact domain endings, "
            "and run the link through RudraShield's **Investigate** module."
        )
    elif "profile" in msg or "account" in msg or "twitter" in msg or "instagram" in msg:
        reply = (
            "Fraudulent social profiles frequently insert extra underscores, duplicate letters, or append keywords "
            "like `_official`, `_care`, or `_support` (e.g., `@sbi_care_official`). "
            "Compare the handle against the verified accounts registered in our **Trusted Identity** registry."
        )
    else:
        reply = (
            "Hello! I am **Rudra**, a rule-based cybersecurity safety guide. "
            "I provide general guidance about suspicious links, profiles, apps, and reporting cyber threats. "
            "I do not analyze the submitted message or check live threat data. "
            "How can I help you stay safer online?"
        )

    return CopilotResponse(
        reply=f"This is general safety guidance, not an analysis of your message. {reply}",
        language="en",
        safety_tips=safety_tips,
        suggested_actions=suggested_actions,
        risk_assessment=None
    )
