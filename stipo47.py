
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

load_dotenv()

# Use hardcoded keys as fallback if environment variables are not set
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "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")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", "pcsk_5Q6iJy_3v4Anzkg9zFjqvYnPyAV7frnzzyvVsfs7RYBtkWGZQJKdVpn339DFRitPi4nxc5")


if not OPENAI_API_KEY or not PINECONE_API_KEY:
    raise ValueError("OPENAI_API_KEY or PINECONE_API_KEY not found in environment variables")

print("Environment variables loaded successfully")
print(f"Using OPENAI_API_KEY: {OPENAI_API_KEY[:5]}...{OPENAI_API_KEY[-5:]}") # Print partial key for debugging
print(f"Using PINECONE_API_KEY: {PINECONE_API_KEY[:5]}...{PINECONE_API_KEY[-5:]}") # Print partial key for debugging



openai = OpenAI(api_key=OPENAI_API_KEY)
pc = Pinecone(api_key=PINECONE_API_KEY)


DATA_PATH = "scholarships.xlsx"
df = pd.read_excel(DATA_PATH, engine="openpyxl").fillna("").astype(str)
print(f"Dataset loaded successfully with {len(df)} rows")


INDEX_NAME = "scholarships-index1"
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
            Prioritet: Ämne ➜ Utbildningsnivå ➜ Syfte ➜ Kön.
            Uteslut stipendier som inte matchar ämne eller nivå när dessa anges.
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
        filters["Category"] = {"$in": ["Flera", "Studier"]}
    elif user_type.lower() == "organization":
        filters["Category"] = {"$in": ["Flera", "Idrottsförening"]}

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



# if __name__ == "__main__":
#     results = find_scholarships_v2(
#         user_purpose="Interested in studying medicine & disease related subjects for my bachelor degree",
#         subject="medicine & health science",
#         user_type="individual",
#         municipality="Stockholm",
#         municipality_filter=True,
#         study_level="university,Masters",
#         gender="female",
#         language="en",
#         top_k=30,
#         debug=True,
#         use_llm_rerank=True
#     )

#     formatted = format_scholarship_json(results, output_language="en")
#     print(formatted)

