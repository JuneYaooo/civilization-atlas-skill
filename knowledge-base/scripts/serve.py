#!/usr/bin/env python3
"""Loopback-only, read-only historical knowledge explorer."""
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from urllib.parse import urlsplit,parse_qs,urlencode
from html import escape
import argparse,json
from query import ROOT,connect,search,detail,entities
CSS='''body{font:16px/1.65 system-ui,sans-serif;background:#f6f4ef;color:#26342d;margin:0}main{max-width:1140px;margin:42px auto;padding:0 24px}h1{font-size:34px;letter-spacing:-1px}h2{font-size:21px}a{color:#205a48}small,.muted{color:#68746d}form,.card{padding:20px;background:white;border:1px solid #dfe4dd;border-radius:10px;margin:16px 0}form{display:flex;flex-wrap:wrap;gap:12px;align-items:end}label{display:flex;flex-direction:column;font-size:13px}input,select,button{font:inherit;padding:8px;border:1px solid #b6c3b9;border-radius:5px;max-width:260px}button{background:#205a48;color:white;cursor:pointer}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#eef1ec;padding:16px;font-size:13px}nav{display:flex;gap:24px}table{width:100%;border-collapse:collapse}td,th{text-align:left;padding:9px;border-bottom:1px solid #ddd}.stats{display:flex;gap:22px;flex-wrap:wrap}.stats b{font-size:24px;display:block}.tag{font-size:12px;background:#e8eee8;padding:3px 7px;margin-right:6px}details{margin:14px 0}summary{cursor:pointer}'''
def esc(x):return escape(str(x if x is not None else '未标注'))
def page(title,body):return '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>'+esc(title)+'</title><style>'+CSS+'</style><main><nav><a href="/">知识检索</a><a href="/coverage">覆盖与缺口</a><a href="/entities">国家、政体与联盟</a></nav><h1>'+esc(title)+'</h1>'+body+'</main></html>'
def year(y):return '未标注' if y is None else ('公元前 '+str(-y) if y<0 else str(y))
def options(rows,current):return '<option value="">全部</option>'+''.join('<option value="'+esc(k)+'"'+(' selected' if k==current else '')+'>'+esc(v)+'</option>' for k,v in rows)
class Handler(BaseHTTPRequestHandler):
 def do_GET(self):
  url=urlsplit(self.path);params={k:v[0] for k,v in parse_qs(url.query).items()}
  try:
   if url.path in ('/api/search','/'):
    args={k:params.get(k,'') for k in ['q','source','topic','entity']}
    args.update({k:int(params[k]) for k in ['start','end','limit','offset'] if params.get(k)})
    data=search(**args)
    if url.path.startswith('/api/'):return self.send(data)
    with connect() as db:
     src=[(r['id'],r['title']) for r in db.execute('SELECT id,title FROM sources WHERE id IN (SELECT DISTINCT source_id FROM records)')]
     topics=[(r[0],r[0]) for r in db.execute('SELECT DISTINCT topic FROM records ORDER BY topic')]
    body='<p>按资料来源、主体和年代查找历史记录。点击条目查看原始字段、出处和定位。</p><form>'
    for key,label in [('q','关键词（原文名称／中文条目）'),('start','起始年（公元前用负数）'),('end','截止年'),('entity','主体标识')]:body+='<label>'+label+'<input name="'+key+'" value="'+esc(params.get(key,''))+'"></label>'
    body+='<label>来源<select name="source">'+options(src,args['source'])+'</select></label><label>主题<select name="topic">'+options(topics,args['topic'])+'</select></label><button>检索</button></form>'
    body+='<p>找到 <b>'+str(data['total'])+'</b> 条来源记录。设置年代条件会排除未注明年代的断言；区间相交不代表逐年持续发生。</p>'
    for r in data['records']:
     body+='<article class="card"><span class="tag">'+esc(r['collection'])+'</span><small>'+esc(year(r['start_year'])+' — '+year(r['end_year']))+'</small><h2><a href="/record?'+urlencode({'id':r['id']})+'">'+esc(r['title'])+'</a></h2><p>'+esc(r['entity_name'])+'</p><small>'+esc(r['source_title'])+' · '+esc(r['locator'])+' · '+esc(r['review_status'])+'</small></article>'
    if data['offset']>0:body+='<a href="/?'+esc(urlencode(dict(params,offset=max(0,data['offset']-data['limit']))))+'">上一页</a>　'
    if data['offset']+data['limit']<data['total']:body+='<a href="/?'+esc(urlencode(dict(params,offset=data['offset']+data['limit'])))+'">下一页</a>'
    return self.send(page('历史与社会知识库',body),html=True)
   if url.path in ('/record','/api/record'):
    data=detail(params.get('id',''))
    if url.path.startswith('/api/'):return self.send(data)
    link=data['source_url'];body='<p>'+esc(data['locator'])+'</p>'
    if link.startswith(('https://','http://')):body+='<p><a href="'+esc(link)+'" target="_blank" rel="noreferrer">打开来源页面</a></p>'
    body+='<p>'+esc(data['time_semantics'])+'</p><h2>原始资料断言</h2><pre>'+esc(json.dumps(data['payload'],ensure_ascii=False,indent=2))+'</pre><details><summary>来源、结构化观察与关系</summary><pre>'+esc(json.dumps({k:v for k,v in data.items() if k!='payload'},ensure_ascii=False,indent=2))+'</pre></details>'
    return self.send(page(data['title'],body),html=True)
   if url.path in ('/coverage','/api/coverage'):
    data=json.loads((ROOT/'reports/coverage.json').read_text())
    if url.path.startswith('/api/'):return self.send(data)
    labels={'records':'来源记录','entities':'主体标识','observations':'观察记录','relations':'关系记录','sources':'来源快照','variables':'变量'}
    body='<div class="stats">'+''.join('<div><b>'+format(v,',')+'</b>'+labels[k]+'</div>' for k,v in data['counts'].items())+'</div><p>记录数包含缺测、元数据和来源重复表述，不等于独立史实数或完整度。不同来源的同名主体尚未自动合并。</p><table><tr><th>来源 / 数据集</th><th>记录</th><th>有日期记录的边界</th></tr>'
    for r in data['collections']:body+='<tr><td>'+esc(r['source_id']+' / '+r['collection'])+'</td><td>'+str(r['rows'])+'</td><td>'+esc(year(r['start'])+' — '+year(r['end']))+'</td></tr>'
    body+='</table><h2>仍需补齐</h2><p>逐年历史事件与原始文献证据链、前现代经济人口序列、古气候与灾害、疾病传播、教育文化和科学突破、2014 年后的战争与 2012 年后的联盟更新。现有政体抽样覆盖不等于全球全史。</p>'
    return self.send(page('覆盖与缺口',body),html=True)
   if url.path=='/entities':
    rows=entities(params.get('q',''),200)
    body='<form><label>名称或标识<input name="q" value="'+esc(params.get('q',''))+'"></label><button>查找主体</button></form><p>按来源保留身份；最多显示 200 项。国家、经济体、聚合地区、历史政体、战争和联盟分别标记。</p><table><tr><th>名称</th><th>类型</th><th>区域</th><th>标识</th></tr>'
    for r in rows:body+='<tr><td><a href="/?'+urlencode({'entity':r['id']})+'">'+esc(r['name'])+'</a></td><td>'+esc(r['kind'])+'</td><td>'+esc(r['region'])+'</td><td>'+esc(r['id'])+'</td></tr>'
    return self.send(page('主体目录',body+'</table>'),html=True)
   self.send_error(404)
  except (ValueError,KeyError) as exc:self.send_error(400,str(exc))
 def send(self,data,html=False):
  raw=(data if html else json.dumps(data,ensure_ascii=False)).encode()
  self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8' if html else 'application/json; charset=utf-8');self.send_header('Content-Length',str(len(raw)));self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(raw)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8765);a=p.parse_args()
 server=ThreadingHTTPServer(('127.0.0.1',a.port),Handler)
 print('Knowledge explorer: http://127.0.0.1:'+str(a.port),flush=True)
 server.serve_forever()
