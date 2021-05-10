# -*- coding: utf-8 -*-

__author__ = 'stevenkaplan'
from sources.functions import *
from sefaria.tracker import add
from sefaria.model import *
from sefaria.helper.schema import *
# from data_utilities.dibur_hamatchil_matcher import match_text
from research.mesorat_hashas_sefaria.mesorat_hashas import *
import bleach
import os
import time
from sefaria.profiling import *

def combine_lines(base_ref, lines, results):
    first = base_ref + ":1"
    actual_matches = [r for r in results if r]
    if not actual_matches:
        #print("Found nothing in {}".format(ref))
        actual_matches = [Ref(base_ref).as_ranged_segment_ref()]
        for i, result in enumerate(results):
            results[i] = Ref(base_ref).as_ranged_segment_ref()
    else:
        for i, result in enumerate(results):
            if result and i == 0:
                break
            elif result:
                for j in range(i):
                    results[j] = Ref(first).to(actual_matches[0])
                break

    new_segments = []
    new_links = []
    current_segment = ""
    prev_result = None
    for line, result in zip(lines, results):
        if result and current_segment and result != prev_result:
            new_segments.append(current_segment)
            new_links.append(prev_result)
            current_segment = line + ". " if not line.endswith(":") else line+"<br/>"
        else:
            current_segment += line + ". " if not line.endswith(":") else line+"<br/>"

        if result:
            prev_result = result

    if current_segment:
        current_segment = current_segment.replace("..", ".", -1)
        new_segments.append(current_segment)
        new_links.append(prev_result)
    return (new_segments, new_links)


def delete_old_links():
    indices = """Rabbeinu Chananel on Sanhedrin""".splitlines()
    relevant_indices = set()

    start_at = "Yoma"
    starting = False
    generated_by = set()
    chananel = LinkSet({"refs": {"$regex": "^Rabbeinu Chananel on"}, "generated_by": {"$regex": "sterling"}})
    nissim = LinkSet({"refs": {"$regex": "^Rav Nissim Gaon on"}, "generated_by": {"$regex": "sterling"}})
    chananel.delete()
    nissim.delete()

    print(nissim.count())
    print(chananel.count())
    with open("chananel+gaon.csv", 'w') as f:
        writer = csv.writer(f)
        for l in list(chananel)+list(nissim):
            ref1, ref2 = l.refs
            ref1_ghost = Ref(ref1).text('he').text in [[], ""]
            ref2_ghost = Ref(ref2).text('he').text in [[], ""]
            ghost = ref1_ghost or ref2_ghost
            if ghost:
                ref = ref1 if ref1.startswith("Rabbeinu") or ref1.startswith("Rav") else ref2
                i = Ref(ref).index.title
                relevant_indices.add(i)
            writer.writerow([l.refs[0], l.refs[1], ghost])
    count = 0
    for i in relevant_indices:
        print(i)
        count += 1
        delete_link(i, server="https://germantalmud.cauldron.sefaria.org")
        time.sleep(count*10)

def just_post_as_is(ref, results, text):
    links = []
    for m, match in enumerate(results):
        if match:
            comm_ref = "{}:{}".format(ref.top_section_ref(), 1 + m)
            link = {"refs": [comm_ref, match.normal()], "generated_by": "redo_chananel", "type": "Commentary",
                    "auto": True}
            links.append(link)
    if daf_as_num not in new_text:
        new_text[daf_as_num] = []
    lines = text.split(". ")
    for n, line in enumerate(lines):
        if line.endswith(":"):
            new_text[daf_as_num].append(line)
        elif not line.endswith("."):
            new_text[daf_as_num].append(line + ".")
        else:
            assert n == len(lines) - 1
            new_text[daf_as_num].append(line)

    return links, new_text

def dher(str):
    dh = " ".join(str.split()[:3])
    return dh

def base_tokenizer(str):
    return strip_nekud(bleach.clean(str, tags=[], strip=True)).split()


def create_new_links():
    links = []
    links_dict = {}
    chananel = library.get_indexes_in_category("Rabbeinu Chananel", include_dependant=True)
    nissim = library.get_indexes_in_category("Rav Nissim Gaon", include_dependant=True)
    for title in chananel:
        if "Avodah Zarah" not in title:
            continue
        print(title)
        new_text = {}
        index = library.get_index(title)
        if "Bavli" not in index.categories:
            continue

        for sec_ref in library.get_index(title).all_section_refs():
            # if "90a" not in sec_ref.normal():
            #     continue
            for ref in sec_ref.all_segment_refs():
                daf = ref.top_section_ref().normal().split()[-1]
                daf_as_num = ref.sections[0]
                base_ref = index.base_text_titles[0] + " " + daf
                base_text = Ref(base_ref).text('he')
                text = ref.text('he').text
                text = text.replace(": ", ":. ")
                lines = [" ".join(bleach.clean(line, strip=True).split()) for line in text.split(". ")]
                results = match_ref(base_text, lines, base_tokenizer, dh_extract_method=dher)
                if results["matches"][0] is None:
                    results = match_ref(base_text, lines, base_tokenizer, dh_extract_method=dher, prev_matched_results=results["match_word_indices"])
                for m, match in enumerate(results["matches"]):
                    if match is None and (m == 0):
                        start = 0
                        while start + 3 < len(lines[m].split()) and results["matches"][0] is None:
                            line = " ".join(lines[m].split()[start+3:])
                            result = match_ref(base_text, [line], base_tokenizer, dh_extract_method=dher)
                            results["matches"][0] = result["matches"][0]
                            start += 3
                new_segments, new_links = combine_lines(base_ref, lines, results["matches"])
                daf_as_num = ref.sections[0]
                if daf_as_num not in new_text:
                    new_text[daf_as_num] = []
                new_text[daf_as_num] += new_segments
                for m, match in enumerate(new_links):
                    rabbeinu_ref = "{} {}:{}".format(title, daf, m+1)
                    links.append({"refs": [rabbeinu_ref, match.normal()], "generated_by": "redo_chananel",
                                  "type": "Commentary", "auto": True})
                    if rabbeinu_ref in links_dict:
                        print()
                    links_dict[rabbeinu_ref] = links[-1]
        new_text = convertDictToArray(new_text)
        send_text = {
            "text": new_text,
            "language": "he",
            "versionTitle": "Vilna Edition",
            "versionSource": "http://primo.nli.org.il/primo-explore/fulldisplay?vid=NLI&docid=NNL_ALEPH001300957&context=L"
        }
        #post_text(title, send_text, server="https://www.sefaria.org")
        post_link_in_steps(links, server="https://germantalmud.cauldron.sefaria.org")
        print(links)


def func_to_profile():
    with open("links.json", 'r') as fp:
        links = json.load(fp)

    before = time.time()
    #result = post_link(links, server="http://localhost:8000")
    for l, our_link in enumerate(links):
        'Link().load({"$or": [{"refs": self.refs}, {"refs": [self.refs[1], self.refs[0]]}]})'
        try:
            our_link["refs"][1] = our_link["refs"][1].split(":")[0]
            add(1, Link, our_link)
        except Exception as e:
            pass
    # with open('result.html', 'w') as f:
    #     try:
    #         f.writelines(result)
    #     except:
    #         print(result)
    after = time.time()
    print(after - before)

#delete_old_links()
#delete_link("Rabbeinu Chananel on Sanhedrin", server="https://germantalmud.cauldron.sefaria.org")

create_new_links()
#prof('func_to_profile()')
#create_new_links()