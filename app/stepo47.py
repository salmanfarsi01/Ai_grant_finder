
import os
import json
import time
import re
import unicodedata
from typing import List, Dict, Any
import pandas as pd
from fuzzywuzzy import fuzz
from deep_translator import GoogleTranslator
from pinecone import Pinecone, ServerlessSpec
from openai import OpenAI
from tiktoken import get_encoding
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv
import numpy as np

from django.conf import settings

load_dotenv()


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "My api key")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", "my_api_key")


if not OPENAI_API_KEY or not PINECONE_API_KEY:
    raise ValueError("OPENAI_API_KEY or PINECONE_API_KEY not found in environment variables")

print("Environment variables loaded successfully")
print(f"Using OPENAI_API_KEY: {OPENAI_API_KEY[:5]}...{OPENAI_API_KEY[-5:]}") 
print(f"Using PINECONE_API_KEY: {PINECONE_API_KEY[:5]}...{PINECONE_API_KEY[-5:]}") 



openai = OpenAI(api_key=OPENAI_API_KEY)
pc = Pinecone(api_key=PINECONE_API_KEY)


DATA_PATH = "scholarships.xlsx"
df = pd.read_excel(DATA_PATH, engine="openpyxl").fillna("").astype(str)
print(f"Dataset loaded successfully with {len(df)} rows")


INDEX_NAME = "scholarships-index1"
INDEX_NAME = "scholarships-index-latest" 
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536

if INDEX_NAME not in [i.name for i in pc.list_indexes()]:
    pc.create_index(
        name=INDEX_NAME,
        dimension=EMBEDDING_DIM,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1")
    )
    time.sleep(10)

index = pc.Index(INDEX_NAME)
enc = get_encoding("cl100k_base")
embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL, openai_api_key=OPENAI_API_KEY)

print("Connected to Pinecone vector store successfully")

FIELD_MAP_SV = {
    "Name": "Namn",
    "Municipality": "Kommun",
    "Category": "Kategory",
    "Purpose": "Ändamål",
    "Study Level": "Utbildningsnivå",
    "Email": "Epost",
    "Website": "Websida",
    "Phone": "Telefon",
    "Assets": "Tillgångar",
    "Main Address": "Huvudadress",
    "Postal Code": "Postnr",
    "City": "Postort",
    "County": "Län",
    "Sport": "Sport NY kategori"
}


# Utility Functions
KEY_TRANSLATION_SV = {
    "Name": "Namn",
    "Municipality": "Kommun",
    "Category": "Kategori",
    "Purpose": "Syfte",
    "Study Level": "Studienivå",
    "Email": "E-post",
    "Website": "Webbplats",
    "Phone": "Telefon",
    "Assets": "Tillgångar",
    "Main Address": "Adress",
    "Postal Code": "Postnummer",
    "City": "Stad",
    "County": "Län",
    "Base Score": "Grundpoäng",
    "Relevance Score": "Relevanspoäng"
}

def safe_truncate(text, max_tokens=8192):
    tokens = enc.encode(text)
    if len(tokens) > max_tokens:
        tokens = tokens[:max_tokens]
        text = enc.decode(tokens)
    return text


def get_openai_embedding(text: str):
    text = text.strip()
    if not text:
        return None
    text = safe_truncate(text)
    response = openai.embeddings.create(model=EMBEDDING_MODEL, input=text)
    return response.data[0].embedding


def safe_translate(text, source, target, max_len=4500):
    if not text or not isinstance(text, str):
        return text
    if len(text) < max_len:
        return GoogleTranslator(source=source, target=target).translate(text)
    chunks = [text[i:i + max_len] for i in range(0, len(text), max_len)]
    translated_chunks = []
    for chunk in chunks:
        try:
            translated_chunks.append(GoogleTranslator(source=source, target=target).translate(chunk))
        except Exception:
            translated_chunks.append(chunk)
    return " ".join(translated_chunks)



