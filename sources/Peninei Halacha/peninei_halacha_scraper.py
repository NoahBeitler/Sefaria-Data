# -*- coding: utf-8 -*-
import django
django.setup()
from sefaria.model import *
from sources.functions import *
import requests
from bs4 import BeautifulSoup, element
import regex as re
import PIL
from PIL import Image
import codecs
import base64

VERSION_TITLE_HE = "Peninei Halakhah, Yeshivat Har Bracha - 2020"
VERSION_SOURCE_HE = "https://ph.yhb.org.il"
VERSION_TITLE_EN = "Peninei Halakhah, English ed. Yeshivat Har Bracha - 2020"
VERSION_SOURCE_EN = "https://ph.yhb.org.il/en"

# NOTE: I ASSUMED THAT IF SECTIONS ARE ALSO TRANSLATED, THEN SIMANIM ARE TRANSLATED TOO.
# IF THAT'S NOT TRUE, ADD "AND FALSE" TO LINES 874 AND 889
tsv_translations_file = "Peninei Halakhah Title Translations.tsv"
tsv_title_changes_file = "PH_Chapter_Section_Title_Changes.tsv"
jar = requests.cookies.RequestsCookieJar()
jar.set("wp-postpass_b0cab8db5ce44e438845f4dedf0fcf4f", "%24P%24BH2d6c1lhrllIz02CYT36lWgURQXVe1")

leading_zeros_re = re.compile('^[\s0]+(.*)')
pre_num_letter_re = re.compile('.+\s*(?:[–.:]|(?:\s-\s))\s*(.*?)$')
img_text_re = re.compile("(.*?)\(max-width.*?(br/>|/p>|/>)")
footnote_re = re.compile("(\[[0123456789]+\])")
# le'eil and le'halan
self_re = re.compile("(?<=\(.*)(\u05dc\u05e2\u05d9\u05dc|\u05dc\u05d4\u05dc\u05df|בהמשך) (\S*), (\S*).*\)")
# shulchan arukh
sa_re = re.compile('\(.*שו"ע(?!\s*(חו"מ|יו"ד|אב"ה|או"ח|אה"ע)).*\)') # re.compile("\(.*\u05e9\u05d5\"\u05e2(?!\s*\u05d7\u05d5\"\u05de|\u05d9\u05d5\"\u05d3|\u05d0\u05d1\"\u05d4|\u05d0\u05d5\"\u05d7|\u05d0\u05d4\"\u05e2).*\)")
# arukh hashulchan
ah_re = re.compile("\(.*\u05e2\u05e8\u05d5\u05d4\"\u05e9 (?!\u05d7\u05d5\"\u05de|\u05d9\u05d5\"\u05d3|\u05d0\u05d1\"\u05d4|\u05d0\u05d5\"\u05d7).*\)")
# mishnah berurah
mb_re = re.compile("\(.*\u05de\"\u05d1.*\)")
# rambam
rm_re = re.compile('\([^)]*רמב"ם\s*([א-ת]{3}[^)]*?)\)')
# ramban
rn_re = re.compile("\(.*\u05e8\u05de\u05d1\"\u05df (?=\u05d1\u05e8\u05d0\u05e9\u05d9\u05ea|\u05e9\u05de\u05d5\u05ea|\u05d5\u05d9\u05e7\u05e8\u05d0|\u05d1\u05de\u05d3\u05d1\u05e8|\u05d3\u05d1\u05e8\u05d9\u05dd).*\)")
# rama
ra_re = re.compile("\(.*(?P<rama>\u05e8\u05de\"\u05d0),? (?!\u05d7\u05d5\"\u05de|\u05d9\u05d5\"\u05d3|\u05d0\u05d1\"\u05d4|\u05d0\u05d5\"\u05d7|\u05d0\u05d4\"\u05e2).*\)")
# ra_re = re.compile("\(.*\u05e8\u05de\"\u05d0 .*\)")
# magen avraham
ma_re = re.compile("\((?<!\u05e8)\u05de\"\u05d0 .*\)")
pics = 0
heb_titles = []
old_titles = []
new_titles = []
titles_to_print = [old_titles, new_titles, heb_titles]
titles_to_print_names = ["Titles with not-allowed characters", "Automatically fixed titles", "Hebrew titles"]
num_chapters = {"Shabbat": 30, "Likkutim I": 11, "Likkutim II": 17, "Festivals": 13, "The Nation and the Land": 10,
                "Berakhot": 18, "High Holidays": 10, "Shmitta and Yovel": 11, "Kashrut I": 19, "Kashrut II": 17,"Kashrut": 37, "Women's Prayer": 24,
                "Prayer": 26, "Family": 10, "Sukkot": 8, "Pesach": 16, "Zemanim": 17, "Simchat Habayit V'Birchato": 10}
books = [("Shabbat", "שבת", 1),  # 0 (eng_name, heb_name, url_number)
         ("Prayer", "תפילה", 2),  # 1
         ("Women's Prayer", "תפילת נשים", 3),  # 2
         ("Pesach", "פסח", 4),  # 3
         ("Zemanim", "זמנים", 5),  # 4
         ("The Nation and the Land", "העם והארץ", 6),  # 5
         ("Likkutim I", "ליקוטים א", 7),  # 6
         ("Likkutim II", "ליקוטים ב", 8),  # 7
         ("Berakhot", "ברכות", 10),  # 8
         ("Family", "משפחה", 11),  # 9
         ("Festivals", "מועדים", 12),  # 10
         ("Sukkot", "סוכות", 13),  # 11
         ("Simchat Habayit V'Birchato", "שמחת הבית וברכתו", 14),  # 12
         ("High Holidays", "ימים נוראים", 15),  # 13
         ("Shmitta and Yovel", "שביעית ויובל", 16),  # 14
         ("Kashrut I", "כשרות א – הצומח והחי", 17),  # 15
         ("Kashrut II", "כשרות ב – המזון והמטבח", 18),  # 16
         ("Kashrut", "כשרות", 17),  # 17
         ]
another_lang = ['es', 'ru', 'fr']

# SET THIS TO TRUE ONCE RABBI FISCHER SENDS LIST OF TITLE TRANSLATIONS (AND BE SURE TO SET PARAM "only_chapters_translated" ACCORDINGLY)
titles_were_translated = True
# SET THIS TO TRUE ONCE RABBI FISCHER SENDS LIST OF TITLE TRANSLATIONS, AND COPY/PASTE LISTS INTO PH_CHAPTER_SECTION_TITLE_CHANGES GOOGLE SHEET SO SHMUEL CAN MAKE CHANGES (THEN REDOWNLOAD TSV)
print_titles_to_be_changed = True

