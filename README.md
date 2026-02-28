# Estonian Scientific Research Trends
## Structure:

## Article_extraction
Contains the scripts that were used to make the data file, containing all the article documents that we could get, smaller.
At first, the file was 16 GB. 
extract_abstracts.py filtered out the abstracts by looking for documents that had a section called abstract. If not, the first 400 words of the document were taken.
jsonfix.py filtered the dataset to throw out trivial descriptions.
filter_abstract.py made a request to GPT using the API. The LLM would decide if the extracted abstract or the first 400 words were good enough to be used in our database.
After this process we got a file with the size of 17 MB(1000 times smaller). 

## Dashboard
Contains the webapp version of the dashboard of our project. The code is in app.py and uses the Plotly Dash framework.
## RUNNING THE DASHBOARD: 
1. Download the data.json file from the Google Drive link that is provided in the Link-to-data .txt file. 
2. Run the command: python -m pip install dash pandas plotly, to install the required Python libraries
3. Replace the DATA_PATH variable value with the location of the data.json file in your computer and run the following command: "path_where_the dashboard_is_in_your_comuputer/"+Dashboard/app.py
4. Click on the link following "Dash is running on ..."

## Classification
Contains the scripts for the GPT API to classify articles with Frascati classification and give them keywords.

## Data_visualization
Contains a test notebook file that we used to try out different plots on our database.

## Link-to-data 
Contains a Google Drive link to all the data that we produced and used in our project.

## Report-poster-other
Contains the poster image file and report as a PDF

## Data-mining
scrape.py tries to download articles or the introduction page. The links are taken from etis.
etis_api.py downloads the data from etis in .json format. This data contains at least the article's title.

## test.ipynb - Test file trying out the GPT API



