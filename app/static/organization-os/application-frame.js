/* Opaque sandbox origin. No owner token, storage, external scripts or network. */
(()=>{'use strict';let initialized=false,serial=0;const pending=new Map();
window.addEventListener('message',e=>{
  if(e.source!==parent)return;
  const d=e.data;
  if(d?.kind==='application-reply'){
    const p=pending.get(d.id);if(!p)return;pending.delete(d.id);clearTimeout(p.timer);
    if(d.error)p.reject(new Error(d.error));else p.resolve(new Response(d.response.body,{status:d.response.status,headers:{'Content-Type':d.response.content_type}}));
  }
  if(d?.kind!=='application-init'||initialized)return;initialized=true;
  window.fetch=(path,options={})=>new Promise((resolve,reject)=>{
    if(typeof path!=='string'||!/^\/api\/[A-Za-z0-9_-]+(?:\?[A-Za-z0-9_=&.%+,-]{0,800})?$/.test(path)||
       (options.method&&options.method.toUpperCase()!=='GET')||options.body){reject(new Error('Podgląd obsługuje tylko bezstanowe GET /api/nazwa.'));return;}
    const id=++serial,timer=setTimeout(()=>{pending.delete(id);reject(new Error('Upłynął czas podglądu.'));},60000);
    pending.set(id,{resolve,reject,timer});parent.postMessage({kind:'application-request',id,path},'*');
  });
  const parsed=new DOMParser().parseFromString(d.html,'text/html');
  const asset=value=>{
    if(typeof value!=='string'||value.startsWith('//'))return '';
    const path=value.replace(/^\.?\//,'');
    if(!/^[A-Za-z0-9_][A-Za-z0-9_./-]*$/.test(path)||path.split('/').some(p=>!p||p.startsWith('.')))return '';
    return Object.prototype.hasOwnProperty.call(d.files,path)&&typeof d.files[path]==='string'?d.files[path]:'';
  };
  const scripts=[...parsed.querySelectorAll('script')].map(s=>s.getAttribute('src')?asset(s.getAttribute('src')):s.textContent);
  const styles=[...parsed.querySelectorAll('style,link[rel~="stylesheet"]')].map(s=>s.tagName==='STYLE'?s.textContent:asset(s.getAttribute('href')));
  const linksRootStyle=[...parsed.querySelectorAll('link[rel~="stylesheet"]')].some(s=>(s.getAttribute('href')||'').replace(/^\.?\//,'')==='style.css');
  if(!linksRootStyle&&d.files['style.css'])styles.unshift(d.files['style.css']);
  parsed.querySelectorAll('script,iframe,object,embed,base,meta,link').forEach(n=>n.remove());
  parsed.querySelectorAll('style').forEach(n=>n.remove());
  for(const source of styles){const style=document.createElement('style');style.textContent=source;document.head.append(style);}
  document.body.replaceChildren(...parsed.body.childNodes);
  for(const source of scripts){const script=document.createElement('script');script.textContent=source;document.body.append(script);}
});
parent.postMessage({kind:'application-ready'},'*');
})();
