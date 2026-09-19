import * as THREE from './vendor/three.module.js';
import {CSS3DRenderer, CSS3DObject, CSS3DSprite} from './vendor/CSS3DRenderer.js';
import {clamp, atlasAnchors, focusedPose, zoomStep, relationPairs} from './motion.mjs?v=3';

const $ = id => document.getElementById(id);
const stage = $('stage'), inspector = $('inspector');
const reduced = matchMedia('(prefers-reduced-motion: reduce)');
const scene = new THREE.Scene(), htmlScene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(42, 1, 1, 6000);
const css = new CSS3DRenderer();
$('html-layer').append(css.domElement);
const cards = new Map(), objects = new Map(), glEdges = [], svgEdges = [];
let anchors = [], shownChapter = -1, zoom = 1, cameraReady = false, focusOffset = [0,0];
const track = $('scene-track');
const symbols = {'compass':'◈','code-2':'⌘','sparkles':'✦','blocks':'▦','palette':'◌','terminal':'›_','handshake':'↔','shield-check':'◉','server':'▤','landmark':'▰','users':'◫'};
let renderer = null, frame = 0, last = 0, target = 0, current = 0, drag = null, renderedFrames = 0;
let width = 1, height = 1, overview = null, tree = null, nextMove = null, alerts = null;
let fetching = false, refreshAgain = false, alive = true, lastSuccess = null, stopSignature = '';
let dialogKind = null, dialogNode = null, dataErrors = [], dialogOrigin = null, dialogAnimation = null, closingDialog = false;
let dialogHistory = [], paletteColors = {surface:'#202024',accent:'#e1e1e8'};
const statuses = {planned:'Zaplanowany',active:'Aktywny',in_progress:'W toku',completed:'Ukończony',blocked:'Zablokowany',paused:'Wstrzymany'};
const count = v => Number.isFinite(Number(v)) ? Math.max(0, Math.round(Number(v))) : 0;
const pct = v => `${clamp(count(v), 0, 100)}%`;
const progressLabel = n => n.measurement_state==='unmeasured'?'—':pct(n.progress);
function el(tag, cls, text) {
  const e = document.createElement(tag); if(cls) e.className = cls;
  if(text !== undefined) e.textContent = text; return e;
}
function button(label, cls, action) {
  const b = el('button', cls, label); b.type = 'button'; b.addEventListener('click', action); return b;
}
function iconButton(label, cls, path, action) {
  const b = button('', cls, action); b.title = label; b.setAttribute('aria-label', label);
  const svg = document.createElementNS('http://www.w3.org/2000/svg','svg'); svg.setAttribute('viewBox','0 0 20 20'); svg.setAttribute('aria-hidden','true');
  const p = document.createElementNS(svg.namespaceURI,'path'); p.setAttribute('d',path); svg.append(p); b.append(svg); return b;
}
function schedule() { if(alive && !frame && !document.hidden) frame = requestAnimationFrame(draw); }
function useFallback() {
  document.body.classList.add('fallback');
  $('render-mode').textContent = 'Tryb lekki · przestrzeń CSS 3D';
  if(renderer) { renderer.dispose(); renderer.domElement.remove(); renderer = null; }
  schedule();
}
try {
  if(new URLSearchParams(location.search).get('graphics') === 'lite') throw new Error('Requested lite renderer');
  renderer = new THREE.WebGLRenderer({alpha:true,antialias:true,powerPreference:'low-power'});
  renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5));
  renderer.setClearColor(0,0); renderer.outputColorSpace = THREE.SRGBColorSpace;
  $('gl-layer').append(renderer.domElement);
  renderer.domElement.addEventListener('webglcontextlost', event => {event.preventDefault(); useFallback();});
  $('render-mode').textContent = 'WebGL · scena renderowana na żądanie';
} catch { useFallback(); }

