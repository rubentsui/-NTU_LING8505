#!/usr/bin/env python
# coding: utf-8
#
# Author:
#   Ruben G. Tsui
#   rubentsui@gmail.com
#
# Last updaded on 2025-12-25:
# This Python script
# (1) uploads a Defense Digest (《國防譯粹》) issue in PDF format to Google Gemini LLM via its API;
# (2) prompts the LLM to extract:
#     (a) unbroken Chinese passages from the magazine's articles; and
#     (b) metadata of each article about its English source article
#     in JSON format
# (3) uses the metadata obtained above to search for 5 candidates of English source articles for each Chinese article in the magazine
# (4) compares each Chinese with each of its English source candidates semantically via an 8k-token context multilingual embeddings model and identify the one with the highest cosine similarity
# (5) populates the JSON file with English candidates' passages
# (6) creates a sentence-aligned parallel corpus (in both plain text and Excel .xlsx formats)
#
# Note: This script has been hand-coded (not vibe-coded)

# General-purpose libraries
import os
from copy import deepcopy
import json
import ujson
from pathlib import Path
import time
import regex as re
from random import random

# Web scraping libraries
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select

# Google GenAI API to access LLMs
from google import genai
from google.genai.types import HarmCategory, HarmBlockThreshold
from google.genai import types

import cloudscraper

# DuckDuckGo Search API
from ddgs import DDGS

#%%
# Set your project's root folder here
if os.name == 'posix': # Linux and macOS
    working_folder = "/Users/rubentsui/NLP/RAGMT"
elif os.name == 'nt': # Windows
    working_folder = "D:/Corpora/RAGMT"

#%%
# Start up a Chrome browser for web scraping
# - You'll need Selenium Chromedriver; get latest version from:
# https://googlechromelabs.github.io/chrome-for-testing/

options = webdriver.ChromeOptions()
options.add_argument("--disable-blink-features")
options.add_argument("--disable-blink-features=AutomationControlled")

options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option('useAutomationExtension', False)

driver = webdriver.Chrome(options=options)

#%%
# Load the 8k-token-context Sentence Transformer embeddings model for comparing entire articles
from sentence_transformers import SentenceTransformer
embedding_model_path = "Alibaba-NLP/gte-multilingual-base"
embedding_model = SentenceTransformer(embedding_model_path, trust_remote_code=True)
print('='*20)
print(f"*** Using {embedding_model_path} for document embedding...")

def cossim(s, t):
    """
    Find the cosine similarity between strings s and t
    """
    return float(embedding_model.similarity(embedding_model.encode(s), embedding_model.encode(t)))

#%%

# List all available Google LLMs 
GOOGLE_AI_STUDIO = 'Your Gemini API key'
llm_client = genai.Client(api_key=GOOGLE_AI_STUDIO)
for idx, m in enumerate(llm_client.models.list()):
    print(idx, m.name, '\t\t', m.input_token_limit,  '\t\t', m.output_token_limit, '\t\t', m.supported_actions)

#%%
# This is the LLM we'll be using to extract text from PDF
llm_model_name = 'gemini-3-flash-preview'

# Set up Temperature abd Safety Setting parameters
generate_content_config = types.GenerateContentConfig(
    temperature=0.1,
    top_p=1,
    top_k=1,
    max_output_tokens=1024*64,
    #response_mime_type="text/plain",
    response_mime_type="application/json",
    safety_settings=[
        types.SafetySetting(
            category='HARM_CATEGORY_HATE_SPEECH',
            threshold='BLOCK_NONE',
        ),
        types.SafetySetting(
            category='HARM_CATEGORY_HARASSMENT',
            threshold='BLOCK_NONE',
        ),
        types.SafetySetting(
            category='HARM_CATEGORY_SEXUALLY_EXPLICIT',
            threshold='BLOCK_NONE',
        ),
        types.SafetySetting(
            category='HARM_CATEGORY_DANGEROUS_CONTENT',
            threshold='BLOCK_NONE',
        ),
    ]
)

def upload_pdf_file(file_path, display_name):
    """
    Uploads a PDF file to the Gemini API and returns the file object.

    Args:
        file_path (str): Path to the PDF file
        display_name (str): Display name for the uploaded file

    Returns:
        File object containing the uploaded file's metadata
    """
    try:
        # Upload the PDF file
        sample_file = llm_client.files.upload(
            file=file_path,
            config={
                "display_name": display_name,
                "mime_type": "application/pdf"
            }
        )

        print(f"Uploaded file '{sample_file.display_name}' as: {sample_file.uri}")

        # Verify the file upload
        file = llm_client.files.get(name=sample_file.name)
        print(f"Retrieved file '{file.display_name}' as: {file.uri}")

        return sample_file

    except Exception as e:
        print(f"Error uploading file: {e}")
        return None


