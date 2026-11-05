(()=>{
  if(window.__INSURANCE_FUND_ONLY__||new URLSearchParams(location.search).has('fundonly'))return;
  const CSS=":host,#am-app{--bg:#0c1420;--panel:#131f2c;--panel2:#192a3a;--line:#2a3b4c;--text:#e7eef6;--muted:#9badbe;--accent:#45c9c3;--blue:#70a6ee;--orange:#e4b16b;--red:#ef8a91;--green:#68c7a1;color:var(--text);font:14px/1.6 -apple-system,BlinkMacSystemFont,\"PingFang SC\",\"Microsoft YaHei\",sans-serif;display:block;background:var(--bg);min-height:100vh}\n*{box-sizing:border-box}body{margin:0}button,input,select{font:inherit}button,a,select{touch-action:manipulation}button{cursor:pointer}button:disabled{opacity:.5;cursor:wait}button:focus-visible,a:focus-visible,input:focus-visible,select:focus-visible{outline:2px solid var(--accent);outline-offset:3px}button,.am-btn{border:1px solid var(--line);border-radius:7px;padding:7px 14px;background:var(--panel2);color:var(--text);text-decoration:none;display:inline-flex;align-items:center;justify-content:center;gap:6px;white-space:nowrap}.primary{background:var(--accent);color:#092326;border-color:var(--accent);font-weight:650}.am-btn:hover,button:hover{filter:brightness(1.15)}.am-top{height:76px;padding:0 30px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid var(--line);gap:20px}.am-brand{display:flex;align-items:center;gap:12px}.am-mark{width:35px;height:35px;background:linear-gradient(145deg,#45c9c3,#2866a5);border-radius:8px;display:grid;place-items:center;color:white;font-weight:800;font-size:20px}.am-brand strong{font-size:20px;letter-spacing:.6px}.eyebrow{font-size:10px;letter-spacing:1.6px;color:var(--muted)}.top-actions{display:flex;gap:12px;align-items:center}.live-dot:before{content:\"\";display:inline-block;width:6px;height:6px;margin-right:7px;border-radius:50%;background:var(--accent)}.top-status{font-size:12px;color:var(--muted)}.market-tabs{display:flex;gap:8px;border-bottom:1px solid var(--line);padding:0 30px;min-height:51px;align-items:stretch}.market-tabs button{background:transparent;border:0;border-radius:0;padding:12px 22px;color:var(--muted)}.market-tabs button.active{color:var(--accent);border-bottom:2px solid var(--accent);background:linear-gradient(0deg,#45c9c30d,transparent)}.am-layout{display:grid;grid-template-columns:178px minmax(0,1fr);min-height:calc(100vh - 127px)}.am-side{border-right:1px solid var(--line);padding:25px 15px;display:flex;flex-direction:column;gap:7px}.side-label{color:var(--muted);font-size:11px;letter-spacing:1px;padding:5px 13px 12px}.am-side button{background:transparent;border:0;justify-content:flex-start;text-align:left;padding:11px 13px;color:var(--muted)}.am-side button.active{background:#45c9c314;color:var(--accent);border:1px solid #45c9c32c}.side-note{margin-top:auto;padding:20px 12px;font-size:11px;color:var(--muted);line-height:1.9}.am-content{padding:27px 30px 50px;max-width:1600px;width:100%;margin:0 auto}.page-heading{display:flex;justify-content:space-between;align-items:center;gap:15px;margin-bottom:23px}.page-heading h1{font-size:22px;margin:0 0 4px;font-weight:650}.subtle{font-size:12px;color:var(--muted)}.period-pill{background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:9px 14px;font-size:12px}.period-pill b{color:var(--accent);margin-left:10px}.kpi-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:16px;margin-bottom:22px}.kpi{background:var(--panel);border:1px solid var(--line);border-radius:9px;padding:19px 21px}.kpi .label{font-size:12px;color:var(--muted)}.kpi strong{display:block;font-size:29px;letter-spacing:-.5px;font-weight:650;margin:8px 0 2px;font-variant-numeric:tabular-nums}.kpi small{font-size:11px;color:var(--muted)}.down{color:var(--red)}.up{color:var(--green)}.panel{background:var(--panel);border:1px solid var(--line);border-radius:9px;padding:21px 23px;margin-bottom:19px;min-width:0}.panel h2{font-size:15px;margin:0;font-weight:650}.panel-head{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:17px}.panel-head small{color:var(--muted);font-size:11px}.panel-grid{display:grid;grid-template-columns:1.05fr 1fr;gap:19px}.section-nav{display:flex;gap:23px;border-bottom:1px solid var(--line);margin-bottom:22px}.section-nav button{border:0;border-bottom:2px solid transparent;border-radius:0;background:transparent;padding:10px 1px;color:var(--muted)}.section-nav button.active{color:var(--accent);border-bottom-color:var(--accent)}.bar-row{display:grid;grid-template-columns:95px 1fr 110px;gap:13px;align-items:center;margin:20px 0}.bar-label{font-size:12px}.bar-track{background:#29405175;height:11px;border-radius:3px;overflow:hidden}.bar-fill{height:100%;border-radius:3px;background:var(--accent)}.bar-value{text-align:right;font-size:12px;font-variant-numeric:tabular-nums}.bar-value small{display:block;font-size:10px;color:var(--muted)}.scope-note{border-top:1px solid var(--line);padding-top:12px;margin-top:13px;color:var(--muted);font-size:11px;line-height:1.8}.am-table-wrap{overflow:auto}.am-table{border-collapse:collapse;width:100%;font-size:12px;white-space:nowrap;font-variant-numeric:tabular-nums}.am-table th{text-align:right;color:var(--muted);font-weight:500;padding:10px 12px;border-bottom:1px solid var(--line);background:var(--panel2)}.am-table td{padding:11px 12px;border-bottom:1px solid #2a3b4c80;text-align:right}.am-table th:first-child,.am-table td:first-child{text-align:left}.am-table td.name{white-space:normal;min-width:210px;max-width:400px}.am-table tr:hover td{background:#45c9c306}.rank{color:var(--accent);font-weight:650}.callout{padding:13px 16px;background:#45c9c309;border:1px solid #45c9c329;border-radius:7px;color:var(--muted);font-size:12px;line-height:1.85;margin:15px 0}.callout b{color:var(--text)}.summary-list{padding:0 0 0 20px;color:var(--muted);font-size:13px}.summary-list li{margin-bottom:12px}.summary-list strong{color:var(--text)}.filters{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:16px}.filters input{flex:1;min-width:200px}input,select{background:var(--bg);color:var(--text);border:1px solid var(--line);border-radius:6px;padding:8px 10px}select{max-width:100%}.pager{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-top:17px}.pager .controls{display:flex;gap:8px}.empty,.loading{padding:50px 24px;text-align:center;color:var(--muted)}.spinner{display:inline-block;width:18px;height:18px;border:2px solid var(--line);border-top-color:var(--accent);border-radius:50%;animation:spin 1s linear infinite;margin-right:9px;vertical-align:middle}@keyframes spin{to{transform:rotate(360deg)}}.report-controls{display:flex;align-items:center;gap:12px;flex-wrap:wrap}.report-controls label{font-size:12px;color:var(--muted)}.report-paper{max-width:1050px;margin:0 auto;background:var(--panel);padding:35px;border:1px solid var(--line);border-radius:9px}.report-paper h1{font-size:24px;margin:0 0 8px}.report-paper h2{font-size:17px;border-bottom:1px solid var(--line);padding-bottom:10px;margin-top:35px}.report-paper h3{font-size:13px;margin:25px 0 12px;color:var(--accent)}.report-paper p{font-size:13px;line-height:1.95;color:var(--muted)}.report-paper .am-table{font-size:11px}.report-paper details{margin:16px 0;border:1px solid var(--line);border-radius:7px;padding:13px}.report-paper summary{cursor:pointer;color:var(--text);font-size:13px}.upload-area{max-width:950px}.upload-box{border:1px dashed #456477;border-radius:9px;background:#45c9c305;padding:28px;margin:17px 0}.upload-box label{display:block;font-size:13px;margin-bottom:9px}.upload-box input{display:block;width:100%;background:var(--panel);padding:18px;margin:8px 0 20px}.upload-state{white-space:pre-wrap;font-size:13px;padding:15px 18px;border:1px solid var(--line);border-radius:6px;margin:17px 0;background:var(--panel2)}.upload-state.error{border-color:#ef8a91;color:var(--red)}.upload-state.success{border-color:#68c7a1;color:var(--green)}.step-strip{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:20px 0}.step-strip span{background:var(--panel2);padding:12px 9px;text-align:center;border-radius:6px;font-size:12px}.history-list{margin-top:20px}.history-item{display:flex;justify-content:space-between;gap:15px;padding:12px 0;border-bottom:1px solid var(--line);font-size:12px}.history-item small{display:block;color:var(--muted)}.missing-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}.missing-card{padding:17px;background:var(--panel2);border-radius:7px}.missing-card span{display:block;font-size:11px;color:var(--muted)}.missing-card strong{font-size:20px;font-weight:500;display:block;margin:5px 0;color:var(--orange)}.scatter{width:100%;height:auto;display:block}.scatter text{fill:var(--muted);font-size:11px}.scatter line{stroke:var(--line)}.legend{display:flex;gap:15px;flex-wrap:wrap;font-size:11px;color:var(--muted)}.legend i{display:inline-block;width:7px;height:7px;border-radius:50%;margin-right:5px}.funds-frame{width:100%;height:calc(100vh - 127px);border:0;display:block;min-height:800px}.am-toast{position:fixed;right:25px;bottom:25px;background:var(--panel2);border:1px solid var(--accent);padding:14px 20px;border-radius:7px;z-index:10000;max-width:450px;font-size:12px}.mobile-only{display:none}.am-light{--bg:#f3f6f9;--panel:#fff;--panel2:#edf2f7;--line:#dbe3ea;--text:#172b3a;--muted:#637789;--accent:#078b88;--red:#b84f5b;--green:#178366;--blue:#467ab7;--orange:#a07527}.report-source{font-size:11px;color:var(--muted);margin-top:16px;overflow-wrap:anywhere}.wide-actions{display:flex;gap:9px;flex-wrap:wrap}.strategy-row{display:grid;grid-template-columns:minmax(250px,1fr) 150px 90px;gap:12px;padding:12px 0;border-bottom:1px solid var(--line);align-items:center}.strategy-row small{display:block;color:var(--muted)}.am-footer{font-size:11px;color:var(--muted);text-align:right;margin-top:25px}\n@media(min-width:1600px){.am-content{padding-left:40px;padding-right:40px}}@media(max-width:1100px){.am-layout{grid-template-columns:155px minmax(0,1fr)}.am-content{padding:22px 20px}.kpi-grid{gap:10px}.kpi{padding:16px}.kpi strong{font-size:24px}.panel-grid{grid-template-columns:1fr}.am-top{padding:0 20px}.am-brand strong{font-size:18px}.top-status{display:none}}@media(max-width:720px){.am-top{height:auto;min-height:72px;padding:14px 15px}.am-brand strong{font-size:17px}.eyebrow{font-size:8px}.top-actions{gap:7px}.top-actions button{font-size:11px;padding:5px 9px}.market-tabs{padding:0 10px}.market-tabs button{padding:12px 17px}.am-layout{display:block}.am-side{padding:10px 12px;flex-direction:row;border-right:0;border-bottom:1px solid var(--line);overflow:auto}.am-side button{padding:7px 13px;white-space:nowrap}.side-label,.side-note{display:none}.am-content{padding:20px 13px}.page-heading{align-items:flex-start;flex-direction:column}.page-heading h1{font-size:21px}.kpi-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.panel{padding:17px 14px}.bar-row{grid-template-columns:80px 1fr 90px;gap:8px}.report-paper{padding:22px 15px}.step-strip{grid-template-columns:1fr 1fr}.missing-grid{grid-template-columns:1fr}.strategy-row{grid-template-columns:1fr 120px}.strategy-row button{grid-column:2}.top-actions .admin-top{display:none}.funds-frame{height:calc(100vh - 122px)}}\n:host .am-shell{background:var(--bg);min-height:100vh}\n",CLOUD=location.hostname.endsWith('.ms.show')?'https://fund-panorama-wsy-1028.xmxmxm348190253.chatgpt.site':location.origin,MS='https://wangshuyang2126-fund-panorama-wsy.ms.show';
  const localFund=location.hostname.endsWith('.ms.show')||!!document.getElementById('deliveryBanner'),old=localFund?[...document.body.children].filter(e=>e.tagName!=='SCRIPT'):[];
  const requestFetch=(window.__INSURANCE_FETCH__||window.fetch).bind(window);
  const host=document.getElementById('am-app')||document.body.insertBefore(document.createElement('div'),document.body.firstChild);host.id='am-app';
  const root=host.attachShadow({mode:'open'}),state={market:'insurance',page:new URLSearchParams(location.search).has('admin')?'upload':'analytics',module:'market',meta:null,data:null,cache:{},report:null,reportMonth:null,category:'',manager:'',search:'',sort:'size',pageNo:1,admin:false};
  const esc=s=>String(s??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
  const fmt=(n,d=2)=>n===null||n===undefined?'待补':Number(n).toLocaleString('zh-CN',{minimumFractionDigits:d,maximumFractionDigits:d}),pct=n=>n===null||n===undefined?'待补':fmt(n*100)+'%',cats=['固定收益类（非货币类）','混合类','权益类','固定收益（货币类）'],colors=['#45c9c3','#70a6ee','#e4b16b','#ac9ad9'];
  const monthName=m=>m?.replace('-','年')+'月',download=(name,version)=>localFund&&snapshotManifest&&(!version||version===snapshotManifest.version)&&snapshotManifest.files[name]?location.origin+'/insurance-data/'+snapshotManifest.version+'/'+name:CLOUD+'/api/insurance/download/'+name+(version?'?version='+encodeURIComponent(version):'');
  const $=s=>root.querySelector(s),$$=s=>[...root.querySelectorAll(s)],numeric=(v,d=2)=>'<span class="'+(v<0?'down':v>0?'up':'')+'">'+fmt(v,d)+'</span>';
  root.innerHTML='<style>'+CSS+'</style><div class="am-shell"><header class="am-top"><div class="am-brand"><div class="am-mark">资</div><div><div class="eyebrow">ASSET MANAGEMENT · MARKET INTELLIGENCE</div><strong>资管市场竞品看板</strong></div></div><div class="top-actions"><span class="top-status live-dot" id="top-status">正在读取云端资料</span><button id="theme" aria-label="切换深浅主题">浅色模式</button><button class="admin-top" id="top-upload">资料上传 ↗</button></div></header><nav class="market-tabs" aria-label="市场"><button data-market="insurance" class="active">保险资管</button><button data-market="funds">公募基金</button></nav><div id="insurance-layout" class="am-layout"><aside class="am-side"><div class="side-label">保险资产管理</div><button data-page="analytics" class="active">◫　数据分析</button><button data-page="reports">▤　月报中心</button><button data-page="upload">↥　资料上传</button><div class="side-note">以原报告月份为准<br>保留历史资料与版本<br>Word · Excel 一键导出</div></aside><main class="am-content" id="content"><div class="loading"><span class="spinner"></span>正在读取最新资料…</div></main></div><section id="funds-wrap" hidden><slot name="funds"></slot></section></div>';
  if(localFund){const wrap=document.createElement('div');wrap.slot='funds';for(const el of old)if(el!==host)wrap.append(el);host.append(wrap);}
  else $('#funds-wrap').innerHTML='<div id="fund-status" class="loading">选择公募基金后读取已发布数据</div><iframe class="funds-frame" id="fund-frame" title="公募基金产品全景" hidden></iframe>';
  function toast(s){const d=document.createElement('div');d.className='am-toast';d.textContent=s;root.append(d);setTimeout(()=>d.remove(),5000);}
  let snapshotManifest=null;
  async function snapshotJSON(path,spec=null){
    const r=await requestFetch(location.origin+path,{cache:'no-store'});
    if(!r.ok)throw new Error('保险资料暂未完成同步，请稍后重新读取');
    const bytes=new Uint8Array(await r.arrayBuffer());
    if(bytes.length>(spec?12000000:128000))throw new Error('保险资料大小异常，请重新读取');
    if(spec){
      if(!Number.isSafeInteger(spec.bytes)||spec.bytes<1||spec.bytes>12000000||!/^[a-f0-9]{64}$/.test(spec.sha256||''))throw new Error('保险资料校验清单异常');
      const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),v=>v.toString(16).padStart(2,'0')).join('');
      if(bytes.length!==spec.bytes||digest!==spec.sha256)throw new Error('保险资料正在同步，请稍后重新读取');
    }
    return JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes));
  }
  async function snapshot(path){
    if(path==='/meta'||!snapshotManifest){
      const m=await snapshotJSON('/insurance-data/manifest.json');
      if(!/^[A-Za-z0-9-]{10,80}$/.test(m.version||'')||!Array.isArray(m.months)||!m.months.length||m.months.length>360||m.months.some(x=>!/^20\d{2}-(0[1-9]|1[0-2])$/.test(x))||new Set(m.months).size!==m.months.length||!m.months.includes(m.latest)||!m.files)throw new Error('保险资料版本清单异常');
      snapshotManifest=m;
    }
    const m=snapshotManifest,month=path.match(/^\/period\/(20\d{2}-(?:0[1-9]|1[0-2]))$/),name=path==='/meta'?'meta.json':month&&m.months.includes(month[1])?'period-'+month[1]+'.json':null;
    if(!name||!m.files[name])throw new Error('该月份尚未同步，请重新读取');
    const data=await snapshotJSON('/insurance-data/'+m.version+'/'+name,m.files[name]);
    if(path==='/meta'){
      if(data.version!==m.version||data.latest!==m.latest||JSON.stringify(data.months)!==JSON.stringify(m.months))throw new Error('保险资料版本不一致，请重新读取');
      return {...data,mirrorSyncedAt:m.syncedAt};
    }
    if(data.month!==month[1])throw new Error('保险资料月份不一致，请重新读取');
    return data;
  }
  async function api(path,options={}){
    if(localFund&&(!options.method||options.method==='GET')&&(path==='/meta'||path.startsWith('/period/')))return snapshot(path);
    const r=await requestFetch(CLOUD+'/api/insurance'+path,{cache:'no-store',...options}),d=await r.json();if(!r.ok)throw new Error(d.error||'云端请求未完成');return d;
  }
  const dataStatus=()=> '最新资料 '+state.meta.latest+(localFund?' · 魔搭已同步':' · 云端已保存');
  async function loadFunds(){
    const status=$('#fund-status'),frame=$('#fund-frame');if(!status||frame.dataset.loaded||frame.dataset.loading)return;
    frame.dataset.loading='1';status.hidden=false;status.textContent='正在读取并校验公募共用版本…';
    const urls={};
    try{
      const release=await (await requestFetch(MS+'/release.json?_='+Date.now(),{cache:'no-store'})).json(),files=release.files,names=Object.keys(files||{});
      if(!/^[\w.-]{1,128}$/.test(release.version||'')||names.length>32||!['index.html','snapshot.js','market.js','echarts.min.js'].every(n=>names.includes(n)))throw new Error('公募版本清单不完整');
      let total=0;for(const n of names){const f=files[n];if(!/^(?:index\.html|market\.js|echarts\.min\.js|snapshot(?:-perf-\d{3})?\.js)$/.test(n)||!/^[a-f0-9]{64}$/.test(f.sha256)||!Number.isSafeInteger(f.bytes)||f.bytes<=0||f.bytes>=26214400)throw new Error('公募版本文件校验信息无效');total+=f.bytes;}
      if(total>83886080)throw new Error('公募版本大小超出范围');
      const buffers={},queue=names.slice();let done=0;
      const workers=await Promise.allSettled(Array.from({length:4},async()=>{
        while(queue.length){
          const name=queue.shift(),response=await requestFetch(MS+'/'+name+'?release='+encodeURIComponent(release.version),{cache:'no-store'});
          if(!response.ok)throw new Error('公募文件读取失败：'+name);
          const b=await response.arrayBuffer(),digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',b)),v=>v.toString(16).padStart(2,'0')).join('');
          if(b.byteLength!==files[name].bytes||digest!==files[name].sha256)throw new Error('公募版本正在更新，请重新读取');
          buffers[name]=b;status.textContent='正在校验公募共用版本：'+(++done)+' / '+names.length;
        }
      }));
      const failed=workers.find(r=>r.status==='rejected');if(failed)throw failed.reason;
      for(const name of names.filter(n=>n.endsWith('.js')))urls[name]=URL.createObjectURL(new Blob([buffers[name]],{type:'text/javascript'}));
      let html=new TextDecoder().decode(buffers['index.html']);
      html=html.replace("script-src 'self' 'unsafe-inline'","script-src 'self' 'unsafe-inline' blob:").replace('script-src &#x27;self&#x27; &#x27;unsafe-inline&#x27;','script-src &#x27;self&#x27; &#x27;unsafe-inline&#x27; blob:');
      html=html.replace(/(<script\s+src=")(snapshot(?:-perf-\d{3})?\.js|market\.js)("\s*>)/g,(_,a,n,z)=>a+urls[n]+z).replace(/href="echarts\.min\.js"/g,'href="'+urls['echarts.min.js']+'"').replace(/window\.__echartsTries\s*=\s*\[[\s\S]*?\];/,'window.__echartsTries=['+JSON.stringify(urls['echarts.min.js'])+'];');
      const parsed=new DOMParser().parseFromString(html,'text/html'),verifiedUrls=new Set(Object.values(urls));
      if([...parsed.querySelectorAll('script[src]')].some(script=>!verifiedUrls.has(script.getAttribute('src'))))throw new Error('公募页面存在未校验的脚本引用');
      html=html.replace('<head>','<head><script>window.__INSURANCE_FUND_ONLY__=true;</'+'script>');
      frame.srcdoc=html;frame.hidden=false;frame.dataset.loaded='1';status.hidden=true;state.fundVersion=release.version;
      $('#top-status').textContent='公募共用版本 '+release.version+' · '+release.dataDate;
    }catch(e){status.textContent=e.message+'。';const b=document.createElement('button');b.textContent='重新读取';b.onclick=loadFunds;status.append(' ',b);Object.values(urls).forEach(u=>URL.revokeObjectURL(u));}
    finally{delete frame.dataset.loading;}
  }
  async function reload(){
    try{state.meta=await api('/meta');state.data=await api('/period/'+state.meta.latest);state.cache={[state.meta.latest]:state.data};state.reportMonth=state.reportMonth&&state.meta.months.includes(state.reportMonth)?state.reportMonth:state.meta.latest;$('#top-status').textContent=dataStatus();render();}
    catch(e){$('#content').innerHTML='<div class="panel empty">'+esc(e.message)+'<br><br><button id="retry">重新读取</button></div>';$('#retry').onclick=reload;$('#top-status').textContent='资料尚未读取';}
  }
  function switchMarket(m){
    state.market=m;$$('[data-market]').forEach(b=>b.classList.toggle('active',b.dataset.market===m));$('#insurance-layout').hidden=m!=='insurance';$('#insurance-layout').style.display=m==='insurance'?'grid':'none';
    if(window.innerWidth<721&&m==='insurance')$('#insurance-layout').style.display='block';
    $('#funds-wrap').hidden=m!=='funds';if(m==='funds'){if(!localFund)loadFunds();window.dispatchEvent(new Event('resize'));}else if(state.meta)$('#top-status').textContent=dataStatus();
  }
  function setPage(p){state.page=p;switchMarket('insurance');render();window.scrollTo({top:0,behavior:'smooth'});}
  $$('[data-market]').forEach(b=>b.onclick=()=>switchMarket(b.dataset.market));
  $$('[data-page]').forEach(b=>b.onclick=()=>setPage(b.dataset.page));$('#top-upload').onclick=()=>setPage('upload');
  $('#theme').onclick=()=>{const on=host.classList.toggle('am-light');root.querySelector('.am-shell').classList.toggle('am-light',on);$('#theme').textContent=on?'深色模式':'浅色模式';try{localStorage.setItem('am-theme',on?'light':'dark');}catch(_){}};
  try{if(localStorage.getItem('am-theme')==='light')$('#theme').click();}catch(_){}
  function table(headers,rows,firstClass=''){
    return '<div class="am-table-wrap"><table class="am-table"><thead><tr>'+headers.map(h=>'<th scope="col">'+esc(h)+'</th>').join('')+'</tr></thead><tbody>'+rows.map(r=>'<tr>'+r.map((v,i)=>'<td'+(i===0?' class="name '+firstClass+'"':'')+'>'+v+'</td>').join('')+'</tr>').join('')+'</tbody></table></div>';
  }
  function title(name,sub,actions=''){return '<div class="page-heading"><div><h1>'+name+'</h1><div class="subtle">'+sub+'</div></div>'+actions+'</div>';}
  function panel(head,body,note=''){return '<section class="panel"><div class="panel-head"><h2>'+head+'</h2></div>'+body+(note?'<div class="scope-note">'+note+'</div>':'')+'</section>';}
  function analytics(){
    const d=state.data,m=d.metrics,period='<div class="period-pill">最新资料月份 <b>'+d.month+'</b></div>';
    const heading=title('保险资管 · 行业与产品分析','行业全口径与开放式披露样本分别呈现，单位：亿元',period);
    const kpi='<div class="kpi-grid"><div class="kpi"><div class="label">行业净资产规模（亿元）</div><strong>'+fmt(m.size)+'</strong><small>原表环比 <span class="'+(m.mom<0?'down':'up')+'">'+pct(m.mom)+'</span></small></div><div class="kpi"><div class="label">行业产品只数</div><strong>'+fmt(m.count,0)+'</strong><small>报告期未终止产品</small></div><div class="kpi"><div class="label">管理机构</div><strong>'+m.managerCount+'</strong><small>前五家规模占比 '+pct(m.top5)+'</small></div><div class="kpi"><div class="label">开放式披露样本</div><strong>'+fmt(m.sampleCount,0)+'</strong><small>'+m.sampleManagerCount+'家机构 · 样本规模 '+fmt(m.sampleSize)+'</small></div></div>';
    return heading+kpi+'<nav class="section-nav" aria-label="分析模块"><button data-module="market" class="'+(state.module==='market'?'active':'')+'">全市场统计</button><button data-module="risk" class="'+(state.module==='risk'?'active':'')+'">风险收益分析</button><button data-module="products" class="'+(state.module==='products'?'active':'')+'">产品分类</button></nav><div id="module-content">'+(state.module==='market'?market():state.module==='risk'?risk():products())+'</div><div class="am-footer">数据截至 '+d.period+' · '+d.sources.length+'份原报告 · <a class="am-btn" href="'+download('database.xlsx')+'" target="_blank" rel="noopener">下载最新产品数据库</a></div>';
  }
  function market(){
    const d=state.data,types=d.types.filter(r=>r.name!=='总计');
    const bars=types.map((r,i)=>'<div class="bar-row"><span class="bar-label">'+esc(r.name)+'</span><div class="bar-track"><div class="bar-fill" style="width:'+r.share*100+'%;background:'+colors[i]+'"></div></div><div class="bar-value">'+fmt(r.size)+'<small>'+pct(r.share)+'</small></div></div>').join('');
    const summary='<ul class="summary-list">'+d.report.sections[0].text.map(t=>'<li>'+esc(t)+'</li>').join('')+'</ul>';
    return '<div class="panel-grid">'+panel('产品类型与规模分布',bars,'行业全口径，包含开放式与封闭式产品。')+panel('本期统计摘要',summary)+'</div>'+
      panel('行业规模与结构',table(['产品类型','产品只数','规模','占比','原表环比','较上期规模增减'],d.types.map(r=>[esc(r.name),fmt(r.count,0),fmt(r.size),pct(r.share),numeric(r.mom==null?null:r.mom*100)+'%',numeric(r.change)])),'较上期：'+(d.priorMonth||'未取得')+' → '+d.month+'；环比取自报告原表。')+
      panel('管理机构规模排名',table(['排名 / 管理机构','净资产规模','行业份额','较上期增减','较上年末增减'],d.managers.map(r=>['<span class="rank">'+r.rank+'</span>　'+esc(r.manager),fmt(r.total),pct(r.share),numeric(r.change),numeric(r.ytdChange)])),'使用官方机构管理规模表；上年末比较期：'+(d.baselineMonth||'未取得')+'。')+
      panel('持有人资金来源',table(['资金来源','规模','占比','较上期占比变化 / 百分点','年初以来规模增幅'],d.holders.map(r=>[esc(r.name),fmt(r.size),pct(r.share),numeric(r.shareChange==null?null:r.shareChange*100),pct(r.ytdGrowth)])),'业内、业外及其细分行按原表层级呈现，完整结构见月报。');
  }
  function scatter(){
    const rows=state.data.products.filter(r=>r.category!==cats[3]&&Number.isFinite(r.ytd)&&r.size>0),xs=rows.map(r=>Math.log10(r.size)),ys=rows.map(r=>r.ytd),minx=Math.min(...xs),maxx=Math.max(...xs),miny=Math.min(0,...ys),maxy=Math.max(0,...ys);
    const x=v=>58+(Math.log10(v)-minx)/(maxx-minx||1)*570,y=v=>250-(v-miny)/(maxy-miny||1)*210;
    let out='<svg class="scatter" viewBox="0 0 680 300" role="img" aria-label="非货币产品期末规模与年初以来收益率散点图">';
    for(let i=0;i<=4;i++){const yy=40+i*52.5,val=maxy-(maxy-miny)*i/4;out+='<line x1="58" x2="628" y1="'+yy+'" y2="'+yy+'"/><text x="49" y="'+(yy+4)+'" text-anchor="end">'+pct(val)+'</text>';}
    for(let i=0;i<=4;i++){const val=10**(minx+(maxx-minx)*i/4),xx=58+i*142.5;out+='<text x="'+xx+'" y="273" text-anchor="middle">'+fmt(val,val<1?2:0)+'</text>';}
    for(const r of rows)out+='<circle cx="'+x(r.size)+'" cy="'+y(r.ytd)+'" r="2.3" opacity=".58" fill="'+colors[cats.indexOf(r.category)]+'"><title>'+esc(r.name)+' | '+fmt(r.size)+'亿元 | YTD '+pct(r.ytd)+'</title></circle>';
    return out+'<text x="340" y="295" text-anchor="middle">期末净资产规模（亿元，对数轴）</text></svg><div class="legend">'+cats.slice(0,3).map((c,i)=>'<span><i style="background:'+colors[i]+'"></i>'+c+'</span>').join('')+'</div>';
  }
  function risk(){
    const d=state.data;
    return panel('收益分布与同类比较',table(['产品类别','样本数','YTD有效样本','本月均值','YTD均值','YTD中位数','YTD最高','YTD最低'],d.returns.map(r=>[esc(r.category),r.count,r.valid,r.money?'未披露':pct(r.monthly),pct(r.mean),pct(r.median),pct(r.max),pct(r.min)])),'均值为披露样本简单平均。货币类YTD列为年化收益，其余为累计收益；各类别分别比较。')+
      '<div class="panel-grid">'+panel('产品规模与年初以来收益',scatter(),'散点展示规模与收益关系。货币类不进入该图。')+
      panel('风险指标数据状态','<div class="missing-grid"><div class="missing-card"><span>YTD最大回撤</span><strong>待补</strong><span>需要期内净值序列</span></div><div class="missing-card"><span>YTD夏普比率</span><strong>待补</strong><span>需要净值及计算口径</span></div><div class="missing-card"><span>年化波动率</span><strong>待补</strong><span>需要期内净值序列</span></div></div><div class="callout">当前报告披露月末净值、本月收益和YTD收益。风险指标补齐后启用对应图表。</div>')+'</div>'+
      panel('开放式非货币固收 · 机构比较',table(['管理机构','样本规模','产品数','较上期增减','本月收益均值','YTD收益均值'],d.sampleManagers.map(r=>[esc(r.manager),fmt(r.size),r.count,numeric(r.change),pct(r.monthly),pct(r.ytd)])),'本表为开放式报告实际披露样本；跨期规模增减包含清单变化。');
  }
  function filtered(){
    let a=state.data.products.filter(r=>(!state.category||r.category===state.category)&&(!state.manager||r.manager===state.manager)&&(!state.search||(r.name+r.manager+r.id).toLowerCase().includes(state.search.toLowerCase())));
    const key=state.sort;a.sort((x,y)=>(Number.isFinite(y[key])?y[key]:-Infinity)-(Number.isFinite(x[key])?x[key]:-Infinity)||x.id.localeCompare(y.id));return a;
  }
  function productTable(){
    const a=filtered(),pages=Math.max(1,Math.ceil(a.length/25));state.pageNo=Math.min(state.pageNo,pages);const shown=a.slice((state.pageNo-1)*25,state.pageNo*25);
    return table(['产品名称 / 产品ID','管理机构','报告类别','规模','本月收益','YTD累计收益','货币YTD年化','成立日期'],shown.map(r=>['<span title="'+esc(r.file+' / 表'+r.table+' / 行'+r.row)+'">'+esc(r.name)+'</span><div class="subtle">'+r.id+'</div>',esc(r.manager),esc(r.category),fmt(r.size),pct(r.monthly),pct(r.ytd),pct(r.annualized),esc(r.inception)]))+
      '<div class="pager"><span class="subtle">共 '+a.length+'只 · 第 '+state.pageNo+' / '+pages+' 页 · 每页25只</span><div class="controls"><button id="prev" '+(state.pageNo===1?'disabled':'')+'>上一页</button><button id="next" '+(state.pageNo===pages?'disabled':'')+'>下一页</button></div></div>';
  }
  function products(){
    const d=state.data,managers=[...new Set(d.products.map(r=>r.manager))].sort(),candidates=d.products.filter(r=>r.strategyCandidate&&!r.strategy).length;
    return panel('产品类别与策略标签','<div class="callout"><b>报告大类</b>：非货币固收、货币、混合、权益。<br><b>策略细分</b>：纯债、固收+、可转债需人工确认。当前有 '+candidates+' 只名称提示候选，候选清单见本期Excel；标签确认后进入对应月报统计。</div>')+
      '<section class="panel"><div class="panel-head"><h2>开放式披露产品明细</h2><button id="export-filter">导出当前筛选 CSV</button></div><div class="filters"><input id="search" aria-label="搜索产品或机构" placeholder="搜索产品名称、管理机构或产品ID" value="'+esc(state.search)+'"><select id="category" aria-label="产品类别"><option value="">全部产品类别</option>'+cats.map(c=>'<option'+(state.category===c?' selected':'')+'>'+esc(c)+'</option>').join('')+'</select><select id="manager" aria-label="管理机构"><option value="">全部管理机构</option>'+managers.map(c=>'<option'+(state.manager===c?' selected':'')+'>'+esc(c)+'</option>').join('')+'</select><select id="sort" aria-label="排序指标"><option value="size">规模从高到低</option><option value="monthly"'+(state.sort==='monthly'?' selected':'')+'>本月收益从高到低</option><option value="ytd"'+(state.sort==='ytd'?' selected':'')+'>YTD累计收益从高到低</option><option value="annualized"'+(state.sort==='annualized'?' selected':'')+'>货币YTD年化从高到低</option></select></div><div id="product-table">'+productTable()+'</div><div class="scope-note">数据期 '+d.month+'。缺失值不参与收益排序；真实0与负值按原文保留。产品ID为本地稳定ID。</div></section>';
  }
  function bindProducts(){
    function refresh(){state.pageNo=1;$('#product-table').innerHTML=productTable();bindPager();}
    $('#category').onchange=e=>{state.category=e.target.value;refresh();};$('#manager').onchange=e=>{state.manager=e.target.value;refresh();};$('#sort').onchange=e=>{state.sort=e.target.value;refresh();};
    let timer;$('#search').oninput=e=>{state.search=e.target.value;clearTimeout(timer);timer=setTimeout(refresh,150);};
    $('#export-filter').onclick=()=>{const headers=['产品ID','产品名称','管理机构','报告大类','期末规模 亿元','本月收益率','YTD累计收益率','货币YTD年化收益率','成立日期','来源文件','原表表号','原表行号'],rows=filtered().map(r=>[r.id,r.name,r.manager,r.category,r.size,pct(r.monthly),pct(r.ytd),pct(r.annualized),r.inception,r.file,r.table,r.row]),csv='\ufeff'+[headers,...rows].map(a=>a.map(v=>'"'+String(v??'').replace(/"/g,'""')+'"').join(',')).join('\r\n'),url=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'})),a=document.createElement('a');a.href=url;a.download='保险资管产品_'+state.data.month+'_筛选明细.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),5000);};bindPager();
  }
  function bindPager(){if($('#prev'))$('#prev').onclick=()=>{state.pageNo--;$('#product-table').innerHTML=productTable();bindPager();};if($('#next'))$('#next').onclick=()=>{state.pageNo++;$('#product-table').innerHTML=productTable();bindPager();};}
  function reports(){
    const options=[...state.meta.months].reverse().map(m=>'<option value="'+m+'"'+(m===state.reportMonth?' selected':'')+'>'+monthName(m)+(m===state.meta.latest?' · 最新':'')+'</option>').join('');
    return title('保险资管 · 月报中心','按报告实际月份归档；上传新月份后自动加入列表')+
      '<div class="panel report-controls"><label for="report-month">选择月份</label><select id="report-month">'+options+'</select><a class="am-btn primary" id="report-bundle" href="'+download('report-'+state.reportMonth+'.zip')+'" target="_blank" rel="noopener">一键导出 Word＋Excel</a><a class="am-btn" id="report-word" href="'+download('report-'+state.reportMonth+'.docx')+'" target="_blank" rel="noopener">Word</a><a class="am-btn" id="report-excel" href="'+download('report-'+state.reportMonth+'.xlsx')+'" target="_blank" rel="noopener">Excel 明细</a><span class="subtle">直接下载，无需登录。</span></div><div id="report-body"><div class="loading"><span class="spinner"></span>正在读取本期月报…</div></div>';
  }
  async function loadReport(){
    const wanted=state.reportMonth;
    try{const v=state.cache[wanted]||await api('/period/'+wanted);state.cache[wanted]=v;if(state.reportMonth!==wanted||state.page!=='reports')return;state.report=v;
      $('#report-body').innerHTML='<article class="report-paper"><div class="eyebrow">INSURANCE ASSET MANAGEMENT · MONTHLY REPORT</div><h1>'+esc(v.report.title)+'</h1><div class="subtle">'+esc(v.report.subtitle)+'</div>'+
        v.report.sections.map((s,i)=>'<section><h2>'+esc(s.title)+'</h2>'+(s.text||[]).map(t=>'<p>'+esc(t)+'</p>').join('')+(s.tables||[]).map((t,j)=>'<details'+(i===1&&j===0?' open':'')+'><summary>'+esc(t.title)+'<span class="subtle">　'+t.rows.length+'行</span></summary>'+table(t.headers,t.rows.map(r=>r.map(esc)))+'</details>').join('')+'</section>').join('')+'<div class="report-source">'+v.sources.map(s=>esc(s.name)+'<br>SHA-256 '+s.sha256).join('<br><br>')+'</div></article>';
    }catch(e){if($('#report-body'))$('#report-body').innerHTML='<div class="panel empty">'+esc(e.message)+'</div>';}
  }
  function history(){return '<div class="history-list">'+state.meta.history.slice(0,12).map((v,i)=>'<div class="history-item"><div>'+(i===0?'当前版本':'历史版本')+' · '+new Date(v.created).toLocaleString('zh-CN',{timeZone:'Asia/Shanghai'})+'<small>资料期 '+v.months.join('、')+'</small></div><a class="am-btn" href="'+download('database.xlsx',v.version)+'" target="_blank" rel="noopener">下载该版Excel</a></div>').join('')+'</div>';}
  function upload(){
    return title('资料上传与云端更新','上传同月份的两份行业报告，自动联动数据库、分析和月报')+
      '<div class="upload-area">'+panel('每月更新流程','<div class="step-strip"><span>① 上传两份报告</span><span>② 核验月份与数据</span><span>③ 更新Excel和月报</span><span>④ 发布最新数据</span></div><div class="callout">新月份追加到历史列表；同月修订保留上一版本。重复资料跳过导入。更新校验完成后显示成功结果。</div>')+
      '<section class="panel" id="upload-control"><div class="loading"><span class="spinner"></span>正在检查上传权限…</div></section>'+
      panel('历史更新版本',history(),state.meta.sourceFiles+'份有效原报告 · '+state.meta.productRows+'条产品历史记录')+'</div>';
  }
  async function loadAdmin(){
    if(localFund){$('#upload-control').innerHTML='<h2>上传本月资料</h2><p class="subtle">任何人均可上传，无需登录。请选择同月份的组合行情和开放式产品业绩两份DOCX报告；通过格式与内容校验后自动更新。云端生成后，魔搭每15分钟检查更新，遇公募发布任务时顺延；本页最近成功同步：'+esc(state.meta.mirrorSyncedAt?new Date(state.meta.mirrorSyncedAt).toLocaleString('zh-CN',{timeZone:'Asia/Shanghai'}):'待确认')+'。</p><a class="am-btn primary" href="'+CLOUD+'/?admin=1" target="_blank" rel="noopener">进入资料上传 ↗</a>';return;}
    try{
      const a=await api('/admin');state.admin=a.admin;
      $('#upload-control').innerHTML='<h2>上传本月资料</h2><p class="subtle">任何人均可上传，无需登录。请选择同月份的两份原始报告，校验通过后自动更新。</p><form id="upload-form"><div class="upload-box"><label for="overview-file">① 保险资产管理产品行业报告（YYYY-MM）-组合行情.docx</label><input type="file" id="overview-file" name="overview" accept=".docx" required><label for="products-file">② 保险资产管理产品行业报告（YYYY-MM）-组合行情-开放式组合类资管产品业绩.docx</label><input type="file" id="products-file" name="products" accept=".docx" required><div class="subtle">每份不超过10MB。文件名月份须与正文一致。</div></div><button class="primary" id="upload-submit" type="submit">上传并自动更新</button><div id="upload-state" role="status" aria-live="polite"></div></form><div id="strategy-admin"></div>';
      $('#upload-form').onsubmit=async e=>{
        e.preventDefault();const f1=$('#overview-file').files[0],f2=$('#products-file').files[0];if(!f1||!f2)return;
        const status=$('#upload-state'),button=$('#upload-submit'),form=new FormData();form.append('files',f1);form.append('files',f2);
        button.disabled=true;status.className='upload-state';status.textContent='正在上传、校验并生成新版Excel和月报，请等待结果…';
        try{const r=await api('/upload',{method:'POST',body:form});status.className='upload-state success';status.textContent=r.message+'\n资料月份：'+r.months.join('、')+'\n最新月份：'+r.latest;
          state.meta=await api('/meta');state.data=await api('/period/'+state.meta.latest);state.cache={[state.meta.latest]:state.data};$('#top-status').textContent='最新资料 '+state.meta.latest+' · 云端已保存';toast(r.message);
        }catch(err){status.className='upload-state error';status.textContent=err.message+'\n此次更新未发布，当前版本继续保留。';}
        finally{button.disabled=false;}
      };
      if(state.admin)renderStrategies();
    }catch(e){$('#upload-control').innerHTML='<div class="empty">'+esc(e.message)+'</div>';}
  }
  function renderStrategies(){
    const candidates=state.data.products.filter(r=>r.strategyCandidate&&!r.strategy),shown=candidates.slice(0,30);
    if(!shown.length)return;
    $('#strategy-admin').innerHTML='<h3>策略标签候选确认</h3><div class="subtle">显示前30项，共'+candidates.length+'项。候选仅由名称提示，确认前不纳入策略统计。</div>'+shown.map(r=>'<div class="strategy-row"><div>'+esc(r.name)+'<small>'+esc(r.manager)+' · 名称提示：'+esc(r.strategyCandidate)+'</small></div><select data-strategy="'+r.id+'" aria-label="'+esc(r.name)+'的策略"><option value="">暂不确认</option><option>纯债</option><option>固收+</option><option>可转债</option></select></div>').join('')+'<button id="confirm-strategies" style="margin-top:16px">保存已选择的策略标签</button>';
    $('#confirm-strategies').onclick=async()=>{
      const items=$$('[data-strategy]').filter(s=>s.value).map(s=>({id:s.dataset.strategy,strategy:s.value}));if(!items.length)return toast('请先选择已核实的策略标签');
      const b=$('#confirm-strategies');b.disabled=true;b.textContent='正在更新报表…';
      try{const r=await api('/strategies',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({items})});toast(r.message);await reload();}
      catch(e){toast(e.message);b.disabled=false;b.textContent='保存已选择的策略标签';}
    };
  }
  function render(){
    if(!state.data)return;
    $$('[data-page]').forEach(b=>b.classList.toggle('active',b.dataset.page===state.page));
    $('#content').innerHTML=state.page==='analytics'?analytics():state.page==='reports'?reports():upload();
    if(state.page==='analytics'){
      $$('[data-module]').forEach(b=>b.onclick=()=>{state.module=b.dataset.module;render();});if(state.module==='products')bindProducts();
    }else if(state.page==='reports'){
      $('#report-month').onchange=e=>{state.reportMonth=e.target.value;render();};loadReport();
    }else loadAdmin();
  }
  document.title='资管市场竞品看板';
  reload();
})();
