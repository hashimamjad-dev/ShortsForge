import json
import unittest
from shorts_generator.stages.highlights.editorial import sentences, select_clips

class EditorialTests(unittest.TestCase):
    def test_sentence_reconstruction_crosses_whisper_segments(self):
        t={'segments':[{'words':[{'start':0,'end':1,'word':'A complete'}]},
                       {'words':[{'start':1,'end':3,'word':'thought.'}]}]}
        self.assertEqual(sentences(t),[{'start':0,'end':3,'text':'A complete thought.'}])

    def test_ids_determine_exact_times(self):
        t={'segments':[{'start':i*10,'end':i*10+10,'text':f'Sentence {i}.'} for i in range(5)]}
        result=select_clips(t,1,lambda _:json.dumps({'clips':[{'start_id':1,'end_id':3,'score':90,'reason':'Complete explanation'}]}))
        self.assertEqual((result[0]['start_time'],result[0]['end_time']),(10,40))
        self.assertEqual(result[0]['hook_sentence'],'Sentence 1.')

    def test_invalid_ids_are_retried_then_fail(self):
        t={'segments':[{'start':0,'end':30,'text':'A sentence.'}]}
        calls=[]
        def bad(prompt):
            calls.append(prompt)
            return '{"clips":[{"start_id":0,"end_id":999,"score":90}]}'
        with self.assertRaises(RuntimeError): select_clips(t,1,bad)
        self.assertEqual(len(calls),3)

    def test_no_suitable_passage_is_not_fabricated(self):
        t={'segments':[{'start':0,'end':5,'text':'Hello.'}]}
        self.assertEqual(select_clips(t,1,lambda _:'{"clips":[]}'),[])

class LongWindowTests(unittest.TestCase):
    def test_every_sentence_is_covered_in_long_recording(self):
        import re
        t={'segments':[{'start':i*10.,'end':(i+1)*10.,'text':f'Sentence {i}.'} for i in range(360)]}
        seen=set(); windows=[]
        def llm(prompt):
            ids=[int(x) for x in re.findall(r'^ID (\d+):',prompt,re.M)]
            seen.update(ids); windows.append(ids)
            return json.dumps({'clips':[{'start_id':ids[0],'end_id':ids[2],'score':80}]})
        clips=select_clips(t,3,llm)
        self.assertEqual(seen,set(range(360)))
        self.assertGreater(len(windows),5)
        self.assertTrue(all(len(w)<70 for w in windows))
        self.assertTrue(all(c['end_time']<=3600 for c in clips))
        self.assertTrue(all(set(a)&set(b) for a,b in zip(windows,windows[1:])))
