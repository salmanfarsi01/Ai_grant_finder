from dotenv import load_dotenv

import app
load_dotenv()
import jwt
import json
import os

import uuid
import datetime
from django.shortcuts import render
from django.conf import settings
from django.core.mail import send_mail
from django.core.files import File
from django.db import models

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.generics import get_object_or_404
from rest_framework.exceptions import ValidationError

from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes

import stripe

from .serializers import MockSerializer, ReviewSerializer, PreDefinedScholarshipSerializer #, ScholarshipApplicantSerializer
from . import ai_utils
from . import stipo54
# from . import stepo_47rag
from . import report_utils
from .models import ScholarshipApplicant, Review, FAQ, Coupon, PreDefinedScholarship, SiteConfig
from deep_translator import GoogleTranslator
import re

# Unicode cleaning regex and replacement map for PDF rendering
_BOX_CLEAN = re.compile(
    r'[\u25A0\u25AA\u25AB\u25FB\u25FC\u25FD\u25FE'
    r'\u2B1B\u2B1C\u2B50\u2B55'
    r'\u00AD\u200B\u200C\u200D\uFEFF'
    r'\u2028\u2029'
    r'\x00-\x08\x0B\x0C\x0E-\x1F]'
)
_BOX_REPLACE = {
    '\u2018': "'", '\u2019': "'",
    '\u201C': '"', '\u201D': '"',
    '\u2013': '-', '\u2014': '-',
    '\u2026': '...', '\u00AB': '"',
    '\u00BB': '"', '\u00A0': ' ',
    '\u2022': '-',
}

def _clean_raw(text):
    """Remove problematic Unicode characters that cause black boxes in PDF"""
    if not isinstance(text, str):
        return text
    text = _BOX_CLEAN.sub('', text)
    for char, rep in _BOX_REPLACE.items():
        text = text.replace(char, rep)
    return text

def clean_scholarship_data(scholarships):
    """Recursively clean all string values in scholarship dictionaries"""
    if isinstance(scholarships, list):
        return [clean_scholarship_data(item) for item in scholarships]
    elif isinstance(scholarships, dict):
        cleaned = {}
        for key, value in scholarships.items():
            if isinstance(value, str):
                cleaned[key] = _clean_raw(value)
            elif isinstance(value, (list, dict)):
                cleaned[key] = clean_scholarship_data(value)
            else:
                cleaned[key] = value
        return cleaned
    else:
        return scholarships

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


# def translate_field(text, target_language="en", source_language="sv", debug=False):
#     """Translate text from Swedish to English using GoogleTranslator"""
#     if not text or not isinstance(text, str):
#         return text
    
#     # Only translate SV→EN (data is stored in Swedish)
#     if target_language.lower() == "en" and source_language.lower() == "sv":
#         try:
#             translated = GoogleTranslator(source_language='sv', target_language='en').translate(text)
#             return translated
#         except Exception as e:
#             print(f"[translate_field] ERROR translating: {e}")
#             return text
    
#     # For any other direction, return unchanged
#     return text

def translate_field(text, target_language="en", source_language="sv", debug=False):
    if not text or not isinstance(text, str):
        return text
    
    # Clean PDF-incompatible and invisible characters from source text
    # BEFORE translation so they don't appear in either language output.
    # U+25A0/U+25AA = black squares already in Pinecone raw data.
    # Other chars cause rendering failures in PDF fonts.
    import re
    CLEAN_PATTERN = re.compile(
        r'[\u25A0\u25AA\u25AB\u25FB\u25FC\u25FD\u25FE'  # black/white squares
        r'\u2B1B\u2B1C\u2B50\u2B55'                      # other geometric shapes
        r'\u00AD'                                          # soft hyphen
        r'\u200B\u200C\u200D\uFEFF'                       # zero-width chars
        r'\u2028\u2029'                                    # line/paragraph separators
        r'\x00-\x08\x0B\x0C\x0E-\x1F]'                  # control characters
    )
    text = CLEAN_PATTERN.sub('', text)
    
    # Replace typographic chars PDF fonts struggle with
    REPLACE_MAP = {
        '\u2018': "'",    # left single quote
        '\u2019': "'",    # right single quote
        '\u201C': '"',    # left double quote
        '\u201D': '"',    # right double quote
        '\u2013': '-',    # en dash
        '\u2014': '-',    # em dash
        '\u2026': '...',  # ellipsis
        '\u00AB': '"',    # left angle quote
        '\u00BB': '"',    # right angle quote
        '\u00A0': ' ',    # non-breaking space
        '\u2022': '-',    # bullet
    }
    for char, replacement in REPLACE_MAP.items():
        text = text.replace(char, replacement)
    
    # Now translate if needed
    if target_language.lower() == "en" and source_language.lower() == "sv":
        try:
            translated = GoogleTranslator(
                source_language='sv', target_language='en'
            ).translate(text)
            # Apply same cleaning to translated output in case
            # Google Translate introduces new special chars
            if translated:
                translated = CLEAN_PATTERN.sub('', translated)
                for char, replacement in REPLACE_MAP.items():
                    translated = translated.replace(char, replacement)
            return translated
        except Exception as e:
            print(f"[translate_field] ERROR translating: {e}")
            return text
    
    return text


