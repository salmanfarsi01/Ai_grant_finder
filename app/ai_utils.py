import os

import json

import pandas as pd

from deep_translator import GoogleTranslator

from concurrent.futures import ThreadPoolExecutor

# from openai import OpenAI
import openai
 
# ======================================

COLUMN_MAP = {

    "Name": "Namn",

    "MainAddress": "Huvudadress",

    "PostalCode": "Postnr",

    "City": "Postort",

    "Phone": "Telefon",

    "Assets": "Tillgångar",

    "Purpose": "Ändamål",

    "Municipality": "Kommun",

    "County": "Län"

}
 
REQUIRED_KEYS = list(COLUMN_MAP.keys())
 
translators = {

    'en': GoogleTranslator(source="sv", target="en"),

    'sv': GoogleTranslator(source="en", target="sv")

}
 
# 🔑 Set OpenAI API Key

# client = OpenAI(api_key="my_openai_key")
openai.api_key = "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"

MODEL_ID = "gpt-5-nano"

def _normalize_text(s):

    if pd.isna(s): return ""

    return str(s).strip()
 
def load_dataset(path):

    df = pd.read_excel(path)

    for col in df.columns:

        df[col] = df[col].apply(_normalize_text)

    return df
 
def filter_by_kommun(df, kommun_value):

    kv = kommun_value.strip().lower()

    kommun_col = COLUMN_MAP["Municipality"]

    exact = df[df[kommun_col].str.lower() == kv]

    if not exact.empty:

        return exact

    return df[df[kommun_col].str.lower().str.contains(kv, na=False)]
 
def df_to_records(df):

    records = []

    for _, row in df.iterrows():

        rec = {k: _normalize_text(row[COLUMN_MAP[k]]) for k in REQUIRED_KEYS}

        records.append(rec)

    return records
 
def translate_helpers(item, detected_language):

    translator = translators[detected_language]

    for k, v in list(item.items()):

        if v and isinstance(v, str):

            try:

                item.pop(k)

                if k not in ('Name', 'Namn'):

                    item[(t_k := translator.translate(k))] = translator.translate(v)

                else:

                    _k = 'Name' if detected_language == 'en' else 'Namn'

                    item[_k] = v

            except:

                pass

    return item
 
def translate_results_to_english(payload, detected_language):

    with ThreadPoolExecutor(max_workers=50) as executor:

        results = executor.map(

            lambda item: translate_helpers(item, detected_language),

            payload["matching_scholarships"]

        )

    payload["matching_scholarships"] = list(results)

    return payload
 
PROMPT_TEMPLATE = """

You are a scholarship matching assistant for Sweden.
 
Return strictly in this format:
 
Detected language: {detected_language}

{{

  "matching_scholarships": [

    {{

        "Name": "...",

        "MainAddress": "...",

        "PostalCode": "...",

        "City": "...",

        "Phone": "...",

        "Assets": "...",

        "Purpose": "...",

        "Municipality": "...",

        "County": "..."

    }}

  ]

}}
 
Instructions:

- Consider the USER INFO carefully (purpose, education level, gender, age, elite athlete status, sport, etc.).

- Based on scholarships purpose or syfte provide the most relevant scholarships to the user.

- Keep the JSON structure exact, without adding extra fields.

"""
 
def build_prompt(user_type, kommun, records, top_n, detected_language, user_info):

    return PROMPT_TEMPLATE.format(detected_language=detected_language) + \
           f"\nUSER TYPE: {user_type}\nTARGET KOMMUN: {kommun}\nTOP_N: {top_n}\n" + \
           f"\n=== USER INFO ===\n{json.dumps(user_info, ensure_ascii=False)}\n" + \
           f"\n=== SCHOLARSHIP RECORDS ===\n{json.dumps(records, ensure_ascii=False)}"
 
# 🔹 Replaced Gemini with OpenAI

def call_openai(prompt):

    response = openai.ChatCompletion.create(

        model=MODEL_ID,

        messages=[{"role": "user", "content": prompt}]

    )

    print(response.choices[0].message.content)
    return response.choices[0].message.content
 
def extract_json_block(mixed_text):

    first_brace = mixed_text.find("{")

    last_brace = mixed_text.rfind("}")

    json_str = mixed_text[first_brace:last_brace+1]

    return json.loads(json_str)
 
# ======================================

# 🔹 STEP 6 — Individual / Organization Functions

# ======================================

def find_scholarships_individual(df, kommun, user_info, top_n=20, detected_language="sv"):

    filtered = filter_by_kommun(df, kommun)

    if filtered.empty:

        return {"matching_scholarships": []}
 
    records = df_to_records(filtered)

    prompt = build_prompt("Individual", kommun, records, top_n, detected_language, user_info)
 
    raw = call_openai(prompt)

    payload = extract_json_block(raw)

    payload["matching_scholarships"] = payload["matching_scholarships"][:top_n]
    
    print("DEBUG LEN", len(payload['matching_scholarships']))
    payload = translate_results_to_english(payload, detected_language.lower())
    print("AFTER AFFECT DEBUG LEN", len(payload['matching_scholarships']))

    return payload
 
def find_scholarships_organization(df, kommun, detected_language="sv"):

    filtered = filter_by_kommun(df, kommun)

    if filtered.empty:

        return {"matching_scholarships": []}
 
    records = df_to_records(filtered)

    payload = {"matching_scholarships": records}
 
    payload = translate_results_to_english(payload, detected_language.lower())

    return payload
 
def find_scholarships(excel_path, kommun, detected_language="sv", user_info=None):

    df = load_dataset(excel_path)

    application_type = user_info['role']

    if application_type in ['organization', 'Organization']:

        return find_scholarships_organization(df, kommun, detected_language)

    else:

        return find_scholarships_individual(df, kommun, user_info or {}, top_n=20, detected_language=detected_language)

 