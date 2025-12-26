import base64
from elevenlabs import Voice, VoiceSettings
from elevenlabs.client import ElevenLabs as el

from app.utils.api_key_encryption import decrypt_api_key


class ElevenLabsClient:
    def __init__(self, elevenlabs_api_key: str):
        decrypted_api_key = decrypt_api_key(elevenlabs_api_key)

        self.client = el(decrypted_api_key)

    async def generate_audio(
        self,
        text_message: str,
        voice_id: str,
        stability: float,
        similarity_boost: float,
        style: float,
    ) -> str:
        voice = Voice(
            voice_id=voice_id,
            settings=VoiceSettings(
                stability=stability,
                similarity_boost=similarity_boost,
                style=style,
                use_speaker_boost=True,
            ),
        )

        audio_iterator = self.client.generate(
            text=text_message, model="eleven_turbo_v2_5", voice=voice
        )

        audio_bytes = b"".join(audio_iterator)
        audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
        return audio_base64

    def add_voice(
        self, voice_name: str, description: str, voice_files: list[str]
    ) -> Voice:
        voice = self.client.clone(
            name=voice_name, description=description, files=voice_files
        )
        return voice

    def get_voice(self, voice_id: str) -> Voice | None:
        voice = self.client.voices.get(voice_id=voice_id)
        return voice if voice else None

    def edit_voice(self, voice_id: str, voice_name: str, description: str) -> bool:
        try:
            self.client.voices.edit(
                voice_id=voice_id, name=voice_name, description=description
            )
            return True
        except Exception as e:
            # TODO: throw exception
            print(f"Error while editing ElevenLabs voice: {e}")
            return False

    def delete_voice(self, voice_id: str) -> bool:
        try:
            self.client.voices.delete(voice_id=voice_id)
            return True
        except Exception as e:
            # TODO: throw exception
            print(f"Error while deleting ElevenLabs voice: {e}")
            return False
