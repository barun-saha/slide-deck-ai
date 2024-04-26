import logging
import os.path
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
        '*** Using PPTX template: %s (exists = %s)',
        GlobalConfig.PPTX_TEMPLATE_FILES[slides_template]['file'],
        os.path.exists(GlobalConfig.PPTX_TEMPLATE_FILES[slides_template]['file'])
    )
    presentation = pptx.Presentation(GlobalConfig.PPTX_TEMPLATE_FILES[slides_template]['file'])

    slide_width_inch = EMU_TO_INCH_SCALING_FACTOR * presentation.slide_width
    slide_height_inch = EMU_TO_INCH_SCALING_FACTOR * presentation.slide_height
    logger.debug('Slide width: %f, height: %f', slide_width_inch, slide_height_inch)

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

    # background = slide.background
    # background.fill.solid()
    # background.fill.fore_color.rgb = RGBColor.from_string('C0C0C0')  # Silver
    # title.text_frame.paragraphs[0].font.color.rgb = RGBColor(0, 0, 128)  # Navy blue

    # Add contents in a loop
    for a_slide in parsed_data['slides']:
        bullet_slide_layout = presentation.slide_layouts[1]
        slide = presentation.slides.add_slide(bullet_slide_layout)
        shapes = slide.shapes

        title_shape = shapes.title
        body_shape = shapes.placeholders[1]
        title_shape.text = remove_slide_number_from_heading(a_slide['heading'])
        all_headers.append(title_shape.text)
        text_frame = body_shape.text_frame

        # The bullet_points may contain a nested hierarchy of JSON arrays
        # In some scenarios, it may contain objects (dictionaries) because the LLM generated so
        #  ^ The second scenario is not covered

        flat_items_list = get_flat_list_of_contents(a_slide['bullet_points'], level=0)

        for an_item in flat_items_list:
            paragraph = text_frame.add_paragraph()
            paragraph.text = an_item[0]
            paragraph.level = an_item[1]

        _handle_key_message(
            slide=slide,
            slide_json=a_slide,
            slide_width_inch=slide_width_inch,
            slide_height_inch=slide_height_inch,
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


def _handle_key_message(
        slide: pptx.slide.Slide,
        slide_json: dict,
        slide_width_inch: float,
        slide_height_inch: float
):
    """
    Add a shape to display the key message in the slide, if available.

    :param slide: The slide to be processed.
    :param slide_json: The content of the slide as JSON data.
    :param slide_width_inch: The width of the slide in inches.
    :param slide_height_inch: The height of the slide in inches.
    """

    if 'key_message' in slide_json and slide_json['key_message']:
        height = pptx.util.Inches(1.6)
        width = pptx.util.Inches(slide_width_inch / 2.3)
        top = pptx.util.Inches(slide_height_inch - height.inches - 0.1)
        left = pptx.util.Inches((slide_width_inch - width.inches) / 2)
        logger.debug(
            '_handle_key_message shape:: left: %.2f, top: %.2f, width: %.2f, height: %.2f',
            left, top, width, height
        )
        shape = slide.shapes.add_shape(
            MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE,
            left=left,
            top=top,
            width=width,
            height=height
        )
        shape.text = slide_json['key_message']


if __name__ == '__main__':
    # bullets = [
    #     'Description',
    #     'Types',
    #     [
    #         'Type A',
    #         'Type B'
    #     ],
    #     'Grand parent',
    #     [
    #         'Parent',
    #         [
    #             'Grand child'
    #         ]
    #     ]
    # ]

    # output = get_flat_list_of_contents(bullets, level=0)
    # for x in output:
    #     print(x)

    json_data = '''
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
        json5.loads(json_data),
        output_file_path=path,
        slides_template='Blank'
    )
    print(f'File path: {path}')

    temp.close()
