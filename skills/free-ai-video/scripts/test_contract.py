"""Behavioral checks for cost boundaries and factual-reference integrity."""
import copy
import unittest
from unittest.mock import patch
from factory import validate
from voice import chunks


def project():
    return {'title': '检查', 'angle': '可核验的工具介绍',
            'sources': [{'id': 'official', 'url': 'https://github.com/rany2/edge-tts', 'label': '官方项目', 'claims': ['提供语音工具']}],
            'scenes': [{'id': str(i), 'kind': 'evidence', 'headline': '免费工具', 'narration': '这是实际说明。', 'source_ids': ['official']} for i in range(3)]}


class CostAndSourceContract(unittest.TestCase):
    def test_comparison_rejects_a_misleading_axis(self):
        data=project();data['visual_mode']='motion'
        for i,scene in enumerate(data['scenes']):
            scene['shots']=[{'id':f'chart-{i}','type':'motion','motion':{'layout':'bars','title':'任务成功率','max_value':100,
                'rows':[{'label':'A','value':65.7},{'label':'B','value':66.4}]}}]
        validate(data)
        data['scenes'][0]['shots'][0]['motion']['min_value']=60
        with self.assertRaisesRegex(ValueError,'zero baseline'):
            validate(data)

    def test_comparison_rejects_nonfinite_data(self):
        data=project();data['visual_mode']='motion'
        data['scenes'][0]['shots']=[{'id':'chart','type':'motion','motion':{'layout':'bars','title':'成功率','max_value':100,
            'rows':[{'label':'A','value':float('nan')},{'label':'B','value':66.4}]}}]
        with self.assertRaisesRegex(ValueError,'finite'):
            validate(data)

    def test_pricing_table_requires_every_cell(self):
        data=project();data['visual_mode']='motion'
        data['scenes'][0]['shots']=[{'id':'table','type':'motion','motion':{'layout':'table','title':'API单价',
            'columns':['输入','输出'],'rows':[{'label':'A','cells':['$2','$10']},{'label':'B','cells':['$4']}]}}]
        with self.assertRaisesRegex(ValueError,'every column'):
            validate(data)

    def test_news_without_research_stops_before_speech(self):
        import tempfile,json
        from pathlib import Path
        from factory import produce
        data=project();data['content_type']='ai_news'
        with tempfile.TemporaryDirectory() as tmp,patch('voice.prepare') as speech:
            source=Path(tmp)/'project.json';source.write_text(json.dumps(data),'utf-8')
            output=Path(tmp)/'output'
            with self.assertRaisesRegex(ValueError,'research_file'):
                produce(source,output)
            speech.assert_not_called();self.assertFalse(output.exists())

    def test_news_rejects_claims_outside_declared_sources(self):
        import tempfile,json
        from pathlib import Path
        from newsroom import load_research
        data=project();data.update(content_type='ai_news',research_file='research.json')
        research={'recorded_at':'2026-10-25','searches':[{'query':'actual query','result_urls':['https://example.org/announcement']}],
            'candidates':[{'id':'selected','primary_sources':['https://example.org/announcement']}],
            'selected_id':'selected','selection_reason':'current launch','claim_checks':[{'claim':'released','source_url':'https://example.org/unlisted'}],
            'media_plan':[{'use':'source excerpt'}]}
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp)/'research.json').write_text(json.dumps(research),'utf-8')
            with self.assertRaisesRegex(ValueError,'claim checks'):
                load_research(data,Path(tmp)/'project.json')

    def test_explicit_ming_failure_does_not_change_provider(self):
        from voice import prepare
        import tempfile
        data=project();data['voice_mode']='ming'
        with tempfile.TemporaryDirectory() as folder, \
             patch('ming.prepare_records',side_effect=RuntimeError('local model unavailable')), \
             patch('voice.one') as other_voice:
            with self.assertRaisesRegex(RuntimeError,'local model unavailable'):
                prepare(data,folder)
            other_voice.assert_not_called()

    def test_paid_endpoint_is_rejected(self):
        data = project()
        data['sources'][0]['url'] = 'https://api.openai.com/v1/responses'
        with self.assertRaisesRegex(ValueError, 'paid'):
            validate(data)

    def test_unverified_source_reference_is_rejected(self):
        data = project()
        data['scenes'][1]['source_ids'] = ['invented']
        with self.assertRaisesRegex(ValueError, 'Unresolved'):
            validate(data)

    def test_duplicate_scene_is_rejected(self):
        data = project()
        data['scenes'][2]['id'] = '0'
        with self.assertRaisesRegex(ValueError, 'Duplicate scene'):
            validate(data)

    def test_caption_splitting_preserves_spoken_text(self):
        text = '做AI短视频，一定要买接口吗？这条视频就是免费流程的实际结果。'
        parts = chunks(text, 14)
        self.assertEqual(''.join(parts), text)
        self.assertTrue(all(0 < len(part) <= 14 for part in parts))

    def test_odd_portrait_dimensions_are_rejected(self):
        data = project()
        data.update(width=721, height=1280)
        with self.assertRaisesRegex(ValueError, 'dimensions'):
            validate(data)


if __name__ == '__main__':
    unittest.main()
