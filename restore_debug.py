import re

# Read the current file
with open('indexer.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the get_google_docs_content function with debug version
old_function = '''def get_google_docs_content(service, document_id):
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
        return []'''

new_function = '''def get_google_docs_content(service, document_id):
    """Lädt den kompletten Inhalt eines Google Docs Dokuments inklusive aller Tabs."""
    try:
        print(f"Lade Dokument mit ID: {document_id}")
        document = service.documents().get(documentId=document_id).execute()
        doc_title = document.get('title', 'Unbenanntes Dokument')
        print(f"Dokument geladen: '{doc_title}'")

        # Debug: Zeige Dokumentstruktur
        print(f"Dokument Keys: {list(document.keys())}")

        # Prüfe ob Tabs existieren
        if 'tabs' in document:
            print(f"Tabs gefunden: {len(document['tabs'])}")
            all_tabs = get_all_tabs(document)
        else:
            print("Keine Tabs gefunden, verwende body direkt")
            # Fallback: Verwende body direkt wenn keine Tabs
            body = document.get('body', {})
            all_tabs = [{'documentTab': {'body': body}, 'tabProperties': {'title': 'Hauptdokument'}}]

        print(f"Anzahl zu verarbeitende Tabs: {len(all_tabs)}")

        # Dokumente für jede Tab erstellen
        tab_documents = []

        for i, tab in enumerate(all_tabs):
            tab_title = tab.get('tabProperties', {}).get('title', f'Tab {i+1}')
            print(f"Verarbeite Tab {i+1}: '{tab_title}'")

            # DocumentTab für den Hauptinhalt
            document_tab = tab.get('documentTab', {})
            body = document_tab.get('body', {})
            content = body.get('content', [])

            print(f"Tab {i+1} hat {len(content)} Inhaltselemente")

            # Text aus dem Tab extrahieren
            tab_text = read_structural_elements(content)
            text_length = len(tab_text.strip())
            print(f"Tab {i+1} extrahierter Text: {text_length} Zeichen")

            if text_length > 0:  # Nur Tabs mit Inhalt hinzufügen
                print(f"Tab {i+1} wird hinzugefügt (erste 100 Zeichen): {tab_text[:100]}")
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
            else:
                print(f"Tab {i+1} übersprungen (kein Text)")

        print(f"Gesamt: {len(tab_documents)} Dokumente mit Inhalt erstellt")
        return tab_documents

    except HttpError as err:
        print(f"Fehler beim Laden des Google Docs: {err}")
        return []'''

# Replace in content
content = content.replace(old_function, new_function)

# Write back
with open('indexer.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Debug function restored successfully")
