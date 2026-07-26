import os
import pandas as pd
from pinecone import Pinecone, ServerlessSpec
import time
from tiktoken import get_encoding
from openai import OpenAI


def update_pinecone_embeddings(file_path=None, index_name=None):

    def load_env_variables():
        """Load API keys directly from .env file by parsing it manually."""
        env_path = os.path.join(os.path.dirname(__file__), '.env')
        env_path = '.env'

        if not os.path.exists(env_path):
            raise FileNotFoundError(f' .env file not found at {env_path}')

        api_keys = {}
        try:
            with open(env_path, 'r', encoding='utf-8') as file:
                for line in file:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if '=' in line:
                        key, value = line.split('=', 1)
                        api_keys[key.strip()] = value.strip()
        except Exception as e:
            raise ValueError(f' Error reading .env file: {e}')

        return api_keys

    api_keys = load_env_variables()
    OPENAI_API_KEY = api_keys.get('OPENAI_API_KEY')
    PINECONE_API_KEY = api_keys.get('PINECONE_API_KEY')

    if not OPENAI_API_KEY or not PINECONE_API_KEY:
        raise ValueError(' API keys not found in .env file')

    print('API keys loaded successfully from .env file')

    openai = OpenAI(api_key=OPENAI_API_KEY)
    pc = Pinecone(api_key=PINECONE_API_KEY)

    if not file_path:
        file_path = 'reports/new_scholarships_db.xlsx'

    try:
        from app.models import DatasetUpload
        dataset = DatasetUpload.get_active()
    except Exception:
        dataset = None

    if not file_path and dataset and dataset.scholarships_db_file:
        file_path = dataset.scholarships_db_file.path

    df = pd.read_excel(file_path, engine='openpyxl')
    df = df.fillna('').astype(str)
    print(f'Dataset loaded successfully from {file_path} with {len(df)} rows')

    if not index_name:
        index_name = 'scholarships-index-latest'
        try:
            if dataset:
                index_name = dataset.get_effective_index_name()
                print(f'✓ Using custom index name from DatasetUpload: {index_name}')
            else:
                print(f'✓ Using default index name: {index_name}')
        except Exception as e:
            print(f'Note: Could not load index name from DatasetUpload, using default. Error: {e}')
    else:
        print(f'✓ Using provided index name: {index_name}')

    index_name = index_name.replace('_', '-').lower()
    print(f'✓ Sanitized index name for Pinecone: {index_name}')

    # Initialize dataset upload tracking if an active DatasetUpload exists
    try:
        from django.utils import timezone
        from app.models import DatasetUpload
        if dataset:
            total_rows_full = len(df)
            dataset.upload_in_progress = True
            dataset.upload_status = DatasetUpload.UPLOAD_STATUS_IN_PROGRESS
            dataset.upload_rows_total = total_rows_full
            dataset.upload_rows_uploaded = 0
            dataset.upload_progress_percent = 0
            dataset.upload_error_message = None
            dataset.save()
    except Exception:
        pass

    embedding_dim = 1536

    existing_indexes = [i.name for i in pc.list_indexes()]
    if index_name not in existing_indexes:
        print(f'Creating index: {index_name}')
        pc.create_index(
            name=index_name,
            dimension=embedding_dim,
            metric='cosine',
            spec=ServerlessSpec(cloud='aws', region='us-east-1')
        )
        print(f" Waiting for '{index_name}' to become active...")
        while True:
            desc = pc.describe_index(index_name)
            if desc.status['ready']:
                print(f"Index '{index_name}' is now ready.")
                try:
                    if dataset:
                        dataset.upload_status = DatasetUpload.UPLOAD_STATUS_INDEX_CREATED
                        dataset.save()
                except Exception:
                    pass
                break
            time.sleep(3)
    else:
        print(f"Index '{index_name}' already exists.")
        try:
            if dataset:
                dataset.upload_status = DatasetUpload.UPLOAD_STATUS_INDEX_CREATED
                dataset.save()
        except Exception:
            pass

    index = pc.Index(index_name)

    enc = get_encoding('cl100k_base')

    def safe_truncate(text, max_tokens=8192):
        tokens = enc.encode(text)
        if len(tokens) > max_tokens:
            print(f' Row truncated ({len(tokens)} → {max_tokens} tokens)')
            tokens = tokens[:max_tokens]
            text = enc.decode(tokens)
        return text

    def get_openai_embedding(text: str):
        text = text.strip()
        if not text:
            return None

        text = safe_truncate(text)
        response = openai.embeddings.create(
            model='text-embedding-3-small',
            input=text
        )
        return response.data[0].embedding

    def embed_and_upload(dataframe, start_idx=0):
        print(f"\nGenerating embeddings & uploading to '{index_name}' row by row...")
        print(f'   Starting from row {start_idx}...')
        total_rows = len(dataframe)
        uploaded_count = 0
        last_reported_percent = 0

        for i, row in dataframe.iterrows():
            text = row.get('Ändamål', '').strip()
            if not text:
                continue

            embedding = get_openai_embedding(text)
            if embedding is None:
                continue

            metadata = row.to_dict()
            index.upsert(
                vectors=[{
                    'id': str(start_idx + i),
                    'values': embedding,
                    'metadata': metadata
                }]
            )
            uploaded_count += 1
            # Update dataset progress every 10% or every 100 rows as a fallback
            percent = int((uploaded_count / total_rows) * 100) if total_rows else 0
            report_now = False
            if percent >= last_reported_percent + 10:
                report_now = True
            if uploaded_count % 100 == 0:
                report_now = True

            if report_now and dataset:
                try:
                    dataset.upload_rows_uploaded = uploaded_count
                    dataset.upload_progress_percent = min(percent, 100)
                    # if we've passed 0% it's partial
                    if percent > 0 and percent < 100:
                        dataset.upload_status = DatasetUpload.UPLOAD_STATUS_PARTIAL
                    dataset.save()
                    last_reported_percent = percent
                except Exception:
                    pass

            if report_now:
                print(f'   ✓ Uploaded {uploaded_count}/{total_rows} rows (ID: {start_idx + i})... Progress: {percent}%')

        print(f'  Batch completed: {uploaded_count} rows uploaded (IDs: {start_idx} → {start_idx + len(dataframe) - 1})')

    chunk1 = df.iloc[:3200]
    chunk2 = df.iloc[3200:6400]

    if len(df) >= 10000:
        chunk3 = df.iloc[6400:]
        print(f"\n Dataset has {len(df)} rows - Processing 3 chunks")
        print(f'   Chunk 1: 0-{len(chunk1)-1} ({len(chunk1)} rows)')
        print(f'   Chunk 2: {len(chunk1)}-{len(chunk1)+len(chunk2)-1} ({len(chunk2)} rows)')
        print(f'   Chunk 3: {len(chunk1)+len(chunk2)}-{len(df)-1} ({len(chunk3)} rows)')
    else:
        chunk3 = None
        print(f"\nDataset has {len(df)} rows - Processing 2 chunks")
        print(f'   Chunk 1: 0-{len(chunk1)-1} ({len(chunk1)} rows)')
        print(f'   Chunk 2: {len(chunk1)}-{len(df)-1} ({len(chunk2)} rows)')

    try:
        print('\nUploading first batch (Chunk 1)...')
        embed_and_upload(chunk1, start_idx=0)

        print('\nUploading second batch (Chunk 2)...')
        embed_and_upload(chunk2, start_idx=3200)

        if chunk3 is not None:
            print('\nUploading third batch (Chunk 3)...')
            embed_and_upload(chunk3, start_idx=6400)
    except Exception as e:
        # Record failure on dataset and re-raise
        try:
            from django.utils import timezone
            from app.models import DatasetUpload
            ds = DatasetUpload.get_active()
            if ds:
                ds.upload_in_progress = False
                ds.upload_status = DatasetUpload.UPLOAD_STATUS_FAILED
                ds.upload_error_message = str(e)
                ds.save()
        except Exception:
            pass
        raise

    print('\nAll embeddings uploaded successfully!')
    print('=' * 60)
    try:
        from django.utils import timezone
        from app.models import DatasetUpload
        dataset = DatasetUpload.get_active()
        if dataset:
            dataset.pinecone_updated = True
            dataset.upload_in_progress = False
            dataset.upload_status = DatasetUpload.UPLOAD_STATUS_COMPLETED
            dataset.upload_progress_percent = 100
            dataset.upload_rows_uploaded = total_rows
            dataset.last_uploaded_at = timezone.now()
            dataset.save()
            print(f"\n✅ SUCCESS: Dataset uploaded to Pinecone index '{index_name}'")
            print('   Pinecone updated flag set to TRUE')
            print('   Dataset completed at', dataset.last_uploaded_at)
            print('   You can now query this index for scholarships')
    except Exception as e:
        print(f'⚠️  Warning: Could not update DatasetUpload status: {e}')
