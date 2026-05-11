"""
Invoice PDF template style configurations.
Each function returns a dict of style settings used by pdf_generator.py.
"""
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import TableStyle


# ── Shared helpers ──────────────────────────────────────────────────────────

def _base_styles():
    return getSampleStyleSheet()


def _grid_style(header_bg, border_color):
    """Standard item/HSN table style with given colours."""
    bc = colors.HexColor(border_color)
    return TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(header_bg)),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, bc),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ])


# ── 1. CLASSIC ──────────────────────────────────────────────────────────────

def get_classic_config():
    """Original red-accented traditional business design."""
    base = _base_styles()
    return {
        'name': 'Classic',
        'company_color': '#d62828',
        'title_color': '#222222',
        'header_bg': '#faefef',
        'border_color': '#cccccc',
        'accent': '#d62828',
        'header_line_color': '#cccccc',
        'styles': {
            'title': ParagraphStyle('T', parent=base['Heading1'], fontSize=14, alignment=1, spaceAfter=4, textColor=colors.HexColor('#222222')),
            'company': ParagraphStyle('C', parent=base['Normal'], fontSize=12, textColor=colors.HexColor('#d62828'), leading=14, alignment=2),
            'normal': ParagraphStyle('N', parent=base['Normal'], fontSize=9, leading=12),
            'normal_right': ParagraphStyle('NR', parent=base['Normal'], fontSize=9, leading=12, alignment=2),
            'bold': ParagraphStyle('B', parent=base['Normal'], fontSize=9, leading=12, fontName='Helvetica-Bold'),
            'bold_right': ParagraphStyle('BR', parent=base['Normal'], fontSize=9, leading=12, fontName='Helvetica-Bold', alignment=2),
            'small': ParagraphStyle('S', parent=base['Normal'], fontSize=8, leading=10, textColor=colors.HexColor('#555555')),
            'terms': ParagraphStyle('TM', parent=base['Normal'], fontSize=8, leading=11),
        },
        'table_style': _grid_style('#faefef', '#cccccc'),
    }


# ── 2. MODERN ───────────────────────────────────────────────────────────────

def get_modern_config():
    """Dark navy header, blue accents, bold modern feel."""
    base = _base_styles()
    return {
        'name': 'Modern',
        'company_color': '#1a2744',
        'title_color': '#ffffff',
        'header_bg': '#1a2744',
        'border_color': '#94a3b8',
        'accent': '#3b82f6',
        'header_line_color': '#3b82f6',
        'styles': {
            'title': ParagraphStyle('T', parent=base['Heading1'], fontSize=14, alignment=1, spaceAfter=4, textColor=colors.HexColor('#1a2744')),
            'company': ParagraphStyle('C', parent=base['Normal'], fontSize=12, textColor=colors.HexColor('#1a2744'), leading=14, alignment=2, fontName='Helvetica-Bold'),
            'normal': ParagraphStyle('N', parent=base['Normal'], fontSize=9, leading=12),
            'normal_right': ParagraphStyle('NR', parent=base['Normal'], fontSize=9, leading=12, alignment=2),
            'bold': ParagraphStyle('B', parent=base['Normal'], fontSize=9, leading=12, fontName='Helvetica-Bold'),
            'bold_right': ParagraphStyle('BR', parent=base['Normal'], fontSize=9, leading=12, fontName='Helvetica-Bold', alignment=2),
            'small': ParagraphStyle('S', parent=base['Normal'], fontSize=8, leading=10, textColor=colors.HexColor('#475569')),
            'terms': ParagraphStyle('TM', parent=base['Normal'], fontSize=8, leading=11),
        },
        'table_style': _modern_table_style(),
    }


def _modern_table_style():
    navy = colors.HexColor('#1a2744')
    border = colors.HexColor('#94a3b8')
    stripe = colors.HexColor('#f1f5f9')
    return TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), navy),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.4, border),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, stripe]),
    ])


# ── 3. ELEGANT ──────────────────────────────────────────────────────────────

