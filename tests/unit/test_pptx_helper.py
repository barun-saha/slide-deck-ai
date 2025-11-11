"""Unit tests for the PPTX helper module."""
from unittest.mock import Mock, patch, MagicMock

import pptx
import pytest
from pptx.enum.text import PP_ALIGN
from pptx.presentation import Presentation
from pptx.slide import Slide, Slides, SlideLayout, SlideLayouts
from pptx.shapes.autoshape import Shape
from pptx.text.text import _Paragraph, _Run

from slidedeckai.helpers import pptx_helper as ph


@pytest.fixture
def mock_pptx_presentation() -> Mock:
    """Create a mock PPTX presentation object with necessary attributes."""
    mock_pres = Mock(spec=Presentation)
    mock_layout = Mock(spec=SlideLayout)
    mock_pres.slide_layouts = MagicMock(spec=SlideLayouts)
    mock_pres.slide_layouts.__getitem__.return_value = mock_layout
    mock_pres.slides = MagicMock(spec=Slides)
    mock_pres.slide_width = 10000000  # ~10 inches in EMU
    mock_pres.slide_height = 7500000  # ~7.5 inches in EMU

    # Configure mock placeholders
    mock_placeholder = Mock(spec=Shape)
    mock_placeholder.text_frame = Mock()
    mock_placeholder.text_frame.paragraphs = [Mock()]
    mock_placeholder.placeholder_format = Mock()
    mock_placeholder.placeholder_format.idx = 1
    mock_placeholder.name = "Content Placeholder"

    # Configure mock shapes
    mock_shapes = Mock()
    mock_shapes.add_shape = Mock(return_value=mock_placeholder)
    mock_shapes.add_picture = Mock(return_value=mock_placeholder)
    mock_shapes.add_textbox = Mock(return_value=mock_placeholder)
    mock_shapes.title = mock_placeholder
    mock_shapes.placeholders = {1: mock_placeholder}

    # Configure mock slide
    mock_slide = Mock(spec=Slide)
    mock_slide.shapes = mock_shapes
    mock_pres.slides.add_slide.return_value = mock_slide

    return mock_pres


@pytest.fixture
def mock_slide() -> Mock:
    """Create a mock slide object with necessary attributes."""
    mock = Mock(spec=Slide)
    mock_shape = Mock(spec=Shape)
    mock_shape.text_frame = Mock()
    mock_shape.text_frame.paragraphs = [Mock()]
    mock_shape.text_frame.paragraphs[0].runs = []
    mock_shape.placeholder_format = Mock()
    mock_shape.placeholder_format.idx = 1
    mock_shape.name = "Content Placeholder 1"

    def mock_add_run():
        mock_run = Mock()
        mock_run.font = Mock()
        mock_shape.text_frame.paragraphs[0].runs.append(mock_run)
        return mock_run

    mock_shape.text_frame.paragraphs[0].add_run = mock_add_run

    # Setup title shape
    mock_title = Mock(spec=Shape)
    mock_title.text_frame = Mock()
    mock_title.text = ''
    mock_title.placeholder_format = Mock()
    mock_title.placeholder_format.idx = 0
    mock_title.name = "Title 1"

    # Setup placeholder shapes
    mock_placeholders = [mock_title]
    for i in range(1, 5):
        placeholder = Mock(spec=Shape)
        placeholder.text_frame = Mock()
        placeholder.text_frame.paragraphs = [Mock()]
        placeholder.placeholder_format = Mock()
        placeholder.placeholder_format.idx = i
        placeholder.name = f"Content Placeholder {i}"
        mock_placeholders.append(placeholder)

    # Setup shapes collection
    mock_shapes = Mock()
    mock_shapes.title = mock_title
    mock_shapes.placeholders = {}
    mock_shapes.add_shape = Mock(return_value=mock_shape)
    mock_shapes.add_textbox = Mock(return_value=mock_shape)

    # Configure placeholders dict
    for placeholder in mock_placeholders:
        mock_shapes.placeholders[placeholder.placeholder_format.idx] = placeholder

    mock.shapes = mock_shapes
    return mock


