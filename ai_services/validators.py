"""
Domain, language, and subject-topic validation utilities for EduAI.
Prevents topic/subject mismatches, non-coding subjects receiving code snippets,
and inconsistent output languages across repeated generations.
"""
import re
import logging

logger = logging.getLogger(__name__)

# Domain keyword mappings (lowercase substring/word patterns)
DOMAIN_KEYWORDS = {
    'tamil': [
        'tamil', 'தமிழ்', 'tamizh', 'sangam', 'சங்க', 'thirukkural', 'திருக்குறள்',
        'tholkappiyam', 'tolkappiyam', 'தொல்காப்பியம்', 'silappathikaram', 'சிலப்பதிகாரம்',
        'manimekalai', 'மணிமேகலை', 'ilakkiyam', 'இலக்கியம்', 'ilakkanam', 'இலக்கணம்',
        'bharathiyar', 'bharathidasan', 'kambaramayanam', 'kambar', 'ettuthogai',
        'pattuppattu', 'pathinenkilkanakku', 'akanaanuru', 'puranaanuru', 'kuruntokai',
        'naladiyar', 'aathichudi', 'ezhuththu', 'agapporul', 'purapporul', 'yappu',
        'chola', 'chera', 'pandya', 'pallava', 'avvaiyar', 'valluvar', 'tirukkural',
    ],
    'programming': [
        'python', 'java', 'javascript', 'typescript', 'c++', 'csharp', 'c#', 'golang',
        'rust', 'php', 'ruby', 'kotlin', 'swift', 'sql', 'mysql', 'postgresql', 'mongodb',
        'database', 'databases', 'html', 'css', 'react', 'angular', 'vue', 'django',
        'flask', 'fastapi', 'nodejs', 'node.js', 'programming', 'coding', 'software',
        'algorithm', 'algorithms', 'data structure', 'data structures', 'web development',
        'rest api', 'machine learning', 'deep learning', 'neural network',
        'artificial intelligence', 'data science', 'cybersecurity', 'encryption',
        'operating system', 'compiler', 'object oriented', 'object-oriented', 'oop',
        'recursion', 'linked list', 'binary tree', 'pandas', 'numpy', 'tensorflow',
        'pytorch', 'scikit', 'docker', 'kubernetes', 'cloud computing', 'computer science',
        'decorators', 'generators', 'async await', 'variables and data types',
    ],
    'english': [
        'english', 'shakespeare', 'sonnet', 'romanticism', 'victorian',
        'macbeth', 'hamlet', 'wordsworth', 'keats', 'chaucer', 'milton', 'phonetics',
        'english literature', 'english grammar', 'parts of speech', 'active and passive voice',
    ],
    'mathematics': [
        'mathematics', 'maths', 'calculus', 'algebra', 'geometry', 'trigonometry',
        'matrix', 'matrices', 'differential', 'integral', 'probability', 'statistics',
        'number theory', 'combinatorics', 'eigenvalue', 'polynomial', 'logarithm',
        'pythagoras', 'theorem', 'quadratic', 'calculus',
    ],
    'physics': [
        'physics', 'newton', 'thermodynamics', 'quantum', 'optics', 'electromagnetism',
        'kinematics', 'relativity', 'gravity', 'mechanics', 'nuclear physics',
        'astrophysics', 'photonics', 'ohm', 'magnetism',
    ],
    'chemistry': [
        'chemistry', 'periodic table', 'organic chemistry', 'inorganic chemistry',
        'stoichiometry', 'titration', 'chemical bond', 'covalent', 'ionic',
        'enthalpy', 'entropy', 'electrochemistry', 'hydrocarbon', 'alkane',
        'polymer', 'molarity', 'molecule', 'valency',
    ],
    'biology': [
        'biology', 'photosynthesis', 'mitosis', 'meiosis', 'genetics', 'dna', 'rna',
        'chromosome', 'ecology', 'ecosystem', 'anatomy', 'physiology', 'botany',
        'zoology', 'microbiology', 'enzyme', 'evolution', 'cell division', 'respiration',
    ],
    'history': [
        'history', 'civilization', 'empire', 'dynasty', 'revolution', 'world war',
        'colonial', 'independence movement', 'maurya', 'mughal', 'harappan',
        'indus valley', 'renaissance', 'ancient', 'medieval', 'sangam age',
    ],
}

