
from json import dump, loads, load
from os.path import exists
from requests import get
from threading import Thread
START_YEAR = "2020" 
END_YEAR = "2025"

TAKE = 1000 # take ei tohi olla kindlasti üle 5000


# https://andmed.eesti.ee/datasets/eesti-teadusinfosusteemi-avaandmed

def get_count():
    COUNT_URL = "https://www.etis.ee:7443/api/publication/getcount?Format=json&SearchType=2&Take=5&Skip=0&PublishingYearMin=2020&PublishingYearMax=2025&ClassificationCode=1&PublicationStatus=1"
    with get(COUNT_URL) as page:
        return loads(page.content)["Count"]

def get_datapart(take, skip, l:list) -> None:
    URL = f"https://www.etis.ee:7443/api/publication/getitems?Format=json&SearchType=2&Take={take}&Skip={skip}&PublishingYearMin=2020&PublishingYearMax=2025&ClassificationCode=1&PublicationStatus=1"
    with get(URL) as page:
        l.extend(loads(page.content)) 
taken = 0
data = []
total = 6500
i = 0

threads = [Thread(target= get_datapart, args = (TAKE, n, data,)) for n in range(0, total, TAKE)]
[th.start() for th in threads]

flag = True
while flag:
    flag = False
    for th in threads:
        if th.is_alive():
            flag= True
            break

with open("etis.json", 'w') as f:
    dump(data, f)
    
    
