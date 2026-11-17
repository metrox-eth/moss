"""Render MOSS wiring cards with the approved Space Grotesk / v0.6 palette.

Run with Pillow installed. Outputs are connection lists, not representations
of connector pin order. Firmware pin assignments live in the wiring guide.
"""
from pathlib import Path
from functools import lru_cache
import json
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'images/wiring'
OUT.mkdir(parents=True, exist_ok=True)
FONT = ROOT / 'fonts/SpaceGrotesk.ttf'
STUDIO=(61,87,106); WHITE=(234,240,239); MINT=(108,248,199)
SALMON=(255,148,126); NAVY=(8,15,26)
W,H=1920,1080

@lru_cache(None)
def font(size,weight=500):
    f=ImageFont.truetype(str(FONT),size)
    f.set_variation_by_axes([weight])
    return f

def text(x,y,s,size=30,color=WHITE,weight=500):
    f=font(size,weight)
    assert x+d.textlength(s,font=f)<=1810,(s,size,x)
    d.text((x,y),s,font=f,fill=color,anchor='lt')

def wrap(x,y,s,size=30,width=1550,color=WHITE,weight=500,step=None):
    line='';step=step or round(size*1.35)
    for word in s.split():
        candidate=(line+' '+word).strip()
        if line and d.textlength(candidate,font=font(size,weight))>width:
            text(x,y,line,size,color,weight);y+=step;line=word
        else:line=candidate
    if line:text(x,y,line,size,color,weight);y+=step
    return y

def panel(x,y,w,h,title):
    d.rounded_rectangle((x,y,x+w,y+h),radius=20,fill=STUDIO,outline=(119,148,161),width=2)
    text(x+30,y+27,title,34,WHITE,600)

def wire(points,color=MINT,width=5):
    d.line(points,fill=color,width=width,joint='curve')
    for x,y in [points[0],points[-1]]:d.ellipse((x-7,y-7,x+7,y+7),fill=color)

def card(number,title,subtitle):
    global im,d
    im=Image.new('RGB',(W,H),STUDIO);d=ImageDraw.Draw(im)
    d.arc((730,-400,1170,40),5,178,fill=MINT,width=7)
    d.arc((-320,720,98,1138),225,420,fill=SALMON,width=7)
    d.arc((1888,600,2152,864),90,265,fill=MINT,width=6)
    # Original MOSS monogram and wordmark proportions.
    pts=[(7,24),(7,8),(11,8),(16,17),(21,8),(25,8),(25,24),(21,24),(21,15),(16,23),(11,15),(11,24)]
    d.polygon([(1658+(a-7)*1.55,70+(b-8)*1.55) for a,b in pts],fill=MINT)
    x=1704
    for char in 'MOSS':
        d.text((x,68),char,font=font(37,700),fill=WHITE,anchor='lt')
        x+=d.textlength(char,font=font(37,700))-37*.055
    d.ellipse((1822,69,1831,78),fill=SALMON)
    text(114,124,'WIRING / '+number,23,MINT,600)
    text(108,190,title,64,WHITE,600)
    wrap(114,280,subtitle,29,width=1690)

def save(name):
    p=OUT/name;im.save(p,optimize=True);return p

def connection_card(number,title,subtitle,left,right,rows,name):
    card(number,title,subtitle)
    panel(112,365,648,550,left);panel(1160,365,648,550,right)
    for i,(src,gpio,dst,note) in enumerate(rows):
        y=465+i*82
        text(150,y-8,src,35,MINT,600)
        if gpio:text(490,y-3,gpio,25,WHITE)
        text(1195,y-8,dst,35,MINT,600)
        if note:text(1195,y+32,note,22)
        wire([(760,y+10),(1160,y+10)],MINT if dst!='GND' else WHITE)
    return save(name)

paths=[]
card('01','The electronics','The computer connects to the track controller, arm adapter, sensors and audio.')
panel(112,405,440,440,'Onboard computer')
text(142,480,'USB host',32,MINT,600)
text(142,550,'Jetson / chosen option',28)
text(142,620,'Runs MOSS software',28)
for y,title,a,b in [(365,'Track control','QT Py → Cytron','Motors + encoders'),
                     (530,'Arm + gripper','Waveshare USB adapter','Serial-servo bus'),
                     (695,'Sensors + gamepad','USB camera, LiDAR, receiver','Depth camera on USB 3')]:
    panel(920,y,888,140,title);text(950,y+78,a,27,MINT,600);text(1390,y+78,b,22)
    wire([(552,y+70),(920,y+70)],MINT)
panel(920,860,888,140,'Speaker');text(950,938,'Jetson I2S → MAX98357A → speaker',27,MINT,600)
wire([(552,810),(730,810),(730,930),(920,930)],SALMON)
paths.append(save('01-overview.png'))

card('02','Rover power distribution','Four power branches share the protected battery-output negative.')
panel(112,365,420,170,'Protected 3S output');text(142,445,'Existing 15 A pack fuse',27,MINT,600)
panel(720,365,430,170,'Main switch');text(750,445,'Round KCD1-5-101EN',27,MINT,600)
panel(1420,365,388,170,'XT30 distribution');text(1450,445,'One in · four out',26,MINT,600)
wire([(532,410),(720,410)],MINT);wire([(1150,410),(1420,410)],MINT)
wire([(1600,535),(1600,620),(1629,620),(291,620)],MINT)
for x,title,detail in [(112,'Cytron MDD10A','Motor power'),(558,'Waveshare adapter','Servo power'),
                        (1004,'Computer','Jetson / Pi supply'),(1450,'Two 12 V fans','Connected in parallel')]:
    panel(x,735,358,160,title);text(x+30,816,detail,24)
    wire([(x+179,620),(x+179,735)],MINT)
    wire([(x+179,895),(x+179,965)],WHITE)
