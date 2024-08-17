"""
A set of functions to create a PowerPoint slide deck.
"""
import logging
import pathlib
import random
import re
import sys
import tempfile
from typing import List, Tuple, Optional

import json5
import pptx
from dotenv import load_dotenv
from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE
from pptx.shapes.placeholder import PicturePlaceholder, SlidePlaceholder

sys.path.append('..')
sys.path.append('../..')

import helpers.image_search as ims
from global_config import GlobalConfig


load_dotenv()


# English Metric Unit (used by PowerPoint) to inches
EMU_TO_INCH_SCALING_FACTOR = 1.0 / 914400
INCHES_1_5 = pptx.util.Inches(1.5)
INCHES_1 = pptx.util.Inches(1)
INCHES_0_5 = pptx.util.Inches(0.5)
INCHES_0_4 = pptx.util.Inches(0.4)
INCHES_0_3 = pptx.util.Inches(0.3)

STEP_BY_STEP_PROCESS_MARKER = '>> '
IMAGE_DISPLAY_PROBABILITY = 0.3
FOREGROUND_IMAGE_PROBABILITY = 0.75
SLIDE_NUMBER_REGEX = re.compile(r"^slide[ ]+\d+:", re.IGNORECASE)


logger = logging.getLogger(__name__)


def remove_slide_number_from_heading(header: str) -> str:
    """
    Remove the slide number from a given slide header.

    :param header: The header of a slide.
    :return: The header without slide number.
    """

    if SLIDE_NUMBER_REGEX.match(header):
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
    :return: A list of presentation title and slides headers.
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

    status = False

    if random.random() < IMAGE_DISPLAY_PROBABILITY:
        if random.random() < FOREGROUND_IMAGE_PROBABILITY:
            status = _handle_display_image__in_foreground(
                presentation,
                slide_json,
                slide_width_inch,
                slide_height_inch
            )
        else:
            status = _handle_display_image__in_background(
                presentation,
                slide_json,
                slide_width_inch,
                slide_height_inch
            )

    if status:
        return

    # Image display failed, so display only text
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


def _handle_display_image__in_foreground(
        presentation: pptx.Presentation(),
        slide_json: dict,
        slide_width_inch: float,
        slide_height_inch: float
) -> bool:
    """
    Create a slide with text and image using a picture placeholder layout.

    :param presentation: The presentation object.
    :param slide_json: The content of the slide as JSON data.
    :param slide_width_inch: The width of the slide in inches.
    :param slide_height_inch: The height of the slide in inches.
    :return: True if the side has been processed.
    """

    img_keywords = slide_json['img_keywords'].strip()
    slide = presentation.slide_layouts[8]  # Picture with Caption
    slide = presentation.slides.add_slide(slide)

    title_placeholder = slide.shapes.title
    title_placeholder.text = remove_slide_number_from_heading(slide_json['heading'])

    pic_col: PicturePlaceholder = slide.shapes.placeholders[1]
    text_col: SlidePlaceholder = slide.shapes.placeholders[2]
    flat_items_list = get_flat_list_of_contents(slide_json['bullet_points'], level=0)

    for idx, an_item in enumerate(flat_items_list):
        if idx == 0:
            text_col.text_frame.text = an_item[0].removeprefix(STEP_BY_STEP_PROCESS_MARKER)
        else:
            paragraph = text_col.text_frame.add_paragraph()
            paragraph.text = an_item[0].removeprefix(STEP_BY_STEP_PROCESS_MARKER)
            paragraph.level = an_item[1]

    if not img_keywords:
        # No keywords, so no image search and addition
        return True

    try:
        photo_url, page_url = ims.get_photo_url_from_api_response(
            ims.search_pexels(query=img_keywords, size='medium')
        )

        if photo_url:
            pic_col.insert_picture(
                ims.get_image_from_url(photo_url)
            )

            _add_text_at_bottom(
                slide=slide,
                slide_width_inch=slide_width_inch,
                slide_height_inch=slide_height_inch,
                text='Photo provided by Pexels',
                hyperlink=page_url
            )
    except Exception as ex:
        logger.error(
            '*** Error occurred while running adding image to slide: %s',
            str(ex)
        )

    return True


