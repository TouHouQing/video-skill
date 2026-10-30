"""Observable edit/approval regressions; integration rendering is in smoke_edit.py."""
import copy
from pathlib import Path
import tempfile
import unittest
from factory import validate, produce
from edit_plan import plan


def project(mode='hybrid'):
    data={'title':'编辑验证','angle':'测试素材，不作为产品能力演示', 'visual_mode':mode,
          'sources':[{'id':'official','label':'资料','url':'https://playwright.dev/python/docs/videos',
                      'claims':['浏览器可以保存实际录制视频'],'capture':False}],
          'media':[{'id':'capture','type':'video','path':'capture.mp4','rights':{'kind':'owned'}}],
          'scenes':[]}
    for i in range(3):
        kind='video' if i==0 else 'motion'
        shot={'id':f'shot-{i}','type':kind,'duration':1}
        if kind=='video':
            shot.update(media_id='capture',source_in=2,source_out=8,speed='auto')
        else:
            shot['motion']={'words':['真实操作','核对结果']}
        data['scenes'].append({'id':f'scene-{i}','kind':'evidence','headline':'验证','narration':'这是测试。',
                               'source_ids':['official'],'shots':[shot]})
    return data


class EditBehavior(unittest.TestCase):
    def test_no_silent_cards_substitution(self):
        data=project('screencast');data['scenes'][0]['shots']=[]
        with self.assertRaisesRegex(ValueError,'actual shots'):
            validate(data)

    def test_public_video_requires_usage_rights(self):
        data=project();data['media'][0]['rights']={'kind':'licensed','source_url':'https://example.com'}
        with self.assertRaisesRegex(ValueError,'license_url'):
            validate(data)

    def test_timeline_uses_actual_narration_and_selected_media(self):
        data=validate(project())
        clocks=[{'start':i*3,'duration':3} for i in range(3)]
        shots=plan(data,clocks,{'capture':{'duration':12,'path':'test.mp4'}})
        self.assertAlmostEqual(shots[0]['effective_speed'],2)
        self.assertEqual([(s['start'],s['end']) for s in shots],[(0,3),(3,6),(6,9)])

    def test_short_footage_cannot_silently_freeze(self):
        data=project();data['scenes'][0]['shots'][0].update(source_in=0,source_out=1,speed=1)
        with self.assertRaisesRegex(ValueError,'refusing to freeze'):
            plan(data,[{'start':i*3,'duration':3} for i in range(3)],{'capture':{'duration':12}})

    def test_camera_cannot_move_outside_actual_source(self):
        data=project();data['scenes'][0]['shots'][0]['camera']={'end':[.9,0,.5,1]}
        with self.assertRaisesRegex(ValueError,'Camera'):
            validate(data)

    def test_subsecond_narration_boundaries_do_not_drift(self):
        data=project()
        clocks=[{'start':i*2.292,'duration':2.292} for i in range(3)]
        shots=plan(data,clocks,{'capture':{'duration':12}})
        self.assertAlmostEqual(shots[-1]['end'],6.876)
        self.assertTrue(all(abs(shots[i]['end']-shots[i+1]['start'])<1e-9 for i in range(2)))

    def test_custom_viewer_is_not_target_app_operation(self):
        data=project();data['requirements']={'real_operation':True}
        data['media'][0].update(role='result_viewer',rights={'kind':'original_capture'})
        with self.assertRaisesRegex(ValueError,'custom result viewer'):
            validate(data)

    def test_recutting_one_stock_source_is_not_two_sources(self):
        data=project();data['requirements']={'stock_montage_sources':2}
        data['media'][0].update(role='b_roll',rights={'kind':'licensed','source_url':'https://example.com/one',
            'license':'Test license','license_url':'https://example.com/license'})
        with self.assertRaisesRegex(ValueError,'distinct footage sources'):
            validate(data)

    def test_approval_blocks_audio_and_video_before_output_creation(self):
        import json
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);data=project();data['approval_status']='awaiting_user'
            source=root/'project.json';source.write_text(json.dumps(data),'utf-8')
            with self.assertRaisesRegex(ValueError,'awaiting user approval'):
                produce(source,root/'must-not-exist')
            self.assertFalse((root/'must-not-exist').exists())


if __name__=='__main__':
    unittest.main()
