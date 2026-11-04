"""Verify bitmap button rectangles match the installed client, including edges."""
from pathlib import Path
import re
root=Path(__file__).resolve().parents[1]
java=(root/'android/src/com/bpmct/trmnl_nook_simple_touch/DisplayActivity.java').read_text()
server=(root/'nook_casa/server.py').read_text()
drawn=[tuple(map(int,m)) for m in re.findall(r'button\(\((\d+),(\d+),(\d+),(\d+)\)',server)]
hitboxes=[tuple(map(int,m)) for m in re.findall(r'return new int\[\]\{(\d+),(\d+),(\d+),(\d+)\}',java)]
assert len(drawn)==3 and set(drawn)==set(hitboxes),(drawn,hitboxes)
assert 'ImageView.ScaleType.FIT_XY' in java
assert 'canvas.scale(getWidth()/600f, getHeight()/800f)' in java
assert 'event.getX()*600f/Math.max(1,v.getWidth())' in java
assert 'event.getY()*800f/Math.max(1,v.getHeight())' in java
assert 'x>=b[0] && x<=b[2] && y>=b[1] && y<=b[3]' in java
print('PASS: all three bitmap, touch and pressed-feedback rectangles match; scaling and inclusive edges agree')
