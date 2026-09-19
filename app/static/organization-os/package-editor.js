/* Sources are inert text. Saving creates a new immutable version, never a run. */
(() => {'use strict';
  window.PackageEditor={create({binding,request,act}){
    const el=(tag,text='')=>{const n=document.createElement(tag);n.textContent=text;return n;};
    const panel=el('section');panel.className='artifact';panel.setAttribute('aria-label','Pliki i nowa wersja źródeł');
    const heading=el('h3',`Pliki paczki #${binding.artifact_id} · podgląd i zmiany`);
    const form=el('fieldset'), legend=el('legend','Edycja wersjonowana — bez uruchamiania kodu');
    const pick=el('select'), pickLabel=el('label','Pliki i katalogi');pickLabel.append(pick);
    pick.append(el('option','Wybierz zapisany plik'));pick.children[0].value='';
    for(const file of binding.files){const o=el('option',`${file.path} · ${file.size_bytes} B`);o.value=file.path;pick.append(o);}
    const open=el('button','Otwórz plik');open.type='button';
    const path=el('input'), pathLabel=el('label','Ścieżka zmienianego lub nowego pliku');path.maxLength=200;path.placeholder='src/module.py';pathLabel.append(path);
    const text=el('textarea'), textLabel=el('label','Treść źródła (nie jest wykonywana)');text.rows=14;text.spellcheck=false;textLabel.append(text);
    const stage=el('button','Dodaj zmianę do szkicu');stage.type='button';
    const purpose=el('input'), purposeLabel=el('label','Opis nowej wersji');purpose.maxLength=2000;purposeLabel.append(purpose);
    const drafts=el('ul'), save=el('button','Zapisz nową wersję źródeł');save.type='button';
    const result=el('div');result.setAttribute('aria-live','polite');
    const changes=new Map();let pending=null, frozen=false, protectedPath=null;
    const root=`/api/tasks/${binding.task_id}/workspace-packages/${binding.artifact_id}`;
    function showDrafts(){drafts.replaceChildren();for(const name of changes.keys()){
      const item=el('li',name),remove=el('button','Usuń ze szkicu');remove.type='button';
      remove.addEventListener('click',()=>{if(frozen)return;changes.delete(name);showDrafts();});item.append(remove);drafts.append(item);
    }}
    open.addEventListener('click',()=>act(async()=>{
      if(!pick.value)return;
      if(text.value && path.value && !confirm('Wczytać plik? Najpierw dodaj niezapisany tekst do szkicu, jeśli chcesz go zachować.'))return;
      const file=await request(root+'/source?path='+encodeURIComponent(pick.value));
      if(file.package_checksum!==binding.checksum)throw Error('Wersja źródła zmieniła się. Wczytaj paczkę ponownie.');
      path.value=file.path;text.value=changes.get(file.path)??file.content;
      protectedPath=file.protected_test?file.path:null;text.readOnly=protectedPath!==null;
      result.replaceChildren(el('p',file.protected_test?'Rozpoznany plik testowy: podgląd dozwolony, zmiana i usunięcie istniejącego testu zablokowane.':'Źródło wczytane bez wykonywania. Edytuj i dodaj zmianę do szkicu.'));
    }));
    path.addEventListener('input',()=>{text.readOnly=path.value===protectedPath;});
    stage.addEventListener('click',()=>{
      if(frozen)return;
      const name=path.value.trim();
      if(!name){result.replaceChildren(el('p','Podaj ścieżkę pliku.'));return;}
      if(name===protectedPath){result.replaceChildren(el('p','Istniejący plik testowy jest chroniony. Użyj innej ścieżki dla nowego testu.'));return;}
      changes.set(name,text.value);showDrafts();result.replaceChildren(el('p','Zmiana tylko w szkicu tej karty. Użyj zapisu, aby utworzyć wersję.'));
    });
    save.addEventListener('click',()=>act(async()=>{
      if(frozen)return;
      if(!changes.size || !purpose.value.trim())throw Error('Dodaj zmiany do szkicu i opis wersji.');
      const body={base_checksum:binding.checksum,purpose:purpose.value.trim(),changes:Object.fromEntries(changes),removals:[]};
      const signature=JSON.stringify(body);
      if(pending&&pending.signature!==signature)throw Error('Najpierw rozstrzygnij wcześniejszy zapis: ponów tę samą treść albo odśwież listę paczek.');
      if(!pending)pending={signature,id:crypto.randomUUID()};
      frozen=true;form.disabled=true;
      try{
        const saved=await request(root+'/edits',{method:'POST',body:JSON.stringify({...body,request_id:pending.id})});
        if(saved.package?.task_id!==binding.task_id || !Number.isSafeInteger(saved.package.artifact_id))throw Error('Niezgodne powiązanie zapisanej wersji. Sprawdź listę paczek.');
        result.replaceChildren(el('h4',`Zapisano nową paczkę #${saved.package.artifact_id}`),el('p','Poprzednia wersja pozostała nienaruszona. Nowa nie dziedziczy wyników testów ani odbioru. Wieloplikowy zapis nie oznacza zgodności z obecnym runnerem.'));
        const next=el('a','Otwórz nową wersję w Budowie i testach');next.href=`/os/build?task=${binding.task_id}&package=${saved.package.artifact_id}`;
        const zip=el('button','Pobierz nową wersję ZIP');zip.type='button';zip.addEventListener('click',()=>act(async()=>{
          const blob=await request(`/api/tasks/${binding.task_id}/workspace-packages/${saved.package.artifact_id}/download`,{},true);
          const url=URL.createObjectURL(blob),a=el('a');a.href=url;a.download=`package-${saved.package.artifact_id}.zip`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
        }));result.append(next,zip);
        // Keep this completed edit frozen; continued work opens the new base.
      }catch(error){frozen=false;form.disabled=false;throw error;}
    }));
    form.append(legend,pickLabel,open,pathLabel,textLabel,stage,drafts,purposeLabel,save);
    panel.append(heading,el('p','Źródła nie są zapisywane na dysku hosta ani wykonywane. Przed zmianą pliku w edytorze dodaj go do szkicu. Szkic istnieje tylko w tej karcie; zmiana paczki lub wylogowanie go usuwa.'),form,result);
    return panel;
  }};
})();
