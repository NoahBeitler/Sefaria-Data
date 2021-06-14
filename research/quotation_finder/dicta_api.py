import django, re, requests, json
from collections import defaultdict
django.setup()
from collections import namedtuple
import unicodecsv as csv
from sources.functions import *
from sources.Scripts.pesukim_linking import *

min_thresh=22
find_url = "https://talmudfinder-1-1x.loadbalancer.dicta.org.il/PasukFinder/api/markpsukim"
# parse_url = f"https://talmudfinder-1-1x.loadbalancer.dicta.org.il/PasukFinder/api/parsetogroups?smin={min_thresh}&smax=10000"
SLEEP_TIME = 1

sandbox = SEFARIA_SERVER.split(".")[0]

def retreive_bold(st):
    return ' '.join([re.sub('<.*?>', '', w) for w in st.split() if '<b>' in w])


def find_pesukim(base_text, mode="tanakh", thresh=0):
    """
    Using the dicta citations finder returns results of optional pesukim that correspond to text in the base text and other metadata
    :param base_text: stripped text to look through.
    :param mode: defaults to Tanakh because we are looking to match text to Pesukim can potentially also be 'mishna' and 'talmud'
    :param thresh: from learning the api it seams to always be 0 and not make a difference when changed.
    :return: dictionary: {'downloadId': int,
                             'allText' : st | it is the base_text
                             'results': list of dicts | {
                                                'mode' :0,
                                                'iVerse': int,
                                                'ijWordPairs': list of dicts ot keys: item1, item2 values: int,
                                                'score':int (0-1000),
                                                'debScore':None
                                                }
                                }
    """
    data_text = {
        "data": base_text,
        "mode": mode,
        "thresh": thresh,
        "fdirectonly": False
    }
    response = requests.post(find_url, data=json.dumps(data_text))
    response_json = response.json()
    sleep(SLEEP_TIME)
    return response_json


def dicta_parse(response_json, min_thresh=22):
    parse_url = f"https://talmudfinder-1-1x.loadbalancer.dicta.org.il/PasukFinder/api/parsetogroups?smin={min_thresh}&smax=10000"
    result = response_json['results']
    downloadId = response_json["downloadId"]
    allText = response_json["allText"]

    data_parse = {
        "allText": allText,
        "downloadId": downloadId,
        "keepredundant": True,
        "results": result
    }

    response = requests.post(parse_url, data=json.dumps(data_parse))
    parsed_results = response.json()
    sleep(SLEEP_TIME)
    return parsed_results


def get_dicta_matches(base_refs, mode="tanakh", onlyDH = False, thresh=0, min_thresh=22, prioraty_tanakh_chunk=None, wrods_to_wipe=''):
    """
    the heart of the quotation finder input Ref and output links
    :param base_refs:
    :param mode:
    :param onlyDH:
    :param thresh:
    :param min_thresh:
    :return: list (as long as the list of base_refs - segs) of matches
    """
    Match = namedtuple("Match", ["textMatched", "textToMatch", "score", "startIChar", "endIChar", "pasukStartIChar", "pasukEndIChar", "dh"])
    link_options = []
    dh_link_options = []
    for base_ref in base_refs:
        base_text = base_ref.text('he').text
        # base_text = strip_cantillation(bleach.clean(base_text, tags=[], strip=True), strip_vowels=True)
        # base_text = re.sub(f"{wrods_to_wipe}", "", base_text)
        response_json = find_pesukim(base_text, mode, thresh=thresh)
        # response_json["results"][0]["ijWordPairs"]
        parsed_results = dicta_parse(response_json, min_thresh=min_thresh)
        dh_res = [res for res in parsed_results if res['startIChar'] <= 10]
        for result in parsed_results:
            matched = result['matches'][0]
            # matched_pasuks = [match['verseDispHeb'] for match in result['matches']]
            # matched_pasuk = matched_pasuks[0]
            if len(result['matches']) > 1:
                many_pesukim_he = [match['verseDispHeb'] for match in result['matches']]
                many_pesukim_refs = [Ref(he_disp) for he_disp in many_pesukim_he]
                suffex = ''.join([f"&p{i+1}={many_pesukim_refs[i].normal()}&lang2=he" for i in list(range(1, len(many_pesukim_refs)))])
                f.write(base_ref.normal())
                f.write(re.sub(" ", "_", f'{sandbox}.cauldron.sefaria.org/{many_pesukim_refs[0].normal()}?lang=he{suffex}'))
                print(re.sub(" ", "_", f'{sandbox}.cauldron.sefaria.org/{many_pesukim_refs[0].normal()}?lang=he{suffex}\n'))
                print(f"more than one pasuk option: {many_pesukim_he}")
                if prioraty_tanakh_chunk:
                    best_match_option_ref = list(set(prioraty_tanakh_chunk.all_segment_refs()) & set(many_pesukim_refs))
                    best_match = [match for match in result['matches'] if Ref(match['verseDispHeb']) == best_match_option_ref]
                    matched = best_match if best_match else matched
                    print(f"{Ref(matched['verseDispHeb']).normal()} was chosen")
            pasuk_ref = Ref(matched['verseDispHeb'])
            matched_pasuk_start = matched['verseiWords'][0]
            matched_pasuk_end = matched['verseiWords'][-1]
            # print(re.sub(" ", "_", f'www.sefaria.org/{base_ref.normal()}?lang=he&p2={pasuk_ref.normal()}'))
            matched_wds_base = retreive_bold(result['text'])
            matched_wds_pasuk = retreive_bold(matched['matchedText'])
            # print(f"{matched_wds_base} | {matched_wds_pasuk}")
            score = matched['score']
            m = Match(matched_wds_base, matched_wds_pasuk, score, result["startIChar"], result["endIChar"], matched_pasuk_start, matched_pasuk_end, result in dh_res)
            link_option = [pasuk_ref, base_ref, m.textMatched, m]
            if result in dh_res:
                link_option.append("dh")
                dh_link_options.append(link_option)
            link_options.append(link_option)
    if onlyDH:
        return dh_link_options
    return link_options


