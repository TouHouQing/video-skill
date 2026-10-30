import unittest
from visual_mix import visual_mix


def shot(sid,seconds,kind='video',url='https://example.org/page',source_id=None):
    media={'id':sid,'role':'source_recording' if kind=='video' else 'source_page',
           'sha256':sid,'rights':{'kind':'original_capture' if kind=='video' else 'source_excerpt','source_url':url}}
    if source_id:media['source_asset_id']=source_id
    return {'id':sid,'start':0,'end':seconds,'duration':seconds,'type':kind,'media':media}


class SourceCoverage(unittest.TestCase):
    def test_checks_duration_instead_of_number_of_cuts(self):
        clips=[shot(str(i),1) for i in range(20)]
        clips.append({'id':'slides','type':'motion','start':20,'end':100,'duration':80})
        with self.assertRaisesRegex(ValueError,'coverage failed'):
            visual_mix({'requirements':{'source_material_min_ratio':.9}},clips)

    def test_cropped_views_of_one_original_are_one_asset(self):
        clips=[shot('crop1',5,source_id='same-figure'),shot('crop2',5,source_id='same-figure')]
        with self.assertRaisesRegex(ValueError,'distinct_source_assets'):
            visual_mix({'requirements':{'min_distinct_source_assets':2}},clips)

    def test_screenshots_and_recordings_are_measured_separately(self):
        clips=[shot('recording',70),shot('screenshot',20,'image','https://example.org/figure'),
               {'id':'graphic','type':'motion','start':90,'end':100,'duration':10}]
        result=visual_mix({'requirements':{'source_material_min_ratio':.9,'recording_min_ratio':.65,
                                         'min_distinct_source_assets':2}},clips)
        self.assertTrue(result['passed'])
        self.assertAlmostEqual(result['source_material_ratio'],.9)
        self.assertAlmostEqual(result['recording_ratio'],.7)
        self.assertEqual(result['distinct_source_assets'],2)

    def test_legacy_motion_project_keeps_its_requested_format(self):
        result=visual_mix({},[{'id':'graphic','type':'motion','start':0,'end':10,'duration':10}])
        self.assertTrue(result['passed'])

    def test_source_led_does_not_force_extra_originals_or_cuts(self):
        result=visual_mix({'visual_style':'source_led'},[shot('continuous-inspection',45)])
        self.assertTrue(result['passed'])
        self.assertEqual(result['distinct_source_assets'],1)
        self.assertNotIn('min_distinct_source_assets',result['limits'])


if __name__=='__main__':unittest.main()
