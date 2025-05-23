# encoding=utf-8
import django
from functools import reduce
django.setup()


import unicodecsv, random, bleach
from collections import defaultdict
from sefaria.model import *
from linking_utilities.alt_titles import alt_name_dict , rambam_alt_names
from parsing_utilities.ibid import *
from sefaria.utils.hebrew import strip_nikkud
from sefaria.system.exceptions import BookNameError

import regex as re


def count_regex_in_all_db(pattern='(?:\(|\([^)]*? )שם(?:\)| [^(]*?\))', lang='he', text='all', example_num = 7):
    '''
    This method is for counting testing perepesis,
    :param lang:
    :param text:
    :return:
    '''

    found = []
    category_dict = defaultdict(int)
    shams_dict = defaultdict(list)

    vtitle = None
    ind_done = 0
    if text == 'all':
        indecies = library.all_index_records()
        inds_len = len(indecies)
    else:
        indecies = [library.get_index(text)]
    for iindex, index in enumerate(indecies):
        print("{}/{}".format(iindex, len(indecies)))
        # if index == Index().load({'title': 'Divrei Negidim'}):
        #     continue
        if text == 'all':
            ind_done += 1
            print(ind_done*1.0/inds_len)
        try:
            unit_list_temp = index.nodes.traverse_to_list(lambda n, _: TextChunk(n.ref(), lang,
                                                                                 vtitle=vtitle).ja().flatten_to_array() if not n.children else [])
            st = ' '.join(unit_list_temp)
            shams = re.finditer(pattern, st)
            cat_key = '/'.join(index.categories)
            num_shams = 0
            if shams:
                for s in shams:
                    num_shams += 1
                    curr_sham = s.group()
                    if len(re.split(r'\s+', curr_sham)) > 6:
                        continue
                    shams_dict[cat_key] += [s.group()]

                # print '{} : {}'.format(index, len(shams))
            found.append((index, num_shams))

            category_dict[cat_key] += num_shams

        except:  # sefaria.system.exceptions.NoVersionFoundError:
            # print 'empty {}'.format(index)
            continue
    max_shams = max(dict(found).values())
    for (k, v) in found:
        if v == max_shams:
            max_index = k
    print('max: {} with {}'.format(max_index, max_shams))

    cat_items = sorted(list(category_dict.items()), key=lambda x: x[1])


    for k,v in reversed(cat_items):
        if v == 0:
            continue
        print(k,v)

    sham_items = sorted(list(shams_dict.items()), key=lambda x: x[1])

    for k, v in reversed(sham_items):
        if v == 0:
            continue
        print(k, v)


    cat_sham_dict = defaultdict(list)
    for ci in cat_items:
        population = shams_dict[ci[0]]
        cat_sham_dict[ci] = random.sample(population, min(len(population), example_num))

    cat_sham_items = sorted(list(cat_sham_dict.items()), key=lambda x: x[0][1], reverse=True)
    cat_sham_dict = OrderedDict()
    for k, v in cat_sham_items:
        cat_sham_dict[k] = v


    print("number of unique shams {}".format(len(sham_items)))

    print('total number of shams {}'.format(sum(dict(found).values())))

    return cat_sham_dict
    # return cat_items


def make_csv(sham_items, example_num, filename='sham_examples_full_cats.csv'):
    f = open(filename, 'wb')
    keys = ['Category', 'Quantity'] + ['Sham {}'.format(i+1) for i in range(example_num)]
    csv = unicodecsv.DictWriter(f, keys)
    # csv = unicodecsv.DictWriter(f, ['Category', 'Quantity'])#, 'Example Shams'])
    csv.writeheader()
    for (cat, count), sham_examples in list(sham_items.items()):
    # for cat, count in sham_items:
        # csv.writerow({'Category': cat, 'Quantity': count})# , 'Example Shams': sham_examples})
        row_dict = {
            'Sham {}'.format(i+1): temp_sham
            for i, temp_sham in enumerate(sham_examples)
        }
        for i in range(len(sham_examples), example_num):
            row_dict['Sham {}'.format(i+1)] = ''

        row_dict['Category'] = cat
        row_dict['Quantity'] = count

        csv.writerow(row_dict)
    f.close()


