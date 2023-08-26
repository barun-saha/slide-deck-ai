import json5
import pptx
import re
import yaml

from pptx.dml.color import RGBColor

PATTERN = re.compile(r"^slide[ ]+\d+:", re.IGNORECASE)


def remove_slide_number_from_heading(header: str) -> str:
    if PATTERN.match(header):
        idx = header.find(':')
        header = header[idx + 1:]

    return header


def generate_powerpoint_presentation(structured_data: str, as_yaml: bool, output_file_name: str):
    """
    Create and save a PowerPoint presentation file containing the contents in JSON or YAML format.

    :param structured_data: The presentation contents as "JSON" (may contain trailing commas) or YAML
    :param as_yaml: True if the input data is in YAML format; False if it is in JSON format
    :param output_file_name: The name of the PPTX file to save as
    """

    if as_yaml:
        # Avoid YAML mode: nested bullets can lead to incorrect YAML generation
        try:
            parsed_data = yaml.safe_load(structured_data)
        except yaml.parser.ParserError as ype:
            print(f'*** YAML parse error: {ype}')
            parsed_data = {'title': '', 'slides': []}
    else:
        # The structured "JSON" might contain trailing commas, so using json5
        parsed_data = json5.loads(structured_data)

    presentation = pptx.Presentation()

    # The title slide
    title_slide_layout = presentation.slide_layouts[0]
    slide = presentation.slides.add_slide(title_slide_layout)
    title = slide.shapes.title
    subtitle = slide.placeholders[1]
    title.text = parsed_data['title']
    print(f'Title is: {title.text}')
    subtitle.text = 'by Myself and SlideDeck AI :)'

    background = slide.background
    background.fill.solid()
    background.fill.fore_color.rgb = RGBColor.from_string('C0C0C0')  # Silver
    title.text_frame.paragraphs[0].font.color.rgb = RGBColor(0, 0, 128)  # Navy blue

    # Add contents in a loop
    for a_slide in parsed_data['slides']:
        bullet_slide_layout = presentation.slide_layouts[1]
        slide = presentation.slides.add_slide(bullet_slide_layout)
        shapes = slide.shapes

        title_shape = shapes.title
        body_shape = shapes.placeholders[1]
        title_shape.text = remove_slide_number_from_heading(a_slide['heading'])
        text_frame = body_shape.text_frame

        for an_item in a_slide['bullet_points']:
            item_type = type(an_item)
            # print('Bullet point type:', item_type)

            if item_type is str:
                paragraph = text_frame.add_paragraph()
                paragraph.text = an_item
                paragraph.level = 0
            elif item_type is list:
                for sub_item in an_item:
                    if type(sub_item) is str:
                        paragraph = text_frame.add_paragraph()
                        paragraph.text = sub_item
                        paragraph.level = 1

        background = slide.background
        background.fill.gradient()
        background.fill.gradient_angle = -225.0

    # The thank-you slide
    last_slide_layout = presentation.slide_layouts[0]
    slide = presentation.slides.add_slide(last_slide_layout)
    title = slide.shapes.title
    title.text = 'Thank you!'

    presentation.save(output_file_name)


if __name__ == '__main__':
    generate_powerpoint_presentation(
        json5.loads(open('examples/example_02_structured_output.json', 'r').read()),
        as_yaml=False,
        output_file_name='test.pptx'
    )
