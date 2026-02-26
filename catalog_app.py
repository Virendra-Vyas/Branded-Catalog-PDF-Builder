import io
import json
import zipfile
from datetime import date
from typing import Dict, List, Tuple

import streamlit as st
from PIL import Image

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader


def read_zip_images(zip_bytes: bytes) -> List[Tuple[str, Image.Image]]:
    out = []
    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as z:
        for name in sorted(z.namelist()):
            if name.lower().endswith((".png", ".jpg", ".jpeg")):
                img = Image.open(io.BytesIO(z.read(name))).convert("RGBA")
                out.append((name, img))
    return out


def img_to_reader(img: Image.Image) -> ImageReader:
    # ReportLab handles RGB best; keep white background for transparency
    if img.mode == "RGBA":
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3])
        img = bg
    else:
        img = img.convert("RGB")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return ImageReader(buf)


def build_catalog_pdf(
    logo_img: Image.Image,
    images: List[Tuple[str, Image.Image]],
    title: str,
    subtitle: str,
    footer: str
) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    W, H = letter

    # --- Cover ---
    c.setTitle(title)
    c.setFont("Helvetica-Bold", 26)
    c.drawString(1.0 * inch, H - 1.4 * inch, title)

    c.setFont("Helvetica", 14)
    c.drawString(1.0 * inch, H - 1.8 * inch, subtitle)
    c.setFont("Helvetica", 11)
    c.drawString(1.0 * inch, H - 2.2 * inch, f"Generated: {date.today().isoformat()}")

    # Logo top-right
    if logo_img:
        lr = img_to_reader(logo_img)
        logo_w = 1.6 * inch
        logo_h = 1.0 * inch
        c.drawImage(lr, W - logo_w - 0.8 * inch, H - logo_h - 0.9 * inch, width=logo_w, height=logo_h, mask='auto')

    # Decorative line
    c.line(1.0 * inch, H - 2.5 * inch, W - 1.0 * inch, H - 2.5 * inch)

    c.setFont("Helvetica", 10)
    c.drawString(1.0 * inch, 0.8 * inch, footer)
    c.showPage()

    # --- One page per image (simple but clean) ---
    for idx, (name, img) in enumerate(images, start=1):
        # Header
        c.setFont("Helvetica-Bold", 18)
        c.drawString(1.0 * inch, H - 1.0 * inch, f"Design {idx:02d}")

        c.setFont("Helvetica", 10)
        c.drawString(1.0 * inch, H - 1.25 * inch, f"Source: {name}")

        # Logo small top-right
        if logo_img:
            lr = img_to_reader(logo_img)
            logo_w = 1.2 * inch
            logo_h = 0.75 * inch
            c.drawImage(lr, W - logo_w - 0.8 * inch, H - logo_h - 0.9 * inch, width=logo_w, height=logo_h, mask='auto')

        # Image area
        margin_x = 1.0 * inch
        top_y = H - 1.6 * inch
        box_w = W - 2 * margin_x
        box_h = H - 3.0 * inch

        ir = img_to_reader(img)
        # Fit image into box while preserving aspect
        iw, ih = img.size
        scale = min(box_w / iw, box_h / ih)
        draw_w = iw * scale
        draw_h = ih * scale
        x = margin_x + (box_w - draw_w) / 2
        y = 1.2 * inch + (box_h - draw_h) / 2
        c.drawImage(ir, x, y, width=draw_w, height=draw_h, mask='auto')

        # Footer
        c.setFont("Helvetica", 10)
        c.drawString(1.0 * inch, 0.8 * inch, footer)

        c.showPage()

    c.save()
    return buf.getvalue()


st.set_page_config(page_title="Catalog PDF Builder", layout="wide")
st.title("Branded Catalog PDF Builder")
st.caption("Upload extracted images → generate a clean, branded multi-page PDF catalog.")

logo_file = st.file_uploader("Upload brand logo (PNG/JPG)", type=["png", "jpg", "jpeg"])
zip_file = st.file_uploader("Upload ZIP of extracted images", type=["zip"])

title = st.text_input("Catalog title", "Sock Design Catalog")
subtitle = st.text_input("Subtitle", "Automated design-board → catalog demo")
footer = st.text_input("Footer contact line", "Sockrates • Florida, USA • sales@sockrates.com • (xxx) xxx-xxxx")

logo_img = None
if logo_file:
    logo_img = Image.open(logo_file).convert("RGBA")
    st.image(logo_img, caption="Logo preview", width=220)

if zip_file:
    images = read_zip_images(zip_file.read())
    st.success(f"Loaded {len(images)} image(s) from ZIP.")
    if images:
        st.image(images[0][1], caption=f"Example: {images[0][0]}", width=400)

    if st.button("Generate PDF", type="primary"):
        pdf_bytes = build_catalog_pdf(
            logo_img=logo_img,
            images=images,
            title=title,
            subtitle=subtitle,
            footer=footer
        )
        st.download_button(
            "Download catalog PDF",
            data=pdf_bytes,
            file_name="catalog.pdf",
            mime="application/pdf"
        )
else:
    st.info("Upload a ZIP of images to generate a PDF catalog.")