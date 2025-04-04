# -*- coding: utf-8 -*-
"""BIO-RAG

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1wfIrk8lea2FroYM-H7czkPC14B8uSNHa
"""

!pip install biopython wikipedia-api unstructured serpapi requests transformers torch scikit-learn faiss-cpu
!pip install google-search-results --upgrade

!pip install nltk
!pip install --upgrade nltk

import nltk
nltk.download('punkt')

import os
from Bio import Entrez
import wikipediaapi
from serpapi import GoogleSearch
import requests
from unstructured.partition.text import partition_text
from transformers import AutoTokenizer, AutoModel, AutoModelForSequenceClassification
import torch
from sklearn.cluster import AgglomerativeClustering
import faiss  # For efficient vector retrieval

# Set up your API keys
os.environ['SERPAPI_API_KEY'] = '2cb59bcf7aa19d173738e7017edf03135fe6dc90f4f9da992442192817f4f350 '
os.environ['TAVILY_API_KEY'] = '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'

def get_pubmed_data(query, max_results=10):
    Entrez.email = "udayasri142003@gmail.com"  # Replace with your email
    handle = Entrez.esearch(db="pubmed", term=query, retmax=max_results)
    record = Entrez.read(handle)
    handle.close()

    ids = record["IdList"]
    handle = Entrez.efetch(db="pubmed", id=ids, rettype="abstract", retmode="text")
    abstracts = handle.read()
    handle.close()

    return abstracts

def get_wikipedia_data(query):
    # Specify the user-agent explicitly in the constructor
    wiki = wikipediaapi.Wikipedia(
        language='en',
        user_agent='BiomedicalResearchTool/1.0 (udayasri142003@gmail.com)'
    )

    # Get the page for the given query
    page = wiki.page(query)

    # Return the text if the page exists
    return page.text if page.exists() else ""

def get_serpapi_data(query):
    params = {
        "engine": "google",
        "q": query,
        "api_key": os.environ['SERPAPI_API_KEY']
    }
    search = GoogleSearch(params)
    results = search.get_dict()

    organic_results = results.get('organic_results', [])
    snippets = [result.get('snippet', '') for result in organic_results]
    return " ".join(snippets)

def get_tavily_data(query):
    api_key = os.environ['TAVILY_API_KEY']

    # Define the endpoint and headers for TAVILY API
    headers = {
        'Authorization': f'Bearer {api_key}',  # Assuming Bearer token for authentication
        'Content-Type': 'application/json'
    }

    # Define the parameters for the query
    params = {
        'query': query,
        'limit': 10  # Adjust limit as per your requirement
    }

    # Make the API request to TAVILY
    response = requests.get('https://api.tavily.com/v1/search', headers=headers, params=params)

    # Check if the response is valid
    if response.status_code == 200:
        results = response.json()
        snippets = [result['snippet'] for result in results.get('items', [])]
        return " ".join(snippets)
    else:
        return f"Error: {response.status_code} - {response.text}"

query = "How does the deficiency of the enzyme alpha-galactosidase A lead to the accumulation of Gb3 in cells, causing Fabry disease??"

pubmed_data = get_pubmed_data(query)
wikipedia_data = get_wikipedia_data(query)
serpapi_data = get_serpapi_data(query)
tavily_data = get_tavily_data(query)

# Combine the data into one text block
combined_data = f"{pubmed_data}\n\n{wikipedia_data}\n\n{serpapi_data}\n\n{tavily_data}"

import os
import nltk

# Specify a directory to download NLTK data
nltk_data_dir = '/custom/nltk_data'
os.makedirs(nltk_data_dir, exist_ok=True)

# Set NLTK data path and download the tokenizer
nltk.data.path.append(nltk_data_dir)
nltk.download('punkt', download_dir=nltk_data_dir)

from unstructured.partition.text import partition_text

chunks = partition_text(
    text=combined_data,
    max_characters=1000,  # Adjust as needed
    overlap=100,  # Adjust as needed
)

# Print the chunks
for i, chunk in enumerate(chunks, 1):
    print(f"Chunk {i}:")
    print(chunk.text)
    print("-" * 50)

import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

# Load the pre-trained PubMedBERT model for MeSH prediction
mesh_tokenizer = AutoTokenizer.from_pretrained('microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext')
mesh_model = AutoModelForSequenceClassification.from_pretrained('microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext')

# Load MeSH term mapping (you would need to create this)
mesh_id_to_term = {
    0: "Cardiovascular Diseases",
    1: "Neoplasms",
    2: "Nervous System Diseases",
    # ... add more mappings as needed
}

