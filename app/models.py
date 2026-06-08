from django.conf import settings
from django.db import models

import random
import uuid


def create_otp(length: int = 4):
    return ''.join(random.choices('0123456789', k=length))

def generate_pdf_path(instance, file_name):
    return f"report-{str(uuid.uuid4())}.pdf"

class ScholarshipApplicant(models.Model):
    email = models.EmailField(unique=True)

    form_data = models.JSONField(default=dict)

    paid = models.BooleanField(default=False) 
    email_verified = models.BooleanField(default=False)
    admin_verified = models.BooleanField(default=False)
    report_file = models.FileField(upload_to=generate_pdf_path, null=True)
    otp = models.CharField(default=create_otp)
    success_count = models.PositiveIntegerField(default=0)

    def refresh_otp(self):
        self.otp = create_otp()

    def __str__(self):
        return f"{self.email}"

def scholarship_db_path(instance, filename):
    return "new_scholarships_db.xlsx"

class SiteConfig(models.Model):
    # process_charge = models.DecimalField(
    #     max_digits=5, decimal_places=2,
    #     default=0
    # )

    admin_check = models.BooleanField(default=True)
    scholarships_db_file = models.FileField(upload_to=scholarship_db_path, null=True)
    pinecone_updated = models.BooleanField(default=False)
    upload_in_progress = models.BooleanField(default=False, help_text="Tracks if an upload is currently running to prevent duplicate uploads")
    last_active_dataset_index = models.CharField(max_length=255, default="scholarships-index-latest", help_text="Previous active index to detect when user changes it")

    query_template = models.TextField(
        verbose_name="LLM filter system prompt",
        default="""You are a scholarship inclusion filter. Your only job is to remove scholarships the user cannot realistically apply for. Default action is INCLUDE. Only exclude when the mismatch is clear and unambiguous.

USER PROFILE
Purpose: {user_purpose}
Study level: {study_level_context}
Domain: {user_domain}
Gender: {gender}

EXCLUSION RULES
Exclude a scholarship only if one of the following is clearly stated in its purpose text:
- The scholarship is exclusively for the opposite gender of the user.
- The scholarship is exclusively for doctoral or postdoc researchers and the user is an undergraduate, with no language about student pathway, thesis work, or studerande, elev, kandidat.
- The scholarship is for primary school or gymnasium only, with no university pathway mentioned.
- The scholarship funds an institution, professorship, chair, faculty operation, or research infrastructure with no individual application path for students.
- The scholarship is exclusively for a clearly unrelated domain such that there is zero realistic connection to the user's stated purpose.

DEFAULT INCLUSION RULE
When in doubt, include. Broad scholarships open to all university students, scholarships with mixed purpose, and scholarships that mention the user's broad field even briefly should always be included.

OUTPUT
Return a JSON array of included scholarship names, nothing else.
Example: ["Scholarship A", "Scholarship B"]"""
    )

    llm_reranker = models.TextField(
        verbose_name="LLM reranker system prompt",
        default="""You are ranking scholarships for a user on a Swedish stipendieportal. The goal is to present scholarships in order of how useful they are to this specific user.

USER PROFILE
Purpose: {user_purpose}
Study level: {study_level}
Domain: {user_domain}

CORE RANKING PRINCIPLE
A broadly applicable scholarship the user clearly qualifies for is more valuable than a niche scholarship requiring a very specific subspecialty match. Wide eligibility plus relevant domain beats narrow eligibility plus perfect domain match. Niche scholarships rank higher only when the user explicitly mentioned that subspecialty in their purpose.

RANKING TIERS
TIER A. Broadly eligible scholarships. Open to all university students at the user's study level, or to a wide range of fields. The user clearly qualifies without needing a specific subspecialty.
TIER B. Domain-relevant scholarships. Targets the user's broad domain (law, technology, business, medicine) without requiring a specific subspecialty.
TIER C. Niche subject-specific scholarships. Targets a specific subspecialty within the user's domain. The user qualifies but eligibility is narrow.
TIER D. Borderline or mixed scholarships. Domain match is weak, the scholarship is primarily research-oriented with only a thin student pathway, or eligibility is unclear.

TIE-BREAKER WITHIN A TIER
Prefer scholarships that mention a clear application process, a deadline, and an explicit monetary value. Prefer scholarships in the user's municipality or county when geography is mentioned. Otherwise keep the order stable.

OUTPUT
Return an ordered JSON array of scholarship names, best first. No commentary.
Example: ["Scholarship A", "Scholarship B", "Scholarship C"]""",
        blank=True,
        help_text="Optional system prompt for LLM reranker. Leave blank to use default behavior."
    )

    # Custom prompts for individual users (overrides default when provided)
    custom_query_prompt_individual = models.TextField(
        verbose_name="Custom LLM Filter Prompt - Individual Users",
        blank=True,
        default="",
        help_text="Custom system prompt for LLM filter when user type is Individual. Leave blank to use the default prompt above."
    )

    custom_query_prompt_organization = models.TextField(
        verbose_name="Custom LLM Filter Prompt - Organization Users",
        blank=True,
        default="",
        help_text="Custom system prompt for LLM filter when user type is Organization. Leave blank to use the built-in organization prompt."
    )

    custom_reranker_prompt_individual = models.TextField(
        verbose_name="Custom LLM Reranker Prompt - Individual Users",
        blank=True,
        default="",
        help_text="Custom system prompt for LLM reranker when user type is Individual. Leave blank to use the default prompt above."
    )

    custom_reranker_prompt_organization = models.TextField(
        verbose_name="Custom LLM Reranker Prompt - Organization Users",
        blank=True,
        default="",
        help_text="Custom system prompt for LLM reranker when user type is Organization. Leave blank to use the built-in organization prompt."
    )

    # Individual "use_default" checkboxes for each field
    use_default_query_filter_base = models.BooleanField(
        default=True,
        verbose_name="Use Default - LLM Filter Base Prompt",
        help_text="Check to use the hardcoded default filter prompt"
    )

    use_default_query_filter_individual = models.BooleanField(
        default=True,
        verbose_name="Use Default - Individual Filter Prompt",
        help_text="Check to use the hardcoded default filter prompt for individual users"
    )

    use_default_query_filter_organization = models.BooleanField(
        default=True,
        verbose_name="Use Default - Organization Filter Prompt",
        help_text="Check to use the hardcoded default filter prompt for organization users"
    )

    use_default_reranker_base = models.BooleanField(
        default=True,
        verbose_name="Use Default - LLM Reranker Base Prompt",
        help_text="Check to use the hardcoded default reranker prompt"
    )

    use_default_reranker_individual = models.BooleanField(
        default=True,
        verbose_name="Use Default - Individual Reranker Prompt",
        help_text="Check to use the hardcoded default reranker prompt for individual users"
    )

    use_default_reranker_organization = models.BooleanField(
        default=True,
        verbose_name="Use Default - Organization Reranker Prompt",
        help_text="Check to use the hardcoded default reranker prompt for organization users"
    )

    # Legacy use_default - kept for backward compatibility
    use_default = models.BooleanField(default=True)

    # Dataset management fields
    use_default_dataset = models.BooleanField(
        default=True,
        verbose_name="Use Default Dataset Index",
        help_text="Check to use the hardcoded default index 'scholarships-index-latest' from stipo54.py. Uncheck to use a custom dataset index."
    )

    active_dataset_index_name = models.CharField(
        max_length=255,
        default="scholarships-index-latest",
        verbose_name="Active Dataset Index Name",
        help_text="The name of the Pinecone index to use when 'Use Default Dataset Index' is unchecked."
    )

    available_dataset_indices = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Available Dataset Indices",
        help_text="JSON map of available dataset index names and their metadata."
    )

    def __str__(self):
        return "Site Settings"

    def get_filter_prompt_individual(self):
        """
        Return custom filter prompt for individual users.
        - If use_default_query_filter_individual is True → return None (use hardcoded default)
        - If use_default_query_filter_individual is False → return custom prompt if set
        """
        if self.use_default_query_filter_individual:
            return None  # Signal to use hardcoded default
        return self.custom_query_prompt_individual.strip() if self.custom_query_prompt_individual else None

    def get_filter_prompt_organization(self):
        """
        Return custom filter prompt for organization users.
        - If use_default_query_filter_organization is True → return None (use hardcoded default)
        - If use_default_query_filter_organization is False → return custom prompt if set
        """
        if self.use_default_query_filter_organization:
            return None  # Signal to use hardcoded default
        return self.custom_query_prompt_organization.strip() if self.custom_query_prompt_organization else None

    def get_reranker_prompt_individual(self):
        """
        Return custom reranker prompt for individual users.
        - If use_default_reranker_individual is True → return None (use hardcoded default)
        - If use_default_reranker_individual is False → return custom prompt if set
        """
        if self.use_default_reranker_individual:
            return None  # Signal to use hardcoded default
        return self.custom_reranker_prompt_individual.strip() if self.custom_reranker_prompt_individual else None

    def get_reranker_prompt_organization(self):
        """
        Return custom reranker prompt for organization users.
        - If use_default_reranker_organization is True → return None (use hardcoded default)
        - If use_default_reranker_organization is False → return custom prompt if set
        """
        if self.use_default_reranker_organization:
            return None  # Signal to use hardcoded default
        return self.custom_reranker_prompt_organization.strip() if self.custom_reranker_prompt_organization else None

    def get_filter_prompt_base(self):
        """
        Return base filter prompt (query_template).
        - If use_default_query_filter_base is True → return None (use hardcoded default)
        - If use_default_query_filter_base is False → return the query_template
        """
        if self.use_default_query_filter_base:
            return None  # Signal to use hardcoded default
        return self.query_template.strip() if self.query_template else None

    def get_reranker_prompt_base(self):
        """
        Return base reranker prompt (llm_reranker).
        - If use_default_reranker_base is True → return None (use hardcoded default)
        - If use_default_reranker_base is False → return the llm_reranker
        """
        if self.use_default_reranker_base:
            return None  # Signal to use hardcoded default
        return self.llm_reranker.strip() if self.llm_reranker else None

    def get_active_dataset_index_name(self):
        """
        Return the active dataset index name.
        - If use_default_dataset is True → return "scholarships-index-latest" (hardcoded default)
        - If use_default_dataset is False → return the configured active_dataset_index_name
        
        NOTE: Automatically converts underscores to hyphens for Pinecone compatibility
        (Pinecone only allows: lowercase alphanumeric and hyphens)
        """
        if self.use_default_dataset:
            return "scholarships-index-latest"  # Signal to use hardcoded default from stipo54.py
        
        index_name = self.active_dataset_index_name.strip() if self.active_dataset_index_name else "scholarships-index-latest"
        # Convert underscores to hyphens for Pinecone compatibility
        # Pinecone requires: lowercase alphanumeric characters or '-' only
        index_name = index_name.replace('_', '-').lower()
        return index_name