def data_to_link(link_option, type="quotation", generated_by="", auto=True):
    match = link_option[3]
    pasuk_ref = link_option[0]
    book_match = link_option[1]
    link_json = {"type": type,
     "refs": [pasuk_ref.normal(), book_match.normal()],
     "auto": auto,
     "charLevelData": {},
    "score": match.score
     }
    if generated_by:
        link_json.update({"generated_by": generated_by})
    link_json["charLevelData"] = {
        "charLevelDataBook": {
            "startChar": match.startIChar,
             "endChar": match.endIChar,
             "versionTitle": link_option[1].text('he').version().versionTitle,
             "language": "he"
        },
     "charLevelDataPasuk": {
         "startWord": match.pasukStartIChar,
         "endWord": match.pasukEndIChar,
         "versionTitle": link_option[0].text('he').version().versionTitle,
         "language": "he"}
        }
    return link_json, match


def write_to_csv(links, linkMatchs,  filename='quotation_links'):
    list_dict = []
    base_text_name = Ref(links[0]["refs"][1]).book
    for link, linkMatch in zip(links, linkMatchs):
        row = {"url": link2url(link),
               "pasuk": link["refs"][0],
               base_text_name: link["refs"][1],
               "words pasuk": linkMatch.textToMatch,
               "words base": linkMatch.textMatched,
               "score": linkMatch.score,
                "dh": linkMatch.dh}
        list_dict.append(row)

    with open(u'{}.csv'.format(filename), 'a') as csv_file:
        writer = csv.DictWriter(csv_file, ['url', 'pasuk', base_text_name, 'words pasuk', 'words base', 'score', "dh"])  # fieldnames = obj_list[0].keys())
        writer.writeheader()
        writer.writerows(list_dict)


def get_links_ys(pear=None, post=False):
    """
    :param post: boolean to post to SEFARIA_SERVER
    :param pear: tuple (oRef Tanakh, oRef base book)
    :return: list of links (to be posted)
    """
    if not pear:
        peared = get_zip_ys()  # ys, perek (Torah)
        books = ['Genesis', 'Exodus', 'Leviticus', 'Numbers', 'Deuteronomy']
        book = random.sample(range(5), 1)[0]
        pear = peared[book][random.sample(range(len(peared[book])), 1)[0]]
    print(pear)
    # from pathlib import Path
    # Path(f"{os.getcwd()}/{pear[0]}").mkdir(parents=True, exist_ok=True)
    os.makedirs(pear[0].normal(), exist_ok=True)   # os.mkdir(f"{os.getcwd()}/{pear[1].normal()}")
    os.chdir(pear[0].normal())
    # dicta code
    thresh = ''
    # for thresh in [10, 22, 50]:
    base_refs = pear[1].all_segment_refs()
    link_options = get_dicta_matches(base_refs, onlyDH=False, prioraty_tanakh_chunk=pear[0], min_thresh=0)
    links, linkMatchs = zip(*[data_to_link(link_option, generated_by="Yalkut_shimoni_quotations") for link_option in link_options])
    # links, link_data = link_options_to_links(link_options, min_score=thresh)
    write_to_csv(links, linkMatchs, filename=f"dicta_{thresh}")
    print(len(links))

    write_links_to_json("ys_links", links)

    if post:
        post_link(links)
    return links

    # # dh code
    # matches = get_matches(pear)
    # links, link_data = link_options_to_links(matches, link_type="Midrash")
    # write_to_csv(links, link_data, filename="dh")


