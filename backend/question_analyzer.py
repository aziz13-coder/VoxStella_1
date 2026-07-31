import builtins
import os
from typing import Dict, Any, List
import re
import logging

try:
    from .taxonomy import Category
    from .horary_engine.aid_doctrine import analyze_aid_question_text
    from .horary_engine.communication_doctrine import analyze_communication_question_text
    from .horary_engine.confinement_doctrine import analyze_confinement_question_text
    from .horary_engine.economic_doctrine import analyze_economic_question_text
    from .horary_engine.event_doctrine import analyze_event_question_text
    from .horary_engine.inheritance_doctrine import analyze_inheritance_question_text
    from .horary_engine.immigration_doctrine import analyze_immigration_question_text
    from .horary_engine.passport_doctrine import analyze_passport_question_text
    from .horary_engine.property_doctrine import analyze_property_question_text
    from .horary_engine.publication_doctrine import analyze_publication_question_text
    from .horary_engine.relationship_doctrine import analyze_relationship_question_text
    from .horary_engine.roommate_doctrine import analyze_roommate_question_text
    from .horary_engine.pregnancy_doctrine import analyze_pregnancy_question_text
    from .horary_engine.children_doctrine import analyze_children_question_text
    from .horary_engine.health_doctrine import analyze_health_question_text
    from .horary_engine.pet_doctrine import analyze_pet_question_text
    from .horary_engine.lost_object_doctrine import analyze_lost_object_question_text
    from .horary_engine.lawsuit_doctrine import analyze_lawsuit_question_text
    from .horary_engine.relative_doctrine import analyze_relative_question_text
    from .horary_engine.surgery_doctrine import analyze_surgery_question_text
    from .horary_engine.theft_doctrine import analyze_theft_question_text
    from .horary_engine.competition_doctrine import analyze_competition_question_text
    from .horary_engine.custody_doctrine import analyze_custody_question_text
    from .horary_engine.state_doctrine import analyze_state_question_text
    from .horary_engine.vehicle_doctrine import analyze_vehicle_question_text
except ImportError:  # pragma: no cover - fallback for script execution
    from taxonomy import Category
    from horary_engine.aid_doctrine import analyze_aid_question_text
    from horary_engine.communication_doctrine import analyze_communication_question_text
    from horary_engine.confinement_doctrine import analyze_confinement_question_text
    from horary_engine.economic_doctrine import analyze_economic_question_text
    from horary_engine.event_doctrine import analyze_event_question_text
    from horary_engine.inheritance_doctrine import analyze_inheritance_question_text
    from horary_engine.immigration_doctrine import analyze_immigration_question_text
    from horary_engine.passport_doctrine import analyze_passport_question_text
    from horary_engine.property_doctrine import analyze_property_question_text
    from horary_engine.publication_doctrine import analyze_publication_question_text
    from horary_engine.relationship_doctrine import analyze_relationship_question_text
    from horary_engine.roommate_doctrine import analyze_roommate_question_text
    from horary_engine.pregnancy_doctrine import analyze_pregnancy_question_text
    from horary_engine.children_doctrine import analyze_children_question_text
    from horary_engine.health_doctrine import analyze_health_question_text
    from horary_engine.pet_doctrine import analyze_pet_question_text
    from horary_engine.lost_object_doctrine import analyze_lost_object_question_text
    from horary_engine.lawsuit_doctrine import analyze_lawsuit_question_text
    from horary_engine.relative_doctrine import analyze_relative_question_text
    from horary_engine.surgery_doctrine import analyze_surgery_question_text
    from horary_engine.theft_doctrine import analyze_theft_question_text
    from horary_engine.competition_doctrine import analyze_competition_question_text
    from horary_engine.custody_doctrine import analyze_custody_question_text
    from horary_engine.state_doctrine import analyze_state_question_text
    from horary_engine.vehicle_doctrine import analyze_vehicle_question_text


_HORARY_DEBUG_STDOUT = str(os.getenv("HORARY_DEBUG_STDOUT", "")).strip().lower() in {"1", "true", "yes"}


def _safe_debug_print(*args, **kwargs):
    if not _HORARY_DEBUG_STDOUT:
        return
    try:
        builtins.print(*args, **kwargs)
    except (OSError, ValueError):
        logging.getLogger(__name__).debug("Suppressed question analyzer debug print failure", exc_info=True)


print = _safe_debug_print  # type: ignore[assignment]

logger = logging.getLogger(__name__)


