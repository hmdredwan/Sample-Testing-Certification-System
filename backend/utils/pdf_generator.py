import io
import qrcode
import hashlib
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

def generate_qr_code_image_buffer(url):
    """Generates a QR code image buffer for a given verification URL."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=6,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0F4C81", back_color="white")
    
    img_buffer = io.BytesIO()
    img.save(img_buffer, format="PNG")
    img_buffer.seek(0)
    return img_buffer

def generate_test_certificate_pdf(certificate, verification_url="http://localhost:3000/verify-certificate/"):
    """
    Generates a high-quality PDF Certificate for an RRI TestRequest.
    Returns bytes of the generated PDF file.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    story = []
    styles = getSampleStyleSheet()

    # Custom Paragraph Styles
    title_style = ParagraphStyle(
        'HeaderTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        alignment=1, # Center
        textColor=colors.HexColor('#0F4C81')
    )
    
    subtitle_style = ParagraphStyle(
        'HeaderSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=13,
        alignment=1,
        textColor=colors.HexColor('#4A5568')
    )

    cert_title_style = ParagraphStyle(
        'CertTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=18,
        alignment=1,
        textColor=colors.HexColor('#1A365D')
    )

    body_style = ParagraphStyle(
        'CertBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor('#2D3748')
    )

    body_bold = ParagraphStyle(
        'CertBodyBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor('#1A202C')
    )

    header_table_cell = ParagraphStyle(
        'HeaderTableCell',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=11,
        textColor=colors.white
    )

    # 1. Header Block
    story.append(Paragraph("RIVER RESEARCH INSTITUTE (RRI)", title_style))
    story.append(Spacer(1, 3))
    story.append(Paragraph("Ministry of Water Resources | Government of the People's Republic of Bangladesh", subtitle_style))
    story.append(Paragraph("Faridpur-7800, Bangladesh | Web: www.rri.gov.bd", subtitle_style))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#0F4C81'), spaceAfter=12))

    # 2. Certificate Title & QR Code Layout (2 columns: Title Left/Center, QR Right)
    full_verification_url = f"{verification_url.rstrip('/')}/{certificate.verification_code}"
    qr_buffer = generate_qr_code_image_buffer(full_verification_url)
    qr_image = Image(qr_buffer, width=1.1*inch, height=1.1*inch)

    cert_header_text = [
        Paragraph("OFFICIAL TEST CERTIFICATE & ANALYTICAL REPORT", cert_title_style),
        Spacer(1, 4),
        Paragraph(f"<b>Certificate No:</b> {certificate.certificate_number}", subtitle_style),
        Paragraph(f"<b>Date of Issue:</b> {certificate.issued_at.strftime('%B %d, %Y')}", subtitle_style),
        Paragraph(f"<b>Verification Code:</b> {certificate.verification_code[:8]}...{certificate.verification_code[-6:]}", subtitle_style),
    ]

    header_layout_table = Table(
        [[cert_header_text, qr_image]],
        colWidths=[4.8*inch, 1.4*inch]
    )
    header_layout_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (1,0), (1,0), 'RIGHT'),
    ]))
    story.append(header_layout_table)
    story.append(Spacer(1, 12))

    # 3. Sample Metadata Table
    test_req = certificate.test_request
    metadata_data = [
        [
            Paragraph("<b>Sample Tag ID:</b>", body_style),
            Paragraph(test_req.sample_tag_id or str(test_req.id)[:13], body_bold),
            Paragraph("<b>Category:</b>", body_style),
            Paragraph(test_req.get_sample_category_display(), body_bold)
        ],
        [
            Paragraph("<b>Client Name:</b>", body_style),
            Paragraph(test_req.user.get_full_name() or test_req.user.username, body_bold),
            Paragraph("<b>Test Requested:</b>", body_style),
            Paragraph(test_req.test_type.name, body_bold)
        ],
        [
            Paragraph("<b>Sampling Location:</b>", body_style),
            Paragraph(test_req.sampling_location or "N/A", body_style),
            Paragraph("<b>Collection Date:</b>", body_style),
            Paragraph(str(test_req.collection_date or "N/A"), body_style)
        ],
        [
            Paragraph("<b>Assigned Officer:</b>", body_style),
            Paragraph(test_req.officer.get_full_name() if test_req.officer else "RRI Scientific Officer", body_style),
            Paragraph("<b>Lab Technician:</b>", body_style),
            Paragraph(test_req.lab_technician.get_full_name() if test_req.lab_technician else "RRI Lab Analyst", body_style)
        ]
    ]

    meta_table = Table(metadata_data, colWidths=[1.3*inch, 2.0*inch, 1.3*inch, 1.6*inch])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F7FAFC')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#E2E8F0')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#EDF2F7')),
        ('PADDING', (0,0), (-1,-1), 5),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 14))

    # 4. Test Results Section
    story.append(Paragraph("<b>LABORATORY ANALYSIS & TEST RESULTS</b>", ParagraphStyle('SubHeading', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=11, textColor=colors.HexColor('#0F4C81'))))
    story.append(Spacer(1, 6))

    result_text = test_req.result or "Standard physical laboratory testing executed according to RRI guidelines."
    measurements_text = test_req.lab_measurements or "No specific laboratory parameters submitted."

    results_table_data = [
        [Paragraph("Parameter / Observation", header_table_cell), Paragraph("Analysis Result & Value", header_table_cell)],
        [Paragraph("<b>Primary Test Result Summary</b>", body_style), Paragraph(result_text.replace('\n', '<br/>'), body_style)],
        [Paragraph("<b>Detailed Lab Measurements</b>", body_style), Paragraph(measurements_text.replace('\n', '<br/>'), body_style)],
        [Paragraph("<b>Compliance Standard</b>", body_style), Paragraph("RRI Laboratory Standard Operational Procedures (SOP-2026)", body_style)]
    ]

    results_table = Table(results_table_data, colWidths=[2.2*inch, 4.0*inch])
    results_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (1,0), colors.HexColor('#0F4C81')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E0')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('PADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(results_table)
    story.append(Spacer(1, 16))

    # 5. Security Hash & Digital Signature Block
    sig_hash = certificate.digital_signature_hash or hashlib.sha256(f"{certificate.certificate_number}-{certificate.verification_code}".encode()).hexdigest()
    
    sig_block_data = [
        [
            Paragraph(f"<b>Digital Verification Hash:</b><br/><font size=7 color='#718096'>{sig_hash}</font>", body_style),
            Paragraph("<b>Authorized Signature:</b><br/><br/><b>Chief Scientific Officer</b><br/>River Research Institute (RRI)", body_style)
        ]
    ]

    sig_table = Table(sig_block_data, colWidths=[4.2*inch, 2.0*inch])
    sig_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#EDF2F7')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E0')),
        ('PADDING', (0,0), (-1,-1), 8),
        ('ALIGN', (1,0), (1,0), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(sig_table)
    story.append(Spacer(1, 14))

    # 6. Bottom Notice / Verification Footer
    footer_text = f"Scan the QR code above or visit <b>{full_verification_url}</b> to verify certificate authenticity.<br/>This is an official computer-generated digital certificate issued by River Research Institute."
    story.append(Paragraph(footer_text, ParagraphStyle('Footer', parent=styles['Normal'], fontName='Helvetica-Oblique', fontSize=8, leading=10, alignment=1, textColor=colors.HexColor('#718096'))))

    # Build PDF
    doc.build(story)
    pdf_data = buffer.getvalue()
    buffer.close()
    return pdf_data
