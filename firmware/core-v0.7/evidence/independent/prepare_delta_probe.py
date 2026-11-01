"""Extract the two reviewed USB functions verbatim for the host delta probe."""
from pathlib import Path
import argparse

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('firmware_directory',type=Path)
args=parser.parse_args()
source=(args.firmware_directory/'MOSS_CORE_V07.ino').read_text()
bodies=[]
for declaration in ['void serviceTx()','bool usbOpen()']:
    begin=source.index(declaration)
    pos=source.index('{',begin)+1
    depth=1
    while depth:
        if source[pos]=='{':depth+=1
        elif source[pos]=='}':depth-=1
        pos+=1
    bodies.append(source[begin:pos])
(Path(__file__).resolve().parent/'usb_functions.inc').write_text(
    '// Verbatim reviewed function bodies from MOSS_CORE_V07.ino\n'
    +'\n\n'.join(bodies)+'\n')