def _handle_display_image__in_background(
        presentation: pptx.Presentation(),
        slide_json: dict,
        slide_width_inch: float,
        slide_height_inch: float
) -> bool:
    """
    Add a slide with text and an image in the background. It works just like
    `_handle_default_display()` but with a background image added.

    :param presentation: The presentation object.
    :param slide_json: The content of the slide as JSON data.
    :param slide_width_inch: The width of the slide in inches.
    :param slide_height_inch: The height of the slide in inches.
    :return: True if the slide has been processed.
    """

    img_keywords = slide_json['img_keywords'].strip()

    # Add a photo in the background, text in the foreground
    slide = presentation.slides.add_slide(presentation.slide_layouts[1])

    title_shape = slide.shapes.title
    body_shape = slide.shapes.placeholders[1]
    title_shape.text = remove_slide_number_from_heading(slide_json['heading'])

    flat_items_list = get_flat_list_of_contents(slide_json['bullet_points'], level=0)

    for idx, an_item in enumerate(flat_items_list):
        if idx == 0:
            body_shape.text_frame.text = an_item[0].removeprefix(STEP_BY_STEP_PROCESS_MARKER)
        else:
            paragraph = body_shape.text_frame.add_paragraph()
            paragraph.text = an_item[0].removeprefix(STEP_BY_STEP_PROCESS_MARKER)
            paragraph.level = an_item[1]

    if not img_keywords:
        # No keywords, so no image search and addition
        return True

    try:
        photo_url, page_url = ims.get_photo_url_from_api_response(
            ims.search_pexels(query=img_keywords, size='large')
        )

        if photo_url:
            picture = slide.shapes.add_picture(
                image_file=ims.get_image_from_url(photo_url),
                left=0,
                top=0,
                width=pptx.util.Inches(slide_width_inch),
            )

            _add_text_at_bottom(
                slide=slide,
                slide_width_inch=slide_width_inch,
                slide_height_inch=slide_height_inch,
                text='Photos provided by Pexels',
                hyperlink=page_url
            )

            # Move picture to background
            # https://github.com/scanny/python-pptx/issues/49#issuecomment-137172836
            slide.shapes._spTree.remove(picture._element)
            slide.shapes._spTree.insert(2, picture._element)
    except Exception as ex:
        logger.error(
            '*** Error occurred while running adding image to the slide background: %s',
            str(ex)
        )

    return True


def _add_text_at_bottom(
        slide: pptx.slide.Slide,
        slide_width_inch: float,
        slide_height_inch: float,
        text: str,
        hyperlink: Optional[str] = None,
        target_height: Optional[float] = 0.5
):
    """
    Add arbitrary text to a textbox positioned near the lower left side of a slide.

    :param slide: The slide.
    :param slide_width_inch: The width of the slide.
    :param slide_height_inch: The height of the slide.
    :param target_height: the target height of the box in inches (optional).
    :param text: The text to be added
    :param hyperlink: The hyperlink to be added to the text (optional).
    """

    footer = slide.shapes.add_textbox(
        left=INCHES_1,
        top=pptx.util.Inches(slide_height_inch - target_height),
        width=pptx.util.Inches(slide_width_inch),
        height=pptx.util.Inches(target_height)
    )

    paragraph = footer.text_frame.paragraphs[0]
    run = paragraph.add_run()
    run.text = text
    run.font.size = pptx.util.Pt(10)
    run.font.underline = False

    if hyperlink:
        run.hyperlink.address = hyperlink


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


def print_placeholder_names(slide: pptx.slide.Slide):
    """
    Display the placeholder details of a given slide.

    :param slide: The slide.
    """

    for shape in slide.placeholders:
        print(f'{shape.placeholder_format.idx=}, {shape.name=}')


