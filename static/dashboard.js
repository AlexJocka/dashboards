'use strict';
const reports = JSON.parse(document.getElementById('report-data').textContent);
const $ = id => document.getElementById(id);
const fmt = v => v === null ? '-' : new Intl.NumberFormat('ru-RU', {maximumFractionDigits: 1}).format(v);
const escapeHtml = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const sum = (rows,key) => {const values=rows.map(r=>r[key]).filter(v=>typeof v === 'number');return values.length ? values.reduce((a,b)=>a+b,0) : null;};
let current, filtered = [];
const filters = [['year-filter','year','Все годы'],['university-filter','university','Все организации'],['program-filter','program','Все программы']];

function loadReport() {
  current=reports[Number($('report-select').value)];
  $('demo-tag').hidden=!current.demo;
  $('page-title').textContent=current.code==='F02A'?'Целевые студенты и треки':current.title;
  $('form-tag').textContent=current.code+' · '+(current.code==='F02A'?'Сводная форма':'Отчёт');
  $('warnings').replaceChildren();
  current.warnings.forEach(w=>{const p=document.createElement('p');p.className='notice';p.textContent=w;$('warnings').append(p);});
  const students=Boolean(current.students);
  $('student-content').hidden=!students;
  $('filters').hidden=!students;
  $('other-content').hidden=students;
  if(!students){
    if(current.chart){
      const max=Math.max(1,...current.chart.values);
      $('other-content').innerHTML='<h2>Фактически обученные по месяцам</h2><div style="margin-top:25px">'+current.chart.labels.map((name,i)=>barGroup(name,null,current.chart.values[i],max)).join('')+'</div>';
    }else{$('other-content').innerHTML='<div class="empty-chart">Для этой формы визуализация пока недоступна.<br>Откройте демо F02A, чтобы посмотреть дашборд.</div>';}
    return;
  }
  for(const [id,key,label] of filters){
    const select=$(id);select.replaceChildren(new Option(label,''));
    [...new Set(current.students.records.map(r=>r[key]))].sort((a,b)=>a.localeCompare(b,'ru',{numeric:true})).forEach(v=>select.add(new Option(v,v)));
  }
  if($('student-search')) $('student-search').value='';
  render();
}

function barGroup(name,plan,contracts,max){
  const bar=(v,cls)=>v===null?'<div class="bar-track"><span class="bar-value">-</span></div>':`<div class="bar-track"><div class="bar ${cls}" style="width:${Math.max(0,v/max*100)}%" title="${cls==='plan'?'План':'Договоры'}: ${fmt(v)}"></div><span class="bar-value">${fmt(v)}</span></div>`;
  return `<div class="bar-group"><div class="bar-heading"><span class="bar-name">${escapeHtml(name)}</span><small>${plan>0&&contracts!==null?fmt(contracts/plan*100)+'% плана':''}</small></div>${plan===null?'':bar(plan,'plan')}${bar(contracts,'contracts')}</div>`;
}

function render(){
  const query=($('student-search')?.value||'').trim().toLocaleLowerCase('ru');
  filtered=current.students.records.filter(r=>filters.every(([id,key])=>!$(id).value||r[key]===$(id).value)&&(!query||[r.university,r.program,r.specialty].some(v=>v.toLocaleLowerCase('ru').includes(query))));
  const totals=Object.fromEntries(['plan','quota','contracts','studying','employed','terminated','graduates'].map(k=>[k,sum(filtered,k)]));
  const cards=[['studying','Продолжают обучение','Контингент на дату'],['employed','Трудоустроены','После завершения обучения'],['terminated','Договоры расторгнуты','На дату отчёта'],['graduates','К трудоустройству','План выпускаемых']];
  $('kpis').innerHTML=cards.map(([key,label,note])=>`<article class="metric"><h2 class="metric__label">${label}</h2><p class="metric__value" data-metric="${key}">${fmt(totals[key])}</p><p class="metric__note">${note}</p></article>`).join('');
  const groups=[...new Set(filtered.map(r=>r.university))].map(name=>{const rows=filtered.filter(r=>r.university===name);return {name,plan:sum(rows,'plan'),contracts:sum(rows,'contracts')};}).sort((a,b)=>(b.contracts||0)-(a.contracts||0));
  const max=Math.max(1,...groups.flatMap(r=>[r.plan||0,r.contracts||0]));
  $('university-count').textContent=`Организаций: ${groups.length}`;
  $('comparison-chart').innerHTML=groups.length?groups.map(r=>barGroup(r.name,r.plan,r.contracts,max)).join(''):'<div class="empty-chart">Нет данных по выбранным фильтрам</div>';
  renderStatus(totals);
  $('row-count').textContent=filtered.length;
  $('detail-body').innerHTML=filtered.map(r=>`<tr><td><strong>${escapeHtml(r.university)}</strong><small>${escapeHtml(r.program)}</small></td><td>${escapeHtml(r.year)}</td>${['plan','quota','contracts','studying','employed','terminated'].map(k=>`<td class="${k==='contracts'?'contract-cell':''}">${fmt(r[k])}</td>`).join('')}</tr>`).join('')||'<tr><td colspan="8">Нет заполненных строк по выбранным фильтрам</td></tr>';
}

