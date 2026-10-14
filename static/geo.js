/* Smart location search, hyperlocal data panel, and the geographic risk map. */
const GEOS={cur:null,last:null,p:null,seq:0,fetched:0,mapKey:null,mode:'none'},GEOLIST=new Map();
const gq=$('gq'),gl=$('gl');let gitems=[],gact=-1,greq=0,gctl=null,gdeb=null,glastQ='';
const fmtCo=(la,lo)=>`${Math.abs(la).toFixed(3)}°${la>=0?'N':'S'}, ${Math.abs(lo).toFixed(3)}°${lo>=0?'E':'W'}`;
const TYPE_TAG={Observed:'live',Forecast:'ref',Historical:'hist','Model estimate':'est',Simulated:'sim',Unavailable:'na'};
const ttag=t=>`<span class="tag ${TYPE_TAG[t]||'na'}">${esc(t)}</span>`,num=(v,d=1)=>v==null?'n/a':(+v).toFixed(d).replace(/\.0+$/,'');
function gmsg(t,isErr,retry){const e=$('gmsg');e.className=isErr?'err':'';e.textContent=t||'';if(retry){const b=document.createElement('button');b.className='btn';b.style.cssText='padding:4px 10px;font-size:12px;margin:0 0 0 8px';b.textContent='Retry';b.onclick=retry;e.appendChild(b)}}
const gspin=on=>{$('gspin').hidden=!on};
function closeList(){gl.hidden=true;gq.setAttribute('aria-expanded','false');gq.removeAttribute('aria-activedescendant');gact=-1}
function renderList(q,res){gl.innerHTML='';
 if(!res.length)gl.innerHTML=`<li class="empty" role="presentation">No place found for “${esc(q)}”. Check the spelling or try a nearby city.</li>`;
 else res.forEach((p,i)=>{const li=document.createElement('li');li.id='go'+i;li.setAttribute('role','option');li.setAttribute('aria-selected','false');
  const sub=[p.admin2&&p.admin2!==p.name?p.admin2:null,p.admin1,p.country].filter(Boolean).join(', '),extra=[p.population?'pop. '+Number(p.population).toLocaleString('en-IN'):null,p.lat.toFixed(2)+', '+p.lon.toFixed(2)].filter(Boolean).join(' · ');
  li.innerHTML=`<span class="ic" aria-hidden="true">📍</span><span class="t"><b>${esc(p.name)}</b><span>${esc(sub)}</span><span style="display:block;font-size:12px">${esc(extra)}</span></span>`;li.onmousedown=e=>{e.preventDefault();pick(p)};gl.appendChild(li)});
 gl.hidden=false;gq.setAttribute('aria-expanded','true')}
function setAct(i){const lis=[...gl.querySelectorAll('li[role=option]')];if(!lis.length)return;gact=(i+lis.length)%lis.length;lis.forEach((l,k)=>l.setAttribute('aria-selected',k==gact));gq.setAttribute('aria-activedescendant',lis[gact].id);lis[gact].scrollIntoView({block:'nearest'})}
async function gsearch(q,enter){const my=++greq;if(gctl)gctl.abort();gctl=new AbortController();gspin(true);
 try{const r=await fetch('/api/locations/search?q='+enc(q),{signal:gctl.signal});let j={};try{j=await r.json()}catch(e){}
  if(my!=greq)return;
  if(!r.ok){gitems=[];closeList();gmsg(j.message||'Location search is unavailable. Please try again.',true,()=>gsearch(q));return}
  gitems=j.results||[];glastQ=q;gmsg(j.degraded?j.message:'',false);renderList(q,gitems);if(enter&&gitems.length===1)pick(gitems[0])}
 catch(e){if(e.name==='AbortError')return;if(my==greq){gitems=[];closeList();gmsg('Could not reach the server. Check your connection and try again.',true,()=>gsearch(q))}}
 finally{if(my==greq)gspin(false)}}
