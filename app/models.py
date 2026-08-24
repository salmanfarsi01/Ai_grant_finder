from django.conf import settings
from django.db import models
from django.utils import timezone

import random
import uuid


def create_otp(length: int = 6):
    return ''.join(random.choices('0123456789', k=length))

def generate_pdf_path(instance, file_name):
    return f"report-{str(uuid.uuid4())}.pdf"

class ScholarshipApplicant(models.Model):
    email = models.EmailField(unique=True)

    form_data = models.JSONField(default=dict)

    paid = models.BooleanField(default=False) 
    email_verified = models.BooleanField(default=False)
    admin_verified = models.BooleanField(default=False)
    report_file = models.FileField(upload_to=generate_pdf_path, null=True, blank=True)
    pdf_created_at = models.DateTimeField(null=True, blank=True, help_text="When the PDF was generated. Used for 24-hour auto-deletion.")
    otp = models.CharField(default=create_otp)
    success_count = models.PositiveIntegerField(default=0)

    def refresh_otp(self):
        self.otp = create_otp()

    def __str__(self):
        return f"{self.email}"

def scholarship_db_path(instance, filename):
    return "new_scholarships_db.xlsx"


STIPO47_SYSTEM_PROMPT = "You always return strict JSON output."


class LLMPromptConfig(models.Model):
    """Editable LLM prompts kept separate from general site settings."""

    query_template = models.TextField(verbose_name="LLM filter system prompt", blank=True, default=STIPO47_SYSTEM_PROMPT, help_text="Default: You always return strict JSON output.")
    llm_reranker = models.TextField(verbose_name="LLM reranker system prompt", blank=True, default=STIPO47_SYSTEM_PROMPT, help_text="Default: You always return strict JSON output.")
    custom_query_prompt_individual = models.TextField(verbose_name="Individual filter prompt", blank=True, default="", help_text="Leave blank to use the built-in individual filter prompt.")
    custom_query_prompt_organization = models.TextField(verbose_name="Organization filter prompt", blank=True, default="", help_text="Leave blank to use the built-in organization filter prompt.")
    custom_reranker_prompt_individual = models.TextField(verbose_name="Individual reranker prompt", blank=True, default="", help_text="Leave blank to use the built-in individual reranker prompt.")
    custom_reranker_prompt_organization = models.TextField(verbose_name="Organization reranker prompt", blank=True, default="", help_text="Leave blank to use the built-in organization reranker prompt.")
    use_default_query_filter_base = models.BooleanField(default=True, verbose_name="Use built-in base filter prompt")
    use_default_query_filter_individual = models.BooleanField(default=True, verbose_name="Use built-in individual filter prompt")
    use_default_query_filter_organization = models.BooleanField(default=True, verbose_name="Use built-in organization filter prompt")
    use_default_reranker_base = models.BooleanField(default=True, verbose_name="Use built-in base reranker prompt")
    use_default_reranker_individual = models.BooleanField(default=True, verbose_name="Use built-in individual reranker prompt")
    use_default_reranker_organization = models.BooleanField(default=True, verbose_name="Use built-in organization reranker prompt")

    class Meta:
        verbose_name = "LLM Prompt Configuration"
        verbose_name_plural = "LLM Prompt Configuration"

    def __str__(self):
        return "LLM Prompt Configuration"

    @classmethod
    def get_config(cls):
        return cls.objects.first() or cls.objects.create()

    def get_filter_prompt_individual(self):
        return STIPO47_SYSTEM_PROMPT if self.use_default_query_filter_individual else self.custom_query_prompt_individual.strip() or STIPO47_SYSTEM_PROMPT

    def get_filter_prompt_organization(self):
        return STIPO47_SYSTEM_PROMPT if self.use_default_query_filter_organization else self.custom_query_prompt_organization.strip() or STIPO47_SYSTEM_PROMPT

    def get_reranker_prompt_individual(self):
        return STIPO47_SYSTEM_PROMPT if self.use_default_reranker_individual else self.custom_reranker_prompt_individual.strip() or STIPO47_SYSTEM_PROMPT

    def get_reranker_prompt_organization(self):
        return STIPO47_SYSTEM_PROMPT if self.use_default_reranker_organization else self.custom_reranker_prompt_organization.strip() or STIPO47_SYSTEM_PROMPT

    def get_filter_prompt_base(self):
        return STIPO47_SYSTEM_PROMPT if self.use_default_query_filter_base else self.query_template.strip() or STIPO47_SYSTEM_PROMPT

    def get_reranker_prompt_base(self):
        return STIPO47_SYSTEM_PROMPT if self.use_default_reranker_base else self.llm_reranker.strip() or STIPO47_SYSTEM_PROMPT


