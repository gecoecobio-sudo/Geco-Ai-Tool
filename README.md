# Geco AI Tool - Google Docs Integration

Ein KI-gestütztes RAG-System, das Google Docs Dokumente als Wissensbasis nutzt.

## Setup

### 1. Google Cloud Console Setup

1. Gehe zu [Google Cloud Console](https://console.cloud.google.com/)
2. Erstelle ein neues Projekt oder wähle ein bestehendes aus
3. Aktiviere die Google Docs API:
   - Gehe zu "APIs & Services" > "Library"
   - Suche nach "Google Docs API"
   - Klicke auf "Enable"

### 2. OAuth 2.0 Credentials erstellen

1. Gehe zu "APIs & Services" > "Credentials"
2. Klicke auf "Create Credentials" > "OAuth 2.0 Client IDs"
3. Wähle "Desktop application" als Application type
4. Gib einen Namen ein (z.B. "Geco AI Tool")
5. Lade die JSON-Datei herunter
6. Benenne sie um zu `credentials.json` und platziere sie im Projektverzeichnis

### 3. Umgebungsvariablen

Erstelle eine `.env` Datei oder setze folgende Umgebungsvariablen:

```bash
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_ENVIRONMENT=your_pinecone_environment
PINECONE_INDEX_NAME=your_pinecone_index_name
GOOGLE_API_KEY=your_google_api_key
GOOGLE_DOCS_ID=1j8eZoc7xKfatazq6vAFOODXMNPbxIIgmVi_8UnZderY
```

### 4. Installation

```bash
pip install -r requirements.txt
```

### 5. Erste Ausführung

1. Indexer ausführen:
```bash
python indexer.py
```

Bei der ersten Ausführung öffnet sich ein Browser-Fenster für die Google OAuth-Authentifizierung.

2. Streamlit App starten:
```bash
streamlit run app.py
```

## Funktionsweise

### Indexer (indexer.py)
- Lädt alle Tabs des konfigurierten Google Docs Dokuments
- Teilt den Inhalt in Chunks auf
- Erstellt Embeddings mit Google's text-embedding-004 Modell
- Speichert die Vektoren in Pinecone

### Chat Interface (app.py)
- Streamlit-basierte Benutzeroberfläche
- RAG-Pipeline mit Gemini 1.5 Pro
- Durchsucht die indexierten Dokumente basierend auf Nutzeranfragen

## Google Docs Dokument Format

Das System liest alle Tabs des konfigurierten Google Docs Dokuments:
- Jeder Tab wird als separates Dokument behandelt
- Unterstützt Paragraph, Überschriften, Listen, Tabellen
- Automatische Extraktion von Metadaten (Tab-Titel, Dokument-Titel)

## Troubleshooting

### "credentials.json not found"
- Stelle sicher, dass die credentials.json Datei im Projektverzeichnis liegt
- Verwende die credentials.json.template als Vorlage

### "Access denied" oder OAuth Errors
- Überprüfe, ob die Google Docs API aktiviert ist
- Stelle sicher, dass die OAuth-Credentials korrekt konfiguriert sind
- Lösche token.json und authentifiziere dich erneut

### "Document not found"
- Überprüfe die GOOGLE_DOCS_ID Umgebungsvariable
- Stelle sicher, dass das Dokument öffentlich zugänglich ist oder du Zugriff darauf hast