gq.addEventListener('input',()=>{clearTimeout(gdeb);const q=gq.value.trim();$('gclr').hidden=!gq.value;if(q.length<2){gitems=[];closeList();gmsg('');if(gctl)gctl.abort();gspin(false);return}gdeb=setTimeout(()=>gsearch(q),250)});
gq.addEventListener('keydown',e=>{
 if(e.key==='ArrowDown'){e.preventDefault();if(gl.hidden&&gitems.length){gl.hidden=false;gq.setAttribute('aria-expanded','true')}setAct(gact+1)}
 else if(e.key==='ArrowUp'){e.preventDefault();setAct(gact-1)}
 else if(e.key==='Enter'){e.preventDefault();const q=gq.value.trim();if(gact>=0&&gitems[gact])pick(gitems[gact]);else if(gitems.length&&q===glastQ)pick(gitems[0]);else if(q.length>=2){clearTimeout(gdeb);gsearch(q,true)}else gmsg('Type at least 2 characters to search.',true)}
 else if(e.key==='Escape'){closeList()}});
gq.addEventListener('focus',()=>{if(gitems.length&&gq.value.trim()===glastQ){gl.hidden=false;gq.setAttribute('aria-expanded','true')}});
gq.addEventListener('blur',()=>setTimeout(closeList,150));
$('gclr').onclick=()=>{gq.value='';gitems=[];closeList();gmsg('');$('gclr').hidden=true;gq.focus()};
$('gme').onclick=()=>{if(!navigator.geolocation){gmsg('Your browser does not support location access. Search for a place by name instead.',true);return}
 gmsg('Waiting for your browser’s location permission…');
 navigator.geolocation.getCurrentPosition(pos=>loadGeo({lat:pos.coords.latitude,lon:pos.coords.longitude,label:null}),er=>gmsg(er.code===1?'Location permission was denied. You can still search for a place by name.':'Your location could not be determined. Try searching by name.',true),{timeout:12000,maximumAge:60000})};
function pick(p){if(p.feature==='BUILTIN'){gq.value='';$('gclr').hidden=true;closeList();enterDemo(p.name);gmsg('The geocoding service is unavailable, so the demo data for '+p.name+' is shown instead.');return}gq.value=p.label;$('gclr').hidden=false;closeList();loadGeo(p)}
/* ---------- loading, errors, stale-data protection ---------- */
const secs=()=>document.querySelectorAll('section');
function busyOn(label){secs().forEach(s=>s.classList.add('updating'));gspin(true);gmsg('Loading data for '+label+'…');const p=$('gpanel');p.hidden=false;
 p.innerHTML='<div class="gpg">'+[0,1,2,3].map(()=>'<div class="card"><div class="sk" style="height:16px;width:50%;margin-bottom:12px"></div><div class="sk" style="height:34px;width:70%;margin-bottom:12px"></div><div class="sk" style="height:12px;margin-bottom:8px"></div><div class="sk" style="height:12px;width:80%"></div></div>').join('')+'</div>'}
function busyOff(){secs().forEach(s=>s.classList.remove('updating'));gspin(false)}
function setNA(j){document.body.classList.add('geo-na');const b=$('gbanner');b.hidden=false;b.textContent=j.unavailable||'Risk scoring is unavailable for this location.'}
function clearNA(){document.body.classList.remove('geo-na');$('gbanner').hidden=true}
async function loadGeo(p,refresh){const my=++GEOS.seq,label=p.label||'your location';busyOn(label);
 try{const r=await fetch('/api/location-risk',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({lat:p.lat,lon:p.lon,name:p.label||undefined,admin1:p.admin1,admin2:p.admin2,country:p.country,country_code:p.country_code,population:p.population,elevation:p.elevation,timezone:p.timezone,refresh:!!refresh})});
  let j={};try{j=await r.json()}catch(e){}
  if(my!==GEOS.seq)return;   // a newer search superseded this response
  if(!r.ok){busyOff();$('gpanel').hidden=!GEOS.last;if(GEOS.last)renderPanel(GEOS.last);gmsg(j.message||'Could not load data for this location.',true,()=>loadGeo(p,refresh));return}
  GEOS.p={...p,label:j.location.label};GEOS.last=j;GEOS.fetched=Date.now();gmsg('');if(j.risk){GEOLIST.delete(j.risk.name);GEOLIST.set(j.risk.name,{risk:j.risk,p:GEOS.p});while(GEOLIST.size>8)GEOLIST.delete(GEOLIST.keys().next().value)}
  if(!j.risk){GEOS.cur=null;setNA(j);renderPanel(j);renderChip(j);busyOff();return}
  clearNA();GEOS.cur=j.risk;renderPanel(j);renderChip(j);show(j.risk);busyOff();
  setTimeout(()=>{const e=$('dash');if(e&&e.getBoundingClientRect().top<-200)e.scrollIntoView({behavior:'smooth'})},50)}
 catch(e){if(my===GEOS.seq){busyOff();if(GEOS.last)renderPanel(GEOS.last);else $('gpanel').hidden=true;gmsg('Could not reach the server. Check your connection and try again.',true,()=>loadGeo(p,refresh))}}}
