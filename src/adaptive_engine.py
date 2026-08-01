import re
from typing import Dict, Any, List, Tuple, Optional


class AdaptiveEngine:
    """
    Adaptive User Behavior & Preference Learning Engine.
    Analyzes user interaction patterns, learns personal writing styles,
    resolves ambiguous inputs using recent activity history, and extracts preference rules.
    """

    @staticmethod
    def analyze_interaction(
        original_text: str,
        rewritten_text: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyzes original vs rewritten text to discover user preferences & style habits.
        Returns dict with:
        {
            "language_style": "Hinglish" | "English" | "Code",
            "formality": "Casual" | "Formal" | "Concise",
            "preference_rules": List[str]
        }
        """
        rules: List[str] = []
        orig_lower = original_text.lower()

        # 1. Detect Language Habits (e.g. Hinglish / Casual Hindi)
        hinglish_words = ["hai", "hun", "karo", "bolta", "bhi", "toh", "kya", "mera", "utne", "aaj", "kal", "samjh"]
        matched_hinglish = [w for w in hinglish_words if re.search(r'\b' + w + r'\b', orig_lower)]
        
        is_hinglish = len(matched_hinglish) >= 2
        lang_style = "Hinglish" if is_hinglish else "English"

        if is_hinglish:
            rules.append("User frequently uses Hinglish: Preserve natural, casual tone and avoid overly stiff corporate phrasing.")

        # 2. Detect Formality & Length Preferences
        orig_words = len(original_text.split())
        rew_words = len(rewritten_text.split())

        if orig_words <= 5 and rew_words <= 10:
            formality = "Concise"
            rules.append("User prefers ultra-concise, single-sentence responses for short inputs.")
        elif any(kw in orig_lower for kw in ["please", "regards", "kindly", "sincerely", "dear"]):
            formality = "Formal"
            rules.append("User prefers formal business etiquette in email & professional communications.")
        else:
            formality = "Casual"

        return {
            "language_style": lang_style,
            "formality": formality,
            "preference_rules": rules
        }

    @staticmethod
    def resolve_ambiguity(
        text: str,
        recent_timeline: List[str],
        context: Dict[str, Any]
    ) -> Tuple[str, str]:
        """
        Resolves ambiguous short inputs (e.g. "fix", "do this", "explain") using recent activity context.
        Returns (resolved_context_summary, enhanced_text_hint)
        """
        clean_text = text.strip().lower()
        is_ambiguous = len(clean_text.split()) <= 2 and clean_text in ["fix", "do", "explain", "help", "check", "do this", "see this"]

        if not is_ambiguous or not recent_timeline:
            return ("", text)

        # Use recent chronological activity to infer intent
        last_event = recent_timeline[-1] if recent_timeline else ""
        inferred_hint = f"Note: User input is brief '{text}'. Referencing recent activity timeline ({last_event}) to infer context."
        
        return (last_event, inferred_hint)
