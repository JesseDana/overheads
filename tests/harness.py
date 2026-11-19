"""Test harness: where the app and jsPDF are, and a stub of the claude.ai host runtime.

The app runs on its own (browser storage, ordinary downloads). Inside claude.ai it can also use the host's shared
database and downloads; the tests stub that runtime so both paths are covered.
"""
import os
HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.environ.get('OVERHEADS_APP', os.path.join(os.path.dirname(HERE), 'index.html'))
JSPDF = os.environ.get('OVERHEADS_JSPDF', os.path.join(HERE, 'node_modules', 'jspdf', 'dist', 'jspdf.umd.min.js'))
STUB="""
window.__saved=[];
window.claude={use:async(name)=>name==='downloads'?{save:async({filename,data})=>{const b=data instanceof Blob?data:new Blob([data]);
  const buf=new Uint8Array(await b.arrayBuffer());let s='';for(let i=0;i<buf.length;i+=32768)s+=String.fromCharCode.apply(null,buf.subarray(i,i+32768));
  window.__saved.push({filename,b64:btoa(s)});}}:null};
"""
