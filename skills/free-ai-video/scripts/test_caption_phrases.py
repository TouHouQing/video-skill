import unittest
from voice import chunks


class CaptionReadingUnits(unittest.TestCase):
    def test_connector_does_not_flash_as_its_own_caption(self):
        text='所以，先看结果，再决定要不要换。'
        parts=chunks(text)
        self.assertNotIn('所以，',parts)
        self.assertEqual(''.join(parts),text)
        self.assertTrue(all(len(p)<=25 for p in parts))

    def test_long_clause_is_preserved_when_broken_to_fit(self):
        text='这是一个没有中间标点但是仍然需要完整保留全部文字和最后数字六十五点七的长句子。'
        parts=chunks(text)
        self.assertEqual(''.join(parts),text)
        self.assertTrue(all(len(p)<=25 for p in parts))


if __name__=='__main__':unittest.main()
