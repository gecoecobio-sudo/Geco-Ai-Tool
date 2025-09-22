# indexer.py (Version 12 - Fixed Service Account Support)

import os
import json
from datetime import datetime, timezone
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from langchain_core.documents import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_pinecone.vectorstores import Pinecone

# --- API-Schlüssel laden ---
PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY")
PINECONE_ENVIRONMENT = os.environ.get("PINECONE_ENVIRONMENT")
PINECONE_INDEX_NAME = os.environ.get("PINECONE_INDEX_NAME")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
GOOGLE_DOCS_ID = os.environ.get("GOOGLE_DOCS_ID", "1j8eZoc7xKfatazq6vAFOODXMNPbxIIgmVi_8UnZderY")

# Google Docs API Scopes
SCOPES = ["https://www.googleapis.com/auth/documents.readonly"]

# --- Zeitstempel-Funktionen ---
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

# --- Google Docs Authentication ---
def get_google_docs_service():
    """Authentifiziert und gibt den Google Docs Service zurück."""
    creds = None

    # 1. Versuche Service Account (für GitHub Actions)
    service_account_info = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if service_account_info:
        try:
            service_account_data = json.loads(service_account_info)
            creds = ServiceAccountCredentials.from_service_account_info(
                service_account_data, scopes=SCOPES
            )
            print("Service Account Authentication erfolgreich.")
        except Exception as e:
            print(f"Service Account Authentication fehlgeschlagen: {e}")

    # 2. Fallback zu OAuth (für lokale Entwicklung)
    if not creds:
        print("Service Account nicht verfügbar, versuche OAuth...")

        # Prüfe vorhandene OAuth Credentials
        if os.path.exists("token.json"):
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)

        # OAuth Credential Refresh oder neue Autorisierung
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                print("OAuth Token erfolgreich erneuert.")
            else:
                # Nur OAuth versuchen wenn credentials.json existiert
                if os.path.exists("credentials.json"):
                    print("Starte OAuth Flow...")
                    flow = InstalledAppFlow.from_client_secrets_file(
                        "credentials.json", SCOPES
                    )
                    creds = flow.run_local_server(port=0)

                    # Credentials für zukünftige Nutzung speichern
                    with open("token.json", "w") as token:
                        token.write(creds.to_json())
                    print("OAuth Authentication erfolgreich.")
                else:
                    print("Fehler: Keine Authentifizierung möglich.")
                    print("Für lokale Entwicklung: credentials.json bereitstellen")
                    print("Für GitHub Actions: GOOGLE_SERVICE_ACCOUNT_JSON Secret setzen")
                    return None

    try:
        service = build("docs", "v1", credentials=creds)
        return service
    except HttpError as err:
        print(f"Fehler beim Erstellen des Google Docs Service: {err}")
        return None

# --- Google Docs Lade-Funktionen ---
def add_current_and_child_tabs(tab, all_tabs):
    """Rekursiv fügt Tabs und ihre Kind-Tabs zu einer Liste hinzu."""
    all_tabs.append(tab)
    for child_tab in tab.get('childTabs', []):
        add_current_and_child_tabs(child_tab, all_tabs)

def get_all_tabs(doc):
    """Gibt eine flache Liste aller Tabs im Dokument zurück."""
    all_tabs = []
    for tab in doc.get('tabs', []):
        add_current_and_child_tabs(tab, all_tabs)
    return all_tabs

def read_paragraph_element(element):
    """Extrahiert Text aus einem Paragraph-Element."""
    text_run = element.get('textRun')
    return text_run.get('content', '') if text_run else ''

