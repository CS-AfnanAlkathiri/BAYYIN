from __future__ import annotations

import json
import os
import re
import html
from html.parser import HTMLParser
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Iterable, List, Optional, Tuple

QURAN_API = os.getenv("BAYYIN_QURAN_API", "https://api.quranpedia.net/v1").rstrip("/")
QURANENC_API = os.getenv("BAYYIN_QURANENC_API", "https://quranenc.com/api/v1").rstrip("/")
QURANENC_TRANSLATION_KEY = os.getenv("BAYYIN_QURANENC_TRANSLATION_KEY", "english_saheeh").strip() or "english_saheeh"
DORAR_API = os.getenv("BAYYIN_DORAR_API", "https://dorar.net/dorar_api.json")
TIMEOUT = float(os.getenv("BAYYIN_SOURCE_API_TIMEOUT", "5"))
ENABLED = os.getenv("BAYYIN_LIVE_SOURCES", "on").strip().lower() not in {"0", "off", "false", "no"}

# Standard surah names are used only to recognize an explicit reference supplied by the user.
SURAH_NAMES = {
1:["الفاتحة","الفاتحه","al fatihah","al fatiha","fatihah","fatiha"],2:["البقرة","البقره","al baqarah","al baqara","baqarah","baqara"],3:["آل عمران","ال عمران","al imran","ali imran"],4:["النساء","an nisa","an-nisa","nisa"],5:["المائدة","المائده","al maidah","al maida","maidah"],6:["الأنعام","الانعام","al anam","al an'am","anam"],7:["الأعراف","الاعراف","al araf","al a'raf","araf"],8:["الأنفال","الانفال","al anfal","anfal"],9:["التوبة","التوبه","at tawbah","at taubah","tawbah","taubah"],10:["يونس","yunus"],11:["هود","hud"],12:["يوسف","yusuf"],13:["الرعد","ar rad","ar ra'd","rad"],14:["إبراهيم","ابراهيم","ibrahim"],15:["الحجر","al hijr","hijr"],16:["النحل","an nahl","nahl"],17:["الإسراء","الاسراء","بني إسرائيل","isra","al isra"],18:["الكهف","al kahf","kahf"],19:["مريم","maryam"],20:["طه","ta ha","taha"],21:["الأنبياء","الانبياء","al anbiya","anbiya"],22:["الحج","al hajj","hajj"],23:["المؤمنون","al muminun","muminun"],24:["النور","an nur","nur"],25:["الفرقان","al furqan","furqan"],26:["الشعراء","ash shuara","shuara"],27:["النمل","an naml","naml"],28:["القصص","al qasas","qasas"],29:["العنكبوت","al ankabut","ankabut"],30:["الروم","ar rum","rum"],31:["لقمان","luqman"],32:["السجدة","as sajdah","sajdah"],33:["الأحزاب","al ahzab","ahzab"],34:["سبأ","saba","sabae"],35:["فاطر","fatir"],36:["يس","ya sin","yasin"],37:["الصافات","as saffat","saffat"],38:["ص","sad"],39:["الزمر","az zumar","zumar"],40:["غافر","ghafir","al ghafir"],41:["فصلت","fussilat"],42:["الشورى","ash shura","shura"],43:["الزخرف","az zukhruf","zukhruf"],44:["الدخان","ad dukhan","dukhan"],45:["الجاثية","al jathiyah","jathiyah"],46:["الأحقاف","al ahqaf","ahqaf"],47:["محمد","muhammad"],48:["الفتح","al fath","fath"],49:["الحجرات","al hujurat","al-hujurat","hujurat"],50:["ق","qaf"],51:["الذاريات","adh dhariyat","dhariyat"],52:["الطور","at tur","tur"],53:["النجم","an najm","najm"],54:["القمر","al qamar","qamar"],55:["الرحمن","ar rahman","rahman"],56:["الواقعة","al waqiah","waqiah"],57:["الحديد","al hadid","hadid"],58:["المجادلة","al mujadilah","mujadilah"],59:["الحشر","al hashr","hashr"],60:["الممتحنة","al mumtahanah","mumtahanah"],61:["الصف","as saff","saff"],62:["الجمعة","al jumuah","jumuah"],63:["المنافقون","al munafiqun","munafiqun"],64:["التغابن","at taghabun","taghabun"],65:["الطلاق","at talaq","talaq"],66:["التحريم","at tahrim","tahrim"],67:["الملك","al mulk","mulk"],68:["القلم","al qalam","qalam"],69:["الحاقة","al haqqah","haqqah"],70:["المعارج","al maarij","maarij"],71:["نوح","nuh"],72:["الجن","al jinn","jinn"],73:["المزمل","al muzzammil","muzzammil"],74:["المدثر","al muddaththir","muddaththir"],75:["القيامة","al qiyamah","qiyamah"],76:["الإنسان","الانسان","al insan","insan"],77:["المرسلات","al mursalat","mursalat"],78:["النبأ","an naba","naba"],79:["النازعات","an naziat","naziat"],80:["عبس","abasa"],81:["التكوير","at takwir","takwir"],82:["الانفطار","al infitar","infitar"],83:["المطففين","al mutaffifin","mutaffifin"],84:["الانشقاق","al inshiqaq","inshiqaq"],85:["البروج","al buruj","buruj"],86:["الطارق","at tariq","tariq"],87:["الأعلى","al ala","ala"],88:["الغاشية","al ghashiyah","ghashiyah"],89:["الفجر","al fajr","fajr"],90:["البلد","al balad","balad"],91:["الشمس","ash shams","shams"],92:["الليل","al layl","layl"],93:["الضحى","ad duha","duha"],94:["الشرح","ash sharh","sharh"],95:["التين","at tin","tin"],96:["العلق","al alaq","alaq"],97:["القدر","al qadr","qadr"],98:["البينة","al bayyinah","bayyinah"],99:["الزلزلة","az zalzalah","zalzalah"],100:["العاديات","al adiyat","adiyat"],101:["القارعة","al qariah","qariah"],102:["التكاثر","at takathur","takathur"],103:["العصر","al asr","asr"],104:["الهمزة","al humazah","humazah"],105:["الفيل","al fil","fil"],106:["قريش","quraysh"],107:["الماعون","al maun","maun"],108:["الكوثر","al kawthar","kawthar"],109:["الكافرون","al kafirun","kafirun"],110:["النصر","an nasr","nasr"],111:["المسد","al masad","masad"],112:["الإخلاص","al ikhlas","ikhlas"],113:["الفلق","al falaq","falaq"],114:["الناس","an nas","nas"],
}