const ambient = new THREE.HemisphereLight(0xe3ffe9, 0x132320, 2.5); scene.add(ambient);
const keyLight = new THREE.DirectionalLight(0xc9ffe4, 3); keyLight.position.set(-500,700,1000); scene.add(keyLight);
const rimLight = new THREE.DirectionalLight(0x8aa2e9, 2); rimLight.position.set(600,-200,500); scene.add(rimLight);
const orbMaterials = [];
function orb(id, name, sub, position, radius, action) {
  const group = new THREE.Group(); group.position.set(...position);
  const material = new THREE.MeshPhysicalMaterial({color:0x9baaa0,metalness:.85,roughness:.22,clearcoat:1});
  orbMaterials.push(material);
  const mesh = new THREE.Mesh(new THREE.SphereGeometry(radius,40,28),material); group.add(mesh);
  // One billboard orbit with sphere-silhouette occlusion, shared with the desktop.
  scene.add(group);
  const hit = button('',`orb-hit ${id}`,action); hit.id = `${id}-orb`; hit.setAttribute('aria-haspopup','dialog');
  hit.append(el('strong','',name),el('small','',sub));
  window.CompanyOrbit?.mount(hit);
  const html = new CSS3DSprite(hit); html.position.copy(group.position); htmlScene.add(html);
  objects.set(id,{position:group.position, group, html, mesh});
}
orb('owner','AI','WŁAŚCICIEL',[-240,470,-100],62,()=>showDialog('owner',null,$('owner-orb')));
orb('brain','Brain','ORKIESTRATOR',[220,470,-180],95,()=>showDialog('brain',null,$('brain-orb')));

function windowFrame() {
  const shape=new THREE.Shape(),x=-216,y=-187,w=432,h=374,r=18;
  shape.moveTo(x+r,y);shape.lineTo(x+w-r,y);shape.quadraticCurveTo(x+w,y,x+w,y+r);
  shape.lineTo(x+w,y+h-r);shape.quadraticCurveTo(x+w,y+h,x+w-r,y+h);
  shape.lineTo(x+r,y+h);shape.quadraticCurveTo(x,y+h,x,y+h-r);
  shape.lineTo(x,y+r);shape.quadraticCurveTo(x,y,x+r,y);
  const geometry=new THREE.ExtrudeGeometry(shape,{depth:14,bevelEnabled:true,bevelSegments:2,steps:1,bevelSize:3,bevelThickness:3,curveSegments:6});
  const mesh=new THREE.Mesh(geometry,new THREE.MeshStandardMaterial({color:0x40574c,metalness:.65,roughness:.4}));
  scene.add(mesh);return mesh;
}

