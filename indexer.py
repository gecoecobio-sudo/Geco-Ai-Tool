# indexer.py (Version 7 - Robuste Lade-Logik)

import os
from datetime import datetime, timezone
import notion_client
from langchain_core.documents import Document
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
        print("Timestamp-Datei nicht gefunden, beginne bei Null.")
        return datetime(1970, 1, 1, tzinfo=timezone.utc)

def set_last_run_timestamp(start_time):
    with open(LAST_RUN_FILE, "w") as f:
        f.write(start_time.isoformat())

# --- NEUE, ROBUSTE NOTION LADE-FUNKTIONEN ---

def get_all_pages_from_notion_db(client, database_id):
    """Holt alle Seiten (nur Metadaten) aus einer Notion-Datenbank."""
    page_summaries = []
    has_more = True
    start_cursor = None
    while has_more:
        response = client.databases.query(
            database_id=database_id,
            start_cursor=start_cursor,
            page_size=100,
        )
        page_summaries.extend(response["results"])
        has_more = response["has_more"]
        start_cursor = response["next_cursor"]
    return page_summaries

def read_block(client, block_id):
    """Liest den Textinhalt eines Blocks und seiner Kinder rekursiv."""
    response = client.blocks.children.list(block_id=block_id)
    text = ""
    for block in response["results"]:
        if "type" in block:
            block_type = block["type"]
            if block_type in ("paragraph", "heading_1", "heading_2", "heading_3", "bulleted_list_item", "numbered_list_item"):
                # Extrahiere Text aus Rich-Text-Arrays
                rich_text = block[block_type].get("rich_text", [])
                for text_part in rich_text:
                    if text_part.get("type") == "text":
                        text += text_part["plain_text"] + "\n"
    return text

# --- Hauptfunktion (MIT NEUER LADE-LOGIK) ---
def main():
    start_time = datetime.now(timezone.utc)
    last_run_time = get_last_run_timestamp()
    print(f"Starte Indexer... Suche nach Änderungen seit: {last_run_time.isoformat()}")

    # 1. Lade Dokumente mit dem offiziellen Notion-Client
    client = notion_client.Client(auth=NOTION_TOKEN)
    page_summaries = get_all_pages_from_notion_db(client, NOTION_DATABASE_ID)

    print(f"Schritt 1: Insgesamt {len(page_summaries)} Seiten-Zusammenfassungen aus Notion geladen.")
    
    # 2. Filtere Seiten manuell und lade den vollständigen Inhalt
    docs_to_update = []
    for page in page_summaries:
        last_edited_str = page.get('last_edited_time', '')
        if last_edited_str:
            last_edited_dt = datetime.fromisoformat(last_edited_str.replace('Z', '+00:00'))
            if last_edited_dt > last_run_time:
                page_id = page['id']
                page_content = read_block(client, page_id)
                page_title = page['properties']['Name']['title'][0]['plain_text'] # Annahme: Titel-Spalte heißt 'Name'
                
                metadata = {
                    "id": page_id,
                    "title": page_title,
                    "last_edited_time": last_edited_str
                }
                docs_to_update.append(Document(page_content=page_content, metadata=metadata))

    if not docs_to_update:
        print("Schritt 2: Keine Dokumente gefunden, die nach dem letzten Lauf geändert wurden. Prozess wird beendet.")
        set_last_run_timestamp(start_time)
        return

    print(f"Schritt 2: {len(docs_to_update)} geänderte Dokumente gefunden. Werden verarbeitet...")

    # ... (Rest des Skripts ist identisch) ...
    # 3. Initialisiere Komponenten
    embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004", google_api_key=GOOGLE_API_KEY)
    vectorstore = Pinecone.from_existing_index(
        index_name=PINECONE_INDEX_NAME, 
        embedding=embeddings, 
        namespace="handbuch-api-mvp"
    )

    # 4. Verarbeite und aktualisiere den Index
    print("Schritt 3: Teile Dokumente in Abschnitte...")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    docs_to_index = text_splitter.split_documents(docs_to_update)
    
    doc_ids_to_upsert = list(set(doc.metadata['id'] for doc in docs_to_update))
    
    for doc in docs_to_index:
        doc.metadata['notion_id'] = doc.metadata['id']
        
    print(f"Schritt 4: Lösche alte Vektoren für {len(doc_ids_to_upsert)} Dokument(e)...")
    vectorstore.delete(filter={"notion_id": {"$in": doc_ids_to_upsert}})
    
    print(f"Schritt 5: Füge {len(docs_to_index)} neue Vektor-Abschnitte hinzu...")
    vectorstore.add_documents(docs_to_index)
    
    # 5. Zeitstempel aktualisieren
    set_last_run_timestamp(start_time)
    print(f"Index erfolgreich aktualisiert. Neuer Zeitstempel: {start_time.isoformat()}")

if __name__ == "__main__":
    main()