def rerank_with_llm(query, scholarships, openai_client, top_n=10):
    formatted_text = "\n".join([
        f"{i+1}. {s['Name']} — Purpose: {s['Purpose']}, Study Level: {s['Study Level']}"
        for i, s in enumerate(scholarships)
    ])

    prompt = f"""
    "Du är en intelligent stipendierekommendationsassistent. "
          "Ditt uppdrag är att hitta och rangordna stipendier som exakt matchar användarens uppgifter. "
          "Du ska bedöma och prioritera baserat på fyra huvuddimensioner:\n\n"

          "1.**Ämne / Studieområde** – Den viktigaste faktorn. "
          "Inkludera endast stipendier vars ändamål, beskrivning eller behörighetskrav "
          "tydligt nämner eller starkt relaterar till användarens valda ämne. "
          "Exempel: Om användaren väljer teknik och ingenjörsvetenskap, inkludera endast stipendier "
          "som handlar om teknik eller ingenjörsvetenskap – uteslut alla andra områden.\n\n"

          "2. **Utbildningsnivå** – Näst viktigast. "
          "Stipendierna måste matcha användarens utbildningsnivå (t.ex. gymnasium, kandidat, master, doktorand). "
          "Om användaren väljer 'grundnivå' eller 'universitet', inkludera endast stipendier som erbjuds på dessa nivåer.\n\n"

          "3. **Syfte / Avsikt** – Tredje prioritet. "
          "Matcha stipendier till användarens syfte, såsom forskning, studieavgifter eller levnadskostnader. "
          "Stipendier som semantiskt stämmer överens med användarens mål prioriteras.\n\n"

          "4. **Könsrelevans** – Fjärde prioritet. "
          "Om användaren anger ett kön (t.ex. man eller kvinna), inkludera endast stipendier som uttryckligen "
          "riktar sig till det könet eller är könsneutrala.\n\n"

          " **Prioritetsordning:** Ämne ➜ Utbildningsnivå ➜ Syfte ➜ Kön.\n\n"

          "**OBS:** Om användaren **inte** anger någon variabel (t.ex. ämne, utbildningsnivå, syfte eller kön), "
          "ska AI:n **inte** söka eller filtrera efter den variabeln. "
          "Till exempel, om användaren inte specificerar ett ämne eller kön, ska AI:n inkludera stipendier "
          "från alla ämnen eller kön istället för att utesluta dem.\n\n"

          "Uteslut stipendier som inte matchar användarens ämne eller utbildningsnivå när dessa anges. "
          "Returnera endast de mest relevanta stipendierna baserat på användarens uppgifter."

    Query: {query}

    Scholarships:
    {formatted_text}

    Return a JSON list of the top {top_n} scholarship names in best-match order.
    """

    response = openai_client.chat.completions.create(
        model="gpt-5",
        messages=[{"role": "user", "content": prompt}],
    )

    try:
        ranked_names = json.loads(response.choices[0].message.content)
    except Exception:
        ranked_names = []

    ranked_list = [s for name in ranked_names for s in scholarships if s["Name"] == name]
    return ranked_list or scholarships[:top_n]



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

    top_k: int = 30,
    debug: bool = True,
    use_llm_rerank: bool = True
) -> List[Dict[str, Any]]:

    query_template = {
      "purpose": user_purpose or "",
      "study_level": study_level or "",
      "subject": subject or "",
      "gender": gender or "",
      "context": (
           
           """
            Du är en intelligent stipendierekommendationsassistent.
            Ditt uppdrag är att hitta och rangordna stipendier som exakt matchar användarens uppgifter.
            För en individuell användare ska du prioritera:
            1. Studie-nivå → Hård matchning (måste matcha användarens nivå eller vara lämplig)
            2. Ämnesområde → Hård matchning (måste vara i samma ämnesområde eller nära relaterat)
            3. Syfte för finansiering → Bör matcha användarens angivna syfte (t.ex., "tuition", "research")
            4. Kön → Matcha användarens kön (om specificerat)
            5. du måste ge mig minst 15 relevanta stipendier
 
            För en organisation ska du prioritera:
            1. Syftet för finansiering → Hård matchning för sportspecifika ändamål (t.ex., "utrustning", "resa", "träning")
            2. Kommun (om angivet) → Måste matcha den valda kommunen
            """

      )
}

    combined_query = json.dumps(query_template, ensure_ascii=False)

    translated_query = (
        safe_translate(combined_query, source="en", target="sv")
        if language.lower() == "en"
        else combined_query
    )

    if debug:
        print(f"\n Structured Query for Embedding:\n{translated_query}\n")

    query_emb = get_openai_embedding(translated_query)
    if query_emb is None:
        print("Embedding generation failed.")
        return []



    filters = {}
    if user_type.lower() in ["individual", "person"]:
        filters["Kommentar"] = {"$in": ["Flera", "Studier"]}
    elif user_type.lower() == "organization":
        filters["Kommentar"] = {"$in": ["Flera", "Idrottsförening"]}

    if municipality_filter and municipality:
        filters["Kommun"] = municipality.strip()

    if debug:
        print(f"Pinecone Filters:\n{json.dumps(filters, indent=4, ensure_ascii=False)}\n")


    try:
        res = index.query(
            vector=query_emb,
            top_k=top_k * 2,
            include_metadata=True,
            filter=filters
        )
    except Exception as e:
        print(f" Pinecone query failed: {e}")
        return []

    matches = res.get("matches", [])
    if not matches:
        print(" No scholarships found.")
        return []


    def compute_soft_score(sch, purpose, level, subj, gen):

        score = 0
        combined_text = f"{sch.get('Purpose','')} {sch.get('Study Level','')}".lower()

        total_weight = 4  # 4 factors: subject, level, purpose, gender
        factor_score = 0  # accumulate normalized score

        if subj:
            subj_score = fuzz.token_set_ratio(subj.lower(), combined_text)
            factor_score += subj_score / 100

        if level:
            lvl_score = fuzz.partial_ratio(level.lower(), combined_text)
            factor_score += lvl_score / 100


        if purpose:
            purp_score = fuzz.token_sort_ratio(purpose.lower(), combined_text)
            factor_score += purp_score / 100


        if gen:
            gen_score = fuzz.partial_ratio(gen.lower(), combined_text)
            factor_score += gen_score / 100

        score = round(factor_score, 3)

        return score


    results_data = []
    for m in matches:
        md = m["metadata"]
        s = {
            "Name": md.get("Namn", ""),
            "Municipality": md.get("Kommun", ""),
            "Category": md.get("Category", ""),
            "Purpose": md.get("Ändamål", ""),
            "Study Level": md.get("study level", ""),
            "Email": md.get("Epost", ""),
            "Website": md.get("Websida", ""),
            "Phone": md.get("Telefon", ""),
            "Assets": md.get("Tillgångar", ""),
            "Main Address": md.get("Huvudadress", ""),
            "Postal Code": md.get("Postnr", ""),
            "City": md.get("Postort", ""),
            "County": md.get("Län", ""),
            "Base Score": round(m["score"], 4)
        }
        s["Relevance Score"] = compute_soft_score(s, user_purpose, study_level, subject, gender)
        results_data.append(s)


    def is_reasonably_relevant(sch):
          text = f"{sch.get('Purpose','')} {sch.get('Study Level','')}".lower()

          subj_ok = not subject or fuzz.partial_ratio(subject, text) > 25
          lvl_ok = not study_level or fuzz.partial_ratio(study_level, text) > 25

          high_semantic = sch.get("Base Score", 0) > 0.78

          return subj_ok or lvl_ok or high_semantic


    results_data = [r for r in results_data if is_reasonably_relevant(r)]

    results_data = sorted(
        results_data,
        key=lambda x: (x["Base Score"] + x["Relevance Score"]),
        reverse=True
    )

    if debug:
        print(f" {len(results_data)} scholarships retrieved and pre-ranked successfully.\n")


    if use_llm_rerank and len(results_data) > 3:
        try:
            ranked = rerank_with_llm(combined_query, results_data[:top_k], openai, top_n=top_k)
            results_data = ranked
            print(" LLM re-ranking applied successfully.")
        except Exception as e:
            print(f" LLM re-ranking failed: {e}")

    for s in results_data:
        s.pop("Base Score", None)
        s.pop("Relevance Score", None)
    return results_data



def format_scholarship_json(scholarship_list: List[Dict[str, Any]], output_language: str = "en") -> str:
    formatted_list = []
 
    for scholarship in scholarship_list:
        formatted_entry = {}
 
        for key, value in scholarship.items():
 
            if output_language.lower() == "en":
                if isinstance(value, str) and value.strip():
                    try:
                        translated_value = safe_translate(value, source="sv", target="en")
                        formatted_entry[key] = translated_value
                    except Exception:
                        formatted_entry[key] = value
                else:
                    formatted_entry[key] = value
 
            elif output_language.lower() == "sv":
 
                new_key = KEY_TRANSLATION_SV.get(key, key)
 
                if isinstance(value, str) and value.strip():
                    try:
                        translated_value = safe_translate(value, source="en", target="sv")
                    except Exception:
                        translated_value = value
                else:
                    translated_value = value
 
                formatted_entry[new_key] = translated_value
 
            else:
                formatted_entry[key] = value
 
        formatted_list.append(formatted_entry)
 
    return formatted_list
   


