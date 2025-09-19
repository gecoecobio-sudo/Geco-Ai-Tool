# indexer.py (Version 3 - mit korrekter Einrückung)

import os
import pinecone
from datetime import datetime, timezone
from langchain_community.document_loaders import NotionDBLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_pinecone import PineconeVectorStore

# Lädt die API-Schlüssel aus den GitHub Actions Secrets
PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY")
PINECONE_ENVIRONMENT = os.environ.get("PINECONE_ENVIRONMENT")
PINECONE_INDEX_NAME = os.environ.get("PINECONE_INDEX_NAME")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")

# Datei zum Speichern des Zeitstempels
LAST_RUN_FILE = "last_run_timestamp.txt"

def get_last_run_timestamp():
    try:
        with open(LAST_RUN_FILE, "r") as f:
            return datetime.fromisoformat(f.read().strip())
    except FileNotFoundError:
        return datetime(1970, 1, 1, tzinfo=timezone.utc)

def set_last_run_timestamp(start_time):
    with open(LAST_RUN_FILE, "w") as f:
        f.write(start_time.isoformat())

def main():
    start_time = datetime.now(timezone.utc)
    last_run_time = get_last_run_timestamp()
    print(f"Starte Indexer... Letzter Lauf war am: {last_run_time.isoformat()}")

    # 1. Lade Dokumente aus der Notion Datenbank
    loader = NotionDBLoader(
        integration_token=NOTION_TOKEN,
        database_id=NOTION_DATABASE_ID,
        request_filter={"filter": {"timestamp": "last_edited_time", "last_edited_time": {"after": last_run_time.isoformat()}}}
    )
    
    docs_to_update = loader.load()

    if not docs_to_update:
        print("Keine geänderten Dokumente in Notion gefunden. Prozess beendet.")
        return

    print(f"{len(docs_to_update)} geänderte Dokumente gefunden. Werden verarbeitet...")

    # 2. Initialisiere Vektor-Store
    embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004", google_api_key=GOOGLE_API_KEY)
    
    vectorstore = PineconeVectorStore.from_existing_index(
        index_name=PINECONE_INDEX_NAME, 
        embedding=embeddings, 
        namespace="handbuch-api-mvp"
    )

    # 3. Teile Dokumente und füge sie hinzu (Upsert)
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    docs_to_index = text_splitter.split_documents(docs_to_update)
    
    doc_ids_to_upsert = [doc.metadata['id'] for doc in docs_to_update]
    
    # Sicherster Weg: erst alte Chunks löschen, dann neue hinzufügen.
    # Wir fügen die Notion-ID als Metadaten hinzu, um sie gezielt löschen zu können.
    for doc in docs_to_index:
        doc.metadata['notion_id'] = doc.metadata['id']
        
    vectorstore.delete(filter={"notion_id": {"$in": doc_ids_to_upsert}})
    print(f"Alte Vektoren für {len(doc_ids_to_upsert)} Dokumente gelöscht.")
    
    vectorstore.add_documents(docs_to_index)
    print(f"{len(docs_to_index)} neue Vektor-Abschnitte hinzugefügt.")
    
    # 4. Zeitstempel aktualisieren, wenn alles erfolgreich war
    set_last_run_timestamp(start_time)
    print(f"Index erfolgreich aktualisiert. Neuer Zeitstempel: {start_time.isoformat()}")

if __name__ == "__main__":
    main()
