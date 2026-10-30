import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from shorts_generator.stages.highlights.engine import chunk_transcript, get_highlights, _sanitize_highlights, dedupe_highlights
from shorts_generator.stages.render.local.subtitles import word_captions, offset_subtitles
from shorts_generator.stages.transcribe.whisper import _transcript_cache_path
from shorts_generator.pipeline import Pipeline


class PipelineTests(unittest.TestCase):
    def test_long_video_uses_relative_times_once(self):
        transcript = {'duration': 2500, 'segments': [
            {'start': i, 'end': i+10, 'text': 'Complete sentence.'} for i in range(0,2500,10)]}
        chunks = chunk_transcript(transcript)
        self.assertEqual(chunks[1]['segments'][0]['start'], 0)
        def llm(prompt):
            if 'classify' in prompt:
                return '{"content_type":"tutorial","density":"high"}'
            return json.dumps({'highlights':[{'start_time': 10, 'end_time': 30, 'score': 90}]})
        ranked = get_highlights(transcript, 3, llm)
        self.assertIn(1150, [h['start_time'] for h in ranked])
        self.assertTrue(all(h['end_time'] <= 2500 for h in ranked))

    def test_nonfinite_and_invalid_model_times(self):
        self.assertEqual(_sanitize_highlights([{'start_time':float('nan'),'end_time':30},
            {'start_time':0,'end_time':float('inf')}, {'start_time':20,'end_time':10}],100), [])

    def test_nested_duplicates_keep_best(self):
        self.assertEqual(len(dedupe_highlights([
            {'start_time':10,'end_time':20,'score':99},
            {'start_time':0,'end_time':100,'score':80}])),1)

    def test_invalid_count_before_download(self):
        pipe = Pipeline('local', lambda *a: self.fail('download called'), None, None, None)
        with self.assertRaises(ValueError):
            pipe.run('x', num_clips=0)

    def test_captions_measured_times_and_escape(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp)/'transcript.json'
            cache.write_text(json.dumps({'transcript':{'segments':[{'words':[
                {'start':10+i*.3,'end':10+(i+1)*.3,'word':w}
                for i,w in enumerate(['This','is','a','{test}','today'])]}]}}))
            with patch('shorts_generator.stages.transcribe.whisper._transcript_cache_path',return_value=cache.with_suffix('.srt')):
                for every,color,expected in [('4','yellow','&H00FFFF&'),('5','green','&H00FF00&')]:
                    with patch.dict('os.environ',CAPTION_HIGHLIGHT_EVERY=every,CAPTION_HIGHLIGHT_COLOR=color):
                        out=Path(tmp)/'clip.ass'
                        self.assertTrue(word_captions('x',str(out),10.2,11.4,'9:16'))
                        text=out.read_text(encoding="utf-8")
                        self.assertIn(expected,text)
                        self.assertIn('0:00:00.00',text)
                        self.assertNotIn('{test}',text)

    def test_cache_source_collision(self):
        self.assertNotEqual(_transcript_cache_path('a/video.mp4'),_transcript_cache_path('b/video.mp4'))

    def test_srt_overlap_clamped(self):
        with tempfile.TemporaryDirectory() as tmp:
            src=Path(tmp)/'in.srt'; out=Path(tmp)/'out.srt'
            src.write_text('1\n00:00:02,000 --> 00:00:06,000\nHello\n')
            offset_subtitles(str(src),str(out),3,5)
            self.assertIn('00:00:00,000 --> 00:00:02,000',out.read_text())

if __name__ == '__main__':
    unittest.main()

