import importlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from shorts_generator.pipeline import Pipeline
from shorts_generator.review import render_plan

class ReviewTests(unittest.TestCase):
    def test_review_selects_top_without_render(self):
        t={'duration':60,'segments':[{'start':0,'end':60,'text':'Complete.'}]}
        clips=[{'start_time':0,'end_time':20,'score':30}, {'start_time':30,'end_time':60,'score':90}]
        pipe=Pipeline('local',lambda *a:'video.mp4',lambda *a:t,lambda *a:clips,
                      lambda *a:self.fail('review invoked rendering'))
        result=pipe.run('video.mp4',num_clips=1,review_only=True)
        self.assertEqual(result['shorts'],[])
        self.assertEqual([h['selected'] for h in result['highlights']],[False,True])

    def test_invalid_review_times_fail_before_render(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'source.mp4';source.touch()
            plan={'mode':'local','source_video_url':str(source),'transcript':{'duration':30,'segments':[]},
                  'highlights':[{'start_time':0,'end_time':float('nan')}]}
            path=Path(tmp)/'plan.json';path.write_text(json.dumps(plan))
            with patch.object(importlib.import_module('shorts_generator.stages.render.local'),'crop_highlights_local') as render:
                with self.assertRaises(ValueError):render_plan(path)
                render.assert_not_called()
