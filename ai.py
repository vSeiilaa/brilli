import json
from typing import Dict, List, Optional, Tuple
import google.generativeai as genai
from openai import OpenAI
from config import GENAI_API_KEY, OPENAI_API_KEY, DELIMITER

# Initialize AI clients
genai.configure(api_key=GENAI_API_KEY)
openai_client = OpenAI(api_key=OPENAI_API_KEY)


def parse_json_response(response_text: str) -> Dict:
    """Extract and parse JSON from AI response text."""
    try:
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        json_str = response_text[json_start:json_end]
        return json.loads(json_str)
    except Exception as e:
        print(f"Error parsing JSON response: {e}")
        return {}


def get_completion_from_messages(messages, model="gpt-4o") -> str:
    """Get completion from OpenAI API."""
    try:
        response = openai_client.chat.completions.create(
            model=model,
            messages=messages
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error getting completion: {e}")
        return ""

# grading.py
def load_grading_template() -> str:
    """Load the grading prompt template from file."""
    try:
        with open('grade_answer.txt', 'r') as f:
            return f.read()
    except Exception as e:
        print(f"Error loading grading template: {e}")
        return ""


def grade_answer(context: str, question: str, answer: str) -> Tuple[bool, str]:
    """Grade a student's answer using AI."""
    prompt_template = load_grading_template()
    prompt = prompt_template.format(
        context=context,
        question=question,
        answer=answer
    )

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=150,
                temperature=1,
            ),
        )

        result = parse_json_response(response.text.strip())
        return result.get('is_correct', False), result.get('comment', '')

    except Exception as e:
        print(f"Error in grade_answer: {e}")
        return False, "Sorry, there was an error processing your answer."

def build_outline_prompt(topic: str, num_lessons: int, feedback: Optional[str] = None) -> str:
    """Build the prompt for course outline generation."""
    prompt = f"""
    As an expert teacher, create a JSON course outline for a course on '{topic}' with {num_lessons} lessons.
    Include a brief 5-10 word description.
    Based on the{topic} and the description write 3 emojis that describe the course.
    For each lesson, also provide 3 relevant emojis that represent its content.
    Return ONLY valid JSON in the following format, with no additional text:
    {{
        "description": "Brief compelling description of the course",
        "emoji_cover": "☕️ ✨ 🌍",
        "lessons": [
            {{
                "title": "Lesson 1: Introduction",
                "emoji_cover": "📚 🔍 💡",
                "sections": [
                    "Basic Concepts",
                    "Core Principles"
                ]
            }}
        ]
    }}
    """
    if feedback:
        prompt += f"\nRemake the outline while considering this feedback: {feedback}"
    return prompt

def generate_course_outline(topic: str, num_lessons: int, feedback: Optional[str] = None) -> Optional[str]:
    """Generate a course outline using AI."""
    prompt = build_outline_prompt(topic, num_lessons, feedback)

    try:
        model = genai.GenerativeModel("gemini-1.5-pro")
        response = model.generate_content(prompt)

        if not response or not response.text:
            print("Empty response from AI model")
            return None

        outline = parse_json_response(response.text.strip())

        if not outline.get('lessons'):
            print("No lessons found in outline")
            return None

        return json.dumps(outline)

    except Exception as e:
        print(f"Error generating course outline: {e}")
        return None

def build_section_prompt(topic: str, lesson_title: str, section_title: str) -> List[Dict]:
    """Build the prompt for section content generation."""
    prompt = f"""
    As an expert teacher, write a lesson content for a section titled '{section_title}' in the lesson '{lesson_title}' for a course on '{topic}'.
    Make sure to add empty "" between the paragraphs to make text easier to read.
    Return ONLY valid JSON in the following format, with no additional text:
    {{
        "section_title": "{section_title}",
        "theory": [
            "First paragraph of theory",
            "",
            "Second paragraph of theory"
        ],
        "question": "A practice question for students",
        "answer": "The one or two word answer to the question"
    }}
    """

    return [
        {'role': 'system', 'content': prompt},
        {'role': 'user', 'content': f"{DELIMITER}{lesson_title}{DELIMITER}{section_title}{DELIMITER}{topic}{DELIMITER}"}
    ]

def generate_section_content(topic: str, lesson_title: str, section_title: str) -> Optional[Dict]:
    """Generate content for a single section."""
    messages = build_section_prompt(topic, lesson_title, section_title)

    try:
        response = get_completion_from_messages(messages)
        result = parse_json_response(response)

        required_keys = ['section_title', 'theory', 'question']
        if all(key in result for key in required_keys):
            return result
        else:
            print(f"Missing required keys in section content for '{section_title}'")
            return None

    except Exception as e:
        print(f"Error generating section content: {e}")
        return None

def generate_full_course(topic: str, lessons: List[Dict]) -> Optional[List[Dict]]:
    """Generate full course content including all lessons and sections."""
    course_content = []

    for lesson in lessons:
        lesson_content = {
            'title': lesson['title'],
            'sections': []
        }

        for section_title in lesson.get('sections', []):
            section_content = generate_section_content(
                topic,
                lesson['title'],
                section_title
            )
            if section_content:
                lesson_content['sections'].append(section_content)

        if lesson_content['sections']:
            course_content.append(lesson_content)

    return course_content if course_content else None