def get_elegant_config():
    """Gold/amber accents, serif hints, luxury feel."""
    base = _base_styles()
    return {
        'name': 'Elegant',
        'company_color': '#92400e',
        'title_color': '#78350f',
        'header_bg': '#fef3c7',
        'border_color': '#d97706',
        'accent': '#b45309',
        'header_line_color': '#d97706',
        'styles': {
            'title': ParagraphStyle('T', parent=base['Heading1'], fontSize=15, alignment=1, spaceAfter=4, textColor=colors.HexColor('#78350f'), fontName='Times-Bold'),
            'company': ParagraphStyle('C', parent=base['Normal'], fontSize=13, textColor=colors.HexColor('#92400e'), leading=15, alignment=2, fontName='Times-Bold'),
            'normal': ParagraphStyle('N', parent=base['Normal'], fontSize=9, leading=12),
            'normal_right': ParagraphStyle('NR', parent=base['Normal'], fontSize=9, leading=12, alignment=2),
            'bold': ParagraphStyle('B', parent=base['Normal'], fontSize=9, leading=12, fontName='Helvetica-Bold'),
            'bold_right': ParagraphStyle('BR', parent=base['Normal'], fontSize=9, leading=12, fontName='Helvetica-Bold', alignment=2),
            'small': ParagraphStyle('S', parent=base['Normal'], fontSize=8, leading=10, textColor=colors.HexColor('#78350f')),
            'terms': ParagraphStyle('TM', parent=base['Normal'], fontSize=8, leading=11),
        },
        'table_style': _elegant_table_style(),
    }


def _elegant_table_style():
    gold_bg = colors.HexColor('#fef3c7')
    gold_border = colors.HexColor('#d97706')
    return TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), gold_bg),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#78350f')),
        ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LINEBELOW', (0, 0), (-1, 0), 1.2, gold_border),
        ('LINEBELOW', (0, -1), (-1, -1), 0.8, gold_border),
        ('LINEAFTER', (0, 0), (-2, -1), 0.3, colors.HexColor('#e5e7eb')),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ])


# ── 4. MINIMAL ──────────────────────────────────────────────────────────────

def get_minimal_config():
    """Borderless, lots of whitespace, ultra-modern simplicity."""
    base = _base_styles()
    return {
        'name': 'Minimal',
        'company_color': '#374151',
        'title_color': '#111827',
        'header_bg': '#f9fafb',
        'border_color': '#e5e7eb',
        'accent': '#6366f1',
        'header_line_color': '#e5e7eb',
        'styles': {
            'title': ParagraphStyle('T', parent=base['Heading1'], fontSize=13, alignment=1, spaceAfter=4, textColor=colors.HexColor('#111827')),
            'company': ParagraphStyle('C', parent=base['Normal'], fontSize=11, textColor=colors.HexColor('#374151'), leading=14, alignment=2),
            'normal': ParagraphStyle('N', parent=base['Normal'], fontSize=9, leading=12, textColor=colors.HexColor('#374151')),
            'normal_right': ParagraphStyle('NR', parent=base['Normal'], fontSize=9, leading=12, alignment=2, textColor=colors.HexColor('#374151')),
            'bold': ParagraphStyle('B', parent=base['Normal'], fontSize=9, leading=12, fontName='Helvetica-Bold', textColor=colors.HexColor('#111827')),
            'bold_right': ParagraphStyle('BR', parent=base['Normal'], fontSize=9, leading=12, fontName='Helvetica-Bold', alignment=2),
            'small': ParagraphStyle('S', parent=base['Normal'], fontSize=8, leading=10, textColor=colors.HexColor('#9ca3af')),
            'terms': ParagraphStyle('TM', parent=base['Normal'], fontSize=8, leading=11, textColor=colors.HexColor('#6b7280')),
        },
        'table_style': _minimal_table_style(),
    }


def _minimal_table_style():
    light = colors.HexColor('#e5e7eb')
    return TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f9fafb')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#374151')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LINEBELOW', (0, 0), (-1, 0), 0.8, light),
        ('LINEBELOW', (0, 1), (-1, -2), 0.3, colors.HexColor('#f3f4f6')),
        ('LINEBELOW', (0, -1), (-1, -1), 0.8, light),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ])


# ── Registry ────────────────────────────────────────────────────────────────

TEMPLATE_CONFIGS = {
    'classic': get_classic_config,
    'modern': get_modern_config,
    'elegant': get_elegant_config,
    'minimal': get_minimal_config,
}

TEMPLATE_INFO = [
    {'key': 'classic', 'name': 'Classic', 'description': 'Traditional business layout with red accents and clean table borders'},
    {'key': 'modern', 'name': 'Modern', 'description': 'Bold navy header with blue accents and alternating row stripes'},
    {'key': 'elegant', 'name': 'Elegant', 'description': 'Luxury feel with gold/amber accents and serif typography'},
    {'key': 'minimal', 'name': 'Minimal', 'description': 'Ultra-clean design with minimal borders and soft grey tones'},
]


def get_template_config(template_key='classic'):
    """Return the config dict for a given template key."""
    factory = TEMPLATE_CONFIGS.get(template_key, get_classic_config)
    return factory()