function selectStop(n) {
  target = clamp(Math.round(n),0,cards.size); zoom = 1;
  if(reduced.matches) current = target;
  cards.forEach(r=>{if(r.index === Math.round(target)-1){r.closed=false; r.minimized=false; r.el.hidden=false;}});
  focusOffset=[...([...cards.values()].find(r=>r.index===target-1)?.offset||[0,0])];
  const top = track.getBoundingClientRect().top + scrollY - document.querySelector('.app-navigation').offsetHeight;
  if(track.getBoundingClientRect().top < 0 || track.getBoundingClientRect().top > innerHeight*.4)
    window.scrollTo({top:Math.max(0,top),behavior:'instant'});
  $('zoom-in').disabled = $('zoom-out').disabled = target===0;
  $('zoom-level').textContent = target ? '100%' : 'Mapa';
  schedule();
}
function addCard(node,index) {
  const article = el('article','spatial-window'); article.dataset.key=node.key;
  const header = el('header','window-bar');
  const label=el('span','window-label');
  header.append(el('span','department-symbol',symbols[node.icon]||'◈'),label);
  const r = {node,index,label,el:article,closed:false,minimized:false,offset:[0,0],signature:''};
  const controls = el('div','controls');
  controls.append(
    iconButton('Powiadomienia działu','bell','M4 13h12l-2-3V7a4 4 0 0 0-8 0v3z M8 16h4',e=>showDialog('alerts',r.node,e.currentTarget)),
    iconButton('Minimalizuj','min','M4 10h12',()=>{r.minimized=!r.minimized;article.style.height=r.minimized?'48px':'370px';r.body.hidden=r.minimized;schedule();}),
    iconButton('Maksymalizuj','max','M4 8V4h4 M12 4h4v4 M16 12v4h-4 M8 16H4v-4',e=>showDialog('node',r.node,e.currentTarget)),
    iconButton('Zamknij okno — przywróć z nawigacji','close','M5 5l10 10 M15 5L5 15',()=>{r.closed=true;article.hidden=true;schedule();}),
  ); header.append(controls);
  r.body = el('div','window-body');r.body.setAttribute('aria-label',`Podsumowanie działu ${node.name}`);
  r.status=el('span','window-status');r.heading=el('h2');r.value=el('strong');
  const progressRow=el('div','progress-row');progressRow.append(r.value,el('span','','REALIZACJA Z API'));
  r.progress=el('progress');r.progress.max=100;r.progress.setAttribute('aria-label','Postęp działu');
  r.meta=el('div','window-meta');
  const open=button('Otwórz szczegóły działu ↗','window-open',e=>showDialog('node',r.node,e.currentTarget));
  r.body.append(r.status,r.heading,progressRow,r.progress,r.meta,open);
  article.append(header,r.body);
  const object = new CSS3DObject(article);object.position.set(...anchors[index]);htmlScene.add(object);r.object=object;
  r.frame=windowFrame();
  objects.set(node.key,{position:object.position,html:object,record:r});cards.set(node.key,r);
  header.addEventListener('pointerdown',e=>{
    if(e.button!==0 || e.target.closest('button'))return;
    e.preventDefault(); header.setPointerCapture(e.pointerId);
    drag={record:r,id:e.pointerId,x:e.clientX,y:e.clientY,ox:r.offset[0],oy:r.offset[1],
      factor:2*Math.tan(THREE.MathUtils.degToRad(camera.fov/2))*(camera.position.z-object.position.z)/height};
  });
  header.addEventListener('pointermove',e=>{
    if(!drag || drag.id!==e.pointerId)return;
    r.offset=[clamp(drag.ox+(e.clientX-drag.x)*drag.factor,-280,280),clamp(drag.oy-(e.clientY-drag.y)*drag.factor,-150,150)];schedule();
  });
  const end=()=>{drag=null;};header.addEventListener('pointerup',end);header.addEventListener('pointercancel',end);header.addEventListener('lostpointercapture',end);
  article.addEventListener('focusin',()=>{if(Math.abs(target-r.index-1)>.1)selectStop(r.index+1);});
  r.body.addEventListener('click',e=>{if(!e.target.closest('button'))selectStop(r.index+1);});
  return r;
}
function updateCard(r,node) {
  r.label.textContent=`${String(r.index+1).padStart(2,'0')} / ${node.name.toUpperCase()}`;
  r.node=node; if(r.signature===JSON.stringify(node))return;r.signature=JSON.stringify(node);
  r.heading.textContent=node.name;r.status.textContent=statuses[node.status]||node.status||'Brak statusu';
  r.value.textContent=progressLabel(node);r.progress.value=clamp(count(node.progress),0,100);r.value.title=node.progress_note||'Postęp przypisanych zadań';
  if(node.measurement_state==='unmeasured')r.status.textContent+=' · brak pomiaru';
  r.meta.replaceChildren(el('span','',`Waga ${count(node.weight)}`),el('span','',`Do odbioru ${count(node.awaiting_review_count)}`));
}
function rebuildRelations(nodes) {
  for(const e of glEdges){scene.remove(e.line);e.line.geometry.dispose();e.line.material.dispose();}glEdges.length=0;
  for(const e of svgEdges)e.line.remove();svgEdges.length=0;
  const root=tree?.nodes?.find(n=>n.key==='ai-company');
  for(const [from,to,kind] of relationPairs(root,nodes,tree.dependencies)) {
    const geometry=new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(),new THREE.Vector3()]);
    const line=new THREE.Line(geometry,new THREE.LineBasicMaterial({color:kind==='depends_on'?0x869499:0x729f89,transparent:true,opacity:.6}));
    scene.add(line);glEdges.push({line,from,to});
    const svg=document.createElementNS('http://www.w3.org/2000/svg','line');svg.dataset.from=from;svg.dataset.to=to;$('fallback-lines').append(svg);svgEdges.push({line:svg,from,to});
  }
}
function resize(preserve=false) {
  width=stage.clientWidth;height=stage.clientHeight;camera.aspect=width/height;camera.updateProjectionMatrix();
  css.setSize(width,height);renderer?.setSize(width,height);
  schedule();
}
function endpoint(key) {
  const obj=objects.get(key);if(!obj || obj.record?.closed)return null;
  const p=obj.position.clone();if(obj.record)p.y+=obj.record.minimized?24:185;return p;
}
function draw(time) {
  frame=0;if(document.hidden)return;
  const dt=Math.min((time-last)/1000||.016,.06);last=time;
  current=reduced.matches?target:current+(target-current)*(1-Math.exp(-9*dt));
  if(Math.abs(target-current)<.001)current=target;
  // Fly directly to the selected window, never through intermediate departments.
  const desired = new THREE.Vector3(...focusedPose(anchors,target,width,height,zoom,focusOffset));
  if(!cameraReady || reduced.matches)camera.position.copy(desired);
  else camera.position.lerp(desired,1-Math.exp(-9*dt));
  cameraReady=true;
  const travelling=camera.position.distanceTo(desired)>.08;
  if(!travelling)camera.position.copy(desired);
  camera.rotation.set(0,0,0);camera.updateMatrixWorld();
  // Both guides travel and change apparent size with the camera, without an idle loop.
  const influence=clamp(current,0,1),guideDepth=1100;
  const viewHeight=2*Math.tan(THREE.MathUtils.degToRad(21))*guideDepth;
  ['owner','brain'].forEach((key,i)=>{
    const obj=objects.get(key),base=i?[220,470,-180]:[-240,470,-100];
    const guide=[camera.position.x+(i?1:-1)*viewHeight*camera.aspect*.35,
      camera.position.y+viewHeight*.34,camera.position.z-guideDepth];
    obj.position.set(...base.map((v,j)=>v+(guide[j]-v)*influence));obj.html.position.copy(obj.position);
    obj.group.rotation.y=reduced.matches?0:current*.12;
  });
  cards.forEach(r=>{
    const a=anchors[r.index];r.object.position.set(a[0]+r.offset[0],a[1]+r.offset[1],a[2]);
    const active=Math.abs(current-r.index-1)<.4;
    r.el.classList.toggle('is-active',active);r.body.hidden=r.minimized;
    r.el.classList.toggle('is-overview',current<.45);
    if(!r.minimized)r.el.style.height='370px';
    r.object.rotation.set(0,0,0);
    r.el.dataset.rotation='0,0,0';
    r.frame.position.copy(r.object.position);r.frame.position.z-=22;r.frame.rotation.copy(r.object.rotation);
    r.frame.visible=!r.closed;r.frame.scale.y=r.minimized?48/370:1;
    r.frame.material.color.set(active?paletteColors.accent:paletteColors.surface);
    // Closed DOM nodes must remain detached from pointer/focus navigation.
    r.el.hidden=r.closed;
  });
  const chapter=Math.round(current);
  if(chapter!==shownChapter){
    shownChapter=chapter;
    const record=[...cards.values()].find(r=>r.index===chapter-1);
    $('chapter-number').textContent=`${String(chapter).padStart(2,'0')} / ${String(cards.size).padStart(2,'0')} · ${chapter?'DZIAŁ':'ORGANIZACJA'}`;
    $('chapter-title').textContent=record?.node.name||'Cała struktura. Jeden kierunek.';
    $('stops').querySelectorAll('button').forEach(b=>{
      if(Number(b.dataset.stop)===chapter)b.setAttribute('aria-current','step');else b.removeAttribute('aria-current');
    });
  }
  const focusKey=[...cards.values()].find(r=>r.index===chapter-1)?.node.key;
  const relevant=e=>!chapter||e.from===focusKey||e.to===focusKey||(e.from==='owner'&&e.to==='brain');
  for(const e of glEdges){const a=endpoint(e.from),b=endpoint(e.to);e.line.visible=!!a&&!!b&&relevant(e);
    if(a&&b){const attr=e.line.geometry.attributes.position;attr.setXYZ(0,a.x,a.y,a.z);attr.setXYZ(1,b.x,b.y,b.z);attr.needsUpdate=true;e.line.geometry.computeBoundingSphere();}}
  for(const e of svgEdges){const a=endpoint(e.from),b=endpoint(e.to);e.line.style.display=renderer||!a||!b||!relevant(e)?'none':'';
    if(a&&b&&!renderer){a.project(camera);b.project(camera);e.line.setAttribute('x1',(a.x+1)*width/2);e.line.setAttribute('y1',(1-a.y)*height/2);e.line.setAttribute('x2',(b.x+1)*width/2);e.line.setAttribute('y2',(1-b.y)*height/2);}}
  css.render(htmlScene,camera);renderer?.render(scene,camera);
  stage.dataset.position=current.toFixed(3);stage.dataset.zoom=zoom.toFixed(3);stage.dataset.renderer=renderer?'webgl':'css3d';
  stage.dataset.frames=String(++renderedFrames);
  if(current!==target||travelling)schedule();
}
function changeZoom(delta,mode=0) {
  if(!target)return;
  zoom=zoomStep(zoom,delta,mode,height);
  $('zoom-level').textContent=`${Math.round(zoom*100)}%`;
  schedule();
}
// Only a selected scene consumes wheel. Native browser zoom and page scroll elsewhere remain intact.
stage.addEventListener('wheel',e=>{
  if(!target||e.ctrlKey||e.metaKey||inspector.open)return;
  e.preventDefault();
  changeZoom(e.deltaY,e.deltaMode);
},{passive:false});
$('zoom-in').addEventListener('click',()=>changeZoom(-100));
$('zoom-out').addEventListener('click',()=>changeZoom(100));
$('previous-department').addEventListener('click',()=>selectStop(target-1));
$('next-department').addEventListener('click',()=>selectStop(target+1));
stage.addEventListener('keydown',e=>{
  if(e.key==='Escape'){e.preventDefault();selectStop(0);return;}
  if(e.target.closest('button,input,select'))return;
  if(['ArrowRight','ArrowDown','PageDown'].includes(e.key)){e.preventDefault();selectStop(Math.floor(target)+1);}
  if(['ArrowLeft','ArrowUp','PageUp'].includes(e.key)){e.preventDefault();selectStop(Math.ceil(target)-1);}
  if(e.key==='Home'){e.preventDefault();selectStop(0);}
  if(['+','=','-'].includes(e.key)){e.preventDefault();changeZoom(e.key==='-'?100:-100);}
});
let swipe=null;
stage.addEventListener('pointerdown',e=>{if(e.pointerType==='touch'&&!e.target.closest('.spatial-window,.orb-hit'))swipe={x:e.clientX,y:e.clientY};});
stage.addEventListener('pointerup',e=>{if(swipe&&Math.abs(e.clientX-swipe.x)>60&&Math.abs(e.clientX-swipe.x)>Math.abs(e.clientY-swipe.y))selectStop(Math.round(target)+(e.clientX<swipe.x?1:-1));swipe=null;});
stage.addEventListener('pointercancel',()=>{swipe=null;});
$('stops').addEventListener('click',e=>{const b=e.target.closest('[data-stop]');if(b)selectStop(Number(b.dataset.stop));});
$('reset').addEventListener('click',()=>{cards.forEach(r=>{r.closed=false;r.minimized=false;r.offset=[0,0];});selectStop(0);});

