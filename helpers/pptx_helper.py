import logging
import pathlib
import re
import tempfile

from typing import List, Tuple

import json5
import pptx
from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE

from global_config import GlobalConfig


# English Metric Unit (used by PowerPoint) to inches
EMU_TO_INCH_SCALING_FACTOR = 1.0 / 914400
INCHES_1_5 = pptx.util.Inches(1.5)
INCHES_1 = pptx.util.Inches(1)
INCHES_0_5 = pptx.util.Inches(0.5)
INCHES_0_4 = pptx.util.Inches(0.4)
INCHES_0_3 = pptx.util.Inches(0.3)

STEP_BY_STEP_PROCESS_MARKER = '>> '

PATTERN = re.compile(r"^slide[ ]+\d+:", re.IGNORECASE)
SAMPLE_JSON_FOR_PPTX = '''
{
    "title": "Understanding AI",
    "slides": [
        {
            "heading": "Introduction",
            "bullet_points": [
                "Brief overview of AI",
                [
                    "Importance of understanding AI"
                ]
            ]
        }
    ]
}
'''

logger = logging.getLogger(__name__)


def remove_slide_number_from_heading(header: str) -> str:
    """
    Remove the slide number from a given slide header.

    :param header: The header of a slide.
    """

    if PATTERN.match(header):
        idx = header.find(':')
        header = header[idx + 1:]

    return header


def generate_powerpoint_presentation(
        structured_data: str,
        slides_template: str,
        output_file_path: pathlib.Path
) -> List:
    """
    Create and save a PowerPoint presentation file containing the content in JSON format.

    :param structured_data: The presentation contents as "JSON" (may contain trailing commas).
    :param slides_template: The PPTX template to use.
    :param output_file_path: The path of the PPTX file to save as.
    :return A list of presentation title and slides headers.
    """

    # The structured "JSON" might contain trailing commas, so using json5
    parsed_data = json5.loads(structured_data)

    logger.debug(
        '*** Using PPTX template: %s',
        GlobalConfig.PPTX_TEMPLATE_FILES[slides_template]['file']
    )
    presentation = pptx.Presentation(GlobalConfig.PPTX_TEMPLATE_FILES[slides_template]['file'])
    slide_width_inch, slide_height_inch = _get_slide_width_height_inches(presentation)

    # The title slide
    title_slide_layout = presentation.slide_layouts[0]
    slide = presentation.slides.add_slide(title_slide_layout)
    title = slide.shapes.title
    subtitle = slide.placeholders[1]
    title.text = parsed_data['title']
    logger.info(
        'PPT title: %s | #slides: %d',
        title.text, len(parsed_data['slides'])
    )
    subtitle.text = 'by Myself and SlideDeck AI :)'
    all_headers = [title.text, ]

    # Add content in a loop
    for a_slide in parsed_data['slides']:
        is_processing_done = _handle_double_col_layout(
            presentation=presentation,
            slide_json=a_slide,
            slide_width_inch=slide_width_inch,
            slide_height_inch=slide_height_inch
        )

        if not is_processing_done:
            is_processing_done = _handle_step_by_step_process(
                presentation=presentation,
                slide_json=a_slide,
                slide_width_inch=slide_width_inch,
                slide_height_inch=slide_height_inch
            )

        if not is_processing_done:
            _handle_default_display(
                presentation=presentation,
                slide_json=a_slide,
                slide_width_inch=slide_width_inch,
                slide_height_inch=slide_height_inch
            )

    # The thank-you slide
    last_slide_layout = presentation.slide_layouts[0]
    slide = presentation.slides.add_slide(last_slide_layout)
    title = slide.shapes.title
    title.text = 'Thank you!'

    presentation.save(output_file_path)

    return all_headers


def get_flat_list_of_contents(items: list, level: int) -> List[Tuple]:
    """
    Flatten a (hierarchical) list of bullet points to a single list containing each item and
    its level.

    :param items: A bullet point (string or list).
    :param level: The current level of hierarchy.
    :return: A list of (bullet item text, hierarchical level) tuples.
    """

    flat_list = []

    for item in items:
        if isinstance(item, str):
            flat_list.append((item, level))
        elif isinstance(item, list):
            flat_list = flat_list + get_flat_list_of_contents(item, level + 1)

    return flat_list