def write_links_to_json(filename, links):
    with open(f'{filename}.txt', "w+") as fl:
        json.dump(links, fl)


def get_links_from_file(file_name):
    with open(file_name, "r") as link_file:
        links = json.load(link_file)
    return links


def post_links_from_file(file_name, score=22):
    links_to_post = []
    links = get_links_from_file(file_name)
    for l in links:
        if l["score"] > score:
            links_to_post.append(l)
    post_link(links_to_post, server="http://localhost:8000")


def dicta_links_from_ref(tref, post=False, onlyDH=False):
    all_links = []
    oref = Ref(tref)
    base_refs = oref.all_segment_refs()
    link_options = get_dicta_matches(base_refs, onlyDH=onlyDH, min_thresh=22)
    if not link_options:
        print("no links found")
        return
    links, linkMatchs = zip(*[data_to_link(link_option, generated_by='quotation_finder', type='quotation') for link_option in link_options])
    write_to_csv(links, linkMatchs, filename=f"dicta_{tref}")
    print(links)
    all_links.extend(links)
    if post:
        post_link(links, server="http://localhost:8000")
    write_links_to_json(f'{oref.book}',links)
    return all_links


def link_a_parashah_node_struct_index(index_name, onlyDH=False, post=False):
    """
    input index with an assumed Parashah structure
    :param index_name: index name
    :param onlyDH: choses to look only at quotations in the beginning of the segment for the commentary type of linking
    :param post: option to post atomatically to SEFARIA-SERVER
    :return: list(:Link): list of all the links
    """
    peared = get_zip_parashot_refs(index_name)
    all_links = []
    for pear in peared:
        base_refs = pear[1].all_segment_refs()
        link_options = get_dicta_matches(base_refs, onlyDH=onlyDH, min_thresh=22, prioraty_tanakh_chunk=pear[0], wrods_to_wipe='''(ב?מדרש|ב?פסוק|והנה|כתיב|פ?רש"?י|ו?כו'?)''')
        if not link_options:
            continue
        links, linkMatchs = zip(*[data_to_link(link_option, generated_by='quotation_linker_dh', type='commentary') for link_option in link_options])
        write_to_csv(links, linkMatchs, filename=f"dicta_{base_refs[0].index.title}")
        print(links)
        all_links.extend(links)
        if post:
            post_link(links)
            print(f"posted Parashah {pear[1]}")
            f.write(f"posted Parashah {pear[1]}\n")
    return all_links

if __name__ == '__main__':
    index_name = 'Siddur Sefard, Kiddush Levanah'# "Noam_Elimelech"
    f = open(f"intraTanakhLinks.txt_{index_name}", "a+")  # not the right place to open this for the other functions. read doc.
    # f.write(index_name)
    # link_a_parashah_node_struct_index(index_name, onlyDH=True, post=True)
    # pear = (Ref('פרשת שלח'), Ref("ילקוט שמעוני על התורה, שלח לך")) #(Ref('Numbers 13:1-15:41'), Ref('Yalkut Shimoni on Torah 742'))  # :7-750:13 ( Ref('פרשת שלח'), Ref("ילקוט שמעוני על התורה, שלח לך"))
    # pear = (Ref('Numbers 16'), Ref("Yalkut_Shimoni_on_Torah.750.15"))
    # links = get_links_ys(pear, post=False)
    links = dicta_links_from_ref('Selichot_Nusach_Ashkenaz_Lita, Erev_Rosh_Hashana.13', post=False)
    f.close()


    # post_links_from_file("/home/shanee/www/Sefaria-Data/research/quotation_finder/Numbers 13:1-15:41/ys_links.txt", score=10)

