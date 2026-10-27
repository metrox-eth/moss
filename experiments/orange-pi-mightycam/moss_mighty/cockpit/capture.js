/* Local-only composition: a landscape video regardless of browser/sidebar width. */
'use strict';
let recorder=null,recordTimer=null,recordStart=0,recordChunks=[],recordStream=null;
const recordCanvas=document.createElement('canvas');recordCanvas.width=1920;recordCanvas.height=1080;
const recordContext=recordCanvas.getContext('2d');
// Keep the last decoded image while the next HTTP image is loading.
const cameraBuffers={};
for(const id of ['raw','detector']){
  const buffer=document.createElement('canvas');cameraBuffers[id]=buffer;
  const retain=()=>{const img=$(id);if(!img.naturalWidth)return;buffer.width=img.naturalWidth;buffer.height=img.naturalHeight;buffer.getContext('2d').drawImage(img,0,0);buffer.ready=true};
  $(id).addEventListener('load',retain);if($(id).complete&&$(id).naturalWidth)retain();
}
function caption(value,x,y,size=20,color=colors.white,weight=500){recordContext.fillStyle=color;recordContext.font=`${weight} ${size}px "Space Grotesk", sans-serif`;recordContext.fillText(value,x,y)}
function videoImage(id,x,y,w,h,label,detail,valid){
  const g=recordContext,img=cameraBuffers[id];g.fillStyle=colors.navy;g.fillRect(x,y,w,h);
  if(img.ready){const s=Math.max(w/img.width,h/img.height);g.save();g.beginPath();g.rect(x,y,w,h);g.clip();g.globalAlpha=valid?1:.2;g.drawImage(img,x+(w-img.width*s)/2,y+(h-img.height*s)/2,img.width*s,img.height*s);g.restore()}
  g.fillStyle='rgba(8,15,26,.8)';g.fillRect(x+12,y+12,Math.min(w-24,500),38);caption(label,x+24,y+38,19,colors.white,600);
  if(detail){g.fillStyle='rgba(8,15,26,.8)';g.fillRect(x+12,y+h-45,w-24,33);caption(detail,x+24,y+h-22,16,valid?colors.mint:colors.salmon)}
}
function composeRecording(){
  const g=recordContext;g.fillStyle=colors.studio;g.fillRect(0,0,1920,1080);
  const logo=$('wordmark');if(logo.complete&&logo.naturalWidth)g.drawImage(logo,48,40,160,160*logo.naturalHeight/logo.naturalWidth);
  caption('dimOS × $60 Orange Pi × $80 MightyCam',250,54,37,colors.white,600);caption('Zero 3W · 6 GB RAM · NPU',251,95,19,'#c3d2d7');caption(online?'LIVE':'OFFLINE',1775,96,18,online?colors.mint:colors.salmon,600);
  caption('CPU LOAD',1260,28,13,'#c3d2d7',600);
  (resources?.cpu?.cores||[]).forEach((c,i)=>{const x=1260+i*63,value=online?c.usage_percent:null;g.fillStyle='rgba(234,240,239,.12)';g.fillRect(x,35,43,35);g.fillStyle=colors.mint;if(value!=null)g.fillRect(x,70-35*value/100,43,35*value/100);caption(value==null?'—':Math.round(value)+'%',x,91,13,'#c3d2d7')});
  g.fillStyle='rgba(8,15,26,.12)';g.fillRect(48,130,1100,750);caption('LIVE TRAJECTORY',72,164,18,colors.mint,600);caption($('tracking').textContent,760,164,15,'#c3d2d7');
  g.save();g.translate(48,178);g.beginPath();g.rect(0,0,1100,650);g.clip();drawPath(g,1100,650,false);g.restore();
  if(!state?.trajectory?.length)caption('Move the camera to begin.',390,510,24,'#c3d2d7');
  caption('VIO path · 1 m grid',72,855,18,'#c3d2d7');caption($('position').textContent,650,855,18,'#c3d2d7');
  videoImage('raw',1172,130,700,363,'MIGHTYCAM · VIO CAMERA',online&&state?.image_age_s<2?'LIVE':'WAITING',online&&state?.image_age_s<2);
  videoImage('detector',1172,517,700,363,'YOLO · '+$('backend').textContent,$('detected').textContent,online&&vision?.active);
  g.strokeStyle='#6A8797';g.beginPath();g.moveTo(48,906);g.lineTo(1872,906);g.stroke();
  const metrics=[['MEMORY USED',$('ram').textContent+' '+$('ram-total').textContent,48],['NPU INFERENCE',$('npu-ms').textContent+' ms',590],['DETECTION RATE',$('fps').textContent+' fps',1050],['TEMPERATURE',$('temperature').textContent+' °C',1510]];
  for(const [label,value,x] of metrics){caption(label,x,940,17,'#c3d2d7',600);caption(online?value:'—',x,998,45,label==='NPU INFERENCE'?colors.mint:colors.white)}
  caption($('stack').textContent,48,1055,17,colors.mint);caption('Live camera + VIO + YOLO · no obstacle map',1300,1055,17,'#c3d2d7');
}
function stopRecording(){if(recorder?.state==='recording')recorder.stop()}
$('record').onclick=async()=>{
  if(recorder?.state==='recording'){stopRecording();return}
  if(!online){text('notice','Connect to the Orange Pi before recording.');return}
  try{
    await document.fonts.ready;
    const type=['video/mp4;codecs=avc1.42001E','video/mp4','video/webm;codecs=vp9','video/webm;codecs=vp8','video/webm'].find(t=>MediaRecorder.isTypeSupported(t));
    if(!type)throw Error('No supported video encoder');
    composeRecording();recordStream=recordCanvas.captureStream(20);recordChunks=[];
    recorder=new MediaRecorder(recordStream,{mimeType:type,videoBitsPerSecond:6000000});
    recorder.ondataavailable=e=>{if(e.data.size)recordChunks.push(e.data)};
    recorder.onstop=()=>{clearInterval(recordTimer);recordStream.getTracks().forEach(t=>t.stop());const blob=new Blob(recordChunks,{type}),url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download='MOSS-OrangePi-MightyCam-'+new Date().toISOString().replace(/[:.]/g,'-')+(type.includes('mp4')?'.mp4':'.webm');document.body.appendChild(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),60000);$('record').classList.remove('recording');text('record','Record');text('notice','Video saved · 1920 × 1080 · no audio');recordChunks=[]};
    recorder.onerror=()=>{text('notice','Recording failed. Use your screen recorder.');stopRecording()};
    recordStart=performance.now();recorder.start(1000);$('record').classList.add('recording');
    recordTimer=setInterval(()=>{composeRecording();const elapsed=(performance.now()-recordStart)/1000;text('record','Stop · '+Math.floor(elapsed)+'s');if(elapsed>=30)stopRecording()},50);
    text('notice','Recording locally · stops after 30 seconds');
  }catch(e){recordStream?.getTracks().forEach(t=>t.stop());text('notice','Recording unavailable here. Open this page in Chrome.');text('record','Record');$('record').classList.remove('recording')}
};
if(!window.MediaRecorder||!recordCanvas.captureStream){$('record').disabled=true;$('record').title='Use Chrome or a screen recorder'}
