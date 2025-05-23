#see link_Izhbitz
from sources.functions import *
from linking_utilities.parallel_matcher import *
from linking_utilities.weighted_levenshtein import WeightedLevenshtein
def find_ref_daf(needle, start, refs, skips):
    start_loc = AddressTalmud(0).toNumber('en', start)
    skip = 0
    for i, ref in enumerate(refs):
        loc = start_loc + i
        loc += skip
        while loc in skips:
            loc += 1
            skip += 1
        loc_daf = AddressTalmud.toStr('en', loc)
        if needle == loc_daf:
            return ref
    return None
def convert(find, lang='en'):
  match = None
  for v, vol in enumerate(library.get_index("Zohar").alt_structs["Daf"]["nodes"]):
    vol_in_find = find.split()[1]
    vol_in_find = vol_in_find.replace(",", "")
    if vol_in_find.isdigit():
        if int(vol_in_find) != v+1:
            continue
    elif roman_to_int(vol_in_find) != v+1:
        continue
    for parasha in vol["nodes"]:
        if "startingAddress" in parasha:
            title = [x['text'] for x in parasha['titles'] if x['lang'] == lang][0]
            m = find_ref_daf(find.split()[-1], parasha["startingAddress"], parasha["refs"], parasha.get("skipped_addresses", []))
            if m:
                match = m
                break
        else:
            for parasha2 in parasha["nodes"]:
                try:
                    title = [x['text'] for x in parasha2['titles'] if x['lang'] == lang][0]
                except:
                    title = parasha2["wholeRef"].replace("Zohar, ", "").split()[0]
                m = find_ref_daf(find.split()[-1], parasha2["startingAddress"], parasha2["refs"], parasha2.get("skipped_addresses", []))
                if m:
                    match = m
                    break
  assert match is not None
  return match


def get_score(words_a, words_b):
    normalizingFactor = 100
    smoothingFactor = 1
    ImaginaryContenderPerWord = 22
    str_a = u" ".join(words_a)
    str_b = u" ".join(words_b)
    dist = WeightedLevenshtein().calculate(str_a, str_b, normalize=False)
    score = 1.0 * (dist + smoothingFactor) / (len(str_a) + smoothingFactor) * normalizingFactor

    dumb_score = (ImaginaryContenderPerWord * len(words_a)) - score
    return dumb_score

results = []
def find_dh(refs):
    global results
    pm = ParallelMatcher(tokenizer=lambda x: bleach.clean(x, strip=True, tags=[]).split(),
                        min_words_in_match=4,
                        ngram_size=3,
                        only_match_first=True,
                        all_to_all=False,
                        min_distance_between_matches=0,
                        verbose=False,
                        calculate_score=get_score,
                        max_words_between=2,
                        dh_extract_method=lambda x: bleach.clean(x, strip=True, tags=[]))
    x = pm.match([r.normal() for r in refs], return_obj=True)
    results += [(i.a.ref.normal(), i.b.ref.normal()) for i in x if i.score > 0]

