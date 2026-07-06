import os
import json
import pickle
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
import pandas as pd
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone, ServerlessSpec
#import openai
import time
from tiktoken import get_encoding
from langchain_openai import OpenAIEmbeddings
from deep_translator import GoogleTranslator
import pandas as pd
import time
from pinecone import Pinecone, ServerlessSpec
from openai import OpenAI
from fuzzywuzzy import fuzz
import time
import re
import unicodedata
from dotenv import load_dotenv


OPENAI_API_KEY = "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"
PINECONE_API_KEY = "pcsk_5Q6iJy_3v4Anzkg9zFjqvYnPyAV7frnzzyvVsfs7RYBtkWGZQJKdVpn339DFRitPi4nxc5"

openai = OpenAI(api_key=OPENAI_API_KEY)
pc = Pinecone(api_key=PINECONE_API_KEY)

def update_index(file_path):
    df = pd.read_excel(file_path, engine="openpyxl")
    # df = pd.read_excel("/content/scholarships.xlsx", engine="openpyxl")
    df = df.fillna("").astype(str)
    print(f"Dataset loaded successfully with {len(df)} rows")

    index_name = "scholarships-index1"
    embedding_dim = 1536  # text-embedding-3-small

    existing_indexes = [i.name for i in pc.list_indexes()]
    if index_name not in existing_indexes:
        print(f"Creating index: {index_name}")
        pc.create_index(
            name=index_name,
            dimension=embedding_dim,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1")
        )
        print(f" Waiting for '{index_name}' to become active...")
        while True:
            desc = pc.describe_index(index_name)
            if desc.status["ready"]:
                print(f" Index '{index_name}' is now ready.")
                break
            time.sleep(3)
    else:
        print(f" Index '{index_name}' already exists.")

    index = pc.Index(index_name)

    enc = get_encoding("cl100k_base")

    def safe_truncate(text, max_tokens=8192):
        """Truncate text if it exceeds the model token limit."""
        tokens = enc.encode(text)
        if len(tokens) > max_tokens:
            print(f" Row truncated ({len(tokens)} → {max_tokens} tokens)")
            tokens = tokens[:max_tokens]
            text = enc.decode(tokens)
        return text

    def get_openai_embedding(text: str):
        text = text.strip()
        if not text:
            return None

        text = safe_truncate(text)
        response = openai.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding

    def embed_and_upload(dataframe, start_idx=0):
        print(f"\n Generating embeddings & uploading to '{index_name}' row by row...")

        for i, row in dataframe.iterrows():
            text = row["Ändamål"].strip()
            if not text:
                continue

            embedding = get_openai_embedding(text)
            if embedding is None:
                continue

            metadata = row.to_dict()
            index.upsert(
                vectors=[{
                    "id": str(start_idx + i),
                    "values": embedding,
                    "metadata": metadata
                }]
            )

            if ((start_idx + i + 1) % 100 == 0):
                print(f" Uploaded {start_idx + i + 1} rows...")

        print(f" Upload completed for rows {start_idx} → {start_idx + len(dataframe) - 1}")

    chunk1 = df.iloc[:3200]
    chunk2 = df.iloc[3200:]

    print("\n Uploading first 3200 rows...")
    embed_and_upload(chunk1, start_idx=0)

    print("\n Uploading remaining rows...")
    embed_and_upload(chunk2, start_idx=3200)

    print("All embeddings uploaded successfully!")

