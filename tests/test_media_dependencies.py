import importlib.util
import tempfile
import unittest
import wave
from pathlib import Path

@unittest.skipUnless(importlib.util.find_spec('faster_whisper'), 'local dependencies not installed')
class MediaDependencyTests(unittest.TestCase):
    def test_whisper_can_decode_audio(self):
        from faster_whisper.audio import decode_audio
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'speech.wav'
            with wave.open(str(path),'wb') as stream:
                stream.setnchannels(1); stream.setsampwidth(2); stream.setframerate(16000)
                stream.writeframes(b'\0\0'*16000)
            samples=decode_audio(str(path))
            self.assertEqual(len(samples),16000)
