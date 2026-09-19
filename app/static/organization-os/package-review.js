/* Explicit owner decision for one immutable package; never automatic acceptance. */
(()=>{'use strict';
const node=(tag,text)=>{const el=document.createElement(tag);el.textContent=text;return el;};
window.PackageReview={create({run,request,act}){
  const section=node('section',''),load=node('button','Odbierz lub wycofaj odbiór tej paczki'),status=node('p','');
  load.type='button';status.setAttribute('aria-live','polite');section.append(load,status);
  let form=null,context=null,pending=null;
  load.addEventListener('click',()=>act(async()=>{
    context=null;pending=null;form?.remove();form=null;
    const data=await request(`/api/package-runs/${run.id}/package-review`);
    if(data.binding.source_checksum!==run.package_checksum||data.binding.package_id!==run.package_id)throw Error('Odbiór wskazuje inną paczkę.');
    context=data;status.textContent=data.accepted?'Ta wersja ma aktualny odbiór właściciela.':'Ta wersja oczekuje na odbiór właściciela.';
    form=node('form','');form.append(node('h4',`Odbiór paczki #${run.package_id}`),
      node('p',data.binding.scope.title),node('p',data.binding.scope.description||'Brak opisu zadania — zweryfikuj zakres przed odbiorem.'),
      node('p',`Źródła: ${data.binding.source_checksum}`),node('p',`Raport testów: ${data.binding.report_checksum}`),node('p',data.note));
    const field=(label,tag)=>{const outer=node('label',label),input=node(tag,'');outer.append(input);form.append(outer);return input;};
    const criteria=field('Sprawdzony zakres i kryteria odbioru','textarea');
    const evidence=field('Dowody i ograniczenia / powód wycofania','textarea');
    for(const input of [criteria,evidence]){input.required=true;input.minLength=10;input.maxLength=2000;}
    const decision=field('Decyzja właściciela','select');
    for(const [value,label] of [['','Wybierz decyzję'],['accept','Odbieram tę wersję'],['reject','Odrzucam / wycofuję odbiór']]){const option=node('option',label);option.value=value;decision.append(option);}decision.required=true;
    const confirm=field(' Potwierdzam sprawdzenie tej wersji i raportu. To nie jest publikacja ani odbiór klienta.','input');confirm.type='checkbox';confirm.required=true;
    const submit=node('button','Zapisz decyzję właściciela');submit.type='submit';form.append(submit);
    form.addEventListener('input',()=>{pending=null;});
    form.addEventListener('submit',event=>{event.preventDefault();if(!context||!confirm.checked||!['accept','reject'].includes(decision.value))return;
      return act(async()=>{
        pending=pending||{request_id:crypto.randomUUID(),context_checksum:context.context_checksum,
          accepted:decision.value==='accept',criteria:criteria.value,evidence:evidence.value,confirm_review:true};
        const result=await request(`/api/package-runs/${run.id}/package-review`,{method:'POST',body:JSON.stringify(pending)});
        status.textContent=`Zapisano decyzję #${result.review_id}. ${result.current?(result.recorded_accepted?'Wersja odebrana. Sprawdź gotowość wydania.':'Odbiór wycofany; wydanie jest wstrzymane.'):'Istnieje nowsza decyzja — odśwież formularz.'} Status zadania nie został zmieniony.`;
        context=null;form.remove();form=null;pending=null;
      });
    });section.append(form);
  }));return section;
}};
})();