/* ---------- selected-location indicator + freshness ---------- */
function ago2(ms){const m=Math.round(ms/60000);return m<1?'just now':m<60?m+' min ago':Math.round(m/60)+' h ago'}
function updFresh(){const e=$('gfresh');if(!e||!GEOS.fetched)return;const age=Date.now()-GEOS.fetched;e.textContent='Updated '+ago2(age)+(age>20*60000?' · data may be out of date, please refresh':'');e.style.color=age>20*60000?'#ffb347':''}
setInterval(updFresh,30000);
function renderChip(j){const c=$('gsel');c.hidden=false;
 if(!j){c.innerHTML=`<span aria-hidden="true">🧪</span><b>Demo data: ${esc(cur?cur.name:'')}</b><span class="mu">Simulated Delhi NCR scenario, not real measurements. Search for a place to use real forecast data.</span>`;return}
 const l=j.location;c.innerHTML=`<span aria-hidden="true">📍</span><b>${esc(l.label)}</b><span class="mu">${fmtCo(l.lat,l.lon)}${l.elevation!=null?' · elev. '+Math.round(l.elevation)+' m':''}${l.timezone?' · '+esc(l.timezone):''}</span><span id="gfresh" class="mu"></span><button class="btn" id="grefresh" type="button" style="margin:0;padding:6px 12px;font-size:13px">⟳ Refresh data</button><button class="btn" id="gdemo" type="button" style="margin:0;padding:6px 12px;font-size:13px">Use demo scenario</button>`;
 $('grefresh').onclick=()=>loadGeo(GEOS.p,true);$('gdemo').onclick=()=>{gq.value='';$('gclr').hidden=true;show(L.find(x=>x.name=='Gurugram'))};updFresh()}
/* ---------- data panel ---------- */
function chartSVG(c){const W=680,H=230,pl=40,pr=40,pt=16,pb=34,n=c.tmax.length,X=i=>pl+i*(W-pl-pr)/(n-1),tv=c.tmax.concat(c.tmin).filter(v=>v!=null),t0=Math.floor(Math.min(...tv)-2),t1=Math.ceil(Math.max(...tv)+2),Y=v=>pt+(t1-v)/(t1-t0)*(H-pt-pb),pm=Math.max(10,...c.precip.filter(v=>v!=null)),YP=v=>H-pb-v/pm*(H-pt-pb)*.55;
 const line=a=>a.map((v,i)=>v==null?'':(i&&a[i-1]!=null?'L':'M')+X(i).toFixed(1)+','+Y(v).toFixed(1)).join('');
 const bars=c.precip.map((v,i)=>v?`<rect x="${X(i)-6}" y="${YP(v)}" width="12" height="${H-pb-YP(v)}" fill="${i<c.split?'#27d3f5':'#27d3f588'}" rx="2"><title>${c.dates[i]}: ${v} mm</title></rect>`:'').join('');
 const lab=c.dates.map((d,i)=>i%3==0?`<text x="${X(i)}" y="${H-12}" fill="#8aa0bd" font-size="10" text-anchor="middle">${d.slice(5)}</text>`:'').join('');
 return `<svg viewBox="0 0 ${W} ${H}" width="100%" role="img" aria-label="21-day maximum temperature and rainfall chart"><rect x="${X(c.split)}" y="${pt}" width="${W-pr-X(c.split)}" height="${H-pt-pb}" fill="#ffffff08"/><line x1="${X(c.split)}" x2="${X(c.split)}" y1="${pt}" y2="${H-pb}" stroke="#ffffff55" stroke-dasharray="4"/>
  <text x="${X(c.split)-6}" y="${pt+10}" fill="#9fc4ff" font-size="11" text-anchor="end">Observed (analysis)</text><text x="${X(c.split)+6}" y="${pt+10}" fill="#ffb347" font-size="11">Forecast</text>
  ${[t0,(t0+t1)/2,t1].map(v=>`<text x="4" y="${Y(v)+4}" fill="#8aa0bd" font-size="10">${Math.round(v)}°</text><line x1="${pl}" x2="${W-pr}" y1="${Y(v)}" y2="${Y(v)}" stroke="#ffffff14"/>`).join('')}${bars}
  <path d="${line(c.tmin)}" stroke="#7fb4ff88" stroke-width="1.5" fill="none"/><path d="${line(c.tmax)}" stroke="#ff8a1f" stroke-width="2.5" fill="none"/>${lab}
  <text x="${W-4}" y="${pt+10}" fill="#27d3f5" font-size="10" text-anchor="end">bars: rain (mm)</text></svg>`}
