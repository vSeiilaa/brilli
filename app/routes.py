# app/routes.py

from flask import render_template, session, redirect, url_for, request, jsonify, abort, flash
from app import app
from app.forms import AnswerForm, CreateCourseForm, FeedbackForm, ConfirmForm
from app.utils import process_content, parse_outline, save_course_content, render_course_outline
from ai import grade_answer, generate_course_outline, generate_full_course
import json
import os

@app.route('/', methods=['GET'])
def show_courses():
    # Load the list of courses
    with open('content/courses.json', 'r', encoding='utf-8') as f:
        courses = json.load(f)
    return render_template('courses.html', courses=courses)

@app.route('/course/<course_id>', methods=['GET'])
def show_lessons(course_id):
    # Load the list of courses
    with open('content/courses.json', 'r', encoding='utf-8') as f:
        courses = json.load(f)

    # Find the selected course
    course = next((course for course in courses if course['id'] == course_id), None)
    if not course:
        abort(404)

    return render_template(
        'lessons.html',
        course=course,
        back_url=url_for('show_courses'),
        button_text='↖️ Go Back'
    )

@app.route('/course/<course_id>/lesson/<lesson_id>', methods=['GET'])
def lesson(course_id, lesson_id):
    # Clear previous session data
    session.clear()
    session['progress'] = 0  # Index of the current section
    session['feedback'] = {}
    session['course_id'] = course_id
    session['lesson_id'] = lesson_id

    # Load the lesson data
    lesson_path = f'content/{course_id}/{lesson_id}.json'
    if not os.path.exists(lesson_path):
        abort(404)
    with open(lesson_path, 'r', encoding='utf-8') as f:
        course_sections = json.load(f)

    forms = {}

    # Prepare the sections to display
    sections_to_display = course_sections[:session['progress'] + 1]

    # Process image tags in all sections
    for section in sections_to_display:
        # Process both theory and question content
        section['section_title'] = process_content(section['section_title'])
        section['theory'] = process_content(section['theory'])
        section['question'] = process_content(section['question'])

    # Create forms for each section displayed
    for idx in range(len(sections_to_display)):
        forms[idx] = AnswerForm()

    # Calculate progress percentage
    progress_percentage = (session['progress'] / len(course_sections)) * 100

    return render_template(
        'course.html',
        sections=sections_to_display,
        forms=forms,
        feedback=session.get('feedback', {}),
        progress=session['progress'],
        total_sections=len(course_sections),
        progress_percentage=progress_percentage,
        back_url=url_for('show_lessons', course_id=course_id),
        button_text='↖️ Go Back'
    )