def is_valid_json(json_str):
    """
    Check to see if a JSON string returned by LLM is valid (elsewhere a "Please continue" prompt will be issued to LLM)
    """
    try:
        ujson.loads(json_str)
        return True
    except json.JSONDecodeError:
        return False
    except:
        return False


def getPage(url):
    """
    Simple general-purpose web-page grabber with Cloudscraper support
    """

    headers = {'user-agent': 'Chrome/143.0.7499.170'}
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'mobile': False
        }
    )

    DONE = False
    MAXTRIALS = 10
    cnt_fail = 0
    res = None
    while not DONE:
        try:
            #res = requests.get(url, headers=headers)
            res = scraper.get(url)
        except requests.exceptions.RequestException:
            try:
                res = requests.get(url, headers=headers)
            except:
                cnt_fail += 1
                print(f"failed {cnt_fail} time(s)...[{url}]", flush=True)
        DONE = res != None or cnt_fail > MAXTRIALS
        time.sleep(5 + random()*6)
    if res == None:
        return None
    else:
        res.encoding = 'utf-8'
        return res.status_code, res.text

def populateCorpus(f):
    """
    Input:
        f: a JSON file
    Output:
        g: a JSON file containing the updated version
    Purpose:
        Given the list of candidate English URLs, retrieve all paragraphs from each URL and place them in the key 'english_paragraphs' (a list of list)
    """

    with open(f, "r", encoding="utf-8", newline="\n") as fi:
        CORPUS = ujson.load(fi)

    for a in CORPUS:
        zh_title = a['chinese_title']
        en_title = a['english_source_title']
        print(zh_title, f"({en_title})")
        zh_paras = a['chinese_paragraphs']

        similarity = []
        english_paragraphs = []
        
        for url_en in a['english_source_url']:
            paras_en = []
            cs = -1.0
            if url_en.endswith('.pdf') or url_en.startswith('ftp:') or 'https://www.linkedin.com' in url_en or 'https://www.facebook.com' in url_en:
                pass
            else:
                try:
                    print(f"Working on: {url_en}")
                    paras_en = getParagraphs(url_en)
                    if paras_en:
                        cs = cossim('\n'.join(paras_en), '\n'.join(zh_paras))
                        print(f"Successfully retrieved! cossim = {cs:.4f}")
                    else:
                        print("Empty list!")
                except:
                    print(en_title)
                    print(f"Not retrievable: {url_en}")

            similarity.append(cs)
            english_paragraphs.append(paras_en)
            print('-'*15)
        a['similarity'] = similarity
        a['english_paragraphs'] = english_paragraphs
            
    return CORPUS

def ddgs_search(metadata, num_results=5):
    """
    Search for URLs based on article metadata.
    """
    # Construct a specific search query
    # We combine the title and the first two authors for high precision
    authors = metadata["Authors"]
    if len(authors) > 1:
        query = f'"{metadata["Title"]}" {authors[0]} {authors[1]} "{metadata["Publication"]}"'
    else:
        query = f'"{metadata["Title"]}" {authors[0]} "{metadata["Publication"]}"'

    # Specify domain for:
    Domains = {
        'Joint Force Quarterly': "ndupress.ndu.edu/Media/News",
        'The Diplomat':  "thediplomat.com",
        'Foreign Affairs': "www.foreignaffairs.com",
        'Air & Space Forces Magazine':  "www.airandspaceforces.com",
        'Air and Space Forces Magazine':  "www.airandspaceforces.com",
        'ARMY Magazine': "www.ausa.org",
        'ARMY': "www.ausa.org",
        'Army Magazine': "www.ausa.org",
        'Army': "www.ausa.org",
        'European Security & Defence': "euro-sd.com",
        'Parameters': "publications.armywarcollege.edu",
        'China Brief': "jamestown.org",
        'Proceedings': "www.usni.org/magazines/proceedings",
        'Military Review': "www.armyupress.army.mil/Journals/Military-Review",
        'The Atlantic': "www.theatlantic.com",
        #'': "",
    }
    if metadata["Publication"] in Domains:
        domain = Domains[metadata["Publication"]]
        query = f'site:{domain} ' + query

    
    print(f"Searching for: {query}\n")
    
    urls = []
    titles = []
    
    try:
        with DDGS() as ddgs:
            # Perform the search
            results = ddgs.text(
                query=query,
                region='us-en',
                safesearch='off',
                timelimit=None,
                max_results=num_results
            )
            
            for i, result in enumerate(results, 1):
                print(f"{i}. {result['title']}")
                print(f"   URL: {result['href']}\n")
                urls.append(result['href'])
                titles.append(result['title'])
                
    except Exception as e:
        print(f"An error occurred: {e}")
    
    return urls, titles

