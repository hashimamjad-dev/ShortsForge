import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from pathlib import Path
import json, subprocess
from shorts_generator.stages.transcribe.whisper import _transcript_cache_path
from shorts_generator.stages.render.local.subtitles import word_captions,burn_subtitles
root=Path('output/render-smoke').resolve(); root.mkdir(parents=True, exist_ok=True)
source=root/'source.mp4'
subprocess.run(['ffmpeg','-y','-v','error','-f','lavfi','-i','color=c=0x18243a:s=360x640:d=2','-f','lavfi','-i','sine=frequency=440:duration=2','-c:v','libx264','-c:a','aac',str(source)],check=True)
cache=_transcript_cache_path(str(source)).with_suffix('.json')
cache.write_text(json.dumps({'transcript':{'segments':[{'words':[{'start':i*.35,'end':(i+1)*.35,'word':w} for i,w in enumerate(['Build','something','that','actually','works.'])]}]}}))
ass=root/'captions.ass'; word_captions(str(source),str(ass),0,2,'9:16')
burn_subtitles(str(source),str(ass),str(root/'captioned.mp4'),'9:16')
subprocess.run(['ffmpeg','-y','-v','error','-ss','0.9','-i',str(root/'captioned.mp4'),'-frames:v','1',str(root/'preview.png')],check=True)
print('FFmpeg caption burn succeeded:',root/'captioned.mp4')