def do_peninei_halakhah(book_name_en, book_name_he, url_number, title_translations_tsv, title_changes_tsv, lang="he", only_chapters_translated=False):
    if lang not in ["he", "en", "es", "ru", "fr", "both"]:
        raise Exception("Language field can only be \"he\", \"en\", or \"both\".")
    if titles_were_translated:
        title_trans_dict = collect_trans_titles_from_tsv(title_translations_tsv)
    else:
        title_trans_dict = {}
    title_ch_dict = collect_ch_titles_from_tsv(title_changes_tsv)
    if book_name_en == "The Nation and the Land": #special case for ha'am veha'aretz
        download_html(book_name_en, url_number, "he")
        introduction_he, chapters_he, ordered_chapter_titles_he, section_titles_he = get_soup(book_name_en, url_number, lang)
        goren_intro, supp_sections, supp_section_titles, sup_all_siman_titles = supplement_parser()
        post_index_to_server(book_name_en, book_name_he, ordered_chapter_titles_he, section_titles_he, title_trans_dict, title_ch_dict, supp_section_titles=supp_section_titles, sup_all_siman_titles=sup_all_siman_titles, only_chapters_translated=False)
        post_text_to_server(book_name_en, introduction_he, chapters_he, lang, goren_intro, supp_sections)

    elif lang == "both":  # if parsing both heb and eng
        download_html(book_name_en, url_number, "he")
        download_html(book_name_en, url_number, "en")  # "en" or "es" or other
        introduction_he, chapters_he, ordered_chapter_titles_he, section_titles_he = get_soup(book_name_en, url_number, "he")
        introduction_en, chapters_en, ordered_chapter_titles_en, section_titles_en = get_soup(book_name_en, url_number, "en", another_lang=None)  # "en", another_lang = None, another_lang = "es"
        post_index_to_server(book_name_en, book_name_he, [ordered_chapter_titles_he, ordered_chapter_titles_en], [section_titles_he, section_titles_en], title_trans_dict, title_ch_dict, both=True, only_chapters_translated=False)
        post_text_to_server(book_name_en, introduction_he, chapters_he, "he")
        post_text_to_server(book_name_en, introduction_en, chapters_en, "en")  # "en" (don't use "es", because it comes)
    else:
        download_html(book_name_en, url_number, lang)  # if just one language
        introduction, chapters, ordered_chapter_titles, section_titles = get_soup(book_name_en, url_number, lang)
        if lang == "he":
            post_index_to_server(book_name_en, book_name_he, ordered_chapter_titles, section_titles, title_trans_dict, title_ch_dict, only_chapters_translated=False)
        post_text_to_server(book_name_en, introduction, chapters, lang)


# get dict of title translations from rabbi fischer
def collect_trans_titles_from_tsv(filename):
    title_trans_dict = {}
    with codecs.open(filename, 'r', 'utf-8') as f:
        first = True
        for line in f:
            if first:
                first = False
                continue

            heb, eng = line.split("\t")
            if heb[0] == "\"":
                heb = heb[1:-1].strip()
            if eng[0] == "\"":
                eng = eng[1:-1].strip()

            if re.search(':', heb):
                heb = u':'.join(heb.split(":")[1::]).strip()
            # heb = heb.replace("\"\"", "\"")
            heb = re.sub('"+', '"', heb)
            eng = re.sub('"+', '"', eng)
            eng = eng.strip()
            title_trans_dict[heb] = eng

    return title_trans_dict


# get dict of title changes from shmuel
def collect_ch_titles_from_tsv(filename):
    title_ch_dict = {}
    with codecs.open(filename, 'r', 'utf-8') as f:
        first = True
        for line in f:
            if first:
                first = False
                continue
            old, new, heb = line.split("\t")
            title_ch_dict[heb.strip()] = new

    return title_ch_dict


# scrape html from webpages if necessary
scraped_dir_name = 'New_Scraped_HTML'

def download_html(book_name, url_number, lang="he", scraped_dir_name=scraped_dir_name):
    try:
        os.mkdir("./{}/{}_{}".format(scraped_dir_name, book_name, lang))
    except OSError:
        pass

    if lang == "he":
        if url_number in [11, 6]:
            url = "https://ph.yhb.org.il/{}-00/".format('%02d' % url_number)
        elif url_number == 17:
            url = "https://ph.yhb.org.il/פתח-דבר/"
        else:
            url = "https://ph.yhb.org.il/{}-00-00/".format('%02d' % url_number)
        text = requests.get(url, cookies=jar).text
        file_path = "./{}/{}_he/Introduction.html".format(scraped_dir_name, book_name)
        if not os.path.exists(file_path):
            with codecs.open(file_path, "w+") as f:
                f.write(text)
    num_chpts = num_chapters[book_name]
    if book_name=="Simchat Habayit V\'Birchato" and lang == 'en':
        num_chpts = 9
    for curr_chapter in range(num_chpts):
        total_num_sections = get_num_sections(book_name, curr_chapter+1, lang, url_number, scrape=True)

        for num_section in range(total_num_sections):
            file_path = "./{}/{}_{}/Chapter_{}_Section_{}.html".format(scraped_dir_name, book_name, lang, curr_chapter+1, num_section+1)
            if os.path.exists(file_path):
                continue
            url = "https://ph.yhb.org.il/{}/{}-{}-{}/".format(lang, '%02d' % url_number, '%02d' % (curr_chapter+1), '%02d' % (num_section+1))
            text = requests.get(url, cookies=jar).text
            with codecs.open(file_path, "w") as f:
                f.write(text)

# determine the total number of sections in a given chapter
def get_num_sections(book_name, curr_chapter, lang, url_number, scrape=False, scraped_dir_name=scraped_dir_name):
    if scrape:
        url = "https://ph.yhb.org.il/{}/{}-{}-02/".format(lang, '%02d' % url_number, '%02d' % (curr_chapter))
        source = requests.get(url, cookies=jar).text
        if re.search("Not Found", BeautifulSoup(source, 'lxml').find("h1").text):
            url = "https://ph.yhb.org.il/{}/{}-{}-01/".format(lang, '%02d' % url_number, '%02d' % (curr_chapter))
            source = requests.get(url, cookies=jar).text
    else:
        filepath = "./{}/{}_{}/Chapter_{}_Section_1.html".format(scraped_dir_name, book_name, lang, curr_chapter)
        with codecs.open(filepath) as f:
            source = f.read()
            if re.search("Not Found", BeautifulSoup(source, 'lxml').find("h1").text):
                print("problem with file {}".format(filepath))
                url = ""
                # text = requests.get(url, cookies=jar).text
                # with codecs.open("./{}/{}_{}/Chapter_{}_Section_{}.html".format(lang, '%02d' % url_number, '%02d' % (curr_chapter), 1), "w") as f:
                #     f.write(text)
    soup = BeautifulSoup(source, 'lxml')
    num_sections = 0
    if lang=='he':
        catlist = soup.find_all("ul", class_='lcp_catlist')
        num_sections = len(catlist[0].find_all('li')) if len(catlist) > 0 else 0
    elif lang=='en' or lang in another_lang:
        num_sections = soup.find_all("div", style="display:block")
        for section in num_sections[1].find_all("li", class_="collapsing categories item"):
            None
        num_sections = int(section.a["href"].split("-")[2][:2].strip('/'))
    if not scrape and lang in another_lang:
        num_sections = len([x for x in os.listdir('./{}/{}_{}/'.format(scraped_dir_name, book_name, another_lang,)) if re.search('Chapter_{}_'.format(curr_chapter), x)])

    bias = 0

    if (book_name == "Prayer" and curr_chapter == 8 and lang == "he") or \
            (book_name == "Women's Prayer" and curr_chapter == 11 and lang == "he") or \
            (book_name == "Women's Prayer" and curr_chapter == 21 and lang == "he") or \
            (book_name == "Women's Prayer" and curr_chapter == 21 and lang == "he"):
        bias += 1

    if book_name=='Kashrut' and curr_chapter == 20:
        num_sections = 16
    return num_sections


# get the title of a given chapter
def get_chapter_title(book_name, curr_chapter, lang, url_number, scrape=False, scraped_dir_name=scraped_dir_name):
    if scrape:
        url = "https://ph.yhb.org.il/{}/{}-{}-01/".format(lang, '%02d' % url_number, '%02d' % (curr_chapter))
        source = requests.get(url, cookies=jar).text
    else:
        file = open("./{}/{}_{}/Chapter_{}_Section_1.html".format(scraped_dir_name,book_name, lang, curr_chapter))
        source = file.read()
    soup = BeautifulSoup(source, 'lxml')
    # chapter_title = soup.find("h1").text or soup.find("div", class_="entry-utility").a.text
    if lang == 'he':
        chapter_title_text = soup.find('a', class_=lambda x: x and x.startswith('elementor-post-info')).text
        chapter_title = chapter_title_text.replace('הלכה מתוך הפרק:', '').strip()
        chapter_title = chapter_title.replace('תפילת נשים', '').strip(' |')
        if re.search('|', chapter_title).group():
            print("NOTE: There is a pipe in {}, does this need fixing?".format(chapter_title))

    elif lang == 'en' or lang == 'es':
        list_option = [t.text for t in soup.findAll(class_='category') if re.search('[-:]', t.text.replace('–','-'))]
        chapter_title = list_option[0].replace('Chapter', '') if list_option else 'place_holder_chapter_name'
    return chapter_title


