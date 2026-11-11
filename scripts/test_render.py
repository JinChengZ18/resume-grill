"""Regression checks for thematic placement, paired answers and legacy payloads."""
import copy
import unittest
import render


def fixture(lang='zh'):
    cards=[]
    for n in ('Q1','Q2'):
        cards.append(dict(n=n,title=n+' topic',anchor='project',ladder=[dict(level='L1',q=n+' opening',answer=n+' opening answer')],ask=n+' decision',ask_answer=n+' decision answer',probe=n+' boundary',probe_answer=n+' boundary answer',good=['legacy notes'],**{'pass':['reasoning']},tell='clarify',followups=[dict(q=n+' extension',answer=n+' extension answer',when='after a claim')]))
    return dict(meta=dict(lang=lang),candidates={'A':dict(name='Candidate',cards=cards,probes=[dict(tag='Availability',q='Start date?',answer='To be confirmed')])})


class RenderTests(unittest.TestCase):
    def test_followup_stays_in_parent_theme(self):
        p=fixture();s=render.md_guide(p,render.LABELS['zh'])
        self.assertLess(s.index('Q1 extension'),s.index('### Q2'))
        self.assertLess(s.index('Q2 extension'),s.index('Start date?'))
        for card in p['candidates']['A']['cards']:
            for q,a in [(card['ladder'][0]['q'],card['ladder'][0]['answer']),(card['ask'],card['ask_answer']),(card['probe'],card['probe_answer']),(card['followups'][0]['q'],card['followups'][0]['answer'])]:
                self.assertLess(s.index(q),s.index(a))
                self.assertEqual(s.count(a),1)

    def test_legacy_answers_still_render(self):
        p=fixture()
        for c in p['candidates']['A']['cards']:
            c['ladder'][0].pop('answer');c.pop('ask_answer');c.pop('probe_answer');c.pop('followups')
        self.assertIn('legacy notes',render.md_guide(p,render.LABELS['en']))

    def test_bilingual_and_script_boundary(self):
        for lang in ('zh','en'):
            p=fixture(lang);p['candidates']['A']['cards'][0]['followups'][0]['answer']='</script><script>bad()</script>'
            s=render.inject('qa_cards.html.tmpl',p,'Test',render.LABELS[lang])
            self.assertNotIn('</script><script>bad()',s)
            self.assertIn(render.LABELS[lang]['sample_answer'],s)
            self.assertNotIn('/*__PAYLOAD__*/{}',s)


if __name__=='__main__':
    unittest.main()
