import io
import base64
import qrcode

def generate_sample_tag_id(test_request_id):
    """Generates a formatted sample tag ID string like RRI-SMP-20260907-XXXX"""
    short_id = str(test_request_id).replace('-', '').upper()[:6]
    return f"RRI-SMP-{short_id}"

def generate_qr_base64(data_string):
    """Generates a QR code image as a base64 encoded PNG data URI string."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=2,
    )
    qr.add_data(data_string)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0F4C81", back_color="white")
    
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    b64_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
    buffer.close()
    return f"data:image/png;base64,{b64_str}"
