# watermark = "./watermark.png"
output_file = "./student_eligibility_report.pdf"

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.graphics import renderPDF
from svglib.svglib import svg2rlg
from reportlab.pdfgen import canvas
import os


PROFILE_KEY_VALUE_MAP = {
    "role": "Roll",
    "name": "Namn",
    "email": "Epost",
    "gender": "Kön",
    "age": "Ålder",
    "study_level": "Studienivå",
    "municipality": "Kommun",
    "purpose_of_funding": "Syfte_med_finansiering",
    "language": "Språk",
    "subject": "Ämne"
}

# English field names
PROFILE_KEY_VALUE_MAP_EN = {
    "role": "Role",
    "name": "Name",
    "email": "Email",
    "gender": "Gender",
    "age": "Age",
    "study_level": "Study Level",
    "municipality": "Municipality",
    "purpose_of_funding": "Purpose of Funding",
    "language": "Language",
    "subject": "Subject"
}

# Fields to exclude from PDF output (removed from frontend)
EXCLUDED_PROFILE_FIELDS = {
    "elite_athlete", "elitidrottare",
    "sport", "sport_name", "sportnamn",
    "education_level_option",
    "education_level_other",
    "include_municipality_filter",
    "admin_check", "admin_verified", "paid", "email_verified"
}

SCHOLARSHIP_KEY_VALUE_MAP_SV = {
    "Name": "Namn",
    "Purpose": "Ändamål",
    "Study Level": "Utbildningsnivå",
    "Municipality": "Kommun",
    "Category": "Kategori",
    "Email": "E-post",
    "Website": "Webbplats",
    "Phone": "Telefon",
    "Assets": "Tillgångar",
    "Main Address": "Huvudadress",
    "Postal Code": "Postnummer",
    "City": "Stad",
    "County": "Län",
    "Sport": "Sport",
    "Namn": "Namn",
    "Ändamål": "Ändamål",
    "Utbildningsnivå": "Utbildningsnivå",
    "Kommun": "Kommun",
    "Kategori": "Kategori",
    "Epost": "E-post",
    "Websida": "Webbplats",
    "Telefon": "Telefon",
    "Tillgångar": "Tillgångar",
    "Huvudadress": "Huvudadress",
    "Postnr": "Postnummer",
    "Stad": "Stad",
    "Län": "Län",
}