# parse through html of books to get text and titles
def get_soup(book_name, url_number, lang="he", another_lang=None):
    final_comment = False
    chapters = []
    introduction = []
    titles = {}
    ordered_chapter_titles = []
    aleph_bet = ""

    num_chpts = num_chapters[book_name]+1
    if book_name=="Simchat Habayit V\'Birchato" and lang == 'en':
        num_chpts = 10
    for curr_chapter in range(num_chpts):
        sections = []
        section_titles = []

        if curr_chapter == 0 and lang == "en" and book_name not in ["Prayer", "Women's Prayer", "Shabbat", "Zemanim"]:
            continue

        # if curr_chapter == 10 and lang == "en" and book_name == "Simchat Habayit V\'Birchato":
        #     continue

        if curr_chapter:
            total_num_sections = get_num_sections(book_name, curr_chapter, lang, url_number)
            chapter_title = get_chapter_title(book_name, curr_chapter, lang, url_number)
            ordered_chapter_titles.append(chapter_title)
            if chapter_title == '18 - Errors, Additions, and Omissions in the Amidah':
                total_num_sections = get_num_sections(book_name, curr_chapter, 'he', url_number)
        else:
            total_num_sections = 1

        for num_section in range(total_num_sections):
            if book_name == "Prayer" and curr_chapter == 0 and (lang == "en" or lang == "es"):
                paragraphs = ["p1", "p2", "p3", "p4", "p5", "p6", "p7", "p8", "p9", "p10"]
                continue
            if book_name == "Prayer" and curr_chapter == 8 and num_section+1 == 9 and another_lang == "es":
                paragraphs.append(["s9"])
                continue
            if book_name == "Prayer" and curr_chapter == 18 and num_section+1 in [8, 9, 10] and another_lang == "es":
                paragraphs.extend(["s8", "s9", "s10"])
                paragraphs = list(set(paragraphs))
                continue
            elif book_name == "Simchat Habayit V\'Birchato" and curr_chapter == 10 and lang == 'en':
                paragraphs = [["s1"], ["s2"], ["s3"], ["s4"], ["s5"], ["s6"], ["s7"], ["s8"], ["s9"], ["s10"]]
                continue
            elif book_name == "Women's Prayer" and curr_chapter == 0 and lang == "en":
                paragraphs = ["p1", "p2", "p3", "p4", "p5", "p6", "p7", "p8"]
                continue
            elif book_name == "Shabbat" and curr_chapter == 0 and lang == "en":
                paragraphs = ["p1", "p2", "p3", "p4", "p5", "p6", "p7", "p8", "p9", "p10", "p11", "p12", "p12", "p14"]
                continue
            elif book_name == "Zemanim" and curr_chapter == 0 and lang == "en":
                paragraphs = ["p1", "p2", "p3", "p4", "p5", "p6", "p7", "p8"]
                continue
            paragraphs = []
            if curr_chapter:
                if another_lang:
                    try:
                        filepath = "./{}/{}_{}/Chapter_{}_Section_{}.html".format(scraped_dir_name, book_name, another_lang, curr_chapter,
                                                                           num_section + 1)
                        file = open(filepath)
                    except FileNotFoundError:
                        print("File not found {}".format(filepath))
                        file = open(filepath.replace(another_lang, 'en'))
                else:
                    file = open("./{}/{}_{}/Chapter_{}_Section_{}.html".format(scraped_dir_name,book_name, lang, curr_chapter, num_section+1))
            else:
                file = open("./{}/{}_he/Introduction.html".format(scraped_dir_name, book_name))
            source = file.read()
            soup = BeautifulSoup(source, 'lxml')

            if curr_chapter:
                curr_section_title = soup.title.text.replace('פניני הלכה', '').strip(' –')
                curr_section_title = curr_section_title.replace('Peninei Halakha', '').strip(' |')
                curr_section_title = curr_section_title.replace('תפילת נשים', '').strip(' |')
                if re.search('|', curr_section_title).group():
                    print("NOTE: There is a pipe in {}, does this need fixing?".format(curr_section_title))
                if curr_chapter == 4 and num_section == 0 and book_name == "Shabbat" and lang == "en":
                    paragraphs.append("<strong>{}</strong> <sup>1</sup><i class=\"footnote\">Editor’s note: The term ner "
                                      "originally referred to an oil lamp. Nowadays, it has become common to speak "
                                      "of “Shabbat candles.” We have adopted this term because of the generic usage, "
                                      "but unless otherwise noted these laws apply to any source of illumination that "
                                      "is acceptable for use as nerot Shabbat.</i>".format(clean_text(curr_section_title)))
                    section_titles.append(clean_text(curr_section_title))
                else:
                    section_titles.append(curr_section_title)
                    # chapter_title and section_title for presenting in the first segment of the section
                    if chapter_title == 'פרק ח -הבדלה ומוצאי שבת':
                        chapter_title = 'פרק ח - הבדלה ומוצאי שבת'
                    chapter_title_pre = re.match(pre_num_letter_re, chapter_title).group(1)
                    try:
                        curr_section_title_pre = re.match(pre_num_letter_re, curr_section_title).group(1)
                    except AttributeError:
                        if re.search('העמוד לא נמצא',curr_section_title):
                            print("non scraped page chapter {}, section {}".format(curr_chapter, num_section+1))
                    paragraphs.append("<strong>{} / {}</strong>".format(chapter_title_pre, curr_section_title_pre))

            list_raw_texts_he =[d for d in
             soup.findAll("div", class_=lambda x: x and x.startswith('elementor-widget-container')) if
             len(d.findAll('p')) > 0]
            assert len(list_raw_texts_he) <= 1  # if list_raw_texts_he has more than one element we need to see whitch is the text one we are looking to upload and find the footnoteds in etc.
            raw_paragraphs = soup.find("div", class_="entry-content") or list_raw_texts_he[0]
            footnotes = get_footnotes(raw_paragraphs, curr_chapter, num_section)

            if soup.find("div", class_="entry-content"):
                first = True
            else:
                first = False
            sups_to_change = raw_paragraphs.find_all("sup")
            for sup in sups_to_change:
                if not re.search(u'\[', sup.text):
                    if (sup.attrs.get('class', []) == 'footnote') or (
                            sup.attrs.get('class', []) == ['footnote']):
                        sup.string = sup.text.replace(sup.text, "[{}]".format(sup.text))
                    elif sup.find('a'):
                        if (re.search('ref', sup.find('a').attrs.get('id')) or re.search('ref', sup.find('a').attrs.get('href'))):
                            sup.string = sup.text.replace(sup.text, "[{}]".format(sup.text))
                    else:
                        sup.decompose()
            for raw_paragraph in raw_paragraphs.find_all(["p", "h5", "h3", "h2", "blockquote", "div", "ul", "figure"], recursive=False):
                if not first or not curr_chapter:
                    if (raw_paragraph.img and raw_paragraph.name != "div") or raw_paragraph.name =='figure':
                        img_paragraphs = parse_pictures(raw_paragraph, curr_chapter, num_section)
                        if img_paragraphs:
                            paragraphs.extend(img_paragraphs)
                    if raw_paragraph.name == "blockquote":
                        paragraphs[len(paragraphs)-1] += " \"" + clean_text(raw_paragraph.p.text) + "\" "
                    elif raw_paragraph.text == "***":
                        final_comment = True
                    elif raw_paragraph.text == '\xa0':
                        continue
                    elif raw_paragraph.name == "ul":
                        bulletpoints = raw_paragraph.find_all("li")
                        for bulletpoint in bulletpoints:
                            paragraphs.append(aleph_bet + clean_text("\u25AA" + bulletpoint.text))
                            aleph_bet = ""
                    elif raw_paragraph.name == "div" and (raw_paragraph.img or (raw_paragraph.a and raw_paragraph.a.img)):
                        # if raw_paragraph["class"] == "wp-caption aligncenter":
                        a = raw_paragraph.find("a", recursive=False)
                        img = raw_paragraph.find("img", recursive=False)
                        if a:
                            if "https://ph.yhb.org.il/en/wp-content/uploads/" in a["href"]:
                                img_paragraphs = parse_pictures(a, curr_chapter, num_section, exception=True)
                                if img_paragraphs:
                                    paragraphs.extend(img_paragraphs)
                        elif img:
                            if "https://ph.yhb.org.il/en/wp-content/uploads/" in img["src"]:
                                img_paragraphs = parse_pictures(raw_paragraph, curr_chapter, num_section, exception=True)
                                if img_paragraphs:
                                    paragraphs.extend(img_paragraphs)
                    else:
                        if final_comment:
                            paragraphs.append("*** <br/><br/>" + clean_text(raw_paragraph.text))
                        elif (not raw_paragraph.img and raw_paragraph.name != "div") or raw_paragraph.name in ["h2", "h5", "h3"]:
                            if raw_paragraph.name == "h2":
                                paragraphs.append(aleph_bet + clean_text("<b>" + raw_paragraph.text + "</b>"))
                                aleph_bet = ""
                            else:
                                cleaned_text = clean_text(raw_paragraph.text)
                                if len(cleaned_text) > 0:
                                    if len(cleaned_text) == 1:
                                        aleph_bet = "{}. ".format(cleaned_text)
                                    else:
                                        paragraphs.append(aleph_bet + cleaned_text)
                                        aleph_bet = ""
                    potential_sups = raw_paragraph.find_all("sup")
                    potential_refs = [r for r in raw_paragraph.find_all('a') if re.search('ref.*?', r.get('id', ''))]
                    for sup in potential_sups+potential_refs:
                        if sup:
                            footnote_num_text = sup.a.text if sup.get('a') else sup.text
                            footnote_num = footnote_num_text.replace("]", "").replace("[", "")
                            try:
                                footnote_key = int(footnote_num)
                            except ValueError:
                                footnote_key = 0  # just a guess. this seems to work in the one case that this is relevant
                            try:
                                footnote_text = footnotes.get(footnote_key)
                                footnote_tag = "<sup>{}</sup><i class=\"footnote\">{}</i>".format(footnote_num, clean_text(footnote_text))
                                paragraphs[len(paragraphs)-1] = paragraphs[len(paragraphs)-1].replace("~~~[{}]~~~".format(footnote_num), footnote_tag)
                            except (TypeError, AttributeError):
                                continue
                first = False

            for num, p in enumerate(paragraphs):
                # paragraphs[num] = replace_for_linker(p)
                paragraphs[num] = last_text_clean(paragraphs[num])

            if curr_chapter:
                sections.append(paragraphs[:])
            print("section added")

        if curr_chapter:
            if book_name == "Prayer" and curr_chapter == 8 and lang == "en":
                pass
            if book_name == "Women's Prayer" and curr_chapter == 11 and lang == "he":
                sections.append(["p1", "p2", "p3", "p4", "p5", "p6", "p7", "p8", "p9"])
                section_titles.append("יא - איסור אמירת דברים שבקדושה מול ערווה")
            elif book_name == "Women's Prayer" and curr_chapter == 21:
                if lang == "he":
                    sections.append(["p1", "p2"])
                    section_titles.append("ה  – נשים בציצית")
                    sections.append(["p1", "p2", "p3", "p4", "p5", "p6"])
                    section_titles.append(" ו  – נשים בתפילין")
            elif book_name == "Simchat Habayit V'Birchato" and curr_chapter == 4 and lang == "he":
                section_titles.extend(["יב - נשים המסוללות", "יג - משכב זכור", "יד - הגורמים לגילוי יצר זה", " טו - מצוות החתונה","טז - האם צריך לספר לפני הנישואין", "יז - יחס התורה לחוטאים במשכב זכר"])
                sections.extend([["s12"], ["s13"], ["s14"], ["s15"], ["s16"], ["s17"]])
            elif book_name == "Simchat Habayit V\'Birchato" and curr_chapter == 10 and lang == 'en':
                sections = [["s1"], ["s2"], ["s3"], ["s4"], ["s5"], ["s6"], ["s7"], ["s8"], ["s9"], ["s10"]]
            chapters.append(sections[:])
            titles[chapter_title] = section_titles[:]
        else:
            introduction = paragraphs[:]
        print("chapter added")

    return introduction, chapters, ordered_chapter_titles, titles