if __name__ == '__main__':
    _JSON_DATA = '''
    {
    "title": "Mastering PowerPoint Shapes",
    "slides": [
        {
            "heading": "Introduction to PowerPoint Shapes",
            "bullet_points": [
                "Shapes are fundamental elements in PowerPoint",
                "Used to create diagrams, flowcharts, and visuals",
                "Available in various types: lines, rectangles, circles, etc."
            ],
            "key_message": "",
            "img_keywords": "PowerPoint shapes, basic shapes"
        },
        {
            "heading": "Types of Shapes in PowerPoint",
            "bullet_points": [
                "Lines: Connect two points",
                "Rectangles: Four-sided figures with right angles",
                [
                    "Squares: Special type of rectangle with equal sides",
                    "Rounded Rectangles: Rectangles with rounded corners"
                ],
                "Circles: Round shapes with no corners",
                "Ovals: Elliptical shapes"
            ],
            "key_message": "",
            "img_keywords": "PowerPoint shapes, types of shapes"
        },
        {
            "heading": "Creating and Manipulating Shapes",
            "bullet_points": [
                ">> Select the 'Home' tab and click on 'Shapes'",
                ">> Choose the desired shape",
                ">> Click and drag to create the shape",
                ">> Resize, move, or rotate shapes using handles",
                ">> Change shape color, fill, and outline"
            ],
            "key_message": "Demonstrates the process of creating and manipulating shapes",
            "img_keywords": "PowerPoint shapes, creating shapes, manipulating shapes"
        },
        {
            "heading": "Advanced Shape Manipulation",
            "bullet_points": [
                {
                    "heading": "Adding Text to Shapes",
                    "bullet_points": [
                        "Right-click on the shape and select 'Add Text'",
                        "Type or paste the desired text"
                    ]
                },
                {
                    "heading": "Grouping and Ungrouping Shapes",
                    "bullet_points": [
                        "Select multiple shapes and press 'Ctrl + G' to group",
                        "Right-click and select 'Ungroup' to separate"
                    ]
                }
            ],
            "key_message": "Explores advanced techniques for working with shapes",
            "img_keywords": "PowerPoint shapes, advanced manipulation, grouping, text in shapes"
        },
        {
            "heading": "Using the 'Format' Tab for Shapes",
            "bullet_points": [
                "Access advanced shape formatting options",
                "Change shape fill, outline, and effects",
                "Adjust shape size and position"
            ],
            "key_message": "",
            "img_keywords": "PowerPoint shapes, format tab, advanced formatting"
        },
        {
            "heading": "Example: Creating a Simple Diagram",
            "bullet_points": [
                "Use rectangles to represent blocks",
                "Use lines to connect blocks",
                "Add text to shapes to label elements"
            ],
            "key_message": "Illustrates the use of shapes to create a simple diagram",
            "img_keywords": "PowerPoint shapes, diagram example, simple diagram"
        },
        {
            "heading": "Example: Creating a Flowchart",
            "bullet_points": [
                "Use different shapes to represent steps, decisions, and inputs/outputs",
                "Use connectors to link shapes",
                "Add text to shapes to describe each step"
            ],
            "key_message": "Demonstrates the use of shapes to create a flowchart",
            "img_keywords": "PowerPoint shapes, flowchart example, creating flowchart"
        },
        {
            "heading": "Double Column Layout: Shapes in Older vs. Newer PowerPoint Versions",
            "bullet_points": [
                {
                    "heading": "Older PowerPoint Versions",
                    "bullet_points": [
                        "Limited shape types and formatting options",
                        "Less intuitive shape creation and manipulation"
                    ]
                },
                {
                    "heading": "Newer PowerPoint Versions",
                    "bullet_points": [
                        "Expanded shape library with more types and styles",
                        "Improved shape formatting and manipulation tools"
                    ]
                }
            ],
            "key_message": "Compares the use of shapes in older and newer PowerPoint versions",
            "img_keywords": "PowerPoint shapes, older versions, newer versions, comparison"
        },
        {
            "heading": "Tips for Effective Use of Shapes",
            "bullet_points": [
                "Keep shapes simple and uncluttered",
                "Use consistent colors and styles",
                "Avoid overusing shapes, maintain balance with text and other elements"
            ],
            "key_message": "Provides best practices for using shapes in presentations",
            "img_keywords": "PowerPoint shapes, best practices, effective use"
        },
        {
            "heading": "Conclusion",
            "bullet_points": [
                "Shapes are versatile tools in PowerPoint",
                "Mastering shapes enhances presentation visuals",
                "Practice and experimentation are key to improving shape usage"
            ],
            "key_message": "Summarizes the importance of shapes in PowerPoint and encourages practice",
            "img_keywords": "PowerPoint shapes, conclusion, importance"
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