def predict_mesh_terms(text, top_k=5):
    # Tokenize the input text
    inputs = mesh_tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512)

    # Get model predictions
    with torch.no_grad():
        outputs = mesh_model(**inputs)

    # Get probabilities using softmax
    probabilities = torch.nn.functional.softmax(outputs.logits, dim=-1)

    # Get the number of classes the model predicts
    num_classes = probabilities.shape[1]

    # Adjust top_k if it's larger than the number of classes
    top_k = min(top_k, num_classes)

    # Get top k predictions
    top_probs, top_indices = torch.topk(probabilities, k=top_k)

    # Decode predictions to MeSH terms
    predicted_mesh_terms = []
    for prob, idx in zip(top_probs[0], top_indices[0]):
        mesh_term = mesh_id_to_term.get(idx.item(), f"Unknown MeSH term (ID: {idx.item()})")
        predicted_mesh_terms.append((mesh_term, prob.item()))

    return predicted_mesh_terms

# Example usage
text = "what are light and heavy backbones"
try:
    mesh_predictions = predict_mesh_terms(text)
    for term, prob in mesh_predictions:
        print(f"{term}: {prob:.4f}")
except Exception as e:
    print(f"An error occurred: {str(e)}")
    print("Model output shape:", outputs.logits.shape)
    print("Number of classes:", outputs.logits.shape[1])

import pandas as pd

# Simulate MeSH indexing
data = pd.DataFrame({'text': [chunk.text for chunk in chunks]})
data['MeSH'] = data['text'].apply(lambda x: predict_mesh_terms(x))

# Example of constructing an SQL query for filtering
def construct_mesh_sql(mesh_terms):
    sql_query = f"SELECT * FROM knowledge_base WHERE MeSH IN ({', '.join(map(str, mesh_terms))})"
    return sql_query

sql_query = construct_mesh_sql(data['MeSH'][0])
print(f"Constructed SQL Query: {sql_query}")

# Load PubMedBERT and CLIP models
pubmedbert_tokenizer = AutoTokenizer.from_pretrained('microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext')
pubmedbert_model = AutoModel.from_pretrained('microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext')

# Function to get embeddings
def get_biomedical_embeddings(text):
    inputs = pubmedbert_tokenizer(text, return_tensors="pt", padding=True, truncation=True)
    embeddings = pubmedbert_model(**inputs).last_hidden_state.mean(dim=1)
    return embeddings

# Generate embeddings for each chunk
data['MEMB_embeddings'] = data['text'].apply(lambda x: get_biomedical_embeddings(x))

# Build FAISS index for vector retrieval
dimension = data['MEMB_embeddings'][0].shape[1]
index = faiss.IndexFlatL2(dimension)

# Ensure faiss_embeddings is a 2D array
faiss_embeddings = torch.cat(data['MEMB_embeddings'].tolist(), dim=0).detach().numpy()  # Concatenate embeddings to create a 2D array

index.add(faiss_embeddings)

# Determine the number of clusters based on the number of samples
n_samples = faiss_embeddings.shape[0]
n_clusters = min(5, n_samples)  # Use 5 clusters, or fewer if there are less than 5 samples

# Hierarchical clustering based on embeddings
clustering_model = AgglomerativeClustering(n_clusters=n_clusters)
data['cluster'] = clustering_model.fit_predict(faiss_embeddings)

# Build hierarchy
hierarchy = data.groupby('cluster')['text'].apply(list).to_dict()
knowledge_base = {
    'documents': data,
    'index': index,
    'hierarchy': hierarchy
}

def retrieve_information(query):
    #query = query_preprocessing(query)
    query_embedding = get_biomedical_embeddings(query)

    # Apply MeSH filtering
    mesh_terms = predict_mesh_terms(query)
    sql_query = construct_mesh_sql(mesh_terms)

    # FAISS vector retrieval
    D, I = knowledge_base['index'].search(query_embedding.detach().numpy(), k=5) # Call detach() before converting to a NumPy array.
    retrieved_data = knowledge_base['documents'].iloc[I[0]]['text']

    return retrieved_data

# Example retrieval
retrieved_information = retrieve_information(query)
print(retrieved_information)

def self_evaluation(retrieved_data):
    if len(retrieved_data) < 3:
        print("Insufficient data retrieved. Refine query or search externally.")
    return True

def generate_answer(retrieved_data):
    answer = " ".join(retrieved_data)
    return answer

# Process the query
if self_evaluation(retrieved_information):
    final_answer = generate_answer(retrieved_information)
    print(f"Answer: {final_answer}")