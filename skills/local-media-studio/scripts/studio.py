"""Run the local, credential-free media tools retained from Easel."""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / 'scripts/vendor/easel'
TOOLS = {
    'video': ('video_ops', '剪切、拼接、变速、去静音、画幅、BGM、水印、抽帧', []),
    'audio': ('audio_ops', '提取音轨、裁切、响度、淡入淡出、降噪', []),
    'image': ('image_ops', '裁切、缩放、压缩、拼图、水印、缩略图', ['PIL']),
    'subtitles': ('subtitle_ops', '解析、双语合并、格式转换、烧录', []),
    'reframe': ('reframe', '横转竖、模糊背景、人脸辅助构图', []),
    'highlights': ('highlight_cut', '候选高光、按时间段批量切片', []),
    'mix': ('audio_mix', '旁白与音乐混合、自动压低背景音', []),
    'beats': ('beatsync', '节拍检测、按节拍编排素材', ['numpy', 'librosa']),
    'chroma': ('chromakey', '绿幕或指定颜色抠像合成', []),
    'enhance': ('img_enhance', '图像锐化、去噪、对比度', ['PIL']),
    'asr': ('asr', '本地 Whisper 语音识别与字幕', []),
    'wordcount': ('wordcount', '中文、英文、社媒字数统计', []),
    'visualizer': ('audio_viz', '音频波形、频谱可视化', []),
    'branding': ('intro_outro', '片头片尾素材与拼接', []),
}
OPTIONAL = {
    'cv2': 'opencv-python（人脸构图和部分图像增强）',
    'librosa': 'librosa（高光能量分析、节拍检测）',
    'numpy': 'numpy（能量/图像计算）',
    'faster_whisper': 'faster-whisper（本地 ASR；模型权重另行下载）',
}


def environment():
    env = dict(os.environ)
    env['PYTHONUTF8'] = '1'
    env['PYTHONIOENCODING'] = 'utf-8'
    # Reuse the existing skill's private wheels, without any Easel installation.
    packages = ROOT.parent / 'free-ai-video/.runtime/packages'
    if packages.is_dir() and not (ROOT/'.runtime/runtime.json').exists():
        env['PYTHONPATH'] = str(packages) + (os.pathsep + env['PYTHONPATH'] if env.get('PYTHONPATH') else '')
    for tool in ('ffmpeg', 'ffprobe'):
        if not shutil.which(tool):
            cache = Path.home() / '.cache/codex-studio-toolchains/ffmpeg'
            found = sorted(cache.glob(f'*/bin/{tool}.exe'))
            if found:
                env['PATH'] = str(found[-1].parent) + os.pathsep + env.get('PATH', '')
    return env


def doctor():
    env = environment()
    # Inspect in the same child environment that executes the commands.
    probe = 'import importlib.util,json;print(json.dumps({n:importlib.util.find_spec(n)is not None for n in '+repr(['PIL', *OPTIONAL])+ '}))'
    result = subprocess.run([sys.executable, '-c', probe], env=env, capture_output=True, text=True, encoding='utf-8', check=True)
    modules = json.loads(result.stdout)
    files = all((VENDOR / (spec[0]+'.py')).is_file() for spec in TOOLS.values())
    ffmpeg = shutil.which('ffmpeg', path=env.get('PATH'))
    ffprobe = shutil.which('ffprobe', path=env.get('PATH'))
    return {'python': sys.executable, 'ready': bool(files and ffmpeg and ffprobe and modules['PIL']),
            'vendor_files_present': files, 'ffmpeg': ffmpeg, 'ffprobe': ffprobe,
            'modules': modules, 'optional_dependencies': OPTIONAL,
            'paid_apis_enabled': False, 'requires_easel_server': False,
            'asr_note': 'The library and the model weights are separate; no weights are downloaded by doctor.'}


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    config_path = ROOT/'.runtime/runtime.json'
    if config_path.is_file():
        configured = Path(json.loads(config_path.read_text('utf-8-sig'))['python'])
        if not configured.is_file():
            raise RuntimeError('Configured media Python is missing; run scripts/bootstrap.py again.')
        if configured.resolve() != Path(sys.executable).resolve():
            return subprocess.run([str(configured), str(Path(__file__).resolve()), *sys.argv[1:]], env=environment()).returncode
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('list')
    sub.add_parser('doctor')
    run = sub.add_parser('run', help='Run one bundled tool. Example: run video info -i clip.mp4')
    run.add_argument('--input', action='append', default=[], help='Tracked input; repeat for auxiliary files. First is the primary recording.')
    run.add_argument('--output', help='Track one output and save its .processing.json receipt.')
    run.add_argument('--reuse', action='store_true', help='Reuse only when tool, arguments, inputs and output hashes match.')
    run.add_argument('tool', choices=TOOLS)
    run.add_argument('args', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.command == 'list':
        print(json.dumps({key: {'script': val[0], 'purpose': val[1]} for key, val in TOOLS.items()}, ensure_ascii=False, indent=2))
    elif args.command == 'doctor':
        data = doctor()
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0 if data['ready'] else 2
    else:
        script = VENDOR / (TOOLS[args.tool][0]+'.py')
        rest = args.args[1:] if args.args[:1] == ['--'] else args.args
        if args.output or args.input or args.reuse:
            if not args.output or not args.input or not rest:
                parser.error('Tracked processing needs --input, --output and a tool command.')
            from receipts import tracked_run
            code, result = tracked_run(args.tool, script, rest, args.input, args.output, environment(), args.reuse)
            print(json.dumps(result, ensure_ascii=False))
            return code
        return subprocess.run([sys.executable, str(script), *(rest or ['--help'])], env=environment()).returncode
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