# replaces citation abbreviations in text with full names for ref catching
def replace_for_linker(paragraph):
    new_p = paragraph
    changed = []  # list of tuples, before and after
    # שולחן ערוך
    sa_match = re.search(sa_re, paragraph)
    if sa_match:
        sa_change = sa_match.group().replace("\u05e9\u05d5\"\u05e2",
                                 "\u05e9\u05d5\"\u05e2 \u05d0\u05d5\"\u05d7")
        new_p = paragraph.replace(sa_match.group(), sa_change)
        sa_t = (sa_match.group(), sa_change)
        changed.append(sa_t)
    # משנה ברורה
    mb_match = re.search(mb_re, new_p)
    if mb_match:
        new_p = new_p.replace(mb_match.group(), mb_match.group().replace("\u05de\"\u05d1",
                                                                     "\u05de\u05e9\u05e0\u05d4 \u05d1\u05e8\u05d5\u05e8\u05d4"))
    # רמב"ם
    rm_match = re.search(rm_re, new_p)
    if rm_match:
        rm_change = rm_match.group().replace("\u05e8\u05de\u05d1\"\u05dd ",
                                                                             "\u05e8\u05de\u05d1\"\u05dd, \u05d4\u05dc\u05db\u05d5\u05ea ")
        new_p = new_p.replace(rm_match.group(), rm_change)
        rm_t = (rm_match.group(), rm_change)
        changed.append(rm_t)
    ah_match = re.search(ah_re, new_p)
    if ah_match:
        new_p = new_p.replace(ah_match.group(), ah_match.group().replace("\u05e2\u05e8\u05d5\u05d4\"\u05e9 ",
                                                                     "\u05e2\u05e8\u05d5\u05d4\"\u05e9, \u05d0\u05d5\u05e8\u05d7 \u05d7\u05d9\u05d9\u05dd "))
    rn_match = re.search(rn_re, new_p)
    if rn_match:
        new_p = new_p.replace(rn_match.group(), rn_match.group().replace("\u05e8\u05de\u05d1\"\u05df ",
                                                                         "\u05e8\u05de\u05d1\"\u05df \u05e2\u05dc "))
    ra_match = re.search(ra_re, new_p)
    if ra_match:
        new_p = new_p.replace(ra_match.group(), ra_match.group().replace("\u05e8\u05de\"\u05d0 ",
                                                                         "\u05e8\u05de\"\u05d0, \u05d0\u05d5\"\u05d7 "))
    ma_match = re.search(ma_re, new_p)
    if ma_match:
        new_p = new_p.replace(ma_match.group(), ma_match.group().replace("\u05de\"\u05d0 ",
                                                                    "\u05de\u05d2\u05df \u05d0\u05d1\u05e8\u05d4\u05dd "))
    return new_p, changed

