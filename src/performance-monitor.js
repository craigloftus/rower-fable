// Opt-in local diagnostics. No analytics uploads; at most 15 minutes of samples.
export const diagnosticsEnabled = new URLSearchParams(location.search).has('perf');
const percentile = (values, fraction) => values.length
  ? values.slice().sort((a,b)=>a-b)[Math.min(values.length-1,Math.floor(values.length*fraction))] : null;
const mean = values => values.length ? values.reduce((a,b)=>a+b,0)/values.length : null;
const round = value => value == null ? null : Math.round(value*100)/100;

export function createPerformanceMonitor(renderer, context) {
  if (!diagnosticsEnabled) return null;
  const panel=document.createElement('details');
  panel.id='performance'; panel.open=true;
  panel.style.cssText='position:fixed;z-index:50;left:8px;top:8px;max-width:calc(100vw - 32px);width:390px;padding:10px;background:#172820ed;color:#fff;border-radius:6px;font:12px/1.5 monospace;max-height:85vh;overflow:auto';
  panel.innerHTML=`<summary>Performance · local measurements</summary>
    <p style="margin:6px 0">Temperature and battery draw require a real phone test.</p>
    <button id="perf-run">Run 60s rowing sample</button> <button id="perf-save">Save report</button>
    <label style="display:block">Resolution <select id="perf-resolution"><option value="auto">Native</option><option value="1">1×</option><option value="1.5">1.5×</option><option value="2">2×</option></select></label>
    <label style="display:block"><input id="perf-character" type="checkbox" checked> Render character</label>
    <output id="perf-live" style="display:block;white-space:pre-wrap">Warming up…</output>
    <details id="perf-data"><summary>Report data</summary><pre id="perf-report" style="white-space:pre-wrap;font-size:10px"></pre></details>`;
  document.body.append(panel);
  const dataPanel=panel.querySelector('#perf-data');
  const live=panel.querySelector('#perf-live'), reportNode=panel.querySelector('#perf-report');
  const gl=renderer.getContext(), ext=gl.getExtension('EXT_disjoint_timer_query_webgl2');
  let pending=[], activeQuery=null, frameNumber=0, lastFrame=null, windowStart=performance.now();
  let frames=[], cpu=[], gpu=[], stages={}, stageStart=0, sampleStart=0, capture=null;
  let rafIntervals=[], lastRaf=null, longTasks=[];
  if (PerformanceObserver.supportedEntryTypes.includes('longtask')) {
    new PerformanceObserver(list => longTasks.push(...list.getEntries().map(entry => entry.duration)))
      .observe({ type: 'longtask' });
  }
  const gpuInfo=gl.getExtension('WEBGL_debug_renderer_info');
  const history=[];
  const metadata={created:new Date().toISOString(),userAgent:navigator.userAgent,devicePixelRatio,
    gpuTimerSupported:!!ext,gpuRenderer:gl.getParameter(gpuInfo ? gpuInfo.UNMASKED_RENDERER_WEBGL : gl.RENDERER),notes:'CPU is JS + render submission, not GPU duration. Desktop results do not establish phone thermals.'};
  function snapshot(){return {metadata,...context(),capture: capture && {state:capture.invalid?'interrupted':capture.done?'complete':'running',warmupSeconds:10,durationSeconds:60},samples:capture?capture.rows:history,rollingSamples:history};}
  function resetWindow(){frames=[];cpu=[];gpu=[];stages={};rafIntervals=[];lastRaf=null;longTasks=[];lastFrame=null;windowStart=performance.now();}
  function cancelQueries(){for(const query of pending)gl.deleteQuery(query);pending=[];}
  document.addEventListener('visibilitychange',()=>{
    resetWindow();cancelQueries();
    if(document.hidden && capture && !capture.done){capture.done=true;capture.invalid=true;api.onCaptureEnd?.();}
  });
  dataPanel.addEventListener('toggle',()=>{if(dataPanel.open)reportNode.textContent=JSON.stringify(snapshot(),null,2);});
  const api={
    panel,
    startCapture(){capture={from:performance.now()+10000,until:performance.now()+70000,rows:[],done:false};resetWindow();},
    get report(){return snapshot();},
    reset:resetWindow,
    animationFrame(now){if(lastRaf!=null)rafIntervals.push(now-lastRaf);lastRaf=now;},
    begin(now){
      sampleStart=stageStart=performance.now();
      if(lastFrame!=null)frames.push(now-lastFrame);lastFrame=now;
    },
    mark(name){const now=performance.now();(stages[name]??=[]).push(now-stageStart);stageStart=now;},
    beforeRender(){
      if(!ext)return;
      const disjoint=gl.getParameter(ext.GPU_DISJOINT_EXT);
      if(disjoint){cancelQueries();return;}
      while(pending.length && gl.getQueryParameter(pending[0],gl.QUERY_RESULT_AVAILABLE)){
        const query=pending.shift();gpu.push(gl.getQueryParameter(query,gl.QUERY_RESULT)/1e6);gl.deleteQuery(query);
      }
      if(frameNumber++%10===0 && pending.length<4){activeQuery=gl.createQuery();gl.beginQuery(ext.TIME_ELAPSED_EXT,activeQuery);}
    },
    end(now){
      if(activeQuery){gl.endQuery(ext.TIME_ELAPSED_EXT);pending.push(activeQuery);activeQuery=null;}
      cpu.push(performance.now()-sampleStart);
      if(now-windowStart<1000)return;
      const info=renderer.info, details=context();
      const row={seconds:round(now/1000),durationMs:round(now-windowStart),browserRafFps:round(1000/mean(rafIntervals)),longTasks:longTasks.length,longTaskMs:round(longTasks.reduce((sum,ms)=>sum+ms,0)),fps:round(1000/mean(frames)),frameP95:round(percentile(frames,.95)),
        over25ms:frames.filter(x=>x>25).length,frameMax:round(Math.max(...frames)),frames:frames.length,cpuMax:round(Math.max(...cpu)),cpuMean:round(mean(cpu)),cpuP95:round(percentile(cpu,.95)),
        gpuMean:round(mean(gpu)),gpuP95:round(percentile(gpu,.95)),calls:info.render.calls,triangles:info.render.triangles,
        geometries:info.memory.geometries,textures:info.memory.textures,programs:info.programs.length,
        drawingBuffer:[renderer.domElement.width,renderer.domElement.height],dpr:round(renderer.getPixelRatio()),
        stages:Object.fromEntries(Object.entries(stages).map(([key,values])=>[key,round(mean(values))])),...details};
      history.push(row);if(history.length>900)history.shift();
      if(capture && !capture.done){
        if(windowStart>=capture.from && now<=capture.until)capture.rows.push(row);
        if(now>=capture.until){capture.done=true;api.onCaptureEnd?.();}
      }
      const state=!capture?'Live':capture.invalid?'Sample interrupted · page was hidden':capture.done?'60s sample complete':now<capture.from?'10s warm-up':`Recording · ${Math.ceil((capture.until-now)/1000)}s left`;
      live.textContent=`${state}\n${row.fps} fps · browser ${row.browserRafFps} Hz\nframe p95 ${row.frameP95} ms\nCPU ${row.cpuMean} ms · p95 ${row.cpuP95} ms\nGPU ${row.gpuMean??'unavailable'} ms\n${row.calls} draws · ${row.triangles.toLocaleString()} triangles\n${row.drawingBuffer.join(' × ')} px · DPR ${row.dpr}\n${row.geometries} geometries · ${row.textures} textures\n${JSON.stringify(row.stages)}`;
      if(dataPanel.open) reportNode.textContent=JSON.stringify(snapshot(),null,2);
      // Keep lastFrame across windows so no frame interval is dropped.
      frames=[];cpu=[];gpu=[];stages={};rafIntervals=[];longTasks=[];windowStart=now;
    },
  };
  panel.querySelector('#perf-run').onclick=()=>{
    if(api.onCaptureStart?.() === false) { live.textContent='Wait for the character to load and disconnect the monitor before a simulated sample. Live measurements still record real rowing.'; return; }
    api.startCapture();
  };
  panel.querySelector('#perf-save').onclick=()=>{
    const url=URL.createObjectURL(new Blob([JSON.stringify(snapshot(),null,2)],{type:'application/json'}));
    const link=document.createElement('a');link.href=url;link.download=`rowing-performance-${Date.now()}.json`;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  };
  panel.querySelector('#perf-resolution').onchange=e=>api.onResolution?.(e.target.value);
  panel.querySelector('#perf-character').onchange=e=>api.onCharacter?.(e.target.checked);
  return api;
}
