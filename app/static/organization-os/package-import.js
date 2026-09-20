/* Owner-selected file only; parsing does not run package code. */
(()=>{'use strict';
window.PackageImport={create({request,act,onSaved,message}){
  const $=id=>document.getElementById(id);let epoch=0;
  $('media-import').addEventListener('submit',event=>{
    event.preventDefault();act(async()=>{
      const ticket=epoch,task=Number($('media-task').value),file=$('media-file').files?.[0];
      if(!Number.isSafeInteger(task)||task<1)throw Error('Podaj ID istniejącego zadania.');
      if(!file||file.size>24*1024*1024)throw Error('Wybierz plik JSON do 24 MiB.');
      const raw=await file.text();if(ticket!==epoch)return;
      let data;try{data=JSON.parse(raw);}catch{throw Error('Nie można odczytać pliku JSON.');}
      const map=value=>value&&typeof value==='object'&&!Array.isArray(value)&&Object.values(value).every(v=>typeof v==='string');
      if(!data||typeof data.purpose!=='string'||!map(data.files)||!map(data.images))
        throw Error('Plik musi zawierać cel (purpose), źródła (files) i obrazy (images).');
      const saved=await request(`/api/tasks/${task}/workspace-media-packages`,{method:'POST',body:JSON.stringify(data)});
      if(ticket!==epoch)return;
      $('media-file').value='';await onSaved(saved);
      if(ticket===epoch)message(`Zapisano paczkę #${saved.artifact_id} ze źródłami i obrazami. Możesz teraz uruchomić testy.`);
    });
  });
  return {clear(){epoch++;$('media-file').value='';$('media-task').value='';}};
}};
})();