def last_text_clean(paragraph):
    new_p = paragraph
    # strip '~~~' in any place it might have been inserted wrongly
    new_p = new_p.replace('~', '')
    # strip the 'alt' symbol from footnotes
    new_p = new_p.replace('↩', '')
    return new_p

# parses supplement chapter for index ha'am veha'aretz
def supplement_parser(scraped_dir_name=scraped_dir_name):
    sections = []
    goren_introduction = []
    all_siman_titles = {}
    section_titles = ["תשובות הרב שלמה גורן", "הרב אברהם שפירא", "הרב נחום אליעזר רבינוביץ\'"]
    aleph_bet = ""

    num_simanim = [12, 2, 1]
    for curr_section in range(3):
        simanim = []
        simanim_titles = []

        for num_siman in range(num_simanim[curr_section]):
            paragraphs = []
            while True:
                print('in scraped_dir_name loop')
                try:
                    if not curr_section and not num_siman:
                        file = open("./{}/The Nation and the Land_he/Chapter_11_Section_1_Introduction.html".format(scraped_dir_name))
                    elif not curr_section:
                        file = open("./{}/The Nation and the Land_he/Chapter_11_Section_{}_Siman_{}.html".format(scraped_dir_name,curr_section + 1, num_siman))
                    else:
                        file = open("./{}/The Nation and the Land_he/Chapter_11_Section_{}_Siman_{}.html".format(scraped_dir_name, curr_section + 1, num_siman + 1))
                    break
                except FileNotFoundError:
                    scraped_dir_name = 'Scraped_HTML'

            source = file.read()
            soup = BeautifulSoup(source, 'lxml')

            if num_siman or curr_section:
                curr_siman_title = soup.title.text.split("|")[0]
                simanim_titles.append(curr_siman_title)
                paragraphs.append("<strong>{}</strong>".format(curr_siman_title))

            raw_paragraphs = soup.find("div", class_="entry-content")
            footnotes = get_footnotes(raw_paragraphs)

            for raw_paragraph in raw_paragraphs.find_all(["p", "h5", "h3", "h2", "blockquote", "div", "ul"], recursive=False):
                if not first: # or not curr_chapter:
                    if raw_paragraph.name == "blockquote":
                        paragraphs[len(paragraphs) - 1] += " \"" + clean_text(raw_paragraph.p.text) + "\" "
                    elif raw_paragraph.text == u'\xa0':
                        continue
                    elif raw_paragraph.name == "ul":
                        bulletpoints = raw_paragraph.find_all("li")
                        for bulletpoint in bulletpoints:
                            paragraphs.append(aleph_bet + clean_text("\u25AA " + bulletpoint.text))
                            aleph_bet = ""
                    else:
                        if (not raw_paragraph.img and raw_paragraph.name != "div") or raw_paragraph.name in ["h2", "h5", "h3"]:
                            if raw_paragraph.name == "h2":
                                paragraphs.append(aleph_bet + clean_text("<b>" + raw_paragraph.text + "</b>"))
                                aleph_bet = ""
                            else:
                                cleaned_text = clean_text(raw_paragraph.text)
                                if len(cleaned_text) > 0:
                                    if len(cleaned_text) == 1:
                                        aleph_bet = "{}. ".format(cleaned_text)
                                    else:
                                        paragraphs.append(aleph_bet + cleaned_text)
                                        aleph_bet = ""
                    potential_sups = raw_paragraph.find_all("sup")
                    for sup in potential_sups:
                        if sup.a:
                            footnote_num = sup.a.text.replace("]", "").replace("[", "")
                            try:
                                footnote_text = footnotes[int(footnote_num)]
                                footnote_tag = "<sup>{}</sup><i class=\"footnote\">{}</i>".format(footnote_num,
                                                                                                   footnote_text)
                                paragraphs[len(paragraphs) - 1] += footnote_tag
                            except TypeError:
                                continue
                first = False
            if curr_section or num_siman:
                simanim.append(paragraphs[:])
            else:
                goren_introduction = paragraphs[:]
            print("section added")

        sections.append(simanim[:])
        all_siman_titles[section_titles[curr_section]] = simanim_titles[:]
        print("chapter added")

    return goren_introduction, sections, section_titles, all_siman_titles


# removes unwanted text from paragraphs
def clean_text(paragraph):
    paragraph = re.sub(footnote_re, r"~~~\1~~~", paragraph)
    paragraph = re.sub(img_text_re, "", paragraph).strip()
    paragraph = paragraph.replace("\u0124", "\u1E24").replace("\u0125", "\u1E25")

    return paragraph


# parses through pictures to get 64 code and any connected text
def parse_pictures(raw_paragraph, curr_chapter, curr_section, footnote=None, exception=False):
    paragraphs = []
    pic = 1
    for child in raw_paragraph.children:
        if isinstance(child, element.Tag):
            if child.name == "img" and ((child["src"][-3:] == "png") or exception or ("https://ph.yhb.org.il/en/wp-content/uploads/" in child["src"])):
                img_64_code = get_64_code(child, curr_chapter, curr_section, pic, footnote)
                if img_64_code:
                    pic += 1
                    paragraphs.append(img_64_code)
            elif child.name == "span":
                paragraphs[len(paragraphs)-1] += clean_text(child.text)
            elif child.name == "a" and ("https://ph.yhb.org.il/en/wp-content/uploads/" in child["href"] or "https://ph.yhb.org.il/wp-content/uploads/" in child["href"]):
                img_64_code = get_64_code(child.img, curr_chapter, curr_section, pic, footnote)
                if img_64_code:
                    pic += 1
                    paragraphs.append(img_64_code)
            elif child.name == "p" and child.parent.find("p", class_="wp-caption-text"):
                try:
                    paragraphs[len(paragraphs)-1] += "<br/>" + child.text
                except IndexError:
                    paragraphs.append(child.text)
            else:
                assert True
        elif isinstance(child, element.NavigableString):
            if len(child) > 2 and "max-width" not in child:
                paragraphs.append(clean_text(child))
        else:
            raise Exception("Something seems wrong. This exception means there is another type of child that was unaccounted for.")
    if not paragraphs:
        if raw_paragraph.name == "img" and raw_paragraph["src"][-3:] == "png":
            img_64_code = get_64_code(raw_paragraph, curr_chapter, curr_section, pic, footnote)
            if img_64_code:
                pic += 1
                paragraphs.append(img_64_code)
    return paragraphs


# translates png or jpg pictures to base64
def get_64_code(img_tag, curr_chapter, curr_section, pic_num, footnote):
    global pics
    if footnote:
        filename = "Chapter_{}_Section_{}_Picture_{}_footnote_{}_{}".format(curr_chapter, curr_section + 1, pic_num, footnote, pics)
    else:
        filename = "Chapter_{}_Section_{}_Picture_{}_{}".format(curr_chapter, curr_section + 1, pic_num, pics)
    pics += 1

    try:
        filename = "./Images/"+filename+".png"
        assert os.path.exists(filename)
    except (IOError, AssertionError):
        img_url = img_tag["src"]
        img = requests.get(img_url, cookies=jar)
        if img.status_code == 404:
            return 0
        with codecs.open(filename, "wb") as f:
            f.write(img.content)
        img = Image.open(filename)

        orig_height = img.size[1]
        orig_width = img.size[0]
        if orig_width > 550:
            percent = 550 / float(orig_width)
            height = int(float(orig_height) * float(percent))
            img = img.resize((550, height), PIL.Image.ANTIALIAS)
            img.save(filename)

    with codecs.open(filename, 'rb') as f:
        data = f.read()
    data = str(base64.b64encode(data))[2:-1]  # base64.encodebytes(data) #data.encode("base64")
    new_tag = '<img src="data:image/png;base64,{}">'.format(data)
    return new_tag