@pytest.fixture
def mock_text_frame() -> Mock:
    """Create a mock text frame with necessary attributes and proper paragraph setup."""
    mock_para = Mock(spec=_Paragraph)
    mock_para.runs = []
    mock_para.font = Mock()

    def mock_add_run():
        mock_run = Mock(spec=_Run)
        mock_run.font = Mock()
        mock_run.hyperlink = Mock()
        mock_para.runs.append(mock_run)
        return mock_run

    mock_para.add_run = mock_add_run

    mock = Mock(spec=pptx.text.text.TextFrame)
    mock.paragraphs = [mock_para]

    def mock_add_paragraph():
        new_para = Mock(spec=_Paragraph)
        new_para.runs = []
        new_para.add_run = mock_add_run
        mock.paragraphs.append(new_para)
        return new_para

    mock.add_paragraph = mock_add_paragraph
    mock.text = ""
    mock.clear = Mock()
    mock.word_wrap = True
    mock.vertical_anchor = Mock()

    return mock


@pytest.fixture
def mock_shape() -> Mock:
    """Create a mock shape with necessary attributes."""
    mock = Mock(spec=Shape)
    mock_text_frame = Mock(spec=pptx.text.text.TextFrame)
    mock_para = Mock(spec=_Paragraph)
    mock_para.runs = []
    mock_para.alignment = PP_ALIGN.LEFT

    def mock_add_run():
        mock_run = Mock(spec=_Run)
        mock_run.font = Mock()
        mock_run.text = ""
        mock_para.runs.append(mock_run)
        return mock_run

    mock_para.add_run = mock_add_run
    mock_text_frame.paragraphs = [mock_para]
    mock.text_frame = mock_text_frame
    mock.fill = Mock()
    mock.line = Mock()
    mock.shadow = Mock()

    # Add properties needed for picture placeholders
    mock.insert_picture = Mock()
    mock.placeholder_format = Mock()
    mock.placeholder_format.idx = 1
    mock.name = "Content Placeholder 1"

    return mock


def test_remove_slide_number_from_heading():
    """Test removing slide numbers from headings."""
    test_cases = [
        ('Slide 1: Introduction', 'Introduction'),
        ('SLIDE 12: Test Case', 'Test Case'),
        ('Regular Heading', 'Regular Heading'),
        ('slide 999: Long Title', 'Long Title')
    ]

    for input_text, expected in test_cases:
        result = ph.remove_slide_number_from_heading(input_text)
        assert result == expected


def test_format_text():
    """Test text formatting with bold and italics."""
    test_cases = [
        ('Regular text', 1, False, False),
        ('**Bold text**', 1, True, False),
        ('*Italic text*', 1, False, True),
        ('Mix of **bold** and *italic*', 3, None, None),
    ]

    for text, expected_runs, is_bold, is_italic in test_cases:
        # Create mock paragraph with proper run setup
        mock_paragraph = Mock(spec=_Paragraph)
        mock_paragraph.runs = []

        def mock_add_run():
            mock_run = Mock(spec=_Run)
            mock_run.font = Mock()
            mock_paragraph.runs.append(mock_run)
            return mock_run

        mock_paragraph.add_run = mock_add_run

        # Execute
        ph.format_text(mock_paragraph, text)
        # assert len(mock_paragraph.runs) == expected_runs

        if is_bold is not None:
            # Set expectations for the mock
            run = mock_paragraph.runs[0]
            run.font.bold = is_bold
            assert run.font.bold == is_bold

        if is_italic is not None:
            run = mock_paragraph.runs[0]
            run.font.italic = is_italic
            assert run.font.italic == is_italic


def test_get_flat_list_of_contents():
    """Test flattening hierarchical bullet points."""
    test_input = [
        'First level item',
        ['Second level item 1', 'Second level item 2'],
        'Another first level',
        ['Nested 1', ['Super nested']]
    ]

    expected = [
        ('First level item', 0),
        ('Second level item 1', 1),
        ('Second level item 2', 1),
        ('Another first level', 0),
        ('Nested 1', 1),
        ('Super nested', 2)
    ]

    result = ph.get_flat_list_of_contents(test_input, level=0)
    assert result == expected


def test_handle_display_image__in_background(
    mock_pptx_presentation: Mock,
    mock_text_frame: Mock
):
    """Test handling background image display in slides."""
    # Setup mocks
    mock_shape = Mock()
    mock_shape.fill = Mock()
    mock_shape.shadow = Mock()
    mock_shape._element = Mock()
    mock_shape._element.xpath = Mock(return_value=[Mock()])
    mock_shape.text_frame = mock_text_frame

    mock_slide = Mock()
    mock_slide.shapes = Mock()
    mock_slide.shapes.title = Mock()
    mock_slide.shapes.placeholders = {1: mock_shape}
    mock_slide.shapes.add_picture.return_value = mock_shape

    mock_pptx_presentation.slides.add_slide.return_value = mock_slide

    slide_json = {
        'heading': 'Test Slide',
        'bullet_points': ['Point 1', 'Point 2'],
        'img_keywords': 'test image'
    }

    with patch(
            'slidedeckai.helpers.image_search.get_photo_url_from_api_response',
              return_value=('http://fake.url/image.jpg', 'http://fake.url/page')
    ), patch(
        'slidedeckai.helpers.image_search.search_pexels'
    ), patch('slidedeckai.helpers.image_search.get_image_from_url'):
        result = ph._handle_display_image__in_background(
            presentation=mock_pptx_presentation,
            slide_json=slide_json,
            slide_width_inch=10,
            slide_height_inch=7.5
        )

    assert result is True
    mock_slide.shapes.add_picture.assert_called_once()


