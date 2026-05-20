# Generated migration to update SiteConfig prompts with new default values

from django.db import migrations


def update_prompts(apps, schema_editor):
    """Update existing SiteConfig record with new default prompts"""
    SiteConfig = apps.get_model('app', 'SiteConfig')
    
    new_query_template = """You are a scholarship inclusion filter. Your only job is to remove scholarships the user cannot realistically apply for. Default action is INCLUDE. Only exclude when the mismatch is clear and unambiguous.

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

    new_reranker_template = """You are ranking scholarships for a user on a Swedish stipendieportal. The goal is to present scholarships in order of how useful they are to this specific user.

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
Example: ["Scholarship A", "Scholarship B", "Scholarship C"]"""

    # Update all existing SiteConfig records
    for config in SiteConfig.objects.all():
        config.query_template = new_query_template
        config.llm_reranker = new_reranker_template
        config.save()


def reverse_update(apps, schema_editor):
    """Reverse function - no action needed"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0023_alter_siteconfig_llm_reranker'),
    ]

    operations = [
        migrations.RunPython(update_prompts, reverse_update),
    ]