def read_structural_elements(elements):
    """Rekursiv extrahiert Text aus strukturellen Elementen."""
    text = ''
    for value in elements:
        if 'paragraph' in value:
            paragraph_elements = value.get('paragraph', {}).get('elements', [])
            text += ''.join(read_paragraph_element(elem) for elem in paragraph_elements)
        elif 'table' in value:
            # Tabellen-Inhalt extrahieren
            table = value.get('table', {})
            for row in table.get('tableRows', []):
                for cell in row.get('tableCells', []):
                    cell_content = cell.get('content', [])
                    text += read_structural_elements(cell_content)
        elif 'sectionBreak' in value:
            text += '\n--- Abschnittsumbruch ---\n'
        elif 'tableOfContents' in value:
            text += '\n--- Inhaltsverzeichnis ---\n'
    return text

def get_google_docs_content(service, document_id):
    """Lädt den kompletten Inhalt eines Google Docs Dokuments inklusive aller Tabs."""
    try:
        document = service.documents().get(documentId=document_id).execute()
        doc_title = document.get('title', 'Unbenanntes Dokument')

        # Alle Tabs des Dokuments abrufen
        all_tabs = get_all_tabs(document)

        # Dokumente für jede Tab erstellen
        tab_documents = []

        for i, tab in enumerate(all_tabs):
            tab_title = tab.get('tabProperties', {}).get('title', f'Tab {i+1}')

            # DocumentTab für den Hauptinhalt
            document_tab = tab.get('documentTab', {})
            body = document_tab.get('body', {})
            content = body.get('content', [])

            # Text aus dem Tab extrahieren
            tab_text = read_structural_elements(content)

            if tab_text.strip():  # Nur Tabs mit Inhalt hinzufügen
                metadata = {
                    "document_id": document_id,
                    "document_title": doc_title,
                    "tab_title": tab_title,
                    "tab_index": i,
                    "last_modified": datetime.now(timezone.utc).isoformat()
                }

                tab_documents.append(Document(
                    page_content=tab_text,
                    metadata=metadata
                ))

        return tab_documents

    except HttpError as err:
        print(f"Fehler beim Laden des Google Docs: {err}")
        return []

# --- Hauptfunktion ---
def main():
    start_time = datetime.now(timezone.utc)
    last_run_time = get_last_run_timestamp()
    print(f"Starte Google Docs Indexer... Suche nach Änderungen seit: {last_run_time.isoformat()}")

    # 1. Google Docs Service initialisieren
    service = get_google_docs_service()
    if not service:
        print("Fehler: Konnte Google Docs Service nicht initialisieren.")
        return

    print(f"Schritt 1: Google Docs Service erfolgreich initialisiert.")

    # 2. Dokument-Inhalt laden
    docs_to_update = get_google_docs_content(service, GOOGLE_DOCS_ID)

    if not docs_to_update:
        print("Schritt 2: Keine Dokumente gefunden. Prozess wird beendet.")
        set_last_run_timestamp(start_time)
        return

    print(f"Schritt 2: {len(docs_to_update)} Tabs aus Google Docs geladen.")

    # 3. Embeddings und Vectorstore initialisieren
    embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004", google_api_key=GOOGLE_API_KEY)
    vectorstore = Pinecone.from_existing_index(
        index_name=PINECONE_INDEX_NAME,
        embedding=embeddings,
        namespace="handbuch-api-mvp"
    )

    print("Schritt 3: Teile Dokumente in Abschnitte...")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    docs_to_index = text_splitter.split_documents(docs_to_update)

    # Metadaten für die Indizierung vorbereiten
    for doc in docs_to_index:
        doc.metadata['google_docs_id'] = doc.metadata['document_id']

    print(f"Schritt 4: Lösche alte Vektoren für Google Docs ID: {GOOGLE_DOCS_ID}...")
    vectorstore.delete(filter={"google_docs_id": GOOGLE_DOCS_ID})

    print(f"Schritt 5: Füge {len(docs_to_index)} neue Vektor-Abschnitte hinzu...")
    vectorstore.add_documents(docs_to_index)

    set_last_run_timestamp(start_time)
    print(f"Google Docs Index erfolgreich aktualisiert. Neuer Zeitstempel: {start_time.isoformat()}")

if __name__ == "__main__":
    main()