@app.route('/submit_answer', methods=['POST'])
def submit_answer():
    # Retrieve course and lesson IDs from the session
    course_id = session.get('course_id')
    lesson_id = session.get('lesson_id')

    if not course_id or not lesson_id:
        return jsonify({'error': 'Course or lesson not selected'}), 400

    # Load the lesson data
    lesson_path = f'content/{course_id}/{lesson_id}.json'
    if not os.path.exists(lesson_path):
        return jsonify({'error': 'Lesson data not found'}), 400

        # Load the list of courses to find the next lesson
    with open('content/courses.json', 'r', encoding='utf-8') as f:
        courses = json.load(f)

    # Find current course and lesson indices
    course = next((c for c in courses if c['id'] == course_id), None)
    if not course:
        return jsonify({'error': 'Course not found'}), 400

    lesson_ids = [lesson['id'] for lesson in course['lessons']]
    current_lesson_index = lesson_ids.index(lesson_id)

    # Determine if there is a next lesson
    if current_lesson_index + 1 < len(lesson_ids):
        next_lesson_id = lesson_ids[current_lesson_index + 1]
        next_lesson_url = url_for('lesson', course_id=course_id, lesson_id=next_lesson_id)
    else:
        next_lesson_url = None  # No more lessons

    with open(lesson_path, 'r', encoding='utf-8') as f:
        course_sections = json.load(f)

    try:
        section_index = int(request.form.get('section_index', 0))
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid section index'}), 400

    form = AnswerForm(request.form)
    feedback_type = ''
    feedback_message = ''
    updated_section_html = ''
    new_section_html = ''
    completion_message = ''

    if form.validate():
        user_answer = form.answer.data.strip()
        section = course_sections[section_index]
        context = section.get('theory', '')
        question = section.get('question', '')
        is_correct, comment = grade_answer(context, question, user_answer)

        # Initialize feedback dict if it doesn't exist
        if 'feedback' not in session:
            session['feedback'] = {}

        # Store the new feedback
        session['feedback'][str(section_index)] = {
            'type': 'correct' if is_correct else 'incorrect',
            'message': comment
        }
        session.modified = True

        if is_correct:
            feedback_type = 'correct'
            feedback_message = comment
            if session['progress'] == section_index:
                session['progress'] += 1

            # Process content for the updated section
            section_processed = section.copy()
            section_processed['section_title'] = process_content(section_processed['section_title'])
            section_processed['theory'] = process_content(section_processed['theory'])
            section_processed['question'] = process_content(section_processed['question'])

            # Render the updated current section (without the form)
            updated_section_html = render_template(
                'section.html',
                section=section_processed,
                index=section_index,
                form=None,
                feedback_type=feedback_type,
                feedback_message=feedback_message,
                progress=session['progress'],
                total_sections=len(course_sections),
                feedback=session.get('feedback', {})
            )

            # Check if the course is completed
            if session['progress'] >= len(course_sections):
                completion_message = render_template(
                    'completion_message.html',
                    next_lesson_url=next_lesson_url
                )
            else:
                # Process content for the next section
                next_section = course_sections[session['progress']].copy()
                next_section['section_title'] = process_content(next_section['section_title'])
                next_section['theory'] = process_content(next_section['theory'])
                next_section['question'] = process_content(next_section['question'])

                new_form = AnswerForm()
                new_section_html = render_template(
                    'section.html',
                    section=next_section,
                    index=session['progress'],
                    form=new_form,
                    feedback_type='',
                    feedback_message='',
                    progress=session['progress'],
                    total_sections=len(course_sections),
                    feedback=session.get('feedback', {})
                )
        else:
            feedback_type = 'incorrect'
            feedback_message = comment
            # Process content for the current section
            section_processed = section.copy()
            section_processed['section_title'] = process_content(section_processed['section_title'])
            section_processed['theory'] = process_content(section_processed['theory'])
            section_processed['question'] = process_content(section_processed['question'])

            # Re-render the current section with feedback
            updated_section_html = render_template(
                'section.html',
                section=section_processed,
                index=section_index,
                form=form,
                feedback_type=feedback_type,
                feedback_message=feedback_message,
                progress=session['progress'],
                total_sections=len(course_sections),
                feedback=session.get('feedback', {})
            )
    else:
        feedback_type = 'incorrect'
        feedback_message = 'Please enter an answer.'
        # Process content for the current section
        section = course_sections[section_index].copy()
        section['section_title'] = process_content(section['section_title'])
        section['theory'] = process_content(section['theory'])
        section['question'] = process_content(section['question'])

        # Re-render the current section with feedback
        updated_section_html = render_template(
            'section.html',
            section=section,
            index=section_index,
            form=form,
            feedback_type=feedback_type,
            feedback_message=feedback_message,
            progress=session['progress'],
            total_sections=len(course_sections),
            feedback=session.get('feedback', {})
        )

    # Calculate progress percentage
    progress_percentage = (session['progress'] / len(course_sections)) * 100

    response = {
        'feedback_type': feedback_type,
        'section_index': section_index,
        'updated_section_html': updated_section_html,
        'new_section_html': new_section_html,
        'completion_message': completion_message,
        'progress_percentage': progress_percentage
    }

    return jsonify(response)

