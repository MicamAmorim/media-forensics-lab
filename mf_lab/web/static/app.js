const $ = (q) => document.querySelector(q);
const input = $('#fileInput'), dropzone = $('#dropzone'), chips = $('#fileChips');
const analyzeBtn = $('#analyzeBtn'), errorBox = $('#errorBox'), progress = $('#progress');
let selectedFiles = [];

function setFiles(files){ selectedFiles = [...files].slice(0,50); chips.innerHTML = selectedFiles.map(f => `<span class="chip" title="${escapeHtml(f.name)}">${escapeHtml(f.name)}</span>`).join(''); }
function escapeHtml(s){ return String(s).replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c])); }
function showError(msg){ errorBox.textContent = msg; errorBox.classList.remove('hidden'); }
function hideError(){ errorBox.classList.add('hidden'); }

dropzone.addEventListener('click', () => input.click());
dropzone.addEventListener('keydown', e => { if(e.key==='Enter'||e.key===' '){e.preventDefault();input.click();} });
input.addEventListener('change', () => setFiles(input.files));
['dragenter','dragover'].forEach(evt => dropzone.addEventListener(evt,e=>{e.preventDefault();dropzone.classList.add('drag')}));
['dragleave','drop'].forEach(evt => dropzone.addEventListener(evt,e=>{e.preventDefault();dropzone.classList.remove('drag')}));
dropzone.addEventListener('drop', e => setFiles([...e.dataTransfer.files].filter(f=>f.type.startsWith('image/') || /\.(heic|heif)$/i.test(f.name))));
$('#printBtn').addEventListener('click',()=>window.print());

function bars(data, maxValue){
  const entries = Object.entries(data); const max = Math.max(maxValue || 0, ...entries.map(([,v])=>Number(v)||0), 1);
  return entries.map(([label,value]) => `<div class="bar-row"><span class="bar-label" title="${escapeHtml(label)}">${escapeHtml(label)}</span><div class="track"><div class="fill" style="width:${Math.min(100,(Number(value)||0)/max*100)}%"></div></div><span class="bar-value">${Number(value)||0}</span></div>`).join('');
}

function summaryCards(s){
  const rows=[['Arquivos analisados',s.files],['Indicadores de triagem',s.screening_signals],['Revisão aprofundada',s.needs_review],['Conclusões inconclusivas',s.inconclusive]];
  return rows.map(([k,v])=>`<div class="summary-card"><small>${k}</small><strong>${v}</strong></div>`).join('');
}

function renderOverview(files){
  const chart=$('#overviewChart'); const values=Object.fromEntries(files.map(f=>[f.name,f.signal_total]));
  chart.innerHTML=`<h3>Indicadores por arquivo</h3><p>Contagem agregada de sinais de triagem emitidos pelos métodos executados.</p>${bars(values)}`;
}

function renderMethods(methods){
  return `<div class="method-list">${methods.map(m=>`<div class="method"><button type="button"><span>${escapeHtml(m.name)}</span><span class="method-state">${m.status==='error'?'erro':'detalhes'} ▾</span></button><div class="method-detail">${escapeHtml(m.summary)}</div></div>`).join('')}</div>`;
}

function renderFiles(files){
  $('#fileResults').innerHTML = files.map((f,i)=>{
    const review=f.triage_assessment==='needs_expert_review';
    return `<article class="file-card"><div class="preview"><span class="file-badge">#${String(i+1).padStart(2,'0')}</span><img src="${f.preview_url}" alt="Prévia de ${escapeHtml(f.name)}" loading="lazy"></div><div class="file-content"><div class="file-head"><div><h3>${escapeHtml(f.name)}</h3><div class="hash">SHA-256 ${escapeHtml(f.sha256||'')}</div></div><span class="status ${review?'review':'ok'}">${review?'revisão recomendada':'triagem registrada'}</span></div><div class="mini-chart">${bars(f.signal_counts)}</div><div class="notice"><b>Conclusão automática:</b> ${escapeHtml(String(f.evidentiary_conclusion||'inconclusivo'))}. Perfil: ${escapeHtml(f.profile||'')}.</div>${renderMethods(f.methods)}</div></article>`;
  }).join('');
  document.querySelectorAll('.method button').forEach(btn=>btn.addEventListener('click',()=>btn.parentElement.classList.toggle('open')));
}

analyzeBtn.addEventListener('click', async()=>{
  hideError(); if(!selectedFiles.length){ showError('Selecione pelo menos uma imagem.'); return; }
  progress.classList.remove('hidden'); analyzeBtn.disabled=true; analyzeBtn.textContent='Analisando…';
  const form=new FormData(); selectedFiles.forEach(f=>form.append('files',f,f.name)); form.append('profile',$('#profile').value);
  try{
    const res=await fetch('/api/analyze',{method:'POST',body:form}); const data=await res.json().catch(()=>({error:'Resposta inválida do servidor.'}));
    if(!res.ok) throw new Error(data.error||`Falha HTTP ${res.status}`);
    $('#results').classList.remove('hidden'); $('#runTitle').textContent=data.run_id; $('#summaryCards').innerHTML=summaryCards(data.summary);
    $('#downloadDocx').href=data.downloads.docx; $('#downloadMd').href=data.downloads.md; $('#downloadJson').href=data.downloads.json;
    renderOverview(data.files); renderFiles(data.files); $('#results').scrollIntoView({behavior:'smooth',block:'start'});
  }catch(err){ showError(err.message||String(err)); }
  finally{ progress.classList.add('hidden'); analyzeBtn.disabled=false; analyzeBtn.textContent='Executar análise'; }
});