function menuLink(label,url) {const a=el('a','menu-link',label);a.href=url;a.append(el('span','','↗'));return a;}
function findPath(key,nodes=tree?.nodes||[],path=[]) {
  for(const node of nodes){const next=[...path,node];if(node.key===key)return next;const result=findPath(key,node.children||[],next);if(result)return result;}
  return null;
}
function renderDialog() {
  const body=$('inspector-body');body.replaceChildren();
  $('inspector-back').textContent=dialogHistory.length?'← Wstecz':'← Wróć do sceny';
  if(dialogKind==='owner') {
    $('inspector-title').textContent='Centrum właściciela';
    body.append(el('p','',overview?`Postęp organizacji: ${pct(overview.organization_progress)}. Działy: ${count(overview.department_count)}. Do odbioru: ${count(overview.awaiting_review_count)}.`:'Dane organizacji są niedostępne.'));
    body.append(button('Powiadomienia systemowe ↗','menu-link',()=>showDialog('alerts')),
      button('Następny ruch ↗','menu-link',()=>showDialog('brain')),
      menuLink('Nowe zlecenie i centrum realizacji','/os/work'),
      menuLink('Zadania i realizacja','/os/work'),menuLink('Odbiór i pliki','/os/review'),menuLink('Publikacje dla klientów','/os/publishing'),menuLink('Historia projektów i aktywność klientów','/os/clients'),menuLink('Panel klienta — podgląd właściciela','/os/client-preview'));
  } else if(dialogKind==='brain') {
    $('inspector-title').textContent='Brain / Orkiestrator';
    body.append(el('p','',nextMove?.title||'Brak dostępnej rekomendacji.'),el('p','',nextMove?.reason||'Rekomendacja zostanie odczytana z API.'),
      el('p','', 'Połączenia przedstawiają odpowiedzialność zapisaną w drzewie, nie aktywne sesje agentów. Ten prototyp nie uruchamia wykonawców.'),menuLink('Zlecenia i plan realizacji','/os/work'),menuLink('Przejdź do centrum operacyjnego','/os'));
  } else if(dialogKind==='alerts') {
    $('inspector-title').textContent=dialogNode?`Powiadomienia / ${dialogNode.name}`:'Powiadomienia systemowe';
    const ids=new Set();const visit=n=>{ids.add(n.id);(n.children||[]).forEach(visit);};if(dialogNode)visit(dialogNode);
    const visible=(alerts||[]).filter(a=>!dialogNode||ids.has(a.organization_unit_id));
    if(alerts===null)body.append(el('p','','Nie udało się pobrać powiadomień.'));
    else if(!visible.length)body.append(el('p','','Brak otwartych powiadomień w pobranym zestawie.'));
    for(const alert of visible){body.append(el('h3','',alert.title),el('p','',alert.message));}
    body.append(el('p','','Widok odczytowy. API zwraca maksymalnie 100 otwartych powiadomień.'));
  } else {
    const node=dialogNode;$('inspector-title').textContent=node.name;
    body.append(el('p','',`${statuses[node.status]||node.status} · postęp ${progressLabel(node)} · waga ${count(node.weight)}`),el('p','',node.description||'Zakres i postęp zapisane w drzewie organizacji.'));
    if(node.progress_note)body.append(el('p','',node.progress_note));
    if(node.foundation){
      body.append(el('h3','','Fundamenty w repozytorium'),el('p','',node.foundation.note));
      for(const a of node.foundation.artifacts)body.append(el('p','',`${a.present?'Jest plik':'Brak pliku'}: ${a.reference}`));
      body.append(el('h3','','Co zbudować teraz'),el('p','',node.foundation.next_step),el('h3','','Kryteria gotowości'));
      const checks=el('ul');for(const c of node.foundation.completion_criteria)checks.append(el('li','',c));body.append(checks);
    }
    const path=findPath(node.key)||[];
    if(path.length>1){const parent=path[path.length-2];body.prepend(button(`← ${parent.name}`,'menu-link',()=>showDialog('node',parent)));}
    body.append(el('p','',`Odpowiedzialność: ${node.manager_agent||'nieprzypisana'}. Status z rejestru nie oznacza aktywnej sesji agenta.`));
    const ul=el('ul','criteria');for(const child of node.children||[]){const li=el('li');li.append(button(child.name,'tree-child',()=>showDialog('node',child)),el('strong','',progressLabel(child)));ul.append(li);}
    if(!node.children?.length)body.append(el('p','','To liść aktualnego drzewa. Dowody i zadania weryfikuj w pełnym pulpicie; nie są dodawane automatycznie przez ten widok.'));
    body.append(ul,menuLink('Otwórz pełny pulpit','/os'));
  }
  if(dataErrors.length)body.prepend(el('p','','Uwaga: część danych jest niedostępna lub nieaktualna. Sprawdź stan synchronizacji.'));
}
function dialogTransform() {
  const r=inspector.getBoundingClientRect();let source=dialogOrigin;
  let b=source?.getBoundingClientRect();
  if(!source?.isConnected||!b?.width||b.bottom<0||b.top>innerHeight||b.right<0||b.left>innerWidth){source=$('owner-shortcut');b=source.getBoundingClientRect();}
  const x=clamp(b.x+b.width/2,0,innerWidth)-(r.x+r.width/2);
  const y=clamp(b.y+b.height/2,0,innerHeight)-(r.y+r.height/2);
  return `translate(${x}px,${y}px) scale(${clamp(b.width/r.width,.05,.28)})`;
}
function showDialog(kind,node=null,origin=null) {
  const wasOpen=inspector.open;dialogAnimation?.cancel();closingDialog=false;
  if(wasOpen&&(kind!==dialogKind||node?.key!==dialogNode?.key)){
    dialogHistory.push({kind:dialogKind,node:dialogNode});if(dialogHistory.length>50)dialogHistory.shift();
  } else if(!wasOpen)dialogHistory=[];
  dialogKind=kind;dialogNode=node;renderDialog();
  inspector.scrollTop=0;
  if(wasOpen){$('inspector-back').focus();return;}
  dialogOrigin?.setAttribute('aria-expanded','false');
  dialogOrigin=origin||$(kind==='brain'?'brain-orb':'owner-orb');dialogOrigin?.setAttribute('aria-expanded','true');
  inspector.showModal();
  if(!reduced.matches)dialogAnimation=inspector.animate([
    {transform:dialogTransform(),opacity:0},{transform:'none',opacity:1}
  ],{duration:320,easing:'cubic-bezier(.16,1,.3,1)'});
}
function closeDialog() {
  if(!inspector.open||closingDialog)return;
  dialogAnimation?.cancel();closingDialog=true;
  if(reduced.matches){inspector.close();return;}
  dialogAnimation=inspector.animate([{transform:'none',opacity:1},{transform:dialogTransform(),opacity:0}],{duration:200,easing:'ease-in'});
  dialogAnimation.onfinish=()=>inspector.close();
}
$('owner-shortcut').addEventListener('click',e=>showDialog('owner',null,e.currentTarget));
$('brain-shortcut').addEventListener('click',e=>showDialog('brain',null,e.currentTarget));
$('close-inspector').addEventListener('click',closeDialog);
$('inspector-back').addEventListener('click',()=>{
  const previous=dialogHistory.pop();if(!previous){closeDialog();return;}
  dialogKind=previous.kind;dialogNode=previous.node?(findPath(previous.node.key)?.at(-1)||previous.node):null;
  renderDialog();inspector.scrollTop=0;$('inspector-back').focus();
});
$('inspector-menu').addEventListener('click',()=>showDialog('owner'));
inspector.addEventListener('cancel',e=>{e.preventDefault();closeDialog();});
inspector.addEventListener('close',()=>{if(inspector.open)return;dialogOrigin?.setAttribute('aria-expanded','false');dialogAnimation?.cancel();dialogAnimation=null;closingDialog=false;dialogKind=null;dialogNode=null;dialogHistory=[];});

