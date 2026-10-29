/* Full-market adapter. Reference layout remains in index.html. */
'use strict';
function snapshotMode(){return window.__FUND_OFFLINE__===true;}
function canConnect(){return !snapshotMode()&&navigator.onLine && !(typeof location!=='undefined' && new URLSearchParams(location.search).get('offline')==='1');}
const SNAP = window.MARKET_SNAPSHOT || {meta:{},funds:[],perf:{},details:{},realtime:{}};
const MARKET = {byCode:new Map(), page:1, size:50, signature:'', busy:false,
  detailJobs:new Map(), detailTried:new Set(),
  detailQueue:Promise.resolve(), sourceMode:'随附快照', failures:[], cacheTimer:null,
  visibleRun:0, visibleKey:'', lazyReady:false, detailProgress:null,
  snapshotIssue:'', snapshotLoaded:Object.keys(SNAP.perf||{}).length,
  returnJob:null, moneyJob:null, returnProgress:null, moneyNonce:0,
  updatedAt:SNAP.meta.updatedAt||'', refreshTime:null, lastVisible:[], stats:{detailOk:0,detailFail:0}};
const finite = value => value==null || value==='' || value==='--' || !Number.isFinite(Number(value)) ? null : Number(value);
const htmlText = value => escapeHtml(value==null?'--':String(value));
function shareClass(name){ return ((name||'').match(/([ABCDEHIJNPQRSXY])(?:[（(](?:人民币|美元)[）)])?$/)||[])[1]||'_'; }
function baseName(name){ return (name||'').replace(/([ABCDEHIJNPQRSXY])(?=(?:[（(](?:人民币|美元)[）)])?$)/,''); }
function isCurrencyShare(p){return /(?:人民币|美元现钞|美元现汇|美元|现钞|现汇|美钞|美汇)(?:[（(]QDII(?:-FOF)?[）)])?[A-Z]?$|[（(](?:人民币|美元)[）)]$/.test(p.name||'');}
function localStamp(value){
  if(!value) return '--';
  const date=new Date(value); if(Number.isNaN(+date)) return String(value);
  return date.toLocaleString('zh-CN',{timeZone:'Asia/Shanghai',hour12:false});
}
function reportFailure(source,error){
  const message=source+'：'+(error&&error.message?error.message:String(error));
  MARKET.failures.push(message); if(MARKET.failures.length>30) MARKET.failures.shift();
}
function healthFailures(){return [...(MARKET.snapshotIssue?[MARKET.snapshotIssue]:[]),...MARKET.failures];}
function checkSnapshotCompleteness(){
  const expected=finite(SNAP.meta.collection&&SNAP.meta.collection.directoryCount);
  MARKET.snapshotLoaded=Object.keys(SNAP.perf||{}).length;
  MARKET.snapshotIssue=expected!=null&&MARKET.snapshotLoaded!==expected?
    '随附快照加载不完整：已加载 '+MARKET.snapshotLoaded.toLocaleString('zh-CN')+' / '+expected.toLocaleString('zh-CN')+' 份额数据。请重新加载页面；当前可读数据仍可查看。':'';
  return !MARKET.snapshotIssue;
}
function addCategory(l1,color,l2,l3){
  let group=INVEST_HIERARCHY.find(h=>h.l1===l1);
  if(!group){group={l1,color,desc:'公开目录分类',l2:[]};INVEST_HIERARCHY.push(group);L1_BY_KEY[l1]=group;}
  let second=group.l2.find(x=>x.key===l2);
  if(!second){second={key:l2,l3:[]};group.l2.push(second);}
  if(!second.l3.includes(l3)) second.l3.push(l3);
  return {l1,l2,l3};
}
assignInvestType=function(p){
  const type=p.type||'';
  if(/商品型/.test(type)||type==='指数型-其他'&&/黄金ETF|黄金交易型|上海金|白银期货/.test(p.name))return addCategory('商品型','#D6AE55','商品投资',/黄金|上海金/.test(p.name)?'黄金':'其他商品');
  if(TYPE_TO_HIER[type]) return {...TYPE_TO_HIER[type]};
  if(/reits?/i.test(type+' '+p.name)) return {l1:'REITs',l2:'基础设施REIT',l3:'公募REIT'};
  if(/货币/.test(type)) return {l1:'货币型',l2:'普通货币',l3:'货币基金'};
  if(/可转债/.test(type)) return addCategory('债券型','#4ECDC4','混合债','可转债');
  if(/混合型.*平衡/.test(type)) return addCategory('混合型','#FFB85C','平衡混合','平衡混合');
  if(/QDII/.test(type)) return addCategory('QDII','#A8DADC',/商品/.test(type)?'商品QDII':'其他QDII',type);
  if(/FOF/.test(type)) return addCategory('FOF','#C77DFF','其他FOF',type);
  if(/债券/.test(type)) return addCategory('债券型','#4ECDC4','其他债券',type);
  if(/混合/.test(type)) return addCategory('混合型','#FFB85C','其他混合',type);
  if(/股票/.test(type)) return addCategory('股票型','#FF6B6B','其他股票',type);
  return addCategory('其他','#8897BA','其他类型',type||'未分类');
};
STATUS_META.unknown={color:'#7A8294',label:'申购状态未核验'};
classifyFundSubtype=function(p){
  const name=p.name||'',type=p.type||'',code=String(p.code||'');
  const exchange=code.startsWith('5')?'SH':/^(15|16|18)/.test(code)?'SZ':'--';
  const result=(fundSubtype,exchangeTraded=false,isETF=false,isETFLink=false)=>({fundSubtype,isETF,isETFLink,isExchangeTraded:exchangeTraded,exchange:exchangeTraded?exchange:'--'});
  if(/ETF.*联接/.test(name))return result('ETF联接',false,false,true);
  if(/ETF/.test(name)&&/^(5|15|16)/.test(code))return result('ETF本体',true,true);
  if(/LOF/i.test(name))return result('LOF',true);
  if(/FOF/.test(type+' '+name))return result('FOF');
  if(/^reits?$/i.test(type)||/基础设施/.test(type))return result('REITs',true);
  if(/QDII/.test(type))return result('QDII');
  if(/货币/.test(type))return result('货币基金',code.startsWith('5'));
  return result('普通开放式基金');
};
function purchaseMeta(value){
  if(!value) return {code:'unknown',label:'申购状态未核验'};
  if(/暂停|封闭|不开放/.test(value)) return {code:'closed',label:value};
  if(/限额|限购|大额/.test(value)) return {code:'limited',label:value};
  if(/开放|正常/.test(value)) return {code:'open',label:value};
  return {code:'unknown',label:value};
}
setProductsFromPool=function(funds){
  const unique=new Map();
  for(const item of funds||[]){
    const code=String(item.code||'').padStart(6,'0');
    if(!/^\d{6}$/.test(code)||!item.name||unique.has(code)) continue;
    const p=normalizeProductPoolItem(item);
    Object.assign(p,{code,company:item.company||null,companyId:item.companyId||null,
      shareClass:item.shareClass||shareClass(item.name),familyId:baseName(item.name),
      scale:finite(item.scale),annualReturn:finite(item.annualReturn),maxDrawdown:null,
      manager:item.manager||'-',status:purchaseMeta(item.purchaseStatus),
      sourceUpdatedAt:item.sourceUpdatedAt||'',purchaseStatus:item.purchaseStatus||null,
      inceptionMeta:item.inceptionMeta&&typeof item.inceptionMeta==='object'?{...item.inceptionMeta}:undefined});
    Object.assign(p,assignInvestType(p),classifyFundSubtype(p)); p._themes=detectTheme(p); unique.set(code,p);
  }
  const families=new Map(), priority={A:0,_:1,B:2,C:3,E:4,Y:9};
  for(const p of unique.values()){
    const key=baseName(p.name); if(!families.has(key))families.set(key,[]);families.get(key).push(p);
  }
  for(const members of families.values()){
    members.sort((a,b)=>(priority[a.shareClass]??5)-(priority[b.shareClass]??5)||a.code.localeCompare(b.code));
    members.forEach((p,i)=>p.isPrimary=i===0);
  }
  PRODUCTS.splice(0,PRODUCTS.length,...unique.values());MARKET.byCode=unique;buildFamilies();
};
familyKey=p=>baseName(p.name)||p.code;
nameStripShareClass=baseName;
isMoneyFund=code=>{const p=MARKET.byCode.get(code);return !!p&&p.l1==='货币型';};
// The source reports class-level assets (verified against an A/C pair).
// Each class code contributes once; unknown classes are not filled with zero.
familyScale=function(p,seenSources){
  const members=FAMILY_MEMBERS.get(FAMILY_BY_CODE.get(p.code))||[p],sources=new Map();
  for(const m of members){const pf=DS.perfMap[m.code]||{},value=finite(pf.scale),source=pf.scaleSourceCode||m.code;
    if(value==null||seenSources&&seenSources.has(source))continue;
    const prior=sources.get(source);if(!prior||String(pf.scaleDate||'')>prior.date)sources.set(source,{value,date:String(pf.scaleDate||'')});
  }
  if(seenSources)for(const source of sources.keys())seenSources.add(source);
  return sources.size?[...sources.values()].reduce((sum,item)=>sum+item.value,0):null;
};
getPerf=function(p){
  const pf=DS.perfMap[p.code]||{},money=isMoneyFund(p.code);
  return {...pf,d1:money?null:finite(pf.d1),w1:money?null:finite(pf.w1),
    y1:finite(pf.y1),mdd:money?null:finite(pf.mdd),ytdMdd:money?null:finite(pf.ytdMdd),
    scale:STATE.showAllShares?finite(pf.scale):familyScale(p)};
};
function validInceptionDate(value){
  if(typeof value!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(value))return null;
  const parsed=new Date(value+'T00:00:00Z');
  return Number.isFinite(+parsed)&&parsed.toISOString().slice(0,10)===value?value:null;
}
const INCEPTION_STATUSES={
  not_established:['尚未成立','来源明确标注该产品尚未成立'],
  not_disclosed:['未披露','已查询来源未披露成立日期'],
  source_unavailable:['来源暂无','现有来源暂无该代码的可用成立日期资料'],
  network_failed:['获取失败','本次来源请求失败，未取得可核验成立日期'],
  identity_mismatch:['待核验','来源返回的产品身份与当前代码尚未核验一致'],
  date_conflict:['待核验','来源成立日期存在冲突，待核验'],
  parse_failed:['待核验','未能从来源页面解析出可核验的成立日期'],
  pending:['待采集','该代码的成立日期尚待采集']
};
function inceptionMetadataNote(meta){
  if(!meta)return '';
  const parts=[];
  if(meta.dateSemantic)parts.push('日期口径：'+String(meta.dateSemantic));
  if(hasField(meta.sourceReportedInceptionDate))parts.push('来源标注成立日：'+meta.sourceReportedInceptionDate);
  if(hasField(meta.issueDate))parts.push('发行日：'+meta.issueDate);
  if(hasField(meta.identityNote))parts.push('身份核验：'+meta.identityNote);
  if(meta.retrievedAt)parts.push('核验时间：'+localStamp(meta.retrievedAt));
  if(meta.sourceUrl)parts.push('来源：'+meta.sourceUrl);
  return parts.length?' · '+parts.join(' · '):'';
}
function inceptionInfo(p){
  const pf=DS.perfMap[p.code]||{},fund=validInceptionDate(p.inception),detail=validInceptionDate(pf.inceptionDate),meta=p.inceptionMeta;
  const note=inceptionMetadataNote(meta),state=meta&&INCEPTION_STATUSES[meta.status];
  if(state)return {date:null,label:state[0],reason:state[1]+note};
  if(fund&&detail&&fund!==detail)return {date:null,label:'待核验',reason:'当前代码的已存成立日期不一致：'+fund+' / '+detail+note};
  const date=detail||fund;
  return {date,label:date||'未取得',reason:(date?'当前行代码 '+p.code+' 的来源披露成立日期；折叠时为代表代码日期':'现有来源尚未取得该代码的成立日期')+note};
}
function hasInceptionAuthority(fund,perf={}){
  return !!(fund&&(validInceptionDate(fund.inception)||fund.inceptionMeta)||validInceptionDate(perf.inceptionDate));
}
function mergeCachedProduct(known,cached){
  const merged={...known,...cached,company:known.company||cached.company,companyId:known.companyId||cached.companyId};
  if(hasInceptionAuthority(known)){
    if(validInceptionDate(known.inception))merged.inception=known.inception;else delete merged.inception;
    if(known.inceptionMeta)merged.inceptionMeta={...known.inceptionMeta};else delete merged.inceptionMeta;
  }
  return merged;
}
function mergeCachedPerf(known,cached,fund){
  const merged=mergePerf(known,cached);
  if(hasInceptionAuthority(fund,known)){
    const state=fund&&fund.inceptionMeta&&fund.inceptionMeta.status;
    const date=state&&INCEPTION_STATUSES[state]?null:validInceptionDate(known.inceptionDate)||validInceptionDate(fund&&fund.inception);
    if(date)merged.inceptionDate=date;else delete merged.inceptionDate;
    delete merged.inceptionMeta;
    if(known.fieldStatus&&known.fieldStatus.inceptionDate)merged.fieldStatus.inceptionDate=known.fieldStatus.inceptionDate;
    else delete merged.fieldStatus.inceptionDate;
  }
  return enforceInceptionIntervals(merged,fund);
}
function getInceptionDate(p){return inceptionInfo(p).date;}
function inceptionCell(p){
  const info=inceptionInfo(p);
  return '<span'+(info.date?'':' style="color:var(--text-4);font-size:11px"')+' title="'+escapeHtml(info.reason)+'">'+htmlText(info.label)+'</span>';
}
sortedProducts=function(list){
  const key=STATE.sortKey,dir=STATE.sortAsc?1:-1;
  const numeric=new Set(['scale','d1','w1','m1','m3','m6','y1','ytd','ytdMdd']);
  const value=p=>key==='inceptionDate'?getInceptionDate(p):key==='w1'?finite((DS.perfMap[p.code]||{})[isMoneyFund(p.code)?'qrnh':'w1']):numeric.has(key)?finite(getPerf(p)[key]):
    key==='manager'?((DS.perfMap[p.code]||{}).manager||p.manager):p[key];
  return [...list].sort((a,b)=>{
    if(key==='w1'&&isMoneyFund(a.code)!==isMoneyFund(b.code))return isMoneyFund(a.code)?1:-1;
    const av=value(a),bv=value(b);if(av==null&&bv==null)return a.code.localeCompare(b.code);
    if(av==null)return 1;if(bv==null)return -1;
    return (numeric.has(key)?av-bv:String(av).localeCompare(String(bv),'zh-CN'))*dir||a.code.localeCompare(b.code);
  });
};
function dailyGrowthUsable(nav){
  if(!Array.isArray(nav)||nav.length<2||!nav.every((p,i)=>finite(p.x)!=null&&(i===0||finite(p.equityReturn)!=null&&Number(p.equityReturn)>-100)))return false;
  const zeroGrowth=nav.slice(1).every(p=>Number(p.equityReturn)===0);
  const values=nav.map(p=>finite(p.y)).filter(x=>x!=null);
  return !(zeroGrowth&&values.length>1&&Math.max(...values)-Math.min(...values)>1e-10);
}
function performancePoints(raw){
  const nav=raw&&Array.isArray(raw.Data_netWorthTrend)?raw.Data_netWorthTrend.slice().sort((a,b)=>a.x-b.x):null;
  if(dailyGrowthUsable(nav)){
    let indexValue=1;
    return nav.map((point,index)=>{if(index)indexValue*=1+Number(point.equityReturn)/100;return [Number(point.x),indexValue];});
  }
  const cumulative=raw&&raw.Data_grandTotal;
  const source=Array.isArray(cumulative)&&cumulative[0];
  if(!source||!Array.isArray(source.data))return [];
  return source.data.filter(x=>Array.isArray(x)&&finite(x[0])!=null&&finite(x[1])!=null&&Number(x[1])>-100)
    .map(x=>[Number(x[0]),1+Number(x[1])/100]).sort((a,b)=>a[0]-b[0]);
}
function drawdown(points){
  if(points.length<2)return null;
  let peak=points[0][1],worst=0;
  for(const [,value]of points){peak=Math.max(peak,value);worst=Math.min(worst,(value/peak-1)*100);}
  return +worst.toFixed(4);
}
const RETURN_FIELDS=['dwjz','d1','w1','m1','m3','m6','y1','ytd','wfsy','qrnh'];
const RISK_FIELDS=['mdd','ytdMdd','historyStart','mddAsOf','riskMethod','ytdStart','ytdAsOf'];
function hasField(value){return value!==null&&value!==undefined&&value!==''&&value!=='-'&&value!=='--';}
function fieldDate(record,key){
  const status=record.fieldStatus&&record.fieldStatus[key];
  if(status&&Object.prototype.hasOwnProperty.call(status,'asOf'))return status.asOf==null?'':String(status.asOf);
  return String((key==='scale'||key==='scaleDate'||key==='scaleSourceCode'?record.scaleDate:
    RISK_FIELDS.includes(key)?(['ytdMdd','ytdStart','ytdAsOf'].includes(key)?record.ytdAsOf||record.mddAsOf:record.mddAsOf):
      (RETURN_FIELDS.includes(key)||key==='jzrq')?record[key+'AsOf']||record.jzrq:record.detailFetchedAt||record.retrievedAt)||'');
}
function monthsBefore(value,months){
  if(!validInceptionDate(value))return null;
  const [year,month,day]=value.split('-').map(Number),index=year*12+month-1-months;
  const targetYear=Math.floor(index/12),targetMonth=index-targetYear*12;
  const last=new Date(value+'T00:00:00Z');last.setUTCFullYear(targetYear,targetMonth+1,0);
  return String(targetYear).padStart(4,'0')+'-'+String(targetMonth+1).padStart(2,'0')+'-'+String(Math.min(day,last.getUTCDate())).padStart(2,'0');
}
function enforceInceptionIntervals(record,fund){
  const next={...record,fieldStatus:{...(record.fieldStatus||{})}};
  const inception=fund&&(!fund.inceptionMeta||fund.inceptionMeta.status==='verified')?validInceptionDate(fund.inception):null;
  if(!inception)return next;
  for(const [key,months]of [['m1',1],['m3',3],['m6',6],['y1',12]]){
    const end=validInceptionDate(fieldDate(next,key));
    if(end&&inception>monthsBefore(end,months)){
      delete next[key];
      next.fieldStatus[key]={status:'missing',reason:'insufficient_history',asOf:end,inceptionDate:inception};
    }
  }
  return next;
}
function currentYear(){return snapshotMode()&&/^\d{4}/.test(SNAP.meta.collection&&SNAP.meta.collection.asOf||SNAP.meta.updatedAt||'')?String(SNAP.meta.collection&&SNAP.meta.collection.asOf||SNAP.meta.updatedAt).slice(0,4):new Date().toLocaleDateString('sv-SE',{timeZone:'Asia/Shanghai'}).slice(0,4);}
function sanitizeYear(record){
  const next={...record,fieldStatus:{...(record.fieldStatus||{})}},year=currentYear();
  for(const key of ['ytd','ytdMdd']){
    const stamp=fieldDate(record,key);
    if(hasField(record[key])&&(!stamp||stamp.slice(0,4)!==year)){
      next[key]=null;next.fieldStatus[key]={status:'missing',reason:stamp?'stopped_before_year':'missing_nav_date',asOf:stamp||null};
    }
  }
  return next;
}
function mergePerf(old,incoming,fund){
  old=sanitizeYear(old);incoming=sanitizeYear(incoming||{});
  const next={...old,fieldStatus:{...(old.fieldStatus||{})}};
  // Preserve each retained value's own observation date when a later batch
  // advances the record date but leaves that field empty.
  for(const key of [...RETURN_FIELDS,...RISK_FIELDS,'scale','manager'])if(hasField(old[key])&&(!next.fieldStatus[key]||!Object.prototype.hasOwnProperty.call(next.fieldStatus[key],'asOf')))
    next.fieldStatus[key]={status:'available',reason:'已取得公开数据',...next.fieldStatus[key],asOf:fieldDate(old,key)||null};
  for(const [key,value]of Object.entries(incoming||{})){
    if(key==='fieldStatus'||!hasField(value))continue;
    const oldDate=fieldDate(old,key),newDate=fieldDate(incoming,key);
    if(hasField(old[key])&&oldDate&&(!newDate||newDate<oldDate))continue;
    next[key]=value;
    if(incoming.fieldStatus&&incoming.fieldStatus[key])next.fieldStatus[key]=incoming.fieldStatus[key];
    else if(RETURN_FIELDS.includes(key)||RISK_FIELDS.includes(key)||key==='scale'||key==='manager')
      next.fieldStatus[key]={status:'available',reason:'已取得公开数据',asOf:newDate||null};
  }
  for(const [key,status]of Object.entries(incoming.fieldStatus||{})){
    if(!hasField(next[key]))next.fieldStatus[key]=status;
    if(status&&status.status==='not_applicable'){next[key]=null;next.fieldStatus[key]=status;}
  }
  return enforceInceptionIntervals(next,fund);
}
const MISSING_REASONS={
  not_disclosed:['未披露','本次公开来源未披露该字段'],
  insufficient_history:['历史不足','公开历史不足以计算该指标'],
  insufficient_year_history:['区间待核验','缺少年初基准，或尚未取得成立日期以核验本年成立以来区间'],
  missing_growth_series:['未取得','缺少可计算的复权收益序列'],
  not_applicable_money:['不适用','货币基金使用万份收益和七日年化，该价格风险指标不适用'],
  stopped_before_year:['待更新','最新可得净值未覆盖当前年份'],
  missing_nav_date:['日期缺失','未取得该指标的净值日期，无法核验今年以来口径'],
  fetch_failed:['获取失败','本次详情请求失败，联网后可点击刷新数据重试'],
  source_unavailable:['未取得','现有公开来源未返回有效详情']
};
function missingFieldInfo(code,key){
  const pf=DS.perfMap[code]||{},explicit=pf.fieldStatus&&pf.fieldStatus[key];
  if(isMoneyFund(code)&&['dwjz','d1','w1','mdd','ytdMdd'].includes(key))return {status:'not_applicable',reason:'货币基金使用万份收益和七日年化，该价格风险指标不适用'};
  if(explicit)return typeof explicit==='string'?{status:explicit,reason:explicit}:explicit;
  return {status:pf.detailFetchedAt?'not_disclosed':'pending',reason:pf.detailFetchedAt?'本次公开来源未返回该字段':snapshotMode()?'随附快照尚未包含该产品的完整详情':'尚未取得该产品的完整详情，联网后自动补取当前页'};
}
function missingFieldLabel(info){
  return (MISSING_REASONS[info.reason]||[])[0]||({not_applicable:'不适用',insufficient_history:'历史不足',not_disclosed:'未披露',unavailable:'未取得',fetch_failed:'获取失败',pending:'待采集',stale:'待更新'}[info.status])||'未取得';
}
function missingValueCell(code,key){
  const info=missingFieldInfo(code,key),reason=(MISSING_REASONS[info.reason]||[])[1]||info.reason||info.status||'未取得';
  return '<span style="color:var(--text-4);font-size:11px" title="'+escapeHtml(reason+(info.asOf?' · 数据日期 '+info.asOf:''))+'">'+missingFieldLabel(info)+'</span>';
}
function dayText(ms){return new Date(ms).toLocaleDateString('sv-SE',{timeZone:'Asia/Shanghai'});}
function periodReturn(points,start){
  let base=-1;for(let i=0;i<points.length;i++){if(points[i][0]<=start)base=i;else break;}
  if(base<0||base>=points.length-1||points[base][1]<=0)return null;
  return +(100*(points.at(-1)[1]/points[base][1]-1)).toFixed(4);
}
parseInstHold=function(raw){
  const h=raw&&raw.Data_holderStructure,s=h&&Array.isArray(h.series)&&h.series.find(x=>/机构/.test(x.name||''));
  if(!s||!Array.isArray(s.data))return null;
  for(let i=s.data.length-1;i>=0;i--){const v=finite(s.data[i]);if(v!=null)return {ratio:v,date:(h.categories||[])[i]||null};}
  return null;
};
function applyDetail(code,raw){
  if(!raw)return;
  const old=DS.perfMap[code]||{},money=isMoneyFund(code);
  const trend=(Array.isArray(raw.Data_netWorthTrend)?raw.Data_netWorthTrend:[])
    .filter(p=>finite(p.x)!=null).slice().sort((a,b)=>a.x-b.x);
  const last=trend.at(-1),points=performancePoints(raw),pointLast=points.at(-1);
  const moneySeries=Array.isArray(raw.Data_millionCopiesIncome)?raw.Data_millionCopiesIncome:[];
  const stamp=last?dayText(last.x):moneySeries.length?dayText(moneySeries.at(-1)[0]):pointLast?dayText(pointLast[0]):null;
  const next={detailFetchedAt:raw._fetchedAt||new Date().toISOString(),fieldStatus:{}};
  const status=(key,kind,reason,asOf=stamp)=>next.fieldStatus[key]={status:kind,reason,asOf};
  const put=(key,value,reason,asOf=stamp)=>{if(finite(value)!=null){next[key]=finite(value);status(key,'available',reason,asOf);}};
  if(stamp)next.jzrq=stamp;
  const scales=raw.Data_fluctuationScale||{},series=Array.isArray(scales.series)?scales.series:[];
  for(let i=series.length-1;i>=0;i--){if(finite(series[i].y)!=null){
    next.scale=finite(series[i].y);next.scaleDate=(scales.categories||[])[i]||null;next.scaleSourceCode=code;
    status('scale','available','份额代码对应的最新公开规模',next.scaleDate);break;
  }}
  if(next.scale==null)status('scale','not_disclosed','详情来源未返回规模披露值',null);
  const managers=Array.isArray(raw.Data_currentFundManager)?raw.Data_currentFundManager.map(x=>x.name).filter(Boolean):[];
  if(managers.length){next.manager=managers.join('、');status('manager','available','公开详情中的当前基金经理',next.detailFetchedAt);}
  else status('manager','not_disclosed','详情来源未返回基金经理',next.detailFetchedAt);
  if(last&&!money)put('dwjz',last.y,'最新披露单位净值');
  const summary=raw._riskSummary||{},historyStart=summary.historyStart||(points.length?dayText(points[0][0]):null);
  const year=Number(currentYear());
  const yearStart=Date.UTC(year,0,1)-8*3600000;
  const isTruncated=!!summary.historyStart&&points.length&&summary.historyStart<dayText(points[0][0]);
  const periods={m1:['syl_1y',1],m3:['syl_3y',3],m6:['syl_6y',6],y1:['syl_1n',12]};
  for(const [key,[variable,months]]of Object.entries(periods)){
    const anchorDate=monthsBefore(stamp,months),anchor=anchorDate?new Date(anchorDate+'T00:00:00+08:00'):null;
    const enough=!historyStart||!anchor||historyStart<=dayText(+anchor);
    if(!enough){status(key,'insufficient_history','公开历史不足'+(months===12?'一年':months+'个月'));continue;}
    if(finite(raw[variable])!=null)put(key,raw[variable],'来源披露的区间收益');
    else if(!money&&points.length&&anchor)put(key,periodReturn(points,+anchor),'公开收益序列复利计算');
    if(next[key]==null)status(key,'not_disclosed','来源未返回区间收益，且可用历史不足以补算');
  }
  if(!money&&points.length>1){
    if(last&&dailyGrowthUsable(trend))put('d1',last.equityReturn,'公开日增长率');
    else status('d1','unavailable','公开日增长率缺失或为全零占位，未把低频区间收益当作日收益');
    if(points.length>=6&&pointLast[0]-points.at(-6)[0]<=14*86400000)put('w1',periodReturn(points,points.at(-6)[0]),'最近5个净值观察区间的复利收益，6个观察点跨度不超过14天');
    else status('w1','insufficient_history','不足6个近期净值观察点，或6点跨度超过14天');
    const firstInYear=points.findIndex(p=>p[0]>=yearStart);
    const riskAsOf=dayText(pointLast[0]);
    next.mddAsOf=riskAsOf;next.historyStart=historyStart;
    next.riskMethod=dailyGrowthUsable(trend)?'公开日增长率连乘序列':'源累计收益可得区间';
    if(!isTruncated)put('mdd',drawdown(points),'可得完整历史收益序列的最大回撤',riskAsOf);
    const inception=old.inceptionDate||raw.inceptionDate;
    const verifiedNewFund=!!inception&&String(inception).startsWith(String(year))&&String(inception)===dayText(points[0][0]);
    const hasYearAnchor=firstInYear>0||firstInYear===0&&verifiedNewFund;
    if(hasYearAnchor&&(!isTruncated||points[0][0]<yearStart)){
      const start=Math.max(0,firstInYear-1),range=points.slice(start);
      next.ytdStart=dayText(range[0][0]);next.ytdAsOf=riskAsOf;
      put('ytd',periodReturn(points,range[0][0]),start===0&&verifiedNewFund?'当年成立以来的复利收益':'上年末至最新净值日的复利收益');
      put('ytdMdd',drawdown(range),'今年以来收益序列的最大回撤',riskAsOf);
    }else if(firstInYear<0){
      status('ytd','stale','历史序列未覆盖当前年份');status('ytdMdd','stale','历史序列未覆盖当前年份');
    }else{
      status('ytd','insufficient_history','insufficient_year_history');
      status('ytdMdd','insufficient_history','insufficient_year_history');
    }
    // A compact chart can retain a complete-series risk summary. Its own date
    // decides precedence; an old summary never overwrites a newer full backfill.
    if(summary.mddAsOf&&summary.mddAsOf===riskAsOf){
      for(const key of ['mdd','ytdMdd'])if(key!=='ytdMdd'||String(summary.mddAsOf).startsWith(String(year)))
        put(key,summary[key],'完整历史预计算摘要',summary.mddAsOf);
      if(summary.historyStart)next.historyStart=summary.historyStart;
      if(summary.riskMethod)next.riskMethod=summary.riskMethod;
    }
  }else if(!money){
    for(const key of ['d1','w1','ytd','mdd','ytdMdd'])status(key,'insufficient_history','可用历史不足2个观察点');
  }
  const holding=parseInstHold(raw);if(holding){next.instHold=holding.ratio;next.instHoldDate=holding.date;}
  if(money){
    for(const key of ['d1','w1','mdd','ytdMdd','dwjz'])status(key,'not_applicable','货币基金不使用单位净值价格回报和回撤');
    for(const [key,variable]of [['wfsy','Data_millionCopiesIncome'],['qrnh','Data_sevenDaysYearIncome']]){
      const arr=raw[variable];if(Array.isArray(arr)&&arr.length)put(key,arr.at(-1)[1],'货币基金公开收益指标',dayText(arr.at(-1)[0]));
      else status(key,'not_disclosed','详情来源未返回该货币基金收益指标');
    }
  }
  DS.perfMap[code]=mergePerf(old,next,MARKET.byCode.get(code));
  const product=MARKET.byCode.get(code);if(product&&DS.perfMap[code].manager)product.manager=DS.perfMap[code].manager;
}

