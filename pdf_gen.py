import os
import json
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm

def generate_invoice_pdf(invoice, output_path):
    # invoice is a dict containing:
    # invoice_number, date, client_name, client_email, client_phone, items (list of dicts), total_amount, status, special_notes
    
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=1.5*cm,
        leftMargin=1.5*cm,
        topMargin=1.5*cm,
        bottomMargin=1.5*cm
    )
    
    story = []
    
    # Setup styles
    styles = getSampleStyleSheet()
    
    # Custom high-end styles matching Koulla's brand
    title_style = ParagraphStyle(
        'InvoiceTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=colors.HexColor('#202020')
    )
    
    brand_sub_style = ParagraphStyle(
        'BrandSub',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#c5a880')
    )
    
    meta_label_style = ParagraphStyle(
        'MetaLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#202020')
    )
    
    meta_val_style = ParagraphStyle(
        'MetaValue',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#555555')
    )
    
    body_bold_style = ParagraphStyle(
        'BodyBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#202020')
    )
    
    th_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=12,
        textColor=colors.white
    )
    
    td_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#333333')
    )
    
    notes_style = ParagraphStyle(
        'NotesStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#666666')
    )

    # 1. Header Layout Table (Brand vs Invoice Title)
    header_data = [
        [
            Paragraph("HEAVEN IN A BITE", title_style),
            Paragraph(f"INVOICE", title_style)
        ],
        [
            Paragraph("BESPOKE CAKES & PLATTERS", brand_sub_style),
            Paragraph(f"No: {invoice['invoice_number']}", ParagraphStyle('No', parent=brand_sub_style, fontName='Helvetica-Bold', alignment=2))
        ]
    ]
    
    header_table = Table(header_data, colWidths=[9*cm, 9*cm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (1,0), (1,-1), 'RIGHT'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 15))
    
    # Thin elegant partition line
    divider = Table([[""]], colWidths=[18*cm])
    divider.setStyle(TableStyle([
        ('LINEABOVE', (0,0), (-1,-1), 1.5, colors.HexColor('#c5a880')),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(divider)
    story.append(Spacer(1, 20))
    
    # 2. Company Details & Client Details Side-by-Side Table
    info_data = [
        [
            Paragraph("FROM (Baking Studio):", meta_label_style),
            Paragraph("TO (Valued Client):", meta_label_style)
        ],
        [
            Paragraph("Koulla / Heaven in a Bite", meta_val_style),
            Paragraph(invoice['client_name'], ParagraphStyle('BoldVal', parent=meta_val_style, fontName='Helvetica-Bold'))
        ],
        [
            Paragraph("23 First Street, Bardene Boksburg", meta_val_style),
            Paragraph(f"Date: {invoice['date']}", meta_val_style)
        ],
        [
            Paragraph("Koulla@heaveninabite.co.za", meta_val_style),
            Paragraph(f"Status: <font color='{'#2e7d32' if invoice['status'] == 'Paid' else '#c62828'}'><b>{invoice['status'].upper()}</b></font>", meta_val_style)
        ],
        [
            Paragraph("+27 84 202 0100", meta_val_style),
            Paragraph("", meta_val_style)
        ]
    ]
    
    info_table = Table(info_data, colWidths=[9*cm, 9*cm])
    info_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('TOPPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 25))
    
    # 3. Items Table Header & Content
    # Setup dynamic line items
    items_list = invoice['items']
    if isinstance(items_list, str):
        items_list = json.loads(items_list)
        
    table_data = [[
        Paragraph("Description", th_style),
        Paragraph("Qty", th_style),
        Paragraph("Unit Price (ZAR)", th_style),
        Paragraph("Subtotal (ZAR)", th_style)
    ]]
    
    for item in items_list:
        qty = int(item.get('qty', 1))
        price = float(item.get('price', 0.0))
        subtotal = qty * price
        table_data.append([
            Paragraph(item.get('description', ''), td_style),
            Paragraph(str(qty), td_style),
            Paragraph(f"R {price:,.2f}", td_style),
            Paragraph(f"R {subtotal:,.2f}", ParagraphStyle('Rtd', parent=td_style, alignment=2))
        ])
        
    # Append Total Row
    table_data.append([
        Paragraph("Total Outstanding Balance:", ParagraphStyle('TotalLabel', parent=body_bold_style, alignment=2)),
        "", "",
        Paragraph(f"R {float(invoice['total_amount']):,.2f}", ParagraphStyle('TotalVal', parent=body_bold_style, textColor=colors.HexColor('#aa8c62'), alignment=2))
    ])
    
    items_table = Table(table_data, colWidths=[9.5*cm, 1.5*cm, 3.5*cm, 3.5*cm])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#202020')),
        ('ALIGN', (0,0), (-1,0), 'LEFT'),
        ('ALIGN', (1,1), (2,-1), 'LEFT'),
        ('ALIGN', (3,1), (3,-1), 'RIGHT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ('LINEBELOW', (0,1), (-1,-2), 0.5, colors.HexColor('#e0d8cb')),
        ('SPAN', (0,-1), (2,-1)), # Span total label across qty & price
        ('LINEABOVE', (0,-1), (-1,-1), 1.5, colors.HexColor('#202020')),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 30))
    
    # 4. Special Notes & Payment Instructions
    if invoice.get('special_notes'):
        story.append(Paragraph("Special Notes & Client Instructions:", meta_label_style))
        story.append(Spacer(1, 5))
        story.append(Paragraph(invoice['special_notes'], notes_style))
        story.append(Spacer(1, 20))
        
    story.append(Paragraph("Banking Payment Details:", meta_label_style))
    story.append(Spacer(1, 5))
    payment_details = """
    <b>Bank:</b> FNB (First National Bank)<br/>
    <b>Account Name:</b> KK Constantinou<br/>
    <b>Account Number:</b> 63182442920<br/>
    <b>Branch Code:</b> 253442<br/>
    <b>Reference:</b> Please use Invoice Number: <b>{}</b>
    """.format(invoice['invoice_number'])
    
    story.append(Paragraph(payment_details, ParagraphStyle('Payment', parent=td_style, leading=14)))
    story.append(Spacer(1, 40))
    
    # Centered soft thank you note
    story.append(Paragraph("Thank you for choosing Heaven in a Bite! We appreciate your custom.", ParagraphStyle('ThankYou', parent=brand_sub_style, fontSize=11, alignment=1)))
    
    doc.build(story)
