import streamlit as st
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound, VideoUnavailable
from deep_translator import GoogleTranslator
import time
import random
import re
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Function to extract YouTube video ID from URL
def extract_video_id(url):
    logging.debug(f"Extracting video ID from URL: {url}")
    pattern = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
    match = re.search(pattern, url)
    if match:
        video_id = match.group(1)
        logging.debug(f"Extracted video ID: {video_id}")
        return video_id
    else:
        logging.error("Failed to extract video ID. Invalid URL format.")
        return None

# Function to check if subtitles are available
@st.cache_data
def check_subtitles_available(video_id, source_language):
    logging.debug(f"Checking subtitles for video ID: {video_id} and source language: {source_language}")
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        for transcript in transcript_list:
            if transcript.language_code == source_language and transcript.is_generated:
                logging.debug("Subtitles are available.")
                return True, transcript
        logging.warning("Subtitles are not available in the specified language.")
        return False, None
    except (TranscriptsDisabled, VideoUnavailable, NoTranscriptFound) as e:
        logging.warning(f"Error checking subtitles: {e}. Subtitles might be disabled or unavailable.")
        return False, None
    except Exception as e:
        logging.error(f"Unexpected error while checking subtitles: {e}")
        return False, None

# Function to fetch and translate subtitles
def fetch_and_translate_subtitles(video_id, source_language='ml', target_language='en'):
    logging.debug(f"Fetching and translating subtitles for video ID: {video_id}")

    subtitles_available, transcript = check_subtitles_available(video_id, source_language)
    if not subtitles_available:
        st.error(f"Could not retrieve subtitles for video ID: {video_id}. Subtitles might be disabled or unavailable.")
        logging.error(f"Could not retrieve subtitles for video ID: {video_id}. Subtitles might be disabled or unavailable.")
        return

    try:
        transcript_data = transcript.fetch()
        source_text = " ".join(entry['text'] for entry in transcript_data)

        # Display original subtitles
        st.text_area("Original Subtitles", source_text, height=150)

        # Initialize translator
        translator = GoogleTranslator(source=source_language, target=target_language)

        translated_text = ""

        # Translate in chunks to avoid errors
        chunks = [source_text[i:i + 500] for i in range(0, len(source_text), 500)]
        full_translation_successful = True

        for chunk in chunks:
            retries_translate = 3
            success = False
            while retries_translate > 0:
                try:
                    translated_chunk = translator.translate(text=chunk)
                    translated_text += translated_chunk + "\n"
                    success = True
                    break  # Exit the retry loop once translation is successful
                except Exception as e:
                    logging.warning(f"Translation error: {e}. Retrying...")
                    retries_translate -= 1
                    time.sleep(random.uniform(5, 10))
            if not success:
                full_translation_successful = False
                break

        if not full_translation_successful:
            logging.error("Failed to translate some parts of the subtitles after multiple retries.")
            st.error("Failed to translate some parts of the subtitles after multiple retries.")
            return

        # Ensure full translation has been done
        if translated_text.strip():
            st.text_area("Translated Subtitles", translated_text, height=150)
            st.download_button("Download Original Subtitles", source_text, file_name=f"{video_id}_original.txt")
            st.download_button("Download Translated Subtitles", translated_text, file_name=f"{video_id}_translated.txt")
            st.success("Translation completed successfully!")
            logging.info("Translation completed successfully!")
        else:
            logging.error("Translation resulted in empty text. Please check the translation API or input.")
            st.error("Translation resulted in empty text. Please check the translation API or input.")
        return

    except Exception as e:
        logging.error(f"An unexpected error occurred in fetch_and_translate_subtitles: {e}")
        st.error(f"An unexpected error occurred: {e}")

# Streamlit UI
st.title("YouTube Subtitle Translator")

youtube_url = st.text_input("YouTube Link")

language_options = {
    'ml': 'Malayalam (ml)',
    'ta': 'Tamil (ta)',
    'te': 'Telugu (te)',
    'hi': 'Hindi (hi)',
    'en': 'English (en)'
}

source_language = st.selectbox("Select Source Language", options=list(language_options.values()), index=0)
target_language = st.selectbox("Select Target Language", options=list(language_options.values()), index=4)

if st.button("Translate Subtitles"):
    video_id = extract_video_id(youtube_url)
    if video_id:
        fetch_and_translate_subtitles(video_id, source_language.split()[-1][1:-1], target_language.split()[-1][1:-1])
    else:
        st.error("Invalid YouTube URL. Please enter a valid URL.")
        logging.error("Invalid YouTube URL. User input is not valid.")
