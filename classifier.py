import pandas as pd
from openai import  AzureOpenAI
from json import dumps, loads

def get_abstracts(PATH:str):
    with open(PATH, 'rb') as f:
        return loads(f.read())

def api_key(path:str) -> str:
    with open(path, 'r') as f:
        key = f.read() 
    return key

def get_text(dt:pd.DataFrame, abstracts):
    text = {}
    for guid in list(dt["Guid"]):
        if guid in abstracts: text[guid] = abstracts[guid]
        elif dt[dt["Guid"] == guid]["AbstractInEstonian"].str.len()>20: text[guid] = dt[dt["Guid"] == guid]["AbstractInEstonian"].str
        elif dt[dt["Guid"] == guid]["AbstractInEnglish"].str.len()>20: text[guid] = dt[dt["Guid"] == guid]["AbstractInEnglish"]
        else: text[guid] = dt[dt["Guid"] == guid]["Title"] 
    return text

def ask_frascati( client:AzureOpenAI, guids:dict):
    real_guids = {}
    message = ""

    for n, guid in enumerate(guids.keys()):
        message += f"{n}\t{guids[guid]}\n"
        real_guids[n] = guid

    with open("frascati_system_prompt.txt") as f:
        system_prompt = f.read()

    chat = client.chat.completions.create(
        model = "IDS2025-Gross-gpt-4o-mini",
        temperature= 0.3,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role":"user", "content":message}])
    
    print("Tokens used:",chat.usage.total_tokens)
    responce = {} #guid:classification
    for entry in chat.choices[0].message.content.splitlines():
        fake_id, catg = entry.split(" ")
        responce[real_guids[fake_id]] = catg
    
    return responce, chat.usage.total_tokens


def write_labels(labels:dict):
    #This adds new labels to the file
    with open("labels.json", 'rb') as f:
        old_labels = load(f)
    labels = old_labels+labels 
    with open("labels", 'wb') as f:
        f.write(dumps(labels))


    


def frascati(limit:int, dt:pd.DataFrame, abstracts:dict):
    client = AzureOpenAI(
        api_key=api_key("../api.key"),  
        api_version="2024-12-01-preview",
        azure_endpoint="https://tu-openai-api-management.azure-api.net/oltatkull/openai/deployments/IDS2025-Gross-gpt-4o-mini/chat/completions?api-version=2024-12-01-preview"
    )
    abstracts = get_abstracts("./article_extraction/articles_reduced_clean.jsonl")
    classify = dt[dt["Frascati"].isnull()]
    classify = classify.iloc[:min(limit, classify.shape[0])]
    
    text = get_text(classify, abstracts)
    responce_frascati, tokens = ask_frascati(client, text)
    responce_labels = ask_labels(client, text)

    for guid in responce_frascati.keys():
        dt[guid] = responce_frascati[guid]
    write_labels(responce_labels)
    return dt

def ask_labels( client:AzureOpenAI, guids:dict):
    real_guids = {}
    message = ""

    for n, guid in enumerate(guids.keys()):
        message += f"{n}\t{guids[guid]}\n"
        real_guids[n] = guid

    with open("labels_system_prompt.txt") as f:
        system_prompt = f.read()

    chat = client.chat.completions.create(
        model = "IDS2025-Gross-gpt-4o-mini",
        temperature= 0.2,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role":"user", "content":message}])
    
    print("Tokens used:",chat.usage.total_tokens)
    responce = {} #guid:classification
    for entry in chat.choices[0].message.content.splitlines():
        fake_id, labels = entry.split(" : ")
        responce[real_guids[fake_id]] = labels.split(" ")
    
    return responce, chat.usage.total_tokens

frascati(1000, pd.read_json("./etis.json"), None)