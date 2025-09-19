# indexer.py (Version 5 - Finale Korrektur)

import os
from datetime import datetime, timezone
from langchain_community.document_loaders import NotionDBLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_pinecone.vectorstores import Pinecone

# --- API-Schlüssel laden (unverändert) ---
PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY")
PINECONE_ENVIRONMENT = os.environ.get("PINECONE_ENVIRONMENT")
PINECONE_INDEX_NAME = os.environ.get("PINECONE_INDEX_NAME")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")

# --- Zeitstempel-Funktionen (unverändert) ---
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

# --- Hauptfunktion (KORRIGIERT) ---
def main():
    """Führt den intelligenten Indexierungs-Prozess aus."""
    start_time = datetime.now(timezone.utc)
    last_run_time = get_last_run_timestamp()
    print(f"Starte Indexer... Letzter Lauf war am: {last_run_time.isoformat()}")

    # 1. Lade ALLE Dokumente aus der Notion Datenbank
    # Der Parameter 'request_filter' wurde entfernt, da er nicht mehr unterstützt wird.
    loader = NotionDBLoader(
        integration_token=NOTION_TOKEN,
        database_id=NOTION_DATABASE_ID,
    )
    
    all_docs_from_notion = loader.load()

    # 2. Filtere die Dokumente manuell basierend auf dem 'last_edited_time'
    docs_to_update = []
    for doc in all_docs_from_notion:
        # Konvertiere den Zeitstempel-String aus den Metadaten in ein datetime-Objekt
        last_edited_str = doc.metadata.get('last_edited_time', '')
        # Stelle sicher, dass der String nicht leer ist
        if last_edited_str:
            # Schneide mögliche Millisekunden und das 'Z' ab für sauberes Parsen
            last_edited_dt = datetime.fromisoformat(last_edited_str.split('.')[0]).replace(tzinfo=timezone.utc)
            if last_edited_dt > last_run_time:
                docs_to_update.append(doc)

    if not docs_to_update:
        print("Keine geänderten Dokumente in Notion gefunden. Prozess beendet.")
        # Wir aktualisieren den Zeitstempel trotzdem, um den "last checked" Zeitpunkt festzuhalten
        set_last_run_timestamp(start_time)
        return

    print(f"{len(docs_to_update)} geänderte Dokumente gefunden. Werden verarbeitet...")

    # 3. Initialisiere die nötigen Komponenten
    embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004", google_api_key=GOOGLE_API_KEY)
    
    vectorstore = Pinecone.from_existing_index(
        index_name=PINECONE_INDEX_NAME, 
        embedding=embeddings, 
        namespace="handbuch-api-mvp"
    )

    # 4. Teile Dokumente in Abschnitte und aktualisiere den Index
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    docs_to_index = text_splitter.split_documents(docs_to_update)
    
    doc_ids_to_upsert = list(set(doc.metadata['id'] for doc in docs_to_update))
    
    for doc in docs_to_index:
        doc.metadata['notion_id'] = doc.metadata['id']
        
    vectorstore.delete(filter={"notion_id": {"$in": doc_ids_to_upsert}})
    print(f"Alte Vektoren für {len(doc_ids_to_upsert)} Dokumente gelöscht.")
    
    vectorstore.add_documents(docs_to_index)
    print(f"{len(docs_to_index)} neue Vektor-Abschnitte hinzugefügt.")
    
    # 5. Zeitstempel aktualisieren, wenn alles erfolgreich war
    set_last_run_timestamp(start_time)
    print(f"Index erfolgreich aktualisiert. Neuer Zeitstempel: {start_time.isoformat()}")

if __name__ == "__main__":
    main()