# parses through footnote sections in a given section
# extremely convoluted because html is extremely inconsistent when it comes to organizing footnotes
def get_footnotes(raw_paragraphs, curr_chapter=None, curr_section=None):

    footnotes_list = raw_paragraphs.findAll("div", class_="footnotes") + raw_paragraphs.findAll("div", class_=None)

    if not len(footnotes_list):
        return

    footnotes_list = [footnote for footnote in footnotes_list if (not footnote.hr or not footnote.find("div", class_=None)) and (footnote.ol or footnote.find("a", class_=None))]
    footnotes_dict = {}
    allowed_footnote_tags = ["span", "strong", "br", "em", "i", "b", "ol", "sup"]
    for footnote in footnotes_list:
        footnotes = footnote.children
        number = 0
        text = ""
        for footnote_line in footnotes:
            if isinstance(footnote_line, element.Tag):
                if footnote_line.name == "a":
                    if re.match(footnote_re, footnote_line.text) or re.search('ref', footnote_line.attrs.get('id', '')):
                        if number:
                            footnotes_dict[number] = text
                            text = ""
                        number = int(footnote_line.text.replace("[", "").replace("]", ""))
                    else:
                        text += footnote_line.text
                elif footnote_line.name == "ol":
                    alts = footnote_line.findAll("li")
                    for alt in alts:
                        if alt.has_attr("id"):
                            if number:
                                footnotes_dict[number] = text
                                text = ""
                            if alt.has_attr("id"):
                                number = int(alt["id"].split("-")[2])
                            elif alt.has_attr("value"):
                                number = int(alt["value"])
                            else:
                                assert False
                            for child in alt.children:
                                if isinstance(child, element.Tag):
                                    if child.name in ["p", "span"]:
                                        text += child.text
                                    elif child.name == "a" and child.has_attr("id") or child.has_attr("href"):
                                        None
                                    elif child.name == "br":
                                        text += "<br/>"
                                    elif child.name == "em":
                                        pass
                                    else:
                                        print("assert False")  # Todo: find the assert false problems when posting languages
                                        pass
                                elif isinstance(child, element.NavigableString):
                                    text += child
                                else:
                                    assert False
                        elif alt.has_attr("value") and alt.a:
                            if number:
                                footnotes_dict[number] = text
                                text = ""
                            if alt.a.has_attr("id"):
                                number = int(alt.a["id"].split("_")[1])
                            elif alt.a.has_attr("value"):
                                number = int(alt["value"])
                            else:
                                assert False
                            for child in alt.children:
                                if isinstance(child, element.Tag):
                                    if child.name in ["p", "span"]:
                                        text += child.text
                                    elif child.name == "a" and child.has_attr("id") or child.has_attr("href"):
                                        None
                                    else:
                                        assert False
                                elif isinstance(child, element.NavigableString):
                                    text += child
                                else:
                                    assert False
                        else:
                            text += alt.text
                elif footnote_line.name == "p":
                    if footnote_line.a:
                        for sub_footnote_line in footnote_line.children:
                            if isinstance(sub_footnote_line, element.Tag):
                                if sub_footnote_line.name == "a":
                                    if number:
                                        footnotes_dict[number] = text
                                        text = ""
                                    try:
                                        number = int(sub_footnote_line.text.replace("[", "").replace("]", ""))
                                    except ValueError:
                                        number = sub_footnote_line.text.replace("[", "").replace("]", "")
                                else:
                                    assert sub_footnote_line.name in allowed_footnote_tags or sub_footnote_line.name == "img" or sub_footnote_line.name == 'figure'
                                    if sub_footnote_line.name in allowed_footnote_tags:
                                        text += get_tag(sub_footnote_line)
                            else:
                                assert isinstance(sub_footnote_line, element.NavigableString)
                                text += sub_footnote_line
                    elif footnote_line.img:
                        img_paragraphs = parse_pictures(footnote_line.img, curr_chapter, curr_section, footnote=number)
                        if img_paragraphs:
                            for paragraph in img_paragraphs:
                                text += "<br/>" + paragraph
                    else:
                        if len(footnote_line.text) > 2:
                            text += "<br/>"
                            for text_child in footnote_line.children:
                                if isinstance(text_child, element.NavigableString):
                                    text += text_child
                                elif isinstance(text_child, element.Tag):
                                    assert text_child.name in allowed_footnote_tags

                                    text += text_child.text
                elif footnote_line.name in allowed_footnote_tags:
                    text += get_tag(footnote_line)
                elif footnote_line.name == "img":
                    img_paragraphs = parse_pictures(footnote_line, curr_chapter, curr_section, footnote=number)
                    if img_paragraphs:
                        for paragraph in img_paragraphs:
                            text += "<br/>" + paragraph
                elif footnote_line.name == "div" and footnote_line.img:
                    img_paragraphs = parse_pictures(footnote_line, curr_chapter, curr_section, footnote=number)
                    if img_paragraphs:
                        for paragraph in img_paragraphs:
                            text += "<br/>" + paragraph
                elif (footnote_line.name == "div" and footnote_line.text.strip() == "") or footnote_line.name == "hr":
                    None
                else:
                    print("failed on footnotes: \n {}".format(footnote_line.text))
                    # assert False
            elif isinstance(footnote_line, element.NavigableString):
                if len(footnote_line) > 2:
                    text += footnote_line
            else:
                raise Exception("There's a footnote child that's not a NavigableString or a p-tag")
        footnotes_dict[number] = text[1:]

    return footnotes_dict


# re-adds special tags to given text if necessary
def get_tag(tag):
    if tag.name in ["strong", "b"]:
        return "<strong>{}</strong>".format(tag.text)
    elif tag.name in ["em", "i"]:
        return "<em>{}</em>".format(tag.text)
    elif tag.name == "br":
        return "<br/>"
    elif tag.name == "sup":
        return "<sup>{}</sup>".format(tag.text)
    elif tag.name == "ol":
        return tag.li.text
    else:
        return tag.text