function scheduleCache(){
  if(snapshotMode())return;
  clearTimeout(MARKET.cacheTimer);MARKET.cacheTimer=setTimeout(async()=>{
    try{const db=await openCache();const tx=db.transaction('state','readwrite');
      tx.objectStore('state').put({funds:PRODUCTS.map(p=>({...p,purchaseStatus:p.purchaseStatus})),
        perf:DS.perfMap,details:DS.pingzhongCache,realtime:DS.realtimeMap,meta:{updatedAt:MARKET.updatedAt,savedAt:Date.now()}},'latest');
      tx.oncomplete=()=>db.close();tx.onerror=()=>db.close();
    }catch(_){/* Embedded snapshot remains usable when browser storage is unavailable. */}
  },500);
}
function openCache(){
  return new Promise((resolve,reject)=>{
    if(!window.indexedDB){reject(new Error('IndexedDB unavailable'));return;}
    const req=indexedDB.open('fund_panorama_v2',1);
    req.onupgradeneeded=()=>{if(!req.result.objectStoreNames.contains('state'))req.result.createObjectStore('state');};
    req.onsuccess=()=>resolve(req.result);req.onerror=()=>reject(req.error);
  });
}
async function readCache(){
  if(snapshotMode())return null;
  try{const db=await openCache();return await new Promise(resolve=>{
    const req=db.transaction('state').objectStore('state').get('latest');
    req.onsuccess=()=>{db.close();resolve(req.result||null);};req.onerror=()=>{db.close();resolve(null);};
  });}catch(_){return null;}
}
const DETAIL_VARS=['Data_netWorthTrend','Data_grandTotal','Data_currentFundManager','Data_fluctuationScale',
  'Data_holderStructure','Data_millionCopiesIncome','Data_sevenDaysYearIncome','syl_1n','syl_6y','syl_3y','syl_1y','fS_code','fS_name'];
