# Wrapper module for stipo54 - integrates new AI logic into backend
# This module accepts all parameters from the old stepo47 interface for backward compatibility
# but uses the improved stipo54 logic internally

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stipo54 import (
    find_scholarships_v2 as _find_scholarships_v2,
    format_scholarship_json as _format_scholarship_json,
    get_predefined_scholarships_by_level,
    DEFAULT_TOP_K,
    MIN_RESULTS
)

# Try to import Django SiteConfig for custom prompts, 
# but don't fail if Django is not initialized yet
try:
    from django.conf import settings
    if settings.configured:
        from .models import SiteConfig
    else:
        SiteConfig = None
except (ImportError, RuntimeError):
    SiteConfig = None


def get_filter_prompt(user_type="individual"):
    """
    Fetch custom LLM filter prompt from SiteConfig.
    Returns None if use_default is True (signals to use hardcoded default).
    Returns custom prompt if use_default is False and custom prompt is set.
    """
    if not SiteConfig:
        return None
    
    try:
        site_config = SiteConfig.objects.first()
        if not site_config:
            return None
        
        if user_type.lower() == "organization":
            return site_config.get_filter_prompt_organization()
        else:
            return site_config.get_filter_prompt_individual()
    except Exception:
        pass
    
    return None


def get_reranker_prompt(user_type="individual"):
    """
    Fetch custom LLM reranker prompt from SiteConfig.
    Returns None if use_default is True (signals to use hardcoded default).
    Returns custom prompt if use_default is False and custom prompt is set.
    """
    if not SiteConfig:
        return None
    
    try:
        site_config = SiteConfig.objects.first()
        if not site_config:
            return None
        
        if user_type.lower() == "organization":
            return site_config.get_reranker_prompt_organization()
        else:
            return site_config.get_reranker_prompt_individual()
    except Exception:
        pass
    
    return None


# Legacy function names for backward compatibility
def get_custom_prompt():
    """Deprecated: use get_filter_prompt() instead"""
    return get_filter_prompt()


def get_llm_reranker_prompt():
    """Deprecated: use get_reranker_prompt() instead"""
    return get_reranker_prompt()


def find_scholarships_v2(
    user_purpose: str,
    user_type: str = "individual",
    study_level: str = None,
    municipality: str = None,
    municipality_filter: bool = False,
    elite_athlete: bool = False,
    sport: str = None,
    subject: str = None,
    gender: str = None,
    language: str = "en",
    top_k: int = DEFAULT_TOP_K,
    debug: bool = True,
    use_llm_rerank: bool = True,
    custom_system_prompt=None,
    custom_rerank_prompt=None
):
    """
    Integrated interface between views.py and stipo54 AI logic.
    
    Accepts all parameters from the old stepo47 interface but uses improved stipo54 logic.
    Extra parameters (user_type, municipality, municipality_filter, study_level, elite_athlete, 
    sport, subject, language) are accepted for backward compatibility but the improved algorithm
    focuses on user_purpose and gender for better results.
    
    Args:
        user_purpose: Main search query (e.g., "business studies")
        user_type: "individual" or "organization" (accepted for compatibility)
        study_level: Study level filter (accepted for compatibility)
        municipality: Municipality filter (accepted for compatibility)
        municipality_filter: Whether to filter by municipality (accepted for compatibility)
        elite_athlete: Elite athlete flag (accepted for compatibility)
        sport: Sport name (accepted for compatibility)
        subject: Subject (accepted for compatibility)
        gender: User's gender (used for filtering)
        language: Output language "en" or "sv"
        top_k: Number of initial candidates to retrieve
        debug: Enable debug output
        use_llm_rerank: Use LLM reranking
        custom_system_prompt: Custom LLM filter prompt (overrides SiteConfig)
        custom_rerank_prompt: Custom LLM reranker prompt (overrides SiteConfig)
        
    Returns:
        List of scholarship dictionaries (formatted ready for PDF generation)
    """
    # Fetch custom prompts from SiteConfig if not provided as parameters
    if custom_system_prompt is None:
        custom_system_prompt = get_filter_prompt(user_type)
    
    if custom_rerank_prompt is None:
        custom_rerank_prompt = get_reranker_prompt(user_type)
    
    # Call the improved stipo54 logic with core parameters
    # The new algorithm is smarter about user_purpose interpretation
    results = _find_scholarships_v2(
        user_purpose=user_purpose,
        user_type=user_type,
        municipality=municipality,
        municipality_filter=municipality_filter,
        gender=gender,
        top_k=top_k,
        debug=debug,
        use_llm_rerank=use_llm_rerank,
        custom_system_prompt=custom_system_prompt,
        custom_rerank_prompt=custom_rerank_prompt
    )
    
    return results


def format_scholarship_json(scholarship_list, output_language="en"):
    """
    Format scholarship results as JSON.
    
    Args:
        scholarship_list: List of scholarship dictionaries
        output_language: "en" for English or "sv" for Swedish
        
    Returns:
        List of formatted scholarship dictionaries ready for PDF/JSON output
    """
    return _format_scholarship_json(scholarship_list, output_language=output_language)