class FAQ(models.Model):

    question = models.TextField()
    answer = models.TextField()

    question_sv = models.TextField(default="")
    answer_sv = models.TextField(default="")

    def __str__(self):
        return self.question[:50] + ('...' if len(self.question) > 50 else '')

class Review(models.Model):
    email = models.EmailField()
    description = models.TextField()
    stars = models.SmallIntegerField()

import random
import string

def random_string():
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(7))


class Coupon(models.Model):
    discount = models.PositiveIntegerField(default=0)
    code = models.CharField(max_length=7, default=random_string, blank=True, null=True, unique=True)
    
    # Usage tracking
    times_used = models.PositiveIntegerField(default=0, help_text="Number of times this coupon has been used")
    created_at = models.DateTimeField(auto_now_add=True, help_text="When the coupon was created")
    last_used = models.DateTimeField(null=True, blank=True, help_text="Last time this coupon was used")
    
    is_active = models.BooleanField(default=True, help_text="Enable/disable this coupon")
    max_uses = models.PositiveIntegerField(null=True, blank=True, help_text="Maximum times coupon can be used (leave blank for unlimited)")
    
    def __str__(self):
        return f"Coupon {self.code} ({self.discount}%)"
    
    def is_usable(self):
        """Check if coupon can still be used"""
        if not self.is_active:
            return False
        if self.max_uses and self.times_used >= self.max_uses:
            return False
        return True


