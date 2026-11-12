"""
LLM Service — Gemini (Free Tier via google.genai and google.generativeai fallback)
Primary AI engine for content generation, quiz creation, recommendations, and feedback.
Includes a rich context-aware mock generator if the API key is not yet set or invalid.
"""
import os
import re
import json
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class LLMService:
    """
    Abstraction layer for LLM calls.
    Primary: Google Gemini (gemini-3-flash-preview / gemini-3.1-flash-lite-preview / gemini-3.5-flash-lite)
    Fallback: Smart context-aware offline generator
    """

    def __init__(self):
        self.client = None
        self.legacy_model = None
        self.use_new_sdk = False
        self._initialize()

    def _initialize(self):
        """Initialize Gemini client."""
        api_key = getattr(settings, 'GEMINI_API_KEY', '') or os.getenv('GEMINI_API_KEY', '')
        if not api_key or api_key == 'your_gemini_api_key_here':
            logger.warning("No valid Gemini API key found. Using context-aware fallback mode.")
            return

        # Attempt modern google.genai SDK first
        try:
            from google import genai
            self.client = genai.Client(api_key=api_key)
            self.use_new_sdk = True
            logger.info("Gemini modern SDK (google.genai) initialized successfully.")
            return
        except Exception as e:
            logger.warning(f"Could not initialize google.genai client: {e}")

        # Fallback to legacy google.generativeai SDK
        try:
            import google.generativeai as legacy_genai
            legacy_genai.configure(api_key=api_key)
            self.legacy_model = legacy_genai.GenerativeModel(
                model_name='gemini-1.5-flash',
                generation_config={
                    'temperature': 0.25,
                    'top_p': 0.85,
                    'top_k': 40,
                    'max_output_tokens': 4096,
                }
            )
            logger.info("Gemini legacy SDK initialized.")
        except Exception as e:
            logger.error(f"Failed to initialize legacy Gemini SDK: {e}")

    def generate_raw(self, prompt: str, temperature: float = 0.2) -> str:
        """
        Call configured Gemini SDK and return text, or empty string if unavailable/failed.
        Does NOT invoke offline fallback.
        """
        if self.use_new_sdk and self.client:
            config = None
            try:
                from google.genai import types
                config = types.GenerateContentConfig(
                    temperature=temperature,
                    top_p=0.85,
                    max_output_tokens=4096,
                )
            except Exception:
                config = None

            for model_name in [
                'gemini-3-flash-preview',
                'gemini-2.5-flash',
                'gemini-3.1-flash-lite-preview',
                'gemini-3.5-flash-lite',
            ]:
                try:
                    kwargs = {'model': model_name, 'contents': prompt}
                    if config is not None:
                        kwargs['config'] = config
                    response = self.client.models.generate_content(**kwargs)
                    if response and response.text:
                        return response.text.strip()
                except Exception as e:
                    logger.warning(f"google.genai call with {model_name} failed: {e}")

        if self.legacy_model:
            try:
                response = self.legacy_model.generate_content(prompt)
                if response and response.text:
                    return response.text.strip()
            except Exception as e:
                logger.warning(f"Legacy Gemini generation failed: {e}")

        return ""

    def generate(self, prompt: str, temperature: float = 0.2) -> str:
        """
        Generate text from a prompt.
        If the API call fails or no key is present, falls back gracefully.
        """
        raw = self.generate_raw(prompt, temperature=temperature)
        if raw:
            return raw

        # Graceful, dynamic offline generator based on prompt requirements
        return self._fallback_generate(prompt)

    def _fallback_generate(self, prompt: str) -> str:
        """
        Context-aware fallback that matches the requested output structure
        (JSON quiz, JSON recommendation, or structured Markdown learning content).
        """
        prompt_lower = prompt.lower()

        # 1. Recommendation request (JSON expected)
        if 'learning recommendations' in prompt_lower or '"next_topics"' in prompt:
            # Extract subject / skill if possible
            subj_match = re.search(r'preferred subjects:\s*([^\n]+)', prompt, re.IGNORECASE)
            subject = subj_match.group(1).strip() if subj_match else "Python"
            return json.dumps({
                "next_topics": [
                    f"{subject} Fundamentals & Architecture",
                    f"Intermediate {subject} Problem Solving",
                    f"Hands-on {subject} Project & Best Practices"
                ],
                "suggested_skill_level": "intermediate",
                "focus_areas": ["Core Concepts", "Code Optimization", "Practical Debugging"],
                "study_tip": "Spend 20 minutes coding active examples rather than passive reading.",
                "daily_challenge": f"Solve one practical coding challenge in {subject} today!",
                "motivational_message": "Consistency is the key to mastery. Keep up the great momentum! 🚀"
            }, indent=2)

        # 2. Quiz generation request (JSON array expected)
        if 'multiple choice quiz' in prompt_lower or 'correct_answer' in prompt:
            # Extract topic and subject
            topic_match = re.search(r'about "(.*?)"', prompt)
            topic = topic_match.group(1) if topic_match else "Core Concepts"
            subj_match = re.search(r'subject "([^"]+)"', prompt)
            subject = subj_match.group(1).strip() if subj_match else "General"
            is_tamil = 'consistently in tamil' in prompt_lower or 'tamil' in subject.lower() or 'தமிழ்' in prompt
            tech_keywords = ['python', 'code', 'programming', 'software', 'algorithm', 'web', 'database', 'sql', 'machine learning', 'computer']
            is_tech = any(k in f"{subject} {topic}".lower() for k in tech_keywords)

            if is_tamil:
                return json.dumps([
                    {
                        "question": f"{topic} குறித்த அடிப்படைக் கருத்து எதைப் பற்றி விளக்குகிறது?",
                        "options": [
                            f"A) {topic}-இன் இலக்கிய, வரலாற்று மற்றும் பண்பாட்டுச் சிறப்புகளை",
                            "B) கணினி வன்பொருள் இயக்க முறைமைகளை",
                            "C) நவீன தரவுத்தள நிரலாக்க மொழிகளை",
                            "D) மின்னணு சுற்று வடிவமைப்பு விதிகளை"
                        ],
                        "correct_answer": "A",
                        "explanation": f"{topic} என்பது {subject} பாடத்தில் முக்கிய இலக்கிய மற்றும் வரலாற்றுப் புரிதலை வழங்கும் பகுதியாகும்."
                    },
                    {
                        "question": f"{topic} படிக்கும்போது முதன்மையாகக் கவனிக்க வேண்டியது எது?",
                        "options": [
                            "A) தொடர்பற்ற கலைச்சொற்களை மனப்பாடம் செய்வது",
                            f"B) {topic}-இன் மூல நூல்கள், சான்றுகள் மற்றும் மையக் கருத்தை அறிவது",
                            "C) வரலாற்றுப் பின்னணியைப் புறக்கணிப்பது",
                            "D) மொழி இலக்கண விதிகளைத் தவிர்ப்பது"
                        ],
                        "correct_answer": "B",
                        "explanation": f"மூலச் சான்றுகளையும் மையக் கருத்தையும் அறிவது {topic} பற்றிய ஆழமான புரிதலுக்கு உதவும்."
                    },
                    {
                        "question": f"{subject} பாடத்தில் {topic} எவ்வாறு மதிப்பிடப்படுகிறது?",
                        "options": [
                            "A) தற்காலிகப் பொழுதுபோக்காக மட்டுமே",
                            "B) சான்றுகள் இல்லாத கற்பனையாக",
                            f"C) {subject} மரபு மற்றும் சிந்தனை வளர்ச்சியின் முக்கிய அடையாளமாக",
                            "D) பயன்பாடற்ற பழைய குறிப்பாக"
                        ],
                        "correct_answer": "C",
                        "explanation": f"{topic} தமிழ் மொழி, இலக்கியம் மற்றும் பண்பாட்டு மரபின் முக்கிய அங்கமாகும்."
                    },
                    {
                        "question": f"{topic} சார்ந்த எடுத்துக்காட்டுகளை ஆய்வு செய்வதன் பயன் என்ன?",
                        "options": [
                            "A) பாடத்தைப் பற்றிய குழப்பத்தை அதிகரிப்பது",
                            f"B) {topic}-இன் நடை, சொல்வளம் மற்றும் பொருள் ஆழத்தைத் தெளிவாக உணர்வது",
                            "C) மூலக் கருத்தை மாற்றி எழுதுவது",
                            "D) பயிற்சியை நிறுத்திவிடுவது"
                        ],
                        "correct_answer": "B",
                        "explanation": "சான்றுகளும் எடுத்துக்காட்டுகளும் கருத்தைத் தெளிவாகப் புரிந்துகொள்ள உதவுகின்றன."
                    },
                    {
                        "question": f"{topic} கற்றலை வலுப்படுத்த சிறந்த வழி எது?",
                        "options": [
                            "A) ஒருமுறை மட்டும் படித்து விட்டுவிடுவது",
                            f"B) முக்கியக் குறிப்புகளைச் சுருக்கி எழுதி, தொடர்புடைய எடுத்துக்காட்டுகளுடன் ஒப்பிட்டுப் பார்ப்பது",
                            "C) பொருள் அறியாமல் மனப்பாடம் செய்வது",
                            "D) பயிற்சி வினாக்களைத் தவிர்ப்பது"
                        ],
                        "correct_answer": "B",
                        "explanation": "குறிப்பெடுத்தலும் எடுத்துக்காட்டுகளுடன் ஒப்பிட்டுப் படிப்பதும் நினைவாற்றலையும் புரிதலையும் மேம்படுத்தும்."
                    }
                ], indent=2, ensure_ascii=False)

            if not is_tech:
                return json.dumps([
                    {
                        "question": f"What is the primary focus of studying {topic} in {subject}?",
                        "options": [
                            f"A) Understanding the core principles, context, and significance of {topic}",
                            "B) Configuring server hardware and network sockets",
                            "C) Writing low-level memory allocators",
                            "D) Compiling source code into binary executables"
                        ],
                        "correct_answer": "A",
                        "explanation": f"{topic} builds foundational understanding and analytical depth within {subject}."
                    },
                    {
                        "question": f"Which approach best strengthens mastery of {topic}?",
                        "options": [
                            "A) Memorizing isolated facts without context",
                            f"B) Analyzing primary examples, key themes, and conceptual connections in {topic}",
                            "C) Skipping foundational definitions",
                            "D) Avoiding review questions"
                        ],
                        "correct_answer": "B",
                        "explanation": f"Connecting core concepts with concrete {subject} examples ensures lasting comprehension."
                    },
                    {
                        "question": f"Why are authentic examples important when learning {topic}?",
                        "options": [
                            "A) They replace the need to understand core ideas",
                            "B) They distract from the main topic",
                            f"C) They illustrate how principles of {topic} apply in real {subject} contexts",
                            "D) They remove all nuance from the subject"
                        ],
                        "correct_answer": "C",
                        "explanation": f"Well-chosen examples bridge abstract concepts and real-world understanding in {subject}."
                    },
                    {
                        "question": f"What common mistake should learners avoid while studying {topic}?",
                        "options": [
                            "A) Reviewing key takeaways",
                            f"B) Relying on rote memorization while ignoring historical or conceptual context in {topic}",
                            "C) Taking structured study notes",
                            "D) Practicing with self-assessment quizzes"
                        ],
                        "correct_answer": "B",
                        "explanation": "Deep understanding requires grasping context and underlying reasoning, not just surface facts."
                    },
                    {
                        "question": f"What is a productive next step after reviewing {topic}?",
                        "options": [
                            "A) Never revisiting the material",
                            f"B) Summarizing the main themes of {topic} in your own words and testing recall",
                            "C) Discarding study notes immediately",
                            "D) Avoiding related topics in the subject"
                        ],
                        "correct_answer": "B",
                        "explanation": "Active recall and summarization reinforce long-term retention."
                    }
                ], indent=2)

            return json.dumps([
                {
                    "question": f"What is the primary role of {topic}?",
                    "options": [
                        f"A) Providing foundational structure and efficiency for {topic}",
                        "B) Deleting unused cache files from local disk",
                        "C) Compiling code strictly into machine language binaries",
                        "D) Managing hardware voltages on the CPU"
                    ],
                    "correct_answer": "A",
                    "explanation": f"{topic} is essential for establishing structured and efficient execution patterns in software."
                },
                {
                    "question": f"Which of the following best represents standard usage of {topic}?",
                    "options": [
                        "A) Ignoring errors and letting programs crash silently",
                        f"B) Applying modular and testable paradigms relevant to {topic}",
                        "C) Hardcoding credentials directly into source control",
                        "D) Disabling typing validation checks entirely"
                    ],
                    "correct_answer": "B",
                    "explanation": f"Best practices for {topic} focus on modularity, readability, and testability."
                },
                {
                    "question": f"When optimizing performance with {topic}, what should you prioritize?",
                    "options": [
                        "A) Infinite loops without terminating conditions",
                        "B) Increasing memory overhead without caching",
                        "C) Time complexity, resource allocation, and algorithmic efficiency",
                        "D) Disabling log outputs across the system"
                    ],
                    "correct_answer": "C",
                    "explanation": f"Efficiency in {topic} depends directly on algorithmic time complexity and smart resource management."
                },
                {
                    "question": f"Which common pitfall should developers avoid when working with {topic}?",
                    "options": [
                        "A) Writing clean documentation and docstrings",
                        f"B) Overcomplicating architectures and neglecting edge cases in {topic}",
                        "C) Using version control to track software releases",
                        "D) Writing automated unit tests"
                    ],
                    "correct_answer": "B",
                    "explanation": "Over-engineering and missing boundary conditions are the most frequent pitfalls."
                },
                {
                    "question": f"What is the recommended next step after understanding the basics of {topic}?",
                    "options": [
                        "A) Never review the code again",
                        f"B) Build an interactive mini-project applying {topic} with real data",
                        "C) Delete all previous learning notes",
                        "D) Switch immediately to unrelated technologies"
                    ],
                    "correct_answer": "B",
                    "explanation": "Active project development cements conceptual knowledge into practical capability."
                }
            ], indent=2)

        # 3. Quiz feedback generation
        if 'student scored' in prompt_lower:
            return "Solid attempt! Review the questions you missed and reinforce the core definitions before moving to the next topic. Keep practicing to build confidence!"

        # 4. Content generation request (Markdown)
        topic_match = re.search(r'about "([^"]+)" in ([^\n.]+)', prompt)
        topic = topic_match.group(1).strip() if topic_match else "Key Concepts"
        subject = topic_match.group(2).strip().rstrip('.') if topic_match else "General Education"

        is_tamil = 'consistently in tamil' in prompt_lower or 'tamil' in subject.lower() or 'தமிழ்' in prompt

        if is_tamil:
            return f"""# 📚 {topic} — விரிவான கற்றல் வழிகாட்டி

## 1. அறிமுகம் மற்றும் மையக் கருத்து
**{subject}** பாடப்பிரிவில் **{topic}** என்பது மொழி, இலக்கியம் மற்றும் பண்பாட்டு வரலாற்றைப் புரிந்துகொள்ள உதவும் மிக முக்கியமான பகுதியாகும். இதன் அடிப்படைக் கூறுகளையும் சூழலையும் தெளிவாக அறிந்துகொள்வது ஆழமான புலமைக்கு வழிவகுக்கும்.

---

## 2. முக்கியக் கருத்துகளும் சிறப்புகளும்
- **வரலாற்று மற்றும் இலக்கியப் பின்னணி:** {topic} உருவான காலம், சமுதாயச் சூழல் மற்றும் அதன் இலக்கிய மதிப்பு.
- **அடிப்படை அமைப்பு:** மையக் கருப்பொருள், நடை, சொல்வளம் மற்றும் வெளிப்பாட்டு முறைகள்.
- **பண்பாட்டு முக்கியத்துவம்:** தமிழ்ச் சமூகத்தின் வாழ்வியல், அறநெறி மற்றும் சிந்தனை மரபுகளைப் பிரதிபலிக்கும் தன்மை.

---

## 3. பொருத்தமான எடுத்துக்காட்டுகள் (இலக்கியம் / வரலாறு / சூழல்)
> **எடுத்துக்காட்டு 1 — இலக்கியச் சான்று மற்றும் பொருள்:**  
> **{topic}** தொடர்பான இலக்கியப் பாடல்களும் குறிப்புகளும் அக்கால மக்களின் வாழ்வியல், இயற்கை உணர்வு (அகம் / புறம்), மற்றும் அறச்சிந்தனைகளைத் தெளிவாக எடுத்துக்காட்டுகின்றன.

> **எடுத்துக்காட்டு 2 — வரலாற்று மற்றும் பண்பாட்டுப் பார்வை:**  
> {subject} மரபில் **{topic}** குறித்த கல்வெட்டுகள், செவ்வியல் நூல்கள் மற்றும் உரையாசிரியர்களின் விளக்கங்கள் அக்கால வரலாற்றை உறுதிப்படுத்தும் சான்றுகளாக விளங்குகின்றன.

> **எடுத்துக்காட்டு 3 — நடைமுறை மற்றும் கல்விப் பயன்பாடு:**  
> சொற்பொருள் ஆய்வு, ஒப்பீட்டு இலக்கியப் பார்வை மற்றும் கட்டுரை எழுதும் பயிற்சிகளில் **{topic}** பற்றிய தெளிவான சான்றுகளை மேற்கோள் காட்டுவது மதிப்பீட்டை உயர்த்தும்.

---

## 4. தவிர்க்க வேண்டிய பொதுவான தவறுகள்
- ❌ **சூழல் இல்லாமல் மனப்பாடம் செய்தல்:** பாடல் அல்லது கருத்தின் வரலாற்றுப் பின்னணியை உணர்ந்து படிக்க வேண்டும்.
- ❌ **சொற்பொருள் பிழைகள்:** பழைய இலக்கியச் சொற்களின் சரியான பொருளை உரை விளக்கத்துடன் சரிபார்க்க வேண்டும்.
- ✅ **தொடர் பயிற்சி:** முக்கியக் குறிப்புகளையும் மேற்கோள்களையும் தொகுத்துப் பயிற்சி செய்ய வேண்டும்.

---

## 5. முக்கியத் தொகுப்பு (Key Takeaways)
- ✅ **{topic}** என்பது **{subject}** பாடத்தின் அடிப்படைத் தூண்களில் ஒன்றாகும்.
- ✅ மூலச் சான்றுகள் மற்றும் எடுத்துக்காட்டுகளுடன் இணைத்துப் படிப்பதே சிறந்த முறையாகும்.
- ✅ உங்கள் புரிதலைச் சோதிக்க AI வினாடி-வினா (AI Quiz) பயிற்சியை மேற்கொள்ளுங்கள்!
"""

        # Check if technical/coding subject vs general/humanities/language
        tech_keywords = ['python', 'code', 'programming', 'software', 'algorithm', 'web', 'database', 'sql', 'backend', 'frontend', 'developer', 'computer']
        is_tech = any(k in f"{subject} {topic}".lower() for k in tech_keywords)

        if is_tech:
            practical_section = f"""```python
# Practical implementation example for {topic}
def execute_task(input_data: list) -> dict:
    \"\"\"
    Demonstrates practical processing for {topic}.
    \"\"\"
    if not input_data:
        return {{"status": "empty", "result": None}}

    # Process and transform the data
    processed = [item.strip().title() for item in input_data if isinstance(item, str)]
    return {{
        "status": "success",
        "count": len(processed),
        "items": processed
    }}

# Example execution
demo_input = ["alpha", "beta", "gamma"]
print(execute_task(demo_input))
```"""
        else:
            practical_section = f"""> **Practical Context & Core Insight:**  
> In studying **{subject}**, **{topic}** provides the essential conceptual framework. Analyzing its structure, historical development, and practical modern context helps learners build deep, lasting understanding.

### Practical Application & Analysis
- **Core Analysis:** Understanding primary themes, structural rules, and critical nuances in **{topic}**.
- **Contextual Integration:** How **{topic}** connects with broader topics across **{subject}**.
- **Real-World Relevance:** Daily communication, academic scholarship, and critical analytical thinking."""

        return f"""# 📚 Comprehensive Guide: {topic}

## 1. Overview & Core Philosophy
In **{subject}**, mastering **{topic}** represents a fundamental step toward building deep conceptual mastery and practical capability. Whether applying it in academic contexts, competitive examinations, or real-world practice, {topic} provides the building blocks needed to excel.

---

## 2. Key Concepts & Principles

### Foundational Principles
- **Clarity & Structure:** Systematic understanding of core definitions and foundational elements.
- **Predictability & Rules:** Consistent principles, patterns, and conventions governing {topic}.
- **Applied Value:** Connecting theoretical knowledge with practical, actionable examples.

{practical_section}

---

## 3. Real-World Applications & Workflow
1. **Foundational Synthesis:** Connecting core principles of {subject} with practical problem-solving.
2. **Analytical Thinking:** Evaluating real-world examples, texts, or scenarios systematically.
3. **Mastery & Retention:** Active recall, periodic review, and practical application.

---

## 4. Common Pitfalls & How to Avoid Them
- ❌ **Superficial Memorization:** Focus on understanding underlying principles rather than rote learning.
- ❌ **Neglecting Core Nuances:** Pay attention to special rules, edge cases, and context-specific usage.
- ✅ **Active Practice:** Regularly test your understanding through exercises, quizzes, and summaries.

---

## 5. Key Takeaways
- ✅ **{topic}** is integral to mastering **{subject}**.
- ✅ Break complex topics down into small, digestible conceptual units.
- ✅ Test your understanding by taking the interactive quiz for this lesson!
"""
