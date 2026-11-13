"""Regression checks for thematic placement, paired answers, legacy payloads and the extra modes."""
import copy
import json
import os
import re
import tempfile
import unittest
import render
import kit


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
        self.assertEqual(set(files),{'demo_index.html','demo_kit_A.html','demo_guide.md',
                                     'demo_weakness.html','demo_resume.html','demo_jd.html'})
        for name,text in files.items():
            for href in local_hrefs(text):
                self.assertTrue(os.path.exists(os.path.join(d,href)),(name,href))
        for name in ('demo_index.html','demo_weakness.html','demo_resume.html','demo_jd.html'):
            self.assertIn(render.LABELS['zh']['export_pdf'],files[name])
        self.assertIn(kit.T['zh']['print'],files['demo_kit_A.html'])
        self.assertIn('demo_kit_A.html',files['demo_index.html'])

    def test_legacy_views_on_request(self):
        p=mode_fixture();p['meta']['views']=['guide','cards','scorecard']
        d,files=self.render(p)
        self.assertTrue({'demo_guide.html','demo_qa_cards.html','demo_scorecard.html','demo_kit_A.html'}<=set(files))
        for name in ('demo_guide.html','demo_qa_cards.html'):
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
        p=mode_fixture();p['meta']['views']=['guide','cards','scorecard']
        p['meta']['links']=[dict(label='old',href='other_slug_scorecard.html'),dict(label='site',href='https://example.com')]
        d,files=self.render(p)
        self.assertNotIn('other_slug_scorecard.html',files['demo_qa_cards.html'])
        self.assertIn('https://example.com',files['demo_guide.html'])

    def test_label_sets_match(self):
        self.assertEqual(set(render.LABELS['zh']),set(render.LABELS['en']))


def kit_fixture():
    """A payload that uses every interviewer-kit field."""
    p=fixture()
    A=p['candidates']['A'];A['name']='Candidate · role'
    for i,c in enumerate(A['cards']):
        c.update(prio='must' if i==0 else 'opt',minutes=8,dims=['D1'],focus='why it matters',flags=['red flag %d'%i],
                 fallback='walk me through one case',transfer='ask',ask_when='if solid',probe_when='if strong',
                 ask_listen=[dict(t='transfer point',**{'pass':True})],probe_listen=[dict(t='probe point',**{'pass':False})])
        c['ladder'][0]['listen']=[dict(t='core point %d'%i,**{'pass':True}),dict(t='bonus point',**{'pass':False})]
        c['followups'][0]['listen']=[]
    A['probes'][0]['listen']='concrete date'
    A['kit']=dict(role='Agent engineer',summary='one line',decide=['Does he own the design?'],
                  verify=[dict(text='metric definition',when='Q1')],notes=['be polite'],time_note='drop Q2 if short',
                  dims=[dict(id='D1',name='Design',kind='core',**{'from':['Q1','Q2']},a4='great',a3='good',a2='weak',a1='poor'),
                        dict(id='D2',name='Transfer',kind='core',**{'from':['Q1–Q2 situational']},a4='x',a3='y',a2='z',a1='w'),
                        dict(id='D3',name='Credibility',kind='gate',**{'from':['Opener','Wrap-up']},a4='x',a3='y',a2='z',a1='w')],
                  rule={'pass':'all core >= 3','fail':'any core = 1','hold':'else'},role_toggle=dict(dim='',label=''),
                  next_round=['design exercise'],opener_minutes=4,wrap_minutes=6,
                  opener_listen=[dict(t='scope is clear',**{'pass':True})],opener_flags=['vague scope'])
    p['meta']=dict(lang='en',date='2026-11-13',plan=dict(minutes=26,perQuestion=8,opener=4,buffer=6,depth='standard'))
    return p


class KitTests(unittest.TestCase):
    def page(self,payload,cid='A'):
        d=tempfile.mkdtemp()
        render.render_all(payload,d,'demo')
        return read(os.path.join(d,'demo_kit_%s.html'%cid))

    def test_no_jump_links_and_answers_follow_questions(self):
        s=self.page(kit_fixture())
        self.assertNotIn('<a ',s)
        for c in kit_fixture()['candidates']['A']['cards']:
            for q,a in [(c['ladder'][0]['q'],c['ladder'][0]['answer']),(c['ask'],c['ask_answer']),(c['probe'],c['probe_answer'])]:
                qi,ai=s.index(q),s.index(a)
                self.assertLess(qi,ai)
                self.assertIn('<details class="ans">',s[qi:ai])
                self.assertEqual(s.count(a),1)
        self.assertNotIn('<details class="ans" open',s)

    def test_kit_fields_render(self):
        s=self.page(kit_fixture())
        for text in ('Does he own the design?','metric definition','drop Q2 if short','core point 0','transfer point',
                     'red flag 1','walk me through one case','if solid','design exercise','concrete date','scope is clear','vague scope'):
            self.assertIn(text,s)
        data=json.loads(re.search(r'id="kitdata">(.*?)</script>',s,re.S).group(1))
        self.assertEqual([g['key'] for g in data['segs']],['OP','Q1','Q2','W'])
        self.assertEqual(data['segs'][-1]['end'],26)
        self.assertTrue([d for d in data['dims'] if d['id']=='D2'][0]['transfer'])
        self.assertEqual(data['dims'][2]['qs'],['OP','W'])

    def test_legacy_payload_falls_back(self):
        s=self.page(fixture())
        data=json.loads(re.search(r'id="kitdata">(.*?)</script>',s,re.S).group(1))
        self.assertEqual([d['kind'] for d in data['dims']],['core','core','gate'])
        self.assertIn('reasoning',s)          # pass -> pass-line listen point
        self.assertIn('clarify',s)            # tell -> danger signal
        self.assertTrue(data['themes'][1]['subs'][0]['listen'][0]['pass'])

    def test_script_boundary_and_resume_embed(self):
        p=kit_fixture();p['candidates']['A']['cards'][0]['title']='</script><script>bad()</script>'
        d=tempfile.mkdtemp()
        png=b'\x89PNG\r\n\x1a\n'+b'0'*32
        with open(os.path.join(d,'cv.png'),'wb') as f: f.write(png)
        p['candidates']['A']['resume']='cv.png'
        render.render_all(p,d,'demo')
        s=read(os.path.join(d,'demo_kit_A.html'))
        self.assertNotIn('</script><script>bad()',s)
        self.assertIn('data:image/png;base64,',s)
        self.assertNotIn('href="cv.png"',s)


if __name__=='__main__':
    unittest.main()
