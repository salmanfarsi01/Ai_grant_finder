from rest_framework import serializers

from .models import ScholarshipApplicant, Review, PreDefinedScholarship


# Subject value translations mapping (English -> Swedish)
SUBJECT_TRANSLATIONS = {
    # Special
    "always": "alltid",
    "other": "Övriga",
    
    # Old format (for backward compatibility)
    "socialSciences": "Samhällsvetenskap",
    "economics": "Ekonomi",
    "naturalSciences": "Naturvetenskap",
    "technology": "Teknik",
    "arts": "Konst",
    "electricityEnergy": "Elektricitet & Energi",
    "vehicleTransport": "Fordon & Transport",
    "construction": "Byggnad & Konstruktion",
    "salesService": "Försäljning & Service",
    "childRecreation": "Barn & Rekreation",
    "engineering": "Ingenjörsvetenskap",
    "medicine": "Medicin",
    "cs": "Datavetenskap",
    "education": "Utbildning",
    "psychology": "Psykologi",
    "law": "Juridik",
    "environment": "Miljö",
    "design": "Design",
    "biology": "Biologi",
    "publicHealth": "Folkhälsa",
    "business": "Företagsekonomi",
    "lifeScience": "Livsvetenskap",
    "pharmacyTech": "Farmacitek",
    "ambulance": "Ambulans",
    "animalCare": "Djurvård",
    "softwareDev": "Mjukvaruutveckling",
    "trainDriver": "Tågförare",
    "dentalNurse": "Tandsköterska",
    "medicalAdmin": "Medicinsk Administration",
    "accounting": "Redovisning",
    "childcare": "Barnomvårdnad",
    "sport": "Sport",
    
    # New undergraduate subjects
    "engineering_technology": "Ingenjörsvetenskap och teknik",
    "economics_business": "Ekonomi, företagsekonomi & management",
    "medicine_health": "Medicin och hälsovetenskap",
    "cs_it_data": "Datavetenskap / IT / Data Science",
    "education_pedagogy": "Utbildning och pedagogik",
    "psychology_behavioral": "Psykologi och beteendevetenskap",
    "law_political": "Juridik och statsvetenskap",
    "environment_sustainability": "Miljö och hållbarhet",
    "design_architecture_arts": "Design, arkitektur och konst",
    "biology_chemistry_life": "Biologi, kemi och livsvetenskap",
    
    # New master's subjects
    "public_health_epidemiology": "Folkhälsa / Epidemiologi",
    "eng_tech_advanced": "Ingenjörsvetenskap & Teknik (cybersäkerhet, supply chain, maskin)",
    "business_management": "Företagsekonomi & Management (finans, redovisning, internationell affär)",
    "cs_digital_data_advanced": "Datavetenskap / Digital affär / Data Science",
    "education_didactics": "Utbildning & Pedagogik (didaktik, ledarskap)",
    "environment_urban": "Miljö & Hållbarhet / Stadsplanering",
    "life_science_biotech": "Livsvetenskap & Bioteknologi",
    "law_llm": "Juridik (LL.M / Juridiska studier)",
    "design_creative_advanced": "Design, arkitektur & konst",
    "social_sciences": "Samhällsvetenskap (psykologi, socialt arbete, statsvetenskap)",
    
    # PhD/Doctoral subjects
    "phd_engineering_technology": "Teknik och ingenjörsvetenskap",
    "phd_economics": "Ekonomi",
    "phd_medicine": "Medicin",
    "phd_law": "Juridik",
    "phd_arts_culture": "Konst/Kultur",
}


# Reverse mapping (Swedish -> English) for translating FROM Swedish to English
SUBJECT_TRANSLATIONS_REVERSE = {v: k for k, v in SUBJECT_TRANSLATIONS.items()}


class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = '__all__'