loadPingzhong=function(code){
  if(!canConnect())return Promise.resolve(DS.pingzhongCache[code]||null);
  if(MARKET.detailJobs.has(code))return MARKET.detailJobs.get(code);
  if(MARKET.detailTried.has(code))return Promise.resolve(DS.pingzhongCache[code]||null);
  MARKET.detailTried.add(code);
  const job=MARKET.detailQueue.then(async()=>{
    let lastError;
    for(let attempt=0;attempt<2;attempt++){
      for(const key of DETAIL_VARS)try{delete window[key];}catch(_){}
      try{
        await jsonpLoad('https://fund.eastmoney.com/pingzhongdata/'+code+'.js?v='+Date.now()+'&attempt='+attempt,18000);
        if(String(window.fS_code||'')!==code)throw new Error('返回的基金代码不一致');
        const raw={_fetchedAt:new Date().toISOString()};for(const key of DETAIL_VARS)if(window[key]!==undefined)raw[key]=window[key];
        if(!raw.Data_netWorthTrend&&!raw.Data_fluctuationScale&&!raw.Data_millionCopiesIncome)throw new Error('接口未返回净值、规模或货币收益');
        DS.pingzhongCache[code]=raw;applyDetail(code,raw);MARKET.stats.detailOk++;
        scheduleCache();return raw;
      }catch(e){lastError=e;}
      finally{for(const key of DETAIL_VARS)try{delete window[key];}catch(_){};}
    }
    MARKET.stats.detailFail++;reportFailure('基金详情 '+code,lastError);
    const old=DS.perfMap[code]||{},fieldStatus={};
    for(const key of ['scale','manager','d1','w1','m1','y1','ytd','ytdMdd'])
      if(!hasField(old[key]))fieldStatus[key]={status:'missing',reason:'fetch_failed'};
    DS.perfMap[code]=mergePerf(old,{fieldStatus},MARKET.byCode.get(code));
    return DS.pingzhongCache[code]||null;
  }).finally(()=>MARKET.detailJobs.delete(code));
  MARKET.detailQueue=job.catch(()=>null);MARKET.detailJobs.set(code,job);return job;
};
loadPerformance=async function(code){await loadPingzhong(code);return DS.perfMap[code]||null;};
loadAllPerformance=async function(codes){
  let success=0,fail=0;for(const code of codes){if(await loadPerformance(code))success++;else fail++;}
  return {success,fail};
};
function signature(){return [STATE.l1,STATE.l2,STATE.l3,STATE.search,STATE.favOnly,STATE.showAllShares,STATE.sortKey,STATE.sortAsc].join('|');}
function currentPageProducts(){
  const key=signature();if(key!==MARKET.signature){MARKET.signature=key;MARKET.page=1;}
  const all=sortedProducts(filteredProducts()),pages=Math.max(1,Math.ceil(all.length/MARKET.size));
  MARKET.page=Math.min(Math.max(1,MARKET.page),pages);
  const list=all.slice((MARKET.page-1)*MARKET.size,MARKET.page*MARKET.size);
  MARKET.lastVisible=list.map(p=>p.code);
  let control=document.getElementById('pageControls');
  if(!control){control=document.createElement('div');control.id='pageControls';control.className='page-controls';document.querySelector('.panel-table').appendChild(control);}
  control.innerHTML='<span>共 '+all.length.toLocaleString('zh-CN')+' 只 · 第 '+MARKET.page+' / '+pages+' 页</span>'+
    '<div class="page-actions"><label>每页 <select id="pageSize" aria-label="每页显示数量">'+[25,50,100].map(n=>'<option '+(n===MARKET.size?'selected':'')+'>'+n+'</option>').join('')+'</select></label>'+
    '<button id="previousPage" '+(MARKET.page===1?'disabled':'')+'>上一页</button><button id="nextPage" '+(MARKET.page===pages?'disabled':'')+'>下一页</button></div>';
  control.querySelector('#previousPage').onclick=()=>{MARKET.page--;renderTable();};
  control.querySelector('#nextPage').onclick=()=>{MARKET.page++;renderTable();};
  control.querySelector('#pageSize').onchange=e=>{MARKET.size=+e.target.value;MARKET.page=1;renderTable();};
  return list;
}
const referenceRenderTable=renderTable;
renderTable=function(){referenceRenderTable();if(MARKET.lazyReady&&!MARKET.busy)refreshVisible();};
renderKpi=function(){
  const list=filteredProducts(),seen=new Set(),families=[];
  for(const p of list){const key=familyKey(p);if(!seen.has(key)){seen.add(key);families.push(p);}}
  const marketTotal=SNAP.meta.marketTotal||{},total=finite(marketTotal.totalTrillionYuan);
  const knownCompanies=list.filter(p=>p.companyId),companies=new Set(knownCompanies.map(p=>p.companyId));
  const returns=list.map(p=>(DS.perfMap[p.code]||{}).y1).filter(v=>finite(v)!=null);
  const loaded=list.filter(p=>finite((DS.perfMap[p.code]||{}).m1)!=null).length;
  const text=(id,value)=>{const el=document.getElementById(id);if(el)el.textContent=value;};
  text('kpiCompanies',companies.size?companies.size.toLocaleString('zh-CN'):'--');
  text('kpiCompaniesSub','公司归属已核验 '+knownCompanies.length.toLocaleString('zh-CN')+' / '+list.length.toLocaleString('zh-CN')+' 只展示产品');
  text('kpiScale',total!=null?total.toLocaleString('zh-CN',{maximumFractionDigits:2,minimumFractionDigits:2}):'待更新');
  text('kpiScaleUnit','万亿元');
  const totalSub=document.getElementById('kpiScaleSub');
  if(totalSub){
    const source=marketTotal.sourceName||'中国证券投资基金业协会';
    const url=/^https:\/\//.test(marketTotal.sourceUrl||'')?marketTotal.sourceUrl:null;
    totalSub.innerHTML=total!=null?'截至 '+htmlText(marketTotal.asOf)+' · '+(url&&!snapshotMode()?'<a href="'+escapeHtml(url)+'" target="_blank" rel="noopener noreferrer" style="color:inherit;text-decoration:underline">'+htmlText(source)+'</a>':htmlText(source))+'<br>全市场公募基金净资产 · 不随筛选变化':'等待核验最新官方月报';
  }
  text('kpiCount',list.length.toLocaleString('zh-CN'));
  text('kpiCountSub',(STATE.showAllShares?'按份额代码计数':'按基金家族去重')+' · 当前筛选结果');
  text('kpiSharpe',returns.length?fmt.signed(returns.reduce((a,b)=>a+b,0)/returns.length,2)+'%':'--');
  text('kpiSharpeSub','等权平均 · 已有近一年收益 '+returns.length+' / '+list.length+' 只');
  text('kpiHealth',list.length?Math.round(loaded/list.length*100):0);
  text('kpiHealthSub','近期业绩覆盖 '+loaded.toLocaleString('zh-CN')+' / '+list.length.toLocaleString('zh-CN')+' 只');
};
updateTableHint=function(){
  const list=filteredProducts(),dates=list.map(p=>(DS.perfMap[p.code]||{}).jzrq).filter(Boolean).sort();
  const el=document.getElementById('tableHint');if(!el)return;
  el.textContent=(dates.length?'净值日期 '+dates[0]+(dates[0]!==dates.at(-1)?'～'+dates.at(-1):'')+' · ':'')+(STATE.sortKey==='w1'?'非货币按近一周、货币按七日年化分组排序 · ':'')+'点击表头排序 · 点击行查看详情';
};
const referenceRenderBubble=renderBubble;
renderBubble=function(){referenceRenderBubble();
  const list=filteredProducts().filter(p=>!isMoneyFund(p.code));
  const count=list.filter(p=>finite(getPerf(p).mdd)!=null&&finite(getPerf(p).y1)!=null).length;
  document.getElementById('matrixCoverage').textContent=count.toLocaleString('zh-CN')+' / '+list.length.toLocaleString('zh-CN')+' 只具备历史回撤及一年收益';
  const original=bubbleChart.getOption().tooltip[0].formatter;
  if(typeof original==='function')bubbleChart.setOption({tooltip:{formatter:params=>{
    const pf=DS.perfMap[params.value&&params.value[3]]||{};
    return original(params)+'<div style="font-size:10px;opacity:.75;margin-top:6px">回撤区间 '+htmlText(pf.historyStart)+' ～ '+htmlText(pf.mddAsOf)+'</div>';
  }}});
};
const referenceRenderTree=renderTree;
renderTree=function(){
  referenceRenderTree();
  const unique=new Map(filteredProducts().map(p=>[familyKey(p),p]));
  const covered=[...unique.values()].filter(p=>(familyScale(p)||0)>0).length;
  const countMode=unique.size>0&&covered/unique.size<.4;
  const panel=document.getElementById('chartTree').closest('.panel');
  panel.querySelector('.panel-title').textContent=countMode?'投资类型 · 三级数量分布':'投资类型 · 三级规模分布';
  panel.querySelector('.panel-hint').textContent=countMode?'块大小 = 基金家族数量 · 规模覆盖 '+covered+' / '+unique.size+'，当前按数量展示 · 点击下钻筛选':'块大小 = 已披露家族规模(亿) · 顶栏显示只数 · 点击下钻筛选';
};
findInternalAlternatives=function(p,max=3){
  const theme=detectTheme(p);
  return PRODUCTS.filter(q=>q.isPrimary&&familyKey(q)!==familyKey(p)&&q.l1===p.l1&&q.l2===p.l2)
    .map(q=>{const scale=familyScale(q),own=familyScale(p);let score=q.l3===p.l3?40:0;
      if(theme&&detectTheme(q)&&themesOverlap(theme,detectTheme(q)))score+=40;
      if(scale!=null&&own>0)score+=Math.max(0,20-Math.abs(Math.log((scale+.01)/(own+.01)))*6);
      return {q,score};}).sort((a,b)=>b.score-a.score||a.q.code.localeCompare(b.q.code)).slice(0,max)
    .map(({q})=>({...q,_altReason:'同投资类型 · '+q.l2+' / '+q.l3+(q.company?' · '+q.company:'')}));
};
tabCompetitorHtml=function(p){
  return '<div class="dr-section"><div class="dr-section-title">全市场同类产品推荐</div>'+
    '<div class="dr-desc">按投资类型、三级细分、名称主题及可得规模匹配。申购状态与具体投资策略见各基金披露。</div>'+
    '<div class="alt-list">'+findInternalAlternatives(p,3).map(q=>'<div class="alt-card" data-jump="'+q.code+'"><div class="alt-name">'+htmlText(q.name)+'</div><div class="alt-meta">'+q.code+' · '+htmlText(q.company)+' · '+htmlText(q.status.label)+'</div><div class="alt-reason">'+htmlText(q._altReason)+'</div></div>').join('')+'</div></div>'+
    '<div class="dr-section"><div class="dr-section-title">同类产品数据对比</div><div id="rivalArea" data-code="'+p.code+'"></div><div id="rivalCompareChart" style="height:280px;display:none"></div><div id="rivalRadarChart" style="height:260px;display:none"></div></div>';
};
findMarketCompetitors=async(p,n)=>findInternalAlternatives(p,n);
renderRivalArea=function(p){
  const el=document.getElementById('rivalArea');if(!el)return;
  const peers=findInternalAlternatives(p,3),rows=[p,...peers];
  if(!peers.length){el.textContent='公开目录中未找到同策略候选产品。';return;}
  const metric=(q,key)=>{const v=key==='scale'?familyScale(q):finite((DS.perfMap[q.code]||{})[key]);return v==null?'--':v.toFixed(2)+(key==='scale'?'':'%');};
  el.innerHTML='<div style="overflow-x:auto"><table style="width:100%;font-size:12px;border-collapse:collapse"><thead><tr><th style="text-align:left">指标</th>'+rows.map(q=>'<th style="min-width:100px;padding:8px">'+htmlText(q.name)+'<br><small style="color:var(--text-3)">'+q.code+'</small></th>').join('')+'</tr></thead><tbody>'+
    [['规模（亿）','scale'],['近一月','m1'],['近一年','y1'],['今年以来','ytd'],['历史最大回撤','mdd']].map(([label,key])=>'<tr><td style="padding:10px 4px;border-top:1px solid var(--border-soft)">'+label+'</td>'+rows.map(q=>'<td style="text-align:center;border-top:1px solid var(--border-soft)">'+metric(q,key)+'</td>').join('')+'</tr>').join('')+'</tbody></table></div>';
  const chart=document.getElementById('rivalCompareChart');chart.style.display='block';
  if(compareChart)compareChart.dispose();compareChart=echarts.init(chart);const T=ct();
  compareChart.setOption({backgroundColor:'transparent',tooltip:{trigger:'axis'},legend:{textStyle:{color:T.legend}},
    grid:{left:45,right:18,bottom:55,top:35},xAxis:{type:'category',data:rows.map(q=>q.code),axisLabel:{color:T.label}},
    yAxis:{type:'value',name:'收益率 %',nameTextStyle:{color:T.label},axisLabel:{color:T.label},splitLine:{lineStyle:{color:T.split}}},
    series:[['近一月','m1'],['近一年','y1']].map(([name,key])=>({name,type:'bar',data:rows.map(q=>finite((DS.perfMap[q.code]||{})[key]))}))});
};
const referenceTabOverview=tabOverviewHtml;
tabOverviewHtml=function(p){
  let text=referenceTabOverview(p);
  text=text.replace(/ · 任职年限 0 年/g,'').replace(/<div class="dr-mgr-mw">代表作：-<\/div>/g,'');
  text=text.replace(/单位净值 <b style="color:var\(--text-2\)">1\.0000<\/b>（货币基金恒定）/g,'货币基金收益指标');
  text=text.replace(/历史净值序列/g,'历史单位净值序列').replace(/昨日/g,'最新日表现');
  if(isMoneyFund(p.code))text=text.replace(/近期净值走势/g,'每万份收益走势（元）').replace(/历史单位净值序列/g,'历史每万份收益序列');
  const pf=DS.perfMap[p.code]||{};
  return '<div class="dr-desc" style="padding:0 0 12px">管理人：'+htmlText(p.company)+' · 数据日期：'+htmlText(pf.jzrq)+'<br>规模披露：'+htmlText(pf.scaleDate)+' · 回撤序列截至：'+htmlText(pf.mddAsOf)+'</div>'+text;
};
renderMiniChart=async function(p){
  const raw=await loadPingzhong(p.code);
  if(STATE.selectedCode!==p.code)return;
  const el=document.getElementById('drawerMiniChart');if(!el)return;
  if(miniChart){miniChart.dispose();miniChart=null;}
  const points=isMoneyFund(p.code)?(raw&&Array.isArray(raw.Data_millionCopiesIncome)?raw.Data_millionCopiesIncome.filter(x=>finite(x[1])!=null).slice(-120).map(x=>({x:x[0],y:Number(x[1])})):[]):
    (raw&&Array.isArray(raw.Data_netWorthTrend)?raw.Data_netWorthTrend.filter(x=>finite(x.y)!=null).slice(-120):[]);
  if(!points.length){el.innerHTML='<div style="padding:35px 0;color:var(--text-3)">'+(snapshotMode()?'本内网快照未内置该产品的历史曲线。':'暂无可用历史净值；联网后可点击刷新数据。')+'</div>';return;}
  miniChart=echarts.init(el);const T=ct(),color=points.at(-1).y>=points[0].y?'#FF5C5C':'#00C853';
  miniChart.setOption({backgroundColor:'transparent',tooltip:{trigger:'axis',textStyle:{color:T.tipText},backgroundColor:T.tipBg,borderColor:T.tipBorder},
    grid:{left:45,right:15,top:12,bottom:28},xAxis:{type:'category',data:points.map(x=>new Date(x.x).toISOString().slice(0,10)),axisLabel:{color:T.label,fontSize:10}},
    yAxis:{type:'value',scale:true,axisLabel:{color:T.label,fontSize:10},splitLine:{lineStyle:{color:T.split}}},
    series:[{type:'line',symbol:'none',data:points.map(x=>x.y),lineStyle:{color,width:2},areaStyle:{color:color+'18'}}]});
  const start=document.getElementById('miniNavStart'),end=document.getElementById('miniNavEnd');
  if(start)start.textContent='起点：'+Number(points[0].y).toFixed(4);if(end)end.textContent='当前：'+Number(points.at(-1).y).toFixed(4);
};
const referenceOpenDrawer=openDrawer;
openDrawer=function(code){
  referenceOpenDrawer(code);
  loadPerformance(code).then(()=>{
    if(STATE.selectedCode!==code)return;const p=MARKET.byCode.get(code);
    if(STATE.activeTab==='overview'){const pane=document.querySelector('[data-pane="overview"]');if(pane){pane.innerHTML=tabOverviewHtml(p);renderMiniChart(p);}}
    renderKpi();renderBubble();renderTree();renderTable();updateSourceUI();
  });
};
function applySnapshotModeUI(){
  if(!snapshotMode())return;
  const refresh=document.getElementById('refreshBtn');if(refresh){refresh.hidden=true;refresh.disabled=true;refresh.onclick=null;}
  const source=document.getElementById('sourceUpdatePolicy');if(source)source.textContent='本页为内网快照模式，使用随附公开来源数据；打开和使用时无需连接外部数据接口。';
  const cache=document.getElementById('cachePolicy');if(cache)cache.textContent='固定展示随附快照，不读取已有在线数据缓存。各字段保留自身披露日期及缺失原因；搜索、筛选、排序和 CSV 导出均可使用。';
  for(const [key,label]of [['ytd',currentYear()+'年以来(%)'],['ytdMdd',currentYear()+'年最大回撤(%)']]){
    const th=document.querySelector('#ptable th[data-sort="'+key+'"]');if(th)th.textContent=label;
  }
}
const referenceRenderTicker=renderTicker;
renderTicker=function(){
  referenceRenderTicker();
  if(snapshotMode()){
    const tail=document.getElementById('tickerTail');if(tail){tail.textContent='内网快照未内置指数行情';tail.classList.remove('warn','fail');}
  }
};
function updateSourceUI(){
  const text=(id,value)=>{const el=document.getElementById(id);if(el)el.textContent=value;};
  text('dsModeLabel',snapshotMode()?'内网快照':'动态数据');text('dsRefreshLabel',snapshotMode()?'快照日期':'动态刷新');
  text('poolSource',MARKET.sourceMode+(MARKET.snapshotIssue?' · 快照加载不完整':''));text('poolUpdated',localStamp(MARKET.updatedAt));
  text('poolCounts',PRODUCTS.length.toLocaleString('zh-CN')+' 份额 · '+FAMILY_MEMBERS.size.toLocaleString('zh-CN')+' 家族');
  const loaded=PRODUCTS.filter(p=>finite((DS.perfMap[p.code]||{}).m1)!=null).length;
  text('dsStatus',(MARKET.busy?'更新中 · ':'')+(MARKET.returnProgress?'批量业绩 '+MARKET.returnProgress.done+' / '+MARKET.returnProgress.total+' · ':'')+(MARKET.detailProgress?'当前页详情 '+MARKET.detailProgress.done+' / '+MARKET.detailProgress.total+' · ':'')+'近期业绩 '+loaded.toLocaleString('zh-CN')+' / '+PRODUCTS.length.toLocaleString('zh-CN'));
  text('dsRefresh',snapshotMode()?localStamp(SNAP.meta.updatedAt):MARKET.refreshTime?localStamp(MARKET.refreshTime):'随附快照 '+localStamp(SNAP.meta.updatedAt));
  const dot=document.getElementById('dsDot');if(dot)dot.style.background=MARKET.busy||healthFailures().length?'var(--gold)':'var(--green)';
  const note=document.getElementById('offlineNote');
  if(note){
    note.textContent=MARKET.snapshotIssue||(snapshotMode()?'内网快照模式 · 数据截至 '+localStamp(SNAP.meta.updatedAt)+' · 搜索、筛选及 CSV 导出可用。':!canConnect()?'当前离线：显示随附快照及最近成功缓存，数据日期见统计和表格。':MARKET.failures.length?'部分接口未更新，保留已有数据。详情见数据健康面板。':'');
    note.style.color=MARKET.snapshotIssue?'#FFB85C':'';note.style.border=MARKET.snapshotIssue?'1px solid #FFB85C':'';
    note.style.fontWeight=MARKET.snapshotIssue?'600':'';note.setAttribute('role',MARKET.snapshotIssue?'alert':'status');
    if(MARKET.snapshotIssue){const retry=document.createElement('button');retry.textContent='重新加载页面';retry.style.cssText='margin-left:12px;padding:4px 10px;border:1px solid currentColor;border-radius:5px;background:transparent;color:inherit;cursor:pointer';retry.onclick=()=>location.reload();note.appendChild(retry);}
  }
};
function fundCsvRecords(list){
  const header=['基金代码','产品名称','基金公司','基金经理','一级类型','二级类型','三级细分','产品形态','规模视图',
    '已披露规模(亿元)','净值日期','份额规模披露日期','最新日增长率(%)','近一周(%)',
    '每万份收益(元)','七日年化(%)','近一月(%)','近一年(%)',snapshotMode()?currentYear()+'年以来(%)':'今年以来(%)',snapshotMode()?currentYear()+'年最大回撤(%)':'今年最大回撤(%)','历史最大回撤(%)','回撤起点','回撤终点','自选','成立日期（当前代码）'];
  const rows=list.map(p=>{const pf=DS.perfMap[p.code]||{},money=isMoneyFund(p.code);
    return [p.code,p.name,p.company,pf.manager||p.manager,p.l1,p.l2,p.l3,p.fundSubtype,STATE.showAllShares?'当前份额':'家族已披露份额合计',getPerf(p).scale,
      pf.jzrq,pf.scaleDate,money?null:finite(pf.d1),money?null:finite(pf.w1),money?finite(pf.wfsy):null,money?finite(pf.qrnh):null,
      finite(pf.m1),finite(pf.y1),finite(pf.ytd),money?null:finite(pf.ytdMdd),money?null:finite(pf.mdd),pf.historyStart,pf.mddAsOf,isFav(p.code)?'是':'否',getInceptionDate(p)];});
  return [header,...rows];
}
exportCsv=function(){
  const list=sortedProducts(filteredProducts());if(!list.length){showToast('当前没有可导出的产品。','info');return;}
  const records=fundCsvRecords(list);
  const escape=value=>{const text=value==null||value==='-'?'':String(value);return /[",\r\n]/.test(text)?'"'+text.replace(/"/g,'""')+'"':text;};
  const csv='\uFEFF'+records.map(row=>row.map(escape).join(',')).join('\r\n');
  const blob=new Blob([csv],{type:'text/csv;charset=utf-8'}),url=URL.createObjectURL(blob),link=document.createElement('a');
  link.href=url;link.download='公募基金筛选结果_'+new Date().toLocaleDateString('sv-SE',{timeZone:'Asia/Shanghai'})+'.csv';
  document.body.appendChild(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);showToast('已导出 '+list.length+' 只产品，包含逐基金数据日期。','info');
};
updateProductPoolUI=updateSourceUI;
updateDataSourceUI=updateSourceUI;
updateHealthBadge=function(){const badge=document.getElementById('healthBadge'),count=healthFailures().length;badge.style.display=count?'inline-block':'none';badge.textContent=String(count);};
function fieldCoverage(key){
  let available=0;const missing={};
  for(const p of PRODUCTS){
    const pf=DS.perfMap[p.code]||{},value=key==='inceptionDate'?getInceptionDate(p):key==='manager'?(pf.manager||p.manager):pf[key];
    if(hasField(value)){available++;continue;}
    const label=key==='inceptionDate'?inceptionInfo(p).label:missingFieldLabel(missingFieldInfo(p.code,key));missing[label]=(missing[label]||0)+1;
  }
  return {available,total:PRODUCTS.length,missing};
}
openHealthPanel=function(){
  const body=document.getElementById('healthBody'),all=PRODUCTS,total=SNAP.meta.marketTotal||{},collection=SNAP.meta.collection||{};
  const detailCount=all.filter(p=>(DS.perfMap[p.code]||{}).detailFetchedAt).length;
  const items=[['产品池来源',MARKET.sourceMode],['产品池时间',localStamp(MARKET.updatedAt)],
    ['份额代码总数',all.length],['基金家族数',FAMILY_MEMBERS.size],
    ['已核验管理人归属',all.filter(p=>p.companyId).length],['未知管理人归属',all.filter(p=>!p.companyId).length],
    ['已采集并处理产品详情',detailCount+' / '+all.length],
    ['已加载随附快照记录',MARKET.snapshotLoaded+' / '+(collection.directoryCount||all.length)],
    ['快照采集尝试 / 目录',collection.attempted!=null?collection.attempted+' / '+(collection.directoryCount||all.length):'--'],
    ['快照成功 / 部分 / 失败',collection.ok!=null?collection.ok+' / '+(collection.partial||0)+' / '+(collection.failed||0):'--'],
    ['已取得规模的家族',all.filter(p=>p.isPrimary&&familyScale(p)!=null).length],
    ['ETF本体 / 联接',countSubtype('ETF本体')+' / '+countSubtype('ETF联接')],
    ['REITs / FOF',countSubtype('REITs')+' / '+countSubtype('FOF')],
    ['本次详情成功 / 失败',MARKET.stats.detailOk+' / '+MARKET.stats.detailFail]];
  const fields=[['份额规模','scale'],['基金经理','manager'],['最新日增长率','d1'],['近一周（非货币）','w1'],['七日年化（货币）','qrnh'],['近一月','m1'],['近一年','y1'],['今年以来','ytd'],['今年最大回撤','ytdMdd'],['历史最大回撤','mdd'],['成立日期（代码）','inceptionDate']];
  body.innerHTML='<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">'+items.map(([label,value])=>'<div class="health-item" style="padding:10px;border:1px solid var(--border-soft);border-radius:8px"><small style="color:var(--text-3)">'+label+'</small><div>'+htmlText(value)+'</div></div>').join('')+'</div>'+
    '<div class="dr-section"><div class="dr-section-title">产品明细字段覆盖</div><table style="width:100%;font-size:12px;border-collapse:collapse"><thead><tr><th style="text-align:left">字段</th><th>已有值 / 份额数</th><th style="text-align:left">空值原因</th></tr></thead><tbody>'+fields.map(([label,key])=>{const c=fieldCoverage(key);return '<tr><td style="padding:9px 3px;border-top:1px solid var(--border-soft)">'+label+'</td><td style="text-align:center;border-top:1px solid var(--border-soft)">'+c.available+' / '+c.total+'</td><td style="border-top:1px solid var(--border-soft);color:var(--text-3)">'+(Object.entries(c.missing).map(([reason,n])=>reason+' '+n).join(' · ')||'已覆盖')+'</td></tr>';}).join('')+'</tbody></table></div>'+
    '<div class="dr-section"><div class="dr-section-title">统计口径</div><div class="dr-desc">全市场规模卡片取官方公募基金净资产月度汇总'+(finite(total.totalTrillionYuan)!=null?'，截至 '+htmlText(total.asOf)+' 为 '+Number(total.totalTrillionYuan).toFixed(2)+' 万亿元':'')+'，不随筛选变化。产品明细规模按份额代码计数；折叠时按家族汇总已取得的份额规模，展开时展示当前份额。家族内其他份额缺失时仅为部分合计，各份额披露日期可能不同。成立日期采用来源对当前代码披露的日期，后设份额按来源核验；折叠时展示代表代码日期，具体口径见日期悬浮说明。货币基金使用万份收益和七日年化，价格回撤标记不适用。回撤优先由公开日增长率连乘计算，缺失时使用源累计收益可得区间，数据日期见详情。采集处理覆盖表示逐产品处理完成，已有值覆盖见逐字段统计。未披露、历史不足、获取失败等原因分别保留，不填零。</div></div>'+
    '<div class="dr-section"><div class="dr-section-title">加载与接口状态</div>'+(healthFailures().length?healthFailures().map(x=>'<div class="flag-item warn">'+htmlText(x)+'</div>').join(''):'<div class="dr-desc">'+(snapshotMode()?'当前为内网快照模式，未发起外部数据请求；数据覆盖量见上方。':'本次已发出的请求暂无失败记录；数据覆盖量见上方。')+'</div>')+'</div>'+
    '<div class="dr-section"><div class="dr-section-title">随附快照</div><div class="dr-desc">'+htmlText(SNAP.meta.updatedAt)+' · 已处理详情 '+detailCount+' / '+all.length+' 份额；'+(SNAP.meta.historyCount||0)+' 只预存曲线。'+(snapshotMode()?'当前展示随附快照，不读取已有在线数据缓存，不向外部请求数据。搜索、筛选、排序和 CSV 导出可直接使用；数据更新后需重新部署内网快照。':'联网打开时尝试更新批量业绩，来源限制跨站访问时保留快照；当前页详情独立补取，切换页面时补取整页所需详情。点击刷新可重新请求，全市场完整更新可运行本地全量更新脚本。页面关闭后不在后台自动更新。')+'</div>'+
      ((SNAP.meta.errors||[]).length?'<div class="dr-desc" style="margin-top:10px">快照来源提示 '+SNAP.meta.errors.length+' 条（展示前20条）：'+SNAP.meta.errors.slice(0,20).map(x=>htmlText(x.source+'：'+x.error)).join('<br>')+'</div>':'')+'</div>';
  document.getElementById('healthPanel').style.transform='translateX(0)';document.getElementById('healthMask').classList.add('show');
};
function mergeReturnRows(rows){
  let n=0;for(const row of rows||[]){const f=String(row).split(','),p=MARKET.byCode.get(f[0]);if(!p||f.length<15)continue;
    const rec={jzrq:f[3],fieldStatus:{}};for(const [key,index]of [['d1',6],['w1',7],['m1',8],['m3',9],['m6',10],['y1',11],['ytd',14],['dwjz',4]])rec[key]=finite(f[index]);
    if(isMoneyFund(p.code)){
      rec.wfsy=finite(f[6]);rec.qrnh=finite(f[7]);
      for(const key of ['d1','w1','dwjz','mdd','ytdMdd'])rec.fieldStatus[key]={status:'not_applicable',reason:'not_applicable_money'};
    }
    DS.perfMap[p.code]=mergePerf(DS.perfMap[p.code]||{},rec,p);n++;
  }return n;
}
async function refreshDirectory(){
  if(snapshotMode())return;
  await jsonpLoad('https://fund.eastmoney.com/js/fundcode_search.js?v='+Date.now(),120000);
  const rows=window.r;if(!Array.isArray(rows)||rows.length<1000)throw new Error('返回目录为空或不完整');
  const funds=rows.filter(row=>Array.isArray(row)&&row.length>=4).map(row=>({...(MARKET.byCode.get(String(row[0]))||{}),code:String(row[0]),name:row[2],type:row[3],shareClass:shareClass(row[2])}));
  if(funds.length<PRODUCTS.length*.8)throw new Error('目录数量大幅减少，保留已有目录');
  setProductsFromPool(funds);MARKET.updatedAt=new Date().toISOString();MARKET.sourceMode='公开接口最新目录';
  try{delete window.r;}catch(_){};renderChips();renderSubChips();renderAll();
}
function validatePageCodes(rows,total,page,pageSize,expectedTotal,previousCode,codeOf,label){
  if(!Number.isInteger(total)||total<=0||!Array.isArray(rows)||!rows.length)throw new Error(label+'未返回有效记录或总数；已保留快照');
  if(expectedTotal!=null&&total!==expectedTotal)throw new Error(label+'翻页期间总数变化，未合并不完整结果');
  const expected=Math.min(pageSize,total-(page-1)*pageSize);
  if(rows.length!==expected)throw new Error(label+'第 '+page+' 页记录不完整，未合并结果');
  const codes=rows.map(codeOf);
  if(codes.some(code=>!/^\d{6}$/.test(code)))throw new Error(label+'返回无效基金代码');
  if(codes.some((code,i)=>i&&code<=codes[i-1])||(previousCode&&codes[0]<=previousCode))throw new Error(label+'基金代码排序不稳定或页间重复，未合并结果');
  return codes;
}
async function readRankingPage(page,pageSize,start,end,expectedTotal,previousCode){
  let lastError;
  for(let attempt=0;attempt<2;attempt++){
    window.rankData=undefined;
    try{
      const url='https://fund.eastmoney.com/data/rankhandler.aspx?op=ph&dt=kf&ft=all&rs=&gs=0&sc=dm&st=asc&sd='+start+'&ed='+end+'&qdii=&tabSubtype=,,,,,&pi='+page+'&pn='+pageSize+'&dx=1&v='+Date.now()+'&attempt='+attempt;
      await jsonpLoad(url,25000);const rank=window.rankData;
      if(!rank||!Array.isArray(rank.datas)||!rank.datas.length)throw new Error('批量业绩来源未返回数据，可能限制跨站访问；已保留快照，可使用本地全量更新脚本');
      if(rank.datas.some(row=>typeof row!=='string'||row.split(',').length<17))throw new Error('批量业绩返回记录格式不完整');
      const total=Number(rank.allRecords),codes=validatePageCodes(rank.datas,total,page,pageSize,expectedTotal,previousCode,row=>row.split(',')[0],'批量业绩');
      return {rows:rank.datas.slice(),total,lastCode:codes.at(-1)};
    }catch(error){lastError=error;}
    finally{window.rankData=undefined;}
  }
  throw lastError;
}
async function refreshReturns(){
  if(snapshotMode())return;
  if(MARKET.returnJob)return MARKET.returnJob;
  MARKET.returnJob=(async()=>{
    const end=new Date(),start=new Date(end.getTime()-366*86400000),fmt=date=>date.toLocaleDateString('sv-SE',{timeZone:'Asia/Shanghai'}),pageSize=200;
    let total=null,lastCode='';const rows=[];
    // rankData is a shared script global: every page and retry is sequential.
    for(let page=1;page<=Math.ceil((total||pageSize)/pageSize);page++){
      const result=await readRankingPage(page,pageSize,fmt(start),fmt(end),total,lastCode);
      total=result.total;lastCode=result.lastCode;rows.push(...result.rows);
      MARKET.returnProgress={done:rows.length,total};updateSourceUI();
    }
    if(rows.length!==total||new Set(rows.map(row=>row.split(',')[0])).size!==total)throw new Error('批量业绩完整性校验失败，已保留快照');
    mergeReturnRows(rows);renderAll();scheduleCache();
  })().finally(()=>{MARKET.returnJob=null;MARKET.returnProgress=null;updateSourceUI();});
  return MARKET.returnJob;
}
async function readMoneyPage(page,pageSize,expectedTotal,previousCode){
  let lastError;
  for(let attempt=0;attempt<2;attempt++){
    const callback='__marketMoney_'+(++MARKET.moneyNonce);let result=null;
    window[callback]=data=>{result=data;};
    try{
      await jsonpLoad('https://api.fund.eastmoney.com/FundRank/GetHbRankList?intCompany=0&MinsgType=&IsSale=0&strSortCol=FCODE&orderType=asc&pageIndex='+page+'&pageSize='+pageSize+'&callback='+callback,25000);
      if(result&&Number(result.ErrCode)===-999)throw new Error('货币基金来源限制跨站访问；已保留快照，可使用本地全量更新脚本');
      if(!result||Number(result.ErrCode)!==0||!Array.isArray(result.Data))throw new Error('货币基金来源未返回数据，可能限制跨站访问；已保留快照，可使用本地全量更新脚本');
      const total=Number(result.TotalCount),codes=validatePageCodes(result.Data,total,page,pageSize,expectedTotal,previousCode,row=>String(row.FCODE||''),'货币基金业绩');
      return {rows:result.Data.slice(),total,lastCode:codes.at(-1)};
    }catch(error){lastError=error;}
    finally{delete window[callback];}
  }
  throw lastError;
}
async function refreshMoneyReturns(){
  if(snapshotMode())return;
  if(MARKET.moneyJob)return MARKET.moneyJob;
  MARKET.moneyJob=(async()=>{
    const pageSize=100,rows=[];let total=null,lastCode='';
    for(let page=1;page<=Math.ceil((total||pageSize)/pageSize);page++){
      const result=await readMoneyPage(page,pageSize,total,lastCode);
      total=result.total;lastCode=result.lastCode;rows.push(...result.rows);
    }
    if(rows.length!==total||new Set(rows.map(row=>row.FCODE)).size!==total)throw new Error('货币基金完整性校验失败，已保留快照');
    for(const row of rows){
      const p=MARKET.byCode.get(row.FCODE);if(!p)continue;
      const rec={jzrq:row.FSRQ,wfsy:finite(row.DWJZ),qrnh:finite(row.LJJZ),
        m1:finite(row.SYL_Y),m3:finite(row.SYL_3Y),m6:finite(row.SYL_6Y),y1:finite(row.SYL_1N),ytd:finite(row.SYL_JN),fieldStatus:{}};
      for(const key of ['d1','w1','mdd','ytdMdd','dwjz'])rec.fieldStatus[key]={status:'not_applicable',reason:'not_applicable_money'};
      DS.perfMap[p.code]=mergePerf(DS.perfMap[p.code]||{},rec,p);
    }
    renderAll();scheduleCache();
  })().finally(()=>{MARKET.moneyJob=null;});
  return MARKET.moneyJob;
}
function needsDetail(code){
  const pf=DS.perfMap[code]||{};
  return !pf.detailFetchedAt||dayText(pf.detailFetchedAt)!==dayText(Date.now())||
    Object.values(pf.fieldStatus||{}).some(s=>s&&['fetch_failed','source_unavailable'].includes(s.reason));
}
async function refreshVisible({force=false}={}){
  if(!canConnect())return;
  const codes=MARKET.lastVisible.slice(),key=codes.join(',');
  if(!force&&key===MARKET.visibleKey)return;
  MARKET.visibleKey=key;const run=++MARKET.visibleRun;
  const pending=codes.filter(code=>!MARKET.detailTried.has(code)&&(force||needsDetail(code)));
  MARKET.detailProgress=null;if(!pending.length){updateSourceUI();return;}
  MARKET.detailProgress={done:0,total:pending.length};updateSourceUI();
  // Vendor detail scripts share globals, so fetch the entire visible page serially.
  for(const code of pending){
    if(run!==MARKET.visibleRun||key!==MARKET.lastVisible.join(','))break;
    await loadPerformance(code);
    if(run!==MARKET.visibleRun)break;
    MARKET.detailProgress.done++;updateSourceUI();
  }
  if(run===MARKET.visibleRun){MARKET.detailProgress=null;renderAll();updateSourceUI();updateHealthBadge();scheduleCache();}
}
async function refreshMarket({forceDetails=true}={}){
  if(snapshotMode())return;
  if(MARKET.busy)return;if(!canConnect()){updateSourceUI();showToast('当前离线，保留随附快照与最近缓存。','info');return;}
  MARKET.busy=true;MARKET.failures=[];MARKET.detailTried.clear();MARKET.visibleKey='';MARKET.visibleRun++;MARKET.detailProgress=null;
  const button=document.getElementById('refreshBtn');button.disabled=true;updateSourceUI();
  const jobs=[['基金目录',refreshDirectory],['批量业绩',refreshReturns],['货币基金业绩',refreshMoneyReturns],['指数行情',async()=>{await loadIndexQuotes();renderTicker();}]];
  await Promise.all(jobs.map(async([label,fn])=>{try{await fn();}catch(e){reportFailure(label,e);}}));
  try{await refreshVisible({force:forceDetails});}catch(e){reportFailure('当前页详情',e);}
  MARKET.busy=false;MARKET.refreshTime=new Date().toISOString();button.disabled=false;
  updateSourceUI();updateHealthBadge();scheduleCache();refreshVisible();
}
kickoffRealtime=refreshVisible;kickoffFullRealtime=refreshVisible;kickoffFullPerf=()=>{};
applyRealtimeToProducts=function(){
  for(const [code,rt]of Object.entries(DS.realtimeMap)){
    const pf=DS.perfMap[code]||{};
    if(rt.jzrq&&(!pf.jzrq||rt.jzrq>=pf.jzrq)){
      DS.perfMap[code]=mergePerf(pf,{dwjz:finite(rt.dwjz),jzrq:rt.jzrq},MARKET.byCode.get(code));
    }
  }
  window.__refreshAfterPerf&&window.__refreshAfterPerf();
};
function detailDataDate(raw){
  if(!raw)return '';
  const nav=Array.isArray(raw.Data_netWorthTrend)?raw.Data_netWorthTrend:[];
  const money=Array.isArray(raw.Data_millionCopiesIncome)?raw.Data_millionCopiesIncome:[];
  const dates=[...nav.map(p=>finite(p.x)),...money.map(p=>finite(p[0]))].filter(p=>p!=null);
  return dates.length?dayText(Math.max(...dates)):'';
}
window.__startApp=async function(){
  checkSnapshotCompleteness();if(snapshotMode())MARKET.sourceMode='内网快照';
  setProductsFromPool(SNAP.funds);DS.perfMap={...(SNAP.perf||{})};DS.pingzhongCache={...(SNAP.details||{})};DS.realtimeMap={...(SNAP.realtime||{})};
  for(const [code,pf]of Object.entries(DS.perfMap))DS.perfMap[code]=enforceInceptionIntervals(sanitizeYear(pf),MARKET.byCode.get(code));
  for(const [code,raw]of Object.entries(DS.pingzhongCache))if(!(DS.perfMap[code]||{}).detailFetchedAt)applyDetail(code,{...raw,_fetchedAt:raw._fetchedAt||SNAP.meta.updatedAt});
  const cached=snapshotMode()?null:await Promise.race([readCache(),new Promise(resolve=>setTimeout(()=>resolve(null),1500))]);
  if(cached){
    const supplied=new Map(SNAP.funds.map(p=>[p.code,p]));
    if(cached.meta&&String(cached.meta.updatedAt)>String(MARKET.updatedAt)&&Array.isArray(cached.funds)){
      setProductsFromPool(cached.funds.map(p=>mergeCachedProduct(supplied.get(p.code)||{},p)));
      MARKET.updatedAt=cached.meta.updatedAt;MARKET.sourceMode='最近成功缓存';
    }
    for(const [code,pf]of Object.entries(cached.perf||{}))DS.perfMap[code]=mergeCachedPerf(DS.perfMap[code]||{},pf,supplied.get(code)||MARKET.byCode.get(code));
    for(const [code,raw]of Object.entries(cached.details||{})){
      const old=DS.pingzhongCache[code],stamp=detailDataDate(raw),previous=detailDataDate(old);
      if(!old||stamp&&stamp>=previous)DS.pingzhongCache[code]=raw;
    }
    for(const [code,rt]of Object.entries(cached.realtime||{}))if(!(DS.realtimeMap[code]||{}).jzrq||rt.jzrq>=(DS.realtimeMap[code]||{}).jzrq)DS.realtimeMap[code]=rt;
  }
  const note=document.createElement('div');note.id='offlineNote';note.className='offline-note';document.querySelector('.kpi-grid').before(note);
  bindThemeToggle();renderTopbarDate();renderChips();renderSubChips();bindSubChipsEvents();
  bubbleChart=echarts.init(document.getElementById('chartBubble'));treeChart=echarts.init(document.getElementById('chartTree'));
  bindTableEvents();bindToolbar();bindDrawerEvents();
  document.getElementById('drawerClose').onclick=closeDrawer;document.getElementById('drawerMask').onclick=closeDrawer;
  document.getElementById('refreshBtn').title='更新公开目录、业绩与当前页详情；失败时保留已有数据';document.getElementById('refreshBtn').onclick=()=>refreshMarket();
  document.getElementById('healthBtn').onclick=openHealthPanel;document.getElementById('healthClose').onclick=closeHealthPanel;document.getElementById('healthMask').onclick=closeHealthPanel;
  const shares=document.getElementById('toggleShares');shares.checked=false;shares.onchange=()=>{STATE.showAllShares=shares.checked;renderAll();};
  document.addEventListener('keydown',event=>{if(event.key==='Escape'){closeHealthPanel();closeDrawer();}});
  window.addEventListener('resize',()=>[bubbleChart,treeChart,miniChart,compareChart].forEach(chart=>chart&&chart.resize()));
  window.addEventListener('offline',updateSourceUI);window.addEventListener('online',updateSourceUI);
  window.__refreshAfterPerf=()=>{renderTable();renderKpi();renderBubble();renderTree();updateSourceUI();};
  applySnapshotModeUI();
  document.getElementById('loadingOverlay').classList.add('hidden');renderAll();updateSourceUI();updateHealthBadge();renderTicker();
  if(MARKET.snapshotIssue)showToast('快照加载不完整，请重新加载页面。已有数据仍可查看。','warn');
  if(!PRODUCTS.length)showToast(snapshotMode()?'随附产品目录为空，请重新生成并部署完整快照。':'随附产品目录为空，请联网后刷新。','warn');
  MARKET.lazyReady=!snapshotMode();if(!snapshotMode())refreshMarket({forceDetails:false});
};
window.__marketReady=true;window.__tryBoot();