def translate_predefined_scholarships(scholarships, output_language="en"):
    """Translate Purpose/Ändamål fields and field names in predefined scholarships based on language"""
    
    # Field name translations from English to Swedish
    field_name_translations_sv = {
        "Subject": "Ämne",
        "Purpose": "Ändamål",
        "Municipality": "Kommun",
        "Category": "Kategori",
        "Email": "Epost",
        "Website": "Websida",
        "Phone": "Telefon",
        "Assets": "Tillgångar",
        "MainHuvudadress": "Huvudadress",
        "PostalPostnr": "Postnr",
        "City": "Stad",
        "County": "Län",
        "Sport": "Sport",
        "Name": "Namn",
    }
    
    translated = []
    for idx, sch in enumerate(scholarships):
        sch_copy = sch.copy() if isinstance(sch, dict) else sch
        
        # Handle Swedish language: rename field keys only (data is already in Swedish)
        if output_language.lower() == "sv":
            sch_sv = {}
            for key, value in sch_copy.items():
                # Translate field name if mapping exists, otherwise keep original
                translated_key = field_name_translations_sv.get(key, key)
                # NO translation of Purpose content - it's already in Swedish!
                sch_sv[translated_key] = value
            translated.append(sch_sv)
        
        # Handle English language: translate Purpose from Swedish to English
        elif output_language.lower() == "en":
            # Translate Purpose field from Swedish to English
            if "Purpose" in sch_copy and isinstance(sch_copy.get("Purpose"), str):
                sch_copy["Purpose"] = translate_field(sch_copy["Purpose"], target_language="en", source_language="sv")
            translated.append(sch_copy)
        
        else:
            translated.append(sch_copy)
    
    return translated

def _matches_any(text, terms):
    """
    Whole-word substring match for short terms (≤3 chars),
    plain substring for longer terms.
    Prevents 'it' matching inside 'political', 'entity' etc.
    """
    for term in terms:
        if len(term) <= 3:
            # word boundary match for short terms
            if re.search(r'\b' + re.escape(term) + r'\b', text):
                return True
        else:
            if term in text:
                return True
    return False

@api_view(['post'])
def submit_application(request):
    SITE_CONFIG = settings.SITE_CONFIG

    email = request.data.get('email')
    form_data = request.data

    # if application_type in ('organization', 'Organisation'):
    #     profile = {
    #         f"{application_type}": request.data.get('organization_name'),

    #     }

    application, _created = ScholarshipApplicant.objects.update_or_create(
        email=request.data.get('email'),
        defaults={
            "form_data": form_data
        }
    )
    application.admin_verified = bool(SITE_CONFIG and not SITE_CONFIG.admin_check)
    application.email_verified = False
    print("DEBUG ADMIN VER...: ", application.admin_verified)
    send_mail(
        subject="Application submitted",
        message=f"plz use the otp: {application.otp}",
        html_message="",
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[application.email]
    )
    #     Thread(
    #     target=send_mail,
    #     kwargs={
    #         "subject": email_subject,
    #         "message": f"your password reset otp: {user.otp}",
    #         "html_message": email_body,
    #         "from_email": settings.EMAIL_HOST_USER,
    #         "recipient_list": [email],
    #         "fail_silently": False,
    #     }
    # ).start()
    application.save()
    return Response({"msg": "your form is submitted"})


@api_view(['post'])
def send_verification_code(request, email):
    # email = request.data.get('email')
    application = get_object_or_404(ScholarshipApplicant, email=email)
    send_mail(
        subject="Application submitted",
        message=f"here is your otp: {application.otp}",
        html_message=f"here is your otp: {application.otp}",
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[email]
    )
    return Response({
        "message": "a message with a verification code"
                   " has been sent to your email."
    })
    pass