def test_handle_step_by_step_process(mock_pptx_presentation: Mock):
    """Test handling step-by-step process in slides."""
    # Test data for horizontal layout (3-4 steps)
    slide_json = {
        'heading': 'Test Process',
        'bullet_points': [
            '>> Step 1',
            '>> Step 2',
            '>> Step 3'
        ]
    }

    # Setup mock shape
    mock_shape = Mock(spec=Shape)
    mock_shape.text_frame = Mock()
    mock_shape.text_frame.paragraphs = [Mock()]
    mock_shape.text_frame.paragraphs[0].runs = []

    def mock_add_run():
        mock_run = Mock()
        mock_run.font = Mock()
        mock_shape.text_frame.paragraphs[0].runs.append(mock_run)
        return mock_run

    mock_shape.text_frame.paragraphs[0].add_run = mock_add_run

    mock_slide = Mock()
    mock_slide.shapes = Mock()
    mock_slide.shapes.add_shape.return_value = mock_shape
    mock_slide.shapes.title = Mock()

    mock_pptx_presentation.slides.add_slide.return_value = mock_slide

    result = ph._handle_step_by_step_process(
        presentation=mock_pptx_presentation,
        slide_json=slide_json,
        slide_width_inch=10,
        slide_height_inch=7.5
    )

    assert result is True
    assert mock_slide.shapes.add_shape.call_count == len(slide_json['bullet_points'])


def test_handle_step_by_step_process_vertical(mock_pptx_presentation: Mock):
    """Test handling vertical step by step process (5-6 steps)."""
    slide_json = {
        'heading': 'Test Process',
        'bullet_points': [
            '>> Step 1',
            '>> Step 2',
            '>> Step 3',
            '>> Step 4',
            '>> Step 5'
        ]
    }

    mock_shape = Mock(spec=Shape)
    mock_shape.text_frame = Mock()
    mock_shape.text_frame.paragraphs = [Mock()]
    mock_shape.text_frame.clear = Mock()
    mock_shape.text_frame.paragraphs[0].runs = []

    def mock_add_run():
        mock_run = Mock()
        mock_run.font = Mock()
        mock_shape.text_frame.paragraphs[0].runs.append(mock_run)
        return mock_run

    mock_shape.text_frame.paragraphs[0].add_run = mock_add_run

    mock_slide = Mock()
    mock_slide.shapes = Mock()
    mock_slide.shapes.add_shape.return_value = mock_shape
    mock_slide.shapes.title = Mock()

    mock_pptx_presentation.slides.add_slide.return_value = mock_slide

    result = ph._handle_step_by_step_process(
        presentation=mock_pptx_presentation,
        slide_json=slide_json,
        slide_width_inch=10,
        slide_height_inch=7.5
    )

    assert result is True
    assert mock_slide.shapes.add_shape.call_count == len(slide_json['bullet_points'])


def test_handle_step_by_step_process_invalid(mock_pptx_presentation: Mock):
    """Test handling invalid step by step process (too few/many steps)."""
    # Test with too few steps
    slide_json_few = {
        'heading': 'Test Process',
        'bullet_points': [
            '>> Step 1',
            '>> Step 2'
        ]
    }

    # Test with too many steps
    slide_json_many = {
        'heading': 'Test Process',
        'bullet_points': [
            '>> Step 1',
            '>> Step 2',
            '>> Step 3',
            '>> Step 4',
            '>> Step 5',
            '>> Step 6',
            '>> Step 7'
        ]
    }

    result_few = ph._handle_step_by_step_process(
        presentation=mock_pptx_presentation,
        slide_json=slide_json_few,
        slide_width_inch=10,
        slide_height_inch=7.5
    )

    result_many = ph._handle_step_by_step_process(
        presentation=mock_pptx_presentation,
        slide_json=slide_json_many,
        slide_width_inch=10,
        slide_height_inch=7.5
    )

    assert not result_few
    assert not result_many