def llm_filter_scholarships(
    user_purpose: str,
    study_level: str,
    subject: str,
    gender: str,
    scholarships: List[Dict[str, Any]],
    model: str = "gpt-4o-mini",
    debug: bool = True
) -> List[Dict[str, Any]]:

    if not scholarships:
        if debug:
            print("[LLM FILTER] No scholarships provided — returning empty list.")
        return []

    if debug:
        print(f"\n[LLM FILTER] Received {len(scholarships)} scholarships for LLM filtering.\n")

    
    user_context = f"""
    USER REQUIREMENTS:
    • Purpose: {user_purpose}
    • Study Level: {study_level}
    • Subject: {subject}
    • Gender: {gender}


    STRICT RELEVANCE RULES:
    1. Study Level → HARD MATCH (must match user level or be obviously suitable)
    2. Subject → HARD MATCH (Must be semantically aligned; related fields are acceptable).
    3. Gender Rules:
         - female user → only female/open scholarships allowed
         - male user → only male/open scholarships allowed
    4. Purpose → Must closely match or support user's stated purpose.
    5. **Only Include those scholarships which are relevant to the user's SUBJECT & STUDY LEVEL.**
    6. **Include at least **8–10** scholarships Must.**
    7. **If subject is not matched with user's *subject* then exclude the scholarships**
    """

    scholarship_blocks = []
    for idx, s in enumerate(scholarships):
        block = f"""
        [{idx}]
        Name: {s.get('Name', '')}
        Purpose: {s.get('Purpose', '')}
        Category: {s.get('Category', '')}
        Study Level: {s.get('Study Level', '')}
        """
        scholarship_blocks.append(block)

    combined_text = "\n".join(scholarship_blocks)

   
    prompt = f"""
    Evaluate the following scholarships for relevance:

    {combined_text}

    Based on the user's requirements:

    {user_context}

    Respond ONLY with valid JSON in this exact format:

    [
      {{"index": 0, "relevance": "relevant"}},
      {{"index": 1, "relevance": "irrelevant"}}
    ]

    DO NOT add commentary, explanations, markdown, or extra text.
    ALWAYS return valid JSON.
    """

    response = openai.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You always return strict JSON output."},
            {"role": "user", "content": prompt}
        ],
        temperature=0
    )

    raw_content = response.choices[0].message.content

    if debug:
        print("\n[LLM FILTER] Raw LLM Output:")
        print("-----------------------------------")
        print(raw_content)
        print("-----------------------------------\n")

    if not raw_content or raw_content.strip() == "":
        if debug:
            print("[LLM FILTER] ERROR: Empty LLM response — returning ALL scholarships.")
        return scholarships

    try:
        decisions = json.loads(raw_content)
    except Exception as e:
        if debug:
            print("[LLM FILTER] JSON PARSE ERROR — returning ALL scholarships.")
            print(f"Error: {e}")
            import traceback
            print(traceback.format_exc())
        return scholarships

    relevant_indices = {
        d.get("index")
        for d in decisions
        if isinstance(d, dict) and d.get("relevance", "").lower() == "relevant"
    }

    relevant_indices = {
        i for i in relevant_indices
        if isinstance(i, int) and 0 <= i < len(scholarships)
    }

    filtered = [scholarships[i] for i in sorted(relevant_indices)]

    if debug:
        excluded = sorted(set(range(len(scholarships))) - relevant_indices)
        print(f"[LLM FILTER] Relevant Scholarships: {len(filtered)}")
        print(f"[LLM FILTER] Excluded Scholarships: {len(excluded)}")
        print(f"[LLM FILTER] Excluded Indexes: {excluded}\n")

    return filtered





INDEX_NAME = "scholarships-index-latest"
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536

if INDEX_NAME not in [i.name for i in pc.list_indexes()]:
    pc.create_index(
        name=INDEX_NAME,
        dimension=EMBEDDING_DIM,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1")
    )
    time.sleep(10)

index = pc.Index(INDEX_NAME)
enc = get_encoding("cl100k_base")
embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL, openai_api_key=OPENAI_API_KEY)

print("Connected to Pinecone vector store successfully")

# Utility Functions

def safe_truncate(text, max_tokens=8192):
    tokens = enc.encode(text)
    if len(tokens) > max_tokens:
        tokens = tokens[:max_tokens]
        text = enc.decode(tokens)
    return text


def get_openai_embedding(text: str):
    text = text.strip()
    if not text:
        return None
    text = safe_truncate(text)
    response = openai.embeddings.create(model=EMBEDDING_MODEL, input=text)
    return response.data[0].embedding


def safe_translate(text, source, target, max_len=4500):
    if not text or not isinstance(text, str):
        return text
    if len(text) < max_len:
        return GoogleTranslator(source=source, target=target).translate(text)
    chunks = [text[i:i + max_len] for i in range(0, len(text), max_len)]
    translated_chunks = []
    for chunk in chunks:
        try:
            translated_chunks.append(GoogleTranslator(source=source, target=target).translate(chunk))
        except Exception:
            translated_chunks.append(chunk)
    return " ".join(translated_chunks)