function renderPanel(j){const p=$('gpanel'),d=j.data,l=j.location,r=j.risk,h=d.heat||{},rn=d.rain||{},w=d.water||{},g=d.groundwater||{},rv=d.river,cu=d.current;p.hidden=false;
 const row=(a,b)=>`<div class="krow"><span>${a}</span><b>${b}</b></div>`,sc=(v,lv)=>v==null?'n/a':`<span style="color:${col[lv]}">${v} ${lv}</span>`;
 const idc=`<div class="card"><h3>Selected location</h3><div style="font-size:18px;font-weight:800">${esc(l.label)}</div>${row('Coordinates',fmtCo(l.lat,l.lon))}${l.elevation!=null?row('Elevation',Math.round(l.elevation)+' m'):''}${l.admin2?row('District',esc(l.admin2)):''}${l.admin1?row('State / region',esc(l.admin1)):''}${l.country?row('Country',esc(l.country)):''}${l.population?row('Population',Number(l.population).toLocaleString('en-IN')):''}
  <div class="mu" style="font-size:12px;margin-top:8px">Data fetched ${esc(d.fetched_at?d.fetched_at.replace('T',' ').slice(0,16)+' UTC':'n/a')}${d.data_time?'; model time '+esc(d.data_time.replace('T',' ')):''}</div></div>`;
 const cc=cu?`<div class="card"><h3>Current conditions ${ttag('Observed')}</h3><div class="gv">${num(cu.temp)}<span class="gu"> °C</span></div>${row('Feels like',num(cu.feels)+' °C')}${row('Humidity',num(cu.humidity,0)+' %')}${row('Wind',num(cu.wind)+' km/h')}${row('Rain now',num(cu.precip)+' mm')}<div class="mu" style="font-size:12px;margin-top:6px">Model analysis for the grid cell, not a station reading.</div></div>`:'<div class="card"><h3>Current conditions '+ttag('Unavailable')+'</h3><p class="mu">The provider returned no current conditions.</p></div>';
 const hc=`<div class="card"><h3>Heat ${ttag('Forecast')}</h3><div class="gv">${num(h.max7)}<span class="gu"> °C max, next 7 days</span></div>${h.normal!=null?row('Normal max for this time of year',num(h.normal)+' °C '+ttag('Historical')):''}${h.anomaly!=null?row('Heat anomaly',(h.anomaly>0?'+':'')+num(h.anomaly)+' °C'):row('Heat anomaly','unavailable')}${h.hot_days!=null?row('Hot days (≥ normal + 4°C)',h.hot_days+' of 7'):''}${h.spell?row('Heat indicator',esc(h.spell)):''}${r?row('Heat score',sc(r.heat,r.heat_level)+' '+ttag('Model estimate')):''}<div class="mu" style="font-size:12px;margin-top:6px">${esc(h.note||'')}</div></div>`;
 const pc=rn.normal14!=null?Math.round(rn.past14/rn.normal14*100):null,rc=`<div class="card"><h3>Rainfall and monsoon ${ttag('Observed')}</h3><div class="gv">${num(rn.past14)}<span class="gu"> mm, last 14 days</span></div>${rn.normal14!=null?row('Normal for 14 days',num(rn.normal14)+' mm '+ttag('Historical')):''}${pc!=null?row('Share of normal',pc+' %'):''}${rn.deficit_pct!=null?row('Rainfall deficit',rn.deficit_pct+' %'):''}${row('Forecast, next 7 days',num(rn.next7)+' mm '+ttag('Forecast'))}${rn.max_day!=null?row('Heaviest forecast day',num(rn.max_day)+' mm'):''}${rn.prob_max!=null?row('Highest rain probability',rn.prob_max+' %'):''}${rn.annual_normal?row('Annual normal',rn.annual_normal+' mm'):''}${row('Monsoon-season window',rn.monsoon_window?'Yes (Jun to Sep, South Asia)':'No / not applicable')}<div class="mu" style="font-size:12px;margin-top:6px">${esc(rn.note||'')}</div></div>`;
 const fc=`<div class="card"><h3>Flood and waterlogging exposure</h3>${r?`<div class="gv" style="color:${col[r.flood_level]}">${r.flood}<span class="gu"> ${r.flood_level} ${ttag('Model estimate')}</span></div>${row('Likely range',r.flood_lo+' to '+r.flood_hi)}${row('Storm used',num(r.flood_parts['Storm rainfall (mm/day)'])+' mm/day '+ttag('Forecast'))}${row('Impervious cover (proxy)',r.flood_parts['Impervious cover (%)']+' %')}`:'<p class="mu">Flood score unavailable.</p>'}${rv?row('River discharge, forecast peak',rv.peak+' m³/s '+ttag('Forecast'))+(rv.ratio?row('Peak vs recent mean',rv.ratio+'×'):''):row('River discharge','Unavailable '+ttag('Unavailable'))}<div class="mu" style="font-size:12px;margin-top:6px">Rule-based index (runoff vs drainage). River discharge comes from a global model and is not a flood warning.</div></div>`;
 const wc=`<div class="card"><h3>Water scarcity and demand</h3>${r?`<div class="gv" style="color:${col[r.scar_level]}">${r.scarcity}<span class="gu"> ${r.scar_level} ${ttag('Model estimate')}</span></div>${row('Likely range',r.scar_lo+' to '+r.scar_hi)}`:''}${w.balance_14d!=null?row('Water balance, 14 days',num(w.balance_14d)+' mm '+ttag('Observed')):''}${w.et0_14d!=null?row('Evapotranspiration, 14 days',num(w.et0_14d)+' mm'):''}${w.soil_moisture!=null?row('Soil moisture',num(w.soil_moisture,3)+' m³/m³'):''}${row('Water demand','Modelled estimate '+ttag('Model estimate'))}<div class="mu" style="font-size:12px;margin-top:6px">No local consumption data is loaded; demand is a modelled assumption.</div></div>`;
 const gc=`<div class="card"><h3>Groundwater ${ttag(g.available?'Historical':'Unavailable')}</h3>${g.available?`<div class="gv">${g.stage}<span class="gu"> % extraction</span></div>${row('Category',esc(g.category))}${row('Reference area',esc(g.area)+' ('+g.dist_km+' km)')}<div class="mu" style="font-size:12px;margin-top:6px">${esc(g.source)}</div>`:`<p class="mu">${esc(g.note||'No reliable groundwater data is available for this location.')}</p><div class="mu" style="font-size:12px">The model assumed a neutral value and its uncertainty was widened.</div>`}</div>`;
 const chart=d.chart?`<div class="card" style="grid-column:1/-1"><h3>Last 14 days and next 7 days</h3>${chartSVG(d.chart)}</div>`:'';
 const sm=r&&j.summary?`<div class="card" style="grid-column:1/-1"><h3>Risk summary and recommendations ${ttag('Model estimate')}</h3><p style="color:#cfe0f5">${esc(j.summary)}</p>${(j.recommendations||[]).length?'<ol style="margin:10px 0 0 20px;color:#cfe0f5">'+j.recommendations.map(z=>`<li><b>${esc(z.title)}</b> <span class="mu">(${esc(z.urgency)}, ${esc(z.audience)}): ${esc(z.why)}</span></li>`).join('')+'</ol>':''}<p class="mu" style="font-size:12px;margin-top:10px">Experimental estimates from a model trained on simulated data. Not an official warning. Community reports are unverified.</p></div>`:'';
 const prov=`<div class="card" style="grid-column:1/-1"><h3>Data sources, types and timestamps</h3><div class="x"><table class="tt"><tr><th>Indicator</th><th>Value</th><th>Type</th><th>Source</th><th>Time</th></tr>${d.provenance.map(z=>`<tr><td>${esc(z.name)}${z.note?`<div class="mu" style="font-size:12px">${esc(z.note)}</div>`:''}</td><td>${z.value==null?'n/a':esc(z.value)+' <span class="mu">'+esc(z.unit||'')+'</span>'}</td><td>${ttag(z.type)}</td><td class="mu">${esc(z.source)}</td><td class="mu">${esc(z.time||'n/a')}</td></tr>`).join('')}</table></div></div>`;
 const val2=j.validation?`<div class="card" style="grid-column:1/-1"><h3>Model input check</h3><p class="mu" style="font-size:13px">Each value is checked against the range the model was trained on. Values outside it are clipped and flagged.</p><div class="x"><table class="tt"><tr><th>Model input</th><th>Raw</th><th>Used</th><th>Unit</th><th>Trained range</th><th>Basis</th></tr>${j.validation.map(v=>`<tr><td>${esc(v.feature)}</td><td>${v.raw}</td><td>${v.used}${v.clipped?' <span class="tag est">clipped</span>':''}</td><td class="mu">${esc(v.unit)}</td><td class="mu">${esc(v.trained_range)}</td><td class="mu">${esc(v.source)}</td></tr>`).join('')}</table></div></div>`:'';
 const lim=`<div class="card" style="grid-column:1/-1"><h3>Limitations and missing data</h3><ul class="wl">${(d.warnings||[]).concat(d.limitations||[]).map(x=>`<li>⚠ ${esc(x)}</li>`).join('')}</ul></div>`;
 p.innerHTML=`<div class="gpg">${idc}${cc}${hc}${rc}${fc}${wc}${gc}${sm}${chart}${val2}${prov}${lim}</div>`}