import re
finds = defaultdict(list)
def find_zohar(segment_str, segment_tref, segment_heTref, self):
    vol_pattern = re.compile(r'(?<!Tikkuney )(?<!Tikkunei )Zohar [(]{0,1}[I123]{1,3}, [0-9]+[ab]*')
    chapter_pattern = re.compile(r"(?<!Tikkuney )(?<!Tikkunei )(?:Zohar, Mishpatim|Zohar, Parashat Mishpatim|Zohar, Ki Tisa|Zohar, Parashat Ki Tisa|Zohar, Parashat Ki Tissa|Zohar, Ki Tissa|Zohar, Sh'lach|Zohar, Parashat Sh'lach|Zohar, Parashat Shelach|Zohar, Parshat Shlach|Zohar, Shlach|Zohar, Sifra DiTzniuta|Zohar, Balak|Zohar, Parashat Balak|Zohar, Parshat Balak|Zohar, Eikev|Zohar, Parashat Eikev|Zohar, Parashat Ekev|Zohar, Idra Rabba|Zohar, Bechukotai|Zohar, Parashat Bechukotai|Zohar, Bekhukotai|Zohar, Vayakhel|Zohar, Parashat Vayakhel|Zohar, Parshat Vayakel|Zohar, Matot|Zohar, Parashat Matot|Zohar, Parshat Matot|Zohar, Toldot|Zohar, Parashat Toldot|Zohar, Parashat Toledot|Zohar, Parshat Toledot|Zohar, Toldos|Zohar, Vayechi|Zohar, Parashat Vayechi|Zohar, Parashat Vayehi|Zohar, Terumah|Zohar, Parashat Terumah|Zohar, Truma|Zohar, Trumah|Zohar, T'rumah|Zohar, Ha'Azinu|Zohar, Parashat Ha'Azinu|Zohar, Parashat Ha'azinu|Zohar, Parashsat Ha'azinu|Zohar, Parashat Haazinu|Zohar, Haazinu|Zohar, Tetzaveh|Zohar, Parashat Tetzaveh|Zohar, T'tzaveh|Zohar, Parashat Tezaveh|Zohar, Parashat Teztaveh|Zohar, Bereshit|Zohar, Parashat Bereshit|Zohar, Parashat Bereishit|Zohar, Parashat Genesis|Zohar, Genesis|Zohar, Bereishit|Zohar, Breishit|Zohar, Bereshis|Zohar, Vayeshev|Zohar, Parashat Vayeshev|Zohar, Parashat Veyeshev|Zohar, Parshat Vayeshev|Zohar, Vayikra|Zohar, Parashat Vayikra|Zohar, Ki Teitzei|Zohar, Parashat Ki Teitzei|Zohar, Parashat Ki Tetze|Zohar, Parashat Ki Teitze|Zohar, Ki Seitzei;|Zohar, Ki Teytzey|Zohar, Ki Teitze|Zohar, Yitro|Zohar, Parashat Yitro|Zohar, Parshat Yitro|Zohar, Jethro|Zohar, Pinchas|Zohar, Parashat Pinchas|Zohar, Shoftim|Zohar, Parashat Shoftim|Zohar, Judges|Zohar, Shofetim|Zohar, Addenda, Volume II|Zohar, Addenda, Volume I|Zohar, Bo|Zohar, Parashat Bo|Zohar, Behar|Zohar, Parashat Behar|Zohar, Vayeilech|Zohar, Parashat Vayeilech|Zohar, Parashat Vayelech|Zohar, Vayelekh|Zohar, Chayei Sara|Zohar, Parashat Chayei Sara|Zohar, Parashat Chayei Sarah|Zohar, Parashat Chaye Sarah|Zohar, Parshat Chayei Sarah|Zohar, Chayei Sarah|Zohar, Hayei Sarah|Zohar, Hayye Sarah|Zohar, Emor|Zohar, Parashat Emor|Zohar, Parshat Emor|Zohar, Shmini|Zohar, Parashat Shmini|Zohar, Parashat Shemini|Zohar, Parshat Shemini|Zohar, Shemini|Zohar, Beshalach|Zohar, Parashat Beshalach|Zohar, Introduction|Zohar, Metzora|Zohar, Parashat Metzora|Zohar, Parsha Metzorah|Zohar, Parashat Metzorah|Zohar, Beha'alotcha|Zohar, Parashat Beha'alotcha|Zohar, Parashat Behaalotcha|Zohar, Parashat Behaalotchah|Zohar, Parashat Behalotecha|Zohar, Parashat Bahalotecha|Zohar, B'ha'alotekha|Zohar, Parasha Behaatlocha|Zohar, Behaloscha|Zohar, Vaetchanan|Zohar, Parashat Vaetchanan|Zohar, Parashat Va'etchanan|Zohar, Parshat V'etchanan|Zohar, Va'etchanan|Zohar, V'etchanan|Zohar, V'ethanan|Zohar, Pekudei|Zohar, Parashat Pekudei|Zohar, Parashat Pikudei|Zohar, Noach|Zohar, Parashat Noach|Zohar, Noah|Zohar, Parshat Noah|Zohar, Tazria|Zohar, Parashat Tazria|Zohar, Parshat Tazria|Zohar, Bamidbar|Zohar, Parashat Bamidbar|Zohar, Parashat Bemidbar|Zohar, Numbers|Zohar, Kedoshim|Zohar, Parashat Kedoshim|Zohar, Miketz|Zohar, Parashat Miketz|Zohar, Addenda, Volume III|Zohar, Achrei Mot|Zohar, Parashat Achrei Mot|Zohar, Parashat Acharei Mot|Zohar, Vaera|Zohar, Parashat Vaera|Zohar, Parashat Va'era|Zohar, Parshat Va'era|Zohar, Ve'Erah|Zohar, Parshat Vaera|Zohar, Lech Lecha|Zohar, Parashat Lech Lecha|Zohar, Parashat Lekh Lekha|Zohar, Nasso|Zohar, Parashat Nasso|Zohar, Parashat Naso|Zohar, Naso|Zohar, Vayera|Zohar, Parashat Vayera|Zohar, Parashat Vayeira|Zohar, Parshat Vayera|Zohar, Chukat|Zohar, Parashat Chukat|Zohar, Parshat Chukkat|Zohar, Vayetzei|Zohar, Parashat Vayetzei|Zohar, Parashat Vayeitzey|Zohar, Vayetze|Zohar, Parashat Vayetze|Zohar, Parashat Vayetzey|Zohar, Vayigash|Zohar, Parashat Vayigash|Zohar, Idra Zuta|Zohar, Shemot|Zohar, Parashat Shemot|Zohar, Parsha Shemot|Zohar, Names|Zohar, Shmot|Zohar, Exodos|Zohar, Sh'mot|Zohar, Vayishlach|Zohar, Parashat Vayishlach|Zohar, Tzav|Zohar, Parashat Tzav|Zohar, Korach|Zohar, Parashat Korach) [(\[]?[a-z0-9]+")
    vol_matches = vol_pattern.findall(segment_str)
    chapter_matches = chapter_pattern.findall(segment_str)
    for find in vol_matches:
        actual_ref = convert(find)
        base_refs_and_text = list(zip(Ref(actual_ref).all_segment_refs(), TextChunk(Ref(actual_ref), lang='he', vtitle='Vocalized Zohar, Israel 2013').text))
        comm_ref_and_text = [Ref(segment_tref), Ref(segment_tref).text('he').text]
        found_zohar_ref = find_dh([Ref(segment_tref)]+Ref(actual_ref).all_segment_refs())
        finds[segment_tref].append(actual_ref)
    for find in chapter_matches:
        finds[segment_tref].append(find)


texts = ["Likutei Moharan", "Likutei Etzot"]
for book in texts:
    for v in library.get_index(book).versionSet():
        if v.language == 'en':
            v.walk_thru_contents(find_zohar)
# for x in finds:
#     for find in finds[x]:
#         try:
#             Link({"generated_by": "zohar_to_LT", "type": "Commentary", "auto": True, "refs": [x, find]}).save()
#         except Exception as e:
#             print(e)
LinkSet({"generated_by": "zohar_to_LT"}).delete()

for x in results:
    print(x[0], "=>", x[1])
    try:
        Link({"generated_by": "zohar_to_LT", "type": "Commentary", "auto": True, "refs": [x[0], x[1]]}).save()
    except Exception as e:
        print(e)