@api_view(['post'])
def verify_otp(request):
    email = request.data.get('email')
    otp = request.data.get('otp')

    print("DEBUG PAYLOD OTP:")
    print(email)
    print(otp)
    if email is None:
        raise ValidationError({"error": "email is required"})

    if otp is None:
        raise ValidationError({"error": "otp is required"})
    application = get_object_or_404(ScholarshipApplicant, email=email)
    print('lt: ', application.otp)

    if otp != application.otp:
        raise ValidationError({"error": "invalid otp"})
        pass
    application.email_verified = True
    # ai_utils.find_scholarships(
    #     user_data
    # )
    application.refresh_otp()
    # application.email_verified=True

    verify_token = jwt.encode({
            'email': application.email,
            "exp": datetime.datetime.now(datetime.UTC)\
                   +datetime.timedelta(minutes=500),
        },
        settings.SECRET_KEY,
        algorithm='HS256'
    )
    application.save()
    return Response({
        "application_token": verify_token
    })

@api_view(['post'])
def generate_data(request):
    application_token = request.data.get('application_token')
    if not application_token:
        raise ValidationError({"error": "application was not provided"})

    try:
        payload = jwt.decode(
            application_token,
            settings.SECRET_KEY,
            algorithms=['HS256']
        )
    except jwt.ExpiredSignatureError as e:
        raise ValidationError({"error": "given token expired"})

    except jwt.PyJWTError as e:
        raise ValidationError({"error": "invalid token"})

    application = get_object_or_404(ScholarshipApplicant, email=payload['email'])
    if application.report_file:
        return Response({
            "success_count": application.success_count
        })

    location = application.form_data.get('municipality')
    language = application.form_data['language']
    print(F"DEBUGING LANGUAGE: {language}")
    

    # report_data = ai_utils.find_scholarships(
    #     settings.DATASET_PATH,
    #     location,
    #     language,
    #     application.form_data,
    # )


    subject = (
        education_level_option
            if (education_level_option:=application.form_data.get('education_level_option'))
            else application.form_data.get('education_level_other')
    )

    print("DEBUGING ROLE *******************  ", application.form_data['role'])
    print("DEBUGING ROLE *******************  ", application.form_data['elite_athlete'])
    
    # Get SiteConfig to retrieve custom prompts if they exist
    site_config = SiteConfig.objects.first()
    user_type = application.form_data['role']
    custom_system_prompt = None
    custom_rerank_prompt = None
    
    if site_config:
        if user_type.lower() == 'individual' or user_type.lower() == 'privatperson':
            custom_system_prompt = site_config.get_filter_prompt_individual()
            custom_rerank_prompt = site_config.get_reranker_prompt_individual()
        elif user_type.lower() == 'organisation' or user_type.lower() == 'organization':
            custom_system_prompt = site_config.get_filter_prompt_organization()
            custom_rerank_prompt = site_config.get_reranker_prompt_organization()
    
    report_data = stipo54.find_scholarships_v2(
        user_purpose=application.form_data['purpose_of_funding'],
        user_type=application.form_data['role'],
        municipality=application.form_data['municipality'],
        gender=application.form_data.get('gender'),
        language=application.form_data['language'],
        municipality_filter=application.form_data.get('include_municipality_filter', False),
        debug=True,  # Enable to see all filtering steps in terminal
        use_llm_rerank=True,
        custom_system_prompt=custom_system_prompt,
        custom_rerank_prompt=custom_rerank_prompt
    )

    # Format AI results - these are raw results from stipo54.find_scholarships_v2()
    formatted_ai_results = stipo54.format_scholarship_json(
        report_data,
        output_language=application.form_data['language']
    )

    # report_data = json.dumps(data)

    # report_data = json.loads(report_data)
    pdf_location = f"{str(uuid.uuid4())}.pdf"

    predefined = PreDefinedScholarship.objects.all()
    
    # Extract study level from form data
    study_level = application.form_data.get('study_level', '').lower()
    # Extract subject from education_level_option AND education_level_other (for "Annat"/Other case)
    education_level_option = application.form_data.get('education_level_option', [])
    education_level_other = application.form_data.get('education_level_other', '')
    subject = None
    
    # Map education_level_option to subject field values
    # Support both old format (economics, engineering, law) and new format
    # Include both regular selection and "Annat" (Other) field
    # Handle both list and string input formats
    education_parts = []
    if education_level_option:
        if isinstance(education_level_option, list):
            education_parts = education_level_option
        else:
            # If it's a string, wrap it in a list (don't use list() which converts to chars)
            education_parts = [str(education_level_option)]
    if education_level_other:
        education_parts.append(education_level_other)
    education_str = ' '.join(education_parts).lower()
    
    print(f"\n[SUBMIT_APPLICATION - DEBUG SUBJECT MAPPING]")
    print(f"  education_level_option: {education_level_option} (type: {type(education_level_option).__name__})")
    print(f"  education_level_other: {education_level_other}")
    print(f"  education_str: {education_str}")
    
    # Detect study level first — subject mapping depends on it
    study_level_lower = study_level.lower()
    if any(t in study_level_lower for t in [
        'undergraduate', 'bachelor', 'kandidat', 'kandidatnivå', 'grundnivå'
    ]):
        detected_level = 'undergraduate'
    elif any(t in study_level_lower for t in [
        'master', 'postgraduate', 'masternivå', 'magister'
    ]):
        detected_level = 'master'
    elif any(t in study_level_lower for t in [
        'phd', 'doctoral', 'doktorand', 'forskarutbildning',
        'doktorsexamen', 'licentiat'
    ]):
        detected_level = 'phd'
    else:
        detected_level = 'unknown'
        subject = None

    if detected_level == 'undergraduate':
        # Undergraduate subject mapping → undergraduate DB keys
        if _matches_any(education_str, ['law', 'political', 'juridik', 'legal', 'statsvetenskap']):
            subject = 'law_political'
        elif _matches_any(education_str, ['engineering', 'technology', 'teknik', 'ingenjörsvetenskap']):
            subject = 'engineering_technology'
        elif _matches_any(education_str, ['economics', 'business', 'ekonomi', 'administration', 'företagsekonomi', 'management']):
            subject = 'economics_business'
        elif _matches_any(education_str, ['medicine', 'health', 'medicin', 'hälsa', 'vårdutbildningar', 'vård']):
            subject = 'medicine_health'
        elif _matches_any(education_str, ['computer', 'it', 'data', 'datavetenskap', 'datalogi', 'datascience']):
            subject = 'cs_it_data'
        elif _matches_any(education_str, ['education', 'pedagogy', 'utbildning', 'pedagogik']):
            subject = 'education_pedagogy'
        elif _matches_any(education_str, ['psychology', 'behavioral', 'psykologi', 'beteendevetenskap']):
            subject = 'psychology_behavioral'
        elif _matches_any(education_str, ['environment', 'sustainability', 'miljö', 'hållbarhet']):
            subject = 'environment_sustainability'
        elif _matches_any(education_str, ['design', 'architecture', 'creative', 'arts', 'arkitektur', 'kreativa']):
            subject = 'design_architecture_arts'
        elif _matches_any(education_str, ['biology', 'chemistry', 'life science', 'biologi', 'kemi', 'naturvetenskap', 'livsvetenskap']):
            subject = 'biology_chemistry_life'

    elif detected_level == 'master':
        # Master's subject mapping → master DB keys (eng_tech_advanced etc.)
        if _matches_any(education_str, ['law', 'llm', 'legal', 'juridik']):
            subject = 'law_llm'
        elif _matches_any(education_str, ['public health', 'epidemiology', 'folkhälsa', 'epidemiologi', 'folkhälsovetenskap']):
            subject = 'public_health_epidemiology'
        elif _matches_any(education_str, ['engineering', 'technology', 'teknik', 'ingenjörsvetenskap', 'cybersecurity', 'supply chain', 'machine engineering']):
            subject = 'eng_tech_advanced'
        elif _matches_any(education_str, ['business', 'management', 'finance', 'accounting', 'international business', 'ekonomi', 'företagsekonomi']):
            subject = 'business_management'
        elif _matches_any(education_str, ['computer', 'digital business', 'data science', 'it', 'datalogi', 'datavetenskap']):
            subject = 'cs_digital_data_advanced'
        elif _matches_any(education_str, ['education', 'pedagogy', 'didactics', 'leadership', 'utbildning', 'pedagogik']):
            subject = 'education_didactics'
        elif _matches_any(education_str, ['environment', 'sustainability', 'urban planning', 'miljö', 'hållbarhet']):
            subject = 'environment_urban'
        elif _matches_any(education_str, ['life science', 'biotechnology', 'biotech', 'livsvetenskap', 'bioteknologi']):
            subject = 'life_science_biotech'
        elif _matches_any(education_str, ['design', 'architecture', 'creative', 'arts', 'arkitektur', 'kreativa']):
            subject = 'design_creative_advanced'
        elif _matches_any(education_str, ['social science', 'social work', 'psychology', 'political science', 'samhällsvetenskap', 'socialt', 'psykologi']):
            subject = 'social_sciences'

        elif detected_level == 'phd':
            # PhD has no subject filtering — always scholarships only
            subject = None

    print(f"\n[SUBJECT MAPPING DEBUG]")
    print(f"  education_str: {education_str}")
    print(f"  detected_level: {detected_level}")
    print(f"  subject (mapped): {subject}")
    
    # If user selected something but no match was found, only show "always" scholarships
    # This prevents irrelevant subject scholarships from appearing
    no_subject_match = (education_level_option or education_level_other) and subject is None
    
    # Use new study level filtering logic
    predefined_always, predefined_filtered = stipo54.get_predefined_scholarships_by_level(
        predefined,
        study_level=study_level,
        subject=subject,
        role=application.form_data['role'],
        sport=application.form_data.get('sport') if application.form_data['role'] == 'Organisation' else None,
        debug=True
    )
    
    # If no subject was matched but user selected something, ignore the filtered results
    if no_subject_match:
        predefined_filtered = predefined.none()
    
    if application.form_data['role'] == 'Organisation':
        # For organizations: start with subject-filtered results
        # Only override with sport filtering if a sport was actually selected
        sport_selected = application.form_data.get('sport', '')
        
        if sport_selected:
            # Organization selected a sport - filter by sport
            predefined_always = PreDefinedScholarship.objects.filter(sport__isnull=False, sport='always', is_organization=True)
            predefined = predefined.filter(sport__isnull=False, is_organization=True)
            
            if 'Football' in sport_selected or 'Fotboll' in sport_selected:
                predefined = predefined.filter(sport="football")
            elif 'Athletics' in sport_selected or 'Friidrott' in sport_selected:
                predefined = predefined.filter(sport="athletics")
            elif 'Golf' in sport_selected:
                predefined = predefined.filter(sport="golf")
            elif 'Gymnastics' in sport_selected or 'Gymnastik' in sport_selected:
                predefined = predefined.filter(sport="gymnastics")
            elif 'Floorball' in sport_selected or 'Innebandy' in sport_selected:
                predefined = predefined.filter(sport="floorball")
            elif 'Ice Hockey' in sport_selected or 'Ishockey' in sport_selected:
                predefined = predefined.filter(sport="ice_hockey")
            elif 'Swimming' in sport_selected or 'Simidrott' in sport_selected or 'Simning' in sport_selected:
                predefined = predefined.filter(sport="swimming")
            elif 'Handball' in sport_selected or 'Handboll' in sport_selected:
                predefined = predefined.filter(sport="handball")
            elif 'Equestrian' in sport_selected or 'Ridsport' in sport_selected:
                predefined = predefined.filter(sport="equestrian")
            elif 'Motorsports' in sport_selected or 'Motorsport' in sport_selected or 'Snowmobile' in sport_selected or 'Snöskoter' in sport_selected:
                predefined = predefined.filter(sport="motorsports")
            
            predefined_filtered = predefined
        else:
            # Organization did NOT select a sport - use subject-filtered results from get_predefined_scholarships_by_level
            # predefined_always and predefined_filtered are already correct from the function call above
            # Just add is_organization filter
            predefined_always = predefined_always.filter(is_organization=True)
            predefined_filtered = predefined_filtered.filter(is_organization=True)
        
        application.form_data['education_level_option'] = []
    else:
        # For individuals: use the filtered results from get_predefined_scholarships_by_level
        # Exclude "always" from the filtered set since it's handled separately
        pass

    # Debug: show what scholarships are returned
    print(f"\n[SUBMIT_APPLICATION - PREDEFINED SCHOLARSHIPS RESULT]")
    print(f"  Role: {application.form_data['role']}")
    print(f"  predefined_always count: {predefined_always.count()}")
    print(f"  predefined_filtered count: {predefined_filtered.count()}")
    if predefined_filtered.count() > 0:
        print(f"  First filtered scholarship subject: {predefined_filtered.first().subject}")


    # Combine AI results with predefined scholarships
    # Combine AI results with predefined scholarships using language-aware serializer
    output_language = application.form_data.get('language', 'en')
    predefined_scholarships_data = PreDefinedScholarshipSerializer(
        predefined_always, many=True, language=output_language
    ).data + PreDefinedScholarshipSerializer(
        predefined_filtered, many=True, language=output_language
    ).data
    
    # Translate predefined scholarships Purpose field to match output language
    predefined_scholarships_data = translate_predefined_scholarships(
        predefined_scholarships_data,
        output_language=output_language
    )
    
    # Order: Predefined scholarships FIRST (always subject + specific subject), then AI results
    # This ensures "always" scholarships appear first, then subject-specific, then AI-matched
    total_result = predefined_scholarships_data + formatted_ai_results[:10-len(predefined_scholarships_data)]
    
    # Clean all Unicode characters that cause black boxes in PDF
    total_result = clean_scholarship_data(total_result)

    if 'include_municipality_filter' in application.form_data:
                     application.form_data.pop('include_municipality_filter')
    report_utils.create_pdf(
        # report_data,
        total_result,
        application.form_data,
        settings.WATERMARK_PATH,
        pdf_location
    )

    with open(pdf_location, 'rb') as file:
        application.report_file.save(application.email, File(file), save=True)

    application.success_count = len(total_result)
    application.save()
    os.remove(pdf_location)
    message = ""

    return Response({
        "success_count": len(total_result),
    })