COMPATIBLE_DOMAIN_PAIRS = {
    frozenset({'programming', 'mathematics'}),
    frozenset({'physics', 'mathematics'}),
    frozenset({'chemistry', 'physics'}),
    frozenset({'chemistry', 'biology'}),
    frozenset({'tamil', 'history'}),
    frozenset({'english', 'history'}),
}


def _match_domains(text: str) -> set[str]:
    """Identify matching academic domains present in text."""
    lower = f" {text.lower()} "
    # Also check Tamil Unicode range directly
    matched = set()
    if re.search(r'[\u0B80-\u0BFF]', text):
        matched.add('tamil')

    for domain, keywords in DOMAIN_KEYWORDS.items():
        for kw in keywords:
            if len(kw) <= 3 and kw.isascii():
                if re.search(rf'\b{re.escape(kw)}\b', lower):
                    matched.add(domain)
                    break
            else:
                if kw in lower:
                    matched.add(domain)
                    break
    return matched


def is_tamil_context(subject: str, topic: str = '', custom_instructions: str = '') -> bool:
    """
    Determine deterministically whether generated educational content/quizzes
    should be written in Tamil script.
    """
    ci_lower = (custom_instructions or '').lower()
    if any(phrase in ci_lower for phrase in ['in english', 'english only', 'use english', 'write in english']):
        return False
    if any(phrase in ci_lower for phrase in ['in tamil', 'tamil only', 'use tamil', 'write in tamil']):
        return True

    subj_lower = (subject or '').strip().lower()
    if (
        'tamil' in subj_lower
        or 'tamizh' in subj_lower
        or 'தமிழ்' in (subject or '')
        or re.search(r'[\u0B80-\u0BFF]', f"{subject} {topic} {custom_instructions}")
    ):
        return True

    return False


def is_coding_subject(subject: str, topic: str = '') -> bool:
    """Return True if subject/topic belongs to software programming / CS."""
    domains = _match_domains(f"{subject} {topic}")
    return 'programming' in domains


def build_language_and_domain_rules(
    subject: str,
    topic: str,
    custom_instructions: str = '',
    is_quiz: bool = False,
) -> str:
    """Build strict, deterministic language and domain instructions for prompts."""
    tamil_mode = is_tamil_context(subject, topic, custom_instructions)
    coding_mode = is_coding_subject(subject, topic)

    rules = []
    if tamil_mode:
        if is_quiz:
            rules.append(
                "CRITICAL LANGUAGE RULE: Write EVERY question, option label text (keeping the A)/B)/C)/D) prefix), "
                "and explanation consistently in Tamil (தமிழ்) script across every generation. "
                "Keep only the JSON keys ('question', 'options', 'correct_answer', 'explanation') in English."
            )
        else:
            rules.append(
                "CRITICAL LANGUAGE RULE: Write the ENTIRE learning content consistently in Tamil (தமிழ்) script "
                "(headings, explanations, examples, and Key Takeaways in Tamil). Maintain this exact same Tamil language "
                "output every time for these inputs. Do NOT switch to English paragraphs."
            )
    else:
        if is_quiz:
            rules.append(
                "CRITICAL LANGUAGE RULE: Write every question, option, and explanation consistently in clear English."
            )
        else:
            rules.append(
                "CRITICAL LANGUAGE RULE: Write the ENTIRE learning content consistently in clear English."
            )

    if coding_mode:
        rules.append(
            "DOMAIN RULE: Since this is a technical/programming subject, include accurate code snippets or technical examples where appropriate."
        )
    else:
        rules.append(
            f"STRICT DOMAIN RULE: '{subject}' / '{topic}' is NOT a software programming topic. "
            "NEVER include Python, Java, JavaScript, SQL, pseudocode, or any programming code blocks anywhere in your response. "
            "Use authentic subject-appropriate examples (such as literary verses/poems, historical events, cultural analysis, worked non-code derivations, or real-world cases)."
        )

    return "\n".join(rules)


