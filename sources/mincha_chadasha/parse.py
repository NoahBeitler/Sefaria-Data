import django
django.setup()
import sys
path_to_add = '/Users/yishaiglasner/sefaria/ai-chatbot/server/chat/V2/agent'
sys.path.append(path_to_add)
import csv
import re
from sefaria.model import *
from source_sheet_serializer import serialize_source_sheet_payload
from sefaria.sheets import save_sheet

linker = library.get_linker("he")
SOURCES = []
try:
    with open('solved_refs.csv') as fp:
        SOLVED = list(csv.DictReader(fp))
except FileNotFoundError:
    pass

def validate_sources(rows):
    source = ''
    for row in rows:
        category = row['category']
        if source == 'start' and category != 'Source-Text':
            row['problem'] = f'{category} after Source'
        if not source and category == 'Source-Text':
            row['problem'] = f'Source-Text not afte Source'
        if category == 'Source':
            source = 'start'
        elif category == 'Source-Text':
            source = 'cont'
        else:
            source = ''

def get_grouped_rows(data):
    sheets = []
    for row in data:
        if row['category'] == 'H1':
            sheets.append([])
        sheets[-1].append(row)
    return sheets

def parse_string(string):
    string = ' '.join(string.split())
    string = string.replace('<span>', '<span style="background-color: #e6dabc;">')
    expected_chars = ' \u0590-\u05ea0-9"\./;=:!\-–\(\)\[\]\?\','
    text_witout_html = re.sub('<[^>]+>', '', string)
    if re.search(rf'[^{expected_chars}]', text_witout_html):
        print(111, string, re.findall(rf'[^{expected_chars}]', text_witout_html))
    expected_tags = 'h1|b|small|span'
    if re.search(f'<(?!/?({expected_tags}))', string):
        print(222, string)
    return string

def get_linker_result(string):
    # import requests
    # url = f'https://www.sefaria.org/api/find-refs'
    # payload = {
    #     "text": {
    #         "body": string,
    #         "title": ""
    #     },
    #     "lang": "he"
    # }
    # res = requests.post(url, json=payload)
    # refs = list(res.json()['body']['refData'])
    return linker.link(string, with_failures=True)

def manipulate_quotation(quotation):
    quotation = re.sub(':$', '', quotation)
    return re.split(', [בה]משנה ', quotation)[0]

def get_ref_map(potential_refs, sep=None):
    SEP = sep or '\nטקסט זה אינו הפניה. עד כאן.\n'
    combined_string = SEP.join(potential_refs)
    linked_doc = get_linker_result(combined_string)

    # Compute char range of each original string in combined_string
    string_ranges = []
    pos = 0
    for s in potential_refs:
        string_ranges.append((pos, pos + len(s)))
        pos += len(s) + len(SEP)

    # Map each ResolvedRef to its original string index
    ref_map = {i: [] for i in range(len(potential_refs))}
    for resolved_ref in linked_doc.resolved_refs:
        ref_start, ref_end = resolved_ref.raw_entity.char_indices
        matched = [i for i, (s_start, s_end) in enumerate(string_ranges)
                   if s_start <= ref_start < s_end or s_start < ref_end <= s_end]
        if len(matched) != 1:
            caught_string = combined_string[ref_start:ref_end]
            print(f"WARNING: ref {resolved_ref} (caught string: '{caught_string}') spans across strings or matched {len(matched)} strings: {matched}")
            continue
        ref_map[matched[0]].append(resolved_ref)
    assert len(ref_map) == len(potential_refs), f'ref map is of length {len(ref_map)} and quotations of length {len(potential_refs)}'
    return ref_map