def run_shaminator(titles=None, with_real_refs=False, SEG_DIST = 5, create_ref_dict = True):
    base_url = "https://www.sefaria.org/"

    title_list = []
    cats = ["Midrash", "Halakha", "Philosophy"]
    collective_titles = ["Rashi", "Kessef Mishneh"]
    for cat in cats:
        title_list += library.get_indexes_in_category(cat)
    for cTitle in collective_titles:
        title_list += library.get_indices_by_collective_title(cTitle)

    title_list = titles
    for ititle, title in enumerate(title_list):
        print("-"*50)
        print(title, ititle+1, '/', len(title_list))
        print("-"*50)

        html = """
        <!DOCTYPE html>
        <html>
            <head>
                <link rel='stylesheet' type='text/css' href='styles.css'>
                <meta charset='utf-8'>
            </head>
            <body>
                <table>
                    <tr><td>Row Id</td><td>Book Ref</td><td>Ref Found</td><td>Sham Found</td><td>Sham Text</td></tr>
        """

        index = library.get_index(title)
        inst = IndexIbidFinder(index)
        if create_ref_dict:
            try:
                ref_dict = inst.find_in_index()
                # ref_dict - OrderedDict. keys: segments. values: dict {'refs': [Refs obj found in this seg], 'locations': [], 'types': []}
            except AssertionError:
                print("Skipping {}".format(title))
                continue # problem with Ein Ayah

        last_index_ref_seen = {}
        row_num = 1
        char_padding = 20
        double_tanakh_books = {"I Samuel": "Samuel", "II Samuel": "Samuel", "I Kings": "Kings", "II Kings": "Kings",
                               "I Chronicles": "Chronicles", "II Chronicles": "Chronicles"}
        for k, v in list(ref_dict.items()):
            curr_ref = Ref(k)
            for i, (r, l, t) in enumerate(zip(v['refs'], v['locations'], v['types'])):
                sham_ref_key = r.index.title if r.index.title not in double_tanakh_books else double_tanakh_books[
                    r.index.title]
                if t == CitationFinder.SHAM_INT and last_index_ref_seen[sham_ref_key] is not None:
                    last_ref_with_citation, last_location_with_citation, last_ref_seen = last_index_ref_seen[sham_ref_key]
                else:  # if t == CitationFinder.REF_INT:
                    last_index_ref_seen[sham_ref_key] = (curr_ref, l, r)
                    if not with_real_refs:
                        continue
                    dist = curr_ref.distance(last_ref_with_citation)
                    last_ref_with_citation = curr_ref
                    last_location_with_citation = l
                    last_ref_seen = r
                    r = "N/A"


                # dist = curr_ref.distance(last_ref_with_citation)
                print(dist)
                if dist == 0:
                    text = strip_nikkud(curr_ref.text('he').text)

                    start_ind = 0 if last_location_with_citation[0] - char_padding < 0 else last_location_with_citation[
                                                                                                0] - char_padding
                    end_ind = l[1] + char_padding

                    before = text[start_ind:last_location_with_citation[0]]
                    real_ref = text[last_location_with_citation[0]:last_location_with_citation[1]]
                    middle = text[last_location_with_citation[1]:l[0]] if last_location_with_citation[1] <= l[0] else ""
                    sham_ref = text[l[0]:l[1]] if t == CitationFinder.SHAM_INT else ""
                    after = text[l[1]:end_ind]
                    text = "{}<span class='r'>{}</span>{}<span class='s'>{}</span>{}".format(before, real_ref, middle,
                                                                                              sham_ref, after)

                else:
                    start_text = strip_nikkud(last_ref_with_citation.text('he').text)
                    # start_text = strip_nikkud(start_text)[last_location_with_citation[0]:]
                    end_text = strip_nikkud(curr_ref.text('he').text)
                    # end_text = strip_nikkud(end_text)[:l[1]+1]
                    if dist > SEG_DIST:
                        continue
                    elif dist > 1 and  dist <= SEG_DIST:
                        print("{} {} {}".format(curr_ref, last_ref_with_citation.next_segment_ref(),
                                                 curr_ref.prev_segment_ref()))
                        mid_text = last_ref_with_citation.next_segment_ref().to(curr_ref.prev_segment_ref()).text(
                            'he').text
                        while isinstance(mid_text, list):
                            mid_text = reduce(lambda a, b: a + b, mid_text)
                    else:
                        mid_text = ""

                    start_ind = 0 if last_location_with_citation[0] - char_padding < 0 else last_location_with_citation[
                                                                                                0] - char_padding
                    end_ind = l[1] + char_padding

                    start_before = start_text[start_ind:last_location_with_citation[0]]
                    start_real_ref = start_text[last_location_with_citation[0]:last_location_with_citation[1]]
                    start_after = start_text[last_location_with_citation[1]:]

                    end_before = end_text[:l[0]]
                    end_sham_ref = end_text[l[0]:l[1]]
                    end_after = end_text[l[1]:end_ind]
                    text = "{}<span class='r'>{}</span>{} {} {}<span class='s'>{}</span>{}".format(start_before,
                                                                                                    start_real_ref,
                                                                                                    start_after,
                                                                                                    mid_text,
                                                                                                    end_before,
                                                                                                    end_sham_ref,
                                                                                                    end_after)

                text = bleach.clean(text, strip=True, tags=['span'], attributes=['class'])
                # surround all non interesting parens with spans
                text = re.sub(r"(?<!>)(\([^)]+\))(?!<)", r"<span class='p'>\1</span>", text)

                rowclass = "realrefrow" if t == CitationFinder.REF_INT else "shamrefrow"
                row = "<tr class='{}' ><td>{}</td><td><a href='{}' target='_blank'>{}</a></td><td>{}</td><td>{}</td><td class='he'>{}</td></tr>"\
                    .format(rowclass, row_num, base_url + curr_ref.url(), k, last_ref_seen, r, text)
                html += row
                row_num += 1

        html += """
                </table>
            </body>
        </html>
        """

        with codecs.open('ibid_output/ibid_{}.html'.format(title), 'wb', encoding='utf8') as f:
            f.write(html)


