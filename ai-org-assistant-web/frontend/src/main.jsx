import React,{useState} from 'react';
import {createRoot} from 'react-dom/client';
import {MessageSquare,Building2,FileText,Database,BarChart3,Users,Settings,Plus,Send,PanelLeft,Code2,Wrench,ShieldCheck,Search,Braces,LockKeyhole,Regex,Clock,Hash} from 'lucide-react';
import './styles.css';

const API='http://localhost:8000';
const nav=[['Chat',MessageSquare],['Documents',FileText],['Data',Database],['Analytics',BarChart3],['Developer Tools',Code2],['Team',Users],['Settings',Settings]];
const tools=[
 ['Multi Decoder','Decode Base64, URL, HTML, Hex, Unicode, ROT13 and JSON',Wrench],
 ['JSON Formatter','Format, validate and inspect JSON',Braces],
 ['Base64','Encode and decode Base64 safely',Code2],
 ['JWT Inspector','Inspect JWT header and payload locally',LockKeyhole],
 ['Regex Tester','Test patterns against text',Regex],
 ['Timestamp','Convert Unix timestamps and dates',Clock],
 ['Hash Generator','Generate common cryptographic hashes',Hash],
 ['Code Assistant','Explain, review, refactor and debug code',Code2],
];

function App(){
 const [mode,setMode]=useState('cowork'),[section,setSection]=useState('Chat');
 const [input,setInput]=useState(''),[messages,setMessages]=useState([{role:'assistant',content:'Hi! I’m your AI coworker. I can chat, work with organization data, analyze documents, and help with developer tools.'}]);
 const [loading,setLoading]=useState(false),[tool,setTool]=useState(null),[decode,setDecode]=useState(''),[results,setResults]=useState([]);
 async function send(){
  if(!input.trim()||loading)return;
  const user={role:'user',content:input}; setMessages(m=>[...m,user]);setInput('');setLoading(true);
  try{const r=await fetch(API+'/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:user.content,history:messages})});const d=await r.json();setMessages(m=>[...m,{role:'assistant',content:d.answer||d.detail||'No response'}]);}
  catch{setMessages(m=>[...m,{role:'assistant',content:'Backend is not connected. Start FastAPI on port 8000.'}]);} finally{setLoading(false)}
 }
 async function runDecoder(){
  const r=await fetch(API+'/api/tools/multi-decode',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({value:decode})});
  const d=await r.json();setResults(d.results||[]);
 }
 return <div className="app">
  <aside className="sidebar"><div className="brand"><span className="logo">AI</span><span>Workspace</span></div>
   <button className="new" onClick={()=>setMessages([{role:'assistant',content:'New conversation started. How can I help?'}])}><Plus size={17}/> New chat</button>
   <div className="mode"><button className={mode==='chat'?'active':''} onClick={()=>setMode('chat')}>AI Chat</button><button className={mode==='cowork'?'active':''} onClick={()=>setMode('cowork')}>Cowork</button></div>
   <div className="nav">{mode==='cowork'&&nav.map(([n,I])=><button key={n} className={section===n?'selected':''} onClick={()=>setSection(n)}><I size={18}/>{n}</button>)}</div>
   <div className="org"><Building2 size={18}/><div><b>My Organization</b><small>Secure workspace</small></div></div>
  </aside>
  <main><header><div><PanelLeft size={20}/><span className="crumb">{mode==='chat'?'AI Chat':`Cowork / ${section}`}</span></div><div className="topsearch"><Search size={16}/> Search</div><div className="avatar">P</div></header>
   {section==='Developer Tools' && mode==='cowork' ? <section className="toolsPage"><div className="hero"><span className="eyebrow">DEVELOPER TOOLKIT</span><h1>Build, decode & analyze</h1><p>Practical AI-powered utilities inside your organization workspace.</p></div><div className="toolGrid">{tools.map(([n,d,I])=><button className="toolCard" onClick={()=>setTool(n)} key={n}><I/><h3>{n}</h3><p>{d}</p><span>Open tool →</span></button>)}</div></section> :
   <><section className="chat">{messages.map((m,i)=><div className={'msg '+m.role} key={i}><div className="bubble">{m.content}</div></div>)}{loading&&<div className="msg assistant"><div className="bubble">Thinking…</div></div>}</section>
   <div className="composer"><button>+</button><textarea value={input} onChange={e=>setInput(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send()}}} placeholder={mode==='chat'?'Message AI…':'Ask your AI coworker…'}/><button className="send" onClick={send}><Send size={18}/></button></div></>}
  </main>
  <aside className="context"><h3>{tool|| (mode==='cowork'?'Workspace':'Chat')}</h3>
   {tool==='Multi Decoder'?<div className="decoder"><p>Paste an encoded value and inspect every useful decoding candidate.</p><textarea value={decode} onChange={e=>setDecode(e.target.value)} placeholder="Paste Base64 / URL / hex / escaped text…"/><button onClick={runDecoder}>Decode</button>{results.map(x=><div className="result" key={x.method}><b>{x.method}</b><pre>{x.result}</pre></div>)}</div>:
   mode==='cowork'?<><div className="card"><FileText/> <span>Documents</span><b>0</b></div><div className="card"><Database/> <span>Datasets</span><b>0</b></div><div className="card"><BarChart3/> <span>Insights</span><b>—</b></div><p>Use Developer Tools for decoding, JSON, regex, hashes and AI-assisted coding workflows.</p></>:<p>General AI chat with optional files, images and conversation history.</p>}
  </aside>
 </div>
}
createRoot(document.getElementById('root')).render(<App/>);
