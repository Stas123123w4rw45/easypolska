"""Text-to-Speech service using OpenAI TTS API."""

import os
import hashlib
from pathlib import Path
from typing import Optional
from openai import AsyncOpenAI
import config


class TTSService:
    """Service for generating Polish audio using OpenAI TTS."""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=config.OPENAI_API_KEY) if config.OPENAI_API_KEY else None
        self.model = config.TTS_MODEL
        self.voice = config.TTS_VOICE
        self.audio_dir = Path(config.TTS_AUDIO_DIR)
        self.audio_dir.mkdir(exist_ok=True)
    
    def _get_cache_path(self, text: str) -> Path:
        """Generate cache file path based on text hash."""
        text_hash = hashlib.md5(text.encode()).hexdigest()
        return self.audio_dir / f"{text_hash}.mp3"
    
    async def generate_speech(
        self,
        text: str,
        use_cache: bool = True
    ) -> Optional[str]:
        """
        Generate speech audio for Polish text.
        
        Args:
            text: Polish text to convert to speech
            use_cache: Whether to use cached audio if available
        
        Returns:
            Path to audio file or None if generation failed
        """
        if not self.client:
            print("⚠️ OpenAI API key not configured, TTS disabled")
            return None
        
        cache_path = self._get_cache_path(text)
        
        # Check cache
        if use_cache and cache_path.exists():
            print(f"✅ Using cached TTS: {cache_path.name}")
            return str(cache_path)
        
        try:
            # Generate audio
            response = await self.client.audio.speech.create(
                model=self.model,
                voice=self.voice,
                input=text
            )
            
            # Save to file
            with open(cache_path, 'wb') as f:
                f.write(response.content)
            
            print(f"✅ Generated TTS: {cache_path.name}")
            return str(cache_path)
        
        except Exception as e:
            print(f"❌ TTS generation failed: {e}")
            return None
    
    def cleanup_old_files(self, max_age_days: int = 7):
        """
        Clean up old cached audio files.
        
        Args:
            max_age_days: Maximum age of files to keep
        """
        import time
        
        now = time.time()
        max_age_seconds = max_age_days * 86400
        
        for file_path in self.audio_dir.glob("*.mp3"):
            if now - file_path.stat().st_mtime > max_age_seconds:
                file_path.unlink()
                print(f"🗑️ Deleted old TTS file: {file_path.name}")


# Singleton instance
tts_service = TTSService()