const directoryCards=new Map();
function updateDirectory(nodes) {
  const desired=new Set(nodes.map(n=>n.key));
  for(const [key,r] of directoryCards)if(!desired.has(key)){r.el.remove();directoryCards.delete(key);}
  nodes.forEach((node,i)=>{
    let r=directoryCards.get(node.key);
    if(!r){r={node,el:el('article','directory-card')};r.heading=el('h3');r.info=el('p');r.value=el('strong','directory-progress');
      r.el.append(r.heading,r.value,r.info,button('Przybliż w przestrzeni ↗','menu-link',()=>selectStop(cards.get(r.node.key).index+1)),button('Przeglądaj podpunkty →','menu-link',e=>showDialog('node',r.node,e.currentTarget)));
      directoryCards.set(node.key,r);$('department-grid').append(r.el);
    }
    r.node=node;r.el.style.order=i;r.heading.textContent=node.name;r.value.textContent=progressLabel(node);
    r.info.textContent=`${statuses[node.status]||node.status} · waga ${count(node.weight)} · ${node.manager_agent||'nieprzypisana rola'}`;
  });filterDirectory();
}
function filterDirectory(){const term=$('department-search').value.trim().toLocaleLowerCase('pl');let visible=0;
  directoryCards.forEach(r=>{r.el.hidden=!`${r.node.name} ${r.node.manager_agent||''}`.toLocaleLowerCase('pl').includes(term);if(!r.el.hidden)visible++;});
  $('directory-summary').textContent=`${visible} z ${directoryCards.size} działów · postęp i role z aktualnego drzewa API`;
}
$('department-search').addEventListener('input',filterDirectory);

