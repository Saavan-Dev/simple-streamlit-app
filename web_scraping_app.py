import streamlit as st
import requests
from bs4 import BeautifulSoup
import wikipedia
import logging

# configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_wikipedia_url(search_term):
  try:
    logging.info(f'Searching wikipedia for : {search_term}')
    page_title=wikipedia.page(search_term).title
    url=f"https://en.wikipedia.org/wiki/{page_title.replace(' ','_')}"
    logging.info(f"Found wikipedia URL: {url}")
    return url
  except Exception as e:
    logging.error(f"An Unexpected error")
    return None

def scrape_content(url,max_words=1000):
    try:
      logging.info(f"Attempting to Scrape url:{url}")
      headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }
      response=requests.get(url,headers=headers)
      response.raise_for_status()
      soup=BeautifulSoup(response.text,'html.parser')
      content=''
      paragraphs=soup.select('p')
      logging.info(f"Found {len(paragraphs)} paragraph tags.")

      for p in paragraphs:
        text=p.get_text()
        words=text.split()
        if len(words)>0:
          content+=text +'\n'

        if len(content.split())>=max_words:
          logging.info(f"Reached Max words({max_words}).stopping scrapping.")
          break

      content=' '.join(content.split()[:max_words])
      logging.info(f"Scrapped Content length(words): {len(content.split())}")
      return content

    except Exception as e:
      logging.error(f"Scrapping Error")
      return f"An scrapping error {e}"

def main():
  st.set_page_config(page_title="Wikipedia Scraper", layout="centered")
  st.title("📚wikipedia content scraper")

  search_term=st.text_input("Enter the search Term: ")

  if search_term:
    with st.spinner("Searching and Scrapping..."):
      wiki_url=get_wikipedia_url(search_term)
      if wiki_url:
        scrapped_text=scrape_content(wiki_url)

        if scrapped_text and not scrapped_text.startswith("Error"):
          st.text_area("Extracted Content :", value=scrapped_text,height=500)

        elif scrapped_text.startswith("Error"):
          st.error(scrapped_text)

        else:
          st.warning("No content was extracted from the Wikipedia page.")

      else:
        st.error("couldn't find Wikipedia page")
if __name__=="__main__":
  main()