function renderStatus(t){
  const statuses=[['Продолжают обучение',t.studying,'#42aaff'],['Трудоустроены',t.employed,'#202945'],['Договор расторгнут',t.terminated,'#d2d2da']];
  const known=statuses.reduce((a,s)=>a+(s[1]||0),0);
  const complete=statuses.every(s=>s[1]!==null)&&filtered.every(r=>['contracts','studying','employed','terminated'].every(k=>r[k]!==null));
  const valid=complete&&t.contracts!==null&&known<=t.contracts&&filtered.every(r=>r.studying+r.employed+r.terminated<=r.contracts);
  if(valid&&t.contracts>known)statuses.push(['Статус не указан',t.contracts-known,'#dce5ed']);
  const denominator=valid?t.contracts:null;
  const circle=2*Math.PI*57;
  let offset=0;
  const segments=denominator>0?statuses.map(([label,value,color])=>{const length=value/denominator*circle;const svg=`<circle cx="80" cy="80" r="57" fill="none" stroke="${color}" stroke-width="14" stroke-dasharray="${length} ${circle-length}" stroke-dashoffset="${-offset}"><title>${escapeHtml(label)}: ${fmt(value)}</title></circle>`;offset+=length;return svg;}).join(''):'';
  $('status-chart').innerHTML=`<div class="donut-wrap"><svg viewBox="0 0 160 160" role="img" aria-label="Распределение статусов студентов"><circle cx="80" cy="80" r="57" fill="none" stroke="#f0f4f8" stroke-width="14"/>${segments}</svg><div class="donut-center"><strong>${fmt(t.contracts)}</strong><span>всего договоров</span></div></div>`+statuses.map(([label,value,color])=>`<div class="status-row"><span class="status-label"><i style="--color:${color}"></i>${label}</span><span><strong>${fmt(value)}</strong><small>${denominator>0?fmt(value/denominator*100)+'%':'-'}</small></span></div>`).join('')+(!valid&&filtered.length?'<p class="notice">Для распределения статусов нужны полные, согласованные значения. Показаны доступные суммы.</p>':'');
}

function exportCsv(){
  const keys=['university','program','year','plan','quota','contracts','studying','employed','terminated'];
  const header=['Организация','Программа','Год','План','Квоты','Договоры','Обучаются','Трудоустроены','Расторгнуты'];
  const cell=v=>'"'+String(v??'').replace(/^[=+@-]/,"'$&").replace(/"/g,'""')+'"';
  const csv=[header,...filtered.map(r=>keys.map(k=>r[k]))].map(row=>row.map(cell).join(';')).join('\r\n');
  const url=URL.createObjectURL(new Blob(['\uFEFF'+csv],{type:'text/csv;charset=utf-8'}));
  const a=document.createElement('a');a.href=url;a.download=current.demo?'Целевые_студенты_ДЕМО.csv':'Целевые_студенты.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
if(reports.length){
  $('report-select').addEventListener('change',loadReport);
  filters.forEach(([id])=>$(id).addEventListener('change',render));
  $('reset-filters').addEventListener('click',()=>{filters.forEach(([id])=>$(id).value='');if($('student-search'))$('student-search').value='';render();});
  $('student-search')?.addEventListener('input',render);
  $('export-csv').addEventListener('click',exportCsv);
  const requested=new URLSearchParams(window.location.search).get('file');
  const reportIndex=reports.findIndex(report=>report.filename===requested);
  if(reportIndex>=0) $('report-select').value=String(reportIndex);
  loadReport();
}
