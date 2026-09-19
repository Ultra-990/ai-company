/* Read-only source inspection. No model, source execution or implicit runner calls. */
(()=>{'use strict';
  const node=(tag,text)=>{const n=document.createElement(tag);if(text)n.textContent=text;return n;};
  window.PackageProfile={create({binding,request,act}){
    const section=node('section'),heading=node('h3','Projekt z wieloma modułami'),
      button=node('button','Sprawdź strukturę i składnię — bez uruchamiania'),output=node('div');
    button.type='button';output.setAttribute('aria-live','polite');
    section.append(heading,node('p','Sprawdzenie zgodności z przygotowywanym profilem Python. Nie wykonuje aplikacji ani nie zalicza testów.'),button,output);
    button.addEventListener('click',()=>act(async()=>{
      const result=await request(`/api/tasks/${binding.task_id}/workspace-packages/${binding.artifact_id}/multifile-inspection`);
      if(result.task_id!==binding.task_id||result.package_id!==binding.artifact_id||result.package_checksum!==binding.checksum)
        throw Error('Wynik kontroli dotyczy innej wersji paczki.');
      output.replaceChildren(node('p',result.compatible?'Struktura i składnia zgodne z profilem wielomodułowym.':'Paczka wymaga dostosowania do profilu wielomodułowego.'));
      const list=node('ul');
      for(const issue of result.issues||[]){
        const row=node('li',`${issue.path||'Paczka'}${issue.line?` · wiersz ${issue.line}`:''}: ${issue.message}`);list.append(row);
      }
      output.append(list,node('p','Dla zgodnej paczki dostępne są testy, bezstanowy podgląd, odbiór tej wersji i wydanie ZIP z instrukcjami. Ta kontrola nie uruchomiła aplikacji. Automatyczne poprawki nie są jeszcze dostępne. Zgodna składnia nie potwierdza działania ani bezpieczeństwa aplikacji.'));
    }));return section;
  }};
})();
