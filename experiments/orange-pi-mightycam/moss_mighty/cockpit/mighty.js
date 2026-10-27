'use strict';
const $=id=>document.getElementById(id),text=(id,value)=>{$(id).textContent=value};
const map=$('map'),mapContext=map.getContext('2d');
let state=null,resources=null,vision=null,online=false,is3d=true,azimuth=.65,elevation=.65,zoom=1,drag=null;
let rateHistory=[],detectionRate=0;
let freshRoute=null;
const colors={mint:'#6CF8C7',salmon:'#FF947E',white:'#EAF0EF',navy:'#080F1A',studio:'#3D576A'};
function project(p){
  if(!is3d)return [p[0],p[1]];
  const a=p[0]*Math.cos(azimuth)+p[1]*Math.sin(azimuth),b=-p[0]*Math.sin(azimuth)+p[1]*Math.cos(azimuth);
  return [a,b*Math.sin(elevation)+p[2]*Math.cos(elevation)];
}
function drawPath(ctx,w,h,clear=true){
  if(clear)ctx.clearRect(0,0,w,h);
  const points=state?.trajectory||[],all=points.length?points:[[0,0,0]],view=all.map(project);
  const xs=view.map(p=>p[0]),ys=view.map(p=>p[1]),minx=Math.min(...xs),maxx=Math.max(...xs),miny=Math.min(...ys),maxy=Math.max(...ys);
  const cx=(minx+maxx)/2,cy=(miny+maxy)/2,scale=Math.min((w-70)/Math.max(3,maxx-minx),(h-100)/Math.max(3,maxy-miny))*zoom;
  const screen=p=>{const q=project(p);return [w/2+(q[0]-cx)*scale,h/2+12-(q[1]-cy)*scale]};
  const center=all.at(-1),extent=Math.min(60,Math.ceil(Math.max(5,maxx-minx,maxy-miny)+3));
  ctx.lineWidth=1;
  for(let k=-extent;k<=extent;k++){
    ctx.strokeStyle=k%5===0?'rgba(234,240,239,.16)':'rgba(234,240,239,.065)';
    for(let axis=0;axis<2;axis++){
      let a=[Math.floor(center[0])-extent,Math.floor(center[1])+k,0],b=[Math.floor(center[0])+extent,Math.floor(center[1])+k,0];
      if(axis){a=[Math.floor(center[0])+k,Math.floor(center[1])-extent,0];b=[Math.floor(center[0])+k,Math.floor(center[1])+extent,0]}
      ctx.beginPath();ctx.moveTo(...screen(a));ctx.lineTo(...screen(b));ctx.stroke();
    }
  }
  if(!points.length)return;
  const active=online&&state.tracking;
  ctx.beginPath();points.forEach((p,i)=>i?ctx.lineTo(...screen(p)):ctx.moveTo(...screen(p)));
  ctx.strokeStyle=active?colors.mint:'rgba(108,248,199,.4)';ctx.lineWidth=3;ctx.lineJoin='round';ctx.lineCap='round';
  ctx.shadowColor=colors.mint;ctx.shadowBlur=active?8:0;ctx.stroke();ctx.shadowBlur=0;
  const first=screen(points[0]),last=screen(points.at(-1));
  ctx.strokeStyle=colors.salmon;ctx.lineWidth=2;ctx.strokeRect(first[0]-5,first[1]-5,10,10);
  ctx.fillStyle=active?colors.mint:colors.salmon;ctx.beginPath();ctx.arc(last[0],last[1],6,0,Math.PI*2);ctx.fill();
  if(state.pose){
    const [x,y,z,a]=state.pose.orientation_xyzw,p=state.pose.position_m;
    const forward=[1-2*(y*y+z*z),2*(x*y+a*z),2*(x*z-a*y)];
    const target=screen(p.map((v,i)=>v+forward[i]*.4)),angle=Math.atan2(target[1]-last[1],target[0]-last[0]);
    ctx.save();ctx.translate(...last);ctx.rotate(angle);ctx.beginPath();ctx.moveTo(0,0);ctx.lineTo(32,-13);ctx.lineTo(32,13);ctx.closePath();
    ctx.fillStyle=active?'rgba(108,248,199,.18)':'rgba(255,148,126,.12)';ctx.fill();ctx.strokeStyle=active?colors.mint:colors.salmon;ctx.lineWidth=1;ctx.stroke();ctx.restore();
  }
}
function draw(){const d=window.devicePixelRatio||1,w=map.clientWidth,h=map.clientHeight;if(!w||!h)return;map.width=w*d;map.height=h*d;mapContext.setTransform(d,0,0,d,0,0);drawPath(mapContext,w,h);$('map-empty').hidden=!!state?.trajectory?.length;}
async function get(path){const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),3000);try{const response=await fetch(path,{cache:'no-store',signal:controller.signal});if(!response.ok)throw Error(response.status);return await response.json()}finally{clearTimeout(timer)}}
function update(){
  document.body.classList.toggle('offline',!online);text('connection',online?'LIVE':'OFFLINE');$('connection').className='status '+(online?'live':'offline');
  const labels={0:'TRACKING STOPPED',1:'INITIALIZING',2:'6DOF OUTPUT',3:'TRACKING DEGRADED',4:'TRACKING LOST',5:'LOW LIGHT',6:'RECOVERING'};
  text('tracking',!online?'CONNECTION LOST':(labels[state?.vio_state?.state]||'WAITING FOR CAMERA'));
  text('map-empty',state?.tracking?'Move the camera to begin.':state?.vio_state?.state===0?'VIO is stopped.':state?.vio_state?.state===1?'Initializing — keep the camera still.':'Position unavailable.');
  const p=state?.pose?.position_m;text('position',p?`X ${p[0].toFixed(2)} · Y ${p[1].toFixed(2)} · Z ${p[2].toFixed(2)} m`:'X — · Y — · Z —');
  const raw=online&&state?.image_age_s!==null&&state?.image_age_s<2,det=online&&vision?.active;
  $('raw-wrap').classList.toggle('stale',!raw);$('detector-wrap').classList.toggle('stale',!det);
  text('raw-state',raw?'LIVE':'WAITING');text('backend',vision?.backend?.includes('NPU')?'A733 NPU':vision?.backend||'ON-DEVICE');
  text('detected',det?((vision.detections||[]).slice(0,3).map(b=>`${b.label} ${Math.round(b.confidence*100)}%`).join(' · ')||'NO OBJECTS DETECTED'):'WAITING');
  const m=resources?.memory;
  if(m){text('ram',(m.used_mib/1024).toFixed(2));text('ram-total','/ '+(m.total_mib/1024).toFixed(1)+' GB');$('ram-bar').style.width=m.used_mib/m.total_mib*100+'%';text('swap','Swap '+m.swap_used_mib.toFixed(0)+' MB')}
  text('temperature',online&&resources?.temperature_c!=null?resources.temperature_c.toFixed(0):'—');
  text('npu-ms',det&&vision.npu_network_ms!=null?vision.npu_network_ms.toFixed(0):'—');text('fps',det?detectionRate.toFixed(1):'—');
  text('pipeline',det&&vision.median_ms?Math.round(vision.median_ms)+' ms total pipeline':'Live camera pipeline');
  const cores=resources?.cpu?.cores||[];
  if($('cpu-cores').children.length!==cores.length){
    $('cpu-cores').replaceChildren(...cores.map(c=>{const el=document.createElement('div');el.className='core';el.innerHTML='<div class="core-bar"><i></i></div><span>—</span>';el.title='Core '+c.id;return el}));
  }
  cores.forEach((c,i)=>{const el=$('cpu-cores').children[i],value=online?c.usage_percent:null;el.querySelector('i').style.height=(value??0)+'%';el.querySelector('span').textContent=value==null?'—':Math.round(value)+'%';el.setAttribute('aria-label','Core '+c.id+': '+(value==null?'unavailable':value+' percent'));});
  const full=resources?.profile==='full-bench'||resources?.services?.['moss-full-bench']?.running;
  text('stack',full?'dimOS + MOSS · rover I/O simulated':'dimOS + MOSS · perception');draw();
}
async function poll(){
  try{
    const result=await Promise.all([get('/status'),get('/resources'),get('/detections')]);[state,resources,vision]=result;online=true;
    if(freshRoute){
      const p=state.pose;
      if(p){
        if(!freshRoute.origin)freshRoute.origin=p.position_m.slice();
        const position=p.position_m.map((v,i)=>v-freshRoute.origin[i]);
        if(state.tracking&&p.received_at!==freshRoute.last){freshRoute.points.push(position);freshRoute.last=p.received_at;}
        state.pose={...p,position_m:position};
      }
      state.trajectory=freshRoute.points;
    }
    const now=Date.now(),n=vision.frames_processed||0;
    if(rateHistory.length&&n<rateHistory.at(-1).n)rateHistory=[];
    rateHistory.push({t:now,n});rateHistory=rateHistory.filter(x=>now-x.t<5000);
    detectionRate=rateHistory.length>1?(n-rateHistory[0].n)/((now-rateHistory[0].t)/1000):0;
    if(state.image_age_s!=null&&state.image_age_s<2)$('raw').src='/image.jpg?t='+now;
    if(vision.active)$('detector').src='/vision.jpg?t='+now;
  }catch(error){online=false;detectionRate=0}
  update();setTimeout(poll,350);
}
$('view2').onclick=()=>{is3d=false;$('view2').classList.add('selected');$('view3').classList.remove('selected');draw()};
$('view3').onclick=()=>{is3d=true;$('view3').classList.add('selected');$('view2').classList.remove('selected');draw()};
$('fit').onclick=()=>{zoom=1;draw()};
const resetPath=document.createElement('button');resetPath.id='reset-path';resetPath.textContent='Reset path';resetPath.title='Clear the displayed route and start at zero without restarting VIO';
document.querySelector('.view-tools').appendChild(resetPath);
resetPath.onclick=()=>{
  const relative=state?.pose?.position_m;
  const origin=relative?(freshRoute?.origin?relative.map((v,i)=>v+freshRoute.origin[i]):relative.slice()):null;
  freshRoute={origin,points:[],last:state?.pose?.received_at};zoom=1;
  if(state){state.trajectory=[];if(state.pose)state.pose={...state.pose,position_m:[0,0,0]};}
  update();
};
$('fullscreen').onclick=async()=>{try{if(document.fullscreenElement)await document.exitFullscreen();else await document.documentElement.requestFullscreen()}catch(e){text('notice','Use the browser fullscreen control.')}};
map.onpointerdown=e=>{drag=[e.clientX,e.clientY];map.setPointerCapture(e.pointerId)};
map.onpointermove=e=>{if(drag&&is3d){azimuth+=(e.clientX-drag[0])*.008;elevation=Math.max(.12,Math.min(1.5,elevation+(e.clientY-drag[1])*.006));drag=[e.clientX,e.clientY];draw()}};
map.onpointerup=map.onpointercancel=()=>drag=null;
map.addEventListener('wheel',e=>{e.preventDefault();zoom=Math.max(.3,Math.min(5,zoom*Math.exp(-e.deltaY*.001)));draw()},{passive:false});
new ResizeObserver(draw).observe(map);poll();