def rerank_with_llm(query, scholarships, openai_client, top_n=10):
    formatted_text = "\n".join([
        f"{i+1}. {s['Name']} — Purpose: {s['Purpose']}, Study Level: {s['Study Level']}"
        for i, s in enumerate(scholarships)
    ])

    prompt = f"""
    "Du är en intelligent stipendierekommendationsassistent. "
          "Ditt uppdrag är att hitta och rangordna stipendier som exakt matchar användarens uppgifter. "
          "Du ska bedöma och prioritera baserat på fyra huvuddimensioner:\n\n"

          "1.**Ämne / Studieområde** – Den viktigaste faktorn. "
          "Inkludera endast stipendier vars ändamål, beskrivning eller behörighetskrav "
          "tydligt nämner eller starkt relaterar till användarens valda ämne. "
          "Exempel: Om användaren väljer teknik och ingenjörsvetenskap, inkludera endast stipendier "
          "som handlar om teknik eller ingenjörsvetenskap – uteslut alla andra områden.\n\n"

          "2. **Utbildningsnivå** – Näst viktigast. "
          "Stipendierna måste matcha användarens utbildningsnivå (t.ex. gymnasium, kandidat, master, doktorand). "
          "Om användaren väljer 'grundnivå' eller 'universitet', inkludera endast stipendier som erbjuds på dessa nivåer.\n\n"

          "3. **Syfte / Avsikt** – Tredje prioritet. "
          "Matcha stipendier till användarens syfte, såsom forskning, studieavgifter eller levnadskostnader. "
          "Stipendier som semantiskt stämmer överens med användarens mål prioriteras.\n\n"

          "4. **Könsrelevans** – Fjärde prioritet. "
          "Om användaren anger ett kön (t.ex. man eller kvinna), inkludera endast stipendier som uttryckligen "
          "riktar sig till det könet eller är könsneutrala.\n\n"

          " **Prioritetsordning:** Ämne ➜ Utbildningsnivå ➜ Syfte ➜ Kön.\n\n"

          "**OBS:** Om användaren **inte** anger någon variabel (t.ex. ämne, utbildningsnivå, syfte eller kön), "
          "ska AI:n **inte** söka eller filtrera efter den variabeln. "
          "Till exempel, om användaren inte specificerar ett ämne eller kön, ska AI:n inkludera stipendier "
          "från alla ämnen eller kön istället för att utesluta dem.\n\n"

          "Uteslut stipendier som inte matchar användarens ämne eller utbildningsnivå när dessa anges. "
          "Returnera endast de mest relevanta stipendierna baserat på användarens uppgifter."

    Query: {query}

    Scholarships:
    {formatted_text}

    Return a JSON list of the top {top_n} scholarship names in best-match order.
    """

    response = openai_client.chat.completions.create(
        model="gpt-5",
        messages=[{"role": "user", "content": prompt}],
    )

    try:
        ranked_names = json.loads(response.choices[0].message.content)
    except Exception:
        ranked_names = []

    ranked_list = [s for name in ranked_names for s in scholarships if s["Name"] == name]
    return ranked_list or scholarships[:top_n]



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

    top_k: int = 30,
    debug: bool = True,
    use_llm_rerank: bool = True
) -> List[Dict[str, Any]]:

    query_template = {
      "purpose": user_purpose or "",
      "study_level": study_level or "",
      "subject": subject or "",
      "gender": gender or "",
      "context": (
           """
            Du är en intelligent stipendierekommendationsassistent.
            Ditt uppdrag är att hitta och rangordna stipendier som exakt matchar användarens uppgifter.
            För en individuell användare ska du prioritera:
            1. Studie-nivå → Hård matchning (måste matcha användarens nivå eller vara lämplig)
            2. Ämnesområde → Hård matchning (måste vara i samma ämnesområde eller nära relaterat)
            3. Syfte för finansiering → Bör matcha användarens angivna syfte (t.ex., "tuition", "research")
            4. Kön → Matcha användarens kön (om specificerat)
            5. du måste ge mig minst 15 relevanta stipendier
 
            För en organisation ska du prioritera:
            1. Syftet för finansiering → Hård matchning för sportspecifika ändamål (t.ex., "utrustning", "resa", "träning")
            2. Kommun (om angivet) → Måste matcha den valda kommunen
            """

      )
    }

    if elite_athlete:
        query_template["context"] += """

    För elitidrottare ska du prioritera:
    1. Sport → Hård matchning (måste matcha sporten)
    2. Syfte → Hård matchning (t.ex. utrustning, resa, träning)
    3. IGNORERA studie-nivå och ämnesområde helt
    4. Returnera minst 15 relevanta stipendier

    """

    combined_query = json.dumps(query_template, ensure_ascii=False)

    translated_query = (
        safe_translate(combined_query, source="en", target="sv")
        if language.lower() == "en"
        else combined_query
    )

    if debug:
        print(f"\n Structured Query for Embedding:\n{translated_query}\n")

    query_emb = get_openai_embedding(translated_query)
    if query_emb is None:
        print("Embedding generation failed.")
        return []



    # PRIORITY: Elite athlete overrides user_type filtering
    filters = {}

# PRIORITY: Elite athlete overrides user_type filtering
    if elite_athlete:
       filters["Kommentar"] = {"$in": ["Flera", "Idrottsförening", "Studier"]}

    elif user_type.lower() in ["individual", "person"]:
      filters["Kommentar"] = {"$in": ["Flera", "Studier"]}

    elif user_type.lower() == "organisation":
      filters["Kommentar"] = {"$in": ["Flera", "Idrottsförening"]}

    if elite_athlete:
        filters["Sport NY kategori"] = {
            "$in": [
                "Oklar idrott",
                "Gymnastik",
                "Tennis",
                "Ishockey; Skridsko",
                "Fotboll; Bandy",
                "Skidskytte; Orientering",
                "Fotboll"
            ]
        }
    if municipality_filter and municipality:
        filters["Kommun"] = municipality.strip()

    if debug:
        print(f"Pinecone Filters:\n{json.dumps(filters, indent=4, ensure_ascii=False)}\n")


    try:
        res = index.query(
            vector=query_emb,
            top_k=top_k * 2,
            include_metadata=True,
            filter=filters
        )
    except Exception as e:
        print(f" Pinecone query failed: {e}")
        return []

    matches = res.get("matches", [])
    if not matches:
        print(" No scholarships found.")
        return []


    def compute_soft_score(sch, purpose, level, subj, gen, elite_athlete=False, sport=None):
        combined_text = f"{sch.get('Purpose','')}" \
                        f" {sch.get('Study Level','')}" \
                        f" {sch.get('Sport','')}".lower()
        factor_score = 0

        # ✅ Elite athlete logic
        if elite_athlete:
            if purpose:
                purp_score = fuzz.token_sort_ratio(purpose.lower(), combined_text)
                factor_score += purp_score / 100

            if sport:
                sport_score = fuzz.token_set_ratio(sport.lower(), combined_text)
                factor_score += sport_score / 100

            return round(factor_score, 3)

        # 🔹 Existing logic
        if subj:
            subj_score = fuzz.token_set_ratio(subj.lower(), combined_text)
            factor_score += subj_score / 100

        if level:
            lvl_score = fuzz.partial_ratio(level.lower(), combined_text)
            factor_score += lvl_score / 100

        if purpose:
            purp_score = fuzz.token_sort_ratio(purpose.lower(), combined_text)
            factor_score += purp_score / 100

        if gen:
            gen_score = fuzz.partial_ratio(gen.lower(), combined_text)
            factor_score += gen_score / 100

        return round(factor_score, 3)


    results_data = []
    for m in matches:
        md = m["metadata"]
        s = {
            "Name": md.get("Namn", ""),
            "Municipality": md.get("Kommun", ""),
            "Category": md.get("Category", ""),
            "Purpose": md.get("Ändamål", ""),
            "Study Level": md.get("study level", ""),
            "Email": md.get("Epost", ""),
            "Website": md.get("Websida", ""),
            "Phone": md.get("Telefon", ""),
            "Assets": md.get("Tillgångar", ""),
            "Main Address": md.get("Huvudadress", ""),
            "Postal Code": md.get("Postnr", ""),
            "City": md.get("Postort", ""),
            "County": md.get("Län", ""),
            "Sport": md.get("Sport NY kategori", ""),
            "Base Score": round(m["score"], 4)
        }
        s["Relevance Score"] = compute_soft_score(
    s,
    user_purpose,
    study_level,
    subject,
    gender,
    elite_athlete=elite_athlete,
    sport=sport
)
        results_data.append(s)

    # Hard filter for elite athletes based on sport
    if elite_athlete and sport:
        sport_lower = sport.lower().strip()
        filtered_results = []
        for r in results_data:
            # Split Sport field by semicolon and check if user sport matches any
            sports_in_scholarship = [s.strip().lower() for s in r.get('Sport', '').split(';')]
            if sport_lower in sports_in_scholarship:
                filtered_results.append(r)
        results_data = filtered_results


    def is_reasonably_relevant(sch):
        text = f"{sch.get('Purpose','')}" \
               f" {sch.get('Study Level','')}" \
               f" {sch.get('Sport','')}".lower()

        # ✅ NEW: Elite athlete logic
        if elite_athlete:
            sport_ok = not sport or fuzz.partial_ratio(sport.lower(), text) > 40
            purpose_ok = not user_purpose or fuzz.partial_ratio(user_purpose.lower(), text) > 30
            high_semantic = sch.get("Base Score", 0) > 0.75

            return sport_ok or purpose_ok or high_semantic

        # 🔹 Existing logic (UNCHANGED)
        subj_ok = not subject or fuzz.partial_ratio(subject, text) > 25
        lvl_ok = not study_level or fuzz.partial_ratio(study_level, text) > 25
        high_semantic = sch.get("Base Score", 0) > 0.78

        return subj_ok or lvl_ok or high_semantic


    results_data = [r for r in results_data if is_reasonably_relevant(r)]

    results_data = sorted(
        results_data,
        key=lambda x: (x["Base Score"] + x["Relevance Score"]),
        reverse=True
    )

    if debug:
        print(f" {len(results_data)} scholarships retrieved and pre-ranked successfully.\n")


    if use_llm_rerank and len(results_data) > 3:
        try:
            ranked = rerank_with_llm(combined_query, results_data[:top_k], openai, top_n=top_k)
            results_data = ranked
            print(" LLM re-ranking applied successfully.")
        except Exception as e:
            print(f" LLM re-ranking failed: {e}")

    return results_data