@app.route('/reset')
def reset():
    session.clear()
    return redirect(url_for('show_courses'))

@app.route('/course_complete')
def course_complete():
    course_id = session.get('course_id')
    if not course_id:
        return redirect(url_for('show_courses'))

    # Load the list of courses to get the course title
    with open('content/courses.json', 'r', encoding='utf-8') as f:
        courses = json.load(f)

    course = next((c for c in courses if c['id'] == course_id), None)
    if not course:
        return redirect(url_for('show_courses'))

    return render_template('course_complete.html', course_title=course['title'])


@app.route('/create_course', methods=['GET', 'POST'])
def create_course():
    form = CreateCourseForm()
    if form.validate_on_submit() and form.generate_button.data:  # Only process if generate button was clicked
        topic = form.topic.data
        num_lessons = int(form.num_lessons.data)

        # Generate course outline using AI
        outline = generate_course_outline(topic, num_lessons)

        if outline is None:
            flash('Unable to generate course outline. This might be due to API limits. Please try again later.', 'error')
            return redirect(url_for('create_course'))

        # Save outline and user inputs in session
        session['outline'] = outline
        session['topic'] = topic
        session['num_lessons'] = num_lessons

        # Render the outline for display
        outline_html = render_course_outline(outline)

        feedback_form = FeedbackForm()
        confirm_form = ConfirmForm()

        return render_template('course_outline.html',
            outline_html=outline_html,
            feedback_form=feedback_form,
            confirm_form=confirm_form,
            back_url=url_for('show_courses'),
            button_text='↖️ Go Back'
        )
    return render_template(
        'create_course.html',
        form=form,
        back_url=url_for('show_courses'),
        button_text='↖️ Go Back'
    )

@app.route('/regenerate_outline', methods=['POST'])
def regenerate_outline():
    feedback_form = FeedbackForm()
    if feedback_form.validate_on_submit():
        feedback = feedback_form.feedback.data
        topic = session.get('topic')
        num_lessons = session.get('num_lessons')

        # Regenerate the outline with feedback
        outline = generate_course_outline(topic, num_lessons, feedback=feedback)

        # Update the outline in session
        session['outline'] = outline

        # Render the updated outline
        outline_html = render_course_outline(outline)

        confirm_form = ConfirmForm()

        return render_template('course_outline.html',
            outline_html=outline_html,
            feedback_form=feedback_form,
            confirm_form=confirm_form,
            back_url=url_for('show_courses'),
            button_text='↖️ Go Back')
    else:
        # If validation fails, redirect back with error
        flash('Sorry! Failed to generate course outline. Please try again later')
        return redirect(url_for('create_course'))


@app.route('/confirm_course_creation', methods=['POST'])
def confirm_course_creation():
    confirm_form = ConfirmForm()
    if confirm_form.validate_on_submit():
        topic = session.get('topic')
        outline = session.get('outline')

        if not topic or not outline:
            flash('Missing course information. Please start over.', 'error')
            return redirect(url_for('create_course'))

        try:
            # Parse the outline to extract lessons and sections
            outline_data = json.loads(outline)
            # Parse the outline to extract lessons and sections
            lessons = parse_outline(outline)

            # Generate full course content
            course_content = generate_full_course(topic, lessons)

            if course_content is None:
                flash('Failed to generate course content. Please try again.', 'error')
                return redirect(url_for('create_course'))

            # Save the course content
            course_id = save_course_content(topic, course_content, outline_data)

            # Clear session variables related to course creation
            session.pop('outline', None)
            session.pop('topic', None)
            session.pop('num_lessons', None)

            return redirect(url_for('show_lessons', course_id=course_id))


        except Exception as e:
            print(f"Error in confirm_course_creation: {e}")
            flash('An error occurred while creating the course. Please try again.', 'error')
            return redirect(url_for('create_course'))
    else:
        return redirect(url_for('create_course'))