def _get_json(url: str) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": "BAYYIN/3.0 (hackathon source verification)"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
        return json.loads(response.read().decode("utf-8"))


def _unwrap_data(value: Any) -> Any:
    """Tolerate common API wrapper shapes without guessing semantic content."""
    current = value
    for _ in range(4):
        if not isinstance(current, dict):
            break
        for key in ("data", "result", "results"):
            if key in current and current[key] is not None:
                current = current[key]
                break
        else:
            break
    return current


def _as_list(value: Any) -> List[Any]:
    value = _unwrap_data(value)
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, dict):
        # Dorar responses have appeared both as a list and as keyed objects.
        # Preserve only dict/list values; do not slice a dict (the previous crash).
        for key in ("ahadith", "items", "records"):
            nested = value.get(key)
            if isinstance(nested, list):
                return nested
            if isinstance(nested, dict):
                return list(nested.values())
        if all(isinstance(v, dict) for v in value.values()) and value:
            return list(value.values())
    return []


def _find_text(obj: Any, keys: Iterable[str]) -> str:
    if isinstance(obj, dict):
        for key in keys:
            value = obj.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        for value in obj.values():
            found = _find_text(value, keys)
            if found:
                return found
    elif isinstance(obj, list):
        for value in obj:
            found = _find_text(value, keys)
            if found:
                return found
    return ""


