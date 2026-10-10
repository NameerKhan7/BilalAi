"""Groq speech-to-text. Called only after an explicit Transcribe action."""
from pathlib import Path
import os
import wave
from dotenv import dotenv_values
from groq import Groq,AuthenticationError,RateLimitError,APITimeoutError,APIConnectionError,APIStatusError
ROOT=Path(__file__).resolve().parent
DEFAULT_MODEL='whisper-large-v3-turbo'
VOCABULARY_HINT='Windows voice assistant vocabulary: Chrome, Google Chrome, Chrome browser, Notion, Spotify, YouTube, Instagram, WhatsApp, Notepad, Calculator, Bilal.'

class TranscriptionError(RuntimeError):
    """A safe, user-facing transcription error without credential details."""


def transcribe_recording(path,api_key=None,language=None):
    path=Path(path)
    if not path.is_file():
        raise TranscriptionError('Recording was not found. Record a command again.')
    if path.stat().st_size>25*1024*1024:
        raise TranscriptionError('Recording is too large. Record a shorter command.')
    try:
        with wave.open(str(path),'rb') as audio:
            if (audio.getnchannels(),audio.getsampwidth(),audio.getframerate())!=(1,2,16000):
                raise TranscriptionError('Use the mono 16 kHz WAV from the command recorder.')
            if audio.getnframes()==0:
                raise TranscriptionError('Recording is empty. Record a command again.')
    except (wave.Error,EOFError,OSError) as exc:
        raise TranscriptionError('Recording could not be read. Record a command again.') from exc
    key=api_key or os.environ.get('GROQ_API_KEY') or dotenv_values(ROOT/'.env').get('GROQ_API_KEY')
    if not key or not key.strip():
        raise TranscriptionError('Add GROQ_API_KEY to your local .env file, then try again.')
    options={'file':(path.name,path.read_bytes()),'model':DEFAULT_MODEL,'response_format':'json','temperature':0.0,'prompt':VOCABULARY_HINT}
    if language: options['language']=language
    try:
        with Groq(api_key=key,timeout=20.0,max_retries=1) as client:
            response=client.audio.transcriptions.create(**options)
    except AuthenticationError as exc:
        raise TranscriptionError('Groq rejected the API key. Update GROQ_API_KEY in your local .env file.') from exc
    except RateLimitError as exc:
        raise TranscriptionError('Groq usage limit reached. Try later or check your Groq account limits.') from exc
    except APITimeoutError as exc:
        raise TranscriptionError('Transcription timed out. Try again.') from exc
    except APIConnectionError as exc:
        raise TranscriptionError('Could not reach Groq. Check your internet connection.') from exc
    except APIStatusError as exc:
        raise TranscriptionError(f'Groq could not transcribe this recording (HTTP {exc.status_code}). Try again.') from exc
    text=getattr(response,'text','')
    if not isinstance(text,str) or not text.strip():
        raise TranscriptionError('No speech was transcribed. Record the command again.')
    return text.strip()
