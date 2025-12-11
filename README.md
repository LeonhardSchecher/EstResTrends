# Estonian Scientific Research Trends
Structure:

## Article_extraction
Contains the scripts that were used to make the data file, containing all the article documents that we could get, smaller.
At first the file was 16 GB. 
extract_abstracts.py filtered out the abstracts by looking, if the document had a section called abstract. If not the first 400 words of the document were taken.
jsonfix.py filtered the dataset to throw out trivial descriptions.
filter_abstract.py made a request to GPT using the API. The LLM would decide if the extracted abstract or first 400 words were good enough to be used in our database.
After this process we got a file with the size of 17 MB(1000 times smaller). 

## Dashboard
Contains the webapp version of the dashboard of our project. The code is in app.py and uses plotly dash framework.

## Data_visualization
Contains test notebook file that we used to try out different plots on our database.

## Link-to-data 
Contains a Google Drive link to all data that we produced and used in our project.

## Report-poster-other
Contains the poster image file and report as a PDF

## etis_api.py
This script downloads the data from etis in .json format. This data contains atleast the article's title.

## Scraper
This script tries to download articles or the introduction page. The links are taken from etis.




