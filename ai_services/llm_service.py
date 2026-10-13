"""
LLM Service — Gemini 1.5 Flash (Free Tier)
Primary AI engine for content generation, quiz creation, and feedback.
"""
import os
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class LLMService:
    """
    Abstraction layer for LLM calls.
    Primary: Google Gemini 1.5 Flash (free tier)
    Fallback: Simple template-based generation
    """

    def __init__(self):
        self.model = None
        self._initialize()

    def _initialize(self):
        """Initialize Gemini client."""
        api_key = getattr(settings, 'GEMINI_API_KEY', '') or os.getenv('GEMINI_API_KEY', '')
        if not api_key or api_key == 'your_gemini_api_key_here':
            logger.warning("⚠️  No Gemini API key found. Using fallback mode.")
            return
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(
                model_name='gemini-2.5-flash',
                generation_config={
                    'temperature': 0.7,
                    'top_p': 0.95,
                    'top_k': 40,
                    'max_output_tokens': 4096,
                }
            )
            logger.info("✅ Gemini 2.5 Flash initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {e}")
            self.model = None

    def generate(self, prompt: str) -> str:
        """
        Generate text from a prompt.
        Returns generated string or empty string on failure.
        """
        if not self.model:
            return self._fallback_generate(prompt)

        try:
            response = self.model.generate_content(prompt)
            if response and response.text:
                return response.text.strip()
            return ''
        except Exception as e:
            logger.error(f"Gemini generation error: {e}")
            return self._fallback_generate(prompt)

    def _fallback_generate(self, prompt: str) -> str:
        """
        Fallback when no API key is configured.
        Returns a helpful demo message.
        """
        if 'quiz' in prompt.lower() or 'question' in prompt.lower():
            return '''[
  {
    "question": "What is a variable in Python?",
    "options": ["A) A fixed constant value", "B) A container for storing data values", "C) A type of function", "D) A loop construct"],
    "correct_answer": "B",
    "explanation": "A variable in Python is a named container that stores a data value. Unlike other languages, Python variables don't need explicit declaration."
  },
  {
    "question": "Which keyword is used to define a function in Python?",
    "options": ["A) function", "B) define", "C) def", "D) func"],
    "correct_answer": "C",
    "explanation": "The 'def' keyword is used to define a function in Python, followed by the function name and parentheses."
  },
  {
    "question": "What does the 'len()' function return?",
    "options": ["A) The last element of a list", "B) The number of elements in an object", "C) The largest element", "D) The memory address"],
    "correct_answer": "B",
    "explanation": "len() returns the number of items (length) in an object such as a string, list, or tuple."
  },
  {
    "question": "How do you create a list in Python?",
    "options": ["A) {1, 2, 3}", "B) (1, 2, 3)", "C) [1, 2, 3]", "D) <1, 2, 3>"],
    "correct_answer": "C",
    "explanation": "Lists in Python are created using square brackets []. They are mutable, ordered collections."
  },
  {
    "question": "What is the output of print(2 ** 3)?",
    "options": ["A) 6", "B) 5", "C) 8", "D) 9"],
    "correct_answer": "C",
    "explanation": "The ** operator in Python means exponentiation (power). 2 ** 3 means 2 to the power of 3, which equals 8."
  }
]'''

        # Generic content fallback
        return """## 🤖 Demo Mode — Configure Gemini API Key

> **Note**: This is sample content. Add your **free** Gemini API key to `.env` to get personalized AI-generated content.

## How to Get a Free Gemini API Key

1. Visit [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Sign in with your Google account
3. Click **"Create API Key"** — it's completely **free**!
4. Copy the key and add it to your `.env` file:
   ```
   GEMINI_API_KEY=your_key_here
   ```
5. Restart the server

## Sample Content: Python Variables

### What are Variables?
Variables are **named containers** that store data values in memory. In Python, you don't need to declare a variable type — Python infers it automatically.

### Syntax
```python
# Creating variables
name = "Alice"          # String
age = 25               # Integer
height = 5.6           # Float
is_student = True      # Boolean
```

### Key Rules
- Variable names must start with a **letter** or **underscore**
- Cannot start with a number
- Case-sensitive (`age` ≠ `Age`)
- Cannot use Python **reserved keywords**

### Multiple Assignment
```python
x = y = z = 0          # Same value
a, b, c = 1, 2, 3      # Different values
```

### Key Takeaways
- ✅ Python uses **dynamic typing** — no type declaration needed
- ✅ Variables are **references** to objects in memory
- ✅ Use **descriptive names** for readable code
- ✅ Follow **snake_case** naming convention in Python
"""