def format_scholarship_json(scholarship_list: List[Dict[str, Any]], output_language: str = "en") -> str:
    formatted_list = []
    for scholarship in scholarship_list:
        formatted_entry = {}
        for key, value in scholarship.items():
            if output_language.lower() == "en" and isinstance(value, str) and value.strip():
                try:
                    translated_value = safe_translate(value, source="sv", target="en")
                    formatted_entry[key] = translated_value
                except Exception:
                    formatted_entry[key] = value
            else:
                formatted_entry[key] = value
        formatted_list.append(formatted_entry)
    return formatted_list
    return json.dumps(formatted_list, indent=4, ensure_ascii=False)


def llm_filter_scholarships(
    user_purpose: str,
    study_level: str,
    subject: str,
    gender: str,
    scholarships: List[Dict[str, Any]],
    model: str = "gpt-4o-mini",
    debug: bool = True
) -> List[Dict[str, Any]]:

    if not scholarships:
        if debug:
            print("[LLM FILTER] No scholarships provided — returning empty list.")
        return []

    if debug:
        print(f"\n[LLM FILTER] Received {len(scholarships)} scholarships for LLM filtering.\n")

    # Build strict user context
    user_context = f"""
    USER REQUIREMENTS:
    • Purpose: {user_purpose}
    • Study Level: {study_level}
    • Subject: {subject}
    • Gender: {gender}

    STRICT RELEVANCE RULES:
    1. Study Level → HARD MATCH (must match user level or be obviously suitable)
    2. Subject → Must be semantically aligned; related fields are acceptable.
    3. Gender Rules:
         - female user → only female/open scholarships allowed
         - male user → only male/open scholarships allowed
    4. Purpose → Must closely match or support user's stated purpose.
    5. Include at least 8–10 scholarships if possible.
    """

    scholarship_blocks = []
    for idx, s in enumerate(scholarships):
        block = f"""
        [{idx}]
        Name: {s.get('Name', '')}
        Purpose: {s.get('Purpose', '')}
        Category: {s.get('Category', '')}
        Study Level: {s.get('Study Level', '')}
        """
        scholarship_blocks.append(block)

    combined_text = "\n".join(scholarship_blocks)

    # ==== FINAL PROMPT STRUCTURE ====
    prompt = f"""
    Evaluate the following scholarships for relevance:

    {combined_text}

    Based on the user's requirements:

    {user_context}

    Respond ONLY with valid JSON in this exact format:

    [
      {{"index": 0, "relevance": "relevant"}},
      {{"index": 1, "relevance": "irrelevant"}}
    ]

    DO NOT add commentary, explanations, markdown, or extra text.
    ALWAYS return valid JSON.
    """

    response = openai.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You always return strict JSON output."},
            {"role": "user", "content": prompt}
        ],
        temperature=0
    )

    raw_content = response.choices[0].message.content

    if debug:
        print("\n[LLM FILTER] Raw LLM Output:")
        print("-----------------------------------")
        print(raw_content)
        print("-----------------------------------\n")

    if not raw_content or raw_content.strip() == "":
        if debug:
            print("[LLM FILTER] ERROR: Empty LLM response — returning ALL scholarships.")
        return scholarships

    try:
        decisions = json.loads(raw_content)
    except Exception as e:
        if debug:
            print("[LLM FILTER] JSON PARSE ERROR — returning ALL scholarships.")
            print(f"Error: {e}")
            import traceback
            print(traceback.format_exc())
        return scholarships

    relevant_indices = {
        d.get("index")
        for d in decisions
        if isinstance(d, dict) and d.get("relevance", "").lower() == "relevant"
    }

    relevant_indices = {
        i for i in relevant_indices
        if isinstance(i, int) and 0 <= i < len(scholarships)
    }

    filtered = [scholarships[i] for i in sorted(relevant_indices)]

    if debug:
        excluded = sorted(set(range(len(scholarships))) - relevant_indices)
        print(f"[LLM FILTER] Relevant Scholarships: {len(filtered)}")
        print(f"[LLM FILTER] Excluded Scholarships: {len(excluded)}")
        print(f"[LLM FILTER] Excluded Indexes: {excluded}\n")

    return filtered




# ==========================================================================================
# ==========================================================================================
# ==========================================================================================
# ==========================================================================================
# ==========================================================================================
# ==========================================================================================
# ==========================================================================================
# ==========================================================================================
# ==========================================================================================
# ==========================================================================================
# ==========================================================================================
# ==========================================================================================
# ==========================================================================================
# ==========================================================================================




import os
import json
import time
import re
import unicodedata
from typing import List, Dict, Any
import pandas as pd
from fuzzywuzzy import fuzz
from deep_translator import GoogleTranslator
from pinecone import Pinecone, ServerlessSpec
from openai import OpenAI
from tiktoken import get_encoding
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv
import numpy as np