def _handle_default_display(
        presentation: pptx.Presentation,
        slide_json: dict,
        slide_width_inch: float,
        slide_height_inch: float
):
    """
    Display a list of text in a slide.

    :param presentation: The presentation object.
    :param slide_json: The content of the slide as JSON data.
    :param slide_width_inch: The width of the slide in inches.
    :param slide_height_inch: The height of the slide in inches.
    """

    bullet_slide_layout = presentation.slide_layouts[1]
    slide = presentation.slides.add_slide(bullet_slide_layout)

    shapes = slide.shapes
    title_shape = shapes.title
    body_shape = shapes.placeholders[1]
    title_shape.text = remove_slide_number_from_heading(slide_json['heading'])
    text_frame = body_shape.text_frame

    # The bullet_points may contain a nested hierarchy of JSON arrays
    # In some scenarios, it may contain objects (dictionaries) because the LLM generated so
    #  ^ The second scenario is not covered

    flat_items_list = get_flat_list_of_contents(slide_json['bullet_points'], level=0)

    for idx, an_item in enumerate(flat_items_list):
        if idx == 0:
            text_frame.text = an_item[0].removeprefix(STEP_BY_STEP_PROCESS_MARKER)
        else:
            paragraph = text_frame.add_paragraph()
            paragraph.text = an_item[0].removeprefix(STEP_BY_STEP_PROCESS_MARKER)
            paragraph.level = an_item[1]

    _handle_key_message(
        the_slide=slide,
        slide_json=slide_json,
        slide_height_inch=slide_height_inch,
        slide_width_inch=slide_width_inch
    )


def _handle_double_col_layout(
        presentation: pptx.Presentation(),
        slide_json: dict,
        slide_width_inch: float,
        slide_height_inch: float
) -> bool:
    """
    Add a slide with a double column layout for comparison.

    :param presentation: The presentation object.
    :param slide_json: The content of the slide as JSON data.
    :param slide_width_inch: The width of the slide in inches.
    :param slide_height_inch: The height of the slide in inches.
    :return: True if double col layout has been added; False otherwise.
    """

    if 'bullet_points' in slide_json and slide_json['bullet_points']:
        double_col_content = slide_json['bullet_points']

        if double_col_content and (
                len(double_col_content) == 2
        ) and isinstance(double_col_content[0], dict) and isinstance(double_col_content[1], dict):
            slide = presentation.slide_layouts[4]
            slide = presentation.slides.add_slide(slide)

            shapes = slide.shapes
            title_placeholder = shapes.title
            title_placeholder.text = remove_slide_number_from_heading(slide_json['heading'])

            left_heading, right_heading = shapes.placeholders[1], shapes.placeholders[3]
            left_col, right_col = shapes.placeholders[2], shapes.placeholders[4]
            left_col_frame, right_col_frame = left_col.text_frame, right_col.text_frame

            if 'heading' in double_col_content[0]:
                left_heading.text = double_col_content[0]['heading']
            if 'bullet_points' in double_col_content[0]:
                flat_items_list = get_flat_list_of_contents(
                    double_col_content[0]['bullet_points'], level=0
                )

                for idx, an_item in enumerate(flat_items_list):
                    if idx == 0:
                        left_col_frame.text = an_item[0].removeprefix(STEP_BY_STEP_PROCESS_MARKER)
                    else:
                        paragraph = left_col_frame.add_paragraph()
                        paragraph.text = an_item[0].removeprefix(STEP_BY_STEP_PROCESS_MARKER)
                        paragraph.level = an_item[1]

            if 'heading' in double_col_content[1]:
                right_heading.text = double_col_content[1]['heading']
            if 'bullet_points' in double_col_content[1]:
                flat_items_list = get_flat_list_of_contents(
                    double_col_content[1]['bullet_points'], level=0
                )

                for idx, an_item in enumerate(flat_items_list):
                    if idx == 0:
                        right_col_frame.text = an_item[0].removeprefix(STEP_BY_STEP_PROCESS_MARKER)
                    else:
                        paragraph = right_col_frame.add_paragraph()
                        paragraph.text = an_item[0].removeprefix(STEP_BY_STEP_PROCESS_MARKER)
                        paragraph.level = an_item[1]

            _handle_key_message(
                the_slide=slide,
                slide_json=slide_json,
                slide_height_inch=slide_height_inch,
                slide_width_inch=slide_width_inch
            )

            return True

    return False


