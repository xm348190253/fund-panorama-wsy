const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'..');
const html=fs.readFileSync(path.join(root,'dist/index.html'),'utf8');
const main=[...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)].map(x=>x[1]).find(x=>x.includes('const CONFIG ='));
const context={console,setTimeout,clearTimeout,navigator:{onLine:false},document:{documentElement:{dataset:{theme:'dark'}}},
  addEventListener:()=>{},__tryBoot:()=>{},localStorage:{getItem:()=>null,setItem:()=>{}}};
context.window=context;vm.createContext(context);
vm.runInContext(fs.readFileSync(path.join(root,'dist/snapshot.js'),'utf8'),context);
for(const part of [...html.matchAll(/<script src="(snapshot-perf-\d+\.js)"><\/script>/g)].map(m=>m[1]))
  vm.runInContext(fs.readFileSync(path.join(root,'dist',part),'utf8'),context);
vm.runInContext(main,context);vm.runInContext(fs.readFileSync(path.join(root,'dist/market.js'),'utf8'),context);
const report=vm.runInContext(`
  setProductsFromPool(SNAP.funds);DS.perfMap={...SNAP.perf};
  for(const [code,raw]of Object.entries(SNAP.details))if(!(DS.perfMap[code]||{}).detailFetchedAt)applyDetail(code,raw);
  ({codes:PRODUCTS.length,families:FAMILY_MEMBERS.size,primary:PRODUCTS.filter(p=>p.isPrimary).length,
    companyMapped:PRODUCTS.filter(p=>p.companyId).length,companies:new Set(PRODUCTS.filter(p=>p.companyId).map(p=>p.companyId)).size,
    completeScaleFamilies:[...FAMILY_MEMBERS.values()].filter(members=>members.length>1&&
      members.every(p=>Number.isFinite(DS.perfMap[p.code]?.scale))).map(members=>({
        actual:familyScale(members[0]),members:members.map(p=>({code:p.code,
          scale:DS.perfMap[p.code].scale,source:DS.perfMap[p.code].scaleSourceCode||p.code,
          date:String(DS.perfMap[p.code].scaleDate||'')}))})),perf:DS.perfMap,
    riskCount:PRODUCTS.filter(p=>finite((DS.perfMap[p.code]||{}).mdd)!=null).length,
    types:[...new Set(PRODUCTS.map(p=>p.l1))],
    badRisk:PRODUCTS.filter(p=>{const v=(DS.perfMap[p.code]||{}).mdd;return v!=null&&(!Number.isFinite(v)||v>0||v<-100);}).length,
    meta:SNAP.meta})
`,context);
assert.equal(report.codes,report.meta.directoryCount);assert.equal(report.families,report.meta.fundFamilyCount);
assert.equal(report.primary,report.families);assert.equal(report.companyMapped,report.meta.companyMappedCount);
assert.equal(report.companies,report.meta.companyCount);assert.equal(report.badRisk,0);
for(const family of report.completeScaleFamilies){
  // Redirect aliases share one source asset value; use its latest disclosure once.
  const ordered=[...family.members].sort((a,b)=>b.date.localeCompare(a.date)),seen=new Set();
  const expected=ordered.reduce((sum,member)=>{
    if(seen.has(member.source))return sum;
    seen.add(member.source);return sum+member.scale;
  },0);
  assert(Number.isFinite(family.actual));
  assert(Math.abs(family.actual-expected)<1e-8,
    'Family must aggregate distinct source assets: '+family.members.map(p=>p.code).join(','));
}
assert.equal(Object.keys(report.perf).length,report.codes);
assert.equal(report.meta.collection.attempted,report.codes);
assert(report.meta.marketTotal.totalYiYuan>0);
assert(Math.abs(report.meta.marketTotal.totalYiYuan/10000-report.meta.marketTotal.preciseTrillionYuan)<1e-6);
for(const [field,count]of Object.entries(report.meta.coverage)){
  assert.equal(count.available+count.missing+count.notApplicable,report.codes,field);
  const actual=Object.values(report.perf).filter(p=>p[field]!=null&&p[field]!=='').length;
  assert.equal(actual,count.available,field+' availability');
}
for(const [code,pf]of Object.entries(report.perf)){
  for(const key of ['mdd','ytdMdd'])if(pf[key]!=null)assert(Number.isFinite(pf[key])&&pf[key]>=-100&&pf[key]<=0,code+':'+key);
  for(const key of ['ytd','ytdMdd'])if(pf[key]!=null){
    const state=pf.fieldStatus?.[key];
    const stamp=state&&Object.prototype.hasOwnProperty.call(state,'asOf')?state.asOf:
      key==='ytdMdd'?pf.ytdAsOf||pf.mddAsOf:pf.ytdAsOf||pf.jzrq;
    assert.equal(typeof stamp,'string',code+':'+key+' must have a known observation date');
    assert(/^\d{4}-\d{2}-\d{2}$/.test(stamp),code+':'+key+' observation date format');
    assert.equal(stamp.slice(0,4),report.meta.collection.asOf.slice(0,4),code+':'+key+' year');
  }
}
for(const file of fs.readdirSync(path.join(root,'dist')))assert(fs.statSync(path.join(root,'dist',file)).size<25*1024*1024,'oversized asset '+file);
for(const type of ['股票型','债券型','货币型','QDII','FOF','REITs'])assert(report.types.includes(type));
let hashes=0;
for(const source of report.meta.sources){
  const file=path.join(root,'source-cache',source.key+'.txt');
  if(fs.existsSync(file)){assert.equal(crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex'),source.sha256,source.key);hashes++;}
}
const standaloneScriptsParsed={};
for(const file of ['公募基金_本地离线版.html','公募基金_领导分享版.html']){
  const standalone=fs.readFileSync(path.join(root,file),'utf8');
  assert(!/<script\s+src=/i.test(standalone),file+' must not require an external script file');
  let scripts=0;for(const match of standalone.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)){
    new vm.Script(match[1],{filename:file+':inline-script-'+(++scripts)});
  }
  standaloneScriptsParsed[file]=scripts;
  if(file==='公募基金_领导分享版.html'){
    // Inspect markup outside scripts so vendor HTML strings are not page tags.
    const markup=standalone.replace(/<script(?:\s[^>]*)?>[\s\S]*?<\/script>/g,'');
    const body=markup.match(/^[ \t]*<body\b[^>]*>/m);
    assert(body,'sharing page must have an actual body tag');
    assert(/^\s*<div id="deliveryBanner" role="status">/.test(markup.slice(body.index+body[0].length)),
      'sharing banner must be the first element under the actual body');
    assert.equal([...standalone.matchAll(/<div id="deliveryBanner"(?=\s|>)/g)].length,1,'sharing banner must occur exactly once');
  }
}
console.log(JSON.stringify({status:'PASS',codes:report.codes,families:report.families,companyMapped:report.companyMapped,
  companies:report.companies,scaleFamiliesVerified:report.completeScaleFamilies.length,
  riskObservations:report.riskCount,sourceHashesVerified:hashes,standaloneScriptsParsed},null,2));
