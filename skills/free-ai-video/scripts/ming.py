"""Batch local Ming inference with a persisted, user-selected reference voice."""
from pathlib import Path
import hashlib,json,os
from runtime import ROOT,emit,ffmpeg,run,save_json

def settings():
    path=ROOT/'.runtime/ming.json'
    if not path.is_file():raise RuntimeError('Ming is not configured; see references/local-tts.md. No fallback was used.')
    return json.loads(path.read_text('utf-8'))

def linux_path(path,config):
    path=str(Path(path).resolve())
    if os.name!='nt':return path
    result=run(['wsl.exe','-d',config['distribution'],'--exec','wslpath','-u',path.replace('\\','/')],timeout=20)
    converted=result.stdout.strip()
    if not converted.startswith('/'):raise RuntimeError('Could not map the Ming input into WSL.')
    return converted

def prepare_records(project,folder):
    import voice
    config=settings();profile_id=project.get('voice_profile',config.get('default_profile','anime-c'))
    if profile_id!='anime-c':raise ValueError('Only the installed anime-c voice profile is configured.')
    profile=json.loads((ROOT/'assets/voices/ming-anime-c.json').read_text('utf-8'))
    reference=ROOT/'assets/voices'/profile['reference_audio']
    ref_sha=hashlib.sha256(reference.read_bytes()).hexdigest()
    if ref_sha!=profile['reference_sha256']:raise RuntimeError('The selected Ming reference voice changed; refusing to silently change the speaker.')
    folder=Path(folder).resolve();folder.mkdir(parents=True,exist_ok=True)
    tempo=float(project.get('voice_tempo',config.get('tempo',1.0)))
    if not .8<=tempo<=1.2:raise ValueError('Ming voice_tempo must be between 0.8 and 1.2.')
    seed=int(project.get('voice_seed',330))
    records=[];pending=[]
    for i,scene in enumerate(project['scenes']):
        path=folder/f'voice-{i:02}.wav';meta_path=path.with_suffix('.meta.json')
        fingerprint=hashlib.sha256(json.dumps({'text':scene['narration'],'provider':'ming-local',
            'model_sha256':config['model_sha256'],'reference_sha256':ref_sha,'profile':profile_id,
            'tempo':tempo,'seed':seed+i,'output_rate':44100},sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        record=None
        if path.exists() and meta_path.exists():
            cached=json.loads(meta_path.read_text('utf-8'))
            if cached.get('fingerprint')==fingerprint and voice.duration(path)>.1:record=cached
        records.append(record)
        if record is None:pending.append((i,scene,path,meta_path,fingerprint))
    if pending:
        batch_id=hashlib.sha256(''.join(x[4] for x in pending).encode()).hexdigest()[:16]
        generated=folder/'ming-generated'/('batch-'+batch_id);generated.mkdir(parents=True,exist_ok=True)
        ref_linux=linux_path(reference,config)
        job={'output':linux_path(generated,config),'samples':[
            {'id':f'voice-{i:02}','label':scene['id'],'task':'TTS','seed':seed+i,
             'text':scene['narration'],'reference_audio':ref_linux,'reference_text':profile['reference_text'],
             'max_length':40,'max_decode_steps':700} for i,scene,_,_,_ in pending]}
        job_path=folder/'ming-job.json';save_json(job_path,job)
        runner=ROOT/'scripts/ming_runner.py'
        command=[config['python'],linux_path(runner,config),'--job',linux_path(job_path,config),
                 '--runtime-root',config['root']]
        if os.name=='nt':command=['wsl.exe','-d',config['distribution'],'--exec']+command
        emit('ming_batch',scenes=len(pending),profile=profile_id,provider='ming-local')
        completed=run(command,timeout=max(180,len(pending)*120))
        (folder/'ming-inference.log').write_text(completed.stdout+'\n'+completed.stderr,'utf-8')
        inference=json.loads((generated/'report.json').read_text('utf-8'))
        if inference.get('status')!='completed' or inference.get('model_sha256')!=config['model_sha256']:
            raise RuntimeError('Ming inference did not complete with the configured checkpoint.')
        actual={x['id']:x for x in inference['samples']}
        for i,scene,path,meta_path,fingerprint in pending:
            generated_path=generated/f'voice-{i:02}.wav'
            filters=[]
            if tempo!=1:filters.append(f'atempo={tempo}')
            args=[ffmpeg(),'-y','-hide_banner','-loglevel','error','-i',generated_path]
            if filters:args+=['-af',','.join(filters)]
            run(args+['-ar','44100','-ac','1','-c:a','pcm_s16le',path],timeout=60)
            details=actual[f'voice-{i:02}']
            record={'fingerprint':fingerprint,'provider':'ming-local','voice':profile_id,'profile_label':profile['label'],
                'seconds':round(voice.duration(path),4),'path':str(path),'paid_api_cost':0,
                'model':config['model'],'reference_sha256':ref_sha,'seed':seed+i,'tempo':tempo,
                'generation_seconds':details['generation_seconds'],'raw_sample_rate':details['sample_rate'],
                'output_sample_rate':44100,'raw_sha256':details['sha256'],
                'network_attempts':inference.get('blocked_network_attempts'),'inference_report':str(generated/'report.json')}
            save_json(meta_path,record);records[i]=record
    return records