def _handle_step_by_step_process(
        presentation: pptx.Presentation,
        slide_json: dict,
        slide_width_inch: float,
        slide_height_inch: float
) -> bool:
    """
    Add shapes to display a step-by-step process in the slide, if available.

    :param presentation: The presentation object.
    :param slide_json: The content of the slide as JSON data.
    :param slide_width_inch: The width of the slide in inches.
    :param slide_height_inch: The height of the slide in inches.
    :return True if this slide has a step-by-step process depiction added; False otherwise.
    """

    if 'bullet_points' in slide_json and slide_json['bullet_points']:
        steps = slide_json['bullet_points']

        no_marker_count = 0.0
        n_steps = len(steps)

        # Ensure that it is a single list of strings without any sub-list
        for step in steps:
            if not isinstance(step, str):
                return False

            # In some cases, one or two steps may not begin with >>, e.g.:
            # {
            #     "heading": "Step-by-Step Process: Creating a Legacy",
            #     "bullet_points": [
            #         "Identify your unique talents and passions",
            #         ">> Develop your skills and knowledge",
            #         ">> Create meaningful work",
            #         ">> Share your work with the world",
            #         ">> Continuously learn and adapt"
            #     ],
            #     "key_message": ""
            # },
            #
            # Use a threshold, e.g., at most 20%
            if not step.startswith(STEP_BY_STEP_PROCESS_MARKER):
                no_marker_count += 1

        slide_header = slide_json['heading'].lower()
        if (no_marker_count / n_steps > 0.25) and not (
                ('step-by-step' in slide_header) or ('step by step' in slide_header)
        ):
            return False

        bullet_slide_layout = presentation.slide_layouts[1]
        slide = presentation.slides.add_slide(bullet_slide_layout)
        shapes = slide.shapes
        shapes.title.text = remove_slide_number_from_heading(slide_json['heading'])

        if 3 <= n_steps <= 4:
            # Horizontal display
            height = INCHES_1_5
            width = pptx.util.Inches(slide_width_inch / n_steps - 0.01)
            top = pptx.util.Inches(slide_height_inch / 2)
            left = pptx.util.Inches((slide_width_inch - width.inches * n_steps) / 2 + 0.05)

            for step in steps:
                shape = shapes.add_shape(MSO_AUTO_SHAPE_TYPE.CHEVRON, left, top, width, height)
                shape.text = step.removeprefix(STEP_BY_STEP_PROCESS_MARKER)
                left += width - INCHES_0_4
        elif 4 < n_steps <= 6:
            # Vertical display
            height = pptx.util.Inches(0.65)
            top = pptx.util.Inches(slide_height_inch / 4)
            left = INCHES_1  # slide_width_inch - width.inches)

            # Find the close to median width, based on the length of each text, to be set
            # for the shapes
            width = pptx.util.Inches(slide_width_inch * 2 / 3)
            lengths = [len(step) for step in steps]
            font_size_20pt = pptx.util.Pt(20)
            widths = sorted(
                [
                    min(
                        pptx.util.Inches(font_size_20pt.inches * a_len),
                        width
                    ) for a_len in lengths
                ]
            )
            width = widths[len(widths) // 2]

            for step in steps:
                shape = shapes.add_shape(MSO_AUTO_SHAPE_TYPE.PENTAGON, left, top, width, height)
                shape.text = step.removeprefix(STEP_BY_STEP_PROCESS_MARKER)
                top += height + INCHES_0_3
                left += INCHES_0_5
        else:
            # Two steps -- probably not a process
            # More than 5--6 steps -- would likely cause a visual clutter
            return False

    return True


def _handle_key_message(
        the_slide: pptx.slide.Slide,
        slide_json: dict,
        slide_width_inch: float,
        slide_height_inch: float
):
    """
    Add a shape to display the key message in the slide, if available.

    :param the_slide: The slide to be processed.
    :param slide_json: The content of the slide as JSON data.
    :param slide_width_inch: The width of the slide in inches.
    :param slide_height_inch: The height of the slide in inches.
    """

    if 'key_message' in slide_json and slide_json['key_message']:
        height = pptx.util.Inches(1.6)
        width = pptx.util.Inches(slide_width_inch / 2.3)
        top = pptx.util.Inches(slide_height_inch - height.inches - 0.1)
        left = pptx.util.Inches((slide_width_inch - width.inches) / 2)
        shape = the_slide.shapes.add_shape(
            MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE,
            left=left,
            top=top,
            width=width,
            height=height
        )
        shape.text = slide_json['key_message']


def _get_slide_width_height_inches(presentation: pptx.Presentation) -> Tuple[float, float]:
    """
    Get the dimensions of a slide in inches.

    :param presentation: The presentation object.
    :return: The width and the height.
    """

    slide_width_inch = EMU_TO_INCH_SCALING_FACTOR * presentation.slide_width
    slide_height_inch = EMU_TO_INCH_SCALING_FACTOR * presentation.slide_height
    # logger.debug('Slide width: %f, height: %f', slide_width_inch, slide_height_inch)

    return slide_width_inch, slide_height_inch


if __name__ == '__main__':
    _JSON_DATA = '''
    {
    "title": "Understanding AI",
    "slides": [
        {
            "heading": "Introduction",
            "bullet_points": [
                "Brief overview of AI",
                [
                    "Importance of understanding AI"
                ]
            ],
            "key_message": ""
        },
        {
            "heading": "What is AI?",
            "bullet_points": [
                "Definition of AI",
                [
                    "Types of AI",
                    [
                        "Narrow or weak AI",
                        "General or strong AI"
                    ]
                ],
                "Differences between AI and machine learning"
            ],
            "key_message": ""
        },
        {
            "heading": "How AI Works",
            "bullet_points": [
                "Overview of AI algorithms",
                [
                    "Types of AI algorithms",
                    [
                        "Rule-based systems",
                        "Decision tree systems",
                        "Neural networks"
                    ]
                ],
                "How AI processes data"
            ],
            "key_message": ""
        },
        {
            "heading": "Building AI Models",
            "bullet_points": [
                ">> Collect data",
                ">> Select model or architecture to use",
                ">> Set appropriate parameters",
                ">> Train model with data",
                ">> Run inference",
            ],
            "key_message": ""
        },
        {
            "heading": "Pros and Cons: Deep Learning vs. Classical Machine Learning",
            "bullet_points": [
                {
                    "heading": "Classical Machine Learning",
                    "bullet_points": [
                        "Interpretability: Easy to understand the model",
                        "Faster Training: Quicker to train models",
                        "Scalability: Can handle large datasets"
                    ]
                },
                {
                    "heading": "Deep Learning",
                    "bullet_points": [
                        "Handling Complex Data: Can learn from raw data",
                        "Feature Extraction: Automatically learns features",
                        "Improved Accuracy: Achieves higher accuracy"
                    ]
                }
            ],
            "key_message": ""
        },
        {
            "heading": "Pros of AI",
            "bullet_points": [
                "Increased efficiency and productivity",
                "Improved accuracy and precision",
                "Enhanced decision-making capabilities",
                "Personalized experiences"
            ],
            "key_message": "AI can be used for many different purposes"
        },
        {
            "heading": "Cons of AI",
            "bullet_points": [
                "Job displacement and loss of employment",
                "Bias and discrimination",
                "Privacy and security concerns",
                "Dependence on technology"
            ],
            "key_message": ""
        },
        {
            "heading": "Future Prospects of AI",
            "bullet_points": [
                "Advancements in fields such as healthcare and finance",
                "Increased use"
            ],
            "key_message": ""
        }
    ]
}'''

    temp = tempfile.NamedTemporaryFile(delete=False, suffix='.pptx')
    path = pathlib.Path(temp.name)

    generate_powerpoint_presentation(
        json5.loads(_JSON_DATA),
        output_file_path=path,
        slides_template='Basic'
    )
    print(f'File path: {path}')

    temp.close()
