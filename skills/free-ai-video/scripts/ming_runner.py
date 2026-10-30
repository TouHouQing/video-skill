"""Run the pinned Ming checkpoint locally, with outbound Python sockets blocked."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,os,socket,sys,time,hashlib,random

ROOT=Path.home()/'.local/share/free-ai-video/ming3'
os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_DATASETS_OFFLINE='1',
                  HF_HUB_DISABLE_TELEMETRY='1',DO_NOT_TRACK='1',TOKENIZERS_PARALLELISM='false',TQDM_DISABLE='1')
attempted_network=[]
def deny_network(*args,**kwargs):
    attempted_network.append('outbound connection blocked')
    raise RuntimeError('Local Ming inference has networking disabled.')
socket.socket.connect=deny_network
socket.socket.connect_ex=deny_network
socket.create_connection=deny_network
sys.path.insert(0,str(ROOT/'src'))
import numpy as np
import soundfile as sf
import torch
from ming_tts import MingTTS

def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        while block:=f.read(4*1024*1024):h.update(block)
    return h.hexdigest()
def save(path,value):Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2),'utf-8')
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--job',required=True)
    parser.add_argument('--runtime-root')
    args=parser.parse_args()
    if args.runtime_root:
        global ROOT
        requested=Path(args.runtime_root).expanduser().resolve()
        if requested!=ROOT.resolve():raise ValueError('This installed runner is pinned to its verified runtime root.')
    job=json.loads(Path(args.job).read_text('utf-8-sig'))
    output=Path(job['output']);output.mkdir(parents=True,exist_ok=True)
    assert torch.cuda.is_available(),'CUDA GPU is not available in this environment.'
    torch.set_num_threads(6)
    torch.set_num_interop_threads(1)
    torch.cuda.reset_peak_memory_stats()
    start=time.perf_counter()
    model=MingTTS(str(ROOT/'model'),device='cuda:0',text_normalization=False)
    torch.cuda.synchronize()
    loaded=time.perf_counter()-start
    provenance=json.loads((ROOT/'source-provenance.json').read_text('utf-8'))
    report={'status':'running','model':'inclusionAI/Ming-3.0-tts-0.5B','provider':'ming-local',
      'started_at':datetime.now(timezone.utc).isoformat(),'repository_commit':provenance['commit'],
      'model_path':str(ROOT/'model'),'model_sha256':digest(ROOT/'model/model.safetensors'),
      'torch_version':torch.__version__,'torch_cuda':torch.version.cuda,'numpy_version':np.__version__,
      'gpu':torch.cuda.get_device_name(),'model_load_seconds':round(loaded,3),
      'load_peak_allocated_mib':round(torch.cuda.max_memory_allocated()/2**20,1),
      'load_peak_reserved_mib':round(torch.cuda.max_memory_reserved()/2**20,1),
      'network_guard':'HF offline flags and Python outbound socket calls blocked',
      'text_normalization':'Skipped optional pynini; supplied Chinese text is prewritten for speaking.',
      'paid_api_cost':0,'samples':[]}
    save(output/'report.json',report)
    previous={}
    for item in job['samples']:
        key=item['id']
        if not key or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789_-' for c in key):raise ValueError('Unsafe sample id')
        seed=item.get('seed',42);random.seed(seed);np.random.seed(seed);torch.manual_seed(seed);torch.cuda.manual_seed_all(seed)
        torch.cuda.reset_peak_memory_stats();torch.cuda.synchronize();start=time.perf_counter()
        options={'task':item.get('task','FREEFORM'),'text':item['text'],'language_id':'Chinese',
          'cfg':item.get('cfg',2.0),'sigma':item.get('sigma',.25),'temperature':item.get('temperature',0.0),
          'max_length':item.get('max_length',40),'max_decode_steps':item.get('max_decode_steps',700),
          'raw_text':item.get('raw_text',False)}
        if item.get('reference_sample'):
            ref=previous[item['reference_sample']]
            options.update(prompt_wav_path=ref['path'],prompt_text=ref['text'],use_spk_emb=True)
        elif item.get('reference_audio'):
            reference_path=Path(item['reference_audio'])
            if not reference_path.is_absolute():reference_path=Path(args.job).resolve().parent/reference_path
            reference_path=reference_path.resolve()
            if not reference_path.is_file() or not item.get('reference_text'):
                raise ValueError('Reference audio must exist and include its exact transcript')
            options.update(prompt_wav_path=str(reference_path),prompt_text=item['reference_text'],use_spk_emb=True)
        else:options['use_zero_spk_emb']=True
        if item.get('instruction'):options['instruction']=item['instruction']
        if item.get('controls'):options['controls']=item['controls']
        print(json.dumps({'stage':'synthesize','id':key,'task':options['task']},ensure_ascii=False),flush=True)
        waveform=model.synthesize(**options)
        torch.cuda.synchronize();seconds=time.perf_counter()-start
        audio=waveform.detach().float().cpu().numpy().reshape(-1)
        if not np.isfinite(audio).all() or len(audio)==0:raise RuntimeError('Generated invalid audio')
        raw_peak=float(np.max(np.abs(audio)));gain=min(1.0,.98/max(raw_peak,1e-8))
        audio=audio*gain
        path=output/(key+'.wav');sf.write(path,audio,model.sample_rate,subtype='PCM_24')
        duration=len(audio)/model.sample_rate
        rms=float(np.sqrt(np.mean(audio.astype(np.float64)**2)))
        if duration<1 or rms<.0001:raise RuntimeError('Generated empty or near-silent output')
        record={'id':key,'label':item['label'],'path':str(path),'text':item['text'],'task':options['task'],
          'instruction':item.get('instruction'),'controls':item.get('controls'),
          'reference_sample':item.get('reference_sample'),'seed':seed,
          'reference_audio':options.get('prompt_wav_path'),'reference_text':options.get('prompt_text'),
          'sample_rate':model.sample_rate,'duration_seconds':round(duration,3),'generation_seconds':round(seconds,3),
          'rtf':round(seconds/duration,3),'peak_allocated_mib':round(torch.cuda.max_memory_allocated()/2**20,1),
          'peak_reserved_mib':round(torch.cuda.max_memory_reserved()/2**20,1),
          'raw_peak':raw_peak,'written_gain':gain,'rms_dbfs':round(20*np.log10(max(rms,1e-12)),2),
          'sha256':digest(path),'provider':'ming-local','paid_api_cost':0}
        previous[key]=record;report['samples'].append(record);save(output/'report.json',report)
        print(json.dumps({'stage':'sample_complete',**record},ensure_ascii=False),flush=True)
    report.update(status='completed',completed_at=datetime.now(timezone.utc).isoformat(),
      blocked_network_attempts=len(attempted_network),subjective_review='User listening required; no claim of a human listening review.')
    save(output/'report.json',report)
    print(json.dumps({'stage':'completed','report':str(output/'report.json'),'samples':len(report['samples']),'network_attempts':len(attempted_network)},ensure_ascii=False),flush=True)

if __name__=='__main__':main()