# makes index default structure and altstruct, and posts index to server
def post_index_to_server(en, he, ordered_chapter_titles, section_titles, title_translations_dict, title_changes_dict, both=False, supp_section_titles=None, sup_all_siman_titles=None, only_chapters_translated=False):

    # cleans and retrieves preferred title from title_changes_dict
    def clean_title(title, he=None, chapter=False):
        def clean_characters(title):
            new_title = title.strip().replace("\u2013", ":").replace("\u2019", "\'").replace("-", ":")\
                .replace("\u0125", "h").replace("\u201c", "\"").replace("\u201d", "\"")\
                .replace("\u0124", "H").replace("\xe0", "a").replace("\u1e25", "h").replace("\u1e24", "H")
            return new_title

        new_title = clean_characters(title)
        if new_title != title.strip() and not he:
            try:
                new_title = title_changes_dict[he.strip()]
                if re.search('""', new_title):
                    new_title =new_title.replace('""', '*').replace('"', '').replace('*','"')
            except KeyError:
                if print_titles_to_be_changed:
                    titles_to_print[0].append(title)
                    titles_to_print[1].append(new_title)
                    titles_to_print[2].append(he)

        if re.match(leading_zeros_re, new_title):
            new_title = re.match(leading_zeros_re, new_title).group(1)
        if re.match('^(\d+)\s*:(.*)$', new_title):
            new_title = '{}. {}'.format(re.match('^(\d+)\s*:', new_title).group(1), re.match('^(\d+)\s*:(.*)$', new_title).group(2))

        if chapter:
            new_title = new_title.replace(".", "")  # .replace("Chapter", "").strip()
        return new_title

    # default structure start
    root = SchemaNode()
    comm_en = "Peninei Halakhah, {}".format(en)
    comm_he = "פניני הלכה, {}".format(he)
    root.add_primary_titles(comm_en, comm_he)
    root.key = "Peninei Halakhah, {}".format(en)

    intro_node = JaggedArrayNode()
    intro_node.add_shared_term("Introduction")
    intro_node.key = "Introduction"
    intro_node.add_structure(["Paragraph"])
    intro_node.toc_zoom = 2
    intro_node.depth = 1
    root.append(intro_node)

    chapters_node = JaggedArrayNode()
    chapters_node.key = "default"
    chapters_node.default = True
    chapters_node.add_structure(["Chapter", "Section", "Paragraph"])
    chapters_node.depth = 3
    root.append(chapters_node)

    if en == "The Nation and the Land":
        supplement_node = SchemaNode()
        supplement_node.add_primary_titles("Supplement", "נספח")

        supplement_sections_en = ["Responsa of Rabbi Shlomo Goren", "Responsa of Rabbi Avraham Shapiro", "Responsa of Rabbi Nahum Rabinovitch"]

        for num, supplement_section_he in enumerate(supp_section_titles):
            if not num:
                supp_section_node = SchemaNode()
                supp_section_node.add_primary_titles(supplement_sections_en[num], supplement_section_he)
                supp_section_node_sub = JaggedArrayNode()
                supp_section_node_sub.add_shared_term("Introduction")
                supp_section_node_sub.key = "Introduction"
                supp_section_node_sub.add_structure(["Paragraph"])
                supp_section_node_sub.toc_zoom = 2
                supp_section_node_sub.depth = 1
                supp_section_node_sub.validate()
                supp_section_node.append(supp_section_node_sub)

                supp_section_node_sub = JaggedArrayNode()
                supp_section_node_sub.key = "default"
                supp_section_node_sub.default = True
                supp_section_node_sub.add_structure(["Siman", "Paragraph"])
                supp_section_node_sub.toc_zoom = 3
                supp_section_node_sub.depth = 2
                supp_section_node_sub.validate()
                supp_section_node.append(supp_section_node_sub)

                supp_section_node.validate()
                supplement_node.append(supp_section_node)
            else:
                supp_section_node = JaggedArrayNode()
                supp_section_node.add_primary_titles(supplement_sections_en[num], supplement_section_he)
                supp_section_node.add_structure(["Siman", "Paragraph"])
                supp_section_node.toc_zoom = 3
                supp_section_node.depth = 2
                supp_section_node.validate()
                supplement_node.append(supp_section_node)

        root.append(supplement_node)

    root.validate()
    # default structure end

    # altstruct start
    altstruct_nodes = []
    array_map = ArrayMapNode()
    array_map.wholeRef = "Peninei Halakhah, {}, Introduction".format(en)
    array_map.depth = 0
    array_map.includeSections = False
    array_map.refs = []
    array_map.add_shared_term("Introduction")
    array_map.key = "Introduction"
    array_map.validate()
    altstruct_nodes.append(array_map.serialize())

    if both:
        chapter_list = ordered_chapter_titles[0]
    else:
        chapter_list = ordered_chapter_titles

    for chap_num, he_chapter_title in enumerate(chapter_list):
        schema = SchemaNode()
        if both and curr_book !=12:  # rabbi fischer title code
            en_chapter_title = (ordered_chapter_titles[1][chap_num])
        elif title_translations_dict:
            en_chapter_title = title_translations_dict.get(he_chapter_title, "couldnt find the en_title")
            if not title_translations_dict.get(he_chapter_title, None):
                en_chapter_title = title_translations_dict.get(he_chapter_title.replace("-", "–"),
                                                               "couldnt find the en_title")
                if en_chapter_title == "couldnt find the en_title":
                    print("couldnt find the en_title in the translation tsv for {}".format(he_chapter_title))
                    with codecs.open('./kashrut_titles.csv', 'a') as f:
                        writer = csv.DictWriter(f, ['he_title'])
                        writer.writerow({'he_title': he_chapter_title})
        else:
            en_chapter_title = "{}".format(chap_num + 1)
        schema.add_primary_titles(clean_title(en_chapter_title, he_chapter_title, chapter=True), he_chapter_title)

        if both:
            if he_chapter_title == 'פרק ח -הבדלה ומוצאי שבת':
                he_chapter_title = 'פרק ח - הבדלה ומוצאי שבת'
            section_list = section_titles[0][he_chapter_title]
        else:
            section_list = section_titles[he_chapter_title]
        bias = 0
        for sec_num, he_section_title in enumerate(section_list):
            array_map = ArrayMapNode()
            if both and curr_book != 12:  # rabbi fischer title code
                try:
                    en_section_title = (section_titles[1][en_chapter_title][sec_num].encode('ascii', errors='ignore').decode())
                except IndexError:
                    print("can't find the english translation list {}, {}".format(section_titles[1][en_chapter_title], sec_num))
                    en_section_title = "{}".format(sec_num + 1 + bias)
            elif not only_chapters_translated and title_translations_dict:
                # he_section_title = re.sub(u'\u2013', u'-', he_section_title)
                # title_translations_dict.keys()[76], he_section_title
                en_section_title = title_translations_dict.get(he_section_title.strip(), 'waiting on Kashrut titles')
                if en_section_title == 'waiting on Kashrut titles':
                    with codecs.open('./kashrut_titles.csv', 'a') as f:
                        writer = csv.DictWriter(f, ['he_title'])
                        writer.writerow({'he_title':he_section_title.strip()})
            else:
                en_section_title = "{}".format(sec_num+1+bias)
            array_map.add_primary_titles(clean_title(en_section_title, he_section_title), he_section_title)
            array_map.depth = 0
            array_map.includeSections = False
            array_map.wholeRef = "Peninei Halakhah, {} {}:{}".format(en, chap_num+1, sec_num+1+bias)
            array_map.refs = []
            array_map.validate()
            schema.append(array_map)
        schema.validate()
        altstruct_nodes.append(schema.serialize())

    if en == "The Nation and the Land":
        supplement_node_alt = SchemaNode()
        supplement_node_alt.add_primary_titles("Supplement", "נספח")

        for sec_num, he_section_title in enumerate(supp_section_titles):

            sub_alt = SchemaNode()
            sub_alt.add_primary_titles(clean_title(supplement_sections_en[sec_num], he_section_title), he_section_title)
            if not sec_num:
                array_map = ArrayMapNode()
                array_map.add_shared_term("Introduction")
                array_map.key = "Introduction"
                array_map.depth = 0
                array_map.includeSections = False
                array_map.wholeRef = "Peninei Halakhah, {}, Supplement, Responsa of Rabbi Shlomo Goren, Introduction".format(en)
                array_map.refs = []
                array_map.validate()
                sub_alt.append(array_map)

                siman_titles = sup_all_siman_titles[he_section_title]
                for sim_num, he_siman_title in enumerate(siman_titles):
                    array_map = ArrayMapNode()
                    if not only_chapters_translated and title_translations_dict:  # rabbi fischer title code
                        en_siman_title = title_translations_dict[he_siman_title.strip()]
                    else:
                        en_siman_title = "Siman {}".format(sim_num + 1)
                    array_map.add_primary_titles(clean_title(en_siman_title, he_siman_title), he_siman_title)
                    array_map.depth = 0
                    array_map.includeSections = False
                    array_map.wholeRef = "Peninei Halakhah, {}, Supplement, {} {}".format(en, supplement_sections_en[sec_num], sim_num + 1)
                    array_map.refs = []
                    array_map.validate()
                    sub_alt.append(array_map)
            else:
                siman_titles = sup_all_siman_titles[he_section_title]
                for sim_num, he_siman_title in enumerate(siman_titles):
                    array_map = ArrayMapNode()
                    if not only_chapters_translated and title_translations_dict:  # rabbi fischer title code
                        en_siman_title = title_translations_dict[he_siman_title.strip()]
                    else:
                        en_siman_title = "Siman {}".format(sim_num + 1)
                    array_map.add_primary_titles(clean_title(en_siman_title, he_siman_title), he_siman_title)
                    array_map.depth = 0
                    array_map.includeSections = False
                    array_map.wholeRef = "Peninei Halakhah, {}, Supplement, {} {}".format(en, supplement_sections_en[sec_num], sim_num + 1)
                    array_map.refs = []
                    array_map.validate()
                    sub_alt.append(array_map)

            sub_alt.validate()
            supplement_node_alt.append(sub_alt)
        altstruct_nodes.append(supplement_node_alt.serialize())
        # altstruct end

    index = {
        "title": comm_en,
        "collective_title": "Peninei Halakhah",
        "schema": root.serialize(),
        "categories": ["Halakhah", "Peninei Halakhah"],
        "alt_structs": {"Topic": {"nodes": altstruct_nodes}}
    }

    post_index(index, server=SEFARIA_SERVER)


