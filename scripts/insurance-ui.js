(()=>{
  if(window.__INSURANCE_FUND_ONLY__||new URLSearchParams(location.search).has('fundonly'))return;
  const CSS=":host,#am-app{--bg:#1c1c1e;--panel:#262628;--panel2:#303033;--line:#454548;--text:#f5f5f5;--muted:#c1c1c5;--brand:#e36715;--accent:#ff9b54;--blue:#a6a6aa;--orange:#ffb57f;--red:#ef8a91;--green:#68c7a1;color:var(--text);font:14px/1.6 -apple-system,BlinkMacSystemFont,\"PingFang SC\",\"Microsoft YaHei\",sans-serif;display:block;background:var(--bg);min-height:100vh}\n*{box-sizing:border-box}body{margin:0}button,input,select{font:inherit}button,a,select{touch-action:manipulation}button{cursor:pointer}button:disabled{opacity:.5;cursor:wait}button:focus-visible,a:focus-visible,input:focus-visible,select:focus-visible{outline:2px solid var(--accent);outline-offset:3px}button,.am-btn{border:1px solid var(--line);border-radius:7px;padding:7px 14px;background:var(--panel2);color:var(--text);text-decoration:none;display:inline-flex;align-items:center;justify-content:center;gap:6px;white-space:nowrap}.primary{background:var(--brand);color:#21140b;border-color:var(--brand);font-weight:650}.am-btn:hover,button:hover{filter:brightness(1.15)}.am-top{height:76px;padding:0 30px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid var(--line);gap:20px}.am-brand{display:flex;align-items:center;gap:12px}.am-mark{width:35px;height:35px;background:linear-gradient(145deg,#f59248,#e36715);border-radius:8px;display:grid;place-items:center;color:white;font-weight:800;font-size:20px}.am-brand strong{font-size:20px;letter-spacing:.6px}.eyebrow{font-size:10px;letter-spacing:1.6px;color:var(--muted)}.top-actions{display:flex;gap:12px;align-items:center}.live-dot:before{content:\"\";display:inline-block;width:6px;height:6px;margin-right:7px;border-radius:50%;background:var(--accent)}.top-status{font-size:12px;color:var(--muted)}.market-tabs{display:flex;gap:8px;border-bottom:1px solid var(--line);padding:0 30px;min-height:51px;align-items:stretch}.market-tabs button{background:transparent;border:0;border-radius:0;padding:12px 22px;color:var(--muted)}.market-tabs button.active{color:var(--accent);border-bottom:2px solid var(--accent);background:linear-gradient(0deg,#e367150d,transparent)}.am-layout{display:grid;grid-template-columns:178px minmax(0,1fr);min-height:calc(100vh - 127px)}.am-side{border-right:1px solid var(--line);padding:25px 15px;display:flex;flex-direction:column;gap:7px}.side-label{color:var(--muted);font-size:11px;letter-spacing:1px;padding:5px 13px 12px}.am-side button{background:transparent;border:0;justify-content:flex-start;text-align:left;padding:11px 13px;color:var(--muted)}.am-side button.active{background:#e3671514;color:var(--accent);border:1px solid #e367152c}.side-note{margin-top:auto;padding:20px 12px;font-size:11px;color:var(--muted);line-height:1.9}.am-content{padding:27px 30px 50px;max-width:1600px;width:100%;margin:0 auto}.page-heading{display:flex;justify-content:space-between;align-items:center;gap:15px;margin-bottom:23px}.page-heading h1{font-size:22px;margin:0 0 4px;font-weight:650}.subtle{font-size:12px;color:var(--muted)}.period-pill{background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:9px 14px;font-size:12px}.period-pill b{color:var(--accent);margin-left:10px}.kpi-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:16px;margin-bottom:22px}.kpi{background:var(--panel);border:1px solid var(--line);border-radius:9px;padding:19px 21px}.kpi .label{font-size:12px;color:var(--muted)}.kpi strong{display:block;font-size:29px;letter-spacing:-.5px;font-weight:650;margin:8px 0 2px;font-variant-numeric:tabular-nums}.kpi small{font-size:11px;color:var(--muted)}.down{color:var(--red)}.up{color:var(--green)}.panel{background:var(--panel);border:1px solid var(--line);border-radius:9px;padding:21px 23px;margin-bottom:19px;min-width:0}.panel h2{font-size:15px;margin:0;font-weight:650}.panel-head{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:17px}.panel-head small{color:var(--muted);font-size:11px}.panel-grid{display:grid;grid-template-columns:1.05fr 1fr;gap:19px}.section-nav{display:flex;gap:23px;border-bottom:1px solid var(--line);margin-bottom:22px}.section-nav button{border:0;border-bottom:2px solid transparent;border-radius:0;background:transparent;padding:10px 1px;color:var(--muted)}.section-nav button.active{color:var(--accent);border-bottom-color:var(--accent)}.bar-row{display:grid;grid-template-columns:95px 1fr 110px;gap:13px;align-items:center;margin:20px 0}.bar-label{font-size:12px}.bar-track{background:#8e8e9330;height:11px;border-radius:3px;overflow:hidden}.bar-fill{height:100%;border-radius:3px;background:var(--accent)}.bar-value{text-align:right;font-size:12px;font-variant-numeric:tabular-nums}.bar-value small{display:block;font-size:10px;color:var(--muted)}.scope-note{border-top:1px solid var(--line);padding-top:12px;margin-top:13px;color:var(--muted);font-size:11px;line-height:1.8}.am-table-wrap{overflow:auto}.am-table{border-collapse:collapse;width:100%;font-size:12px;white-space:nowrap;font-variant-numeric:tabular-nums}.am-table th{text-align:right;color:var(--muted);font-weight:500;padding:10px 12px;border-bottom:1px solid var(--line);background:var(--panel2)}.am-table td{padding:11px 12px;border-bottom:1px solid #8e8e9340;text-align:right}.am-table th:first-child,.am-table td:first-child{text-align:left}.am-table td.name{white-space:normal;min-width:210px;max-width:400px}.am-table tr:hover td{background:#e3671506}.rank{color:var(--accent);font-weight:650}.callout{padding:13px 16px;background:#e3671509;border:1px solid #e3671529;border-radius:7px;color:var(--muted);font-size:12px;line-height:1.85;margin:15px 0}.callout b{color:var(--text)}.summary-list{padding:0 0 0 20px;color:var(--muted);font-size:13px}.summary-list li{margin-bottom:12px}.summary-list strong{color:var(--text)}.filters{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:16px}.filters input{flex:1;min-width:200px}input,select{background:var(--bg);color:var(--text);border:1px solid var(--line);border-radius:6px;padding:8px 10px}select{max-width:100%}.pager{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-top:17px}.pager .controls{display:flex;gap:8px}.empty,.loading{padding:50px 24px;text-align:center;color:var(--muted)}.spinner{display:inline-block;width:18px;height:18px;border:2px solid var(--line);border-top-color:var(--accent);border-radius:50%;animation:spin 1s linear infinite;margin-right:9px;vertical-align:middle}@keyframes spin{to{transform:rotate(360deg)}}.report-controls{display:flex;align-items:center;gap:12px;flex-wrap:wrap}.report-controls label{font-size:12px;color:var(--muted)}.report-paper{max-width:1050px;margin:0 auto;background:var(--panel);padding:35px;border:1px solid var(--line);border-radius:9px}.report-paper h1{font-size:24px;margin:0 0 8px}.report-paper h2{font-size:17px;border-bottom:1px solid var(--line);padding-bottom:10px;margin-top:35px}.report-paper h3{font-size:13px;margin:25px 0 12px;color:var(--accent)}.report-paper p{font-size:13px;line-height:1.95;color:var(--muted)}.report-paper .am-table{font-size:11px}.report-paper details{margin:16px 0;border:1px solid var(--line);border-radius:7px;padding:13px}.report-paper summary{cursor:pointer;color:var(--text);font-size:13px}.upload-area{max-width:950px}.upload-box{border:1px dashed #99999e;border-radius:9px;background:#e3671505;padding:28px;margin:17px 0}.upload-box label{display:block;font-size:13px;margin-bottom:9px}.upload-box input{display:block;width:100%;background:var(--panel);padding:18px;margin:8px 0 20px}.upload-state{white-space:pre-wrap;font-size:13px;padding:15px 18px;border:1px solid var(--line);border-radius:6px;margin:17px 0;background:var(--panel2)}.upload-state.error{border-color:#ef8a91;color:var(--red)}.upload-state.success{border-color:#68c7a1;color:var(--green)}.step-strip{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:20px 0}.step-strip span{background:var(--panel2);padding:12px 9px;text-align:center;border-radius:6px;font-size:12px}.history-list{margin-top:20px}.history-item{display:flex;justify-content:space-between;gap:15px;padding:12px 0;border-bottom:1px solid var(--line);font-size:12px}.history-item small{display:block;color:var(--muted)}.missing-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}.missing-card{padding:17px;background:var(--panel2);border-radius:7px}.missing-card span{display:block;font-size:11px;color:var(--muted)}.missing-card strong{font-size:20px;font-weight:500;display:block;margin:5px 0;color:var(--orange)}.scatter{width:100%;height:auto;display:block}.scatter text{fill:var(--muted);font-size:11px}.scatter line{stroke:var(--line)}.legend{display:flex;gap:15px;flex-wrap:wrap;font-size:11px;color:var(--muted)}.legend i{display:inline-block;width:7px;height:7px;border-radius:50%;margin-right:5px}.funds-frame{width:100%;height:calc(100vh - 127px);border:0;display:block;min-height:800px}.am-toast{position:fixed;right:25px;bottom:25px;background:var(--panel2);border:1px solid var(--accent);padding:14px 20px;border-radius:7px;z-index:10000;max-width:450px;font-size:12px}.mobile-only{display:none}:host(.am-light),.am-light{--bg:#f5f5f5;--panel:#fff;--panel2:#f3f3f3;--line:#dedee0;--text:#202020;--muted:#555558;--brand:#e36715;--accent:#b94b0a;--red:#b84f5b;--green:#178366;--blue:#747478;--orange:#b94b0a}.report-source{font-size:11px;color:var(--muted);margin-top:16px;overflow-wrap:anywhere}.wide-actions{display:flex;gap:9px;flex-wrap:wrap}.strategy-row{display:grid;grid-template-columns:minmax(250px,1fr) 150px 90px;gap:12px;padding:12px 0;border-bottom:1px solid var(--line);align-items:center}.strategy-row small{display:block;color:var(--muted)}.am-footer{font-size:11px;color:var(--muted);text-align:right;margin-top:25px}\n@media(min-width:1600px){.am-content{padding-left:40px;padding-right:40px}}@media(max-width:1100px){.am-layout{grid-template-columns:155px minmax(0,1fr)}.am-content{padding:22px 20px}.kpi-grid{gap:10px}.kpi{padding:16px}.kpi strong{font-size:24px}.panel-grid{grid-template-columns:1fr}.am-top{padding:0 20px}.am-brand strong{font-size:18px}.top-status{display:none}}@media(max-width:720px){.am-top{height:auto;min-height:72px;padding:14px 15px}.am-brand strong{font-size:17px}.eyebrow{font-size:8px}.top-actions{gap:7px}.top-actions button{font-size:11px;padding:5px 9px}.market-tabs{padding:0 10px}.market-tabs button{padding:12px 17px}.am-layout{display:block}.am-side{padding:10px 12px;flex-direction:row;border-right:0;border-bottom:1px solid var(--line);overflow:auto}.am-side button{padding:7px 13px;white-space:nowrap}.side-label,.side-note{display:none}.am-content{padding:20px 13px}.page-heading{align-items:flex-start;flex-direction:column}.page-heading h1{font-size:21px}.kpi-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.panel{padding:17px 14px}.bar-row{grid-template-columns:80px 1fr 90px;gap:8px}.report-paper{padding:22px 15px}.step-strip{grid-template-columns:1fr 1fr}.missing-grid{grid-template-columns:1fr}.strategy-row{grid-template-columns:1fr 120px}.strategy-row button{grid-column:2}.top-actions .admin-top{display:none}.funds-frame{height:calc(100vh - 122px)}}\n:host .am-shell{background:var(--bg);color:var(--text);min-height:100vh}\n\n.type-bar{width:100%;padding:8px 0;text-align:left;border:0;border-radius:5px;background:transparent;white-space:normal}.type-bar:hover,.type-bar.active{background:var(--panel2)}.type-bar .bar-label small{color:var(--accent)}.chart-types{display:flex;flex-wrap:wrap;gap:9px;margin-bottom:18px}.chart-types button.active{border-color:var(--accent);color:var(--accent);background:var(--panel2)}.chart-types i{width:8px;height:8px;display:inline-block;border-radius:50%}.type-chart{scroll-margin-top:18px}.type-chart .scatter{max-width:1000px;margin:0 auto}.chart-summary{display:flex;flex-wrap:wrap;gap:12px 24px;color:var(--muted);font-size:12px;padding:12px 14px;background:var(--panel2);border-radius:6px;margin-bottom:15px}.chart-summary b{color:var(--text);font-variant-numeric:tabular-nums}.scatter circle:hover{opacity:1;stroke:var(--text);stroke-width:1.1;r:4px}\n.type-pie-layout{display:grid;grid-template-columns:minmax(160px,1fr) minmax(190px,1fr);gap:20px;align-items:center;min-height:260px}.type-pie{display:block;width:100%;max-width:260px;margin:auto;overflow:visible}.type-pie path{stroke:var(--panel);stroke-width:2;cursor:pointer;transition:opacity .15s}.type-pie path:hover,.type-pie path:focus-visible{opacity:.8;stroke:var(--text);outline:none}.type-pie-legend{display:grid;gap:12px}.pie-legend-row{display:grid;grid-template-columns:10px 1fr auto;gap:5px 10px;padding:10px;text-align:left}.pie-legend-row i{width:9px;height:9px;border-radius:3px}.pie-legend-row strong{font-variant-numeric:tabular-nums;font-size:15px}.pie-legend-row small{grid-column:2 / -1;color:var(--muted);font-size:12px}.chart-metrics{display:flex;gap:8px;margin-bottom:12px}.chart-metrics button.active{color:var(--accent);border-color:var(--accent)}.chart-metric-note{margin-bottom:12px}\n.am-table{table-layout:fixed;min-width:700px;white-space:normal}.am-table th,.am-table td,.am-table th:first-child,.am-table td:first-child{text-align:center;vertical-align:middle;padding:13px 14px;line-height:1.6;overflow-wrap:anywhere}.am-table th:first-child{width:32%}.am-table td.name{min-width:0;max-width:none}.am-table th{font-weight:600}.table-sort{width:100%;padding:0;border:0;background:transparent;border-radius:0;white-space:normal;text-align:center;line-height:1.6;display:block;color:inherit;font-size:inherit}.sort-indicator{display:inline-block;margin-left:5px;color:var(--accent);font-size:11px}.product-details{min-width:1420px}.product-details th:first-child{width:360px}.product-details th:nth-child(2){width:240px}.product-details th:nth-child(3){width:160px}.product-details th:nth-child(n+4):nth-child(-n+7){width:130px}.product-details th:last-child{width:140px}.product-details .product-link{width:100%;white-space:normal;text-align:center;justify-content:center;line-height:1.6}.product-details .subtle{margin-top:5px;overflow-wrap:anywhere}\n@media(max-width:600px){.type-pie-layout{grid-template-columns:1fr;gap:8px}.type-pie{max-width:230px}.type-pie-legend{grid-template-columns:1fr;gap:3px}.pie-legend-row{grid-template-columns:10px 1fr auto}.pie-legend-row small{grid-column:3;text-align:right}}\n\n.manager-source{border-top:0;margin:0 0 15px;padding:0;color:var(--muted)}\n.overview-grid{grid-template-columns:repeat(2,minmax(0,1fr));align-items:stretch;margin-bottom:19px}\n.overview-grid>.panel{margin-bottom:0}\n.overview-grid .summary-list{display:grid;gap:24px;margin:0;padding-left:20px;line-height:1.95}\n.overview-grid .summary-list li{margin:0;padding-left:4px}\n.type-chart .scatter{max-width:none;--point:#ff8a1c}\n.type-chart .scatter[data-kind=\"1\"]{--point:#ffb52e}\n.type-chart .scatter[data-kind=\"2\"]{--point:#ff7454}\n.type-chart .scatter[data-kind=\"3\"]{--point:#f5bb34}\n:host(.am-light) .type-chart .scatter{--point:#ff7900}\n:host(.am-light) .type-chart .scatter[data-kind=\"1\"]{--point:#f7a21c}\n:host(.am-light) .type-chart .scatter[data-kind=\"2\"]{--point:#ff633a}\n:host(.am-light) .type-chart .scatter[data-kind=\"3\"]{--point:#efa918}\n.type-chart .scatter circle{fill:var(--point)}\n.type-chart .scatter text{font-size:12px;fill:var(--text)}\n.type-chart .scatter .axis-title{font-weight:600}\n.type-chart .scatter .vertical-grid{stroke-dasharray:3 5;opacity:.55}\n.type-chart .scatter .zero-line{stroke:var(--muted);stroke-dasharray:5 4;opacity:.65}\n.chart-view-controls{display:flex;align-items:center;flex-wrap:wrap;gap:9px;margin:0 0 12px}\n.chart-view-controls button.active{color:var(--accent);border-color:var(--accent);background:var(--panel2)}\n.chart-hover{display:flex;align-items:center;flex-wrap:wrap;gap:8px 20px;min-height:48px;background:var(--panel2);border-left:3px solid var(--accent);padding:12px 15px;margin-top:8px;color:var(--muted);font-size:12px;line-height:1.7}\n.chart-hover strong,.chart-hover b{color:var(--text)}\n.am-table th:first-child,.am-table td:first-child,.report-paper.report-reference td:first-child{font-weight:700}\n.kpi,.missing-card,.callout,.upload-state{text-align:center}\n.overview-grid>.panel:last-child{text-align:center;display:flex;flex-direction:column}\n.overview-grid>.panel:last-child .panel-head{justify-content:center}\n.overview-grid .summary-list{list-style:none;padding:0}\n.overview-grid .summary-list li{padding:0}\n.overview-grid .summary-list{flex:1;align-content:center}\n.overview-grid .summary-list strong{font-weight:750}\n.chart-summary,.chart-hover{justify-content:center;text-align:center}\n.upload-area>.panel:has(.step-strip) .panel-head{justify-content:center}\n@media(max-width:1100px){.overview-grid{grid-template-columns:1fr}}\n/* Monthly report follows the supplied print reference in either dashboard theme. */\n.report-paper.report-reference{background:#fff;color:#111;max-width:1050px;padding:44px 54px;border:1px solid #ddd;box-shadow:0 8px 30px #00000012;font-family:Arial,\"Microsoft YaHei\",\"PingFang SC\",sans-serif}\n.report-paper.report-reference h1{color:#000;font-size:28px;line-height:1.45;text-align:center;margin:0 0 10px;font-weight:750;letter-spacing:0}\n.report-paper.report-reference .report-subtitle{color:#666;text-align:center;font-size:13px;margin-bottom:28px}\n.report-paper.report-reference h2{color:#000;font-size:23px;margin:34px 0 16px;border:0;padding:0;line-height:1.5}\n.report-paper.report-reference h3{color:#ea6200;font-size:18px;line-height:1.6;margin:24px 0 10px;font-weight:700}\n.report-paper.report-reference .report-paragraph{color:#111;font-size:16px;line-height:1.9;margin:10px 0 14px;text-align:justify}\n.report-paper.report-reference strong{color:#111;font-weight:700}\n.report-paper.report-reference .report-label{color:#ea6200}\n.report-paper.report-reference .report-bullet{padding-left:18px;position:relative}\n.report-paper.report-reference .report-bullet:before{content:'·';position:absolute;left:0;top:0;color:#ea6200;font-weight:700}\n.report-paper.report-reference .report-table{margin:20px 0 26px}\n.report-paper.report-reference figcaption{font-size:15px;font-weight:700;color:#111;margin-bottom:9px}\n.report-paper.report-reference .report-table-scroll{overflow:auto;border:0;border-radius:0}\n.report-paper.report-reference table{table-layout:fixed;border-collapse:collapse;width:100%;min-width:640px;font-size:13px;line-height:1.5;margin:0}\n.report-paper.report-reference th{background:#f0822b;color:#fff;font-weight:700;text-align:center;white-space:normal;padding:12px 9px;position:static;border:1px solid #bbb}\n.report-paper.report-reference td{background:#fff;color:#111;text-align:right;white-space:normal;padding:9px;border:1px solid #bbb;overflow-wrap:anywhere}\n.report-paper.report-reference td.report-name{text-align:left}\n.report-paper.report-reference tr:nth-child(even) td{background:#f0f0f0}\n.report-paper.report-reference tr.report-total td{background:#e1e1e1;font-weight:700}\n.report-paper.report-reference tr.report-emphasis td{font-weight:700}\n.report-paper.report-reference td.report-negative{color:#d93025}\n.report-paper.report-reference .report-table-source{font-size:12px;line-height:1.7;color:#707070;margin:8px 0 0}\n.scatter circle[data-product-id]{cursor:pointer;outline:none}\n.scatter circle[data-product-id]:focus-visible{opacity:1;stroke:var(--text);stroke-width:2;r:5px}\n.product-link{display:inline;padding:0;border:0;background:transparent;color:var(--accent);white-space:normal;text-align:left;line-height:1.6}\n.product-link:hover{text-decoration:underline;filter:none}\n.product-dialog{color:var(--text);background:var(--panel);border:1px solid var(--line);border-radius:12px;width:min(640px,calc(100vw - 32px));max-height:85vh;padding:26px;box-shadow:0 24px 80px #0006}\n.product-dialog::backdrop{background:#171719b3;backdrop-filter:blur(3px)}\n.product-dialog-head{display:flex;justify-content:space-between;align-items:flex-start;gap:18px}\n.product-dialog h2{font-size:20px;line-height:1.5;margin:6px 0 22px}\n.product-dialog-head button{font-size:22px;padding:0 9px}\n.product-facts{display:grid;grid-template-columns:1fr 1fr;gap:18px 24px;margin:0 0 22px}\n.product-facts dt{font-size:12px;color:var(--muted);margin-bottom:4px}\n.product-facts dd{margin:0;font-size:14px;overflow-wrap:anywhere}\n.product-dialog-actions{display:flex;justify-content:flex-end;margin-top:22px}\n@media(max-width:700px){.report-paper.report-reference{padding:24px 18px}.report-paper.report-reference h1{font-size:23px}.report-paper.report-reference h2{font-size:21px}.report-paper.report-reference .report-paragraph{font-size:15px}}\n",CLOUD=location.hostname.endsWith('.ms.show')?'https://fund-panorama-wsy-1028.xmxmxm348190253.chatgpt.site':location.origin,MS='https://wangshuyang2126-fund-panorama-wsy.ms.show';
  const localFund=location.hostname.endsWith('.ms.show')||!!document.getElementById('deliveryBanner'),old=localFund?[...document.body.children].filter(e=>e.tagName!=='SCRIPT'):[];
  const requestFetch=(window.__INSURANCE_FETCH__||window.fetch).bind(window);
  const host=document.getElementById('am-app')||document.body.insertBefore(document.createElement('div'),document.body.firstChild);host.id='am-app';
  const root=host.attachShadow({mode:'open'}),state={market:'insurance',page:new URLSearchParams(location.search).has('admin')?'upload':'analytics',module:'market',meta:null,data:null,cache:{},report:null,reportMonth:null,category:'',chartCategory:'固定收益类（非货币类）',chartView:'dense',manager:'',search:'',sort:'size',pageNo:1,admin:false};
  const esc=s=>String(s??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
  const fmt=(n,d=2)=>n===null||n===undefined?'待补':Number(n).toLocaleString('zh-CN',{minimumFractionDigits:d,maximumFractionDigits:d}),pct=(n,missing='待补')=>n===null||n===undefined?missing:fmt(n*100)+'%',cats=['固定收益类（非货币类）','混合类','权益类','固定收益（货币类）'],colors=['#e36715','#f2b07c','#96969c','#c8b4a4'];
  const monthName=m=>m?.replace('-','年')+'月',download=(name,version)=>localFund&&snapshotManifest&&(!version||version===snapshotManifest.version)&&snapshotManifest.files[name]?location.origin+'/insurance-data/'+snapshotManifest.version+'/'+name:CLOUD+'/api/insurance/download/'+name+(version?'?version='+encodeURIComponent(version):'');
  const $=s=>root.querySelector(s),$$=s=>[...root.querySelectorAll(s)],numeric=(v,d=2)=>'<span class="'+(v<0?'down':v>0?'up':'')+'">'+fmt(v,d)+'</span>';
  const numericPct=v=>'<span class="'+(v<0?'down':v>0?'up':'')+'">'+pct(v)+'</span>';
  root.innerHTML='<style>'+CSS+'</style><div class="am-shell"><header class="am-top"><div class="am-brand"><div class="am-mark">资</div><div><div class="eyebrow">ASSET MANAGEMENT · MARKET INTELLIGENCE</div><strong>资管市场竞品看板</strong></div></div><div class="top-actions"><span class="top-status live-dot" id="top-status">正在读取云端资料</span><button id="theme" aria-label="切换深浅主题">浅色模式</button><button class="admin-top" id="top-upload">资料上传 ↗</button></div></header><nav class="market-tabs" aria-label="市场"><button data-market="insurance" class="active">保险资管</button><button data-market="funds">公募基金</button></nav><div id="insurance-layout" class="am-layout"><aside class="am-side"><div class="side-label">保险资产管理</div><button data-page="analytics" class="active">◫　数据分析</button><button data-page="reports">▤　月报中心</button><button data-page="upload">↥　资料上传</button><div class="side-note">以原报告月份为准<br>按月份查看最新版<br>Word · Excel 一键导出</div></aside><main class="am-content" id="content"><div class="loading"><span class="spinner"></span>正在读取最新资料…</div></main></div><section id="funds-wrap" hidden><slot name="funds"></slot></section></div>';
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
      html=html.replace(/(<script\s+src=")(snapshot(?:-perf-\d{3})?\.js|market\.js)(?:\?release=[\w.-]+)?("\s*>)/g,(_,a,n,z)=>a+urls[n]+z).replace(/href="echarts\.min\.js"/g,'href="'+urls['echarts.min.js']+'"').replace(/window\.__echartsTries\s*=\s*\[[\s\S]*?\];/,'window.__echartsTries=['+JSON.stringify(urls['echarts.min.js'])+'];');
      const parsed=new DOMParser().parseFromString(html,'text/html'),verifiedUrls=new Set(Object.values(urls));
      if([...parsed.querySelectorAll('script[src]')].some(script=>!verifiedUrls.has(script.getAttribute('src'))))throw new Error('公募页面存在未校验的脚本引用');
      html=html.replace('<head>','<head><script>window.__INSURANCE_FUND_ONLY__=true;</'+'script>');
      frame.onload=()=>{syncFundTheme();observeFundTheme(frame.contentDocument);};
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
  let themeMode='dark',fundThemeObserver=null;
  function syncFundTheme(){
    const doc=localFund?document:$('#fund-frame')?.contentDocument;
    if(!doc?.documentElement||doc.documentElement.dataset.theme===themeMode)return;
    const toggle=doc.getElementById('themeToggle');
    if(toggle)toggle.click();
    else doc.documentElement.dataset.theme=themeMode;
  }
  function applyTheme(mode){
    themeMode=mode==='light'?'light':'dark';
    const light=themeMode==='light';
    host.classList.toggle('am-light',light);
    root.querySelector('.am-shell').classList.toggle('am-light',light);
    $('#theme').textContent=light?'深色模式':'浅色模式';
    try{localStorage.setItem('am-theme',themeMode);localStorage.setItem('fm_theme',themeMode);}catch(_){}
    syncFundTheme();
  }
  function observeFundTheme(doc){
    if(!doc||typeof MutationObserver==='undefined')return;
    fundThemeObserver?.disconnect();
    fundThemeObserver=new MutationObserver(()=>applyTheme(doc.documentElement.dataset.theme));
    fundThemeObserver.observe(doc.documentElement,{attributes:true,attributeFilter:['data-theme']});
  }
  $('#theme').onclick=()=>applyTheme(themeMode==='light'?'dark':'light');
  try{themeMode=localStorage.getItem('am-theme')||localStorage.getItem('fm_theme')||'dark';}catch(_){}
  applyTheme(themeMode);
  if(localFund)observeFundTheme(document);
  function table(headers,rows,firstClass='',options={}){
    const key=options.id||headers.join('¦');
    const heading=h=>esc(h).replace(/（/g,'<br>（');
    return '<div class="am-table-wrap"><table class="am-table'+(options.id==='products'?' product-details':'')+'" data-table-key="'+esc(key)+'"><thead><tr>'+headers.map((h,i)=>'<th scope="col" aria-sort="none"><button class="table-sort" data-sort-column="'+i+'"'+(options.keys?' data-sort-field="'+options.keys[i]+'"':'')+'>'+heading(h)+'<span class="sort-indicator" aria-hidden="true">↕</span></button></th>').join('')+'</tr></thead><tbody>'+rows.map(r=>'<tr>'+r.map((v,i)=>'<td'+(i===0?' class="name '+firstClass+'"':'')+'>'+v+'</td>').join('')+'</tr>').join('')+'</tbody></table></div>';
  }
  function compareValues(a,b,direction='asc'){
    const missing=v=>v===null||v===undefined||v===''||['/','待补','未披露','--'].includes(v);
    if(missing(a)||missing(b))return missing(a)===missing(b)?0:missing(a)?1:-1;
    const result=typeof a==='number'&&typeof b==='number'?a-b:String(a).localeCompare(String(b),'zh-CN',{numeric:true});
    return direction==='desc'?-result:result;
  }
  const tableSorts=new Map();
  function bindTables(){
    $$('.am-table').forEach(table=>{
      const key=table.dataset.tableKey,buttons=[...table.querySelectorAll('.table-sort')];
      const apply=sort=>{
        if(!sort)return;
        buttons.forEach((b,i)=>{b.closest('th').setAttribute('aria-sort',i===sort.column?(sort.direction==='asc'?'ascending':'descending'):'none');b.querySelector('.sort-indicator').textContent=i===sort.column?(sort.direction==='asc'?'↑':'↓'):'↕';});
        if(key==='products')return;
        const body=table.tBodies[0],rows=[...body.rows];
        const value=row=>{
          const text=row.cells[sort.column].textContent.trim();
          if(sort.column===0&&buttons[0].textContent.includes('排名'))return Number(text.match(/^\d+/)?.[0]);
          const clean=text.replace(/[,％%\s]/g,'');
          return /^[+-]?(?:\d+\.?\d*|\.\d+)$/.test(clean)?Number(clean):text;
        };
        rows.sort((a,b)=>compareValues(value(a),value(b),sort.direction));
        rows.forEach(row=>body.append(row));
      };
      apply(key==='products'?{column:buttons.findIndex(b=>b.dataset.sortField===state.sort),direction:state.sortDirection||'desc'}:tableSorts.get(key));
      buttons.forEach((button,column)=>button.onclick=()=>{
        if(key==='products'){
          const field=button.dataset.sortField;
          state.sortDirection=state.sort===field&&state.sortDirection!=='asc'?'asc':state.sort===field?'desc':['name','manager','category','inception'].includes(field)?'asc':'desc';
          state.sort=field;state.pageNo=1;$('#product-table').innerHTML=productTable();if($('#sort'))$('#sort').value=field;bindPager();return;
        }
        const old=tableSorts.get(key),sort={column,direction:old?.column===column&&old.direction==='asc'?'desc':'asc'};
        tableSorts.set(key,sort);apply(sort);
      });
    });
  }
  function typePie(types){
    const total=types.reduce((sum,r)=>sum+r.size,0);let angle=-Math.PI/2;
    const slices=types.map(r=>{
      const category=r.name==='固定收益类'?cats[0]:r.name,color=colors[cats.indexOf(category)],next=angle+r.size/total*Math.PI*2;
      const x1=110+92*Math.cos(angle),y1=110+92*Math.sin(angle),x2=110+92*Math.cos(next),y2=110+92*Math.sin(next);
      const path='M110 110 L'+x1+' '+y1+' A92 92 0 '+(next-angle>Math.PI?1:0)+' 1 '+x2+' '+y2+' Z';angle=next;
      return '<path class="pie-slice" d="'+path+'" fill="'+color+'" data-chart-category="'+esc(category)+'" role="button" tabindex="0" aria-label="查看'+esc(r.name)+'规模收益图"><title>'+esc(r.name)+' '+fmt(r.size)+'亿元 · '+pct(r.share)+'</title></path>';
    }).join('');
    return '<div class="type-pie-layout"><svg class="type-pie" viewBox="0 0 220 220" role="group" aria-label="产品类型净资产规模饼图">'+slices+'</svg><div class="type-pie-legend">'+types.map(r=>{const category=r.name==='固定收益类'?cats[0]:r.name;return '<button data-chart-category="'+esc(category)+'" class="type-bar pie-legend-row"><i style="background:'+colors[cats.indexOf(category)]+'"></i><span>'+esc(r.name)+'</span><strong>'+pct(r.share)+'</strong><small>'+fmt(r.size)+' 亿元</small></button>';}).join('')+'</div></div>';
  }
  function title(name,sub,actions=''){return '<div class="page-heading"><div><h1>'+name+'</h1><div class="subtle">'+sub+'</div></div>'+actions+'</div>';}
  function panel(head,body,note=''){return '<section class="panel"><div class="panel-head"><h2>'+head+'</h2></div>'+body+(note?'<div class="scope-note">'+note+'</div>':'')+'</section>';}
  function analytics(){
    const d=state.data,m=d.metrics,period='<div class="period-pill">最新资料月份 <b>'+d.month+'</b></div>';
    const heading=title('保险资管 · 行业与产品分析','行业全口径与开放式披露样本分别呈现，单位：亿元',period);
    const kpi='<div class="kpi-grid"><div class="kpi"><div class="label">行业净资产规模（亿元）</div><strong>'+fmt(m.size)+'</strong><small>原表环比 <span class="'+(m.mom<0?'down':'up')+'">'+pct(m.mom)+'</span></small></div><div class="kpi"><div class="label">行业产品只数</div><strong>'+fmt(m.count,0)+'</strong><small>报告期未终止产品</small></div><div class="kpi"><div class="label">管理机构</div><strong>'+m.managerCount+'</strong><small>前五家规模占比 '+pct(m.top5)+'</small></div><div class="kpi"><div class="label">开放式披露样本</div><strong>'+fmt(m.sampleCount,0)+'</strong><small>'+m.sampleManagerCount+'家机构 · 样本规模 '+fmt(m.sampleSize)+'</small></div></div>';
    return heading+kpi+'<nav class="section-nav" aria-label="分析模块"><button data-module="market" class="'+(state.module==='market'?'active':'')+'">全市场统计</button><button data-module="risk" class="'+(state.module==='risk'?'active':'')+'">收益分析</button><button data-module="products" class="'+(state.module==='products'?'active':'')+'">产品分类</button></nav><div id="module-content">'+(state.module==='market'?market():state.module==='risk'?risk():products())+'</div><div class="am-footer">数据截至 '+d.period+' · '+d.sources.length+'份原报告 · <a class="am-btn" href="'+download('database.xlsx')+'" target="_blank" rel="noopener">下载最新产品数据库</a></div>';
  }
  function market(){
    const d=state.data,types=d.types.filter(r=>r.name!=='总计');
    const bars=typePie(types);
    const summary='<ul class="summary-list">'+d.report.sections[0].text.map(t=>'<li>'+esc(t).replace(/^(行业情况|公司情况|竞品情况)([：:])/,'<strong>$1$2</strong>')+'</li>').join('')+'</ul>';
    return '<div class="panel-grid overview-grid">'+panel('产品类型与规模分布',bars,'行业全口径，包含开放式与封闭式产品。点击类型查看下方开放式产品规模收益图；固定收益默认显示非货币类，可另选货币类。')+panel('本期统计摘要',summary)+'</div>'+typeChart()+
      panel('行业规模与结构',table(['产品类型','产品数量（只）','净资产规模（亿元）','规模占比（%）','原表环比（%）','较上期规模增减（亿元）'],d.types.map(r=>[esc(r.name),fmt(r.count,0),fmt(r.size),pct(r.share),numericPct(r.mom),numeric(r.change)])),'较上期：'+(d.priorMonth||'未取得')+' → '+d.month+'；环比取自报告原表。')+
      panel('管理机构规模排名','<div class="scope-note manager-source">来源：《组合行情》报告第2表“机构管理规模”的“合计（亿元）”列。采用行业全口径（含开放式、封闭式产品），不是开放式披露产品清单加总。</div>'+table(['排名 / 管理机构','净资产规模（亿元）','行业份额（%）','较上期增减（亿元）','较上年末增减（亿元）'],d.managers.map(r=>['<span class="rank">'+r.rank+'</span>　'+esc(r.manager),fmt(r.total),pct(r.share),numeric(r.change),numeric(r.ytdChange)])),'机构份额使用原表规模除以行业总规模；上年末比较期：'+(d.baselineMonth||'未取得')+'。')+
      panel('持有人资金来源',table(['资金来源','规模（亿元）','占比（%）','较上期占比变化（百分点）','年初以来规模增幅（%）'],d.holders.map(r=>[esc(r.name),fmt(r.size),pct(r.share),numeric(r.shareChange==null?null:r.shareChange*100),pct(r.ytdGrowth)])),'业内、业外及其细分行按原表层级呈现，完整结构见月报。');
  }
  function chartKey(category=state.chartCategory){return category===cats[3]?'annualized':state.chartMetric||'monthly';}
  function chartRows(category=state.chartCategory){const key=chartKey(category);return state.data.products.filter(r=>r.category===category&&Number.isFinite(r[key])&&Number.isFinite(r.size)&&r.size>0);}
  function typeChart(){
    return '<section class="panel type-chart" id="type-chart"><div class="panel-head"><div><h2>按产品类型看规模与收益</h2><div class="subtle">开放式披露样本 · 每个圆点代表一只产品</div></div></div><div class="chart-types" role="group" aria-label="规模收益图产品类型">'+cats.map((c,i)=>'<button data-chart-category="'+esc(c)+'" aria-pressed="'+(c===state.chartCategory)+'" class="'+(c===state.chartCategory?'active':'')+'"><i style="background:'+colors[i]+'"></i>'+esc(c)+'</button>').join('')+'</div><div id="type-chart-body" aria-live="polite">'+typeChartBody()+'</div></section>';
  }
  function typeChartBody(){
    const category=state.chartCategory,rows=chartRows(),total=state.data.products.filter(r=>r.category===category).length,key=chartKey(),label=key==='annualized'?'年初以来年化收益率':key==='monthly'?'本月收益率':'年初以来累计收益率',size=rows.reduce((s,r)=>s+r.size,0),avg=rows.length?rows.reduce((s,r)=>s+r[key],0)/rows.length:null;
    const metric=category===cats[3]?'<div class="subtle chart-metric-note">货币类使用报告披露的年初以来年化收益率。</div>':'<div class="chart-metrics" role="group" aria-label="收益区间">'+[['monthly','本月收益'],['ytd','年初以来收益']].map(([value,name])=>'<button data-chart-metric="'+value+'" aria-pressed="'+(key===value)+'" class="'+(key===value?'active':'')+'">'+name+'</button>').join('')+'</div>';
    const view=scatterViewport(rows,key),zoom=rows.length>40?'<div class="chart-view-controls" role="group" aria-label="散点图显示范围">'+[['dense','放大密集区'],['all','全部范围']].map(([value,name])=>'<button data-chart-view="'+value+'" aria-pressed="'+((state.chartView||'dense')===value)+'" class="'+((state.chartView||'dense')===value?'active':'')+'">'+name+'</button>').join('')+'<span class="subtle">普通坐标轴 · 可切换查看完整分布</span></div>':'';
    const viewNote=view.rows.length<rows.length?'当前放大密集区，另有 '+(rows.length-view.rows.length)+' 只产品位于视窗外，点击“全部范围”查看。上方统计包含全部有效样本。':'当前展示全部有效样本。';
    return metric+'<div class="chart-summary"><span><b>'+esc(category)+'</b></span>'+(rows.length===total?'<span>有效样本 <b>'+rows.length+'</b>只</span>':'')+'<span>有效样本规模合计 <b>'+fmt(size)+'</b>亿元</span><span>'+label+'均值 <b>'+pct(avg)+'</b></span></div>'+zoom+scatter(category)+'<div class="chart-hover" id="chart-hover">悬浮圆点查看产品名称、机构和数值，点击查看完整详情。</div><div class="scope-note">横轴：期末净资产规模（亿元）；纵轴：'+label+'。均值为披露产品简单平均。'+viewNote+(rows.length<total?'当前区间有'+(total-rows.length)+'只产品缺少有效规模或收益，图中展示已有数据的产品。':'')+'</div>';
  }
  function bindTypeChart(){
    $$('[data-chart-category]').forEach(button=>{
      button.onkeydown=event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();button.onclick();}};
      button.onclick=()=>{
      state.chartCategory=button.dataset.chartCategory;$('#type-chart-body').innerHTML=typeChartBody();
      $$('[data-chart-category]').forEach(b=>{const active=b.dataset.chartCategory===state.chartCategory;b.classList.toggle('active',active);b.setAttribute('aria-pressed',String(active));});
      bindChartMetrics();bindProductLinks();
      if(button.classList.contains('type-bar')||button.classList.contains('pie-slice'))$('#type-chart').scrollIntoView({behavior:'smooth',block:'start'});
      };
    });
    bindChartMetrics();bindProductLinks();
  }
  function bindChartMetrics(){
    $$('[data-chart-metric]').forEach(button=>button.onclick=()=>{state.chartMetric=button.dataset.chartMetric;$('#type-chart-body').innerHTML=typeChartBody();bindChartMetrics();bindProductLinks();});
    $$('[data-chart-view]').forEach(button=>button.onclick=()=>{state.chartView=button.dataset.chartView;$('#type-chart-body').innerHTML=typeChartBody();bindChartMetrics();bindProductLinks();});
  }
  function axisBounds(values,nonnegative=false){
    const low=Math.min(...values),high=Math.max(...values),span=high-low;
    const padding=span>0?span*.08:Math.max(Math.abs(low)*.08,.01);
    return [nonnegative?Math.max(0,low-padding):low-padding,high+padding];
  }
  function scatterViewport(rows,key){
    if(!rows.length)return {rows:[],x:[0,1],y:[-1,1]};
    const xs=rows.map(r=>r.size).sort((a,b)=>a-b),ys=rows.map(r=>r[key]).sort((a,b)=>a-b);
    const quantile=(a,p)=>{const n=(a.length-1)*p,i=Math.floor(n);return a[i]+(a[Math.min(i+1,a.length-1)]-a[i])*(n-i);};
    let x=axisBounds(xs,true),y=axisBounds(ys);
    if((state.chartView||'dense')==='dense'&&rows.length>40){
      x=axisBounds([xs[0],quantile(xs,.95)],true);
      y=axisBounds([quantile(ys,.025),quantile(ys,.975)]);
    }
    return {x,y,rows:rows.filter(r=>r.size>=x[0]&&r.size<=x[1]&&r[key]>=y[0]&&r[key]<=y[1])};
  }
  function scatter(category=state.chartCategory){
    const all=chartRows(category),key=chartKey(category),label=key==='annualized'?'年初以来年化收益率':key==='monthly'?'本月收益率':'年初以来累计收益率';
    if(!all.length)return '<div class="empty">该类型暂无同时披露规模与收益的产品。</div>';
    const {rows,x:[minx,maxx],y:[miny,maxy]}=scatterViewport(all,key);
    const x=v=>76+(v-minx)/(maxx-minx)*788,y=v=>354-(v-miny)/(maxy-miny)*312;
    let out='<svg class="scatter" data-kind="'+cats.indexOf(category)+'" viewBox="0 0 900 412" role="group" aria-label="'+esc(category)+'期末规模与'+label+'散点图"><text x="76" y="21" class="axis-title">'+label+'（%）</text>';
    for(let i=0;i<=5;i++){const yy=42+i*62.4,val=maxy-(maxy-miny)*i/5;out+='<line x1="76" x2="864" y1="'+yy+'" y2="'+yy+'"/><text x="65" y="'+(yy+4)+'" text-anchor="end">'+pct(val)+'</text>';}
    for(let i=0;i<=5;i++){const val=minx+(maxx-minx)*i/5,xx=76+i*157.6;out+='<line x1="'+xx+'" x2="'+xx+'" y1="42" y2="354" class="vertical-grid"/><text x="'+xx+'" y="380" text-anchor="middle">'+fmt(val,maxx-minx<10?2:0)+'</text>';}
    if(miny<0&&maxy>0)out+='<line x1="76" x2="864" y1="'+y(0)+'" y2="'+y(0)+'" class="zero-line"/>';
    for(const r of rows)out+='<circle data-product-id="'+esc(r.id)+'" role="button" tabindex="0" aria-label="查看产品 '+esc(r.name)+'" cx="'+x(r.size)+'" cy="'+y(r[key])+'" r="2.8" opacity=".95"><title>'+esc(r.name)+' | '+esc(r.manager)+' | '+fmt(r.size)+'亿元 | '+label+' '+pct(r[key])+'</title></circle>';
    return out+'<text x="470" y="405" class="axis-title" text-anchor="middle">期末净资产规模（亿元）</text></svg>';
  }
  function risk(){
    const d=state.data;
    return panel('收益分布与同类比较',table(['产品类别','样本数量（只）','YTD有效样本（只）','本月均值（%）','YTD均值（%）','YTD中位数（%）','YTD最高（%）','YTD最低（%）'],d.returns.map(r=>[esc(r.category),r.count,r.valid,r.money?'未披露':pct(r.monthly),pct(r.mean),pct(r.median),pct(r.max),pct(r.min)])),'均值为披露样本简单平均。货币类YTD列为年化收益，其余为累计收益；各类别分别比较。')+
      typeChart()+
      panel('开放式非货币固收 · 机构比较',table(['管理机构','样本规模（亿元）','产品数量（只）','较上期增减（亿元）','本月收益均值（%）','YTD收益均值（%）'],d.sampleManagers.map(r=>[esc(r.manager),fmt(r.size),r.count,numeric(r.change),pct(r.monthly),pct(r.ytd)])),'本表为开放式报告实际披露样本；跨期规模增减包含清单变化。');
  }
  function filtered(){
    let a=state.data.products.filter(r=>(!state.category||r.category===state.category)&&(!state.manager||r.manager===state.manager)&&(!state.search||(r.name+r.manager+r.id).toLowerCase().includes(state.search.toLowerCase())));
    const key=state.sort;a.sort((x,y)=>compareValues(x[key],y[key],state.sortDirection||'desc')||x.id.localeCompare(y.id));return a;
  }
  function productTable(){
    const a=filtered(),pages=Math.max(1,Math.ceil(a.length/25));state.pageNo=Math.min(state.pageNo,pages);const shown=a.slice((state.pageNo-1)*25,state.pageNo*25);
    return table(['产品名称 / 产品ID','管理机构','报告类别','规模（亿元）','本月收益（%）','YTD累计收益（%）','货币YTD年化（%）','成立日期'],shown.map(r=>['<button class="product-link" data-product-id="'+esc(r.id)+'" title="'+esc(r.file+' / 表'+r.table+' / 行'+r.row)+'">'+esc(r.name)+'</button><div class="subtle">'+r.id+'</div>',esc(r.manager),esc(r.category),fmt(r.size),pct(r.monthly,'/'),pct(r.ytd,'/'),pct(r.annualized,'/'),esc(r.inception)]),'',{id:'products',keys:['name','manager','category','size','monthly','ytd','annualized','inception']})+
      '<div class="pager"><span class="subtle">共 '+a.length+'只 · 第 '+state.pageNo+' / '+pages+' 页 · 每页25只</span><div class="controls"><button id="prev" '+(state.pageNo===1?'disabled':'')+'>上一页</button><button id="next" '+(state.pageNo===pages?'disabled':'')+'>下一页</button></div></div>';
  }
  function products(){
    const d=state.data,managers=[...new Set(d.products.map(r=>r.manager))].sort();
    return '<section class="panel"><div class="panel-head"><h2>开放式披露产品明细</h2><button id="export-filter">导出当前筛选 CSV</button></div><div class="filters"><input id="search" aria-label="搜索产品或机构" placeholder="搜索产品名称、管理机构或产品ID" value="'+esc(state.search)+'"><select id="category" aria-label="产品类别"><option value="">全部产品类别</option>'+cats.map(c=>'<option'+(state.category===c?' selected':'')+'>'+esc(c)+'</option>').join('')+'</select><select id="manager" aria-label="管理机构"><option value="">全部管理机构</option>'+managers.map(c=>'<option'+(state.manager===c?' selected':'')+'>'+esc(c)+'</option>').join('')+'</select><select id="sort" aria-label="排序指标">'+[['size','规模'],['monthly','本月收益'],['ytd','YTD累计收益'],['annualized','货币YTD年化'],['name','产品名称'],['manager','管理机构'],['category','报告类别'],['inception','成立日期']].map(([value,label])=>'<option value="'+value+'"'+(state.sort===value?' selected':'')+'>'+label+'</option>').join('')+'</select></div><div id="product-table">'+productTable()+'</div><div class="scope-note">数据期 '+d.month+'。缺失值不参与收益排序；真实0与负值按原文保留。产品ID为本地稳定ID。</div></section>';
  }
  function bindProducts(){
    function refresh(){state.pageNo=1;$('#product-table').innerHTML=productTable();bindPager();}
    $('#category').onchange=e=>{state.category=e.target.value;refresh();};$('#manager').onchange=e=>{state.manager=e.target.value;refresh();};$('#sort').onchange=e=>{state.sort=e.target.value;state.sortDirection=['name','manager','category','inception'].includes(state.sort)?'asc':'desc';refresh();};
    let timer;$('#search').oninput=e=>{state.search=e.target.value;clearTimeout(timer);timer=setTimeout(refresh,150);};
    $('#export-filter').onclick=()=>{const headers=['产品ID','产品名称','管理机构','报告大类','期末规模（亿元）','本月收益率（%）','YTD累计收益率（%）','货币YTD年化收益率（%）','成立日期','来源文件','原表表号','原表行号'],rows=filtered().map(r=>[r.id,r.name,r.manager,r.category,r.size,pct(r.monthly,'/'),pct(r.ytd,'/'),pct(r.annualized,'/'),r.inception,r.file,r.table,r.row]),csv='\ufeff'+[headers,...rows].map(a=>a.map(v=>'"'+String(v??'').replace(/"/g,'""')+'"').join(',')).join('\r\n'),url=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'})),a=document.createElement('a');a.href=url;a.download='保险资管产品_'+state.data.month+'_筛选明细.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),5000);};bindPager();
  }
  function bindPager(){if($('#prev'))$('#prev').onclick=()=>{state.pageNo--;$('#product-table').innerHTML=productTable();bindPager();};if($('#next'))$('#next').onclick=()=>{state.pageNo++;$('#product-table').innerHTML=productTable();bindPager();};bindTables();bindProductLinks();}
  function bindProductLinks(){
    $$('[data-product-id]').forEach(el=>{
      el.onclick=()=>showProduct(el.dataset.productId);
      if(el.tagName?.toLowerCase()==='circle'){
        el.onmouseenter=el.onfocus=()=>{const p=state.data.products.find(r=>r.id===el.dataset.productId),tip=$('#chart-hover');if(p&&tip){const key=chartKey(p.category),label=key==='monthly'?'本月收益':key==='annualized'?'年初以来年化':'年初以来收益';tip.innerHTML='<strong>'+esc(p.name)+'</strong><span>'+esc(p.manager)+'</span><span>规模 <b>'+fmt(p.size)+'</b> 亿元</span><span>'+label+' <b>'+pct(p[key])+'</b></span>';}};
        el.onkeydown=event=>{
        if(event.key==='Enter'||event.key===' '){event.preventDefault();showProduct(el.dataset.productId);}
        };
      }
    });
  }
  function showProduct(id){
    const product=state.data.products.find(r=>r.id===id);
    if(!product)return;
    $('#product-detail')?.remove();
    const dialog=document.createElement('dialog');
    dialog.id='product-detail';dialog.className='product-dialog';
    dialog.setAttribute('aria-labelledby','product-detail-title');
    const fields=[['管理机构',esc(product.manager)],['产品ID',esc(product.id)],['报告类别',esc(product.category)],
      ['报告月份',esc(state.data.month)],['期末规模',fmt(product.size)+' 亿元'],['本月收益',pct(product.monthly,'未披露')],
      ['年初以来累计收益',pct(product.ytd,'未披露')],['货币年初以来年化',pct(product.annualized,'未披露')],
      ['成立日期',esc(product.inception||'未披露')],['策略标签',esc(product.strategy||'待确认')]];
    dialog.innerHTML='<div class="product-dialog-head"><div><div class="subtle">保险资管 · 产品详情</div><h2 id="product-detail-title">'+esc(product.name)+'</h2></div><button id="close-product" aria-label="关闭产品详情">×</button></div><dl class="product-facts">'+fields.map(([label,value])=>'<div><dt>'+label+'</dt><dd>'+value+'</dd></div>').join('')+'</dl><div class="scope-note">来源 '+esc(product.file)+' · 表 '+esc(product.table)+' · 行 '+esc(product.row)+'</div><div class="product-dialog-actions"><button class="primary" id="locate-product">跳转产品明细</button></div>';
    root.append(dialog);
    $('#close-product').onclick=()=>dialog.close();
    dialog.onclick=event=>{if(event.target===dialog){const r=dialog.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)dialog.close();}};
    $('#locate-product').onclick=()=>{
      dialog.close();state.module='products';state.category='';state.manager='';state.search=product.id;state.pageNo=1;
      state.page='analytics';switchMarket('insurance');render();$('#product-table').scrollIntoView({behavior:'smooth',block:'center'});
    };
    dialog.addEventListener('close',()=>dialog.remove(),{once:true});
    dialog.showModal();
  }
  function reports(){
    const options=[...state.meta.months].reverse().map(m=>'<option value="'+m+'"'+(m===state.reportMonth?' selected':'')+'>'+monthName(m)+(m===state.meta.latest?' · 最新':'')+'</option>').join('');
    return title('保险资管 · 月报中心','按报告实际月份归档；上传新月份后自动加入列表')+
      '<div class="panel report-controls"><label for="report-month">选择月份</label><select id="report-month">'+options+'</select><a class="am-btn primary" id="report-bundle" href="'+download('report-'+state.reportMonth+'.zip')+'" target="_blank" rel="noopener">一键导出 Word＋Excel</a><a class="am-btn" id="report-word" href="'+download('report-'+state.reportMonth+'.docx')+'" target="_blank" rel="noopener">Word</a><a class="am-btn" id="report-excel" href="'+download('report-'+state.reportMonth+'.xlsx')+'" target="_blank" rel="noopener">Excel 明细</a><span class="subtle">直接下载，无需登录。</span></div><div id="report-body"><div class="loading"><span class="spinner"></span>正在读取本期月报…</div></div>';
  }
  async function loadReport(){
    const wanted=state.reportMonth;
    try{const v=state.cache[wanted]||await api('/period/'+wanted);state.cache[wanted]=v;if(state.reportMonth!==wanted||state.page!=='reports')return;state.report=v;
      $('#report-body').innerHTML='<article class="report-paper report-reference"><h1>'+esc(v.report.title)+'</h1><div class="report-subtitle">'+esc(v.report.subtitle)+'</div>'+
        v.report.sections.map(s=>'<section><h2>'+esc(s.title)+'</h2>'+(s.blocks||[...(s.text||[]).map(text=>({type:'paragraph',text})),...(s.tables||[]).map(t=>({type:'table',...t}))]).map(reportBlock).join('')+'</section>').join('')+'</article>';
    }catch(e){if($('#report-body'))$('#report-body').innerHTML='<div class="panel empty">'+esc(e.message)+'</div>';}
  }
  function reportBlock(b){
    if(b.type==='paragraph')return '<p class="report-paragraph'+(b.bullet?' report-bullet':'')+'">'+(b.label?'<strong class="report-label">'+esc(b.label)+'：</strong>':'')+(b.lead?'<strong>'+esc(b.lead)+'</strong>':'')+esc(b.text||'')+'</p>';
    if(b.type==='subheading')return '<h3>'+esc(b.text)+'</h3>';
    if(b.type!=='table'||!b.rows.length)return '';
    const cell=c=>esc(c).replace(/\n/g,'<br>'),weights=b.widths||b.headers.map((_,i)=>i?1:b.firstColumnWeight||2),sum=weights.reduce((a,c)=>a+c,0);
    return '<figure class="report-table"><figcaption>'+esc(b.title)+'</figcaption><div class="report-table-scroll"><table><colgroup>'+weights.map(w=>'<col style="width:'+w/sum*100+'%">').join('')+'</colgroup><thead><tr>'+b.headers.map(h=>'<th scope="col">'+cell(h)+'</th>').join('')+'</tr></thead><tbody>'+b.rows.map((r,i)=>'<tr class="'+(b.totalRows?.includes(i)?'report-total ':'')+(b.emphasisRows?.includes(i)?'report-emphasis':'')+'">'+r.map((c,j)=>'<td'+(!j?' class="report-name"':b.negativeRed&&/^-\d/.test(String(c))?' class="report-negative"':'')+'>'+cell(c)+'</td>').join('')+'</tr>').join('')+'</tbody></table></div>'+(b.source?'<p class="report-table-source">'+esc(b.source)+'</p>':'')+'</figure>';
  }
  function history(){return '<div class="history-item"><div>当前云端资料 · '+new Date(state.meta.updated).toLocaleString('zh-CN',{timeZone:'Asia/Shanghai'})+'<small>月报月份 '+state.meta.months.join('、')+'</small></div><a class="am-btn" href="'+download('database.xlsx')+'" target="_blank" rel="noopener">下载最新Excel</a></div>';}

  function upload(){
    return title('资料上传与云端更新','上传同月份的两份行业报告，自动联动数据库、分析和月报')+
      '<div class="upload-area">'+panel('每月更新流程','<div class="step-strip"><span>① 上传两份报告</span><span>② 核验月份与数据</span><span>③ 更新Excel和月报</span><span>④ 发布最新数据</span></div><div class="callout">新月份加入月报列表；同月资料更新后提供最新结果。重复资料跳过导入，模板升级时自动重新生成月报。</div>')+
      '<section class="panel" id="upload-control"><div class="loading"><span class="spinner"></span>正在检查上传权限…</div></section>'+
      panel('当前云端资料',history(),state.meta.sourceFiles+'份有效原报告 · '+state.meta.productRows+'条产品历史记录')+'</div>';
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
      $$('[data-module]').forEach(b=>b.onclick=()=>{state.module=b.dataset.module;render();});if(state.module==='products')bindProducts();else {bindTypeChart();bindTables();}
    }else if(state.page==='reports'){
      $('#report-month').onchange=e=>{state.reportMonth=e.target.value;render();};loadReport();
    }else loadAdmin();
  }
  document.title='资管市场竞品看板';
  reload();
})();
