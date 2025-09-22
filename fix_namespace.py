import re

# Read the file
with open('indexer.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the namespace part
old_pattern = r'vectorstore = Pinecone\.from_existing_index\(\s*index_name=PINECONE_INDEX_NAME,\s*embedding=embeddings,\s*namespace="handbuch-api-mvp"\s*\)'

new_code = '''# Verwende konfigurierbaren Namespace (Standard: leer)
    namespace = os.environ.get("PINECONE_NAMESPACE", "")
    print(f"Verwende Pinecone Namespace: '{namespace}' (leer = Standard)")
    
    vectorstore = Pinecone.from_existing_index(
        index_name=PINECONE_INDEX_NAME,
        embedding=embeddings,
        namespace=namespace
    )'''

content = re.sub(old_pattern, new_code, content, flags=re.MULTILINE | re.DOTALL)

# Write back
with open('indexer.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Namespace fix applied successfully")