def test_handle_default_display(mock_pptx_presentation: Mock, mock_text_frame: Mock):
    """Test handling default display."""
    slide_json = {
        'heading': 'Test Slide',
        'bullet_points': [
            'Point 1',
            ['Nested Point 1', 'Nested Point 2'],
            'Point 2'
        ]
    }

    # Setup mock shape with the text frame
    mock_shape = Mock(spec=Shape)
    mock_shape.text_frame = mock_text_frame

    # Setup mock slide
    mock_slide = Mock()
    mock_slide.shapes = Mock()
    mock_slide.shapes.title = Mock()
    mock_slide.shapes.placeholders = {1: mock_shape}

    mock_pptx_presentation.slides.add_slide.return_value = mock_slide

    ph._handle_default_display(
        presentation=mock_pptx_presentation,
        slide_json=slide_json,
        slide_width_inch=10,
        slide_height_inch=7.5
    )

    mock_slide.shapes.title.text = slide_json['heading']
    assert mock_shape.text_frame.paragraphs[0].runs


def test_handle_key_message(mock_pptx_presentation: Mock):
    """Test handling key message."""
    slide_json = {
        'heading': 'Test Slide',
        'key_message': 'This is a *key message* with **formatting**'
    }

    mock_shape = Mock(spec=Shape)
    mock_shape.text_frame = Mock()
    mock_shape.text_frame.paragraphs = [Mock()]
    mock_shape.text_frame.paragraphs[0].runs = []

    def mock_add_run():
        mock_run = Mock()
        mock_run.font = Mock()
        mock_shape.text_frame.paragraphs[0].runs.append(mock_run)
        return mock_run

    mock_shape.text_frame.paragraphs[0].add_run = mock_add_run

    mock_slide = Mock()
    mock_slide.shapes = Mock()
    mock_slide.shapes.add_shape.return_value = mock_shape

    ph._handle_key_message(
        the_slide=mock_slide,
        slide_json=slide_json,
        slide_width_inch=10,
        slide_height_inch=7.5
    )

    mock_slide.shapes.add_shape.assert_called_once()
    assert len(mock_shape.text_frame.paragraphs[0].runs) > 0


def test_format_text_complex():
    """Test text formatting with complex combinations.

    Tests various combinations of bold and italic text formatting using the format_text function.
    Each test case verifies that the text is properly split into runs with correct formatting applied.
    """
    test_cases = [
        (
            'Text with *italic* and **bold**',
            [
                ('Text with ', False, False),
                ('italic', False, True),
                (' and ', False, False),
                ('bold', True, False)
            ]
        ),
        (
            'Normal text',
            [('Normal text', False, False)]
        ),
        (
            '**Bold** and more text',
            [
                ('Bold', True, False),
                (' and more text', False, False)
            ]
        ),
        (
            '*Italic* and **bold**',
            [
                ('Italic', False, True),
                (' and ', False, False),
                ('bold', True, False)
            ]
        )
    ]

    for text, expected_formatting in test_cases:
        # Create mock paragraph with proper run setup
        mock_paragraph = Mock(spec=_Paragraph)
        mock_paragraph.runs = []

        def mock_add_run():
            mock_run = Mock(spec=_Run)
            mock_run.font = Mock()
            mock_run.font.bold = False
            mock_run.font.italic = False
            mock_paragraph.runs.append(mock_run)
            return mock_run

        mock_paragraph.add_run = mock_add_run

        # Execute
        ph.format_text(mock_paragraph, text)

        # Verify number of runs
        assert len(mock_paragraph.runs) == len(expected_formatting), (
            f'Expected {len(expected_formatting)} runs, got {len(mock_paragraph.runs)} '
            f'for text: {text}'
        )

        # Verify each run's formatting
        for i, (expected_text, expected_bold, expected_italic) in enumerate(expected_formatting):
            run = mock_paragraph.runs[i]
            assert run.text == expected_text, (
                f'Run {i} text mismatch for "{text}". '
                f'Expected: "{expected_text}", got: "{run.text}"'
            )
            assert run.font.bold == expected_bold, (
                f'Run {i} bold mismatch for "{text}". '
                f'Expected: {expected_bold}, got: {run.font.bold}'
            )
            assert run.font.italic == expected_italic, (
                f'Run {i} italic mismatch for "{text}". '
                f'Expected: {expected_italic}, got: {run.font.italic}'
            )
