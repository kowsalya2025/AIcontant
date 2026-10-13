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
    Primary: Google Gemini (gemini-2.5-flash / gemini-1.5-flash)
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
                    'temperature': 0.7,
                    'top_p': 0.95,
                    'top_k': 40,
                    'max_output_tokens': 4096,
                }
            )
            logger.info("Gemini legacy SDK initialized.")
        except Exception as e:
            logger.error(f"Failed to initialize legacy Gemini SDK: {e}")

    def generate(self, prompt: str) -> str:
        """
        Generate text from a prompt.
        If the API call fails or no key is present, falls back gracefully.
        """
        # Try modern google.genai SDK
        if self.use_new_sdk and self.client:
            for model_name in ['gemini-2.5-flash', 'gemini-1.5-flash']:
                try:
                    response = self.client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                    )
                    if response and response.text:
                        return response.text.strip()
                except Exception as e:
                    logger.warning(f"google.genai call with {model_name} failed: {e}")

        # Try legacy SDK
        if self.legacy_model:
            try:
                response = self.legacy_model.generate_content(prompt)
                if response and response.text:
                    return response.text.strip()
            except Exception as e:
                logger.warning(f"Legacy Gemini generation failed: {e}")

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
        topic = topic_match.group(1) if topic_match else "Key Programming Concepts"
        subject = topic_match.group(2) if topic_match else "Computer Science"

        return f"""# 📚 Comprehensive Guide: {topic}

## 1. Overview & Core Philosophy
In **{subject}**, mastering **{topic}** represents a fundamental step toward building reliable, performant, and scalable applications. Whether developing distributed systems, data workflows, or interactive user interfaces, {topic} provides the building blocks needed to solve real-world problems.

---

## 2. Key Concepts & Architecture

### Foundational Principles
- **Modularity:** Separating concerns ensures maintainability and simplifies unit testing.
- **Predictability:** Consistent handling of inputs and edge cases prevents unexpected runtime exceptions.
- **Resource Efficiency:** Proper memory and computational management ensures high throughput.

```python
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
```

---

## 3. Real-World Applications & Workflow
1. **Data Pipeline Integration:** Transforming inputs into standardized schema representations.
2. **Business Logic Layer:** Encapsulating domain rules away from transport mechanisms.
3. **Production Reliability:** Adding logging, timeouts, and fallback policies.

---

## 4. Common Pitfalls & How to Avoid Them
- ❌ **Unchecked Boundary Cases:** Always validate `None`, empty lists, or unexpected network failures.
- ❌ **Premature Optimization:** Focus first on clean readability and automated test coverage.
- ✅ **Idiomatic Patterns:** Adhere to established language idioms and clear naming conventions.

---

## 5. Key Takeaways
- ✅ **{topic}** is integral to high-quality **{subject}** workflows.
- ✅ Break complex implementations down into small, easily verifiable functions.
- ✅ Test your understanding by attempting the interactive quiz for this lesson!
"""