@api_view(['post'])
def generate_payment_link(request, email, method):
    # email = request.data.get('email')
    if method not in ['klarna', 'paypal', 'card']:
        raise ValidationError({"error": "invalid payment method."})
    coupon = request.data.get('coupon_code')
    discount = 0

    if coupon:
        if cpn:=Coupon.objects.filter(code=coupon).first():
            print(cpn)
            print(cpn.discount)
            discount = cpn.discount
        else:
            print(coupon)
            raise ValidationError({"error": "invalid copuon"})

    SITE_CONFIG = settings.SITE_CONFIG
    success_url = request.data.get('success_url')
    cancel_url = request.data.get('cancel_url')


    application = get_object_or_404(
        ScholarshipApplicant,
        email=email,
    )
    if not application.email_verified:
        raise ValidationError({"error": "the email is not verified."})
    if application.paid:
        raise ValidationError({
            "error": "you have already paid."
        })

    stripe.api_key = os.environ['STRIPE_SECRET_KEY']
    # stripe.api_key = "sk_test_51OXdHWFvvW23GozqQWzgshPAf66cX6EhWQ8MBpEoLaZiEBMZKNmgLR0zYUZfedZXwDEVJN3mcSFOG3OlPk2KGeiw00gm81YC9z"
    

    STD_PRICE = 299
    PHD_PRICE = 599
    ORG_PRICE = 1599
    print(application.form_data)
    
    # Check PhD FIRST (before general individual check)
    if application.form_data.get('role', "").lower() in ['privatperson', 'individual'] and 'phd' in application.form_data.get('study_level', "").lower():
        price = PHD_PRICE
    elif application.form_data.get('role', "").lower() in ['privatperson', 'individual']:
        price = STD_PRICE
    else:
        price = ORG_PRICE

    print(discount)
    print(price)
    price = price - price*(discount/100)
    session = stripe.checkout.Session.create(
      success_url=success_url if success_url else "https://example.com/success",
      cancel_url=cancel_url if cancel_url else "https://example.com/success?error=payment failed",
      line_items=[{
        "price_data":{
            "currency": "sek",
            "product_data": {
                "name": "application fee"
            },
            "unit_amount": int(float(price)*100)
        },
        "quantity": 1
      }],
      mode="payment",
      # payment_method_types=["klarna"],
      payment_method_types=[method],
      metadata={
        "email": email
      }
    )
    return Response({
        "payment_link": session['url']
    })


