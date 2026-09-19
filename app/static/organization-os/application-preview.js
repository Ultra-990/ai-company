/* Owner-side broker. Frame receives sources and bounded replies, NEVER credentials. */
(()=>{'use strict';
window.createApplicationPreview=({request,message})=>{
  const section=document.getElementById('application-preview'),host=document.getElementById('application-host');
  let frame=null,binding=null,files=null,html='',version=0,inFlight=false,requests=0;
  function close(){version++;frame=null;binding=null;files=null;html='';host.replaceChildren();section.hidden=true;inFlight=false;}
  async function rpc(path){
    const expected=binding?.package_checksum;
    const result=await request('/api/package-runs/preview',{method:'POST',body:JSON.stringify({...binding,path,request_id:crypto.randomUUID(),confirm_execution:true})});
    if(!expected||result.source_checksum!==expected)throw Error('Odpowiedź podglądu wskazuje inną paczkę.');
    return result;
  }
  async function open(run){
    close();const ticket=version;
    message('Uruchamiam podgląd w izolacji. Nie zamykaj karty podczas przygotowania.');
    const pkg=await request(`/api/tasks/${run.task_id}/workspace-packages/${run.package_id}`);
    if(ticket!==version)return;
    if(pkg.checksum!==run.package_checksum)throw Error('Zmieniła się suma paczki.');
    binding={task_id:run.task_id,package_id:run.package_id,package_checksum:run.package_checksum};
    const result=await rpc('/');if(ticket!==version)return;
    if(result.source_checksum!==binding.package_checksum)throw Error('Odpowiedź podglądu wskazuje inną paczkę.');
    files=result.assets;
    if(!files||typeof files!=='object')throw Error('Serwer nie przekazał plików podglądu. Odśwież panel.');
    for(const entry of pkg.files.filter(f=>['app.js','style.css'].includes(f.path)||(f.path.startsWith('static/')&&/\.(css|js)$/.test(f.path))))
      if(typeof files[entry.path]!=='string'||!files[entry.path].trim())throw Error('Brak treści pliku podglądu: '+entry.path);
    if(result.response.status!==200)throw Error('Serwer aplikacji nie zwrócił strony.');
    html=result.response.body;requests=0;
    frame=document.createElement('iframe');frame.title='Działający podgląd aplikacji';frame.setAttribute('sandbox','allow-scripts allow-forms');
    frame.referrerPolicy='no-referrer';frame.src='/os/application-frame';host.replaceChildren(frame);section.hidden=false;
    section.scrollIntoView({behavior:'smooth',block:'start'});
    message('Aplikacja otwarta. Każde obliczenie uruchamia krótki, izolowany proces; dane nie są zachowywane między żądaniami.');
  }
  window.addEventListener('message',async e=>{
    if(!frame||e.source!==frame.contentWindow||e.origin!=='null')return;
    const d=e.data;
    if(d?.kind==='application-ready'){frame.contentWindow.postMessage({kind:'application-init',html,files},'*');return;}
    if(d?.kind!=='application-request'||!Number.isSafeInteger(d.id)||typeof d.path!=='string')return;
    const target=frame.contentWindow,ticket=version;
    const reply=value=>{if(ticket===version&&frame?.contentWindow===target)target.postMessage({kind:'application-reply',id:d.id,...value},'*');};
    if(inFlight||requests>=30||!/^\/api\/[A-Za-z0-9_-]+(?:\?[A-Za-z0-9_=&.%+,-]{0,800})?$/.test(d.path)){reply({error:'Żądanie niedozwolone, limit podglądu lub trwa poprzednie obliczenie.'});return;}
    inFlight=true;requests++;
    try{const data=await rpc(d.path);reply({response:data.response});}
    catch(error){reply({error:'Błąd izolowanego podglądu.'});if(ticket===version)message(error.message);}
    finally{if(ticket===version)inFlight=false;}
  });
  document.getElementById('close-application').addEventListener('click',close);
  return {open,close};
};
})();
