import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';

const home=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const defaults=JSON.parse(fs.readFileSync(path.join(home,'assets/defaults.json'),'utf8'));
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const num=(n,label,min=0)=>{if(!Number.isFinite(n)||n<min)throw Error(label+' must be a finite number >= '+min);return n;};
const requireText=(s,label)=>{if(typeof s!=='string'||!s.trim())throw Error(label+' requires text');};
const round=n=>Math.round(n*1000000)/1000000;
const merge=(a,b={})=>Object.fromEntries(Object.entries({...a,...b}).map(([k,v])=>[k,v&&typeof v==='object'&&!Array.isArray(v)?merge(a[k]||{},v):v]));
const segments=x=>typeof x==='string'?[{text:x}]:x;
function rich(x,chars=false){
  return segments(x).map(s=>{
    const text=chars?Array.from(s.text).map(c=>'<span class="char">'+esc(c)+'</span>').join(''):esc(s.text);
    return s.accent?'<span class="accent">'+text+'</span>':text;
  }).join('');
}
function checkRich(x,label){
  if(!Array.isArray(segments(x))||!segments(x).length)throw Error(label+' requires text segments');
  for(const s of segments(x)){requireText(s.text,label);if(s.accent!==undefined&&typeof s.accent!=='boolean')throw Error(label+' accent must be boolean');}
}
export function validate(config,base='.',checkFiles=true){
  if(config.version!==1)throw Error('version must be 1');
  if(!Array.isArray(config.scenes)||!config.scenes.length)throw Error('scenes required');
  const d=merge(defaults,config.design);
  if(d.frame.width!==1080||d.frame.height!==1440||d.frame.fps!==30)throw Error('This renderer supports 1080x1440 30fps; adapt layout before changing frame.');
  if(!/^[\p{L}\p{N} _-]+$/u.test(d.fontFamily))throw Error('Invalid font family');
  for(const [k,v] of Object.entries(d.type))num(v,'type.'+k,0.001);
  for(const [k,v] of Object.entries(d.motion))num(v,'motion.'+k,k==='qHold'?0:0.01);
  if(d.motion.title<0.12)throw Error('title duration must be >= .12');
  num(d.colors.angle,'gradient angle');if(d.colors.angle>360)throw Error('angle > 360');
  if(d.colors.gradient.length!==3)throw Error('Use three gradient stops');
  for(const c of [...d.colors.gradient,d.colors.ink,d.colors.muted,d.colors.cardInk])if(!/^#[0-9a-f]{6}$/i.test(c))throw Error('Colors require #RRGGBB');
  const media=config.media||{};
  for(const [id,m] of Object.entries(media)){
    if(!/^[a-zA-Z][\w-]*$/.test(id))throw Error('Invalid media ID '+id);
    requireText(m.path,'media path');
    if(!['video','audio','image'].includes(m.kind))throw Error('media kind required');
    if(checkFiles&&!fs.existsSync(path.resolve(base,m.path)))throw Error('Missing media '+id+': '+m.path);
    if(m.in!==undefined)num(m.in,'media.in');
    if(m.out!==undefined){num(m.out,'media.out');if(m.out<=(m.in||0))throw Error('source out must exceed in');}
    if(m.speed!==undefined){num(m.speed,'speed',0.5);if(m.speed>2)throw Error('Prepare extreme speeds separately');}
    if(m.kind==='image'&&(m.in!==undefined||m.out!==undefined||m.speed!==undefined))throw Error('Image cannot have trim/speed');
  }
  const use=(id,kind)=>{if(!media[id]||!kind.includes(media[id].kind))throw Error('Missing or wrong-kind media '+id);};
  let t=0, previous=null;
  const ids=new Set(),questionChapters=new Set(),timeline=[];
  for(const s of config.scenes){
    if(!/^[a-z][a-z0-9-]*$/.test(s.id)||ids.has(s.id))throw Error('Unique safe scene IDs required');
    ids.add(s.id);
    let duration=s.duration;
    if(s.type==='theme'){
      if(previous?.type==='theme')throw Error('Consecutive theme scenes are unsupported');
      use(s.portrait,['image']);requireText(s.name,'name');requireText(s.role,'role');
      if(s.title?.length!==2||s.topics?.length!==3)throw Error('Theme requires two title lines and three topic groups');
      s.title.forEach(x=>checkRich(x,'title'));s.topics.forEach(x=>{if(!Array.isArray(x)||!x.length||x.length>2)throw Error('Topic needs 1-2 lines');x.forEach(y=>requireText(y,'topic'));});
      if(s.outline){requireText(s.outline.viewBox,'outline viewBox');if(!/^\d+(?:\.\d+)?(?:\s+\d+(?:\.\d+)?){3}$/.test(s.outline.viewBox))throw Error('Invalid viewBox');for(const p of s.outline.paths)if(!/^[MmLlHhVvCcSsQqTtAaZz0-9.,eE+\s-]+$/.test(p))throw Error('Invalid outline path');}
      duration=0.04+d.motion.person+d.motion.title+3*d.motion.bubble;
    }else if(s.type==='question'){
      requireText(s.label,'question label');requireText(s.context,'question context');
      if(s.lines?.length!==2)throw Error('Question requires two complete question lines');
      s.lines.forEach(x=>checkRich(x,'question'));
      if(s.chapter){if(questionChapters.has(s.chapter))throw Error('One Q per chapter');questionChapters.add(s.chapter);}
      const hold=s.hold??d.motion.qHold;num(hold,'Q hold');
      duration=d.motion.expand+d.motion.qLine+2*d.motion.qStagger+hold;
      if(s.fromTopic!==undefined&&(!Number.isInteger(s.fromTopic)||s.fromTopic<0||s.fromTopic>2||previous?.type!=='theme'))throw Error('fromTopic needs preceding theme and index 0-2');
    }else if(s.type==='quote'){
      if(s.variant!=='climax')use(s.media,['video']);
      if(s.media)use(s.media,['video','audio']);
      if(!['standard','compact','impact','climax','risk',undefined].includes(s.variant))throw Error('Unknown quote variant');
      if(s.variant==='risk'){if(s.rows?.length!==2)throw Error('Risk requires two rows');s.rows.forEach(r=>{requireText(r.label,'risk label');checkRich(r.value,'risk value');});}
      else{if(!s.lines?.length||s.lines.length>2)throw Error('Quote requires 1-2 lines');s.lines.forEach(x=>checkRich(x,'quote'));}
      if(s.kicker!==undefined)requireText(s.kicker,'kicker');
      num(s.top??720,'quote top');if((s.top??720)>1100)throw Error('Quote top beyond safe area');
      if(s.align&&!['left','right'].includes(s.align))throw Error('align must be left/right');
    }else if(s.type==='answer'){
      use(s.media,['video']);
      if(s.headline?.length!==2)throw Error('Answer requires two headline lines');s.headline.forEach(x=>checkRich(x,'headline'));
      if(!Array.isArray(s.captions)||!s.captions.length)throw Error('Answer captions required');
      let last=0;for(const c of s.captions){num(c.start,'caption start');num(c.end,'caption end');requireText(c.text,'caption');if(c.start<last||c.end<=c.start||c.end>s.duration)throw Error('Captions overlap or exceed answer');last=c.end;}
      for(const e of s.evidence||[]){use(e.media,['image','video']);requireText(e.evidenceId,'evidence ID');num(e.start,'evidence start');num(e.end,'evidence end');if(e.end<=e.start||e.end>s.duration)throw Error('Evidence outside answer');}
    }else if(s.type==='outro'){
      if(s.lines?.length!==2)throw Error('Outro requires two lines');s.lines.forEach(x=>checkRich(x,'outro'));
    }else throw Error('Unsupported scene type '+s.type);
    num(duration,'scene duration',0.1);
    if(s.volume!==undefined){num(s.volume,'volume');if(s.volume>1)throw Error('volume must be 0-1; normalize source for gain');}
    if(s.objectPosition&&!/^\d+(?:\.\d+)?% \d+(?:\.\d+)?%$/.test(s.objectPosition))throw Error('objectPosition requires two percentages');
    timeline.push({...s,start:round(t),duration:round(duration)});t+=duration;previous=s;
  }
  for(const a of config.audio||[]){use(a.media,['audio','video']);num(a.start,'audio start');num(a.duration,'audio duration',0.01);num(a.volume,'audio volume');if(a.volume>1||a.start+a.duration>t+0.00001)throw Error('Audio bounds invalid');}
  return {design:d,timeline,duration:round(t)};
}
function probe(p){
  return JSON.parse(execFileSync('ffprobe',['-v','error','-show_entries','format=duration:stream=codec_type','-of','json',p],{encoding:'utf8'}));
}
function mediaPlan(config,base,timeline){
  const plan={};
  for(const [id,m] of Object.entries(config.media||{})){
    const p=path.resolve(base,m.path);
    if(m.kind==='image'){plan[id]={...m,path:p};continue;}
    const info=probe(p),dur=Number(info.format?.duration);
    if(!Number.isFinite(dur))throw Error('Cannot determine media duration '+id);
    const end=m.out??dur,start=m.in??0,rate=m.speed??1;
    if(end>dur+0.04||start>=end)throw Error('Source trim exceeds media '+id);
    plan[id]={...m,path:p,in:start,out:end,speed:rate,duration:(end-start)/rate,audio:info.streams.some(s=>s.codec_type==='audio')};
  }
  for(const s of timeline){
    if(s.media&&plan[s.media].kind!=='image'){
      if(plan[s.media].duration+0.034<s.duration)throw Error('Media too short for '+s.id);
      if(['quote','answer'].includes(s.type)&&!plan[s.media].audio)throw Error('Speech media has no audio: '+s.id);
    }
    for(const e of s.evidence||[])if(plan[e.media].kind==='video'&&plan[e.media].duration+0.034<e.end-e.start)throw Error('Evidence video too short');
  }
  for(const a of config.audio||[])if(!plan[a.media].audio||plan[a.media].duration+0.034<a.duration)throw Error('Audio bed too short or absent');
  return plan;
}
function materialize(plan,out){
  fs.mkdirSync(path.join(out,'assets/media'),{recursive:true});
  const result={};
  for(const [id,m] of Object.entries(plan)){
    const digest=crypto.createHash('sha256').update(JSON.stringify(m)).digest('hex').slice(0,10);
    const ext=m.kind==='image'?path.extname(m.path):(m.kind==='audio'?'.m4a':'.mp4');
    const rel='assets/media/'+id+'-'+digest+ext,dest=path.join(out,rel);
    if(m.kind==='image'||(m.in===0&&m.speed===1&&m.out===undefined)){fs.copyFileSync(m.path,dest);}
    else{
      const args=['-v','error','-nostdin','-ss',String(m.in),'-t',String(m.out-m.in),'-i',m.path];
      if(m.kind==='video')args.push('-map','0:v:0','-vf','setpts=PTS/'+m.speed+',scale=trunc(iw/2)*2:trunc(ih/2)*2','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-r','30');
      else args.push('-vn');
      if(m.audio)args.push('-map','0:a:0','-af','atempo='+m.speed,'-c:a','aac','-b:a','192k');
      else args.push('-an');
      args.push('-movflags','+faststart',dest);
      execFileSync('ffmpeg',args,{stdio:'pipe'});
    }
    result[id]=rel;
  }
  return result;
}
function style(d){
  const g='linear-gradient('+d.colors.angle+'deg,'+d.colors.gradient[0]+' 0%,'+d.colors.gradient[1]+' 50%,'+d.colors.gradient[2]+' 100%)';
  const t=d.type;
  return ':root{--ink:'+d.colors.ink+';--muted:'+d.colors.muted+';--card-ink:'+d.colors.cardInk+';--brand-gradient:'+g+';--display-tracking:'+t.tracking+'em;--display-leading:'+t.leading+';--display-gap:'+t.lineGap+'px;--body-tracking:'+t.bodyTracking+'em;--body-leading:'+t.bodyLeading+';--quote-label-size:'+t.quoteSmall+'px;}'+
  'body{font-family:"'+d.fontFamily+'","Microsoft YaHei",sans-serif;}'+Object.entries({'.hero':t.quote,'.hero.compact':t.compact,'.hero.impact':t.impact,'.quote-climax .hero':t.climax,'.theme-title':t.theme,'.bubble-copy':t.topic,'.bubble-copy-scenes':t.topicScenes,'.theme-name':t.name,'.theme-role':t.role,'.q-heading':t.qLabel,'.q-context':t.qContext,'.q-question':t.qText,'.answer-head':t.answer,'.caption-copy':t.caption}).map(([sel,size])=>sel+'{font-size:'+size+'px;}').join('');
}
export function compose(config,prepared){
  const {design:d,timeline,duration}=validate(config,'.',false),html=[],anim=[],cues=[];
  const tween=(sel,vars,time)=>anim.push('tl.from('+JSON.stringify(sel)+','+JSON.stringify(vars)+','+round(time)+');');
  const clip=(id,cls,start,dur,inner,attrs='')=>'<section id="'+id+'" class="clip '+cls+'" data-start="'+round(start)+'" data-duration="'+round(dur)+'" '+attrs+'>'+inner+'</section>';
  const media=(id,asset,start,dur,cls,extra='')=>'<video id="'+id+'" class="clip '+cls+'" src="'+esc(prepared[asset])+'" data-start="'+round(start)+'" data-duration="'+round(dur)+'" muted playsinline '+extra+'></video>';
  const audio=(id,asset,start,dur,volume=1)=>'<audio id="'+id+'" src="'+esc(prepared[asset])+'" data-start="'+round(start)+'" data-duration="'+round(dur)+'" data-volume="'+volume+'"></audio>';
  const rad=d.colors.angle*Math.PI/180;
  const grad=id=>'<defs><linearGradient id="'+id+'" x1="'+(.5-.5*Math.sin(rad))+'" y1="'+(.5+.5*Math.cos(rad))+'" x2="'+(.5+.5*Math.sin(rad))+'" y2="'+(.5-.5*Math.cos(rad))+'">'+d.colors.gradient.map((c,i)=>'<stop offset="'+i/2+'" stop-color="'+c+'"/>').join('')+'</linearGradient></defs>';
  const glyphTitle=lines=>lines.map(x=>'<span class="type-line">'+rich(x,true)+'</span>').join('');
  const rowText=lines=>lines.map(x=>'<span>'+rich(x)+'</span>').join('');
  for(let i=0;i<timeline.length;i++){
    const s=timeline[i],id=s.id,t=s.start,sel='#'+id;
    if(s.type==='quote'){
      if(s.media){if(s.variant!=='climax')html.push(media(id+'-video',s.media,t,s.duration,'quote-video','style="object-position:'+esc(s.objectPosition||'50% 50%')+'"'));
        html.push(audio(id+'-voice',s.media,t,s.duration,s.volume??1));}
      let inner='';
      if(s.variant==='risk')inner='<div class="risk-grid">'+s.rows.map(r=>'<div class="risk-row"><span class="risk-label">'+esc(r.label)+'</span><strong class="risk-value">'+rich(r.value)+'</strong></div>').join('')+'</div>';
      else inner=(s.kicker?'<div class="beat-kicker">'+esc(s.kicker)+'</div>':'')+'<div class="hero '+(s.variant==='climax'?'centered':esc(s.variant||''))+'">'+s.lines.map(x=>'<span class="line-box"><span class="line-text">'+rich(x)+'</span></span>').join('')+'</div>';
      html.push(clip(id,'beat '+(s.variant==='climax'?'quote-climax':''),t,s.duration,'<div class="beat-content" style="'+(s.variant==='climax'?'':'padding-top:'+(s.top??720)+'px;')+'align-items:'+(s.align==='right'?'flex-end':'flex-start')+'">'+inner+'</div>'));
      if(s.kicker)tween(sel+' .beat-kicker',{opacity:0,x:-22,duration:.16,ease:'power3.out'},t+.01);
      tween(sel+(s.variant==='risk'?' .risk-row':' .line-box'),{scaleX:0,transformOrigin:'left center',duration:.18,stagger:.055,ease:'power4.out'},t+.015);
      tween(sel+(s.variant==='risk'?' .risk-row > *':' .line-text'),{opacity:0,x:-20,duration:.14,stagger:.055,ease:'power3.out'},t+.08);
    }else if(s.type==='theme'){
      const next=timeline[i+1],overlap=next?.type==='question'?d.motion.expand:0;
      const outline=s.outline?'<svg class="theme-person-outline" viewBox="'+esc(s.outline.viewBox)+'" preserveAspectRatio="none" data-layout-ignore>'+s.outline.paths.map(p=>'<path d="'+esc(p)+'"/>').join('')+'</svg>':'';
      const bubbles=s.topics.map((lines,k)=>{const double=k===2,w=double?350:384,h=double?188:130,b=double?164:106;
        return '<div class="topic-bubble"><svg class="bubble-shape" viewBox="0 0 '+w+' '+h+'" preserveAspectRatio="none" data-layout-ignore>'+grad(id+'-g'+k)+'<path d="M21 2 H'+(w-21)+' Q'+(w-2)+' 2 '+(w-2)+' 21 V'+(b-19)+' Q'+(w-2)+' '+b+' '+(w-21)+' '+b+' H'+(w-48)+' L'+(w-32)+' '+(h-3)+' L'+(w-74)+' '+b+' H21 Q2 '+b+' 2 '+(b-19)+' V21 Q2 2 21 2Z" fill="#000" stroke="url(#'+id+'-g'+k+')" stroke-width="3"/></svg><span class="bubble-copy '+(lines.length>1?'bubble-copy-scenes':'')+'">'+lines.map(x=>'<span>'+esc(x)+'</span>').join('')+'</span></div>';}).join('');
      html.push(clip(id,'theme-scene',t,s.duration+overlap,'<div class="theme-person" data-layout-allow-overflow><img class="theme-person-photo" src="'+esc(prepared[s.portrait])+'"/>'+outline+'</div><div class="theme-content"><div class="theme-title">'+glyphTitle(s.title)+'</div><div class="theme-topics">'+bubbles+'</div></div><div class="theme-card-layer"><div class="theme-identity"><div class="identity-pill"><svg class="identity-spark" viewBox="0 0 32 32" data-layout-ignore><path d="M16 1.8C17.5 10.1 21.9 14.5 30.2 16C21.9 17.5 17.5 21.9 16 30.2C14.5 21.9 10.1 17.5 1.8 16C10.1 14.5 14.5 10.1 16 1.8Z"/></svg><strong class="theme-name">'+esc(s.name)+'</strong><span class="identity-dash">—</span><span class="theme-role">'+esc(s.role)+'</span></div></div></div>'));
      tween(sel,{opacity:0,duration:.24,ease:'sine.out'},t);
      tween(sel+' .theme-person, '+sel+' .theme-identity',{opacity:0,x:140,duration:d.motion.person,ease:'power2.out'},t+.04);
      tween(sel+' .char',{opacity:0,y:16,duration:.12,stagger:{amount:d.motion.title-.12},ease:'power3.out'},t+.04+d.motion.person);
      tween(sel+' .topic-bubble',{opacity:0,x:-24,scale:.96,transformOrigin:'right bottom',duration:d.motion.bubble,stagger:d.motion.bubble,ease:'circ.out'},t+.04+d.motion.person+d.motion.title);
    }else if(s.type==='question'){
      const gid=id+'-brand';
      html.push(clip(id,'question-scene',t,s.duration,'<div class="q-scrim"></div><div class="q-layout"><div class="q-shell"><svg class="q-outline" viewBox="0 0 940 500" data-layout-ignore>'+grad(gid)+'<path d="M36 8 H904 Q932 8 932 36 V402 Q932 430 904 430 H232 L266 489 L151 430 H36 Q8 430 8 402 V36 Q8 8 36 8Z" fill="#000" stroke="url(#'+gid+')" stroke-width="3"/></svg><div class="q-heading"><span class="accent">'+esc(s.number||'Q'+(i+1))+'</span><span>'+esc(s.label)+'</span></div><svg class="q-mark" viewBox="0 0 142 208" data-layout-ignore><path d="M16 40 C32 15 57 7 80 10 C113 13 133 34 132 66 C131 91 117 105 96 120 C78 133 76 141 76 155 H43 C42 130 50 114 70 98 C88 84 98 77 98 63 C98 48 89 39 76 39 C61 39 52 45 41 59Z M43 176 H77 V205 H43Z" fill="#000" stroke="url(#'+gid+')" stroke-width="2.5"/></svg><div class="q-copy"><div class="q-context">'+esc(s.context)+'</div><div class="q-question">'+s.lines.map(x=>'<span class="q-line">'+rich(x)+'</span>').join('')+'</div></div></div></div>'));
      const fromTheme=timeline[i-1]?.type==='theme',box=[[126,535,384,130],[246,723,390,130],[126,911,350,188]][s.fromTopic??0];
      tween(sel+' .q-scrim',{opacity:0,duration:d.motion.expand,ease:'sine.out'},t);
      tween(sel+' .q-shell',fromTheme?{x:box[0]-70,y:box[1]-480,scaleX:box[2]/940,scaleY:box[3]/500,duration:d.motion.expand,ease:'power3.inOut'}:{opacity:0,scale:.96,duration:d.motion.expand,ease:'power2.out'},t);
      tween(sel+' .q-heading',{opacity:0,y:8,duration:.2,ease:'power2.out'},t+Math.max(0,d.motion.expand-.2));
      tween(sel+' .q-mark',{opacity:0,scale:.86,duration:.2,ease:'circ.out'},t+Math.max(0,d.motion.expand-.2));
      tween(sel+' .q-context, '+sel+' .q-line',{opacity:0,y:16,duration:d.motion.qLine,stagger:d.motion.qStagger,ease:'power3.out'},t+d.motion.expand);
    }else if(s.type==='answer'){
      html.push(clip(id,'answer-scene',t,s.duration,'<div class="answer-layout"><div class="answer-head">'+rowText(s.headline)+'</div></div>'));
      html.push(media(id+'-video',s.media,t,s.duration,'answer-video','style="z-index:81;object-position:'+esc(s.objectPosition||'50% 35%')+'"'));
      html.push(clip(id+'-border','',t,s.duration,'<div class="answer-border"></div>','style="z-index:93;pointer-events:none"'));
      html.push(audio(id+'-voice',s.media,t,s.duration,s.volume??1));
      tween(sel+' .answer-head',{opacity:0,y:12,duration:.24,ease:'power3.out'},t);
      tween(sel+'-video',{opacity:0,duration:.18,ease:'sine.out'},t);
      for(const [j,c] of s.captions.entries()){
        html.push(clip(id+'-c'+j,'caption-clip',t+c.start,c.end-c.start,'<div class="caption-layout"><div class="caption-copy">'+esc(c.text)+'</div></div>'));
        cues.push({id:id+'-c'+j,start:round(t+c.start),end:round(t+c.end),text:c.text,scene:id});
      }
      for(const [j,e] of (s.evidence||[]).entries()){
        const eid=id+'-e'+j,attrs='style="z-index:90"';
        if(config.media[e.media].kind==='image')html.push(clip(eid,'evidence-scene',t+e.start,e.end-e.start,'<img class="evidence-media" src="'+esc(prepared[e.media])+'"/>'));
        else html.push(media(eid,e.media,t+e.start,e.end-e.start,'evidence-media',attrs));
        tween('#'+eid,{opacity:0,duration:.2,ease:'sine.out'},t+e.start);
      }
    }else if(s.type==='outro'){
      html.push(clip(id,'outro-scene',t,s.duration,'<div class="outro-layout"><div class="theme-title">'+glyphTitle(s.lines)+'</div></div>'));
      tween(sel,{opacity:0,duration:.25,ease:'sine.out'},t);
      tween(sel+' .char',{opacity:0,y:12,duration:.12,stagger:{amount:Math.min(1,s.duration-.15)},ease:'power3.out'},t+.01);
    }
  }
  for(const [i,a] of (config.audio||[]).entries())html.push(audio('music-'+i,a.media,a.start,a.duration,a.volume));
  const body='<div id="root" data-composition-id="main" data-start="0" data-duration="'+duration+'" data-width="1080" data-height="1440">'+html.join('\n')+'</div>';
  let template=fs.readFileSync(path.join(home,'assets/renderer.html'),'utf8');
  template=template.replace('{{STYLE}}',()=>style(d)).replace('{{BODY}}',()=>body).replace('{{ANIMATION}}',()=>anim.join('\n'));
  return {html:template,timeline,cues,duration,design:d};
}
function srtTime(n){let v=Math.round(n*1000);const ms=v%1000;v=Math.floor(v/1000);const s=v%60;v=Math.floor(v/60);const m=v%60,h=Math.floor(v/60);return [h,m,s].map(x=>String(x).padStart(2,'0')).join(':')+','+String(ms).padStart(3,'0');}
export function build(configPath,out,validateOnly=false){
  const input=path.resolve(configPath),base=path.dirname(input),config=JSON.parse(fs.readFileSync(input,'utf8'));
  const checked=validate(config,base),plan=mediaPlan(config,base,checked.timeline);
  if(validateOnly)return {status:'ok',duration:checked.duration,scenes:checked.timeline.length,media:Object.keys(plan).length};
  const dest=path.resolve(out);if(fs.existsSync(dest))throw Error('Output already exists; use a new build directory');
  fs.mkdirSync(dest,{recursive:true});
  const prepared=materialize(plan,dest),result=compose(config,prepared);
  fs.writeFileSync(path.join(dest,'index.html'),result.html);
  fs.writeFileSync(path.join(dest,'timeline.json'),JSON.stringify({duration:result.duration,scenes:result.timeline,captions:result.cues},null,2));
  fs.writeFileSync(path.join(dest,'captions.srt'),result.cues.map((c,i)=>(i+1)+'\n'+srtTime(c.start)+' --> '+srtTime(c.end)+'\n'+c.text+'\n').join('\n'));
  const portable={...config,media:Object.fromEntries(Object.entries(prepared).map(([id,p])=>[id,{kind:config.media[id].kind,path:p}]))};
  fs.writeFileSync(path.join(dest,'project.json'),JSON.stringify(portable,null,2));
  fs.writeFileSync(path.join(dest,'source-map.json'),JSON.stringify({input,media:config.media},null,2));
  fs.writeFileSync(path.join(dest,'DESIGN.md'),'# Interview template design\n\n'+JSON.stringify(result.design,null,2)+'\n\nRead the skill components reference. Do not introduce another palette.\n');
  fs.writeFileSync(path.join(dest,'package.json'),JSON.stringify({name:'interview-template-project',private:true,type:'module',scripts:{check:'npx --yes hyperframes@0.8.34 check',render:'npx --yes hyperframes@0.8.34 render'}},null,2));
  return {status:'built',project:dest,duration:result.duration,scenes:result.timeline.length,captions:result.cues.length};
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
  try{const a=process.argv.slice(2);if(a[0]==='--validate')console.log(JSON.stringify(build(a[1],null,true),null,2));else if(a.length===2)console.log(JSON.stringify(build(a[0],a[1]),null,2));else throw Error('Usage: node build.mjs --validate config.json | node build.mjs config.json NEW_DIRECTORY');}
  catch(e){console.error(e.message);process.exitCode=1;}
}