class LanguageAwarePreDefinedScholarshipSerializer(serializers.ModelSerializer):
    """
    Language-aware serializer that translates fields based on requested language.
    Supports both Swedish (sv) and English (en) output.
    """
    Namn = serializers.SerializerMethodField()
    Name = serializers.SerializerMethodField()
    Municipality = serializers.SerializerMethodField()
    Category = serializers.SerializerMethodField()
    Purpose = serializers.SerializerMethodField()
    Subject = serializers.SerializerMethodField()
    Email = serializers.SerializerMethodField()
    Website = serializers.SerializerMethodField()
    Phone = serializers.SerializerMethodField()
    Assets = serializers.SerializerMethodField()
    MainHuvudadress = serializers.SerializerMethodField()
    PostalPostnr = serializers.SerializerMethodField()
    City = serializers.SerializerMethodField()
    County = serializers.SerializerMethodField()
    Sportkategori = serializers.SerializerMethodField()
    Sport = serializers.SerializerMethodField()

    class Meta:
        model = PreDefinedScholarship
        fields = [
            'Namn', 'Municipality', "Category", "Purpose",
            "Subject", "Email", "Website", "Phone",
            "Assets", "MainHuvudadress", "PostalPostnr", "City",
            "County", "Sportkategori", "Name", "Sport", 'id'
        ]

    def __init__(self, *args, language='en', **kwargs):
        super().__init__(*args, **kwargs)
        self.language = language

    def get_Namn(self, instance):
        return instance.organization_name

    def get_Name(self, instance):
        return instance.organization_name

    def get_Municipality(self, instance):
        return instance.munucipality

    def get_Category(self, instance):
        # Translate category from English to Swedish if needed
        category = instance.category
        if self.language.lower() == 'sv' and category:
            # Translate common category terms from English to Swedish
            category_translations = {
                "Foundation": "Stiftelse",
                "Association": "Förening",
                "Fund": "Fond",
                "Organization": "Organisation",
                "Trust": "Förtroende",
                "Society": "Sällskap",
            }
            for en_term, sv_term in category_translations.items():
                if en_term.lower() in category.lower():
                    category = category.replace(en_term, sv_term)
        return category

    def get_Purpose(self, instance):
        return instance.purpose

    def get_Subject(self, instance):
        subject = instance.subject
        if not subject:
            return subject
        
        if self.language.lower() == 'sv':
            # Translate TO Swedish: use SUBJECT_TRANSLATIONS
            return SUBJECT_TRANSLATIONS.get(subject, subject)
        elif self.language.lower() == 'en':
            # Translate TO English: check if subject is already in Swedish and translate back
            # If subject is a known Swedish translation, convert to English key
            if subject in SUBJECT_TRANSLATIONS_REVERSE:
                return SUBJECT_TRANSLATIONS_REVERSE.get(subject, subject)
            # If subject is an English key, return as-is
            return subject
        return subject

    def get_Email(self, instance):
        return instance.organization_email

    def get_Website(self, instance):
        return instance.organization_website

    def get_Phone(self, instance):
        return instance.organization_phone

    def get_Assets(self, instance):
        return instance.organization_assets

    def get_MainHuvudadress(self, instance):
        return instance.organization_main_address

    def get_PostalPostnr(self, instance):
        return instance.organization_postal_code

    def get_City(self, instance):
        return instance.organization_city

    def get_County(self, instance):
        return instance.organization_county

    def get_Sportkategori(self, instance):
        return None  # No corresponding field on the model

    def get_Sport(self, instance):
        return instance.sport  # No corresponding field on the model


class MockSerializer(serializers.ModelSerializer):
    Name = serializers.SerializerMethodField()
    Subject = serializers.SerializerMethodField()
    Municipality = serializers.SerializerMethodField()
    Category = serializers.SerializerMethodField()
    Purpose = serializers.SerializerMethodField()
    Email = serializers.SerializerMethodField()
    Website = serializers.SerializerMethodField()
    Phone = serializers.SerializerMethodField()
    Assets = serializers.SerializerMethodField()
    Main_Address = serializers.SerializerMethodField()
    Postal = serializers.SerializerMethodField()
    City = serializers.SerializerMethodField()
    County = serializers.SerializerMethodField()
    Sport = serializers.SerializerMethodField()

    class Meta:
        model = PreDefinedScholarship
        fields = [
            'Name', 'Municipality', "Category", "Purpose",
            "Subject", "County",
            "Email", "Website", "Phone",
            "Assets", "City", "Postal",
            "Sport", 'id', "Main_Address",
        ]

    def __init__(self, *args, language='en', **kwargs):
        super().__init__(*args, **kwargs)
        self.language = language

    def get_Name(self, instance):
        return instance.organization_name

    def get_Municipality(self, instance):
        return instance.munucipality

    def get_Category(self, instance):
        # Translate category from English to Swedish if needed
        category = instance.category
        if self.language.lower() == 'sv' and category:
            # Translate common category terms from English to Swedish
            category_translations = {
                "Foundation": "Stiftelse",
                "Association": "Förening",
                "Fund": "Fond",
                "Organization": "Organisation",
                "Trust": "Förtroende",
                "Society": "Sällskap",
            }
            for en_term, sv_term in category_translations.items():
                if en_term.lower() in category.lower():
                    category = category.replace(en_term, sv_term)
        return category

    def get_Purpose(self, instance):
        return instance.purpose

    def get_Subject(self, instance):
        subject = instance.subject
        if not subject:
            return subject
        
        if self.language.lower() == 'sv':
            # Translate TO Swedish: use SUBJECT_TRANSLATIONS
            return SUBJECT_TRANSLATIONS.get(subject, subject)
        elif self.language.lower() == 'en':
            # Translate TO English: check if subject is already in Swedish and translate back
            # If subject is a known Swedish translation, convert to English key
            if subject in SUBJECT_TRANSLATIONS_REVERSE:
                return SUBJECT_TRANSLATIONS_REVERSE.get(subject, subject)
            # If subject is an English key, return as-is
            return subject
        return subject

    def get_Email(self, instance):
        return instance.organization_email

    def get_Website(self, instance):
        return instance.organization_website

    def get_Phone(self, instance):
        return instance.organization_phone


    def get_Assets(self, instance):
        return instance.organization_assets


    def get_City(self, instance):
        return instance.organization_city

    def get_County(self, instance):
        return instance.organization_county

    def get_Sport(self, instance):
        return instance.sport  # No corresponding field on the model

    def get_Main_Address(self, instance):
        return instance.organization_main_address  # No corresponding field on the model

    def get_Postal(self, instance):
        return instance.organization_postal_code  # No corresponding field on the model

# Use language-aware serializer as default
PreDefinedScholarshipSerializer = LanguageAwarePreDefinedScholarshipSerializer