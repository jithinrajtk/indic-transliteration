import streamlit as st
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound, VideoUnavailable
from googletrans import Translator
import time
import random
from pytube import YouTube
import re

# Function to fetch video duration
def fetch_video_duration(video_id):
    try:
        yt = YouTube(f"https://www.youtube.com/watch?v={video_id}")
        return yt.length
    except Exception as e:
        st.error(f"Error fetching video duration: {e}")
        return None

# Function to extract YouTube video ID from URL
def extract_video_id(url):
    pattern = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
    match = re.search(pattern, url)
    return match.group(1) if match else None

# Function to fetch and translate subtitles
def fetch_and_translate_subtitles(video_id, source_language='ml', target_language='en'):
    try:
        duration = fetch_video_duration(video_id)
        if duration is None:
            st.error("Could not fetch video duration.")
            return
        
        minutes, seconds = divmod(duration, 60)
        st.write(f"**Video duration:** {minutes} minutes {seconds} seconds")

        max_retries = 5
        retry_count = 0

        while retry_count < max_retries:
            try:
                transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

                for transcript in transcript_list:
                    if transcript.language_code == source_language and transcript.is_generated:
                        st.success(f"Subtitles found in {source_language.upper()} for video ID: {video_id}")
                        
                        transcript_data = transcript.fetch()
                        source_text = " ".join(entry['text'] for entry in transcript_data)

                        # Display original subtitles
                        st.text_area("Original Subtitles", source_text, height=150)

                        translator = Translator()
                        translated_text = ""

                        # Translate in chunks to avoid errors
                        chunks = [source_text[i:i + 500] for i in range(0, len(source_text), 500)]
                        full_translation_successful = True

                        for chunk in chunks:
                            retries_translate = 3
                            success = False
                            while retries_translate > 0:
                                try:
                                    translated_chunk = translator.translate(chunk, src=source_language, dest=target_language).text
                                    translated_text += translated_chunk + "\n"
                                    success = True
                                    break  # Exit the retry loop once translation is successful
                                except Exception as e:
                                    retries_translate -= 1
                                    time.sleep(random.uniform(5, 10))
                            if not success:
                                full_translation_successful = False
                                break

                        if not full_translation_successful:
                            st.error("Failed to translate some parts of the subtitles after multiple retries.")
                            return

                        # Ensure full translation has been done
                        if translated_text.strip():
                            st.text_area("Translated Subtitles", translated_text, height=150)
                            st.download_button("Download Original Subtitles", source_text, file_name=f"{video_id}_original.txt")
                            st.download_button("Download Translated Subtitles", translated_text, file_name=f"{video_id}_translated.txt")
                            st.success("Translation completed successfully!")
                        else:
                            st.error("Translation resulted in empty text. Please check the Google Translate API or input.")
                        return

                retry_count += 1
                time.sleep(2)

            except (TranscriptsDisabled, VideoUnavailable, NoTranscriptFound):
                retry_count += 1
                time.sleep(2)
            except Exception as e:
                st.error(f"An error occurred: {e}. Retrying...")
                retry_count += 1
                time.sleep(2)

        st.error("Failed to retrieve transcripts after multiple attempts.")

    except Exception as e:
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