wire([(291,965),(1629,965)],WHITE)
# The negative rail runs around the left edge, avoiding a false junction.
wire([(150,535),(150,580),(90,580),(90,965),(291,965)],WHITE)
text(190,568,'+ after fuse and switch',27,MINT,600)
text(740,997,'Protected negative / GND',26,WHITE)
paths.append(save('02-power-distribution.png'))

paths.append(connection_card('03','QT Py to Cytron','Use the printed pin names on the BFF and the driver.',
    'QT Py / Terminal Block BFF','Cytron MDD10A',[
        ('A0','GPIO 18','PWM1','Left motor speed'),('A1','GPIO 17','DIR1','Left motor direction'),
        ('A2','GPIO 9','PWM2','Right motor speed'),('A3','GPIO 8','DIR2','Right motor direction'),
        ('GND','','GND','Signal ground')], '03-qtpy-cytron.png'))

card('04','Motors and encoders','Motor power and encoder power are separate. Identify wires by function, not colour.')
for x,title,channel,pa,pb in [(112,'Left track','Motor 1','SDA · GPIO 7','SCL · GPIO 6'),
                              (1000,'Right track','Motor 2','TX · GPIO 5','RX · GPIO 16')]:
    panel(x,365,808,590,title)
    rows=[('Motor leads (2)',channel+' outputs',MINT),('Encoder VCC','QT Py 3V / 3.3 V',SALMON),
          ('Encoder GND','GND',WHITE),('Encoder A',pa,MINT),('Encoder B',pb,MINT)]
    for i,(a,b,c) in enumerate(rows):
        y=474+i*92;text(x+25,y,a,29,c,600);text(x+395,y,b,27,WHITE)
        wire([(x+325,y+18),(x+375,y+18)],c)
        if i==0:wire([(x+325,y+32),(x+375,y+32)],c,width=3)
paths.append(save('04-motors-encoders.png'))

card('05','The two-wire track stop','Normally closed contact → QT Py input. This is a software stop for the tracks.')
panel(112,365,648,490,'Stop button · NC contact');panel(1160,365,648,490,'QT Py / BFF')
for y,a,b,note,c in [(525,'NC terminal A','SCK','GPIO 36',MINT),(705,'NC terminal B','GND','Ground',WHITE)]:
    text(150,y,a,34,c,600);text(1195,y,b,35,c,600);text(1410,y+5,note,27)
    wire([(760,y+18),(1160,y+18)],c)
wrap(114,922,'Press: tracks stop. Release: still stopped. clearstop: latch cleared, still disarmed.',29,width=1680)
paths.append(save('05-stop-button.png'))

card('06','Measure the rover voltage','STEMMA QT carries logic power and I2C. A separate wire senses the positive supply.')
panel(112,365,530,520,'QT Py · STEMMA QT');panel(950,365,430,520,'INA219');panel(1500,550,308,185,'XT30 rail')
for i,(a,b,c) in enumerate([('3.3 V','VCC',SALMON),('GND','GND',WHITE),('SDA1 · GPIO 41','SDA',MINT),('SCL1 · GPIO 40','SCL',MINT)]):
    y=475+i*90;text(147,y,a,29,c,600);text(985,y,b,30,c,600);wire([(642,y+15),(950,y+15)],c)
text(1180,610,'Vin−',31,SALMON,600);text(1530,625,'Switched +',28,SALMON,600)
wire([(1380,645),(1500,645)],SALMON)
text(1180,800,'Vin+ unused',25)
wrap(114,938,'Vin− is the positive-voltage sense input here. It is not battery negative.',30,width=1660)
paths.append(save('06-ina219-voltage.png'))

card('07','Speaker to Jetson','Physical numbers on the 40-pin Jetson header — not GPIO numbers.')
panel(112,365,590,560,'Jetson Orin Nano');panel(1020,365,430,560,'MAX98357A');panel(1600,510,208,290,'Speaker')
for i,(a,b,c) in enumerate([('Pin 2 · 5 V','VIN',SALMON),('Pin 6 · GND','GND',WHITE),
                           ('Pin 12 · clock','BCLK',MINT),('Pin 35 · frame','LRC',MINT),('Pin 40 · data out','DIN',MINT)]):
    y=470+i*85;text(145,y,a,31,c,600);text(1050,y,b,31,c,600);wire([(702,y+17),(1020,y+17)],c)
text(1330,550,'SPK+',25,MINT,600);text(1330,710,'SPK−',25,WHITE,600)
wire([(1450,570),(1600,570)],MINT);wire([(1450,730),(1600,730)],WHITE)
text(1630,638,'4 Ω',32,MINT,600)
wrap(114,966,'Connect the speaker across SPK+ and SPK−. Neither output goes to ground.',28,width=1670)
paths.append(save('07-jetson-speaker.png'))

manifest={'font':'Space Grotesk variable, explicit weights 500/600/700',
          'palette':{'STUDIO':'#3D576A','WHITE':'#EAF0EF','MINT':'#6CF8C7','SALMON':'#FF947E'},
          'canvas':[W,H],'files':[str(p.relative_to(ROOT)) for p in paths]}
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
sheet=Image.new('RGB',(1920,3*360),STUDIO)
for i,p in enumerate(paths):
    tile=Image.open(p);tile.thumbnail((640,360),Image.Resampling.LANCZOS)
    sheet.paste(tile,((i%3)*640,(i//3)*360))
sheet.save(OUT/'contact-sheet.jpg',quality=90)
print(json.dumps(manifest,indent=2))