def handle_quotations(sources):
    quotations = [x for x in sources if 'source' in x]
    potential_refs = [manipulate_quotation(q['source']) for q in quotations]
    ref_map = get_ref_map(potential_refs)

    ibid_hist = []
    for i, v in ref_map.items():
        q = quotations[i]
        # After having solved refs file!
        if SOLVED:
            row = SOLVED.pop(0)
            new_ref = row['ref'] or row['new']
        else:
            new_ref = ''
        if new_ref:
            new_ref = Ref(new_ref)

        # before having solved refs file
        k = potential_refs[i]
        # print(k)
        # for r in v:
        #     if getattr(r, 'ref', None):
        #         print(r.ref)
        #     else:
        #         print(r.get_debug_spans())
        refs = {getattr(r, 'ref', None) for r in v}
        refs = {r for r in refs if r}
        ibid = 'IBID' in [resolved.get_debug_spans()[0]['contextType'] for resolved in v]
        if len(refs) == 1 and ibid:
            ibid_hist.append(q['source'])
        else:
            ibid_hist = []
        if not refs:
            if ibid:
                sep = '\nזה ציטוט של מקור שהוא יותר ארוך מהרגיל. עד כאן לשונו.\n'
                ibid_ref_map = get_ref_map(ibid_hist)
                values = list(ibid_ref_map.values())
                last = values[-1] if values else []
                refs = [r.ref for r in last if getattr(r, 'ref', None)]
            else:
                linked_doc = get_linker_result(manipulate_quotation(q['source']))
                refs = [r.ref for r in linked_doc.resolved_refs if getattr(r, 'ref', None)]
        if len(refs) > 1:
            print(7777)

        SOURCES.append({'source': q['source'], 'text': q['text'], 'ref': ''})
        text = '<br>'.join(q['text'])
        if len(refs) == 1 or new_ref:
            ref = new_ref if new_ref else refs.pop()
            q['heRef'] = q.pop('source')
            q['ref'] = ref.normal()
            q['text'] = {'he': text, 'en': ref.text('en').as_string()}
            SOURCES[-1]['ref'] = q['ref']
        else:
            q['outsideText'] = f'<p><span style="color: #999999;"><b>{q["source"]}</b></span><br>{text}</p>'
            if v and v[0].is_ambiguous:
                SOURCES[-1]['ref'] = 'ambiguous'
    return ref_map

def parse_sheet(rows):
    title = parse_string(rows.pop(0)['text'])
    sources = []
    source = {}
    for row in rows:
        category = row['category']
        text = parse_string(row['text'])
        if source and category != 'Source-Text':
            sources.append(source)
            source = {}
        if category == 'Source':
            source = {'source': text, 'text': []}
        elif category == 'Source-Text':
            source['text'].append(text)
        else:
            if category == 'H2':
                text = f'<h1>{text}</h1>'
            elif category == 'Sub-heading':
                text = f'<b>{text}</b>'
            else:
                text = f'<em>{text}</em>'
            sources.append({'outsideText': f'<p>{text}</p>'})
    if source:
        sources.append(source)
    handle_quotations(sources)
    return {'title': title, 'summary': '', 'sources': sources}

with open('minchah chadasha parsed - input.csv') as fp:
    data = list(csv.DictReader(fp))
validate_sources(data)
sheets = get_grouped_rows(data)
user_id = 270678
for i, sheet in enumerate(sheets):
    sheet = parse_sheet(sheet)
    sheet = serialize_source_sheet_payload(**sheet)
    sheet['status'] = 'public'
    sheet['group'] = 'מנחה חדשה'
    sheet['displayedCollection'] = 'מנחה-חדשה'
    save_sheet(sheet, user_id)

with open('rows_categories_validation_report.csv', 'w') as fp:
    w = csv.DictWriter(fp, fieldnames=['category', 'text', 'problem'])
    w.writeheader()
    for row in data:
        w.writerow(row)

with open('find_refs_report.csv', 'w') as fp:
    w = csv.DictWriter(fp, fieldnames=['source', 'text', 'ref'])
    w.writeheader()
    for row in SOURCES:
        w.writerow(row)

print(len([r for r in SOURCES if r['ref'] and r['ref'] != 'ambiguous']), len([r for r in SOURCES if r['ref'] == 'ambiguous']))