INDEX_NAME = "scholarships-index-latest"
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536

if INDEX_NAME not in [i.name for i in pc.list_indexes()]:
    pc.create_index(
        name=INDEX_NAME,
        dimension=EMBEDDING_DIM,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1")
    )
    time.sleep(10)

index = pc.Index(INDEX_NAME)
enc = get_encoding("cl100k_base")
embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL, openai_api_key=OPENAI_API_KEY)

print("Connected to Pinecone vector store successfully")


FIELD_MAP_SV = {
    "Name": "Namn",
    "Subject": "ämne",
    "Municipality": "Kommun",
    "Category": "Kategori",
    "Purpose": "Ändamål",
    "Study Level": "Utbildningsnivå",
    "Email": "Epost",
    "Website": "Websida",
    "Phone": "Telefon",
    "Assets": "Tillgångar",
    "Main Address": "Huvudadress",
    "Main_Address": "Huvudadress",
    "Postal Code": "Postnr",
    "City": "Postort",
    "County": "Län",
    "Sport": "Sport NY kategori"
}
 
 
def safe_truncate(text, max_tokens=8192):
    tokens = enc.encode(text)
    if len(tokens) > max_tokens:
        tokens = tokens[:max_tokens]
        text = enc.decode(tokens)
    return text


def get_openai_embedding(text: str):
    text = text.strip()
    if not text:
        return None
    text = safe_truncate(text)
    response = openai.embeddings.create(model=EMBEDDING_MODEL, input=text)
    return response.data[0].embedding


def safe_translate(text, source, target, max_len=4500):
    if not text or not isinstance(text, str):
        return text
    if len(text) < max_len:
        return GoogleTranslator(source=source, target=target).translate(text)
    chunks = [text[i:i + max_len] for i in range(0, len(text), max_len)]
    translated_chunks = []
    for chunk in chunks:
        try:
            translated_chunks.append(GoogleTranslator(source=source, target=target).translate(chunk))
        except Exception:
            translated_chunks.append(chunk)
    return " ".join(translated_chunks)



MIN_RESULTS = 10  


