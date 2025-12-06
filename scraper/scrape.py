
import os
from json import load, dumps
import sys
from requests import get
from threading import Thread
from time import sleep

WORK_PATH = sys.argv[0].replace("scrape.py", "")
if WORK_PATH == "":WORK_PATH = "./"
DOWNLOAD_INFO = WORK_PATH+"links.json"
WRITE_PATH = WORK_PATH+"/data"
print(WORK_PATH)
if not (os.path.exists(DOWNLOAD_INFO) and os.path.isfile(DOWNLOAD_INFO)): exit(1)
if not (os.path.exists(WRITE_PATH)): os.mkdir(WRITE_PATH)

#salvestame failid alati kujul (etise) GUID.ext
with open(DOWNLOAD_INFO, 'rb') as file:
    links = load(file)

def get_done_guids(path):
    print("getting file list")
    files = os.listdir(path)
    return set([file.split(".")[0] for file in files])

def save(path, contents):
    with open(path, 'wb') as f:
        f.write(contents)

def download(url:str, guid:str, links:dict, write_path:str):
    try:
        with get(url) as page:
            links["status"]["guid"] = page.status_code
            if page.status_code != 200:
                return
            byts = page.content
    except:
        print("viga: " + guid, url)
        links["status"][guid] = -1
        with open("./error.txt", 'a') as f:
            f.write(guid+ " " + url+"\n")
        return
    
    ext = ".unkwn"
    
    if byts.lower().startswith(b'%pdf'): ext = ".pdf"
    elif b'html' in byts.lower(): ext = ".html"

    save(write_path+'/'+guid+ext, byts)


#init
done_guids = get_done_guids(WRITE_PATH)
url_guids = set(links["Url"].keys())
text_guids = set(links["FullTextLocation"].keys()).union(url_guids).difference(done_guids)
doi_guids = set(links["Doi"].keys()).difference(text_guids).difference(done_guids)


urls = {}
# generate links
for guid in text_guids:
    lnk = links["FullTextLocation"][guid]
    if lnk is None: continue
    urls[guid] = lnk
for guid in doi_guids:
    lnk = links["Doi"][guid]
    if lnk is None: continue
    urls[guid] = lnk
print(len(urls))

threads = [Thread(target=download, args = (urls[guid], guid, links, WRITE_PATH,)) for guid in urls.keys()]
init_thread_count = len(threads)
[th.start() for th in threads]
