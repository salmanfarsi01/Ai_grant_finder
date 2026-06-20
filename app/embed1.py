import os
import json
import pickle
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone, ServerlessSpec
import time
from tiktoken import get_encoding
from langchain_openai import OpenAIEmbeddings
from deep_translator import GoogleTranslator
from openai import OpenAI
from fuzzywuzzy import fuzz

def update_pinecone_embeddings(file_path=None, index_name=None):

    def load_env_variables():
        """Load API keys directly from .env file by parsing it manually."""
        env_path = os.path.join(os.path.dirname(__file__), '.env')
        env_path = ".env"
        
        if not os.path.exists(env_path):
            raise FileNotFoundError(f" .env file not found at {env_path}")
        
        api_keys = {}
        try:
            with open(env_path, 'r', encoding='utf-8') as file:
                for line in file:
                    line = line.strip()
                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue
                    # Parse key=value pairs
                    if '=' in line:
                        key, value = line.split('=', 1)
                        api_keys[key.strip()] = value.strip()
        except Exception as e:
            raise ValueError(f" Error reading .env file: {e}")
        
        return api_keys

    # Load the API keys
    api_keys = load_env_variables()
    OPENAI_API_KEY = api_keys.get("OPENAI_API_KEY")
    PINECONE_API_KEY = api_keys.get("PINECONE_API_KEY")

    if not OPENAI_API_KEY or not PINECONE_API_KEY:
        raise ValueError(" API keys not found in .env file")

    print("API keys loaded successfully from .env file")

    openai = OpenAI(api_key=OPENAI_API_KEY)
    pc = Pinecone(api_key=PINECONE_API_KEY)

    # Use provided file path or default
    if not file_path:
        file_path = "reports/new_scholarships_db.xlsx"
    
    df = pd.read_excel(file_path, engine="openpyxl")
    df = df.fillna("").astype(str)
    print(f"Dataset loaded successfully from {file_path} with {len(df)} rows")

    # Use provided index_name, or get from SiteConfig, or use default
    if not index_name:
        index_name = "scholarships-index-latest"
        try:
            from django.conf import settings
            from app.models import SiteConfig
            site_config = SiteConfig.objects.first()
            if site_config and site_config.active_dataset_index_name:
                index_name = site_config.active_dataset_index_name
                print(f"✓ Using custom index name from SiteConfig: {index_name}")
            else:
                print(f"✓ Using default index name: {index_name}")
        except Exception as e:
            print(f"Note: Could not load index name from SiteConfig, using default. Error: {e}")
    else:
        print(f"✓ Using provided index name: {index_name}")
    
    # Sanitize index name for Pinecone (underscores → hyphens, lowercase)
    # Pinecone requires: lowercase alphanumeric characters or '-' only
    index_name = index_name.replace('_', '-').lower()
    print(f"✓ Sanitized index name for Pinecone: {index_name}")
    
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
                print(f"Index '{index_name}' is now ready.")
                break
            time.sleep(3)
    else:
        print(f"Index '{index_name}' already exists.")

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
        """Generate embeddings using OpenAI API."""
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
        """Generate embeddings and upload to Pinecone index."""
        print(f"\nGenerating embeddings & uploading to '{index_name}' row by row...")
        print(f"   Starting from row {start_idx}...")
        total_rows = len(dataframe)
        uploaded_count = 0

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
            uploaded_count += 1

            if (uploaded_count % 100 == 0):
                print(f"   ✓ Uploaded {uploaded_count}/{total_rows} rows (ID: {start_idx + i})...")

        print(f"  Batch completed: {uploaded_count} rows uploaded (IDs: {start_idx} → {start_idx + len(dataframe) - 1})")



    chunk1 = df.iloc[:3200]
    chunk2 = df.iloc[3200:6400]


    if len(df) >= 10000:
        chunk3 = df.iloc[6400:]
        print(f"\n Dataset has {len(df)} rows - Processing 3 chunks")
        print(f"   Chunk 1: 0-{len(chunk1)-1} ({len(chunk1)} rows)")
        print(f"   Chunk 2: {len(chunk1)}-{len(chunk1)+len(chunk2)-1} ({len(chunk2)} rows)")
        print(f"   Chunk 3: {len(chunk1)+len(chunk2)}-{len(df)-1} ({len(chunk3)} rows)")
    else:
        chunk3 = None
        print(f"\nDataset has {len(df)} rows - Processing 2 chunks")
        print(f"   Chunk 1: 0-{len(chunk1)-1} ({len(chunk1)} rows)")
        print(f"   Chunk 2: {len(chunk1)}-{len(df)-1} ({len(chunk2)} rows)")

    print("\nUploading first batch (Chunk 1)...")
    embed_and_upload(chunk1, start_idx=0)

    print("\nUploading second batch (Chunk 2)...")
    embed_and_upload(chunk2, start_idx=3200)

    if chunk3 is not None:
        print("\nUploading third batch (Chunk 3)...")
        embed_and_upload(chunk3, start_idx=6400)

    print("\nAll embeddings uploaded successfully!")
    print("=" * 60)
    
    # Update SiteConfig to mark upload as complete
    try:
        from app.models import SiteConfig
        site_config = SiteConfig.objects.first()
        if site_config:
            site_config.pinecone_updated = True
            site_config.save()
            print(f"\n✅ SUCCESS: Dataset uploaded to Pinecone index '{index_name}'")
            print(f"   Pinecone updated flag set to TRUE")
            print(f"   You can now query this index for scholarships")
    except Exception as e:
        print(f"⚠️  Warning: Could not update SiteConfig status: {e}")


