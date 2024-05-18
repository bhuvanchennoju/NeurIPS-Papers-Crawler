

''' 
===================================================================================================



===================================================================================================
|- data folder structure
    |- data - year
        |- paper_id 
            |- paper_id_abstract.json
            |- paper_id_metadata.json
            |- paper_id.pdf
|-  scraper.py
|-  getdata.py

'''




import os
import sys
import json
import argparse
import asyncio
import aiohttp
import requests  # Import requests for fetching metadata and PDFs
from bs4 import BeautifulSoup

base_url = "https://papers.nips.cc"
default_headers = {
    "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.183 Safari/537.36",
}

def get_conference_url(year):
    return f"{base_url}/paper/{year}"

async def fetch(session, url):
    try:
        async with session.get(url, headers=default_headers) as response:
            response.raise_for_status()
            return await response.text()
    except aiohttp.ClientError as e:
        print(f"Error fetching {url}: {e}")
        sys.exit(1)

async def fetch_all(session, urls):
    tasks = [fetch(session, url) for url in urls]
    return await asyncio.gather(*tasks)

async def get_paper_paths(year):
    url = get_conference_url(year)
    async with aiohttp.ClientSession() as session:
        page_content = await fetch(session, url)
        soup = BeautifulSoup(page_content, "html.parser")
        
        paper_ids, abstract_paths, metadata_paths, pdf_paths = [], [], [], []
    
        
        for li in soup.find("div", class_='container-fluid').find_all("li"):
            paper_temp_url = li.a.get('href')
            paper_id = paper_temp_url.split("/")[-1].split("-")[0]
            
            paper_ids.append(paper_id)
            abstract_paths.append(f"{base_url}{paper_temp_url}")
            
            paper_base_url = f"{base_url}{paper_temp_url.rsplit('.', 1)[0]}"
            metadata_paths.append(f"{paper_base_url.replace('Abstract', 'Metadata').replace('hash', 'file')}.json")
            pdf_paths.append(f"{paper_base_url.replace('Abstract', 'Paper').replace('hash', 'file')}.pdf")
        
        return paper_ids, abstract_paths, metadata_paths, pdf_paths

def get_metadata(meta_path):
    response = requests.get(meta_path)
    if response.status_code != 200:
        return {}
    return response.json()

def get_pdf(pdf_path):
    try:
        response = requests.get(pdf_path)
        response.raise_for_status()
        return response.content
    except Exception as e:
        print(f"Error downloading PDF from {pdf_path}: {e}")
        return None
    

def get_abstract(abstract_path):
    response = requests.get(abstract_path)
    if response.status_code != 200:
        return ""
    soup = BeautifulSoup(response.text, "html.parser")
    abstract_text = soup.find('h4', string ='Abstract').find_next('p').get_text()

    # wrap the text into small paragraphs
    abstract_text = " ".join(abstract_text.split())
    
    title = soup.find('meta', {'name': 'citation_title'})['content']
    authors = soup.find_all('meta', {'name': 'citation_author'})
    authors = [author['content'] for author in authors]
    return {'title': title, 'authors': authors, 'abstract': abstract_text}

def get_latest_conference_year():
    url = 'https://papers.nips.cc/'
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    years = []
    for item in soup.find_all('li'):
        try:
            year = int(item.text.split()[-1].strip('()'))
            years.append(year)
        except (ValueError, IndexError):
            continue

    return max(years) if years else 2023


def get_args():
    latest_year = get_latest_conference_year()
    parser = argparse.ArgumentParser(description='Download NIPS papers')
    parser.add_argument('--start_year', type=int, default=1987, help='start year')
    parser.add_argument('--end_year', type=int, default=latest_year, help='end year')
    parser.add_argument('--output_dir', type=str, default='data', help='output directory')
    return parser.parse_args()

def check_args(args):

    if args.start_year < 1987:
        sys.exit("Start year must be 1987 or later")
    if args.start_year > args.end_year:
        sys.exit("Start year must be less than or equal to end year")

async def main():
    args = get_args()
    start_year = args.start_year
    end_year = args.end_year
    output_dir = args.output_dir

    if not os.path.exists(output_dir):
        sys.exit(f"Output directory {output_dir} does not exist")


    for year in range(start_year, end_year + 1):
        year_dir = os.path.join('../data', str(year))

        paper_ids, abstract_paths, metadata_paths, pdf_paths = await get_paper_paths(year)

        for paper_id, abstract_path, metadata_path, pdf_path in zip(paper_ids, abstract_paths, metadata_paths, pdf_paths):
            print(f"Downloading {paper_id}")
            
            # save directory for the paper
            save_dir = os.path.join(year_dir, paper_id)
            os.makedirs(save_dir, exist_ok=True)
            
            abstract = get_abstract(abstract_path)
            metadata = get_metadata(metadata_path)
            pdf = get_pdf(pdf_path)

            with open(os.path.join(save_dir, f"{paper_id}_abstract.json"), "w") as f:
                json.dump(abstract, f, indent=4)

            with open(os.path.join(save_dir, f"{paper_id}_metadata.json"), "w") as f:
                json.dump(metadata, f, indent=4)

            with open(os.path.join(save_dir, f"{paper_id}.pdf"), "wb") as f:
                f.write(pdf)

            break 



if __name__ == "__main__":
    asyncio.run(main())