class EmailTemplateConfig(models.Model):
    """Editable transactional email templates kept separate from site settings."""

    otp_email_subject_en = models.CharField(max_length=255, default="Your scholarship OTP code")
    otp_email_body_en = models.TextField(default="Hello,\n\nUse this OTP code to continue your scholarship search:\n\n{otp}\n\nThank you.\n")
    otp_email_subject_sv = models.CharField(max_length=255, default="Din OTP-kod för stipendiesökning")
    otp_email_body_sv = models.TextField(default="Hej,\n\nAnvänd denna OTP-kod för att fortsätta din stipendiesökning:\n\n{otp}\n\nTack.\n")
    report_email_subject_en = models.CharField(max_length=255, default="Your scholarship report is ready")
    report_email_body_en = models.TextField(default="Hello,\n\nYour scholarship report is attached. Please review the attached file for the matching scholarships.\n\nReport file: {report_file_name}\n\nBest regards,\nScholarship team\n")
    report_email_subject_sv = models.CharField(max_length=255, default="Din stipendierapport är klar")
    report_email_body_sv = models.TextField(default="Hej,\n\nDin stipendierapport är bifogad. Granska den bifogade filen för matchade stipendier.\n\nRapportfil: {report_file_name}\n\nVänliga hälsningar,\nStipendieteamet\n")

    class Meta:
        verbose_name = "Email Template Configuration"
        verbose_name_plural = "Email Template Configuration"

    def __str__(self):
        return "Email Template Configuration"

    @classmethod
    def get_config(cls):
        return cls.objects.first() or cls.objects.create()

    def _normalize_language(self, language):
        language = language.strip().lower() if isinstance(language, str) else "en"
        return language if language in ("en", "sv") else "en"

    def get_otp_email_subject(self, language="en"):
        return getattr(self, f"otp_email_subject_{self._normalize_language(language)}")

    def get_otp_email_body(self, language="en"):
        return getattr(self, f"otp_email_body_{self._normalize_language(language)}")

    def get_report_email_subject(self, language="en"):
        return getattr(self, f"report_email_subject_{self._normalize_language(language)}")

    def get_report_email_body(self, language="en"):
        return getattr(self, f"report_email_body_{self._normalize_language(language)}")


class SiteConfig(models.Model):
    # process_charge = models.DecimalField(
    #     max_digits=5, decimal_places=2,
    #     default=0
    # )

    admin_check = models.BooleanField(default=True)
    use_default = models.BooleanField(default=True)

    def __str__(self):
        return "Site Settings"


    def get_active_dataset_index_name(self):
        """
        Return the active dataset index name.
        This delegates to DatasetUpload if one is configured.
        """
        try:
            dataset = DatasetUpload.get_active()
            if dataset:
                return dataset.get_effective_index_name()
        except Exception:
            pass
        return "scholarships-index-latest"


class DatasetUpload(models.Model):
    scholarships_db_file = models.FileField(upload_to=scholarship_db_path, null=True, blank=True)
    index_name = models.CharField(
        max_length=255,
        default="scholarships-index-latest",
        verbose_name="Dataset Index Name"
    )
    use_default_dataset = models.BooleanField(
        default=True,
        verbose_name="Use Default Dataset Index",
        help_text="Check to use the hardcoded default index 'scholarships-index-latest'."
    )
    active = models.BooleanField(
        default=True,
        verbose_name="Active Dataset",
        help_text="Mark this dataset upload as the active index used for queries."
    )
    pinecone_updated = models.BooleanField(
        default=False,
        verbose_name="Pinecone updated",
        help_text="Set to true when this dataset has been successfully uploaded to Pinecone."
    )
    last_uploaded_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Last uploaded at",
        help_text="Timestamp when this dataset was successfully uploaded to Pinecone."
    )
    # Upload status tracking (for admin UX and restart-safety)
    UPLOAD_STATUS_PENDING = 'pending'
    UPLOAD_STATUS_IN_PROGRESS = 'in_progress'
    UPLOAD_STATUS_INDEX_CREATED = 'index_created'
    UPLOAD_STATUS_PARTIAL = 'partial'
    UPLOAD_STATUS_COMPLETED = 'completed'
    UPLOAD_STATUS_FAILED = 'failed'

    UPLOAD_STATUS_CHOICES = (
        (UPLOAD_STATUS_PENDING, 'Pending'),
        (UPLOAD_STATUS_IN_PROGRESS, 'In Progress'),
        (UPLOAD_STATUS_INDEX_CREATED, 'Index Created'),
        (UPLOAD_STATUS_PARTIAL, 'Partial Upload'),
        (UPLOAD_STATUS_COMPLETED, 'Completed'),
        (UPLOAD_STATUS_FAILED, 'Failed'),
    )

    upload_status = models.CharField(
        max_length=32,
        choices=UPLOAD_STATUS_CHOICES,
        default=UPLOAD_STATUS_PENDING,
        verbose_name='Upload Status',
        help_text='High-level status of the dataset upload to Pinecone.'
    )

    upload_progress_percent = models.PositiveSmallIntegerField(
        default=0,
        verbose_name='Upload Progress (%)',
        help_text='Integer percent progress (0-100) updated during background uploads.'
    )

    upload_rows_uploaded = models.PositiveIntegerField(
        default=0,
        verbose_name='Rows uploaded',
        help_text='Number of rows successfully uploaded to the index.'
    )

    upload_rows_total = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name='Total rows',
        help_text='Total number of rows in the dataset when upload started.'
    )

    upload_error_message = models.TextField(
        null=True,
        blank=True,
        verbose_name='Upload error message',
        help_text='If the upload fails, a short error message is recorded here.'
    )
    upload_in_progress = models.BooleanField(
        default=False,
        verbose_name="Upload in progress",
        help_text="Internal use only: true while a background upload is running."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Dataset Upload"
        verbose_name_plural = "Dataset Uploads"
        ordering = ["-updated_at", "-created_at"]

    def __str__(self):
        return self.index_name or "Dataset Upload"

    def get_effective_index_name(self):
        if self.use_default_dataset:
            return "scholarships-index-latest"
        index_name = self.index_name.strip() if self.index_name else "scholarships-index-latest"
        return index_name.replace("_", "-").lower()

    @classmethod
    def get_active(cls):
        active_record = cls.objects.filter(active=True).order_by("-updated_at", "-created_at").first()
        if active_record:
            return active_record
        return cls.objects.order_by("-updated_at", "-created_at").first()

    def save(self, *args, **kwargs):
        if self.active:
            DatasetUpload.objects.exclude(pk=self.pk).update(active=False)
        super().save(*args, **kwargs)


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
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True, help_text="When the coupon was created")
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