async function fetchData(path) {
  const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),10000);
  try {
    const response=await fetch(`/api/organization-os/${path}`,{signal:controller.signal,cache:'no-store',redirect:'error'});
    if(!response.ok)throw new Error(String(response.status));
    const value=await response.json();
    if(!value || typeof value!=='object' || Array.isArray(value))throw new Error('Invalid API payload');
    if(path==='tree'&&!Array.isArray(value.nodes))throw new Error('Invalid tree');
    if(path==='alerts'&&!Array.isArray(value.alerts))throw new Error('Invalid alerts');
    if(path==='overview'&&!Number.isFinite(value.organization_progress))throw new Error('Invalid overview');
    return value;
  }
  finally{clearTimeout(timer);}
}
async function refresh() {
  if(!alive||document.hidden)return;if(fetching){refreshAgain=true;return;}fetching=true;$('retry').disabled=true;
  try {
    const results=await Promise.allSettled(['tree','overview','next-move','alerts'].map(fetchData));
    if(!alive)return;dataErrors=results.flatMap((r,i)=>r.status==='rejected'?[i]:[]);
    if(results[0].status==='fulfilled') {
      const value=results[0].value;
      if(!Array.isArray(value.nodes))throw new Error('Niepoprawny kontrakt drzewa');tree=value;
      const all=value.nodes.find(n=>n.key==='ai-company')?.children||[];
      const selected=[...all].sort((a,b)=>(a.sort_order||0)-(b.sort_order||0));
      anchors=atlasAnchors(selected.length);
      const desired=new Set(selected.map(n=>n.key));
      for(const [key,r] of cards)if(!desired.has(key)){
        htmlScene.remove(r.object);scene.remove(r.frame);r.frame.geometry.dispose();r.frame.material.dispose();
        cards.delete(key);objects.delete(key);
      }
      selected.forEach((n,i)=>{const r=cards.get(n.key)||addCard(n,i);r.index=i;updateCard(r,n);});
      const signature=selected.map(n=>n.key).join();
      if(signature!==stopSignature){stopSignature=signature;$('stops').replaceChildren();
        ['Całość',...selected.map(n=>n.name)].forEach((name,i)=>{const b=button(String(i).padStart(2,'0'),'',()=>{});b.dataset.stop=i;b.title=name;b.setAttribute('aria-label',name);if(!i)b.append(el('span','',name));$('stops').append(b);});
        shownChapter=-1;resize();}
      updateDirectory(selected);
      rebuildRelations(selected);target=clamp(target,0,selected.length);
      $('scene-loading').hidden=selected.length>0;
      if(!selected.length)$('scene-loading').textContent='Brak wybranych działów w API. Otwórz pełny pulpit.';
    }
    if(results[1].status==='fulfilled')overview=results[1].value;
    if(results[2].status==='fulfilled')nextMove=results[2].value;
    if(results[3].status==='fulfilled'&&Array.isArray(results[3].value.alerts))alerts=results[3].value.alerts;
    if(!dataErrors.length)lastSuccess=new Date();
    $('sync').textContent=dataErrors.length?`Niepełne dane · ${dataErrors.length} źródła niedostępne${lastSuccess?' · ostatnia synchronizacja '+lastSuccess.toLocaleTimeString('pl-PL'):''}`:`Dane API · ${lastSuccess.toLocaleTimeString('pl-PL')} · odświeżanie 30 s`;
    if(!tree)$('scene-loading').textContent='Dane niedostępne. Użyj „Odśwież dane” lub pełnego pulpitu.';
    if(inspector.open){if(dialogNode)dialogNode=findPath(dialogNode.key)?.at(-1)||dialogNode;const previousScroll=inspector.scrollTop;renderDialog();inspector.scrollTop=previousScroll;}
    schedule();
  } catch {$('sync').textContent='Błąd danych. Spróbuj ponownie.';$('scene-loading').textContent='Nie udało się zbudować sceny z danych API.';}
  finally{fetching=false;$('retry').disabled=false;if(refreshAgain){refreshAgain=false;refresh();}}
}
$('retry').addEventListener('click',refresh);
const poll=setInterval(refresh,30000);
document.addEventListener('visibilitychange',()=>{if(document.hidden){cancelAnimationFrame(frame);frame=0;}else{last=0;refresh();schedule();}});
function themeChanged(){
  const style=getComputedStyle(document.documentElement);
  paletteColors={surface:style.getPropertyValue('--ui-surface').trim()||'#202024',accent:style.getPropertyValue('--ui-accent').trim()||'#e1e1e8'};
  orbMaterials.forEach(m=>m.color.set(paletteColors.accent));
  ambient.color.set('#ffffff');keyLight.color.set('#ffffff');rimLight.color.set(paletteColors.accent);
  for(const id of ['owner','brain'])objects.get(id)?.group.children.slice(1).forEach(r=>r.material.color.set(paletteColors.accent));
  schedule();
}
const observer=new MutationObserver(themeChanged);observer.observe(document.documentElement,{attributes:true,attributeFilter:['data-theme','data-palette']});
window.addEventListener('resize',()=>resize(true));reduced.addEventListener('change',schedule);
window.addEventListener('pagehide',()=>{alive=false;clearInterval(poll);cancelAnimationFrame(frame);observer.disconnect();renderer?.dispose();});
window.addEventListener('pageshow',e=>{if(e.persisted)location.reload();});
resize();themeChanged();refresh();