SPORT_CHOICES = [
    ('always', 'always'),
    ("football","football",),
    ("athletics","athletics",),
    ("golf","golf",),
    ("gymnastics","gymnastics",),
    ("floorball","floorball",),
    ("ice_hockey","ice_hockey",),
    ("swimming","swimming", ),
    ("handball","handball", ),
    ("equestrian","equestrian", ),
    ("motorsports","motorsports", ),
]

class PreDefinedScholarship(models.Model):
    is_organization = models.BooleanField(default=True)
    sport = models.CharField(
        max_length=50,
        choices=SPORT_CHOICES,
        blank=True,
        null=True
    )
    
    study_level = models.CharField(
        max_length=50,
        choices=[
            ('undergraduate', 'Undergraduate/Bachelor'),
            ('master', 'Master\'s'),
            ('phd', 'PhD/Doctoral'),
            ('all', 'All Levels'),
        ],
        default='all',
        null=True,
        blank=True,
        help_text='Target study level for this scholarship'
    )

    subject = models.CharField(null=True, blank=True, choices=[
        # Special
        ("always", "Always"),
        ("other", "Other"),
        
        # UNDERGRADUATE subjects
        ("engineering_technology", "Engineering and Technology"),
        ("economics_business", "Economics, Business Administration & Management"),
        ("medicine_health", "Medicine and Health Sciences"),
        ("cs_it_data", "Computer Science / IT / Data Science"),
        ("education_pedagogy", "Education and Pedagogy"),
        ("psychology_behavioral", "Psychology and Behavioral Sciences"),
        ("law_political", "Law and Political Science"),
        ("environment_sustainability", "Environmental and Sustainability Sciences"),
        ("design_architecture_arts", "Design, Architecture, and Creative Arts"),
        ("biology_chemistry_life", "Biology, Chemistry, and Life Sciences"),
        
        # MASTER'S subjects
        ("public_health_epidemiology", "Public Health / Epidemiology"),
        ("eng_tech_advanced", "Engineering & Technology (cybersecurity, supply chain, machine)"),
        ("business_management", "Business & Management (Finance, Accounting, International Business)"),
        ("cs_digital_data_advanced", "Computer Science / Digital Business / Data Science"),
        ("education_didactics", "Education & Pedagogy (Didactics, Leadership)"),
        ("environment_urban", "Environmental & Sustainability Sciences / Urban Planning"),
        ("life_science_biotech", "Life Sciences & Biotechnology"),
        ("law_llm", "Law (LL.M / Legal Studies)"),
        ("design_creative_advanced", "Design, Architecture & Creative Arts"),
        ("social_sciences", "Social Sciences (Psychology, Social Work, Political Science)"),
        
        # PhD/DOCTORAL subjects
        ("phd_engineering_technology", "Engineering/Technology | Teknik och ingenjörsvetenskap"),
        ("phd_economics", "Economics | Ekonomi"),
        ("phd_medicine", "Medicine | Medicin"),
        ("phd_law", "Law | Juridik"),
        ("phd_arts_culture", "Arts/Culture | Konst/Kultur"),
    ])

    # study_level = models.CharField(choices=[
    #     ("universityUndergraduate", "universityUndergraduate"),
    #     ("universityMasters", "universityMasters"),
    #     ("postSecondary", "postSecondary"),
    #     ("upperSecondary", "upperSecondary"),
    #     ("compulsory", "compulsory"),
    #     ("phd", "phd"),
    # ])

    organization_name = models.TextField()
    munucipality = models.TextField()
    category = models.TextField()
    purpose = models.TextField()
    organization_email = models.TextField()
    organization_website = models.TextField()
    organization_phone = models.TextField()
    organization_assets = models.TextField()
    organization_main_address = models.TextField()
    organization_postal_code = models.TextField()
    organization_city = models.TextField()
    organization_county = models.TextField()