def create_pdf(data, user_profile, watermark_path, output_path):
    # Setup PDF
    doc = SimpleDocTemplate(output_path, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    # story.append(PageBreak())
    # Title

    if user_profile.get('language', '') == 'sv':
        story.append(Paragraph("Rapport om studentbehörighet", styles["Title"]))
    else:
        story.append(Paragraph("Student Eligibility Report", styles["Title"]))
    story.append(Spacer(1, 12))

    # User Profile Section
    if user_profile.get('language', '') == 'sv':
        story.append(Paragraph("<b>Studentprofil</b>", styles["Heading2"]))
    else:
        story.append(Paragraph("<b>Student Profile</b>", styles["Heading2"]))
    
    profile = user_profile
    is_swedish = user_profile.get('language', '') == 'sv'
    
    for key, value in profile.items():
        # Skip excluded fields
        if key.lower() in EXCLUDED_PROFILE_FIELDS:
            continue
        
        # Skip empty values
        if not value or value == '':
            continue
        
        # Get the translated field name
        if is_swedish and key in PROFILE_KEY_VALUE_MAP:
            display_key = PROFILE_KEY_VALUE_MAP[key]
        elif not is_swedish and key in PROFILE_KEY_VALUE_MAP_EN:
            display_key = PROFILE_KEY_VALUE_MAP_EN[key]
        else:
            display_key = key.replace('_', ' ').title()
        
        story.append(Paragraph(f"<b>{display_key}</b>: {value}", styles["Normal"]))
    
    story.append(Spacer(1, 12))

    # Eligible Scholarships Section
    story.append(Paragraph("<b>Eligible Scholarships</b>", styles["Heading2"]))

    # for scholarship in data["matching_scholarships"]:
    for scholarship in data:
        scholarship_name = scholarship['Name'] \
            if 'Name' in scholarship.keys() else scholarship['Namn']

        # print(f"DE..BUG: {scholarship_name}", scholarship.get('Name'), scholarship.get('Namn'))
        story.append(Paragraph(f"<b>{scholarship_name}</b>", styles["Heading3"]))

        # Convert dict to table with text wrapping
        table_data = []

        if user_profile.get('language' , '') == 'en':
            wrapped_value = Paragraph(str(scholarship_name), styles["Normal"])
            table_data.append(['Name', wrapped_value])

        else:
            wrapped_value = Paragraph(str(scholarship_name), styles["Normal"])
            table_data.append(['Namn', wrapped_value])

        if 'Name' in scholarship.keys():
            scholarship.pop('Name')
        if 'Namn' in scholarship.keys():
            scholarship.pop('Namn')
        for key, value in scholarship.items():
            if key in ['Base Score', 'Relevance Score', 'Entity Bonus', 'Adjusted Score']:
                continue
            if value and str(value) != "NaN":
                # Wrap the value in a Paragraph for text wrapping
                wrapped_value = Paragraph(str(value), styles["Normal"])
                # Translate key to Swedish if user language is Swedish
                display_key = key
                if user_profile.get('language', '') == 'sv' and key in SCHOLARSHIP_KEY_VALUE_MAP_SV:
                    display_key = SCHOLARSHIP_KEY_VALUE_MAP_SV[key]
                table_data.append([display_key, wrapped_value])

        table = Table(table_data, colWidths=[120, 350])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.black),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),  # Align to top for wrapped text
            ("LEFTPADDING", (0, 0), (-1, -1), 6),  # Add padding
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(table)
        story.append(Spacer(1, 24))

    # # Watermark function (tiled, 20% opacity) - COMMENTED OUT
    # def add_watermark(c, doc):
    #     width, height = A4
    #     c.saveState()
    #     c.drawImage(watermark, 0, height//3, width, height//3, 
    #                mask='auto', preserveAspectRatio=True)
    #     c.restoreState()
    #     return
    #
    #     drawing = svg2rlg(watermark_path)
    #     width, height = A4
    #     scale_x = width / drawing.width
    #     scale_y = scale_x  # keep proportions
    #
    #     drawing.width *= scale_x
    #     drawing.height *= scale_y
    #     drawing.scale(scale_x, scale_y)
    #
    #     c.saveState()
    #     c.setFillColorRGB(1,1,1)
    #     # Proper transparency handling (20%)
    #     if hasattr(c, "setFillAlpha"):
    #         c.setFillAlpha(0.9)
    #     elif hasattr(c, "setAlpha"):
    #         c.setAlpha(0.9)
    #
    #     renderPDF.draw(drawing, c, 0, height//3)
    #     # # Repeat watermark vertically
    #     # y = 0
    #     # while y < height:
    #     #     renderPDF.draw(drawing, c, 0, y/2)
    #     #     y += drawing.height
    #
    #     c.restoreState()

    # Build PDF without watermark
    doc.build(story)


if __name__ == "__main__":
    # Example Data
    data = {
        "user_profile": {
            "name": "Anna Karlsson",
            "email": "anna@example.com",
            "gender": "Kvinna",
            "age": 23,
            "level": "Universitet",
            "athlete": "Nej",
            "municipality": "Stockholm"
        },
        "eligible_scholarships": [
            {
                "Namn": "Knut och Alice Wallenbergs Stiftelse",
                "Huvudadress": "Box 16066",
                "Postnr": 10322,
                "Postort": "STOCKHOLM",
                "Telefon": "08-54501780",
                "Län": "Stockholms län",
                "Kommun": "Stockholm",
                "Tillgångar": 6899855000,
                "Ändamål": "Att främja vetenskaplig forskning och undervisnings- eller studieverksamhet av landsgagnelig innebörd...",
            },
            {
                "Namn": "Nordea Sveriges Vinstandelsstiftelse",
                "Huvudadress": "M514",
                "Postnr": "105 71",
                "Postort": "STOCKHOLM",
                "Telefon": "010-1571863",
                "Län": "Stockholms län",
                "Kommun": "Stockholm",
                "Tillgångar": 1990073000,
                "Ändamål": "Stiftelsens ändamål skall vara att ge Nordea Bank Abp:s personal i Sverige delägarintresse...",
            }
        ]
    }

    # watermark = "/mnt/data/7145370c-e98d-4dc7-9cac-01d6bc1eefc7.svg"
    # output_file = "/mnt/data/student_eligibility_report.pdf"
    create_pdf(data, watermark, output_file)
    print(f"PDF generated at {output_file}")