class _HTMLTextExtractor(HTMLParser):
    """Extract visible text only; script/style/head content is ignored."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: List[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: Any) -> None:
        if tag.lower() in {"head", "script", "style", "noscript"}:
            self._skip += 1
        elif not self._skip and tag.lower() in {"br", "p", "div", "li", "hr"}:
            self.parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"head", "script", "style", "noscript"} and self._skip:
            self._skip -= 1
        elif not self._skip and tag.lower() in {"p", "div", "li"}:
            self.parts.append(" ")

    def handle_data(self, data: str) -> None:
        if not self._skip and data.strip():
            self.parts.append(data)


def _visible_html_text(fragment: str) -> str:
    """Turn an API HTML fragment into readable text without exposing markup."""
    if not fragment:
        return ""
    parser = _HTMLTextExtractor()
    try:
        parser.feed(html.unescape(fragment))
        parser.close()
        text = " ".join(parser.parts)
    except Exception:
        # Last-resort sanitizer: never return raw markup to the UI.
        text = re.sub(r"<[^>]+>", " ", html.unescape(fragment))
    return re.sub(r"\s+", " ", text).strip()


def _clean_dorar_fragment(fragment: str) -> Tuple[str, Dict[str, str]]:
    """Extract hadith wording and any explicitly returned Dorar metadata.

    Dorar's documented JSON endpoint can place HTML inside ``th``.  BAYYIN
    must never display that HTML as primary source text.  This parser strips
    markup and separates common metadata labels when they are present.
    """
    visible = _visible_html_text(fragment)
    visible = re.sub(r"^\s*\d+\s*[-–—]\s*", "", visible)
    labels = [
        "الراوي", "المحدث", "المصدر", "الصفحة أو الرقم", "خلاصة حكم المحدث",
        "التخريج", "أحاديث مشابهة", "الصحيح البديل",
    ]
    first = len(visible)
    for label in labels:
        m = re.search(re.escape(label) + r"\s*[:：]", visible)
        if m:
            first = min(first, m.start())
    hadith_text = visible[:first].strip(" -–—|؛;")

    meta: Dict[str, str] = {}
    for i, label in enumerate(labels):
        pattern = re.escape(label) + r"\s*[:：]\s*(.*?)"
        following = labels[i + 1:] + labels[:i]
        if following:
            pattern += r"(?=(?:" + "|".join(re.escape(x) for x in following) + r")\s*[:：]|$)"
        m = re.search(pattern, visible)
        if m and m.group(1).strip():
            meta[label] = m.group(1).strip(" |؛;")
    return hadith_text, meta


def extract_quran_reference(text: str) -> Optional[Tuple[int, int]]:
    raw = text or ""
    for m in re.finditer(r"(?<!\d)(\d{1,3})\s*[:/]\s*(\d{1,3})(?!\d)", raw):
        surah, ayah = int(m.group(1)), int(m.group(2))
        if 1 <= surah <= 114 and ayah >= 1:
            return surah, ayah
    lowered = raw.lower()
    for sid, names in SURAH_NAMES.items():
        for name in names:
            match = re.search(r"(?:سورة\s*)?" + re.escape(name) + r"(?:\s+|[-:]|/)(\d{1,3})\b", lowered, flags=re.I)
            if match:
                ayah = int(match.group(1))
                if ayah >= 1:
                    return sid, ayah
    return None


def quranpedia_ayah(surah: int, ayah: int) -> Optional[Dict[str, Any]]:
    if not ENABLED:
        return None
    try:
        verse_raw = _get_json(f"{QURAN_API}/mushafs/1/{surah}/{ayah}")
        verse = _unwrap_data(verse_raw)
        text_ar = _find_text(verse, ("text", "aya_text", "ayah_text", "content"))
        if not text_ar:
            return None

        # The current scientific package explicitly lists QuranEnc and its public API
        # for approved multilingual Qur'an translations. Prefer it for English
        # translation, while retaining Quranpedia's documented translation endpoint
        # as a safe fallback if QuranEnc is temporarily unavailable.
        trans = ""
        translation_source = ""
        try:
            qenc = _get_json(f"{QURANENC_API}/translation/aya/{QURANENC_TRANSLATION_KEY}/{surah}/{ayah}")
            trans = _find_text(qenc, ("translation", "text", "content"))
            if trans:
                translation_source = f"QuranEnc.com — {QURANENC_TRANSLATION_KEY}"
        except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError, KeyError, TypeError):
            pass

        if not trans:
            translations_raw = _get_json(f"{QURAN_API}/translations/{surah}/{ayah}/en")
            translations = _as_list(translations_raw)
            for item in translations:
                if not isinstance(item, dict):
                    continue
                book = item.get("book") or item.get("translation") or {}
                book_id = str(book.get("id", "")) if isinstance(book, dict) else ""
                book_name = str(book.get("name", "")) if isinstance(book, dict) else str(book)
                if book_id == "1947" or "saheeh international" in book_name.lower() or "sahih international" in book_name.lower():
                    trans = _find_text(item, ("translation-content", "translation_content", "text", "content"))
                    break
            if not trans and translations:
                trans = _find_text(translations[0], ("translation-content", "translation_content", "text", "content"))
            if trans:
                translation_source = "Quranpedia.net — Saheeh International (translation book 1947)"

        return {
            "id": f"live-quran-{surah}-{ayah}",
            "source_type": "quran",
            "reference": f"Qur'an {surah}:{ayah}",
            "title_ar": f"القرآن الكريم — {surah}:{ayah}",
            "title_en": f"Qur'an {surah}:{ayah}",
            "text_ar": text_ar,
            "text_en": trans,
            "context_ar": "استرجاع مباشر للنص من واجهة Quranpedia. يعرض بيّن المرجع والمطابقة فقط ولا يستنتج تفسيرًا أو حكمًا شرعيًا من الآية وحدها.",
            "context_en": "Live text retrieval from the Quranpedia API. BAYYIN shows the reference and match only; it does not infer tafsir or a religious ruling from the verse alone.",
            "source_url": f"https://quranpedia.net/en/translations/{surah}",
            "source_platform": "Quranpedia.net API" + (" + QuranEnc.com API" if translation_source.startswith("QuranEnc") else ""),
            "source_authority": "Quranpedia live Qur'an text; approved translation source recorded separately",
            "translation_source": translation_source or "No English translation returned",
            "provenance": "Live Quranpedia API for Qur'an text; QuranEnc preferred for English translation; retrieved at request time",
            "review_status": "source_trace_live; specialist_review_required_for_interpretation",
            "retrieval_layer": "live_api",
            "live_source": True,
            "api_endpoint": f"{QURAN_API}/mushafs/1/{surah}/{ayah}",
            "match_score": 100,
            "match_trace": {"retrieval": "quranpedia_live_reference", "exact_reference": True},
        }
    except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError, KeyError, TypeError):
        return None


def _extract_dorar_items(data: Any) -> List[Dict[str, Any]]:
    """Normalize documented and observed Dorar response shapes into records."""
    root = _unwrap_data(data)
    if isinstance(root, dict) and "ahadith" in root:
        root = root["ahadith"]
    if isinstance(root, dict) and any(k in root for k in ("th", "text", "hadith")):
        return [root]
    if isinstance(root, dict) and root and all(isinstance(v, str) for v in root.values()):
        return [{"th": value} for value in root.values() if value.strip()]
    if isinstance(root, list):
        return [item if isinstance(item, dict) else {"th": item} for item in root if isinstance(item, (dict, str))]
    items = _as_list(root)
    return [item for item in items if isinstance(item, dict)]


def dorar_search(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    if not ENABLED or not query.strip():
        return []
    try:
        url = DORAR_API + "?" + urllib.parse.urlencode({"skey": query})
        data = _get_json(url)
        items = _extract_dorar_items(data)
        results: List[Dict[str, Any]] = []
        for item in items[: max(0, limit)]:
            raw_fragment = _find_text(item, ("th", "text", "hadith"))
            if not raw_fragment:
                continue
            text, meta = _clean_dorar_fragment(raw_fragment)
            # Never surface a malformed HTML/API wrapper as religious text.
            if not text or "<" in text or ">" in text or len(text) < 8:
                continue
            score = 90 if query.strip() in text else 78
            grading = meta.get("خلاصة حكم المحدث", "")
            narrator = meta.get("الراوي", "")
            scholar = meta.get("المحدث", "")
            source_name = meta.get("المصدر", "")
            page_ref = meta.get("الصفحة أو الرقم", "")
            results.append({
                "id": f"live-dorar-{abs(hash(text))}",
                "source_type": "hadith",
                "reference": "Dorar.net — live hadith search result",
                "title_ar": "نتيجة حديثية من الدرر السنية",
                "title_en": "Dorar.net live hadith result",
                "text_ar": text,
                "text_en": "",
                "context_ar": "نتيجة بحث مباشرة من الموسوعة الحديثية في الدرر السنية. يعرض بيّن النص المنظف والبيانات التي أعادها المصدر فقط؛ افتح المصدر لفحص التخريج والسياق الكامل.",
                "context_en": "Live result from Dorar.net's Hadith Encyclopedia. BAYYIN shows only sanitized returned text and metadata; open the source to inspect full takhrij and context.",
                "source_url": url,
                "source_platform": "Dorar.net API",
                "source_authority": "Dorar.net — Hadith Encyclopedia API",
                "provenance": "Live Dorar.net API search; HTML sanitized and metadata separated at request time",
                "review_status": "source_trace_live; source_inspection_required",
                "retrieval_layer": "live_api",
                "live_source": True,
                "api_endpoint": DORAR_API,
                "hadith_grading_ar": grading,
                "narrator_ar": narrator,
                "grader_ar": scholar,
                "collection_ar": source_name,
                "source_reference_ar": page_ref,
                "match_score": score,
                "match_trace": {"retrieval": "dorar_live_api", "grading_displayed": bool(grading), "html_sanitized": True},
            })
        return results
    except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError, KeyError, TypeError):
        return []