def validate_subject_topic_relevance(subject: str, topic: str, llm_service=None) -> tuple[bool, str]:
    """
    Validate that the provided topic is relevant to the selected subject.
    Returns (is_valid, error_message).
    """
    subj_clean = (subject or '').strip()
    topic_clean = (topic or '').strip()

    if not subj_clean:
        return False, "Please enter or select a subject."
    if not topic_clean:
        return True, ""

    # Allow standard default topic derived from the same subject
    normalized_subj = subj_clean.lower()
    normalized_topic = topic_clean.lower()
    if (
        normalized_topic == f"{normalized_subj} overview & fundamentals"
        or normalized_topic == f"{normalized_subj} fundamentals"
        or normalized_subj in normalized_topic
    ):
        # If the user typed "<OtherSubject> Overview & Fundamentals" under a different subject, catch it below
        if (
            normalized_topic.startswith(normalized_subj)
            or normalized_subj in normalized_topic
        ):
            return True, ""

    # Reject explicit "<DifferentSubject> Overview & Fundamentals"
    overview_match = re.match(r'^(.+?)\s+(?:overview\s*&\s*fundamentals|fundamentals)$', normalized_topic)
    if overview_match:
        prefix = overview_match.group(1).strip()
        if prefix and prefix != normalized_subj and normalized_subj not in prefix and prefix not in normalized_subj:
            return (
                False,
                f'The topic "{topic_clean}" belongs to "{prefix.title()}", which does not match the selected subject "{subj_clean}". Please enter a {subj_clean}-related topic.'
            )

    subj_domains = _match_domains(subj_clean)
    topic_domains = _match_domains(topic_clean)

    # Strong deterministic domain mismatch check
    if subj_domains and topic_domains:
        if subj_domains & topic_domains:
            return True, ""
        # Check if any pair between subject domains and topic domains is legitimately compatible
        is_compatible = any(
            frozenset({sd, td}) in COMPATIBLE_DOMAIN_PAIRS
            for sd in subj_domains
            for td in topic_domains
        )
        if not is_compatible:
            return (
                False,
                f'The topic "{topic_clean}" is not relevant to the selected subject "{subj_clean}". Please enter a topic related to {subj_clean}.'
            )

    # Optional live-LLM relevance guard for unlisted subjects/topics (skipped in offline fallback mode)
    if llm_service and (getattr(llm_service, 'use_new_sdk', False) or getattr(llm_service, 'legacy_model', None)):
        validation_prompt = (
            f'You are a strict academic curriculum validator.\n'
            f'Subject: "{subj_clean}"\n'
            f'Topic: "{topic_clean}"\n\n'
            f'Is the Topic educationally relevant or belonging to the Subject? '
            f'Wait: only reply INVALID if the topic is clearly unrelated to the subject (for example, Python Programming under Tamil, or Biology under History).\n'
            f'Reply with ONLY one line:\n'
            f'VALID\n'
            f'or\n'
            f'INVALID: <brief 1-sentence reason explaining the mismatch>'
        )
        try:
            verdict = llm_service.generate_raw(validation_prompt, temperature=0.0) if hasattr(llm_service, 'generate_raw') else ''
            if verdict and verdict.strip().upper().startswith('INVALID:'):
                reason = verdict.split(':', 1)[1].strip()
                return False, reason or f'The topic "{topic_clean}" is not relevant to "{subj_clean}".'
        except Exception as exc:
            logger.debug(f"LLM subject-topic check skipped due to error: {exc}")

    return True, ""