# posts main text, introduction, and supplement if necessary, to server
def post_text_to_server(book_name_en, introduction, chapters, lang, goren_intro=None, supp_sections=None):
    supplement_sections_en = ["Responsa of Rabbi Shlomo Goren", "Responsa of Rabbi Avraham Shapiro",
                              "Responsa of Rabbi Nahum Rabinovitch"]
    if lang == "he":
        vt = VERSION_TITLE_HE
        vs = VERSION_SOURCE_HE
    else:
        vt = VERSION_TITLE_EN
        vs = VERSION_SOURCE_EN

    send_text_chapters = {
        "text": chapters,
        "versionTitle": vt,
        "versionSource": vs,
        "language": lang
    }

    post_text("Peninei Halakhah, {}".format(book_name_en), send_text_chapters, server=SEFARIA_SERVER)


    send_text_intro = {
        "text": introduction,
        "versionTitle": vt,
        "versionSource": vs,
        "language": lang
    }

    post_text("Peninei Halakhah, {}, Introduction".format(book_name_en), send_text_intro, server=SEFARIA_SERVER)

    if book_name_en == "The Nation and the Land":
        for num, rav in enumerate(supplement_sections_en):
            send_text_supp = {
                "text": supp_sections[num],
                "versionTitle": vt,
                "versionSource": vs,
                "language": lang
            }

            post_text("Peninei Halakhah, {}, Supplement, {}".format(book_name_en, rav), send_text_supp, server=SEFARIA_SERVER)

        send_text_goren_intro = {
            "text": goren_intro,
            "versionTitle": vt,
            "versionSource": vs,
            "language": lang
        }

        post_text("Peninei Halakhah, {}, Supplement, Responsa of Rabbi Shlomo Goren, Introduction".format(book_name_en), send_text_goren_intro, server=SEFARIA_SERVER)


# parses to find, and posts to server, self links (le'eil and le'halan)
def post_self_links(bookname_en):
    links = []
    # finds and collects all self links
    def get_self_links(paragraph, intro=False, curr_para_num=None, ref_title=None):
        matches = re.findall(self_re, paragraph, overlapped=True)
        if matches:
            for match in matches:
                reference, chapter, section_s = match
                chapter_num = getGematria(chapter)
                section_s = section_s.replace(",", "").replace(";", "")

                if "-" in section_s:
                    all_sections = []
                    sec1, sec2 = section_s.split("-")
                    num1 = getGematria(sec1)
                    num2 = getGematria(sec2)
                    for sec_num in range(num2 - num1 + 1):
                        all_sections.append(sec_num + num1)
                else:
                    all_sections = [getGematria(section_s)]

                for section in all_sections:
                    if intro:
                        main_ref = "Peninei Halakhah, {}, Introduction {}".format(bookname_en, curr_para_num)
                    else:
                        main_ref = ref_title
                    other_ref = "Peninei Halakhah, {}, {}:{}".format(bookname_en, chapter_num, section)
                    link = {"refs": [main_ref, other_ref],
                            "generated_by": "peninei_halakhah_linker",
                            "auto": True,
                            "type": "Self"}
                    links.append(link)

    index = library.get_index("Peninei Halakhah, {}".format(bookname_en))
    introduction_refs = [ref for ref in index.all_section_refs()[0].all_subrefs()]
    introduction = [ref.text("he").text for ref in introduction_refs]
    chapter_refs = [ref for ref in index.all_segment_refs()[len(introduction):]]
    all_ref_titles = [ref.normal() for ref in chapter_refs]
    all_texts = [ref.text("he").text for ref in chapter_refs]
    all_text_and_ref_titles = zip(all_ref_titles, all_texts)

    ref_rows = []
    ref_dict = {'Ref': None,
               'match before': None,
               'caught before': None,
               'match after': None,
               'caught after': None}
    for p_num, paragraph in enumerate(introduction):
        get_self_links(paragraph, intro=True, curr_para_num=p_num+1)

    for ref_title, paragraph in all_text_and_ref_titles:
        get_self_links(paragraph, ref_title=ref_title)
        print(ref_title)
        changed_list = retroactive_replace_for_linking(paragraph, ref_title=ref_title)
        for tup in changed_list:

            ref_dict = {'Ref': ref_title,
                   'match before': tup[0],
                   'caught before': library.get_refs_in_string(tup[0]),
                   'match after': tup[1],
                   'caught after': library.get_refs_in_string(tup[1])}
            ref_dict.update({'num before/after': str(len(ref_dict['caught before'])) + " - " + str(len(ref_dict['caught after'])) + " = " + str(len(ref_dict['caught after'])-len(ref_dict['caught before']))})
            ref_rows.append(ref_dict)
    if links:
        links
        # post_link(links, server=SEFARIA_SERVER)


    with codecs.open('./changerefs.csv', 'w') as f:
        writer = csv.DictWriter(f, ['Ref', 'num before/after', 'match before', 'caught before', 'match after', 'caught after'])
        writer.writeheader()
        writer.writerows(ref_rows)

def retroactive_replace_for_linking(paragraph, ref_title=None):
    tc = TextChunk(Ref(ref_title), 'he', vtitle = VERSION_TITLE_HE)
    new_p, changed_list = replace_for_linker(paragraph)
    # tc.text = new_p
    # tc.save(force_save=True)
    return changed_list



if __name__ == "__main__":
    add_term("Peninei Halakhah", "פניני הלכה")
    add_category("Peninei Halakhah",["Halakhah", "Peninei Halakhah"], "פניני הלכה")
    he_book_list = [17]  # [5, 6, 7, 8, 9, 11, 12, 13, 14, 15]
    both_book_list = []  # [0, 1, 2, 3, 4, 10]
    langs = ["he", "both"]

    for lang, book_list in enumerate([he_book_list, both_book_list]):
        for curr_book in book_list:
            do_peninei_halakhah(books[curr_book][0], books[curr_book][1], books[curr_book][2], title_translations_tsv=tsv_translations_file, title_changes_tsv=tsv_title_changes_file, lang=langs[lang], only_chapters_translated=False)
            # library.refresh_index_record_in_cache("Peninei Halakhah, {}".format(books[curr_book][0]))
            # # FOR POSTING LINKS, FIRST RUN SCRIPT WITH THE LINE BELOW COMMENTED OUT, THEN RESET EACH INDEX, THEN RUN SCRIPT WITH THE ABOVE LINES COMMENTED OUT
            # post_self_links(books[curr_book][0])

    if print_titles_to_be_changed:
        for num, list in enumerate(titles_to_print):
            print("__________________{}___________________".format(titles_to_print_names[num]))
            for title in list:
                print(title)