/* ---------- geographic risk map (Leaflet) ---------- */
let LM=null,LMG=null,MAPCFG={url:'https://tile.openstreetmap.org/{z}/{x}/{y}.png',attribution:'© OpenStreetMap contributors',darken:true,max_zoom:19};
fetch('/api/map-config').then(r=>r.json()).then(c=>{if(c&&c.url)MAPCFG=c}).catch(()=>{});
function mapNote(show){let n=$('lmapnote');if(!n){n=document.createElement('div');n.id='lmapnote';n.className='lmapnote';n.textContent='Map tiles could not be loaded. Markers still show each location.';$('mapbox').appendChild(n)}n.style.display=show?'block':'none'}
function mapInit(){if(LM||!window.LF)return;const el=$('mapbox');el.innerHTML='';el.setAttribute('role','region');el.setAttribute('aria-label','Geographic risk map');
 LM=LF.map(el,{scrollWheelZoom:false}).setView([28.5,77.1],8);const cfg=MAPCFG,tl=LF.tileLayer(cfg.url,{maxZoom:cfg.max_zoom||19,attribution:cfg.attribution}).addTo(LM);if(cfg.darken)el.classList.add('map-dark');let te=0;tl.on('tileerror',()=>{if(++te===4)mapNote(true)});tl.on('tileload',()=>{if(te>=4)mapNote(false);te=0});LMG=LF.layerGroup().addTo(LM);setTimeout(()=>LM.invalidateSize(),300);addEventListener('resize',()=>LM&&LM.invalidateSize())}
