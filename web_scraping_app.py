import streamlit as st
import requests
from bs4 import BeautifulSoup
import wikipedia
import logging
from io import BytesIO
from gtts import gTTS

# configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

ERROR_PREFIX = "Error:"

# Languages offered in the UI (gTTS language codes)
LANGUAGES = {
    "English": "en",
    "Hindi": "hi",
    "Gujarati": "gu",
    "French": "fr",
    "German": "de",
    "Spanish": "es",
}


def get_wikipedia_url(search_term):
    try:
        logging.info(f'Searching wikipedia for : {search_term}')
        page_title = wikipedia.page(search_term).title
        url = f"https://en.wikipedia.org/wiki/{page_title.replace(' ', '_')}"
        logging.info(f"Found wikipedia URL: {url}")
        return url
    except Exception as e:
        logging.error(f"Wikipedia search error: {e}")
        return None


def scrape_content(url, max_words=1000):
    try:
        logging.info(f"Attempting to Scrape url:{url}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        content = ''
        paragraphs = soup.select('p')
        logging.info(f"Found {len(paragraphs)} paragraph tags.")

        for p in paragraphs:
            text = p.get_text()
            if len(text.split()) > 0:
                content += text + '\n'

            if len(content.split()) >= max_words:
                logging.info(f"Reached Max words({max_words}). stopping scrapping.")
                break

        content = ' '.join(content.split()[:max_words])
        logging.info(f"Scrapped Content length(words): {len(content.split())}")
        return content

    except Exception as e:
        logging.error(f"Scrapping Error: {e}")
        # Consistent prefix so main() can detect it
        return f"{ERROR_PREFIX} scrapping failed - {e}"


@st.cache_data(show_spinner=False)
def text_to_speech(text, lang="en", slow=False):
    """Convert text to MP3 bytes with gTTS. Cached so reruns don't regenerate audio."""
    try:
        logging.info(f"Generating speech (lang={lang}, slow={slow}, words={len(text.split())})")
        tts = gTTS(text=text, lang=lang, slow=slow)
        audio_buffer = BytesIO()
        tts.write_to_fp(audio_buffer)
        audio_buffer.seek(0)
        logging.info("Speech generated successfully.")
        return audio_buffer.getvalue()
    except Exception as e:
        logging.error(f"gTTS Error: {e}")
        return None


def main():
    st.set_page_config(page_title="Wikipedia Scraper", layout="centered")
    st.title("📚 Wikipedia content scraper")

    search_term = st.text_input("Enter the search Term: ")

    # Text-to-speech options
    col1, col2 = st.columns(2)
    with col1:
        lang_name = st.selectbox("Speech language", list(LANGUAGES.keys()))
    with col2:
        slow = st.checkbox("Slow speech", value=False)

    if search_term:
        with st.spinner("Searching and Scrapping..."):
            wiki_url = get_wikipedia_url(search_term)

        if not wiki_url:
            st.error("Couldn't find Wikipedia page")
            return

        with st.spinner("Scrapping content..."):
            scrapped_text = scrape_content(wiki_url)

        if not scrapped_text:
            st.warning("No content was extracted from the Wikipedia page.")
            return

        if scrapped_text.startswith(ERROR_PREFIX):
            st.error(scrapped_text)
            return

        st.markdown(f"**Source:** [{wiki_url}]({wiki_url})")
        st.text_area("Extracted Content :", value=scrapped_text, height=500)

        # ---- gTTS section ----
        st.subheader("🔊 Listen to the content")
        with st.spinner("Converting text to speech..."):
            audio_bytes = text_to_speech(scrapped_text, LANGUAGES[lang_name], slow)

        if audio_bytes:
            st.audio(audio_bytes, format="audio/mp3")
            st.download_button(
                label="⬇️ Download MP3",
                data=audio_bytes,
                file_name=f"{search_term.replace(' ', '_')}.mp3",
                mime="audio/mpeg",
            )
        else:
            st.error("Text-to-speech conversion failed. Check your internet connection and try again.")


if __name__ == "__main__":
    main()
