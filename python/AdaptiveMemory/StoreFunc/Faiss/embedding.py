import requests 
import json
from Settings.config import api_key,embedding_url

def getEmbedding(text, model="text-embedding-3-large", encoding_format="float"):

    authorization = "Bearer " + api_key

    headers = { 
    "Content-Type": "application/json", 
    "Authorization": authorization
    } 

    data = {
        "model": model,
        "input": text,
        "encoding_format": encoding_format,
    }
    response = requests.post(
        embedding_url,
        headers=headers,
        data=json.dumps(data),
        timeout=60,
    )
    response.raise_for_status()
    res = response.json()
    return res['data'][0]['embedding']

def getEmbeddingsList(text_list, model="text-embedding-3-large", encoding_format="float"):
    authorization = "Bearer " + api_key
    headers = {
        "Content-Type": "application/json",
        "Authorization": authorization
    }

    data = {
        "model": model,
        "input": text_list,
        "encoding_format": encoding_format,
    }

    response = requests.post(
        embedding_url,
        headers=headers,
        data=json.dumps(data),
        timeout=60,
    )
    response.raise_for_status()
    res = response.json()
    embedding_list = []
    for item in res["data"]:
        embedding_list.append(item["embedding"])

    return embedding_list