def handle_checkout_session_complete(event):
    metadata = event['data']['object']['metadata']

    email = metadata.get('email')
    # subscription_type = metadata.get('subscription_type')

    application = get_object_or_404(ScholarshipApplicant, email=email)

    application.paid = True
    application.save()
    return Response({"msg": "payment accepted"})


@api_view(['post'])
def stripe_payment_webhook(request):
    event = None
    payload = request.body
    sig_header = request.headers.get('STRIPE_SIGNATURE')
    if not sig_header:
        raise ValidationError({"error": "validation signature not found"})

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, os.environ['STRIPE_WEBHOOK_SECRET'],
        )

    except ValueError as e:
        return Response({'error': "invalid payload"}, status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        return Response({'error': "invalid signature"}, status=status.HTTP_400_BAD_REQUEST)

    if event['type'] == 'checkout.session.completed':
        return handle_checkout_session_complete(event)

    return Response("")


class ReviewView(APIView):
    def get(self, request):

        reviews = Review.objects.order_by("-stars")
        average_rating = reviews.aggregate(models.Avg('stars', default=0))
        return Response({
            "average_rating": average_rating,
            "reviews": [
                {
                    # "email": review.email,
                    "stars": review.stars,
                    "description": review.description
                } for review in reviews
            ]
        })
        pass


    @extend_schema(request=ReviewSerializer)
    def post(self, request):
        email = request.data.get('email')
        description = request.data.get('description')
        stars = request.data.get('stars')

        review = Review.objects.filter(email=email).first()
        if review:
            raise ValidationError({"error": "Review with the same email already exists."})

        if not isinstance(stars, int):
            raise ValidationError({"error": "stars must be an integer."})

        if not 0<stars<6:
            raise ValidationError({"error": "stars must be between 1 and 5"}) 

        Review.objects.create(
            email=email,
            description=description,
            stars=stars
        )
        return Response({
            "error": "review submitted."
        })

@api_view(['get'])
def faq_list(request):
    faqs = []
    faqs_sv = []

    for faq in FAQ.objects.all():
        faqs.append({
            "question": faq.question,
            "answer": faq.answer,
        })
        faqs_sv.append({
            "question": faq.question_sv,
            "answer": faq.answer_sv
        })

    return Response({
        "faqs": faqs,
        "faqs_sv": faqs_sv
    })




@api_view(['post'])
def generate_data_playground(request):

    application = get_object_or_404(ScholarshipApplicant, email="salmanf4545@gmail.com")
    # if application.report_file:
    #     return Response({
    #         "success_count": application.success_count
    #     })

    location = application.form_data.get('municipality')
    language = application.form_data['language']
    print(F"DEBUGING LANGUAGE: {language}")
    

    # report_data = ai_utils.find_scholarships(
    #     settings.DATASET_PATH,
    #     location,
    #     language,
    #     application.form_data,
    # )


    subject = (
        education_level_option
            if (education_level_option:=application.form_data.get('education_level_option'))
            else application.form_data.get('education_level_other')
    )


    pdf_location = f"{str(uuid.uuid4())}.pdf"

    predefined = PreDefinedScholarship.objects.all()
    
    # Extract study level from form data
    study_level = application.form_data.get('study_level', '').lower()
    # Extract subject from education_level_option AND education_level_other (for "Annat"/Other case)
    education_level_option = application.form_data.get('education_level_option', [])
    education_level_other = application.form_data.get('education_level_other', '')
    subject = None
    
    # Map education_level_option to subject field values
    # Support both old format (economics, engineering, law) and new format
    # Include both regular selection and "Annat" (Other) field
    # Handle both list and string input formats
    education_parts = []
    if education_level_option:
        if isinstance(education_level_option, list):
            education_parts = education_level_option
        else:
            # If it's a string, wrap it in a list (don't use list() which converts to chars)
            education_parts = [str(education_level_option)]
    if education_level_other:
        education_parts.append(education_level_other)
    education_str = ' '.join(education_parts).lower()
    
    # Undergraduate and Master's subjects - matching Swedish form names
    if any(term in education_str for term in ['engineering', 'technology', 'teknik', 'teknik och ingenjörsvetenskap', 'ingenjörsvetenskap']):
        subject = 'engineering_technology'
    elif any(term in education_str for term in ['economics', 'business', 'ekonomi', 'administration', 'företagsekonomi', 'management']):
        subject = 'economics_business'
    elif any(term in education_str for term in ['medicine', 'health', 'medicin', 'hälsa', 'vårdutbildningar', 'vård']):
        subject = 'medicine_health'
    elif any(term in education_str for term in ['computer', 'it', 'data', 'datavetenskap', 'cs', 'datalogi', 'datascience']):
        subject = 'cs_it_data'
    elif any(term in education_str for term in ['education', 'pedagogy', 'utbildning', 'pedagogik']):
        subject = 'education_pedagogy'
    elif any(term in education_str for term in ['psychology', 'behavioral', 'psykologi', 'beteendevetenskap']):
        subject = 'psychology_behavioral'
    elif any(term in education_str for term in ['law', 'political', 'juridik', 'legal', 'statsvetenskap']):
        subject = 'law_political'
    elif any(term in education_str for term in ['environment', 'sustainability', 'miljö', 'hållbarhet']):
        subject = 'environment_sustainability'
    elif any(term in education_str for term in ['design', 'architecture', 'creative', 'arts', 'arkitektur', 'kreativa ämnen']):
        subject = 'design_architecture_arts'
    elif any(term in education_str for term in ['biology', 'chemistry', 'life science', 'biologi', 'kemi', 'naturvetenskap', 'natural science', 'livsvetenskap']):
        subject = 'biology_chemistry_life'
    elif any(term in education_str for term in ['public health', 'epidemiology', 'folkhälsa', 'folkhälsovetenskap', 'epidemiologi']):
        subject = 'public_health_epidemiology'
    elif any(term in education_str for term in ['social science', 'social work', 'samhäll', 'socialt', 'samhällsvetenskap']):
        subject = 'social_sciences'
    
    # If user selected something but no match was found, only show "always" scholarships
    # This prevents irrelevant subject scholarships from appearing
    no_subject_match = (education_level_option or education_level_other) and subject is None
    
    # Use new study level filtering logic
    predefined_always, predefined_filtered = stipo54.get_predefined_scholarships_by_level(
        predefined,
        study_level=study_level,
        subject=subject,
        role=application.form_data['role'],
        sport=application.form_data.get('sport') if application.form_data['role'] == 'Organisation' else None,
        debug=False
    )
    
    # If no subject was matched but user selected something, ignore the filtered results
    if no_subject_match:
        predefined_filtered = predefined.none()
    
    if application.form_data['role'] == 'Organisation':
        # For organizations: start with subject-filtered results
        # Only override with sport filtering if a sport was actually selected
        sport_selected = application.form_data.get('sport', '')
        
        if sport_selected:
            # Organization selected a sport - filter by sport
            predefined_always = PreDefinedScholarship.objects.filter(sport__isnull=False, sport='always', is_organization=True)
            predefined = predefined.filter(is_organization=True, sport__isnull=False)
            
            if 'Football' in sport_selected or 'Fotboll' in sport_selected:
                predefined = predefined.filter(sport="football")
            elif 'Athletics' in sport_selected or 'Friidrott' in sport_selected:
                predefined = predefined.filter(sport="athletics")
            elif 'Golf' in sport_selected:
                predefined = predefined.filter(sport="golf")
            elif 'Gymnastics' in sport_selected or 'Gymnastik' in sport_selected:
                predefined = predefined.filter(sport="gymnastics")
            elif 'Floorball' in sport_selected or 'Innebandy' in sport_selected:
                predefined = predefined.filter(sport="floorball")
            elif 'Ice Hockey' in sport_selected or 'Ishockey' in sport_selected:
                predefined = predefined.filter(sport="ice_hockey")
            elif 'Swimming' in sport_selected or 'Simidrott' in sport_selected or 'Simning' in sport_selected:
                predefined = predefined.filter(sport="swimming")
            elif 'Handball' in sport_selected or 'Handboll' in sport_selected:
                predefined = predefined.filter(sport="handball")
            elif 'Equestrian' in sport_selected or 'Ridsport' in sport_selected:
                predefined = predefined.filter(sport="equestrian")
            elif 'Motorsports' in sport_selected or 'Motorsport' in sport_selected or 'Snowmobile' in sport_selected or 'Snöskoter' in sport_selected:
                predefined = predefined.filter(sport="motorsports")
            
            predefined_filtered = predefined
        else:
            # Organization did NOT select a sport - use subject-filtered results from get_predefined_scholarships_by_level
            # predefined_always and predefined_filtered are already correct from the function call above
            # Just add is_organization filter
            predefined_always = predefined_always.filter(is_organization=True)
            predefined_filtered = predefined_filtered.filter(is_organization=True)
        
        application.form_data['education_level_option'] = []
    else:
        # For individuals: filter by is_organization=False and use study level filtering
        predefined_always = predefined_always.filter(is_organization=False)
        predefined_filtered = predefined_filtered.filter(is_organization=False)


    predefined_scholarships=MockSerializer(
        predefined_always, many=True
    ).data+MockSerializer(
        predefined_filtered, many=True
    ).data
    
    # Translate predefined scholarships Purpose field to match output language
    predefined_scholarships = translate_predefined_scholarships(
        predefined_scholarships,
        output_language=application.form_data['language']
    )

    if 'include_municipality_filter' in application.form_data:
                     application.form_data.pop('include_municipality_filter')


    total_result = stipo54.format_scholarship_json(
        predefined_scholarships,
        output_language=application.form_data['language']
    )
    
    # Clean all Unicode characters that cause black boxes in PDF
    total_result = clean_scholarship_data(total_result)
    
    report_utils.create_pdf(
        # report_data,
        total_result,
        application.form_data,
        settings.WATERMARK_PATH,
        pdf_location
    )

    with open(pdf_location, 'rb') as file:
        application.report_file.save(application.email, File(file), save=True)

    application.save()
    os.remove(pdf_location)
    message = ""

    return Response({
    })