def getEngURLsDdgs(article):

    a = deepcopy(article)

    article_metadata = {
        "Publication": a['english_source_publication'],
        "Issue": a['english_source_date'],
        "Title": a['english_source_title'],
        "Authors": a['english_source_authors']
    }

    return ddgs_search(article_metadata, num_results=7)



def google_search(query, num=5):

    google_search_endpoint_url = "https://www.googleapis.com/customsearch/v1"
    api_key = "Your Google Search API key"
    cx = "Your cx"

    params = {
        'key': api_key,
        'cx': cx,
        'q': query,
        'num': num
    }
    try:
        response = requests.get(google_search_endpoint_url, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error: {response.status_code}")
            return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None


def getEngURLs(article):
    search_query = """
{title},
{authors},
{publication}
    """.strip()
    
    a = deepcopy(article)

    title = a['english_source_title']
    authors = ', '.join(a['english_source_authors'])
    publication = a['english_source_publication']
    
    query = search_query.format(title=title, authors=authors, publication=publication)
    print(query)
    print('-'*20)

    english_source_url = a['english_source_url']
    english_source_candidate_titles = [None]
    top_matches = google_search(query, num=5)
    for match in top_matches['items']:
        #if match['link'] not in english_source_url:
        english_source_url.append(match['link'])
        try:
            english_source_candidate_titles.append(match['pagemap']['metatags'][0]['og:title'])
        except:
            english_source_candidate_titles.append(None)

    # remove duplicates
    L = english_source_url
    ogurl = L[0]
    if ogurl in L[1:]: # if original URL is also in the remainder of the list
        L.pop(0) # remove original URL
        english_source_candidate_titles.pop(0) # remove None title
        
    
    return english_source_url, english_source_candidate_titles
    

def getParagraphs0(article_url):
    """
    Given a URL, retrieve all non-empty <p> text segments
    """
    paras = []
    s, h = getPage(article_url)
    if s == 200:
        soup = BeautifulSoup(h, 'lxml')
        for p in soup.find_all('p'):
            if p.text.strip():
                paras.append(p.text.strip())

    return paras

def getParagraphs(article_url):
    """
    Given a URL, retrieve all non-empty <p> text segments
    """
    paras = []
    if article_url.startswith('https://www.foreignaffairs.com'):
        s, html = getPage(article_url)
        if s != 200:
            return None
    else:
        driver.get(article_url)
        time.sleep(5)
        html = driver.page_source

    soup = BeautifulSoup(html, 'lxml')
    for p in soup.find_all(('p', 'h1', 'h2', 'h3', 'h4')):
        if p.text.strip():
            paras.append(p.text.strip())

    return paras

def updateEngURLs(f):
    """
    Input:
        f: a JSON file
    Output:
        g: a JSON file containing the updated version
    Notes:
        Use Google Serch to get a list of URLs for candidates of the Chinese article's English source
    """

    with open(f, "r", encoding="utf-8", newline="\n") as fi:
        CORPUS = ujson.load(fi)

    ###
    for a in CORPUS:

        ESU, ESCT = getEngURLsDdgs(a) # getEngURLs(a)
        
        a['english_source_url'] = ESU
        a['english_source_candidate_titles'] = ESCT
            
    return CORPUS

#%%
# ## Step (1)
print('\n\n'+"="*20)
print("*** Step (1) commences:")
#%%

# Folder that stores the PDF files
PDF_folder = './PDF'

files = Path(PDF_folder).rglob("國防譯粹202512.pdf")
allfiles = sorted(files)
print(allfiles)
print(f"*** Uploaded PDF files to Google GenAI: {allfiles}")


#%%

uploaded_pdf_files = [upload_pdf_file(f, f.name) for f in allfiles[:]]
print(uploaded_pdf_files)
print(uploaded_pdf_files[0].uri)

#%%

chat = llm_client.chats.create(
    model=llm_model_name,
    config=generate_content_config,
    history=[],
)
print('\n\n'+"="*20)
print(f"*** Creating new chat with the LLM {llm_model_name}")

#%%
# Request that LLM perform the text extraction process
start_time = time.perf_counter()

USER_PROMPT = '''
The uploaded PDF is a Mandarin Chinese monthly digest on defense topics published by the Taiwanese defense ministry.
The digest contains about a dozen articles translated from English into Chinese.
Your tasks:
(1) Examine the preamble of each Chinese article and identify the English source article on the Internet;
(2) For each Chinese article from the PDF, extract complete sentences and paragraphs by reconstituting words/sentences broken across lines/pages due to column width limitations; ignore page breaks; use traditional Chinese punctuation marks. Retrieve all text, including captions of images. Leave all section headers on separate lines.
(3) Produce a JSON file containing the Chinese metadata (issue number, page, Chinese article title, etc.) and that of its English counterpart (publication, source URL, title, author, etc.), as well as the extracted Chinese paragraphs. Do NOT translate the Chinese text into English.
(4) Use the following JSON template with sample data enclosed in the <json> tag to produce the output:
<json>
[
    {
        "digest_issue": "第X卷第Y期",
        "digest_page_range": "5-18",
        "chinese_title": "中文標題一",
        "chinese_authors": [],
        "chinese_translators": [
          "陳聰明", "曉聰明"
        ],
        "chinese_reviewers": [
          "黃小明"
        ],
        "chinese_paragraphs": [
          "第1段落。",
          "第2段落。",
          "第3段落。",
          "第4段落。"
        ],
        "english_source_publication": "State-of-the-Art Military Tech",
        "english_source_date": "May 2025",
        "english_source_title": "English Title 1",
        "english_source_authors": [
          "Author 1",
          "Author 2",
          "Author 3"
        ],
        "english_source_url": ["https://sotamt.com/article/EnglishTitle1.html", "https://alternative.site.com/example.html"],
    },
]
</json>
(5) Make sure the English source URLs you have identified are valid links. Visit these pages to make sure they exist.
(6) If you're unable to find an English URL that corresponds to a Chinese article, just put an empty list [] in the output; do not hallucinate or make up a false answer.
(7) Make sure the total number of articles retrieved matches the article count on the 目錄 CONTENTS page. 
'''.strip()

contents =  [
                types.Part.from_uri(
                    file_uri=uploaded_pdf_files[0].uri,
                    mime_type="application/pdf"
                ),
                types.Part(text=USER_PROMPT)
            ]

f = Path(uploaded_pdf_files[0].display_name).stem + '.json'

print('\n\n'+"="*20)
print(f"*** Extracting text from PDF to {f}...")

DONE = False
cnt = 0
while not DONE:
    cnt += 1
    if cnt == 1:
        print(f"Sending prompt to model: {llm_model_name} ...")
        response = chat.send_message(
            message=contents,
            config=generate_content_config,
        )
        print("Done sending prompt to model.")
    else:
        followup_message = 'Please continue generating.'
        print(followup_message)
        print(f"Sending prompt ({cnt} times) to model: {llm_model_name} ...")
        response = chat.send_message(
            message=followup_message,
            config=generate_content_config,
        )
        print(f"Done sending prompt ({cnt} times) to model.")
    if is_valid_json(response.text):
        with open(f, 'w', encoding='utf-8', newline='\n') as fo:
            fo.write(response.text)        
        DONE = True
    else:
        print(f"Invalid JSON; trial no. {cnt}")

end_time = time.perf_counter()
duration = end_time - start_time
print(f"The LLM process ran in: {duration:.2f} seconds")

# ## Step 2: 

fin_issue = uploaded_pdf_files[0].display_name

fin_json = Path(fin_issue).stem + '.json'
DEFDIG = ujson.load(open(fin_json, 'r', encoding='utf-8'))

print('\n\n'+"="*20)
print(f"*** Created a CORPUS JSON of {len(DEFDIG)} articles")

#%%
# ### Update JSON with English candidate articles (obtained via DDGS)


fin = Path(fin_issue).stem + '.json'
fon = Path(fin_issue).stem + '.newEngURLs.json'

with open(fon, 'w', encoding='utf-8', newline='\n') as fo:
    NEW_CORPUS = updateEngURLs(fin)
    ujson.dump(NEW_CORPUS, fo, ensure_ascii=False, indent=2)

print('\n\n'+"="*20)
print(f"*** Updated CORPUS JSON with English source candidates and created new JSON: {fon}")

#%%
# ### Populate JSON with English candidates' passages, with computed cosine similarity scores

fin = Path(fin_issue).stem + '.newEngURLs.json'
fon = Path(fin_issue).stem + '.populated.json'

start_time = time.perf_counter()
NEW_CORPUS = populateCorpus(fin)
end_time = time.perf_counter()
duration = end_time - start_time
print(f"The population process ran in: {duration:.2f} seconds")

with open(fon, 'w', encoding='utf-8', newline='\n') as fo:
    ujson.dump(NEW_CORPUS, fo, ensure_ascii=False, indent=2)

print('\n\n'+"="*20)
print(f"*** Populated CORPUS JSON with paragraphs from English source articles and created new JSON: {fon}")

#%%
# ### Perform sentence alignment via an external script "alignDefDig.py"
print('\n\n'+"="*20)
print("*** Performing sentence alignment...")

import subprocess

fin = Path(uploaded_pdf_files[0].display_name).stem
result = subprocess.run(['python', 'alignDefDig.py', '1', fin], capture_output=True, text=True)
print(result.stdout)
print(result.stderr)
