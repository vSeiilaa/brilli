# app/utils.py

from flask import url_for
import re
import json
import os
import time


def process_image_tags(text):
    """
    Replace [IMG]filename.png[/IMG] tags with proper HTML img elements
    using Flask's url_for
    """
    def replace_tag(match):
        filename = match.group(1)
        image_url = url_for('static', filename=f'images/{filename}')
        return f'<img src="{image_url}" alt="{filename}" class="content-image">'

    # Use regex to find all [IMG]filename.png[/IMG] patterns and replace them
    processed_text = re.sub(r'\[IMG\](.*?)\[/IMG\]', replace_tag, text)
    return processed_text

def process_content(content):
    """
    Process content that might be either a string or a list,
    handling image tags in either case
    """
    if isinstance(content, list):
        # Process each line and join them with line breaks
        processed_lines = [process_image_tags(line) for line in content]
        return '<br>'.join(processed_lines)
    else:
        # If it's not a list, process it as a single string
        return process_image_tags(content)

def parse_outline(outline):
    # Parse the JSON outline
    if outline is None:
        print("Warning: Received None outline")
        return []

    if not isinstance(outline, str):
        print(f"Warning: Outline is not a string, got {type(outline)}")
        return []

    try:
        outline_data = json.loads(outline)
        lessons = outline_data.get('lessons', [])
        return lessons
    except json.JSONDecodeError as e:
        print(f"Error parsing outline JSON: {e}")
        print(f"Received outline: {outline}")
        return []
    except Exception as e:
        print(f"Unexpected error parsing outline: {e}")
        return []

def save_course_content(topic, course_content, outline_data):
    # Create a unique course ID
    course_id = f"user_course_{int(time.time())}"

    # Save the course content to a JSON file
    course_dir = f'content/{course_id}'
    os.makedirs(course_dir, exist_ok=True)

    topic = topic.title()

    # Get description from outline_data or use default
    description = outline_data.get('description', "Comprehensive course on " + topic)

    # Default emojis if none provided
    emoji_cover = outline_data.get('emoji_cover', "📚✨💡")

    # Get the lesson emoji covers from outline_data
    lesson_emoji_covers = {
        lesson['title']: lesson.get('emoji_cover', "💡💡💡")
        for lesson in outline_data.get('lessons', [])
    }

    # Save each lesson as a separate JSON file
    for idx, lesson in enumerate(course_content):
        lesson_id = f'lesson{idx+1}'
        lesson_path = os.path.join(course_dir, f'{lesson_id}.json')
        with open(lesson_path, 'w', encoding='utf-8') as f:
            json.dump(lesson['sections'], f, ensure_ascii=False, indent=4)

    # Update courses.json to include the new course
    courses_json_path = 'content/courses.json'
    with open(courses_json_path, 'r+', encoding='utf-8') as f:
        courses = json.load(f)
        new_course = {
                    "id": course_id,
                    "title": topic,
                    "description": description,
                    "emoji_cover": emoji_cover,
                    "lessons": [{
                        "id": f"lesson{idx+1}",
                        "title": lesson['title'],
                        "description": "",
                        "emoji_cover": lesson_emoji_covers.get(lesson['title'], "✨✨✨")
                    } for idx, lesson in enumerate(course_content)]
                }
        courses.append(new_course)
        f.seek(0)
        json.dump(courses, f, ensure_ascii=False, indent=4)
        f.truncate()

    return course_id

def render_course_outline(outline):
    # Parse the outline JSON and render it into HTML

    if outline is None:
        return '<p class="error">Unable to generate course outline. Please try again.</p>'

    lessons = parse_outline(outline)

    if not lessons:
        return '<p class="error">No lessons found in the outline. This might be due to API limits or an error in generation.</p>'

    html_output = '<ol>'
    try:
        for lesson in lessons:
            html_output += f"<li><strong>{lesson.get('title', 'Untitled Lesson')}</strong><ul>"
            for section_title in lesson.get('sections', []):
                html_output += f"<li>{section_title}</li>"
            html_output += "</ul></li>"
        html_output += '</ol>'
    except Exception as e:
        print(f"Error rendering outline: {e}")
        return '<p class="error">Error rendering course outline. Please try again.</p>'

    return html_output
