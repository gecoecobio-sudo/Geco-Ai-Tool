import streamlit as st
from langchain_google_genai import GoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain.prompts import PromptTemplate
from langchain.schema.runnable import RunnablePassthrough
from langchain.schema.output_parser import StrOutputParser

# --- Konfiguration ---
st.set_page_config(page_title="Franchise KI-Assistent", layout="wide")
st.title("🤖 Franchise Handbuch KI-Assistent")

# API-Schlüssel aus Streamlit Secrets laden (unverändert)
PINECONE_INDEX_NAME = st.secrets.get("PINECONE_INDEX_NAME")
GOOGLE_API_KEY = st.secrets.get("GOOGLE_API_KEY")

# --- RAG Kette initialisieren ---
@st.cache_resource
def get_rag_chain():
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-004", google_api_key=GOOGLE_API_KEY)
    # Wichtig: Nutze denselben Namespace wie der Indexer
    vectorstore = PineconeVectorStore.from_existing_index(
        index_name=PINECONE_INDEX_NAME, 
        embedding=embeddings, 
        namespace="handbuch-api-mvp"
    )
    retriever = vectorstore.as_retriever()
    
    llm = GoogleGenerativeAI(model="gemini-1.5-pro-latest", google_api_key=GOOGLE_API_KEY)
    
    template = """Du bist ein hilfreicher KI-Assistent für Franchisenehmer. Deine Kernbotschaft ist immer "Keine Panik, das ist schaffbar." 
    Antworte auf die Frage des Nutzers ausschließlich basierend auf dem folgenden Kontext aus dem offiziellen Handbuch.
    Wenn die Antwort nicht im Kontext enthalten ist, sage, dass du die Antwort im Handbuch nicht finden konntest. Sei immer freundlich und ermutigend.

    Kontext:
    {context}

    Frage:
    {question}

    Hilfreiche Antwort:
    """
    prompt = PromptTemplate.from_template(template)
    
    rag_chain = (
        {"context": retriever, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    return rag_chain

rag_chain = get_rag_chain()

# --- Chat-Interface (unverändert) ---
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hallo! Wie kann ich dir heute mit dem Handbuch helfen?"}]

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Stellen Sie hier Ihre Frage zum Handbuch"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Ich durchsuche das Handbuch..."):
            response = rag_chain.invoke(prompt)
            st.markdown(response)
    st.session_state.messages.append({"role": "assistant", "content": response})