def index_ibid_finder():
    index = library.get_index("Sefer Mitzvot Gadol")
    inst = IndexIbidFinder(index)
    inst.find_in_index()


def segment_ibid_finder(title):
    index = library.get_index("Sefer HaChinukh")
    inst = IndexIbidFinder(index)
    r = Ref(title)
    st = r.text("he").text
    refs, locations, types = inst.find_in_segment(st)
    print(refs, locations, types)


def validate_alt_titles():
    alt_titles = {
        "ויקרא": ["ויק'"],
        "במדבר": ["במ'"],
        "דברים": ["דב'"],
        "יהושוע": ["יהוש'"],
        "שופטים": ["שופטי'"],
        "ישעיהו": ["ישע'"],
        "ירמיהו": ["ירמ'"],
        "יחזקאל": ["יחז'"],
        "מיכה": ["מיכ'"],
        "צפניה": ["צפנ'"],
        "זכריה": ["זכרי"],
        "מלאכי": ["מלא'"],
        "תהילים": ["תה'"],
        "נחמיה": ["נחמי'"],
        "דניאל": ["דני'"],
        "אסתר": ["אס'"],
        "איכה": ["איכ'"]
    }
    for k, v in list(alt_titles.items()):
        for t in v:
            try:
                i = library.get_index(t)
                print("{} -> {}".format(k, t))
            except BookNameError:
                pass


def alt_titles():
    idxset = IndexSet({'title': {'$regex': '^Mishneh Torah'}})

    for idx in idxset:
        title = idx.get_title("he")
        print(title)
        newtitle = title.replace('תלמוד ירושלמי', 'ירושלמי')
        print(newtitle)
        idx.nodes.add_title(newtitle, "he")
        idx.save(override_dependencies=True)

    library.rebuild()


