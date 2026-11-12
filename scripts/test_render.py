"""Regression checks for thematic placement, paired answers, legacy payloads and the extra modes."""
import copy
import os
import re
import tempfile
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


def mode_fixture(lang='zh'):
    """fixture() plus the three extra-mode sections from reference/modes-spec.md."""
    p=fixture(lang);A=p['candidates']['A']
    A['weakness']=dict(summary='overall',keep=['keep this'],actions=['act first'],items=[
        dict(id='W2',severity='low',category='low cat',quote='q2',issue='i2',why='w2',followups=[],fix='f2',rewrite=''),
        dict(id='W1',severity='high',category='high cat',quote='<script>alert(1)</script>',issue='i1',why='w1',
             followups=[dict(q='weak follow-up',answer='weak answer',when='weak when')],fix='f1',rewrite='用【待补充：数字】说明')])
    A['resume_opt']=dict(summary='plan',questions=[dict(id='A1',q='ask the user',why='because',affects=['E1'])],
        edits=[dict(id='E1',section='headline',before='old line',after='[TBD: metric] new line',why='clearer')],
        optimized=dict(name='Name',headline='Headline',contact='【待补充：邮箱】',
                       sections=[dict(title='Work',entries=[dict(title='Role',org='Org',period='2025',bullets=['did x'])])]))
    A['jd_match']=dict(jd_title='Backend role',jd_source='https://example.com/jd',summary='fit',
        requirements=[dict(id='R1',text='python',priority='must',status='met',evidence=['used python'],note='n1',action='a1'),
                      dict(id='R2',text='years',priority='must',status='gap',evidence=[],note='n2',action='a2')],
        keywords=dict(present=['Python'],missing=['Go']),gaps=[dict(gap='years gap',plan='p',talk='t')],
        questions=[dict(q='jd question',answer='jd answer',when='jd when')])
    return p


def read(path):
    with open(path,encoding='utf-8') as f:
        return f.read()


def local_hrefs(text):
    return [h for h in re.findall(r'href="([^"#$]+)"',text) if not h.startswith(('http:','https:'))]


class ModeTests(unittest.TestCase):
    def render(self,payload,slug='demo'):
        d=tempfile.mkdtemp()
        lang,written=render.render_all(payload,d,slug)
        return d,{os.path.basename(w):read(w) for w in written}

    def test_all_pages_written_and_linked(self):
        d,files=self.render(mode_fixture())
        self.assertEqual(set(files),{'demo_index.html','demo_guide.html','demo_qa_cards.html','demo_scorecard.html',
                                     'demo_guide.md','demo_weakness.html','demo_resume.html','demo_jd.html'})
        for name,text in files.items():
            for href in local_hrefs(text):
                self.assertTrue(os.path.exists(os.path.join(d,href)),(name,href))
        for name in ('demo_index.html','demo_guide.html','demo_weakness.html','demo_resume.html','demo_jd.html','demo_qa_cards.html'):
            self.assertIn(render.LABELS['zh']['export_pdf'],files[name])
        self.assertIn('demo_index.html',files['demo_scorecard.html'])

    def test_only_present_sections_written(self):
        p=mode_fixture();A=p['candidates']['A']
        for k in ('cards','probes','resume_opt','jd_match'): A.pop(k)
        d,files=self.render(p)
        self.assertEqual(set(files),{'demo_index.html','demo_weakness.html'})
        self.assertNotIn('demo_guide.html',files['demo_index.html'])

    def test_escaping_placeholders_and_order(self):
        d,files=self.render(mode_fixture('en'))
        w=files['demo_weakness.html']
        self.assertNotIn('<script>alert(1)</script>',w)
        self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;',w)
        self.assertIn('<mark class="tbd">【待补充：数字】</mark>',w)
        self.assertLess(w.index('high cat'),w.index('low cat'))
        self.assertLess(w.index('weak follow-up'),w.index('weak answer'))
        r=files['demo_resume.html']
        self.assertIn('data-print="resume"',r)
        self.assertIn('<mark class="tbd">[TBD: metric]</mark>',r)
        self.assertIn(render.LABELS['en']['tbd_left'].replace('{n}','1'),r)
        j=files['demo_jd.html']
        self.assertIn('%s 1</span>'%render.LABELS['en']['status_met'],j)
        self.assertIn('%s 1</span>'%render.LABELS['en']['status_gap'],j)
        self.assertIn('href="https://example.com/jd"',j)

    def test_hand_written_links_to_own_pages_are_replaced(self):
        p=mode_fixture();p['meta']['links']=[dict(label='old',href='other_slug_scorecard.html'),dict(label='site',href='https://example.com')]
        d,files=self.render(p)
        self.assertNotIn('other_slug_scorecard.html',files['demo_qa_cards.html'])
        self.assertIn('https://example.com',files['demo_guide.html'])

    def test_label_sets_match(self):
        self.assertEqual(set(render.LABELS['zh']),set(render.LABELS['en']))


if __name__=='__main__':
    unittest.main()