function draw(){mapInit();if(!LM)return;LMG.clearLayers();const pts=[],ck=cur?cur.name:'',gm=GEOS.mode==='geo';
 if(gm){GEOLIST.forEach(({risk,p},name)=>{const v=val(risk),c=LV(v),sel=name===ck,m=LF.circleMarker([risk.lat,risk.lon],{radius:sel?16:10,color:'#fff',weight:sel?3:1.5,fillColor:c,fillOpacity:.9}).addTo(LMG);m.bindTooltip(`${name}: ${v}`);if(!sel)m.on('click',()=>loadGeo(p));pts.push([risk.lat,risk.lon])})}
 else L.forEach(l=>{if(l.lat==null)return;const v=val(l),c=LV(v),sel=ck===l.name,m=LF.circleMarker([l.lat,l.lon],{radius:sel?13:9,color:sel?'#fff':c,weight:sel?3:1.5,fillColor:c,fillOpacity:.8}).addTo(LMG);m.bindTooltip(`${l.name}: ${v}`);m.on('click',()=>show(l));pts.push([l.lat,l.lon])});
 const key=gm?ck:'demo';if(GEOS.mapKey!==key){GEOS.mapKey=key;if(gm&&GEOS.cur)LM.setView([GEOS.cur.lat,GEOS.cur.lon],9,{animate:true});else if(pts.length)LM.fitBounds(pts,{padding:[30,30]})}
 setTimeout(()=>LM.invalidateSize(),50)}