def check_apperence_alt_titles(alt_titles):
    inst = CitationFinder()
    example_num = 20
    if type(alt_titles) is not list:
        title = alt_titles
    else:
        for i, title in enumerate(alt_titles):
            sham_items = count_regex_in_all_db(inst.get_ultimate_title_regex(title, None, 'he'), text='all', example_num=example_num) #text='all', text='Ramban on Genesis')
    cl_title = re.sub('''["']''', '', title)
    make_csv(sham_items, example_num, filename='''ibid_output/alt_titles_output/{}.csv'''.format(cl_title))

def reurl(st):
    return re.sub('_', ' ', st)

def run_shaminator_for_outsidetext(chaimjasonfile):
    """
    this code was written specificaly to read and write to Chaim's json files of Topics from Aspaclaria's db parsing
    :param chaimjasonfile: Chaim intern 2018
    :return:
    """
    inst = CitationFinder()
    dead_ind = library.get_index("Genesis")
    resolver = IndexIbidFinder(dead_ind)
    l = 0

    with codecs.open(chaimjasonfile, encoding="utf8") as rfp:
        cnt = 0
        # data = json.loads(rfp.read())
        alldata = json.loads(rfp.read())
        keys = list(alldata.keys())[0:3]
        data = {}
        for k in keys:
            data[k] = alldata[k]
        for k, topic in list(data.items()):
            cnt +=1
            if cnt > 3:
                break
            citations = topic["RelatedSources"]
            l += len(citations)
            for i, cit in enumerate(citations):
                cit = re.sub('פרק', '', cit)
                cit = "("+cit+")"
                refs, locations, types = resolver.find_in_segment(cit)
                print(cit, refs[0].normal() if refs else [])
                topic["RelatedSources"][i] = (topic["RelatedSources"][i], refs[0].normal() if refs else [])

    with codecs.open('resolved_asp.json', mode='w', encoding="utf8") as wfp:
        json.dump(data, wfp)
    print(l)

if __name__ == "__main__":
    # inst = CitationFinder()
    # example_num = 20
    # title = u'ר"ה'
    # node = library.get_schema_node(title, 'he')
    # sham_items = count_regex_in_all_db(inst.get_ultimate_title_regex(title, None, 'he'), text = 'all', example_num=example_num) #, text = 'Ramban on Genesis')
    # sham_items = count_regex_in_all_db(example_num=example_num)
    # make_csv(sham_items, example_num, filename='alt_title_{}.csv'.format(title))
    # alt_titles_lst = [item for lst in rambam_alt_names().values() for item in lst]
    # check_apperence_alt_titles(u'ד"ה')
    # #
    # import cProfile
    # import pstats
    #
    # cProfile.run("inst = CitationFinder(); count_regex_in_all_db(inst.get_ultimate_title_regex(u'שם', 'he'), text = 'Ramban on Genesis',example_num=7)", "stats")
    # p = pstats.Stats("stats")
    # p.strip_dirs().sort_stats("cumulative").print_stats()

    #index_ibid_finder()
    #segment_ibid_finder()
    # for mass in library.get_indexes_in_category('Mishnah'):
    #     index_title = u'Tosafot Yom Tov on {}'.format(mass)
    #     tosfot_yt = []
    #     if library.get_index(index_title):
    #         print index_title
    #         tosfot_yt.append(index_title)
    #         # run_shaminator(index_title)
    # run_shaminator(tosfot_yt)
    # run_shaminator([u'Ramban on Genesis'], with_real_refs = True)
    # for humash in library.get_indexes_in_category(u'Torah'):
    #     run_shaminator([u'Ramban on {}'.format(humash)],  with_real_refs=True)
    # segment_ibid_finder(u'Ramban on Genesis 4:32:1')
    # validate_alt_titles()
    # run_shaminator([reurl(u"Rashi on Deuteronomy")], with_real_refs=True, SEG_DIST=2)
    run_shaminator_for_outsidetext("aspakdictbook5.json")



# bug at Bemidbar Rabbah 9:50. It says the sham is Jeremiah 16:16. I believe it should just be Jeremiah 16
