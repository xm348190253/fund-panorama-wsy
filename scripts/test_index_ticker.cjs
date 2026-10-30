const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..'),html=fs.readFileSync(path.join(root,'dist/index.html'),'utf8');
const main=[...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)].map(m=>m[1]).find(s=>s.includes('const CONFIG ='));
const elements={tickerItems:{dataset:{},innerHTML:''},tickerTail:{textContent:'',classList:{add(){},remove(){}}}};
const context={console,Date,Map,Set,Promise,Math,Number,String,Object,Array,JSON,RegExp,setTimeout,clearTimeout,URL,assert,
 navigator:{onLine:false},localStorage:{getItem(){return null},setItem(){}},addEventListener(){},__tryBoot(){},
 document:{documentElement:{dataset:{theme:'dark'}},getElementById:id=>elements[id]}};
context.window=context;vm.createContext(context);vm.runInContext(main,context);
vm.runInContext(fs.readFileSync(path.join(root,'dist/market.js'),'utf8'),context);
vm.runInContext(`
enableTickerMarquee=()=>{};
window.__FUND_OFFLINE__=true;
window.__FUND_INDEX_SNAPSHOT__={collectedAt:'2026-10-30T17:55:00+08:00'};
DS.indexQuotes=[{name:'上证指数',market:'CN',val:100,pct:0,quoteDate:'2026-10-30',quoteTime:'15:00:00'},
{name:'标普500',market:'US',val:200,pct:-1,quoteDate:'2026-10-30',quoteTime:'04:00:00'},
{name:'测试<指数>',val:null,pct:null}];
renderTicker();
`,context);
assert.match(elements.tickerItems.innerHTML,/行情 2026-10-30 15:00:00 北京时间/);
assert.match(elements.tickerItems.innerHTML,/行情 2026-10-30 04:00:00 北京时间/);
assert.match(elements.tickerItems.innerHTML,/本次未取得行情/);
assert.match(elements.tickerItems.innerHTML,/0\.00%/);
assert.match(elements.tickerItems.innerHTML,/测试&lt;指数&gt;/);
assert.match(elements.tickerTail.textContent,/采集 2026-10-30 17:55:00 北京时间/);
assert.match(elements.tickerTail.textContent,/2\/3 个指数/);
vm.runInContext(`assert.equal(parseEastmoneyQuoteTime({f80:20261030,f86:1793347920}).quoteDate,null);`,context);
console.log('PASS: per-index Beijing quote times, collection time, missing data, zero change and escaped names');