def rerank_with_llm(query, scholarships, openai_client, top_n=10):
    formatted_text = "\n".join([
        f"{i+1}. {s['Name']} — Purpose: {s['Purpose']}"
        for i, s in enumerate(scholarships)
    ])

    prompt = f"""
    "Du är en intelligent stipendierekommendationsassistent. "
          "Ditt uppdrag är att hitta och rangordna stipendier som exakt matchar användarens uppgifter. "
          "Du ska bedöma och prioritera baserat på fyra huvuddimensioner:\n\n"

          "1.**Ämne / Studieområde** – Den viktigaste faktorn. "
          "Inkludera endast stipendier vars ändamål, beskrivning eller behörighetskrav "
          "tydligt nämner eller starkt relaterar till användarens valda ämne. "
          "Exempel: Om användaren väljer teknik och ingenjörsvetenskap, inkludera endast stipendier "
          "som handlar om teknik eller ingenjörsvetenskap – uteslut alla andra områden.\n\n"

          "2. **Utbildningsnivå** – Näst viktigast. "
          "Stipendierna måste matcha användarens utbildningsnivå (t.ex. gymnasium, kandidat, master, doktorand). "
          "Om användaren väljer 'grundnivå' eller 'universitet', inkludera endast stipendier som erbjuds på dessa nivåer.\n\n"

          "3. **Syfte / Avsikt** – Tredje prioritet. "
          "Matcha stipendier till användarens syfte, såsom forskning, studieavgifter eller levnadskostnader. "
          "Stipendier som semantiskt stämmer överens med användarens mål prioriteras.\n\n"

          "4. **Könsrelevans** – Fjärde prioritet. "
          "Om användaren anger ett kön (t.ex. man eller kvinna), inkludera endast stipendier som uttryckligen "
          "riktar sig till det könet eller är könsneutrala.\n\n"

          " **Prioritetsordning:** Ämne ➜ Utbildningsnivå ➜ Syfte ➜ Kön.\n\n"

          "**OBS:** Om användaren **inte** anger någon variabel (t.ex. ämne, utbildningsnivå, syfte eller kön), "
          "ska AI:n **inte** söka eller filtrera efter den variabeln. "
          "Till exempel, om användaren inte specificerar ett ämne eller kön, ska AI:n inkludera stipendier "
          "från alla ämnen eller kön istället för att utesluta dem.\n\n"

          "Uteslut stipendier som inte matchar användarens ämne eller utbildningsnivå när dessa anges. "
          "Returnera endast de mest relevanta stipendierna baserat på användarens uppgifter."

    Query: {query}

    Scholarships:
    {formatted_text}

    IMPORTANT: Return a JSON list of INTEGER INDEXES (1-based, matching the
    numbers above) in best-match order. Example: [3, 1, 7, 2]
    Return only the top {top_n} indexes. No names, no explanations, only a
    JSON integer array.
    """

    response = openai_client.chat.completions.create(
        model="gpt-5",
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.choices[0].message.content.strip()

    if raw.startswith("```"):
        raw = raw.strip("`").strip()
        if raw.lower().startswith("json"):
            raw = raw[4:].strip()

    try:
        ranked_indexes = json.loads(raw)
        ranked_list = []
        for idx in ranked_indexes:
            if isinstance(idx, int) and 1 <= idx <= len(scholarships):
                ranked_list.append(scholarships[idx - 1])
        
        if len(ranked_list) < top_n:
            seen = {id(s) for s in ranked_list}
            remaining = [s for s in scholarships if id(s) not in seen]
            ranked_list.extend(remaining[: top_n - len(ranked_list)])
        return ranked_list[:top_n]
    except Exception:
        return scholarships[:top_n]


def find_scholarships_v2(
    user_purpose: str,
    user_type: str = "individual",
    municipality: str = None,
    municipality_filter: bool = False,
    gender: str = None,
    language: str = "en",
    top_k: int = 30,
    debug: bool = True,
    use_llm_rerank: bool = True
) -> List[Dict[str, Any]]:

    DEFAULT_QUERY_TEMPLATE = {
        "purpose": user_purpose or "",
        "context": """
            DITT JOBB:

STEG 1 — ANALYSERA ANVÄNDARENS SYFTE
- Identifiera vilket ämne/område användaren studerar eller är intresserad av  
  (t.ex. teknik, medicin, juridik, datavetenskap, konst etc.)
  → Om inget ämne nämns: hoppa över ämnesfiltrering helt

- Identifiera användarens studienivå  
  (t.ex. gymnasium, grundutbildning, kandidatexamen, master, doktorsexamen etc.)
  → Om ingen studienivå nämns: hoppa över filtrering av studienivå helt


STEG 2 — UTVÄRDERA VARJE STIPENDIUM

1. ÄNDAMÅLSMATCHNING (HÖGSTA PRIORITET)
   - Stipendiets syfte MÅSTE direkt matcha användarens behov
   - Icke-relaterade stipendier = IRRELEVANTA

2. ÄMNESMATCHNING
   - Om ett ämne identifierades i Steg 1:
     → Stipendiet måste vara relevant för detta ämne
     → Ex: teknikstudent → konststipendium = IRRELEVANT
   - Om inget ämne hittades:
     → Ignorera denna regel helt

3. STUDIENIVÅMATCHNING
   - Om studienivå identifierades:
     → Stipendiet måste passa denna nivå eller vara öppet för alla nivåer
   - Om ingen studienivå hittades:
     → Ignorera denna regel helt

4. KÖN
   - Kvinnlig användare → endast kvinnliga eller öppna stipendier
   - Manlig användare → endast manliga eller öppna stipendier
   - Ej specificerat → inkludera alla

5. OSÄKERHET
   - Vid minsta tveksamhet → markera som IRRELEVANTA
   - Endast EXAKTA och tydliga matchningar ska inkluderas
        """
    }

    if settings.SITE_CONFIG.use_default:
        query_template = DEFAULT_QUERY_TEMPLATE
    else:
        query_template = settings.SITE_CONFIG.query_template


    combined_query = json.dumps(query_template, ensure_ascii=False)


    translated_query = (
        safe_translate(combined_query, source="en", target="sv")
        if language.lower() == "en"
        else combined_query
    )

    if debug:
        print(f"\n Structured Query for Embedding:\n{translated_query}\n")


    query_emb = get_openai_embedding(translated_query)
    if query_emb is None:
        print("Embedding generation failed.")
        return []

    filters = {}

    if user_type.lower() in ["individual", "person"]:
        filters["Kommentar"] = {"$in": ["Flera", "Studier"]}
    elif user_type.lower() == "organization":
        filters["Kommentar"] = {"$in": ["Flera", "Idrottsförening"]}

    if municipality_filter and municipality:
        filters["Kommun"] = municipality.strip()

    if debug:
        print(f"Pinecone Filters:\n{json.dumps(filters, indent=4, ensure_ascii=False)}\n")


    try:
        res = index.query(
            vector=query_emb,
            top_k=top_k * 3,
            include_metadata=True,
            filter=filters if filters else None
        )
        print(res)
        print("kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk")
    except Exception as e:
        print(f" Pinecone query failed: {e}")
        return []

    matches = res.get("matches", [])
    if not matches:
        print(" No scholarships found.")
        return []

 
    def compute_soft_score(sch, purpose):
        combined_text = f"{sch.get('Purpose', '')}".lower()
        factor_score = 0
        if purpose:
            purp_score = fuzz.token_sort_ratio(purpose.lower(), combined_text)
            factor_score += purp_score / 100
        return round(factor_score, 3)

    results_data = []
    for m in matches:
        md = m["metadata"]
        s = {
            "Name": md.get("Namn", ""),
            "Municipality": md.get("Kommun", ""),
            "Category": md.get("Category", ""),
            "Purpose": md.get("Ändamål", ""),
            "Study Level": md.get("study level", ""),
            "Email": md.get("Epost", ""),
            "Website": md.get("Websida", ""),
            "Phone": md.get("Telefon", ""),
            "Assets": md.get("Tillgångar", ""),
            "Main Address": md.get("Huvudadress", ""),
            "Postal Code": md.get("Postnr", ""),
            "City": md.get("Postort", ""),
            "County": md.get("Län", ""),
            "Sport": md.get("Sport NY kategori", ""),
            "Base Score": round(m["score"], 4)
        }
        s["Relevance Score"] = compute_soft_score(s, user_purpose)
        results_data.append(s)

  
    def is_reasonably_relevant(sch, user_purpose):
        text = f"{sch.get('Purpose', '')}".lower()
        purpose_ok = not user_purpose or fuzz.partial_ratio(user_purpose.lower(), text) > 30
        print(sch)
        print("uuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuu")
        high_semantic = sch.get("Base Score", 0) > 0.78

        return purpose_ok or high_semantic

    results_data = [r for r in results_data if is_reasonably_relevant(r, user_purpose)]


    results_data = sorted(
        results_data,
        key=lambda x: (x["Base Score"] + x["Relevance Score"]),
        reverse=True
    )

    if debug:
        print(f" {len(results_data)} scholarships retrieved and pre-ranked successfully.\n")

   
    if len(results_data) > 0:
        try:
            # Pass A — with gender, full pool
            strict_results = llm_filter_scholarships(
                user_purpose=user_purpose,
                gender=gender,
                enforce_gender=True,
                scholarships=results_data,  
                model="gpt-4o",
                debug=debug
            )

            if len(strict_results) >= MIN_RESULTS:
                results_data = strict_results
                if debug:
                    print(f" Gender filter applied. {len(results_data)} results to rerank.")
            else:
                if debug:
                    print(f" Only {len(strict_results)} results with gender filter."
                          f" Relaxing gender to reach {MIN_RESULTS}...")


                relaxed_results = llm_filter_scholarships(
                    user_purpose=user_purpose,
                    gender=None,
                    enforce_gender=False,
                    scholarships=results_data,   
                    model="gpt-4o-mini",
                    debug=debug
                )

     
                seen_names = {r["Name"] for r in strict_results}
                fill = [r for r in relaxed_results if r["Name"] not in seen_names]
                results_data = (strict_results + fill)

                if debug:
                    print(f" Gender relaxed. {len(results_data)} results to rerank.")

            print(" LLM filter cleanup applied successfully.")
        except Exception as e:
            print(f" LLM filter cleanup failed: {e}")
            
    if use_llm_rerank and len(results_data) > 3:
        try:
            ranked = rerank_with_llm(
                combined_query,
                results_data,
                openai,
                top_n=MIN_RESULTS   # always return exactly 10
            )
            results_data = ranked
            print(" LLM re-ranking applied successfully.")
        except Exception as e:
            print(f" LLM re-ranking failed: {e}")
            results_data = results_data[:MIN_RESULTS]   # fallback slice to 10
    else:
        results_data = results_data[:MIN_RESULTS]

    return results_data


def format_scholarship_json(
    scholarship_list: List[Dict[str, Any]],
    output_language: str = "en"
) -> str:
 
    formatted_list = []
 
    for scholarship in scholarship_list:
        formatted_entry = {}
 
        for key, value in scholarship.items():
 
            # ---------- SWEDISH OUTPUT ----------
            if output_language.lower() == "sv":
 
                sw_key = FIELD_MAP_SV.get(key, key)
 
                if isinstance(value, str) and value.strip():
                    try:
                        # translate only if value seems English
                        translated_value = safe_translate(value, source="en", target="sv")
                        formatted_entry[sw_key] = translated_value
                    except Exception:
                        formatted_entry[sw_key] = value
                else:
                    formatted_entry[sw_key] = value
 
            # ---------- ENGLISH OUTPUT ----------
            else:
 
                if isinstance(value, str) and value.strip():
                    try:
                        translated_value = safe_translate(value, source="sv", target="en")
                        formatted_entry[key] = translated_value
                    except Exception:
                        formatted_entry[key] = value
                else:
                    formatted_entry[key] = value
 
        formatted_list.append(formatted_entry)
    
    return formatted_list
    # return json.dumps(formatted_list, indent=4, ensure_ascii=False)


def llm_filter_scholarships(
    user_purpose: str,
    gender: str,
    scholarships: List[Dict[str, Any]],
    enforce_gender: bool = True,
    model: str = "gpt-4o-mini",
    debug: bool = True
) -> List[Dict[str, Any]]:

    if not scholarships:
        if debug:
            print("[LLM FILTER] No scholarships provided — returning empty list.")
        return []

    if debug:
        print(f"\n[LLM FILTER] Received {len(scholarships)} scholarships "
              f"(enforce_gender={enforce_gender}).\n")

    # Gender rule is injected only when enforce_gender=True and gender is given
    if enforce_gender and gender:
        gender_rule = f"""
      4. GENDER (LOWEST PRIORITY)
         User gender: {gender}
         - female → exclude scholarships explicitly for males only
         - male   → exclude scholarships explicitly for females only
         - Keep all gender-neutral scholarships regardless.
         NOTE: Only remove a scholarship on gender if it is EXPLICITLY for
         the opposite gender. When in doubt → keep it.
    """
    else:
        gender_rule = """
      4. GENDER → Completely ignored in this pass. Include all scholarships
         regardless of any gender targeting.
    """

    user_context = f"""
    USER PURPOSE (exactly as typed):
    "{user_purpose}"

    YOUR JOB:

    STEP 1 — Extract from the purpose sentence:
      - Subject/field (e.g. engineering, medicine, law, arts, IT)
        → If none mentioned: skip subject filtering entirely
      - Study level (e.g. undergraduate, bachelor, master, PhD)
        → If none mentioned: skip study level filtering entirely

    STEP 2 — Evaluate each scholarship using these rules IN ORDER:

      1. PURPOSE MATCH (HIGHEST PRIORITY)
         The scholarship purpose must DIRECTLY match what the user needs
         money for. Clearly unrelated = irrelevant.

      2. SUBJECT MATCH
         If subject detected → scholarship must relate to that subject.
         Example: user studies engineering → art scholarship = irrelevant.
         If no subject detected → skip this rule entirely.

      3. STUDY LEVEL MATCH
         If study level detected → scholarship must match that level or be
         open to all levels.
         If no study level detected → skip this rule entirely.

    {gender_rule}

      5. MINIMUM RESULTS RULE (IMPORTANT)
         You MUST mark at least {MIN_RESULTS} scholarships as relevant.
         If strict rules leave fewer than {MIN_RESULTS}, relax subject and
         study level and include next best purpose-matched scholarships
         until you reach {MIN_RESULTS}.

      6. DOUBT RULE
         When genuinely unsure → mark as relevant (don't over-filter).
    """

    scholarship_blocks = []
    for idx, s in enumerate(scholarships):
        block = f"""
        [{idx}]
        Name: {s.get('Name', '')}
        Purpose: {s.get('Purpose', '')}
        Category: {s.get('Category', '')}
        Study Level: {s.get('Study Level', '')}
        """
        scholarship_blocks.append(block)

    combined_text = "\n".join(scholarship_blocks)

    prompt = f"""
    A user is looking for scholarships. Their full request:
    "{user_purpose}"

    Candidate scholarships:
    {combined_text}

    Evaluation rules:
    {user_context}

    Respond ONLY with valid JSON in this exact format:
    [
      {{"index": 0, "relevance": "relevant"}},
      {{"index": 1, "relevance": "irrelevant"}}
    ]

    DO NOT add commentary, explanations, markdown, or extra text.
    ALWAYS return valid JSON.
    ALWAYS mark at least {MIN_RESULTS} scholarships as relevant if available.
    """

    response = openai.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You always return strict JSON output."},
            {"role": "user", "content": prompt}
        ],
        temperature=0
    )

    raw_content = response.choices[0].message.content

    # Strip markdown fences if present
    if raw_content and raw_content.strip().startswith("```"):
        raw_content = raw_content.strip().strip("`").strip()
        if raw_content.lower().startswith("json"):
            raw_content = raw_content[4:].strip()

    if debug:
        print("\n[LLM FILTER] Raw LLM Output:")
        print("-----------------------------------")
        print(raw_content)
        print("-----------------------------------\n")

    if not raw_content or raw_content.strip() == "":
        if debug:
            print("[LLM FILTER] ERROR: Empty response — returning ALL scholarships.")
        return scholarships

    try:
        decisions = json.loads(raw_content)
    except Exception as e:
        if debug:
            print("[LLM FILTER] JSON PARSE ERROR — returning ALL scholarships.")
            print(f"Error: {e}")
            import traceback
            print(traceback.format_exc())
        return scholarships

    relevant_indices = {
        d.get("index")
        for d in decisions
        if isinstance(d, dict) and d.get("relevance", "").lower() == "relevant"
    }

    relevant_indices = {
        i for i in relevant_indices
        if isinstance(i, int) and 0 <= i < len(scholarships)
    }

    # ── Safety net: if LLM still returned fewer than MIN_RESULTS,
    #    top up from remaining scholarships by Base Score
    if len(relevant_indices) < MIN_RESULTS:
        all_indices = set(range(len(scholarships)))
        remaining = sorted(
            all_indices - relevant_indices,
            key=lambda i: scholarships[i].get("Base Score", 0),
            reverse=True
        )
        needed = MIN_RESULTS - len(relevant_indices)
        relevant_indices.update(remaining[:needed])
        if debug:
            print(f"[LLM FILTER] Safety net: added {needed} results to reach {MIN_RESULTS}.")

    excluded = sorted(set(range(len(scholarships))) - relevant_indices)
    filtered = [scholarships[i] for i in sorted(relevant_indices)]

    if debug:
        print(f"[LLM FILTER] Relevant Scholarships: {len(filtered)}")
        print(f"[LLM FILTER] Excluded Scholarships: {len(excluded)}")
        print(f"[LLM FILTER] Excluded Indexes: {excluded}\n")

    return filtered