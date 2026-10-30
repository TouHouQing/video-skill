"""Regressions for real handoffs, stage isolation and processing reuse."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from workflow import load_project, prepare_inputs, ops_module


def write(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False), 'utf-8')


def project():
    return {'title': '离线衔接测试', 'angle': '不代表真实新闻或模型实测', 'visual_mode': 'montage',
            'sources': [{'id': 'docs', 'url': 'https://example.org/docs', 'label': 'Fixture', 'claims': ['Fixture only']}],
            'media': [{'id': 'image', 'type': 'image', 'path': 'future-image.png', 'rights': {'kind': 'owned'}}],
            'scenes': [{'id': str(i), 'kind': 'evidence', 'headline': '测试', 'narration': '这是测试。', 'source_ids': ['docs'],
                        'shots': [{'id': 'shot-'+str(i), 'type': 'image', 'media_id': 'image'}]} for i in range(3)]}


class WorkflowChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root/'project.json'
        self.ops = ops_module()
        self.channel = self.root/'channel'
        self.ops.initialize(self.channel)

    def save(self, data):
        write(self.path, data)
        return self.path

    def test_profile_fills_only_missing_preferences(self):
        data = project()
        data.update(channel_dir='channel', content_type='ai_news', voice_mode='local', requirements={'recording_min_ratio': .5})
        value, trace = load_project(self.save(data))
        self.assertEqual(value['voice_mode'], 'local')
        self.assertEqual(value['voice_profile'], 'anime-c')
        self.assertEqual(value['visual_style'], 'source_led')
        self.assertEqual(value['requirements']['recording_min_ratio'], .5)
        self.assertIn('voice_profile', trace['defaults_applied'])
        self.assertNotEqual(trace['effective_sha256'], trace['input_sha256'])

    def test_project_without_channel_keeps_legacy_behavior(self):
        data = project()
        data.pop('visual_mode')
        value, trace = load_project(self.save(data))
        self.assertNotIn('voice_mode', value)
        self.assertNotIn('visual_mode', value)
        self.assertIsNone(trace['profile_path'])

    def test_draft_preflight_does_not_require_planned_media_or_tts(self):
        with patch('voice.prepare') as speech:
            result, _, inventory, _ = prepare_inputs(self.save(project()), 'draft')
        self.assertTrue(result['technical_inputs_ready'])
        self.assertEqual(inventory, {})
        speech.assert_not_called()

    def test_production_preflight_rejects_missing_media(self):
        with self.assertRaisesRegex(ValueError, 'Media file missing'):
            prepare_inputs(self.save(project()), 'produce')

    def test_draft_gate_is_checked_before_processing(self):
        data = project()
        data['approval_status'] = 'awaiting_user'
        with self.assertRaisesRegex(ValueError, 'awaiting user approval'):
            prepare_inputs(self.save(data), 'produce')

    def test_map_that_no_longer_matches_used_shots_is_rejected(self):
        data = project()
        data['evidence_map'] = [{'scene_id': str(i), 'source_ids': ['docs'], 'media_ids': ['wrong-media'],
                                 'viewer_focus': '检查结果'} for i in range(3)]
        with self.assertRaisesRegex(ValueError, 'actually used'):
            prepare_inputs(self.save(data), 'draft')

    def test_complete_map_exposes_the_actual_spoken_idea(self):
        data = project()
        data['evidence_map'] = [{'scene_id': str(i), 'source_ids': ['docs'], 'media_ids': ['image'],
                                 'viewer_focus': '展示原始结果'} for i in range(3)]
        report, _, _, _ = prepare_inputs(self.save(data), 'draft')
        self.assertEqual(report['scene_material_map'][0]['narration'], data['scenes'][0]['narration'])
        self.assertEqual(report['scene_material_map'][0]['media'][0]['id'], 'image')

    def test_new_mode_does_not_capture_unused_source_pages(self):
        report, _, _, _ = prepare_inputs(self.save(project()), 'draft')
        self.assertEqual(report['sources_to_capture'], [])
        data = project()
        data['sources'][0]['capture'] = True
        report, _, _, _ = prepare_inputs(self.save(data), 'draft')
        self.assertEqual(report['sources_to_capture'], ['docs'])

    def test_missing_topic_link_fails_before_rendering(self):
        data = project()
        data.update(channel_dir='channel', topic_id='unknown')
        with self.assertRaisesRegex(ValueError, 'Unknown topic_id'):
            prepare_inputs(self.save(data), 'draft')

    def seed_topic(self, status='selected'):
        self.ops.record_rows(self.channel, 'topics', [{'id': 'topic', 'title': '测试', 'audience_problem': '测试用例',
                                                     'sources': ['https://example.org/docs'], 'status': status}])

    def test_brief_is_bounded_and_stage_specific(self):
        learning = [{'id': str(i), 'observation': 'fixture', 'evidence': ['test fixture'],
                     'recorded_at': '2026-10-28T01:00:00+08:00'} for i in range(15)]
        self.ops.record_rows(self.channel, 'learning', learning)
        draft = self.ops.brief(self.channel, 'draft', limit=3)
        production = self.ops.brief(self.channel, 'produce')
        self.assertEqual(len(draft['learning']), 3)
        self.assertNotIn('learning', production)
        self.assertNotIn('performance', draft)
        self.assertEqual(draft['counts']['learning'], 15)

    def test_linking_encode_does_not_claim_editorial_approval_or_posting(self):
        self.seed_topic()
        video = self.root/'test.mp4'
        video.write_bytes(b'fixture; media validity is tested separately')
        report_path = self.root/'report.json'
        write(report_path, {'status': 'completed', 'verification': {'passed': True}, 'video': str(video)})
        self.ops.attach_production(self.channel, 'topic', self.path, report_path)
        topic = self.ops.read(self.channel/'topics.json')[0]
        self.assertEqual(topic['status'], 'produced_pending_review')
        self.assertEqual(topic['artifacts'][0]['editorial_review'], 'pending')
        self.assertNotIn('published_at', topic)

    def test_failed_encode_cannot_update_topic(self):
        self.seed_topic()
        before = (self.channel/'topics.json').read_bytes()
        report_path = self.root/'report.json'
        write(report_path, {'status': 'failed', 'verification': {'passed': False}})
        with self.assertRaisesRegex(ValueError, 'Only a completed'):
            self.ops.attach_production(self.channel, 'topic', self.path, report_path)
        self.assertEqual((self.channel/'topics.json').read_bytes(), before)

    def test_existing_published_status_survives_a_new_local_artifact(self):
        self.seed_topic('published')
        video = self.root/'test.mp4'
        video.write_bytes(b'fixture')
        report_path = self.root/'report.json'
        write(report_path, {'status': 'completed', 'verification': {'passed': True}, 'video': str(video)})
        self.ops.attach_production(self.channel, 'topic', self.path, report_path)
        self.assertEqual(self.ops.read(self.channel/'topics.json')[0]['status'], 'published')


class ProcessingChecks(unittest.TestCase):
    def setUp(self):
        path = Path(__file__).resolve().parents[2]/'local-media-studio/scripts/receipts.py'
        spec = importlib.util.spec_from_file_location('tested_receipts', path)
        self.receipts = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.receipts)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root/'raw.mp4'
        self.output = self.root/'cut.mp4'
        self.script = self.root/'tool.py'
        self.source.write_bytes(b'original-fixture')
        self.script.write_text('pass', 'utf-8')

    def tracked(self, tool='video', operation='cut', source=None, output=None):
        source, output = source or self.source, output or self.output
        args = [operation, '-i', str(source), '-o', str(output)]
        def execute(*unused, **kwargs):
            output.write_bytes(source.read_bytes()+b'-processed')
            return subprocess.CompletedProcess([], 0)
        with patch.object(self.receipts.subprocess, 'run', side_effect=execute) as runner:
            _, result = self.receipts.tracked_run(tool, self.script, args, [source], output, {}, True)
            return result, runner.call_count

    def test_exact_cache_hit_skips_execution(self):
        first, first_calls = self.tracked()
        second, second_calls = self.tracked()
        self.assertEqual((first['status'], first_calls), ('completed', 1))
        self.assertEqual((second['status'], second_calls), ('reused', 0))

    def test_changed_input_output_or_code_invalidates_cache(self):
        self.tracked()
        self.source.write_bytes(b'changed')
        self.assertEqual(self.tracked()[1], 1)
        self.output.write_bytes(b'tampered')
        self.assertEqual(self.tracked()[1], 1)
        self.script.write_text('# fixed tool\npass', 'utf-8')
        self.assertEqual(self.tracked()[1], 1)

    def test_two_step_lineage_reaches_original_and_detects_tampering(self):
        self.tracked()
        final = self.root/'portrait.mp4'
        self.tracked('reframe', 'reframe', self.output, final)
        root = {'status': 'completed', 'sha256': self.receipts.sha256(self.source)}
        lineage = self.receipts.validate_capture_lineage(final, self.receipts.sha256(final), root, self.receipts.sidecar(final))
        self.assertEqual(lineage['depth'], 2)
        self.output.write_bytes(b'broken parent')
        with self.assertRaisesRegex(ValueError, 'input has changed'):
            self.receipts.validate_capture_lineage(final, self.receipts.sha256(final), root, self.receipts.sidecar(final))

    def test_non_picture_operation_cannot_become_recording_evidence(self):
        self.tracked('visualizer', 'render')
        root = {'status': 'completed', 'sha256': self.receipts.sha256(self.source)}
        with self.assertRaisesRegex(ValueError, 'does not preserve recording'):
            self.receipts.validate_capture_lineage(self.output, self.receipts.sha256(self.output), root, self.receipts.sidecar(self.output))

    def test_tracking_cannot_overwrite_the_original(self):
        with self.assertRaisesRegex(ValueError, 'separate output'):
            self.receipts.tracked_run('video', self.script, ['cut', str(self.source)], [self.source], self.source, {}, True)

    def test_same_stem_video_and_audio_have_different_receipts(self):
        self.assertNotEqual(self.receipts.sidecar(self.root/'clip.mp4'), self.receipts.sidecar(self.root/'clip.wav'))

    def test_raw_recording_and_processed_view_remain_one_original(self):
        from media import resolve_media
        self.tracked()
        manifest = self.root/'raw.recording.json'
        write(manifest, {'status': 'completed', 'sha256': self.receipts.sha256(self.source)})
        raw = {'id': 'raw', 'type': 'video', 'path': str(self.source), 'role': 'target_app',
               'recording_manifest': str(manifest), 'rights': {'kind': 'original_capture'}}
        edited = {**raw, 'id': 'edited', 'path': str(self.output),
                  'processing_manifest': str(self.receipts.sidecar(self.output))}
        with patch('media.probe', return_value={'width': 360, 'height': 640, 'duration': 2}):
            inventory = resolve_media({'media': [raw, edited]}, self.root)
        self.assertEqual(inventory['raw']['source_asset_id'], inventory['edited']['source_asset_id'])


if __name__ == '__main__':
    unittest.main()