/* ---------- keep demo/searched state consistent ---------- */
const _showG=show;show=function(l){
 if(l&&!l.geo){GEOS.cur=null;GEOS.last=null;clearNA();if($('gpanel'))$('gpanel').hidden=true;setMode('demo')}
 if(l&&l.geo)setMode('geo');
 _showG(l);
 if(l&&l.geo)$('st').textContent='· Data: searched location (Open-Meteo analysis and forecast). Scores are experimental model estimates.';
 else if(l){renderChip(null);pipeline();document.querySelectorAll('#demochips button').forEach(b=>b.classList.toggle('on',b.dataset.n===l.name))}};
/* ---------- modes: nothing until a place or demo data is chosen ---------- */
function setMode(m){GEOS.mode=m;const b=document.body;b.classList.toggle('no-loc',m==='none');b.classList.toggle('demo-mode',m==='demo');b.classList.toggle('geo-mode',m==='geo');$('demobtn').setAttribute('aria-pressed',String(m==='demo'))}
function enterDemo(name){const l=L.find(x=>x.name===name)||L[0];if(!l)return;GEOS.seq++;busyOff();gq.value='';$('gclr').hidden=true;closeList();gmsg('');$('demochips').hidden=false;$('demobtn').setAttribute('aria-expanded','true');show(l);setTimeout(()=>{const e=$('dash');if(e&&e.getBoundingClientRect().top<-200)e.scrollIntoView({behavior:'smooth'})},50)}
function fillDemoChips(){$('demochips').innerHTML=L.map(l=>`<button type="button" data-n="${esc(l.name)}">${esc(l.name)}</button>`).join('')}
$('demobtn').onclick=()=>{const c=$('demochips'),open=c.hidden;c.hidden=!open;$('demobtn').setAttribute('aria-expanded',String(open));if(open&&!c.children.length&&L.length)fillDemoChips()};
$('demochips').onclick=e=>{const b=e.target.closest('button');if(b)enterDemo(b.dataset.n)};
async function quickSearch(n){gq.value=n;$('gclr').hidden=false;await gsearch(n,false);if(gitems.length)pick(gitems[0])}
$('welcome').onclick=e=>{const b=e.target.closest('button[data-q]');if(b)quickSearch(b.dataset.q)};
function noLocHint(){const e=$('dash');e.scrollIntoView({behavior:'smooth'});gmsg('Search for a place or open Demo data first, then every section will show its results.');const w=$('welcome');w.classList.add('flash');setTimeout(()=>w.classList.remove('flash'),1200);gq.focus({preventScroll:true})}
document.addEventListener('click',e=>{const a=e.target.closest('a[href^="#"]');if(!a||!document.body.classList.contains('no-loc'))return;const id=a.getAttribute('href').slice(1);if(id&&id!=='dash'){e.preventDefault();noLocHint()}});
function ensureOpt(id,v){const s=$(id);if(s&&![...s.options].some(o=>o.value===v))s.add(new Option(v,v))}