class TraditionalHoraryQuestionAnalyzer:
    """Analyze questions using traditional horary house assignments"""
    
    def __init__(self):
        # Traditional house meanings for horary
        self.house_meanings = {
            1: ["querent", "self", "body", "life", "personality", "appearance"],
            2: ["money", "possessions", "moveable goods", "income", "resources", "values"],
            3: ["siblings", "neighbors", "short journeys", "communication", "letters", "rumors"],
            4: ["father", "home", "land", "property", "endings", "foundations", "graves"],
            5: ["children", "pregnancy", "pleasure", "gambling", "creativity", "entertainment"],
            6: ["illness", "servants", "small animals", "work", "daily routine", "uncle/aunt"],
            7: ["spouse", "partner", "open enemies", "thieves", "others", "contracts"],
            8: ["death", "partner's money", "wills", "transformation", "fear", "surgery"],
            9: ["long journeys", "foreign lands", "religion", "law", "higher learning", "dreams"],
            10: ["mother", "career", "honor", "reputation", "authority", "government"],
            11: ["friends", "hopes", "wishes", "advisors", "king's money", "groups"],
            12: ["hidden enemies", "large animals", "prisons", "secrets", "self-undoing", "witchcraft"]
        }
        
        # ENHANCED: Comprehensive traditional horary question patterns
        self.question_patterns = {
            Category.LOST_OBJECT: ["where is", "lost", "missing", "find", "stolen", "disappeared", "locate"],
            Category.PET: ["cat", "dog", "pet", "kitten", "puppy", "bird", "rabbit", "hamster", "guinea pig", "ferret", "parrot", "fish", "turtle", "lizard", "snake", "mouse", "rat", "chinchilla", "hedgehog", "budgie", "canary", "cockatiel", "parakeet", "goldfish", "animal"],
            Category.MARRIAGE: ["marry", "wedding", "spouse", "husband", "wife", "engagement", "propose"],
            Category.PREGNANCY: ["pregnant", "conceive", "conception", "expecting", "baby", "fertility"],
            Category.CHILDREN: ["child", "children", "son", "daughter", "offspring", "kids"],
            Category.TRAVEL: [
                "journey", "travel", "trip", "go to", "visit", "vacation", "move to",
                "train", "bus", "metro", "subway", "tram", "commute", "flight", "plane",
            ],
            Category.GAMBLING: ["lottery", "lotto", "win lottery", "jackpot", "scratch", "raffle", "betting", "bet", "gamble", "gambling", "casino", "poker", "blackjack", "slots", "dice", "win money", "lucky", "speculation"],
            Category.FUNDING: ["funding", "fund", "investment", "invest", "investor", "funding round", "seed", "series a", "series b", "venture capital", "vc", "angel", "capital", "raise money", "raise capital", "secure funding", "startup funding", "business loan", "loan", "loan application", "finance", "financial backing", "sponsor", "grant", "equity", "valuation"],
            Category.MONEY: ["money", "wealth", "rich", "profit", "gain", "debt", "financial", "income", "salary", "pay", "trading", "stock", "loan", "loan application"],
            Category.CAREER: ["job", "career", "work", "employment", "business", "promotion", "interview"],
            Category.HEALTH: ["sick", "illness", "disease", "health", "recover", "die", "cure", "healing", "medical"],
            Category.LAWSUIT: ["court", "lawsuit", "legal", "judge", "trial", "litigation", "case"],
            Category.RELATIONSHIP: ["love", "relationship", "friend", "enemy", "romance", "dating", "go out", "go out with", "date", "ask out", "see each other", "like me", "interested in", "attracted to", "reconciliation", "reconcile", "get back together", "ex", "former", "past relationship", "breakup", "break up", "makeup", "make up", "together", "couple", "partner", "boyfriend", "girlfriend", "romantic", "crush", "feelings", "attraction", "divorce", "separation", "separate"],
            # NEW: Education and learning patterns
            Category.EDUCATION: [
                "exam", "test", "study", "student", "school", "college", "university", "learn", "pass", "graduate", "degree", "education", "academic", "course", "class", "conference", "paper", "publication", "publish", "journal", "research", "submit", "accepted", "peer review", "review", "presentation", "symposium", "seminar", "physiotherapy", "nursing", "medical", "certification", "admission", "admit", "admitted", "enroll", "enrolled", "enrollment", "program", "master", "masters"
            ],
            # NEW: Specific person relationship patterns
            Category.PARENT: ["father", "mother", "dad", "mom", "parent", "stepfather", "stepmother"],
            Category.SIBLING: ["brother", "sister", "sibling"],
            Category.FRIEND_ENEMY: ["friend", "enemy", "ally", "rival", "competitor"],
            # NEW: Property and housing
            Category.PROPERTY: ["house", "home", "property", "real estate", "land", "apartment", "buy house", "sell house"],
            # NEW: Death and inheritance
            Category.DEATH: ["death", "die", "inheritance", "testament", "legacy", "last will", "will and testament"],
            # NEW: Spiritual and religious
            Category.SPIRITUAL: ["god", "religion", "spiritual", "prayer", "divine", "faith", "church"],
        }
        
        # Person keywords mapped to their traditional houses
        self.person_keywords = {
            4: ["father", "dad", "grandfather", "stepfather"],
            10: ["mother", "mom", "mum", "stepmother"],
            7: ["spouse", "husband", "wife", "partner"],
            3: ["brother", "sister", "sibling"],
            5: ["child", "son", "daughter", "baby"],
            11: ["friend", "ally", "benefactor"]
        }
    
    def _turn(self, base: int, offset: int) -> int:
        """Return the house offset steps from base (1-based)."""
        return ((base + offset - 1) % 12) + 1
    
    # NOTE: Duplicate methods removed - using enhanced versions below
    
    def _parse_question_timeframe(
        self,
        question: str,
        reference_datetime: Any = None,
    ) -> Dict[str, Any]:
        """Parse timeframe constraints relative to the chart's local datetime."""
        import re
        from datetime import datetime, timedelta
        import calendar
        
        timeframe_patterns = {
            "this_month": [r"this month", r"by the end of this month", r"within this month"],
            "next_month": [r"next month", r"by next month"],
            "this_year": [r"this year", r"by the end of this year", r"within this year"], 
            "this_week": [r"this week", r"by the end of this week", r"within this week"],
            "today": [r"today", r"by today", r"by the end of today"],
            "soon": [r"soon", r"quickly", r"fast"],
            "by_date": [r"by (\w+ \d+)", r"before (\w+ \d+)"],
            "specific_month": [
                r"in (january|february|march|april|may|june|july|august|september|october|november|december)"
            ],
            # NEW: Numeric timeframes
            "within_days": [r"within (\d+) days?", r"in (\d+) days?"],
            "within_weeks": [r"within (\d+) weeks?", r"in (\d+) weeks?"],
            "within_months": [r"within (\d+) months?", r"in (\d+) months?"],
            "by_numeric_date": [r"by (\d{4}-\d{2}-\d{2})", r"before (\d{4}-\d{2}-\d{2})"],
        }
        
        detected_timeframes = []
        numeric_extracts = {}  # Store captured numeric values
        
        for timeframe_type, patterns in timeframe_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, question, re.IGNORECASE)
                if match:
                    detected_timeframes.append(timeframe_type)
                    # Extract numeric values for numeric patterns
                    if match.groups():
                        numeric_extracts[timeframe_type] = match.groups()
                    break
        
        if not detected_timeframes:
            return {"has_timeframe": False, "type": None, "end_date": None, "window_days": None}
        
        # Calculate end date and window_days for timeframes
        now = reference_datetime or datetime.now()
        # Calendar phrases such as "this month" refer to local wall time.  Drop
        # timezone metadata before combining the reference with naive calendar
        # boundaries below.
        if getattr(now, "tzinfo", None) is not None:
            now = now.replace(tzinfo=None)
        end_date = None
        window_days = None
        
        # Handle numeric timeframes first (higher priority)
        if "within_days" in detected_timeframes and "within_days" in numeric_extracts:
            days = int(numeric_extracts["within_days"][0])
            window_days = days
            end_date = now + timedelta(days=days)
        elif "within_weeks" in detected_timeframes and "within_weeks" in numeric_extracts:
            weeks = int(numeric_extracts["within_weeks"][0])
            window_days = weeks * 7
            end_date = now + timedelta(weeks=weeks)
        elif "within_months" in detected_timeframes and "within_months" in numeric_extracts:
            months = int(numeric_extracts["within_months"][0])
            window_days = months * 30  # Approximate
            end_date = now + timedelta(days=window_days)
        elif "by_numeric_date" in detected_timeframes and "by_numeric_date" in numeric_extracts:
            date_str = numeric_extracts["by_numeric_date"][0]
            try:
                end_date = datetime.strptime(date_str, "%Y-%m-%d")
                window_days = (end_date - now).days
            except ValueError:
                pass
        elif "this_month" in detected_timeframes:
            # End of current month
            if now.month == 12:
                next_month = datetime(now.year + 1, 1, 1)
            else:
                next_month = datetime(now.year, now.month + 1, 1)
            end_date = next_month - timedelta(microseconds=1)
            window_days = max(1, (next_month - now).days + 1)
        elif "this_week" in detected_timeframes:
            # End of current week (Sunday)
            days_until_sunday = (6 - now.weekday()) % 7
            end_date = now + timedelta(days=days_until_sunday)
            window_days = days_until_sunday
        elif "today" in detected_timeframes:
            end_date = now.replace(hour=23, minute=59, second=59)
            window_days = 1
        elif "specific_month" in detected_timeframes:
            # End of referenced month in current year
            match = re.search(
                timeframe_patterns["specific_month"][0], question, re.IGNORECASE
            )
            if match:
                month_str = match.group(1).lower()
                month_numbers = {
                    "january": 1,
                    "february": 2,
                    "march": 3,
                    "april": 4,
                    "may": 5,
                    "june": 6,
                    "july": 7,
                    "august": 8,
                    "september": 9,
                    "october": 10,
                    "november": 11,
                    "december": 12,
                }
                month_num = month_numbers[month_str]
                last_day = calendar.monthrange(now.year, month_num)[1]
                end_date = datetime(now.year, month_num, last_day)
                window_days = (end_date - now).days

        # Fallback window_days if not calculated
        if window_days is None and end_date:
            window_days = (end_date - now).days

        return {
            "has_timeframe": True,
            "type": detected_timeframes[0],  # Use first match
            "end_date": end_date,
            "window_days": window_days,
            "patterns_matched": detected_timeframes
        }
    
    def analyze_question(
        self,
        question: str,
        reference_datetime: Any = None,
    ) -> Dict[str, Any]:
        """Analyze question to determine significators using traditional methods"""

        question_lower = question.lower()

        # Detect post-event phrasing (e.g., "just took", "already did")
        post_event = bool(
            re.search(r"(just|already)\s+(took|did|submitted|happened)", question_lower)
        )

        # ENHANCEMENT: Detect 3rd person questions requiring house turning
        third_person_analysis = self._detect_third_person_question(question_lower)
        
        # ENHANCEMENT: Parse timeframe from question
        timeframe_analysis = self._parse_question_timeframe(
            question_lower,
            reference_datetime=reference_datetime,
        )
        
        # Determine question type and intent
        question_type, matched_pattern = self._determine_question_type(question_lower)
        question_intent = self._determine_question_intent(question, question_type)
        custody_analysis = analyze_custody_question_text(question, third_person_analysis)
        if custody_analysis and custody_analysis.get("category_override"):
            question_type = custody_analysis["category_override"]
        confinement_analysis = analyze_confinement_question_text(question, third_person_analysis)
        if confinement_analysis and confinement_analysis.get("category_override"):
            question_type = confinement_analysis["category_override"]
        relative_analysis = analyze_relative_question_text(question, third_person_analysis)
        roommate_analysis = analyze_roommate_question_text(question, third_person_analysis)
        theft_analysis = analyze_theft_question_text(question, third_person_analysis)
        lawsuit_analysis = analyze_lawsuit_question_text(question, third_person_analysis)
        if (
            not custody_analysis
            and not confinement_analysis
            and not relative_analysis
            and not theft_analysis
            and lawsuit_analysis
            and lawsuit_analysis.get("category_override")
        ):
            question_type = lawsuit_analysis["category_override"]
        inheritance_analysis = analyze_inheritance_question_text(question, third_person_analysis)
        if (
            not custody_analysis
            and not confinement_analysis
            and not lawsuit_analysis
            and inheritance_analysis
            and inheritance_analysis.get("category_override")
        ):
            question_type = inheritance_analysis["category_override"]
        if theft_analysis and theft_analysis.get("category_override"):
            question_type = theft_analysis["category_override"]
        publication_analysis = analyze_publication_question_text(question)
        if publication_analysis and publication_analysis.get("category_override"):
            question_type = publication_analysis["category_override"]
        vehicle_analysis = None if publication_analysis else analyze_vehicle_question_text(question, third_person_analysis)
        if vehicle_analysis and vehicle_analysis.get("category_override"):
            question_type = vehicle_analysis["category_override"]
        aid_analysis = None if publication_analysis else analyze_aid_question_text(question, third_person_analysis)
        if aid_analysis and aid_analysis.get("category_override"):
            question_type = aid_analysis["category_override"]
        economic_analysis = None if (publication_analysis or aid_analysis or vehicle_analysis) else analyze_economic_question_text(question_lower, question_type)
        if (
            not custody_analysis
            and not confinement_analysis
            and not inheritance_analysis
            and not relative_analysis
            and not vehicle_analysis
            and not aid_analysis
            and
            not theft_analysis
            and
            not lawsuit_analysis
            and question_type != Category.PROPERTY
            and economic_analysis
            and economic_analysis.get("category_override")
        ):
            question_type = economic_analysis["category_override"]
        if (
            not custody_analysis
            and not confinement_analysis
            and not inheritance_analysis
            and not vehicle_analysis
            and not roommate_analysis
            and relative_analysis
            and relative_analysis.get("category_override")
        ):
            question_type = relative_analysis["category_override"]
        if roommate_analysis and roommate_analysis.get("category_override"):
            question_type = roommate_analysis["category_override"]

        property_analysis = None
        relationship_analysis = None
        pregnancy_analysis = None
        children_analysis = None
        health_analysis = None
        surgery_analysis = analyze_surgery_question_text(question, third_person_analysis)
        pet_analysis = None
        lost_object_analysis = None
        competition_analysis = analyze_competition_question_text(question_lower)
        if competition_analysis and competition_analysis.get("category_override"):
            question_type = competition_analysis["category_override"]
        state_analysis = analyze_state_question_text(question)
        if state_analysis and state_analysis.get("category_override"):
            question_type = state_analysis["category_override"]
        immigration_analysis = analyze_immigration_question_text(question, third_person_analysis)
        if immigration_analysis and immigration_analysis.get("category_override"):
            question_type = immigration_analysis["category_override"]
        passport_analysis = analyze_passport_question_text(question, third_person_analysis)
        if passport_analysis and passport_analysis.get("category_override"):
            question_type = passport_analysis["category_override"]
        if surgery_analysis and surgery_analysis.get("category_override"):
            question_type = surgery_analysis["category_override"]
        if publication_analysis and publication_analysis.get("category_override"):
            question_type = publication_analysis["category_override"]
        event_analysis = analyze_event_question_text(question)
        if event_analysis and event_analysis.get("category_override"):
            question_type = event_analysis["category_override"]
        communication_analysis = analyze_communication_question_text(question, third_person_analysis)
        if (
            not economic_analysis
            and not publication_analysis
            and not vehicle_analysis
            and not aid_analysis
            and not immigration_analysis
            and not passport_analysis
            and communication_analysis
            and communication_analysis.get("category_override")
        ):
            question_type = communication_analysis["category_override"]
        if economic_analysis or publication_analysis or aid_analysis or vehicle_analysis or immigration_analysis or passport_analysis:
            communication_analysis = None
        if (
            question_type == Category.PROPERTY
            and not (
                inheritance_analysis
                and inheritance_analysis.get("family") == "estate_property_inheritance"
            )
        ):
            property_analysis = analyze_property_question_text(question_lower, question_intent)
        elif question_type == Category.RELATIONSHIP:
            relationship_analysis = analyze_relationship_question_text(question_lower)
        elif question_type == Category.PREGNANCY:
            pregnancy_analysis = analyze_pregnancy_question_text(question_lower)
        elif question_type == Category.CHILDREN:
            children_analysis = analyze_children_question_text(question_lower)
        elif question_type == Category.HEALTH:
            if surgery_analysis and surgery_analysis.get("family") == "medical_procedure":
                health_analysis = surgery_analysis
            else:
                health_analysis = analyze_health_question_text(
                    question_lower, question_type, third_person_analysis
                )
        elif question_type == Category.PET:
            pet_analysis = analyze_pet_question_text(question_lower)
        elif question_type == Category.LOST_OBJECT:
            lost_object_analysis = analyze_lost_object_question_text(question_lower)

        # Determine primary houses involved (with house turning if needed)
        houses, possession_analysis = self._determine_houses(
            question_lower,
            question_type,
            third_person_analysis,
            vehicle_analysis=vehicle_analysis,
            aid_analysis=aid_analysis,
            economic_analysis=economic_analysis,
            custody_analysis=custody_analysis,
            confinement_analysis=confinement_analysis,
            inheritance_analysis=inheritance_analysis,
            property_analysis=property_analysis,
            publication_analysis=publication_analysis,
            relative_analysis=relative_analysis,
            roommate_analysis=roommate_analysis,
            theft_analysis=theft_analysis,
            lawsuit_analysis=lawsuit_analysis,
            health_analysis=health_analysis,
            surgery_analysis=surgery_analysis,
            pet_analysis=pet_analysis,
            lost_object_analysis=lost_object_analysis,
            competition_analysis=competition_analysis,
            state_analysis=state_analysis,
            immigration_analysis=immigration_analysis,
            passport_analysis=passport_analysis,
            event_analysis=event_analysis,
            communication_analysis=communication_analysis,
        )

        # Determine significators
        significators = self._determine_significators(
            houses,
            question_type,
            possession_analysis,
            third_person_analysis,
            vehicle_analysis=vehicle_analysis,
            aid_analysis=aid_analysis,
            economic_analysis=economic_analysis,
            custody_analysis=custody_analysis,
            confinement_analysis=confinement_analysis,
            inheritance_analysis=inheritance_analysis,
            property_analysis=property_analysis,
            publication_analysis=publication_analysis,
            relative_analysis=relative_analysis,
            roommate_analysis=roommate_analysis,
            theft_analysis=theft_analysis,
            lawsuit_analysis=lawsuit_analysis,
            health_analysis=health_analysis,
            surgery_analysis=surgery_analysis,
            pet_analysis=pet_analysis,
            lost_object_analysis=lost_object_analysis,
            competition_analysis=competition_analysis,
            state_analysis=state_analysis,
            immigration_analysis=immigration_analysis,
            passport_analysis=passport_analysis,
            event_analysis=event_analysis,
            communication_analysis=communication_analysis,
        )

        # DEBUG: Emit classification traceability information
        logger.debug(
            "category=%s, matched=%s, houses=%s",
            question_type.value,
            matched_pattern,
            houses,
        )

        return {
            "question_type": question_type,
            "question_intent": question_intent,
            "relevant_houses": houses,
            "significators": significators,
            "vehicle_analysis": vehicle_analysis,
            "aid_analysis": aid_analysis,
            "economic_analysis": economic_analysis,
            "custody_analysis": custody_analysis,
            "confinement_analysis": confinement_analysis,
            "inheritance_analysis": inheritance_analysis,
            "property_analysis": property_analysis,
            "publication_analysis": publication_analysis,
            "relative_analysis": relative_analysis,
            "roommate_analysis": roommate_analysis,
            "theft_analysis": theft_analysis,
            "lawsuit_analysis": lawsuit_analysis,
            "relationship_analysis": relationship_analysis,
            "pregnancy_analysis": pregnancy_analysis,
            "children_analysis": children_analysis,
            "health_analysis": health_analysis,
            "surgery_analysis": surgery_analysis,
            "pet_analysis": pet_analysis,
            "lost_object_analysis": lost_object_analysis,
            "competition_analysis": competition_analysis,
            "state_analysis": state_analysis,
            "immigration_analysis": immigration_analysis,
            "passport_analysis": passport_analysis,
            "event_analysis": event_analysis,
            "communication_analysis": communication_analysis,
            "third_person_analysis": third_person_analysis,
            "timeframe_analysis": timeframe_analysis,
            "traditional_analysis": True,
            "post_event": post_event,
        }
    
    def _apply_house_derivation(self, base_house: int, derived_house: int) -> int:
        """Apply traditional house derivation rules (house from house)"""
        # Convert to 0-based indexing, apply derivation, convert back
        result = ((base_house - 1 + derived_house - 1) % 12) + 1
        return result
    
    def _detect_third_person_question(self, question: str) -> Dict[str, Any]:
        """Detect if question is about someone else requiring house turning"""
        
        import re
        question_lower = question.lower()
        self_reproductive_question = self._is_self_reproductive_question(question_lower)
        inferred_subject_house = self._infer_subject_house(question)

        # Strong 3rd person indicators
        third_person_patterns = [
            # Direct pronouns
            r"\bwill he\b", r"\bwill she\b", r"\bwill they\b",
            r"\bdid he\b", r"\bdid she\b",
            r"\bhas he\b", r"\bhas she\b",
            r"\bdoes he\b", r"\bdoes she\b",
            r"\bcan he\b", r"\bcan she\b",
            r"\bshould he\b", r"\bshould she\b",
            r"\bis he\b", r"\bis she\b", r"\bis they\b",
            # Possessives
            r"\bhis\b", r"\bher\b", r"\btheir\b",
            # Specific relationships
            r"the student", r"my student", r"the teacher", r"my friend", r"my partner", r"my husband",
            r"my wife", r"my child", r"my son", r"my daughter", r"the patient", r"my client",
            # Question about someone else
            r"asked by his", r"asked by her", r"asked by the",
        ]

        # Context clues that suggest 3rd person
        for pattern in third_person_patterns:
            if re.search(pattern, question):
                if self_reproductive_question and pattern in {r"my child", r"my son", r"my daughter"}:
                    continue
                # In an adoption decision, "they" denotes the current
                # caretakers while "the baby" is the grammatical object. Do
                # not let the later child noun steal the subject role. Keep
                # inferred named relatives for multi-sentence questions such
                # as "Where is my Dad? Is he ok?".
                generic_adoption_subject = (
                    pattern == r"\bwill they\b"
                    and bool(re.search(r"\b(adopt|adoption)\b", question))
                )
                pronoun_subject_house = (
                    7 if generic_adoption_subject else inferred_subject_house
                )
                return {
                    "is_third_person": True,
                    "subject_house": pronoun_subject_house or 7,  # The other person = 7th house by default
                    "turn_houses": True,
                    "pattern_matched": pattern.strip(),
                }
        
        # Educational context: teacher asking about student
        if any(x in question for x in ["asked by his teacher", "asked by her teacher", "asked by the teacher"]):
            return {
                "is_third_person": True,
                "subject_house": 7,  # Student = 7th house from teacher's perspective
                "turn_houses": True,
                "pattern_matched": "teacher asking about student",
                "educational_context": True
            }

        if inferred_subject_house:
            if self_reproductive_question and inferred_subject_house == 5:
                return {"is_third_person": False}
            return {
                "is_third_person": True,
                "subject_house": inferred_subject_house,
                "turn_houses": True,
                "pattern_matched": "subject-title inference",
            }
        
        return {"is_third_person": False}

    def _has_phrase_match(self, text: str, phrase: str) -> bool:
        pattern = r"\b" + re.escape(phrase).replace(r"\ ", r"\s+") + r"\b"
        return bool(re.search(pattern, text, re.IGNORECASE))

    def _infer_subject_house(self, question: str) -> int | None:
        """Infer the operative subject house for explicit third-party questions."""

        prioritized_subject_phrases = [
            (4, ["my father", "my dad", "my grandfather", "my stepfather"]),
            (10, ["my mother", "my mom", "my mum", "my stepmother"]),
            (3, ["my brother", "my sister", "my sibling"]),
            (5, ["my child", "my son", "my daughter", "my baby"]),
            (11, ["my friend", "my ally"]),
            (7, ["my spouse", "my husband", "my wife", "my partner"]),
        ]
        for house, phrases in prioritized_subject_phrases:
            if any(self._has_phrase_match(question, phrase) for phrase in phrases):
                return house

        subject_house_map = {
            4: ["father", "dad", "grandfather", "stepfather"],
            10: [
                "mother",
                "mom",
                "mum",
                "stepmother",
                "king",
                "queen",
                "president",
                "prime minister",
                "judge",
                "governor",
                "mayor",
                "magistrate",
                "boss",
                "employer",
            ],
            7: ["spouse", "husband", "wife", "partner", "boyfriend", "girlfriend", "date", "lover"],
            3: ["brother", "sister", "sibling"],
            5: ["child", "son", "daughter", "baby"],
            11: ["friend", "ally"],
            9: ["pope", "bishop", "cardinal", "priest", "minister", "clergy", "archbishop", "rabbi", "imam", "pastor", "churchman", "monk"],
        }

        for house, keywords in subject_house_map.items():
            if any(self._has_phrase_match(question, keyword) for keyword in keywords):
                return house
        return None

    def _is_self_reproductive_question(self, question: str) -> bool:
        """Identify first-person fertility/childbearing questions that should stay on L1/L5."""

        first_person = any(phrase in question for phrase in ["i ", "i'", "my ", "me "])
        if not first_person:
            return False

        fertility_phrases = [
            "my own child",
            "own child",
            "biological child",
            "have a child",
            "having a child",
            "have my own child",
            "having my own child",
            "have children",
            "having children",
            "conceive",
            "pregnant",
            "fertility",
            "baby of my own",
        ]
        return any(phrase in question for phrase in fertility_phrases)

    def _get_derived_house_for_possessions(self, person_house: int) -> int:
        """Get 2nd house from person's house (their possessions/money)"""
        return self._apply_house_derivation(person_house, 2)
    
    def _analyze_possession_questions(self, question_lower: str) -> Dict:
        """Enhanced logic for possession/property questions with proper house derivation"""
        real_estate_words = ["house", "home", "property", "flat", "apartment", "land", "building", "real estate"]

        # CRITICAL FIX: Distinguish between SALE TRANSACTIONS and POSSESSION questions
        
        # SALE/TRANSACTION questions (will X sell Y?) use natural significators
        sale_indicators = ["sell", "buy", "sale", "purchase", "trade"]
        if any(word in question_lower for word in sale_indicators):
            if any(word in question_lower for word in real_estate_words):
                return None
            # Detect valuable items using traditional natural significators
            natural_significator = self._detect_natural_significator(question_lower)

            if natural_significator:
                return {
                    "type": Category.MONEY,
                    "houses": [1, 7],
                    "natural_significators": natural_significator,
                    "transaction_context": True,
                }
            else:
                # General sale: seller + buyer
                return {"type": Category.MONEY, "houses": [1, 7]}
        
        # POSSESSION questions (does X own Y?) use house derivation
        # BUT: Skip possession analysis for transaction/investment questions
        transaction_words = ["invest", "buy", "sell", "purchase", "trade", "profit", "gain", "should i"]
        is_transaction = any(word in question_lower for word in transaction_words)
        
        possession_indicators = ["money", "possessions", "belongings", "assets"]
        if any(word in question_lower for word in possession_indicators) and not is_transaction:
            # Determine whose possessions - check for other people first, then default to querent
            if re.search(r"\b(his|her|husband|wife|spouse)\b", question_lower):
                # Partner's possessions = 8th house (2nd from 7th)
                return {"type": Category.MONEY, "houses": [1, 7, 8]}  # Querent + partner + partner's possessions
            elif re.search(r"\b(father|dad)\b", question_lower):
                # Father's possessions = 5th house (2nd from 4th)
                return {"type": Category.MONEY, "houses": [1, 4, 5]}
            elif re.search(r"\b(mother|mom)\b", question_lower):
                # Mother's possessions = 11th house (2nd from 10th)
                return {"type": Category.MONEY, "houses": [1, 10, 11]}
            elif re.search(r"\b(my|i|will i)\b", question_lower):
                return {"type": Category.MONEY, "houses": [1, 2]}  # Querent's possessions
            else:
                # Default: assume querent's possessions if no person specified
                return {"type": Category.MONEY, "houses": [1, 2]}
        
        return None
    
    def _detect_natural_significator(self, question_lower: str) -> Dict:
        """Detect natural significators based on traditional horary assignments"""
        
        # Traditional Natural Significators (from Lilly, Bonatti, etc.)
        natural_significators = {
            # Vehicles & Transportation
            "vehicles": {
                "keywords": ["car", "vehicle", "automobile", "truck", "motorcycle", "bike"],
                "significator": "sun",  # Sun = valuable possessions, status symbols
                "category": Category.VEHICLE,
            },

            # Real Estate
            "real_estate": {
                "keywords": ["house", "home", "property", "building", "land", "estate"],
                "significator": "moon",  # Moon = home, real estate (4th house connection)
                "category": Category.PROPERTY,
            },

            # Precious Items
            "precious_items": {
                "keywords": ["jewelry", "gold", "silver", "diamond", "ring", "watch", "precious"],
                "significator": "venus",  # Venus = luxury items, beauty, value
                "category": Category.PRECIOUS,
            },

            # Technology
            "technology": {
                "keywords": ["computer", "phone", "laptop", "electronics", "device", "gadget"],
                "significator": "mercury",  # Mercury = communication, technology
                "category": Category.TECHNOLOGY,
            },

            # Livestock & Animals
            "livestock": {
                "keywords": ["horse", "cattle", "cow", "livestock", "animal"],
                "significator": "mars",  # Mars = large animals (traditional)
                "category": Category.LIVESTOCK,
            },

            # Boats & Ships
            "maritime": {
                "keywords": ["boat", "ship", "yacht", "vessel"],
                "significator": "moon",  # Moon = water-related items
                "category": Category.MARITIME,
            },
        }
        
        # Detect which category matches
        for category, info in natural_significators.items():
            if any(keyword in question_lower for keyword in info["keywords"]):
                item_name = next(keyword for keyword in info["keywords"] if keyword in question_lower)
                return {
                    item_name: info["significator"],
                    "category": info["category"],
                    "traditional_source": "Based on classical horary significator assignments"
                }
        
        return None
    
    def _determine_question_type(self, question: str) -> tuple[Category, List[str]]:
        """Enhanced question type determination with transaction and possession priority"""

        third_person_analysis = self._detect_third_person_question(question)
        surgery_analysis = analyze_surgery_question_text(question, third_person_analysis)
        if surgery_analysis and surgery_analysis.get("category_override"):
            return surgery_analysis["category_override"], [surgery_analysis["family"]]
        publication_analysis = analyze_publication_question_text(question)
        if publication_analysis and publication_analysis.get("category_override"):
            return publication_analysis["category_override"], [publication_analysis["family"]]
        confinement_analysis = analyze_confinement_question_text(question, third_person_analysis)
        if confinement_analysis and confinement_analysis.get("category_override"):
            return confinement_analysis["category_override"], [confinement_analysis["family"]]
        vehicle_analysis = analyze_vehicle_question_text(question, third_person_analysis)
        if vehicle_analysis and vehicle_analysis.get("category_override"):
            return vehicle_analysis["category_override"], [vehicle_analysis["family"]]

        relative_analysis = analyze_relative_question_text(
            question, third_person_analysis
        )
        if relative_analysis and relative_analysis.get("category_override"):
            return relative_analysis["category_override"], [relative_analysis["family"]]

        theft_analysis = analyze_theft_question_text(
            question, third_person_analysis
        )
        if theft_analysis and theft_analysis.get("category_override"):
            return theft_analysis["category_override"], [theft_analysis["family"]]

        lawsuit_analysis = analyze_lawsuit_question_text(
            question, third_person_analysis
        )
        if lawsuit_analysis and lawsuit_analysis.get("category_override"):
            return lawsuit_analysis["category_override"], [lawsuit_analysis["family"]]

        inheritance_analysis = analyze_inheritance_question_text(
            question, third_person_analysis
        )
        if inheritance_analysis and inheritance_analysis.get("category_override"):
            return inheritance_analysis["category_override"], [inheritance_analysis["family"]]

        explicit_death_patterns = [
            (r"\b(will|would|is|are|can|could|might|may|did|has|have)\b.*\b(die|dead|death|pass away|decease)\b", "explicit death event"),
            (r"\b(die|dead|death|pass away|decease)\b", "death language"),
            (r"\b(inheritance|testament|legacy|will and testament)\b", "death estate"),
        ]

        import re
        for pattern, description in explicit_death_patterns:
            if re.search(pattern, question, re.IGNORECASE):
                return Category.DEATH, [description]

        adoption_patterns = [
            (r"\b(adoption|adopt)\b", "adoption"),
            (r"\bput\b.*\bbaby\b.*\bup for adoption\b", "adoption decision"),
        ]
        for pattern, description in adoption_patterns:
            if re.search(pattern, question, re.IGNORECASE):
                return Category.CHILDREN, [description]

        competition_analysis = analyze_competition_question_text(question)
        if competition_analysis and competition_analysis.get("category_override"):
            return competition_analysis["category_override"], [competition_analysis["family"]]

        roommate_analysis = analyze_roommate_question_text(
            question, self._detect_third_person_question(question)
        )
        if roommate_analysis and roommate_analysis.get("category_override"):
            return roommate_analysis["category_override"], [roommate_analysis["family"]]

        def _has_phrase(text: str, phrase: str) -> bool:
            pattern = r"\b" + re.escape(phrase).replace(r"\ ", r"\s+") + r"\b"
            return bool(re.search(pattern, text, re.IGNORECASE))

        pet_keywords = self.question_patterns.get(Category.PET, [])
        has_pet = any(_has_phrase(question, word) for word in pet_keywords)

        lost_object_analysis = analyze_lost_object_question_text(question)
        if lost_object_analysis and not has_pet:
            return Category.LOST_OBJECT, [lost_object_analysis["family"]]

        property_transition_patterns = [
            (r"\b(invest|investment)\s+in\s+(property|real\s*estate|house|building|land|flat|apartment|home)\b", "property investment"),
            (r"\b(buy|purchase|buying|acquire|acquiring|get|obtain)\b.*\b(property|real\s*estate|house|building|land|flat|apartment|home)\b", "property acquisition"),
            (r"\b(property|real\s*estate|house|building|land|flat|apartment|home)\b.*\b(buy|purchase|buying|acquire|acquiring|get|obtain)\b", "property acquisition"),
            (r"\b(sell|sale|selling|dispose of)\b.*\b(property|real\s*estate|house|building|land|flat|apartment|home)\b", "property sale"),
            (r"\b(property|real\s*estate|house|building|land|flat|apartment|home)\b.*\b(sell|sale|selling|dispose of)\b", "property sale"),
            (r"\bshould\s+(i|we)\s+(invest|buy|purchase).*\b(property|real\s*estate|house|building|land|flat|apartment|home)\b", "property decision"),
            (r"\b(tenant|occupant|lodger|renter|boarder)\b.*\b(move out|leave|vacate|quit)\b", "tenant occupancy change"),
            (r"\b(move out|vacate|quit)\b.*\b(tenant|occupant|lodger|renter|boarder)\b", "tenant occupancy change"),
            (r"\bwill\s+(he|she|they)\b.*\bleave\b.*\b(property|house|home|flat|apartment|building)\b", "occupant departure"),
            (r"\b(evict|evicted|eviction)\b.*\b(home|house|property|flat|apartment|building)?\b", "eviction risk"),
            (r"\blose\b.*\b(home|house|property|flat|apartment|building)\b", "loss of home"),
            (r"\b(friend'?s?)\s+(house|home|flat|apartment)\b.*\b(move|stay|live)\b", "friend house move"),
            (r"\b(move|stay|live)\b.*\b(friend'?s?)\s+(house|home|flat|apartment)\b", "friend house move"),
            (r"\b(rent|lease|hire)\b.*\b(house|home|property|flat|apartment)\b", "property rental"),
        ]
        for pattern, description in property_transition_patterns:
            if re.search(pattern, question, re.IGNORECASE):
                return Category.PROPERTY, [description]

        aid_analysis = analyze_aid_question_text(question, third_person_analysis)
        if aid_analysis and aid_analysis.get("category_override"):
            return aid_analysis["category_override"], [aid_analysis["family"]]

        economic_analysis = analyze_economic_question_text(question, None)
        if economic_analysis and economic_analysis.get("category_override"):
            return economic_analysis["category_override"], [economic_analysis["family"]]
        
        # PRIORITY 1: Financial transactions override relationship keywords
        transaction_words = ["sell", "buy", "purchase", "sale", "profit", "gain", "lose", "cost", "price", "payment", "trade", "exchange", "loan"]
        if any(word in question for word in transaction_words):
            return Category.MONEY, [word for word in transaction_words if word in question]
        
        # PRIORITY 2: Possession/property questions override person keywords  
        possession_words = ["car", "vehicle", "possessions", "belongings", "assets", "furniture", "jewelry", "valuables"]
        if any(word in question for word in possession_words):
            return Category.MONEY, [word for word in possession_words if word in question]

        # PRIORITY 3: Pet questions with possession words (lost/missing cat) should be PET, not LOST_OBJECT
        possession_indicators = ["lost", "missing", "find", "where is", "stolen", "disappeared"]
        has_possession = any(_has_phrase(question, word) for word in possession_indicators)
        
        if has_possession and has_pet:
            matched_pets = [word for word in pet_keywords if _has_phrase(question, word)]
            return Category.PET, matched_pets
        if has_pet:
            matched_pets = [word for word in pet_keywords if _has_phrase(question, word)]
            return Category.PET, matched_pets

        health_specific_patterns = [
            (r"\b(tumou?r|multiple sclerosis|sclerosis|diagnosis|diagnosed|inflammation|stomach|neurologist|symptom|symptoms)\b", "medical symptom/diagnosis"),
            (r"\b(stop growing|get better|recover|recovery|stabili[sz]e|improve|worsen|overworking)\b", "health development"),
            (r"\b(medicine|medication|treatment|therapy|prescription|dose|tablet|pill)\b", "medical treatment"),
            (r"\b(covid|doctor|clinic|hospital|medical|lab|laboratory|blood|biopsy|scan|mri|ct|x-?ray|xray|ultrasound|thyroid)\b.*\b(test result|result|results|report|letter|email|message|call|hear back|come back|arrive)\b", "medical result/contact"),
            (r"\b(test result|result|results|report|letter|email|message|call|hear back|come back|arrive)\b.*\b(covid|doctor|clinic|hospital|medical|lab|laboratory|blood|biopsy|scan|mri|ct|x-?ray|xray|ultrasound|thyroid)\b", "medical result/contact"),
        ]
        for pattern, description in health_specific_patterns:
            if re.search(pattern, question, re.IGNORECASE):
                return Category.HEALTH, [description]

        event_analysis = analyze_event_question_text(question)
        if event_analysis and event_analysis.get("category_override"):
            return event_analysis["category_override"], [event_analysis["family"]]

        passport_analysis = analyze_passport_question_text(
            question, self._detect_third_person_question(question)
        )
        if passport_analysis and passport_analysis.get("category_override"):
            return passport_analysis["category_override"], [passport_analysis["family"]]

        communication_analysis = analyze_communication_question_text(
            question, self._detect_third_person_question(question)
        )
        if communication_analysis and communication_analysis.get("category_override"):
            return communication_analysis["category_override"], [communication_analysis["family"]]

        if (
            "survive" in question.lower()
            and not has_pet
            and not any(token in question.lower() for token in ["vote of no confidence", "confidence vote", "stay in office", "remain prime minister"])
        ):
            return Category.DEATH, ["survival/death-edge wording"]

        # ENHANCED: Priority-based matching to handle overlapping keywords
        # Some words like "paralegal" contain "legal" but should match "education" not "lawsuit"
        
        matches = []
        for q_type, keywords in self.question_patterns.items():
            # FIXED: Better word boundary matching to avoid false positives like "ex" in "exam"
            matched_keywords = []
            for keyword in keywords:
                # Use word boundary checks for short words that can cause false positives
                if len(keyword) <= 3:
                    # For short words, require word boundaries or specific context
                    import re
                    pattern = r'\b' + re.escape(keyword) + r'\b'
                    if re.search(pattern, question, re.IGNORECASE):
                        matched_keywords.append(keyword)
                else:
                    # For longer words, simple substring matching is usually fine
                    if keyword in question:
                        matched_keywords.append(keyword)
            
            if matched_keywords:
                matches.append((q_type, matched_keywords))
        
        if not matches:
            return Category.GENERAL, []

        # If only one match, return it
        if len(matches) == 1:
            return matches[0][0], matches[0][1]
            
        # ENHANCED: Handle multiple matches with priority logic
        # Priority 1: Education keywords take precedence over legal when both match
        education_match = None
        lawsuit_match = None

        for q_type, matched_keywords in matches:
            if q_type == Category.EDUCATION:
                education_match = (q_type, matched_keywords)
            elif q_type == Category.LAWSUIT:
                lawsuit_match = (q_type, matched_keywords)
        
        # If both education and lawsuit match, prefer education for exam/student contexts
        if education_match and lawsuit_match:
            # Check for strong education indicators
            education_indicators = ["exam", "test", "student", "school", "college", "university", "pass", "graduate"]
            if any(indicator in question for indicator in education_indicators):
                return Category.EDUCATION, education_match[1]
            # Check for strong legal indicators  
            legal_indicators = ["court", "lawsuit", "judge", "trial", "litigation", "case"]
            if any(indicator in question for indicator in legal_indicators):
                return Category.LAWSUIT, lawsuit_match[1]

        # Priority 2: Prefer career over lost-object when ambiguity is caused by generic verbs like "find"
        # Example: "Will I find a new job?" should be CAREER, not LOST_OBJECT
        career_match = next(((qt, kw) for qt, kw in matches if qt == Category.CAREER), None)
        lost_match = next(((qt, kw) for qt, kw in matches if qt == Category.LOST_OBJECT), None)
        if career_match and lost_match:
            lost_keywords = set(lost_match[1])
            generic_lost_triggers = {"find", "where is", "locate"}
            strong_lost_triggers = {"lost", "missing", "stolen", "disappeared"}
            # If lost-object matched only via generic verbs, prefer career
            if lost_keywords and not (lost_keywords & strong_lost_triggers):
                return career_match[0], career_match[1]

        relationship_match = next(((qt, kw) for qt, kw in matches if qt == Category.RELATIONSHIP), None)
        if relationship_match and lost_match:
            lost_keywords = set(lost_match[1])
            strong_lost_triggers = {"lost", "missing", "stolen", "disappeared"}
            if lost_keywords and not (lost_keywords & strong_lost_triggers):
                return relationship_match[0], relationship_match[1]

        # Default: return the first match (maintains original behavior for other cases)
        return matches[0][0], matches[0][1]

    def _determine_question_intent(self, question: str, category: Category | None = None) -> str:
        """Classify a question as OCCURRENCE, QUALITY, or SAFETY.

        The analyzer historically used REUNION as a catch-all fallback, which
        made many non-reunion questions read oddly in pinned fixtures. The
        engine already uses a richer OCCURRENCE/QUALITY model, so the analyzer
        mirrors that vocabulary here while preserving a dedicated SAFETY label
        for explicit welfare/condition questions.
        """
        if not question:
            return "OCCURRENCE"

        q = question.lower().strip()

        quality_indicators = (
            "should i",
            "should we",
            "is it good",
            "is it wise",
            "is it favorable",
            "is it advisable",
            "is it beneficial",
            "is it worth",
            "is it right",
            "good idea",
            "wise to",
            "advisable to",
            "beneficial to",
            "favorable",
            "worth it",
            "good for me",
            "good for us",
            "right choice",
            "best option",
        )
        affection_indicators = (
            "like one another",
            "like each other",
            "like me",
            "like him",
            "like her",
            "feelings",
            "romantically",
            "romantic interest",
            "attracted",
            "attraction",
            "interested in",
            "crush",
            "spark",
            "chemistry",
        )
        safety_indicators = (
            "safe",
            "safety",
            "alive",
            "okay",
            "ok",
            "condition",
            "well",
            "healthy",
            "hurt",
            "injured",
            "sick",
            "dead",
            "died",
            "survive",
            "survival",
            "get better",
            "recover",
            "recovery",
            "improve",
            "improving",
            "harming",
            "helping",
        )
        occurrence_indicators = (
            "will i",
            "will we",
            "will it",
            "will this",
            "will there",
            "will they",
            "will he",
            "will she",
            "am i going to",
            "are we going to",
            "is it going to",
            "going to happen",
            "will happen",
            "going to get",
            "will get",
            "will receive",
            "will find",
            "will succeed",
            "will fail",
            "will be",
            "going to be",
            "happen",
            "occur",
            "come to pass",
            "succeed",
            "work out",
            "come back",
            "return",
            "get",
            "find",
            "obtain",
            "achieve",
            "arrive",
            "approved",
            "approval",
            "be approved",
            "be admitted",
            "hold another",
            "win",
            "sell",
            "buy",
        )
        direct_safety_starts = ("is ", "are ", "am ")

        def _has_indicator(text: str, indicator: str) -> bool:
            pattern = r"\b" + re.escape(indicator).replace(r"\ ", r"\s+") + r"\b"
            return bool(re.search(pattern, text))

        if any(_has_indicator(q, token) for token in affection_indicators):
            return "QUALITY"
        if any(_has_indicator(q, token) for token in quality_indicators):
            return "QUALITY"

        has_safety = any(_has_indicator(q, token) for token in safety_indicators)
        has_occurrence = any(_has_indicator(q, token) for token in occurrence_indicators)

        if q.startswith(direct_safety_starts) and has_safety:
            return "SAFETY"
        if has_safety and not has_occurrence:
            return "SAFETY"
        if has_safety and has_occurrence:
            if any(_has_indicator(q, token) for token in ("is he", "is she", "are they", "is my", "is our")) or any(token in q for token in ("ok?", "okay?")):
                return "SAFETY"
            return "OCCURRENCE"
        if has_occurrence:
            return "OCCURRENCE"

        if category == Category.PROPERTY:
            return "QUALITY" if any(_has_indicator(q, token) for token in quality_indicators) else "OCCURRENCE"
        if category in {
            Category.LOST_OBJECT,
            Category.MARRIAGE,
            Category.PREGNANCY,
            Category.CHILDREN,
            Category.TRAVEL,
            Category.GAMBLING,
            Category.FUNDING,
            Category.MONEY,
            Category.CAREER,
            Category.LAWSUIT,
            Category.RELATIONSHIP,
            Category.EDUCATION,
            Category.PROPERTY,
            Category.GENERAL,
        }:
            return "OCCURRENCE"
        if category in {Category.HEALTH, Category.DEATH, Category.PARENT, Category.PET}:
            return "SAFETY" if has_safety else "OCCURRENCE"

        return "OCCURRENCE"

    def _is_higher_education_question(self, question: str) -> bool:
        """Return True when the question is about higher learning/admission rather than generic success."""
        higher_education_keywords = [
            "university", "college", "campus", "degree", "masters", "master's", "master",
            "phd", "doctorate", "academic", "admission", "admitted", "enroll", "enrolled",
            "enrollment", "program", "coursework", "thesis", "dissertation", "exam", "exams",
            "certification", "board exam", "entrance exam",
        ]
        basic_education_markers = [
            "elementary", "primary school", "middle school", "high school", "grade school",
        ]
        question_lower = question.lower()
        if any(marker in question_lower for marker in basic_education_markers):
            return False
        return any(keyword in question_lower for keyword in higher_education_keywords)

    def _travel_house_focus(self, question: str) -> int:
        """Return the primary travel house, distinguishing short local transit from long journeys."""
        long_distance_keywords = [
            "far", "foreign", "abroad", "overseas", "international",
            "long-distance", "long distance", "long-term", "extended",
            "distant", "vacation", "holiday", "cruise", "pilgrimage",
        ]
        question_lower = question.lower()
        return 9 if any(word in question_lower for word in long_distance_keywords) else 3

    def _is_travel_health_question(self, question: str) -> bool:
        """Only add the 6th house to travel questions when illness or harm is actually in view."""
        import re

        travel_health_keywords = [
            "sick", "ill", "illness", "health", "injured", "injury",
            "hurt", "accident", "recover", "survive", "better",
        ]
        question_lower = question.lower()
        return any(re.search(r"\b" + re.escape(word) + r"\b", question_lower) for word in travel_health_keywords)
    
    def _determine_houses(
        self,
        question: str,
        question_type: Category,
        third_person_analysis: Dict = None,
        vehicle_analysis: Dict = None,
        aid_analysis: Dict = None,
        economic_analysis: Dict = None,
        custody_analysis: Dict = None,
        confinement_analysis: Dict = None,
        inheritance_analysis: Dict = None,
        property_analysis: Dict = None,
        publication_analysis: Dict = None,
        relative_analysis: Dict = None,
        roommate_analysis: Dict = None,
        theft_analysis: Dict = None,
        lawsuit_analysis: Dict = None,
        health_analysis: Dict = None,
        surgery_analysis: Dict = None,
        pet_analysis: Dict = None,
        lost_object_analysis: Dict = None,
        competition_analysis: Dict = None,
        state_analysis: Dict = None,
        immigration_analysis: Dict = None,
        passport_analysis: Dict = None,
        event_analysis: Dict = None,
        communication_analysis: Dict = None,
    ) -> tuple:
        """ENHANCED: Determine houses using comprehensive traditional horary rules"""
        
        # Start with querent (always 1st house)
        houses = [1]
        
        print(f"\n=== DEBUG: _determine_houses ===")
        print(f"question_type: {question_type}")
        print(f"question: {question[:100]}...")
        print(f"Initial houses: {houses}")
        
        if custody_analysis and custody_analysis.get("relevant_houses"):
            houses = list(custody_analysis["relevant_houses"])
            return houses, None

        if confinement_analysis and confinement_analysis.get("relevant_houses"):
            houses = list(confinement_analysis["relevant_houses"])
            return houses, None

        if inheritance_analysis and inheritance_analysis.get("relevant_houses"):
            houses = list(inheritance_analysis["relevant_houses"])
            return houses, None

        if surgery_analysis and surgery_analysis.get("relevant_houses"):
            houses = list(surgery_analysis["relevant_houses"])
            return houses, None

        if not vehicle_analysis and relative_analysis and relative_analysis.get("relevant_houses"):
            houses = list(relative_analysis["relevant_houses"])
            return houses, None

        if roommate_analysis and roommate_analysis.get("relevant_houses"):
            houses = list(roommate_analysis["relevant_houses"])
            return houses, None

        if vehicle_analysis and vehicle_analysis.get("relevant_houses"):
            houses = list(vehicle_analysis["relevant_houses"])
            return houses, None

        if aid_analysis and aid_analysis.get("relevant_houses"):
            houses = list(aid_analysis["relevant_houses"])
            return houses, None

        if theft_analysis and theft_analysis.get("relevant_houses"):
            houses = list(theft_analysis["relevant_houses"])
            return houses, None

        if economic_analysis and economic_analysis.get("relevant_houses"):
            houses = list(economic_analysis["relevant_houses"])
            return houses, None

        if question_type == Category.PROPERTY and property_analysis and property_analysis.get("relevant_houses"):
            houses = list(property_analysis["relevant_houses"])
            return houses, None

        if publication_analysis and publication_analysis.get("relevant_houses"):
            houses = list(publication_analysis["relevant_houses"])
            return houses, None

        if question_type == Category.LAWSUIT and lawsuit_analysis and lawsuit_analysis.get("relevant_houses"):
            houses = list(lawsuit_analysis["relevant_houses"])
            return houses, None

        if competition_analysis and competition_analysis.get("relevant_houses"):
            houses = list(competition_analysis["relevant_houses"])
            return houses, None

        if state_analysis and state_analysis.get("relevant_houses"):
            houses = list(state_analysis["relevant_houses"])
            return houses, None

        if immigration_analysis and immigration_analysis.get("relevant_houses"):
            houses = list(immigration_analysis["relevant_houses"])
            return houses, None

        if passport_analysis and passport_analysis.get("relevant_houses"):
            houses = list(passport_analysis["relevant_houses"])
            return houses, None

        if event_analysis and event_analysis.get("relevant_houses"):
            houses = list(event_analysis["relevant_houses"])
            return houses, None

        if communication_analysis and communication_analysis.get("relevant_houses"):
            houses = list(communication_analysis["relevant_houses"])
            return houses, None

        if question_type == Category.LOST_OBJECT and lost_object_analysis and lost_object_analysis.get("relevant_houses"):
            houses = list(lost_object_analysis["relevant_houses"])
            return houses, None

        # PRIORITY: Check for possession questions first with proper house derivation
        possession_analysis = self._analyze_possession_questions(question.lower())
        if possession_analysis:
            print(f"Possession analysis detected, returning: {possession_analysis['houses']}")
            return possession_analysis["houses"], possession_analysis
        
        # ENHANCED: Comprehensive house determination
        if question_type == Category.PET:
            # Pet questions: L1 (querent's ability to act) & L6 (small animals/pet's life)
            houses.append(6)  # 6th house = small domesticated animals
            logger.info(f"DETECTED PET QUESTION: Using houses [1, 6] for significators")
            
        elif question_type == Category.LOST_OBJECT:
            # Object questions: L1 (querent) & L2 (moveable possessions)
            houses.append(2)  # 2nd house = moveable possessions

        elif question_type == Category.MARRIAGE or "spouse" in question:
            houses.append(7)  # Marriage/spouse

        elif question_type == Category.RELATIONSHIP:
            # ENHANCED: Relationship questions use L1/L7 axis (self vs others)
            houses.append(7)  # L1 = self, L7 = other person/partner

        elif question_type == Category.PREGNANCY:
            if third_person_analysis and third_person_analysis.get("is_third_person"):
                subject_house = third_person_analysis["subject_house"]
                pregnancy_house = self._apply_house_derivation(subject_house, 5)
                houses.extend([subject_house, pregnancy_house])
            else:
                houses.append(5)  # Pregnancy and children

        elif question_type == Category.CHILDREN:
            if third_person_analysis and third_person_analysis.get("is_third_person"):
                subject_house = third_person_analysis["subject_house"]
                child_house = self._apply_house_derivation(subject_house, 5)
                houses.extend([subject_house, child_house])
            else:
                houses.append(5)  # Children

        elif question_type == Category.GAMBLING:
            houses.append(5)  # Gambling, speculation, lottery - 5th house pleasure/risk

        elif question_type == Category.TRAVEL:
            houses.append(self._travel_house_focus(question))
            if self._is_travel_health_question(question):
                houses.append(6)
                
        elif question_type == Category.FUNDING:
            # ENHANCED: Funding questions use L2/L8 axis (self resources vs others' money)
            if any(word in question for word in ["secure", "get", "receive", "obtain", "raise", "from investors", "investor", "vc", "angel"]):
                houses.extend([1, 8])  # L1 = querent, L8 = funding from others/investors
            elif any(word in question for word in ["my funding", "our funding", "have enough", "sufficient capital"]):
                houses.extend([1, 2])  # L1 = querent, L2 = self resources
            else:
                houses.extend([2, 8])  # Default: both self resources and others' money
            
        elif question_type == Category.MONEY:
            if any(word in question for word in ["debt", "loan", "owe", "borrow"]):
                houses.append(8)  # Debts and others' money
            elif any(word in question for word in ["property", "house", "real estate", "building", "land", "invest"]):
                # CRITICAL FIX: Property investment questions use L4 (property/real estate) not L2 (money)
                houses.append(4)  # Property, real estate, immovable goods
            else:
                houses.append(2)  # Personal money/possessions
                
        elif question_type == Category.CAREER:
            houses.append(10)  # Career/reputation/profession

        elif question_type == Category.HEALTH:
            if health_analysis and health_analysis.get("relevant_houses"):
                houses = list(health_analysis["relevant_houses"])
            else:
                # ENHANCED: Health questions use L1/L6 axis (self vs illness)
                houses.append(6)  # L1 already added; L6 = illness/disease
                
        elif question_type == Category.LAWSUIT:
            houses.extend([7, 10, 4])  # Opponent, judge, and end of the matter
            
        # NEW: Education questions with 3rd person logic - CRITICAL FIX
        elif question_type == Category.EDUCATION:
            if third_person_analysis and third_person_analysis.get("is_third_person"):
                # Question about someone else's education (e.g., "Will he pass the exam?")
                student_house = third_person_analysis["subject_house"]  # 7th house for the student
                
                # Student's preparation/knowledge = 3rd from student = radical 9th
                # (3rd house rules basic learning, study habits, preparation)
                prep_house = self._apply_house_derivation(student_house, 3)  # 9th house
                
                # Success in exams = 10th house (honors/achievement)
                success_house = 10
                
                houses = [1, student_house, prep_house, success_house]  # Querent, student, prep, success
                
            elif self._is_higher_education_question(question):
                houses.append(9)  # Higher learning/admission/exams above elementary level
            elif re.search(r"\b(my|i|will i)\b", question):
                houses.extend([10, 9])  # L10 = success/result first, then L9 = exam/knowledge
            else:
                houses.extend([10, 9])  # Default: L10 success primary, L9 knowledge secondary
                
        # NEW: Person-specific house assignments
        elif question_type == Category.PARENT:
            if any(word in question for word in ["father", "dad"]):
                houses.append(4)  # 4th house = father
            elif any(word in question for word in ["mother", "mom"]):
                houses.append(10)  # 10th house = mother
            else:
                houses.append(4)  # Default to father
                
        elif question_type == Category.SIBLING:
            houses.append(3)  # 3rd house = siblings
            
        elif question_type == Category.FRIEND_ENEMY:
            if any(word in question for word in ["friend", "ally"]):
                houses.append(11)  # 11th house = friends
            else:
                houses.append(7)   # 7th house = open enemies
                
        # NEW: Property questions
        elif question_type == Category.PROPERTY:
            for house in (property_analysis or {}).get("relevant_houses", [1, 4]):
                if house not in houses:
                    houses.append(house)
            
        # NEW: Death and inheritance
        elif question_type == Category.DEATH:
            if third_person_analysis and third_person_analysis.get("is_third_person"):
                subject_house = third_person_analysis["subject_house"]
                death_house = self._apply_house_derivation(subject_house, 8)
                houses = [subject_house]
                if death_house not in houses:
                    houses.append(death_house)
            else:
                houses.append(8)  # 8th house = death, wills, inheritance
            
        # NEW: Spiritual questions
        elif question_type == Category.SPIRITUAL:
            houses.append(9)  # 9th house = religion, spirituality, higher wisdom
            
        else:
            # Enhanced default logic - analyze question context
            if re.search(r"\b(other|they|he|she|person|someone)\b", question):
                houses.append(7)  # 7th house for other people
            else:
                houses.append(7)  # Default fallback

        if question_type == Category.GENERAL:
            houses = [1, 7]

        print(f"Final houses before return: {houses}")
        print(f"=== END _determine_houses DEBUG ===\n")
        
        return houses, None
    
    def _determine_significators(
        self,
        houses: List[int],
        question_type: Category,
        possession_analysis: Dict = None,
        third_person_analysis: Dict = None,
        vehicle_analysis: Dict = None,
        aid_analysis: Dict = None,
        economic_analysis: Dict = None,
        custody_analysis: Dict = None,
        confinement_analysis: Dict = None,
        inheritance_analysis: Dict = None,
        property_analysis: Dict = None,
        publication_analysis: Dict = None,
        relative_analysis: Dict = None,
        roommate_analysis: Dict = None,
        theft_analysis: Dict = None,
        lawsuit_analysis: Dict = None,
        health_analysis: Dict = None,
        surgery_analysis: Dict = None,
        pet_analysis: Dict = None,
        lost_object_analysis: Dict = None,
        competition_analysis: Dict = None,
        state_analysis: Dict = None,
        immigration_analysis: Dict = None,
        passport_analysis: Dict = None,
        event_analysis: Dict = None,
        communication_analysis: Dict = None,
    ) -> Dict[str, Any]:
        """Determine traditional significators with enhanced multi-house support"""
        
        # CRITICAL FIX: Handle natural significators for transaction questions
        if possession_analysis and "natural_significators" in possession_analysis:
            # For transaction questions (e.g., car sales), use natural significators
            natural_sigs = possession_analysis["natural_significators"]
            
            significators = {
                "querent_house": 1,  # Seller/querent
                "quesited_house": 7,  # Buyer/other party  
                "moon_role": "co-significator of querent and general flow",
                "special_significators": natural_sigs,  # Natural significators (e.g., Sun for car)
                "transaction_type": True  # Flag for transaction analysis
            }
        else:
            # ENHANCED: Handle 3rd person questions with multiple significators
            if custody_analysis and custody_analysis.get("family"):
                significators = {
                    "querent_house": custody_analysis.get("querent_house", custody_analysis.get("subject_house", 1)),
                    "subject_house": custody_analysis.get("subject_house", custody_analysis.get("querent_house", 1)),
                    "quesited_house": custody_analysis.get("quesited_house", houses[-1] if houses else 5),
                    "moon_role": "co-significator of the matter and unfolding testimony",
                    "special_significators": {},
                    "transaction_type": False,
                    "custody_family": custody_analysis.get("family"),
                    "child_house": custody_analysis.get("child_house"),
                    "opponent_house": custody_analysis.get("opponent_house"),
                    "judge_house": custody_analysis.get("judge_house"),
                    "outcome_house": custody_analysis.get("outcome_house"),
                }
            elif confinement_analysis and confinement_analysis.get("family"):
                subject_house = confinement_analysis.get("subject_house", 1)
                significators = {
                    "querent_house": 1,
                    "subject_house": subject_house,
                    "quesited_house": confinement_analysis.get("quesited_house", houses[-1] if houses else subject_house),
                    "moon_role": "co-significator of the matter and unfolding testimony",
                    "special_significators": {},
                    "transaction_type": False,
                    "confinement_family": confinement_analysis.get("family"),
                }
                for key in ("authority_house", "confinement_house"):
                    if confinement_analysis.get(key) is not None:
                        significators[key] = confinement_analysis.get(key)
            elif inheritance_analysis and inheritance_analysis.get("family"):
                subject_house = inheritance_analysis.get("subject_house", 1)
                significators = {
                    "querent_house": subject_house,
                    "subject_house": subject_house,
                    "quesited_house": inheritance_analysis.get("quesited_house", houses[-1] if houses else subject_house),
                    "moon_role": "co-significator of the matter and unfolding testimony",
                    "special_significators": {},
                    "transaction_type": False,
                    "inheritance_family": inheritance_analysis.get("family"),
                    "estate_house": inheritance_analysis.get("estate_house"),
                }
                if inheritance_analysis.get("property_house") is not None:
                    significators["property_house"] = inheritance_analysis.get("property_house")
            elif publication_analysis and publication_analysis.get("family"):
                significators = {
                    "querent_house": 1,
                    "quesited_house": publication_analysis.get("quesited_house", 9),
                    "moon_role": "co-significator of the matter and unfolding testimony",
                    "special_significators": {},
                    "transaction_type": False,
                    "publication_family": publication_analysis.get("family"),
                    "publication_house": publication_analysis.get("publication_house", 9),
                }
                for key in ("gain_house", "publisher_house"):
                    if publication_analysis.get(key) is not None:
                        significators[key] = publication_analysis.get(key)
            elif surgery_analysis and surgery_analysis.get("family"):
                subject_house = surgery_analysis.get("subject_house", 1)
                significators = {
                    "querent_house": subject_house,
                    "subject_house": subject_house,
                    "quesited_house": surgery_analysis.get("quesited_house", houses[-1] if houses else subject_house),
                    "moon_role": "co-significator of the matter and unfolding testimony",
                    "special_significators": {},
                    "transaction_type": False,
                    "surgery_family": surgery_analysis.get("family"),
                }
                for key in ("illness_house", "doctor_house", "procedure_house", "cost_house"):
                    if surgery_analysis.get(key) is not None:
                        significators[key] = surgery_analysis.get(key)
            elif (
                third_person_analysis
                and third_person_analysis.get("is_third_person")
                and question_type == Category.EDUCATION
                and not (aid_analysis and aid_analysis.get("family"))
            ):
                # Special case for education about someone else (e.g., "Will he pass the exam?")
                significators = {
                    "querent_house": 1,  # Teacher (querent)
                    "student_house": houses[1] if len(houses) > 1 else 7,  # Student (7th house)
                    "preparation_house": houses[2] if len(houses) > 2 else 9,  # Student's prep (9th house)
                    "success_house": houses[3] if len(houses) > 3 else 10,  # Success (10th house)
                    "quesited_house": houses[3] if len(houses) > 3 else 10,  # Primary question = success
                    "moon_role": "translation of light between significators",
                    "special_significators": {},
                    "transaction_type": False,
                    "third_person_education": True
                }
            elif third_person_analysis and third_person_analysis.get("is_third_person") and question_type == Category.PREGNANCY:
                subject_house = houses[1] if len(houses) > 1 else third_person_analysis.get("subject_house", 7)
                pregnancy_house = houses[2] if len(houses) > 2 else self._apply_house_derivation(subject_house, 5)
                significators = {
                    "querent_house": 1,
                    "subject_house": subject_house,
                    "pregnancy_house": pregnancy_house,
                    "quesited_house": pregnancy_house,
                    "moon_role": "co-significator of querent and general flow",
                    "special_significators": {},
                    "transaction_type": False,
                    "third_person_pregnancy": True
                }
            elif third_person_analysis and third_person_analysis.get("is_third_person") and question_type == Category.CHILDREN:
                subject_house = houses[1] if len(houses) > 1 else third_person_analysis.get("subject_house", 7)
                child_house = houses[2] if len(houses) > 2 else self._apply_house_derivation(subject_house, 5)
                significators = {
                    "querent_house": 1,
                    "subject_house": subject_house,
                    "child_house": child_house,
                    "quesited_house": child_house,
                    "moon_role": "co-significator of querent and general flow",
                    "special_significators": {},
                    "transaction_type": False,
                    "third_person_children": True
                }
            elif third_person_analysis and third_person_analysis.get("is_third_person") and question_type == Category.DEATH:
                subject_house = houses[0] if houses else third_person_analysis.get("subject_house", 7)
                death_house = houses[1] if len(houses) > 1 else self._apply_house_derivation(subject_house, 8)
                significators = {
                    "querent_house": subject_house,
                    "subject_house": subject_house,
                    "death_house": death_house,
                    "quesited_house": death_house,
                    "moon_role": "co-significator of the matter and unfolding testimony",
                    "special_significators": {},
                    "transaction_type": False,
                    "third_person_death": True
                }
            elif (not vehicle_analysis) and relative_analysis and relative_analysis.get("family"):
                significators = {
                    "querent_house": relative_analysis.get("subject_house", houses[0] if houses else 1),
                    "subject_house": relative_analysis.get("subject_house", houses[0] if houses else 1),
                    "quesited_house": relative_analysis.get("quesited_house", houses[-1] if houses else 7),
                    "moon_role": "co-significator of the matter and unfolding testimony",
                    "special_significators": {},
                    "transaction_type": False,
                    "relative_family": relative_analysis.get("family"),
                    "partner_house": relative_analysis.get("partner_house"),
                    "welfare_house": relative_analysis.get("welfare_house"),
                }
            elif theft_analysis and theft_analysis.get("family"):
                significators = {
                    "querent_house": 1,
                    "quesited_house": theft_analysis.get("quesited_house", houses[-1] if houses else 7),
                    "moon_role": "co-significator of the matter and unfolding testimony",
                    "special_significators": {},
                    "transaction_type": False,
                    "theft_family": theft_analysis.get("family"),
                    "thief_house": theft_analysis.get("thief_house"),
                    "object_house": theft_analysis.get("object_house"),
                    "money_house": theft_analysis.get("money_house"),
                    "thief_possession_house": theft_analysis.get("thief_possession_house"),
                }
            elif question_type == Category.HEALTH and health_analysis:
                subject_house = health_analysis.get("subject_house", 1)
                illness_house = health_analysis.get("illness_house", 6)
                significators = {
                    "querent_house": subject_house,
                    "subject_house": subject_house,
                    "illness_house": illness_house,
                    "quesited_house": health_analysis.get("quesited_house", illness_house),
                    "moon_role": "co-significator of the matter and unfolding testimony",
                    "special_significators": {},
                    "transaction_type": False,
                    "health_family": health_analysis.get("family", "general"),
                }
                if health_analysis.get("doctor_house") is not None:
                    significators["doctor_house"] = health_analysis.get("doctor_house")
                if health_analysis.get("treatment_house") is not None:
                    significators["treatment_house"] = health_analysis.get("treatment_house")
            elif question_type == Category.LAWSUIT and lawsuit_analysis:
                significators = {
                    "querent_house": lawsuit_analysis.get("querent_house", houses[0] if houses else 1),
                    "quesited_house": lawsuit_analysis.get("quesited_house", houses[1] if len(houses) > 1 else 7),
                    "moon_role": "co-significator of the matter and unfolding testimony",
                    "special_significators": {},
                    "transaction_type": False,
                    "lawsuit_family": lawsuit_analysis.get("family", "court_adjudication"),
                    "opponent_house": lawsuit_analysis.get("opponent_house"),
                    "judge_house": lawsuit_analysis.get("judge_house"),
                    "outcome_house": lawsuit_analysis.get("outcome_house"),
                    "subject_matter_house": lawsuit_analysis.get("subject_matter_house"),
                }
            elif question_type == Category.LOST_OBJECT and lost_object_analysis:
                significators = {
                    "querent_house": 1,
                    "quesited_house": lost_object_analysis.get("quesited_house", 2),
                    "object_house": lost_object_analysis.get("object_house", 2),
                    "moon_role": "co-significator of querent and recovery flow",
                    "special_significators": {},
                    "transaction_type": False,
                    "lost_object_family": lost_object_analysis.get("family", "discovery"),
                    "natural_object_significator": lost_object_analysis.get("natural_object_planet"),
                }
            elif competition_analysis and competition_analysis.get("family"):
                significators = {
                    "querent_house": competition_analysis.get("querent_house", houses[0] if houses else 1),
                    "quesited_house": competition_analysis.get("quesited_house", houses[-1] if houses else 7),
                    "moon_role": "co-significator of the contest and unfolding result",
                    "special_significators": {},
                    "transaction_type": False,
                    "competition_family": competition_analysis.get("family"),
                    "incumbent_house": competition_analysis.get("incumbent_house"),
                    "challenger_house": competition_analysis.get("challenger_house"),
                    "office_house": competition_analysis.get("office_house"),
                }
            elif state_analysis and state_analysis.get("family"):
                significators = {
                    "querent_house": state_analysis.get("querent_house", houses[0] if houses else 1),
                    "quesited_house": state_analysis.get("quesited_house", houses[-1] if houses else 7),
                    "moon_role": "co-significator of the matter and unfolding testimony",
                    "special_significators": {},
                    "transaction_type": False,
                    "state_family": state_analysis.get("family"),
                    "homeland_house": state_analysis.get("homeland_house"),
                    "foreign_state_house": state_analysis.get("foreign_state_house"),
                    "target_state_house": state_analysis.get("target_state_house"),
                }
            elif immigration_analysis and immigration_analysis.get("family"):
                subject_house = immigration_analysis.get("subject_house", 1)
                significators = {
                    "querent_house": subject_house,
                    "subject_house": subject_house,
                    "quesited_house": immigration_analysis.get("quesited_house", houses[-1] if houses else 9),
                    "moon_role": "co-significator of the matter and unfolding testimony",
                    "special_significators": {},
                    "transaction_type": False,
                    "immigration_family": immigration_analysis.get("family"),
                    "authorization_house": immigration_analysis.get("authorization_house"),
                    "authority_house": immigration_analysis.get("authority_house"),
                    "work_house": immigration_analysis.get("work_house"),
                }
            elif passport_analysis and passport_analysis.get("family"):
                subject_house = passport_analysis.get("subject_house", 1)
                significators = {
                    "querent_house": subject_house,
                    "subject_house": subject_house,
                    "quesited_house": passport_analysis.get("quesited_house", houses[-1] if houses else 3),
                    "moon_role": "co-significator of the matter and unfolding testimony",
                    "special_significators": {},
                    "transaction_type": False,
                    "passport_family": passport_analysis.get("family"),
                    "document_house": passport_analysis.get("document_house"),
                    "authority_house": passport_analysis.get("authority_house"),
                }
            elif roommate_analysis and roommate_analysis.get("family"):
                subject_house = roommate_analysis.get("subject_house", 1)
                significators = {
                    "querent_house": subject_house,
                    "subject_house": subject_house,
                    "quesited_house": roommate_analysis.get("quesited_house", houses[-1] if houses else 7),
                    "moon_role": "co-significator of the matter and unfolding testimony",
                    "special_significators": {},
                    "transaction_type": False,
                    "roommate_family": roommate_analysis.get("family"),
                    "roommate_house": roommate_analysis.get("roommate_house"),
                    "partner_house": roommate_analysis.get("partner_house"),
                    "home_house": roommate_analysis.get("home_house"),
                }
            elif vehicle_analysis and vehicle_analysis.get("family"):
                significators = {
                    "querent_house": vehicle_analysis.get("subject_house", houses[0] if houses else 1),
                    "subject_house": vehicle_analysis.get("subject_house"),
                    "quesited_house": vehicle_analysis.get("quesited_house", houses[-1] if houses else 7),
                    "moon_role": "co-significator of the matter and unfolding testimony",
                    "special_significators": vehicle_analysis.get("special_significators", {}),
                    "transaction_type": bool(vehicle_analysis.get("transaction_type")),
                    "vehicle_family": vehicle_analysis.get("family"),
                    "vehicle_house": vehicle_analysis.get("vehicle_house"),
                    "seller_house": vehicle_analysis.get("seller_house"),
                    "buyer_house": vehicle_analysis.get("buyer_house"),
                    "possession_house": vehicle_analysis.get("possession_house"),
                    "buyer_money_house": vehicle_analysis.get("buyer_money_house"),
                }
            elif aid_analysis and aid_analysis.get("family"):
                subject_house = aid_analysis.get("subject_house", 1)
                significators = {
                    "querent_house": subject_house,
                    "subject_house": subject_house,
                    "quesited_house": aid_analysis.get("quesited_house", houses[-1] if houses else subject_house),
                    "moon_role": "co-significator of the matter and unfolding testimony",
                    "special_significators": {},
                    "transaction_type": False,
                    "aid_family": aid_analysis.get("family"),
                    "education_house": aid_analysis.get("education_house"),
                    "scholarship_house": aid_analysis.get("scholarship_house"),
                    "support_house": aid_analysis.get("support_house"),
                    "eligibility_house": aid_analysis.get("eligibility_house"),
                    "authority_house": aid_analysis.get("authority_house"),
                }
            elif event_analysis and event_analysis.get("family"):
                significators = {
                    "querent_house": 1,
                    "quesited_house": event_analysis.get("quesited_house", houses[-1] if houses else 7),
                    "moon_role": "co-significator of the matter and unfolding testimony",
                    "special_significators": {},
                    "transaction_type": False,
                    "event_family": event_analysis.get("family"),
                    "event_house": event_analysis.get("event_house"),
                }
            elif communication_analysis and communication_analysis.get("family"):
                significators = {
                    "querent_house": 1,
                    "quesited_house": communication_analysis.get("quesited_house", houses[-1] if houses else 7),
                    "moon_role": "co-significator of the matter and unfolding testimony",
                    "special_significators": {},
                    "transaction_type": False,
                    "communication_family": communication_analysis.get("family"),
                    "communication_house": communication_analysis.get("communication_house"),
                    "recipient_house": communication_analysis.get("recipient_house"),
                    "friend_house": communication_analysis.get("friend_house"),
                    "goods_house": communication_analysis.get("goods_house"),
                    "home_house": communication_analysis.get("home_house"),
                    "courier_house": communication_analysis.get("courier_house"),
                    "holder_house": communication_analysis.get("holder_house"),
                }
            else:
                # FIXED: For general questions, use 7th house. For derived house questions, use the actual target.
                if question_type == Category.GENERAL:
                    target_house = 7  # Traditional "other person" for general questions
                elif question_type == Category.EDUCATION:
                    target_house = houses[1] if len(houses) > 1 else 10
                elif economic_analysis and economic_analysis.get("quesited_house"):
                    target_house = economic_analysis["quesited_house"]
                elif question_type == Category.CAREER:
                    target_house = 10
                elif question_type in [Category.RELATIONSHIP, Category.MARRIAGE] and 7 in houses:
                    target_house = 7  # Relationship questions should use 7th house, not 8th
                elif question_type == Category.PROPERTY and property_analysis and property_analysis.get("quesited_house"):
                    target_house = property_analysis["quesited_house"]
                elif competition_analysis and competition_analysis.get("quesited_house") is not None:
                    target_house = competition_analysis["quesited_house"]
                else:
                    # For derived house questions (e.g., [1, 7, 8] for husband's possessions)
                    target_house = houses[-1] if len(houses) > 1 else 7

                significators = {
                    "querent_house": 1,  # Always 1st house
                    "quesited_house": target_house,  # Use the final derived house
                    "moon_role": "co-significator of querent and general flow",
                    "special_significators": {},
                    "transaction_type": False
                }

        if question_type == Category.PROPERTY and property_analysis:
            significators["property_house"] = property_analysis.get("property_house", 4)
            significators["seller_house"] = property_analysis.get("seller_house", 7)
            if property_analysis.get("counterparty_house") is not None:
                significators["counterparty_house"] = property_analysis.get("counterparty_house")
            significators["profit_house"] = property_analysis.get("profit_house", 10)
            significators["end_house"] = property_analysis.get("end_house", 4)
            significators["property_family"] = property_analysis.get("family", "condition")
        if economic_analysis:
            for key in (
                "tenant_house",
                "tenant_money_house",
                "receipt_house",
                "stake_house",
                "bookmaker_house",
                "winnings_house",
                "counterparty_house",
                "business_house",
                "profit_house",
                "partner_house",
                "reviewer_house",
                "counterparty_money_house",
                "lender_house",
                "loan_house",
            ):
                if economic_analysis.get(key) is not None:
                    significators[key] = economic_analysis.get(key)
            if economic_analysis.get("family"):
                significators["economic_family"] = economic_analysis["family"]
        if vehicle_analysis:
            if vehicle_analysis.get("family"):
                significators["vehicle_family"] = vehicle_analysis.get("family")
            for key in (
                "subject_house",
                "vehicle_house",
                "seller_house",
                "buyer_house",
                "possession_house",
                "buyer_money_house",
            ):
                if vehicle_analysis.get(key) is not None:
                    significators[key] = vehicle_analysis.get(key)
        if aid_analysis:
            if aid_analysis.get("family"):
                significators["aid_family"] = aid_analysis.get("family")
            for key in (
                "subject_house",
                "education_house",
                "scholarship_house",
                "support_house",
                "eligibility_house",
                "authority_house",
            ):
                if aid_analysis.get(key) is not None:
                    significators[key] = aid_analysis.get(key)
        if custody_analysis:
            if custody_analysis.get("family"):
                significators["custody_family"] = custody_analysis.get("family")
            for key in ("subject_house", "child_house", "opponent_house", "judge_house", "outcome_house"):
                if custody_analysis.get(key) is not None:
                    significators[key] = custody_analysis.get(key)
        if relative_analysis and not vehicle_analysis:
            if relative_analysis.get("family"):
                significators["relative_family"] = relative_analysis["family"]
            for key in ("subject_house", "partner_house", "welfare_house"):
                if relative_analysis.get(key) is not None:
                    significators[key] = relative_analysis.get(key)
        if theft_analysis:
            if theft_analysis.get("family"):
                significators["theft_family"] = theft_analysis.get("family")
            for key in ("thief_house", "object_house", "money_house", "thief_possession_house"):
                if theft_analysis.get(key) is not None:
                    significators[key] = theft_analysis.get(key)
        if lawsuit_analysis:
            if lawsuit_analysis.get("family"):
                significators["lawsuit_family"] = lawsuit_analysis.get("family")
            for key in ("opponent_house", "judge_house", "outcome_house", "subject_matter_house"):
                if lawsuit_analysis.get(key) is not None:
                    significators[key] = lawsuit_analysis.get(key)
        if lost_object_analysis:
            significators["lost_object_family"] = lost_object_analysis.get("family")
            if lost_object_analysis.get("natural_object_planet") is not None:
                significators["natural_object_significator"] = lost_object_analysis.get("natural_object_planet")
        if pet_analysis:
            significators["pet_family"] = pet_analysis.get("family")
        if competition_analysis:
            if competition_analysis.get("family"):
                significators["competition_family"] = competition_analysis.get("family")
            for key in ("incumbent_house", "challenger_house", "office_house"):
                if competition_analysis.get(key) is not None:
                    significators[key] = competition_analysis.get(key)
        if state_analysis:
            if state_analysis.get("family"):
                significators["state_family"] = state_analysis.get("family")
            for key in ("homeland_house", "foreign_state_house", "target_state_house"):
                if state_analysis.get(key) is not None:
                    significators[key] = state_analysis.get(key)
        if immigration_analysis:
            if immigration_analysis.get("family"):
                significators["immigration_family"] = immigration_analysis.get("family")
            for key in ("authorization_house", "authority_house", "work_house"):
                if immigration_analysis.get(key) is not None:
                    significators[key] = immigration_analysis.get(key)
        if passport_analysis:
            if passport_analysis.get("family"):
                significators["passport_family"] = passport_analysis.get("family")
            for key in ("document_house", "authority_house", "subject_house"):
                if passport_analysis.get(key) is not None:
                    significators[key] = passport_analysis.get(key)
        if roommate_analysis:
            if roommate_analysis.get("family"):
                significators["roommate_family"] = roommate_analysis.get("family")
            for key in ("roommate_house", "partner_house", "home_house", "subject_house"):
                if roommate_analysis.get(key) is not None:
                    significators[key] = roommate_analysis.get(key)
        if event_analysis:
            if event_analysis.get("family"):
                significators["event_family"] = event_analysis.get("family")
            if event_analysis.get("event_house") is not None:
                significators["event_house"] = event_analysis.get("event_house")
        if communication_analysis:
            if communication_analysis.get("family"):
                significators["communication_family"] = communication_analysis.get("family")
            for key in (
                "communication_house",
                "recipient_house",
                "friend_house",
                "goods_house",
                "home_house",
                "courier_house",
                "holder_house",
            ):
                if communication_analysis.get(key) is not None:
                    significators[key] = communication_analysis.get(key)
        
        # Add natural significators based on question type
        if question_type == Category.MARRIAGE:
            significators["special_significators"]["venus"] = "natural significator of love"
            significators["special_significators"]["mars"] = "natural significator of men"
        elif question_type == Category.GAMBLING:
            significators["special_significators"]["jupiter"] = "natural significator of fortune and luck"
            significators["special_significators"]["venus"] = "natural significator of pleasure and enjoyment"
        elif question_type == Category.FUNDING:
            significators["special_significators"]["jupiter"] = "natural significator of abundance and investors"
            significators["special_significators"]["venus"] = "natural significator of attraction and partnerships"
            significators["special_significators"]["mercury"] = "natural significator of contracts and negotiations"
        elif question_type == Category.MONEY:
            significators["special_significators"]["jupiter"] = "greater fortune"
            significators["special_significators"]["venus"] = "lesser fortune"
        elif question_type == Category.CAREER:
            significators["special_significators"]["sun"] = "honor and reputation"
            significators["special_significators"]["jupiter"] = "success"
        elif question_type == Category.HEALTH:
            significators["special_significators"]["mars"] = "fever and inflammation"
            significators["special_significators"]["saturn"] = "chronic illness"
        # NEW: Education significators
        elif question_type == Category.EDUCATION:
            significators["special_significators"]["mercury"] = "natural significator of learning and knowledge"
            significators["special_significators"]["jupiter"] = "wisdom and higher learning"
        # NEW: Travel significators
        elif question_type == Category.TRAVEL:
            significators["special_significators"]["mercury"] = "short journeys"
            significators["special_significators"]["jupiter"] = "long journeys and foreign travel"
        
        return significators


