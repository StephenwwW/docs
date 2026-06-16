"""
build_index.py
==============
掃描 essentials/ 和 full/ 資料夾，根據 v4 知識樹分類，
標記 Dolch / Fry / NGSL 高頻標籤 + CEFR 六階段分級，輸出 index.json。

CEFR 標籤系統：
  A1  啟蒙與語音基石  — 高頻 500 字、生存情境
  A2  初級溝通實務    — 詞綴擴充至 1500 字、實用場景
  B1  中級獨立運用    — 抽象詞彙、敘事、半真實素材
  B2  中高級流利表達  — 慣用語、職場英語、批判思維
  C1  高級精通與精準  — 語域意識、學術文獻、即興演說
  C2  專業母語等級    — 修辭美學、專業領域、文化整合
  A1-A2 / B1-B2 / B2-C1  跨階過渡標籤
  CEFR-Academic           學術英語子標籤 (EAP)
  CEFR-Idiom              慣用語 / 片語動詞 (B2-C1)

執行方式：
    python build_index.py
    python build_index.py --config my_config.json
"""

import os
import re
import json
import argparse
from pathlib import Path

# 語義網絡引擎（同目錄下的 semantic_network.py）
try:
    import sys as _sys
    _sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from semantic_network import build_semantic_links, _build_phrase_index
    _SEMANTIC_ENABLED = True
except ImportError:
    _SEMANTIC_ENABLED = False
    def _build_phrase_index(_): return {}
    def build_semantic_links(w, pi, s): return {}

# ==========================================
# 知識樹分類定義 (v4.html 架構)
# ==========================================
KNOWLEDGE_TREE = [
    {
        "id": "0",
        "label": "LAYER 0｜詞頻基礎層",
        "color": "gray",
        "children": [
            {"id": "0-A", "label": "0-A｜高頻詞 High Frequency", "keywords": [
                "a","an","all","another","anybody","anyone","anything","each","everybody",
                "everyone","everything","he","her","hers","herself","him","his","i","it",
                "its","itself","me","my","myself","nobody","none","nothing","other","our",
                "ourselves","she","some","somebody","someone","something","that","the",
                "their","them","these","they","this","those","we","what","whatever",
                "which","who","whoever","whom","whose","you","your","yours","yourself",
                "any","every","about","after","again","against","ago","ahead","also",
                "although","always","among","anymore","apart","apparently","around","as",
                "at","back","because","before","between","but","by","come","day","did",
                "do","down","during","enough","even","ever","everywhere","exactly","find",
                "first","for","from","generally","get","give","go","good","had","has",
                "have","here","however","if","in","into","is","just","know","large",
                "last","left","let","like","little","long","look","made","make","many",
                "may","most","much","new","no","not","now","of","off","on","once","only",
                "open","or","out","over","own","part","people","place","put","read",
                "right","said","same","see","should","since","small","so","still","than",
                "then","there","think","through","time","to","today","together","too",
                "under","until","up","us","very","was","went","were","when","where",
                "while","with","word","would","write","yes","yet","your",
                "actually","almost","alone","along","already","anyway","anywhere",
                "approximately","certain","clearly","completely","currently","especially",
                "eventually","finally","fortunately","further","immediately","increasingly",
                "indeed","instead","lately","likely","mainly","meanwhile","merely","mostly",
                "nearly","normally","obviously","often","otherwise","particularly","perhaps",
                "probably","quickly","rather","recently","relatively","shortly","simply",
                "slightly","somehow","sometimes","soon","suddenly","therefore","thus",
                "totally","typically","ultimately","unfortunately","unusually","usually",
                "well","widely",
                "away","best","better","common","different","early","famous","full","general","great","high","important","less","live","low","main","more","national","natural","next","old","poor","possible","public","quite","ready","real","rich","short","simple","single","special","strong","sure","true","wide","whole","young","bad","basic","bright","central","clean","cold","complete","correct","deep","difficult","dirty","dry","easy","fair","fast","fine","firm","flat","foreign","formal","free","fresh","funny","gentle","global","hard","heavy","huge","human","ideal","kind","known","late","light","local","mad","male","mean","mental","middle","modern","narrow","necessary","normal","odd","original","pale","particular","past","patient","personal","physical","plain","pleasant","plural","popular","pretty","primary","private","proud","pure","quiet","rapid","reasonable","regular","serious","sharp","slow","smart","solid","southern","square","strange","strict","sweet","technical","thin","tight","tiny","total","traditional","typical","unique","utter","various","vast","vital","warm","wild","wrong","annual","appropriate","artificial","available","capable","chemical","complex","conscious","consistent","constant","continuous","creative","critical","crucial","current","dead","distinct","diverse","dramatic","dynamic","economic","effective","efficient","emotional","entire","equal","essential","evident","exact","excessive","existing","external","extreme","financial","fixed","flexible","frequent","fundamental","gradual","historic","horizontal","identical","illegal","immediate","industrial","inevitable","informal","initial","innovative","intellectual","intense","internal","international","invalid","invisible","joint","literal","logical","manual","marginal","massive","mature","mechanical","multiple","mutual","neutral","obvious","official","optional","oral","ordinary","organic","outstanding","overall","parallel","partial","passive","permanent","political","positive","potential","previous","principal","productive","professional","profound","progressive","prominent","proportional","protective","provisional","rational","realistic","regional","relevant","remarkable","remote","rigid","royal","rural","scientific","selective","sensitive","severe","significant","slight","stable","standard","static","statistical","strategic","substantial","superficial","superior","symbolic","systematic","tactical","temporal","theoretical","thermal","uniform","urban","valid","virtual","voluntary","widespread",
                "a d ",
                "can't cannot",
                "doesn't does not",
                "isn't is not",
                "wasn't was not",
                "won't will not",
                "wouldn't would not",
                "you're you are",
                "i'll i will",
                "we'll we will",
                "mr ",
                "mr mrs",
                "each other",
                "no offense",
                "all right"]},
            {"id": "0-B", "label": "0-B｜語法功能詞 Grammar Words", "keywords": [
                "above","across","against","along","among","apart","around","at","back",
                "behind","below","between","by","down","from","in","inside","into","near",
                "off","on","out","outside","over","through","to","toward","under","up",
                "upon","within","after","before","during","for","since","till","until",
                "although","and","as","because","but","either","if","neither","nor",
                "or","since","so","than","though","unless","when","where","whereas",
                "whether","while","both","few","several","such","am","are","be","been",
                "being","was","were","can","could","did","do","does","had","has","have",
                "may","might","must","shall","should","will","would","how","what","when",
                "where","which","who","whom","whose","why","ah","hey","hi","oh","wow",
            ]},
            {"id": "0-C", "label": "0-C｜高頻動詞核心 Core Verbs", "keywords": [
                "abandon","abandoning","abduct","accept","achieve","acquire","act","add",
                "address","admit","adopt","advance","advise","affect","afford","allow",
                "alter","analyze","announce","answer","apologize","appeal","appear",
                "apply","appoint","appreciate","approach","approve","argue","arise",
                "arrest","ask","assault","assess","assist","assume","attach","attack",
                "attempt","attend","attract","authorize","avoid","base","become","borrow",
                "break","brush","build","buy","calculate","call","cancel","carry","catch",
                "change","check","clean","clear","convey","cope","create","dance","decay",
                "die","direct","discard","disrupt","divert","draw","dream","drink","eat",
                "edit","enhance","enjoy","enlarge","evaluate","fall","focus","forbid",
                "harvest","heal","hear","help","hire","hold","hope","injure","interpret",
                "know","laugh","launch","leave","leverage","look","measure","navigate",
                "need","observe","offer","order","perceive","persevere","persist",
                "persuade","play","polish","proceed","promote","propose","provoke",
                "pursue","recall","reject","relax","remember","request","reset","resolve",
                "respect","respond","run","say","scan","scare","search","see","sell",
                "send","sever","sharpen","sing","sit","speak","specialize","spend",
                "start","step","strike","take","talk","teach","tell","test","threaten",
                "throw","turn","undergo","use","value","wake","walk","want","wash",
                "weep","work","breathe","rest","sleep","sweat","yawn","absorb",
                "accelerate","access","accomplish","accuse","ache","acknowledge","adapt",
                "adhere","admire","advocate","aid","aim","allege","amble","amplify",
                "annoy","anticipate","articulate","comply","confirm","contribute","convert",
                "count","define","delay","deliver","describe","detect","develop",
                "discover","discuss","distribute","enable","engage","ensure","establish",
                "exist","expand","experience","explain","express","extend","facilitate",
                "fail","follow","force","form","fulfill","gain","generate","grow","guide",
                "handle","identify","ignore","implement","improve","include","increase",
                "indicate","influence","inform","integrate","invest","involve","justify",
                "lead","learn","lose","maintain","manage","mention","motivate","obtain",
                "organize","overcome","perform","plan","prepare","prevent","process",
                "produce","protect","provide","reach","realize","recognize","reduce",
                "refer","release","remain","remove","replace","represent","require",
                "result","review","save","select","show","solve","store","strengthen",
                "submit","suggest","support","suppose","survive","transfer","transform",
                "translate","treat","understand","update","wait","ascend","climb","crawl",
                "creep","dash","descend","drift","drive","float","fly","gallop","glide",
                "jog","jump","leap","march","meander","plunge","ride","sail","skip",
                "slide","sneak","soar","sprint","stagger","stalk","stride","stroll",
                "stumble","swim","tiptoe","trot","wander","assemble","carve","clap",
                "clutch","craft","cut","drill","grab","grip","hammer","knit","pinch",
                "press","pull","push","screw","sew","squeeze","stitch","toss","twist",
                "weld","yank","collapse","compile","construct","demolish","design",
                "destroy","forge","modify","patch","renovate","restore","shatter","smash",
                "abandoned","abandoning","abducted","achieved","achieving","acted",
                "advanced","appeared","applied","argued","asked","attended","avoided",
                "became","broke","built","cancelled","changed","completed","continued",
                "created","decided","described","developed","done","eaten","established",
                "evaluated","felt","finished","gave","grown","happened","heard","helped",
                "improved","increased","involved","kept","known","learned","led","liked",
                "lived","meant","met","moved","noticed","organized","paid","planned",
                "played","produced","provided","reached","received","remained","removed",
                "required","resulted","returned","reviewed","seen","sent","shown",
                "started","stayed","stopped","studied","supported","taken","talked",
                "thought","told","tried","turned","waited","walked","wanted","worked",
                "written",
                "abuse","abused","abusing","accord","accompany","accompanied","adjust","adjusted","alarmed","analyse","analysed","analysing","arrange","arrive","arrived","assessing","assign","assisting","associate","assure","awaken","award","began","begin","believe","belong","bleed","blow","browse","bypass","came","care","cause","cite","clash","climbed","climbing","compare","comprise","conceive","condemn","congratulate","consume","control","copy","cried","cross","dancing","deal","denounce","deplore","derive","determine","devour","diagnose","disappoint","disarm","discovered","display","divided","drop","drown","embarrass","end","enlighten","enroll","examine","excrete","exercising","exert","expect","expel","experiment","faint","fart","fascinate","feeds","feel","fell","fight","fill","fit","flow","focused","forget","frighten","gasp","getting","going","gone","got","guess","gulp","having","held","highlight","hijack","hoped","hurt","illustrate","ignite","ingest","infect","insure","interrogate","intervene","investigate","invite","invoke","irritate","iterate","joined","jumped","kidnap","killed","lay","lend","lie","lifted","listen","live","located","losing","lost","masturbate","meet","menstruate","miss","move","neglect","nibble","occupy","oppress","passed","pedal","perspire","pick","poison","portray","practice","printed","procreate","progress","promise","publish","puke","pump","raid","raise","ran","rebound","reckon","record","repress","reproduce","restrain","revolt","rob","roar","rolled","running","secrete","serve","settled","shift","shiver","shouted","sigh","slept","smiled","sounded","steal","steer","stop","stab","stand","stay","suspend","terminate","throb","tilt","topple","transmit","transplant","trespass","tuck","vibrate","visit","waiting","watching","wear","win","wonder","wrote",
                "brake",
                "flown",
                "gasoline",
                "wax"]},
        ],
    },
    {
        "id": "A",
        "label": "Group A｜人與社會",
        "color": "coral",
        "children": [
            {"id": "A-1", "label": "A-1｜家庭 Family", "keywords": [
                "aunt","baby","brother","child","children","cousin","dad","daddy",
                "daughter","elder","family","father","granddaughter","grandfather",
                "grandma","grandmother","grandpa","grandson","husband","kid","mom",
                "mommy","mother","parents","sister","son","wife","widow","couple",
                "engagement","marriage","partner","relationship","spouse","babe",
                "darling","dear","honey","kiddo","adolescence","adult","age","anniversary",
                "birthday","birth","childhood","divorce","elderly","funeral","infant",
                "nonuplets","octuplets","orphan","pregnancy","quadruplets","remarriage",
                "sextuplets","superfecundation","superfetation","teenager","toddler",
                "triplets","weaning","wedding","youngster","youth","decuplets",
                "discipline","expression","household","interaction","love","rule",
                "estate","finance","inheritance","insurance","property","in-law",
                "sister-in-law","brother-in-law","father-in-law","mother-in-law",
                "upbringing","widowed","uncle","housewife","lady","girl","boy","man","woman","women","men","guy","junior","pal",
                "mommy mummy",
                "mr mrs",
                "growing up",
                "youth group",
                "the masses",
                "the other",
                "the others",
                "doll",
                "home",
                "party",
                "please",
                "gift",
                "favorite",
                "bag",
                "book",
                "picture"]},
            {"id": "A-2", "label": "A-2｜學校 School", "keywords": [
                "classroom","laboratory","library","classmate","librarian","principal",
                "professor","student","teacher","tutor","notebook","textbook","whiteboard",
                "biology","chemistry","curriculum","geography","history","literature",
                "mathematics","music","physical education","physics","science","subject",
                "all-nighter","education","elementary","learning","study","research",
                "revision","academic","admission","campus","college","degree","diploma",
                "dormitory","enrollment","graduate","scholarship","thesis","tuition",
                "university","assignment","essay","exercise","homework","lecture",
                "paragraph","quiz","task","worksheet","club","extracurricular","festival",
                "exchange","internship","evaluation","exam","grade","mark","score","test",
                "transcript","dyslexia","learning disability",
                "grammar","dictionary","syllable","verb","noun","vowel","consonant","suffix","numeral","symbol","sentence","composition","index","folder","workbook","publisher","booklet","bookmark","bookshelf","bookcase","bookstore","encyclopedia","novel","outline","summary","blackboard","marker","pencil","grades","classmates",
                "reading room",
                "school year",
                "study room",
                "before christ (bc)",
                "before common era (bce)",
                "republic of china era (roc era)",
                "arizona state university",
                "boston university",
                "brandeis university",
                "brown university",
                "california institute of technology (caltech)",
                "carnegie mellon university",
                "case western reserve university",
                "catholic university of america",
                "clark university",
                "cold spring harbor laboratory (cshl)",
                "columbia university",
                "cornell university",
                "dartmouth college",
                "duke university",
                "emory university",
                "fordham university",
                "george washington university",
                "georgia institute of technology",
                "harvard university",
                "icahn school of medicine at mount sinai",
                "indiana university bloomington",
                "iowa state university",
                "johns hopkins university",
                "mcgill university",
                "michigan state university",
                "new york university (nyu)",
                "northeastern university",
                "northwestern university",
                "ohio state university",
                "parsons school of design",
                "pennsylvania state university",
                "princeton university",
                "pratt institute",
                "purdue university",
                "rice university",
                "rutgers university–new brunswick",
                "stanford university",
                "stony brook university",
                "syracuse university",
                "texas a&m university",
                "the city university of new york (cuny)",
                "the cooper union",
                "the juilliard school",
                "the rockefeller university",
                "tufts university",
                "tulane university",
                "university at buffalo, suny",
                "university of arizona",
                "university of california, berkeley",
                "university of california, davis",
                "university of california, irvine",
                "university of california, los angeles",
                "university of california, riverside",
                "university of california, san diego",
                "university of california, santa barbara",
                "university of california, santa cruz",
                "university of chicago",
                "university of colorado boulder",
                "university of florida",
                "university of illinois urbana-champaign",
                "university of iowa",
                "university of kansas",
                "university of maryland, college park",
                "university of miami",
                "university of michigan",
                "university of minnesota, twin cities",
                "university of missouri",
                "university of nebraska–lincoln (unl)",
                "university of north carolina at chapel hill",
                "university of notre dame",
                "university of oregon",
                "university of pennsylvania (upenn)",
                "university of pittsburgh",
                "university of rochester",
                "university of south florida",
                "university of southern california (usc)",
                "university of texas at austin",
                "university of toronto",
                "university of utah",
                "university of virginia",
                "university of washington",
                "university of wisconsin–madison",
                "vanderbilt university",
                "washington university in st louis",
                "weill cornell medicine",
                "yale university",
                "adult education center",
                "associate degree",
                "bachelor's degree",
                "bartending school",
                "boarding school",
                "coding academy",
                "coding bootcamp",
                "community college",
                "comprehensive universities",
                "continuing education",
                "culinary academy",
                "culinary school",
                "culinary studio",
                "dance studio",
                "doctoral program",
                "driving school",
                "enrichment program",
                "graduate entry",
                "graduate school",
                "grammar school",
                "higher education",
                "junior college",
                "junior high school",
                "k-12 education",
                "language institute",
                "language school",
                "liberal arts college",
                "major universities",
                "master's degree",
                "medical school (med school)",
                "medical training continuum",
                "middle school",
                "minor league baseball (milb)",
                "non-degree education",
                "non-degree seeking",
                "nursery school",
                "phd program",
                "pharmacy school",
                "pre-k (pre-kindergarten)",
                "pre-school education",
                "primary school",
                "professional certification",
                "professional degree education",
                "professional schools",
                "professional training",
                "secondary school",
                "senior high school",
                "skill-based training",
                "tennis academy",
                "tertiary education",
                "university park",
                "vocational education",
                "vocational high school",
                "vocational training center",
                "yoga studio",
                "academic education",
                "academic paper",
                "academic research",
                "baking studio",
                "association of american universities (aau)",
                "ivy league",
                "second bachelor's degree",
                "non-reserved seat",
                "nontraditional student",
                "degree title"]},
            {"id": "A-3", "label": "A-3｜職場 Workplace", "keywords": [
                "actor","actress","admin","administration","agent","applicant","architect",
                "artist","baker","boss","chef","clerk","coach","colleague","cook",
                "designer","doctor","driver","employer","engineer","farmer","firefighter",
                "headhunter","industrialist","instructor","journalist","leader","mailman",
                "manager","mechanic","nurse","office worker","physician","pilot",
                "police officer","politician","programmer","recruiter","sailor",
                "salesman","salesperson","secretary","sheriff","shopkeeper","supervisor",
                "vendor","waiter","weaver","worker","writer","yeoman","yes-man",
                "zoologist","data scientist","developer","devops","product manager",
                "software engineer","ux designer","board","ceo","department","director",
                "executive","hierarchy","management","organization","team","brainstorm",
                "collaborate","delegate","discuss","draft","file","follow up",
                "keynote speech","organize","plan","present","report","review",
                "benefit","bonus","commission","compensation","commensurate","payroll",
                "pension","raise","salary","background check","bootcamp","career",
                "career path","career pivot","cover letter","hire","between jobs",
                "in between roles","inspection","interview","job","job description",
                "job offer","job search period","overstaffed","part-time","full-time",
                "profession","professional","promotion","resignation","resume","sideline",
                "status","time off","understaffed","vacancy","agenda","business letter",
                "email","meeting","memo","minutes","presentation","contract","labor law",
                "overtime","policy","regulation","union","worker rights",
                "workplace harassment","business model","funding","pitch","startup",
                "venture","onboarding","progress report","work from home",
                "accountant","adviser","attorney","author","broadcaster","cashier","coworker","dentist","editor","electrician","employee","exhibitor","founder","hostess","illustrator","interpreter","investigator","interviewer","interviewee","operator","pharmacist","philosopher","plumber","producer","publisher","realtor","supervise","veterinarian","waitress","workers","workplace","conference","performance","schedule","mission","document","income","invoice","reservation",
                "assembly line",
                "executive summary",
                "key takeaways",
                "personal development period",
                "bookstore chain",
                "office",
                "alternative",
                "brief",
                "continually",
                "invariably",
                "material",
                "prospect",
                "treasure",
                "brother industries",
                "canon inc",
                "daikin industries",
                "eneos holdings",
                "fast retailing co , ltd",
                "fanuc",
                "hitachi, ltd",
                "hmm co , ltd",
                "honda motor co , ltd",
                "idemitsu kosan",
                "imabari shipbuilding",
                "itochu corporation",
                "keyence",
                "kyocera corporation",
                "marubeni corporation",
                "mazda motor corporation",
                "megmilk snow brand",
                "mitsubishi corporation",
                "mitsui & co",
                "nintendo co , ltd",
                "nissan motor co , ltd",
                "nissin foods",
                "nitori holdings",
                "omron corporation",
                "orix",
                "panasonic holdings",
                "rakuten group",
                "sharp corporation",
                "softbank group",
                "sony group",
                "subaru corporation",
                "sumitomo corporation",
                "suntory holdings",
                "suzuki motor corporation",
                "toyota motor corporation",
                "toyota tsusho",
                "yamaha corporation",
                "yaskawa electric",
                "chubu electric power",
                "associated press (ap)",
                "bloomberg l p",
                "carnegie council for ethics in international affairs",
                "council on foreign relations (cfr)",
                "fox news",
                "new york academy of sciences",
                "new york daily news",
                "new york post",
                "the boston globe",
                "the christian science monitor",
                "the new york times (the times , nyt)",
                "the wall street journal (wsj)",
                "boston business journal",
                "boston herald",
                "career changer",
                "career transition",
                "lateral move",
                "business strategy",
                "project management",
                "value proposition",
                "strategic foresight",
                "proactive assessment",
                "proactive measures",
                "resume (cv)",
                "former member",
                "resigned or removed"]},
            {"id": "A-4", "label": "A-4｜社區/城市 Community", "keywords": [
                "apartment","building","condominium","house","neighborhood","suburb",
                "city hall","courthouse","fire station","hospital","police station",
                "post office","bank","café","convenience store","market","pharmacy",
                "restaurant","shop","supermarket","city","district","municipality",
                "prefecture","province","region","town","village","ambulance","community",
                "delivery","emergency","public service","social welfare","bus","metro",
                "subway","tram","trolley","compost","garbage","recycle","recyclable",
                "waste","infrastructure","midtown","park","public space","urban",
                "uptown","zoning","evacuation","first aid","rescue","shelter","survival",
                "crossroads","expressway","freeway","highway","interchange","junction","municipal","outskirts","provincial","railroad","rural","terminal","tollway","underground","underpass","uphill","downhill",
                "access ramp",
                "access point",
                "food court",
                "parking rack",
                "railway station",
                "repair shop",
                "storage room",
                "train station",
                "toll booth",
                "toll station",
                "belmont park",
                "botanical garden",
                "bryant park",
                "campus park",
                "central park",
                "city park",
                "cultural park",
                "dog park",
                "ecological park",
                "educational park",
                "fitness park",
                "forest park",
                "heritage park",
                "historical park",
                "imperial garden",
                "imperial palace",
                "linear park",
                "marine park",
                "memorial park",
                "national park",
                "neighborhood park",
                "play park",
                "pocket park",
                "public plaza",
                "rooftop park",
                "safari park",
                "science park",
                "skate park",
                "sports park",
                "technology park",
                "theme park",
                "urban park",
                "waterfront park",
                "wetland park",
                "wildlife park",
                "university park",
                "brooklyn bridge",
                "chrysler building",
                "empire state building",
                "flatiron building",
                "grand central terminal",
                "hudson yards",
                "one world trade center (freedom tower)",
                "radio city music hall",
                "rockefeller center",
                "statue of liberty",
                "summit one vanderbilt",
                "the high line",
                "times square",
                "top of the rock",
                "wall street",
                "washington square park",
                "ellis island",
                "governors island",
                "little island",
                "roosevelt island",
                "roosevelt island tramway",
                "fifth avenue",
                "broadway theatre district",
                "greenwich village",
                "little italy",
                "soho (south of houston street)",
                "dumbo (down under the manhattan bridge overpass",
                "designated city",
                "urban landscapes",
                "urban planning",
                "urban sprawl",
                "open spaces",
                "prefecture-level cities",
                "provincial capital",
                "regional district headquarters",
                "remote islands",
                "sub-provincial cities",
                "ddp (dongdaemun design plaza)",
                "myeongdong shopping street",
                "n seoul tower",
                "bukchon hanok village"]},
            {"id": "A-5", "label": "A-5｜醫院 Medical", "keywords": [
                "dermatologist","doctor","nurse","physician","psychiatrist","surgeon",
                "ankle","arm","body","cervix","ear","endometrium","erythrocyte","eye",
                "face","fallopian tube","foot","hand","head","heart","hormone","libido",
                "metabolism","myocardium","ovary","pore","skin","spine","teeth","toe",
                "uterus","vagina","chorion","bone","joint","ligament","muscle","skeleton",
                "tendon","brain","intestine","kidney","liver","lung","pancreas","stomach",
                "autonomic nervous system","gaba","nerve","neuron","rem","abrasion",
                "acute","addiction","bruise","burnout","chronic","disease","disorder",
                "illness","infection","injury","stroke","symptom","virus","amotivation",
                "anxiety","depression","insomnia","mental health","psychosis","stress",
                "acupuncture","diagnosis","operation","prescription","surgery","therapy",
                "treatment","vaccination","dha","supplement","vitamin","contraception",
                "puberty","reproductive","sexual health","tampon","antibiotic","dosage",
                "drug","medication","medicine","painkiller","side effect","appointment",
                "clinic","examination","first-aid kit","follow-up","outpatient",
                "registration","anti-aging","diet","exercise","fatigue","fitness",
                "hygiene","nutrition","prevention","wellness","memorial sloan kettering",
                "artery","blood","bones","chromosome","dna","earbuds","earplugs","ears","eyebrow","eyelid","eyes","fetus","fingers","forehead","gallbladder","hydrating","hydration","hypoallergenic","intestacy","intestines","intimacy","irritable","irritation","legs","limb","lip","lubrication","masturbation","moisture","monolid","mouth","nutrient","organ","organism","oxygen","perspire","prostate","rib","sexual","shoulder","stethoscope","thermometer","thumb","tonsil","tuberculosis","urine","vaccine","vein","weight",
                "cell vacuole",
                "dark circles",
                "double eyelid",
                "nucleic acid",
                "pill capsule",
                "synaptic vesicle",
                "urinary bladder",
                "finger oneself",
                "play with herself",
                "pleasure oneself",
                "rub one out",
                "touch oneself",
                "jack off jerk off",
                "flick the bean",
                "abnormality",
                "athlete",
                "brood",
                "amniotic sac",
                "autonomic nervous system (ans)",
                "autonomic nervous system balance",
                "binge eating",
                "brain fog",
                "brain oxygenation",
                "cerebral cortex",
                "cerebral oxygenation",
                "conjoined twins",
                "depressed mood",
                "dichorionic diamniotic, dcda",
                "dizygotic twins",
                "fraternal twins",
                "gaba (gamma-aminobutyric acid)",
                "identical sisters",
                "identical twins",
                "leptin stability",
                "lack of motivation",
                "low mood",
                "memorial sloan kettering cancer center (msk)",
                "mental drain",
                "mitochondrial energy",
                "monochorionic diamniotic, mcda",
                "monochorionic monoamniotic, mcma",
                "monozygotic twins",
                "multiple births",
                "sanitary pad",
                "stocking density",
                "vanishing twin",
                "selective breeding",
                "icahn school of medicine at mount sinai",
                "weill cornell medicine",
                "resident physician",
                "d d s    d m d  (doctor of dental surgery medicine)",
                "m d  (medical doctor)",
                "pharm d (doctor of pharmacy)",
                "j d  (juris doctor)"]},
            {"id": "A-6", "label": "A-6｜政治/軍事 Politics", "keywords": [
                "accuse","activist","aggressive","authority","democracy","election",
                "governance","law","legislation","parliament","policy","politician",
                "politics","senate","sovereignty","treaty","vote","quorate","quorum",
                "air defense system","air force","aircraft carrier","ammunition",
                "armored vehicle","army","artillery","ballistic missile","bayonet",
                "combat","defence","deployment","destroyer","fighter jet","grenade",
                "machine gun","missile defense","nuke","radar","rifle","submarine",
                "tank","warhead","weapon","interceptor","constitution","court",
                "jurisdiction","legal","rights","statute","alliance","ambassador",
                "diplomat","embassy","foreign affairs","international","sanction",
                "anarchy","asylum","ballot","bourgeois","citizenship","civilian","coup","defect","dissident","dynasty","exile","flag","guerrilla","hijack","institution","institutional","invade","invasion","militant","prison","protest","raid","realm","rebel","revolt","revolution","sedition","soldier","soldiers","spy","subversion","terror","treason","tribe","truce","veto","war",
                "avoid getting pulled over (by the police)",
                "national football conference, nfc",
                "national football league, nfl",
                "nfl draft",
                "prejudice",
                "irascible",
                "anti-aircraft gun",
                "atomic bomb (a-bomb)",
                "hydrogen bomb (h-bomb)",
                "japan maritime self-defense force (jmsdf)",
                "naval district",
                "naval port",
                "nuclear weapon",
                "sam (surface-to-air missile)",
                "autonomous region",
                "designated city",
                "provincial capital"]},
            {"id": "A-7", "label": "A-7｜體育/競技 Sports", "keywords": [
                "acrobatics","aikido","alpine skiing","archery","artistic swimming",
                "athletics","badminton","baseball","basketball","biathlon","bobsled",
                "bowling","boxing","cheerleading","chess","competition","cricket",
                "curling","cycling","dancesport","diving","esports","fencing",
                "figure skating","football","golf","gymnastics","handball","ice hockey",
                "judo","kabaddi","karate","kayaking","lacrosse","marathon",
                "mountaineering","paddleboarding","polo","racquetball","rappel","rowing",
                "rugby","sailing","skateboarding","skiing","snorkeling","softball",
                "sport climbing","sprinting","squash","sumo","surfing","swimming",
                "table tennis","taekwondo","tennis","teqball","triathlon","tug of war",
                "underwater sports","volleyball","wakeboarding","water polo","waterskiing",
                "weightlifting","wheelchair basketball","wrestling","wushu","yoga",
                "arena","bullpen","catcher","court","dugout","field","gym","pitch",
                "pool","stadium","track","championship","coach","endurance","inning",
                "outfielder","pitcher","roster","shortstop","slalom","streak","team",
                "tournament","warm up","bindings","crampons","galoshes","kayak",
                "snorkel","triathlon suit","wetsuit","wicking","air sports",
                "boules sports","roller sports","american football","track and field",
                "bikepacking","billiards","bobsleigh","bodybuilding","canoe","darts","dodgeball","draughts","equestrian","fistball","floorball","futsal","hockey","jiu-jitsu","jogging","kendo","kickboxing","korfball","kurash","luge","muaythai","netball","orienteering","padel","pickleball","pilates","playoffs","powerboating","powerlifting","sambo","savate","sepaktakraw","snowboarding","soccer","trampoline","triple-double","windsurfing",
                "american football conference, afc",
                "artistic gymnastics",
                "australian football",
                "beach soccer",
                "beach volleyball",
                "bmx racing freestyle",
                "canoeing and kayaking",
                "commute cycling",
                "contract bridge",
                "core training",
                "cross country skiing",
                "cross-country skiing",
                "cycling gloves",
                "cycling path",
                "electric bicycle",
                "elliptical training elliptical workout",
                "field hockey",
                "flying disc",
                "folding bicycle",
                "freestyle skiing",
                "go (game)",
                "gym workout",
                "hybrid bicycle",
                "ice skating",
                "indoor hockey",
                "inline skating",
                "jump ball",
                "modern pentathlon",
                "motorcycle racing",
                "mountain bike (mtb)",
                "muay thai",
                "national football conference, nfc",
                "national football league, nfl",
                "nba draft",
                "nba finals",
                "nfl draft",
                "paddle tennis",
                "pedal bike",
                "play-in tournament",
                "point guard (pg)",
                "power forward (pf)",
                "pro bowl",
                "pull-ups chin-ups",
                "push bike",
                "quarterback (qb)",
                "recumbent bicycle",
                "rhythmic gymnastics",
                "road bike",
                "rugby sevens",
                "running back (rb)",
                "scuba diving",
                "short track speed skating",
                "ski jumping",
                "ski mountaineering",
                "slam dunk",
                "slow jogging",
                "small forward (sf)",
                "soft tennis",
                "speed skating",
                "square dancing",
                "standing broad jump",
                "standing long jump",
                "stationary cycling",
                "strength training",
                "super bowl",
                "tai chi taiji",
                "three pointer beyond the arc",
                "weight training",
                "shooting guard (sg)",
                "tandem bicycle",
                "two-wheeler",
                "southwest division",
                "arizona diamondbacks",
                "atlanta braves",
                "baltimore orioles",
                "boston red sox",
                "chicago cubs",
                "chicago white sox",
                "cincinnati reds",
                "cleveland guardians",
                "colorado rockies",
                "detroit tigers",
                "houston astros",
                "kansas city royals",
                "los angeles angels",
                "los angeles dodgers",
                "miami marlins",
                "milwaukee brewers",
                "minnesota twins",
                "new york mets",
                "new york yankees",
                "oakland athletics (a's)",
                "philadelphia phillies",
                "pittsburgh pirates",
                "san diego padres",
                "san francisco giants",
                "seattle mariners",
                "st louis cardinals",
                "tampa bay rays",
                "texas rangers",
                "toronto blue jays",
                "washington nationals",
                "atlanta hawks",
                "boston celtics",
                "brooklyn nets",
                "charlotte hornets",
                "chicago bulls",
                "cleveland cavaliers",
                "dallas mavericks",
                "denver nuggets",
                "detroit pistons",
                "golden state warriors",
                "houston rockets",
                "indiana pacers",
                "los angeles clippers",
                "los angeles lakers",
                "memphis grizzlies",
                "miami heat",
                "milwaukee bucks",
                "minnesota timberwolves",
                "new orleans pelicans",
                "new york knicks",
                "oklahoma city thunder",
                "orlando magic",
                "philadelphia 76ers",
                "phoenix suns",
                "portland trail blazers",
                "sacramento kings",
                "san antonio spurs",
                "toronto raptors",
                "utah jazz",
                "washington wizards",
                "26-man active roster",
                "40-man roster",
                "acc   atlantic coast conference",
                "all-star game",
                "american league (al)",
                "aqueduct racetrack",
                "belmont park",
                "city of champions",
                "college world series (cws)",
                "collegiate sports venues",
                "dh (designated hitter)",
                "die-hard fans",
                "draft eligibility",
                "eastern conference",
                "era (earned run average)",
                "free agent (fa)",
                "gillette stadium",
                "green monster",
                "harvard stadium",
                "head of the charles regatta",
                "home run derby",
                "home team",
                "injured list (il)",
                "ivy league",
                "major arenas",
                "major league baseball   mlb",
                "metlife stadium",
                "national basketball association (nba)",
                "national league, nl",
                "ncaa division i baseball",
                "regular season",
                "seventh-inning stretch",
                "spring training",
                "triple crown",
                "universal dh",
                "us open",
                "visiting team   away team",
                "walk-off home run",
                "world series",
                "fenway park",
                "yankee stadium",
                "td garden",
                "citi field",
                "red bull arena",
                "agganis arena",
                "matthews arena",
                "metlife stadium",
                "gillette stadium",
                "madison square garden",
                "barclays center",
                "outdoor gym",
                "sports park",
                "skate park",
                "atlantic division",
                "central division",
                "pacific division",
                "northwest division",
                "southeast division",
                "western conference",
                "eastern conference",
                "sec (southeastern conference)",
                "boston marathon finish line",
                "head of the charles regatta"]},
            {"id": "A-8", "label": "A-8｜性別/身分 Gender & ID", "keywords": [
                "cisgender","gender","genderqueer","identity","nonbinary","transgender",
                "diversity","equality","inclusion","lgbtq","minority","representation",
                "copulate","intercourse","lesbian","procreate","reproductive"]},
        ],
    },
    {
        "id": "B",
        "label": "Group B｜自然與科學",
        "color": "teal",
        "children": [
            {"id": "B-1", "label": "B-1｜地球/地理 Earth", "keywords": [
                "altitude","archipelago","backcountry","backwater","bedrock","cave",
                "coastline","continent","crust","earth","earthquake","environment",
                "fault line","flood plain","headland","hill","horizon","island","lake",
                "landscape","latitude","mountain","ocean","peak","peninsula","plain",
                "plateau","precipice","quicksand","ridge","river","rock","sea","strand",
                "terrain","valley","volcano","crevasse","blowhole","erosion","geological",
                "geothermal","geyser","mineral","tectonic","border","boundary","capital",
                "country","nation","territory",
                "capricorn","celestial","constellation","cosmos","equinox","grassland","groundwater","plains","reservoir","solstice","tropic","waterfall","wilderness","northern","southern","western","eastern","overseas","soil","sand","stone","stream","jungle","swamp","canyon","cliff","dune","glacier"]},
            {"id": "B-2", "label": "B-2｜氣象/天氣 Weather", "keywords": [
                "acclimatization","air mass","airmass","atmosphere","avalanche",
                "bushfire","climate","cloud","cloudbank","cloudburst","cold front",
                "downdraft","dry season","dust storm","eyewall","flash flood","fog",
                "frost heave","hailstone","hailstorm","monsoon","rain","snow","storm",
                "sunscreen","temperature","turbulence","typhoon","weather","wind",
                "zephyr","ashfall","clear","cloudy","cool","dry","humid","overcast",
                "rainy","snowy","stormy","sunny","windy",
                "afterglow","lightning","thunder","tornado","torrent","tremor","twinkle","vapor","waves","freeze","mist","breeze","hail","blizzard","drizzle","dew","frost","cyclone","hurricane",
                "lunar eclipse",
                "solar eclipse",
                "golden hour",
                "meteor shower"]},
            {"id": "B-3", "label": "B-3｜外太空 Outer Space", "keywords": [
                "aerospace","galaxy","planet","space","star","sun","zenith",
                "space center","space debris","space junk","space probe","space program",
                "space shuttle","space station","spacecraft","spaceship","spacesuit",
                "telescope","universe","zero gravity","weightlessness","asteroid",
                "comet","jupiter","mars","mercury","meteor","moon","neptune","saturn",
                "supernova","ufo","uranus","venus","black hole","dark matter","orbit",
                "radiation","solar system","zodiac","alien",
                "astronaut","astronomer","atomic","electron","extraterrestrial","fission","gravity","ionic","light-year","meteorite","microgravity","molecules","nebula","nucleus","observatory","planets","pluto","rocket","rotation","satellite","shooting","stars","drone","vacuum",
                "houston rockets",
                "space capsule",
                "space shuttles",
                "artificial satellite",
                "launch pad",
                "light year",
                "lunar eclipse",
                "meteor shower",
                "milky way",
                "shooting star",
                "solar eclipse"]},
            {"id": "B-4", "label": "B-4｜動物 Animal", "keywords": [
                "animal","ant","bat","bird","breeding","bull","butterfly","carcass",
                "cat","dog","elephant","feral","fish","flock","fox","herd","horse",
                "insect","lion","maggot","mice","monkfish","pet","prey","ruminant",
                "salmon","shark","shrimp","tiger","whale","wildlife","zebra","zoo",
                "zoology","aquarium","aquatics","aquifer","hibernate","migrate",
                "predator",
                "badgers","bats","bear","bedbugs","bees","birds","booklice","butterflies","caimans","canine","capybaras","carnivore","cattle","centipedes","chipmunks","cicadas","cockroaches","coyotes","crickets","duck","earthworms","earwigs","fleas","flies","foxes","geckos","hedgehogs","hibernation","iguanas","insects","ladybugs","lizards","millipedes","mosquitoes","opossums","rabbit","raccoons","rats","robin","scorpion","sheep","silverfish","skunks","slugs","snakes","spiders","squirrel","squirrels","termites","toads","wasps","woodlice","yellowhammer","livestock","domesticated",
                "camel's hump",
                "carpet beetles",
                "clothes moths",
                "dust mites",
                "fur beetles",
                "hamster's cheek pouch",
                "pelican's pouch"]},
            {"id": "B-5", "label": "B-5｜植物/農業 Plant", "keywords": [
                "agriculture","almond","aubergine","banana","botany","bouquet","branch",
                "cashew","cherry","coconut","crop","dewdrop","flower","fruit",
                "greenhouse","harvest","leaf","lemon","pasture","pine","plant","pumpkin",
                "root","rose","seed","spinach","sweetsop","tree","vegetable","wood",
                "yam","yew","zucchini","rot","cultivate","farm","fertilizer","irrigation",
                "orchard","organic","plantation","sprinkle",
                "barley","buckwheat","bulgur","cereal","cornbread","cornmash","cornmeal","couscous","flatbread","grits","injera","kamut","ketupat","lentils","matooke","millet","oatmeal","oats","plantains","pseudocereals","rye","sago","semolina","sorghum","spelt","teff","ugali","yams","wheat","vine","vineyard",
                "grain bin",
                "oil tank",
                "gas cylinder",
                "gas holder",
                "corn"]},
            {"id": "B-6", "label": "B-6｜災害 Disaster", "keywords": [
                "flood","hurricane","landslide","tsunami","wildfire","accident",
                "explosion","fire","industrial accident","oil spill","pollution",
                "relief",
                "earthquake","tornado","volcanic","tremor","blizzard","drought","famine","epidemic","casualty","destruction","wreck","disaster"]},
        ],
    },
    {
        "id": "C",
        "label": "Group C｜物質與科技",
        "color": "blue",
        "children": [
            {"id": "C-1", "label": "C-1｜居家 Home & Living", "keywords": [
                "bathroom","bedroom","dining room","kitchen","living room","room","yard",
                "accessory","address","adjustable bed","alarm","alarm clock","amenity",
                "armchair","bathtub","bed","bench","box","bucket","bulb","carpet",
                "chair","clock","deck","desk","door","faucet","flashlight","furniture",
                "glass","heater","mirror","mug","pillow","roof","shaver","shower","sink",
                "slippers","sofa","staircase","stove","table","toilet","umbrella",
                "vacuum","vat","wall","window","yarn","zipper","patching","repair",
                "renovation","cleaning",
                "attic","basement","bath","bedsheet","bedspread","blanket","bookcase","bookshelf","bottle","cabinet","canvas","cardboard","cellar","closet","clothes","coat","comforter","cushion","drawer","duvet","envelope","folder","frame","fridge","garage","handbag","hardcover","headboard","helmet","hose","humidifier","jackets","lockbox","locker","mattress","mop","pail","pajamas","pantry","paperback","pillowcase","pocket","projector","purse","pyjamas","refrigerator","screen","shelf","shoes","suitcase","tablet","tarpaulin","terrace","thermos","trunk","tupperware","tv","utensil","valve","villa","wallet","workstation",
                "bed frame",
                "bed skirt",
                "bedside table",
                "body pillow",
                "bunk bed",
                "carpet beetles",
                "clothes moths",
                "cremation urn",
                "do the cleaning",
                "dust mites",
                "duvet cover",
                "electric blanket",
                "fabric softener",
                "file folder",
                "fitted sheet",
                "flat sheet",
                "fleece blanket",
                "food container",
                "garbage can",
                "glass jar",
                "ironing board",
                "latex mattress",
                "laundry basket",
                "linen sheet",
                "lint roller",
                "mason jar",
                "mattress protector",
                "mattress topper",
                "memory foam mattress",
                "memory foam pillow",
                "neck pillow",
                "official trash bag",
                "pencil box",
                "pencil case",
                "photo booth",
                "robot vacuum",
                "sleep mask",
                "sleeping bag",
                "smart bulb",
                "smart home",
                "smart lock",
                "smart thermostat",
                "sofa bed",
                "spring mattress",
                "stain remover",
                "storage room",
                "storage trunk",
                "throw pillow",
                "trash bag",
                "trash can",
                "travel pillow",
                "vacuum cleaner",
                "walk-in closet",
                "weighted blanket",
                "go to bed"]},
            {"id": "C-2", "label": "C-2｜飲食/料理 Culinary", "keywords": [
                "aftertaste","alcohol","alcoholic","aroma","baguette","boring",
                "breakfast","burger","cake","candies","canteen","cheese","coffee","cola",
                "cookie","cuisine","custard","delicious","dessert","dine in","dinner",
                "drink","empanada","food","gazpacho","grocery","hamburger","hungry",
                "ingredient","lemonade","lunch","meal","meat","menu","noodle","paella",
                "pancake","pasta","quiche","sake","sandwich","sauce","savory","seafood",
                "sip","steak","sugar","sushi","takeout","tasty","tea","to go","water",
                "yogurt","yolk","bodega","taste bad","bake","boil","chop","cook","fry",
                "grill","mix","roast","stir","steam","transport cafe","be thirsty",
                "calamari","chopsticks","congee","cornbread","cornmash","cornmeal","couscous","cup","dough","dumpling","flatbread","grits","injera","kamut","ketupat","lentils","lontong","matooke","millet","mochi","oatmeal","oats","plantains","potsticker","pseudocereals","ramen","rye","sago","schnitzel","semolina","snack","somen","sorghum","spelt","teff","tempura","tonkatsu","tortillas","ugali","udon","wonton","yams","eggs","groceries","rice",
                "baba's rice noodles",
                "bamboo rice",
                "banana leaf rice",
                "barley bread",
                "barley rice",
                "battered fish",
                "beat the meat",
                "black rice",
                "brown rice",
                "buckwheat noodles",
                "cassava flour",
                "cassava mash",
                "cellophane noodles",
                "cereal rice",
                "chicken nuggets",
                "chicken wings",
                "clay oven roll",
                "crispy chicken",
                "crispy shrimp",
                "curly fries",
                "deep-fried food",
                "donghong kiwifruit",
                "dragon boat",
                "durum wheat",
                "ee-fu noodles",
                "egg noodles",
                "einkorn wheat",
                "emmer wheat",
                "fish and chips",
                "five-grain rice",
                "flaked rice",
                "flat rice noodles",
                "french fries",
                "fried bacon",
                "fried cheese balls",
                "fried chicken",
                "fried crab",
                "fried dough sticks",
                "fried eggplant",
                "fried fish",
                "fried food",
                "fried mushrooms",
                "fried mussels",
                "fried okra",
                "fried onion rings",
                "fried oysters",
                "fried pork chop",
                "fried pumpkin",
                "fried rice cakes",
                "fried sausage",
                "fried scallops",
                "fried shrimp",
                "fried snack",
                "fried squid",
                "fried steak",
                "fried tofu",
                "fried wontons",
                "fried zucchini",
                "glass noodles",
                "glutinous rice",
                "hash browns",
                "honghua kiwifruit",
                "hongyang kiwifruit",
                "instant noodles",
                "jalapeño poppers",
                "jasmine rice",
                "karaage chicken",
                "konjac noodles",
                "laksa noodles",
                "lentil rice",
                "millet rice",
                "mixed grain rice",
                "mozzarella sticks",
                "mung bean noodles",
                "new year rice cake",
                "oat bread",
                "pita bread",
                "popcorn chicken",
                "popcorn shrimp",
                "potato croquettes",
                "potato wedges",
                "rat tail noodles",
                "red kiwifruit",
                "rice cake",
                "rice cakes",
                "rice noodles",
                "rice noodles (round)",
                "rice vermicelli",
                "rice vermicelli (thin)",
                "saffron rice",
                "sesame flatbread",
                "shahe fen",
                "shoestring fries",
                "shumai shaomai",
                "sorghum rice",
                "spiced rice",
                "spring rolls",
                "steamed bread",
                "steamed bun",
                "street food",
                "sweet potatoes",
                "tater tots",
                "tempura shrimp",
                "tempura vegetables",
                "vegetable fritters",
                "waffle fries",
                "wheat bread",
                "wheat noodles",
                "white rice",
                "wild rice",
                "wotou steamed corn bun",
                "yam mash",
                "yellow noodles",
                "zespri rubyred kiwifruit",
                "zongzi sticky rice dumpling",
                "eat breakfast",
                "have breakfast",
                "drink water",
                "food court",
                "deep-fried food",
                "food container",
                "basque pelota",
                "choke the chicken",
                "a bulb of garlic",
                "a clove of garlic",
                "a pinch of salt",
                "bar of chocolate",
                "bunch of grapes",
                "chili pepper",
                "chocolate box",
                "chocolate chip cookie",
                "ear of corn",
                "eight culinary traditions",
                "flying fish roe",
                "green beans",
                "head of lettuce",
                "ice cream",
                "loaf of bread",
                "monkfish liver",
                "red onion",
                "roll of toilet paper",
                "salmon roe",
                "slice of cake",
                "snow peas",
                "stick of butter",
                "tin can",
                "wedge of cheese",
                "culinary academy",
                "culinary school",
                "culinary studio",
                "baking studio",
                "cooking school",
                "can you go easy on the sauce",
                "make a meal"]},
            {"id": "C-3", "label": "C-3｜交通 Transport", "keywords": [
                "aircraft","airline","airplane","bicycle","bike","bus","car","carriage",
                "forklift","jeepney","plane","rv","sedan","ship","shuttle","train",
                "vessel","yacht","airport","aisle seat","arrival","boarding","booking",
                "bus station","bus stop","bus terminal","departure","electronic ticket",
                "fare","gate","platform","railway","reserved seat","round-trip ticket",
                "station announcement","ticket booth","ticket vending machine","traffic",
                "shinkansen","collision","detour","vehicle",
                "bikepacking","cockpit","commute","cyclist","drone","expressway","flyover","freeway","handlebar","highway","luge","pedal","peloton","rocket","route","saddle","tollway","trail","truck","tunnel","two-wheeler","underpass","wheels","bobsleigh",
                "bike computer",
                "bike lane",
                "bike light",
                "bike lock",
                "cardboard box",
                "cargo hold",
                "cargo spacecraft",
                "commute cycling",
                "cycling path",
                "electric bicycle",
                "exiting the highway safely",
                "external drive",
                "folding bicycle",
                "get off the highway take the exit",
                "get on the highway",
                "high-occupancy vehicle lane",
                "high-speed rail (hsr)",
                "hybrid bicycle",
                "mountain bike (mtb)",
                "national freeway",
                "on the road",
                "one-way ticket",
                "parking rack",
                "pay toll at the toll booth",
                "paying the toll",
                "pedal bike",
                "provincial highway",
                "push bike",
                "railway station",
                "rear rack",
                "recumbent bicycle",
                "relief road",
                "repair shop",
                "return ticket",
                "road bike",
                "round trip ticket",
                "shift gears",
                "shipping container",
                "single ticket",
                "speed limit",
                "tandem bicycle",
                "toll booth",
                "toll station",
                "train car",
                "train coach",
                "train station",
                "water bottle holder",
                "baggage rack",
                "cargo",
                "air",
                "aoimori railway",
                "eizan cable",
                "enshu railway",
                "hankai tramway",
                "hankyu corporation",
                "hanshin electric railway",
                "hakodate city tram",
                "hiroshima electric railway (hiroden)",
                "ikoma cable",
                "kagoshima city tram",
                "keihan electric railway",
                "keikyu electric railway",
                "keio corporation",
                "keisei electric railway",
                "kintetsu railway",
                "kumamoto city tram",
                "kyoto city subway",
                "nagoya railroad (meitetsu)",
                "nankai electric railway",
                "nishi-nippon railroad (nishitetsu)",
                "odakyu electric railway",
                "okinawa urban monorail",
                "osaka metro",
                "rokko cable",
                "romen densha",
                "seibu railway",
                "toyama chihō railway",
                "tobu railway",
                "toden arakawa line",
                "toei subway",
                "tokyo metro",
                "tokyu railways",
                "jr central",
                "jr east",
                "jr hokkaido",
                "jr kyushu",
                "jr shikoku",
                "jr west",
                "aerial tramway",
                "cable car",
                "limited express",
                "local train",
                "through service",
                "standard class",
                "non-reserved seat",
                "bullet train",
                "arrival time",
                "departure time",
                "fast pass",
                "package tour",
                "peak season",
                "travel logistics",
                "visa-free transit",
                "summit station",
                "public transit hub",
                "pyongyang metro",
                "air busan",
                "air seoul",
                "airasia japan",
                "ana (all nippon airways)",
                "asiana airlines",
                "bangkok airways",
                "batik air",
                "batik air malaysia",
                "cebu pacific air",
                "china airlines (cal)",
                "daily air",
                "eva air",
                "fuji dream airlines",
                "garuda indonesia",
                "jal (japan airlines)",
                "japan transocean air (jta)",
                "jeju air",
                "jetstar japan",
                "jin air",
                "korean air",
                "lion air",
                "malaysia airlines",
                "mandarin airlines",
                "nok air",
                "peach aviation",
                "philippine airlines",
                "philippines airasia",
                "singapore airlines",
                "skymark airlines",
                "solaseed air",
                "spring airlines japan",
                "starlux airlines",
                "t'way air",
                "thai airasia",
                "thai airways",
                "thai vietjet air",
                "tigerair taiwan",
                "uni air",
                "vietjet air",
                "vietnam airlines",
                "hub airport",
                "boutique airline",
                "low-cost carrier",
                "full service carrier",
                "hybrid carrier",
                "flag carrier",
                "ryukyu air commuter (rac)",
                "fast pass",
                "port of kisarazu",
                "port of kure",
                "port of maizuru",
                "port of naha",
                "port of ominato",
                "port of sasebo",
                "port of yokosuka",
                "rv (recreational vehicle)"]},
            {"id": "C-4", "label": "C-4｜科技/數位 Technology", "keywords": [
                "action camera","amplifier","aperture","app","application","battery",
                "desktop","electronics","fax","hardware","modem","phone","router",
                "scanner","software","television","tripod","viewfinder","zapper",
                "authentication","clickbait","cloud computing","consumer electronics",
                "download","internet","meme","netizen","network","password","gaming",
                "streaming","virtual","camera","film","lens","photography","algorithm",
                "artificial intelligence","chunking","classification","clustering",
                "collaborative","dimensionality","embedding","hierarchical",
                "machine learning","neural network","optimization","proxy","robustness",
                "semantic","sensitivity","tensor","transformer","vector","system",
                "tech","esports",
                "camcorder","controller","debug","device","e-reader","earbuds","ebook","editor","headphones","headset","keyboard","laptop","lite","lockbox","locker","microphone","mobile","monitor","mouse","online","offline","phablet","printer","projector","screen","server","smartphone","smartwatch","speaker","tablet","tv","ultrabook","webcam","workstation","zip",
                "answered the phone",
                "data center",
                "digital frame",
                "docking station",
                "feature phone",
                "flash drive",
                "game console",
                "gaming monitor",
                "gaming pc",
                "handheld console",
                "ink cartridge",
                "mini pc",
                "network switch",
                "smart band",
                "smart camera",
                "smart home",
                "smart lock",
                "smart speaker",
                "smart thermostat",
                "smart tv",
                "thumb drive",
                "vr headset",
                "who answered the phone",
                "authentication monitoring",
                "base station",
                "digital media",
                "digital payment",
                "electronic device",
                "entry systems",
                "extension cord",
                "it operations",
                "light bulbs",
                "login detection",
                "runtime monitoring",
                "site monitoring",
                "system architecture",
                "system upgrade",
                "time monitoring",
                "streaming platform",
                "television network"]},
            {"id": "C-5", "label": "C-5｜建築/工程 Architecture", "keywords": [
                "abutment","arch","beam","bridge","column","concrete","foundation",
                "pillar","structure","drill","hammer","kit","peg","saw","screw","tool",
                "cement","glass","metal","steel","timber","carat","diamond","jewel",
                "wristband","construction","renovation","blueprint","scaffold",
                "brick","buckle","corrugated","crank","frame","gear","lever","ramp","rim","rope","saddle","scrap","silo","terrace","tilt","trunk","tunnel","valve","ventilation","villa","wrench",
                "arch bridge",
                "arch of triumph",
                "aomori bay bridge",
                "architectural change",
                "architectural design",
                "bascule bridge",
                "beam bridge",
                "bridge system",
                "cable car",
                "cable-stayed bridge",
                "cantilever bridge",
                "expansion joint",
                "floor plan",
                "grand bridge",
                "hamanako bridge",
                "highway bridge",
                "hirado bridge",
                "ikema bridge",
                "interior design",
                "irabu bridge",
                "kouri bridge",
                "kurima bridge",
                "landscape bridge",
                "load capacity",
                "main cable",
                "movable bridges",
                "ohnaruto bridge",
                "pedestrian bridge",
                "prestressed concrete",
                "railway bridge",
                "rainbow bridge",
                "reinforced concrete",
                "road bridge",
                "saikai bridge",
                "sea-crossing bridge",
                "seismic design",
                "shin-saikai bridge",
                "steel frame",
                "steel structure",
                "structural engineer",
                "structural types",
                "suspension bridge",
                "suspending cable",
                "swing bridge",
                "tied-arch bridge",
                "traditional architecture",
                "transporter bridge",
                "truss bridge",
                "tsunoshima bridge",
                "vertical-lift bridge",
                "vine bridge",
                "viaduct",
                "civil engineer",
                "electrical engineer",
                "landscape architect",
                "infrastructure expansion",
                "height restriction",
                "hakucho bridge",
                "kanmon bridge",
                "kintai bridge",
                "tatara bridge",
                "togetsukyo bridge",
                "yokohama bay bridge",
                "brooklyn bridge",
                "tokyo bay aqua-line",
                "tokyo gate bridge"]},
            {"id": "C-6", "label": "C-6｜電力/物理 Physics", "keywords": [
                "acceleration","acoustics","aerodynamics","allotrope","aqueous",
                "buoyancy","capacitance","catalyst","chemistry","covalent","dielectric",
                "dispersion","emulsion","energy","friction","gradient","hygroscopic",
                "impedance","kinetic","mechanics","modulation","momentum","oscillation",
                "oxidation","physics","polarity","polymer","refraction","resonance",
                "tensile","thermodynamics","velocity","viscosity","zinc","electricity",
                "circuit","voltage","current","resistance","magnetism","force",
                "atomic","chemical","electron","fission","fluid","ionic","magnet","magnitude","microgravity","molecules","nucleus","oxygen","rotation","substances","thermometer","vapor","vibrate","vibration",
                "atomic bomb (a-bomb)",
                "chubu electric power",
                "chubu electric power mirai tower",
                "chugoku electric power",
                "electric circuit",
                "electric power",
                "electric shock",
                "electric vehicle (ev)",
                "electrical engineer",
                "electrical wiring",
                "electricity bill",
                "extension cord",
                "high voltage electricity",
                "hokkaido electric power",
                "hydrogen bomb (h-bomb)",
                "kansai electric power (kepco)",
                "kyushu electric power",
                "nuclear weapon",
                "okinawa electric power",
                "power grid",
                "power off",
                "power on",
                "power plant",
                "power station",
                "power supply",
                "plug in",
                "run on electricity",
                "shikoku electric power",
                "taiwan power company (taipower)",
                "tohoku electric power",
                "korea electric power",
                "korea electric power corporation (kepco)"]},
        ],
    },
    {
        "id": "D",
        "label": "Group D｜文化與地域",
        "color": "purple",
        "children": [
            {"id": "D-1", "label": "D-1｜日本 Japan", "keywords": [
                "aichi","akita","chugoku","ehime","fukui","fukushima","gifu","gunma",
                "hyogo","ishikawa","iwate","kagawa","kanagawa","kansai","kanto",
                "kumamoto","mie","nagano","nagasaki","nara","niigata","saitama","shiga",
                "shimane","tokushima","toyama","wakayama","yamagata","yamaguchi",
                "akashi kaikyo bridge","arima onsen","beppu jigoku onsen","dogo onsen",
                "dotonbori","enoshima","fushimi inari","genbikei gorge","gero onsen",
                "ginzan onsen","gion district","higashi chaya","kusatsu onsen",
                "matsushima","matsuyama castle","minato mirai","naruto whirlpools",
                "noboribetsu","nyuto onsen","oshino hakkai","ouchi-juku","seto ohashi",
                "takachiho gorge","tottori sand dunes","tsurugaoka hachimangu",
                "shinkansen","japanese","japan","anime","calligraphy","kimono","manga",
                "origami","samurai","zen","fukuoka","nagoya","sendai","osaka","tokyo",
                "kendo","mochi","ramen","somen","tempura","tonkatsu","udon","yufuin",
                "aomori bay bridge",
                "asahiyama zoo",
                "atsuta jingu shrine",
                "beppu ropeway",
                "bizan ropeway",
                "bitchu matsuyama castle",
                "bureau of waterworks, tokyo metropolitan government",
                "central alps komagatake ropeway",
                "chiba port tower",
                "choshi port tower",
                "chubu electric power",
                "chubu electric power mirai tower",
                "chugoku electric power",
                "chuson-ji golden hall",
                "daisetsuzan sounkyo kurodake ropeway",
                "dazaifu tenmangu shrine",
                "dogo onsen honkan",
                "eizan cable",
                "enshu railway",
                "former hokkaido government office",
                "furano lavender fields",
                "fushimi inari taisha",
                "goryokaku park",
                "goryokaku tower",
                "hakkoda ropeway",
                "hakodate city tram",
                "hakone komagatake ropeway",
                "hakone ropeway",
                "hakucho bridge",
                "hankai tramway",
                "hankyu corporation",
                "hanshin electric railway",
                "higashi chaya district",
                "higashiyama sky tower",
                "hikone castle",
                "himeji castle",
                "hirado bridge",
                "hirosaki park",
                "hiroshima electric railway (hiroden)",
                "hiroshima peace memorial park",
                "hokkaido electric power",
                "huis ten bosch",
                "ikema bridge",
                "ikoma cable",
                "imabari shipbuilding",
                "innoshima bridge",
                "inuyama castle",
                "irabu bridge",
                "iriomote island",
                "itsukushima shrine (miyajima)",
                "izu peninsula",
                "izumo taisha shrine",
                "jal (japan airlines)",
                "japan maritime self-defense force (jmsdf)",
                "japan transocean air (jta)",
                "jr central",
                "jr east",
                "jr hokkaido",
                "jr kyushu",
                "jr shikoku",
                "jr west",
                "kagoshima city tram",
                "kaikyo yume tower",
                "kanazawa castle",
                "kankakei ropeway",
                "kanmon bridge",
                "kansai electric power (kepco)",
                "kasuga taisha shrine",
                "katsurahama beach",
                "keihan electric railway",
                "keikyu electric railway",
                "keio corporation",
                "keisei electric railway",
                "kenrokuen garden",
                "kintai bridge",
                "kintetsu railway",
                "kiyomizu-dera temple",
                "kobe harborland",
                "kobe port tower",
                "kochi castle",
                "kokusai dori street",
                "kotohira-gu shrine",
                "kouri bridge",
                "kumamoto castle",
                "kumamoto city tram",
                "kurashiki bikan historical quarter",
                "kurima bridge",
                "kurushima kaikyo bridge",
                "kyocera corporation",
                "kyoto city subway",
                "kyushu electric power",
                "lake akan",
                "lake ashi",
                "lake kawaguchi",
                "lake towada",
                "lake toya",
                "marugame castle",
                "maruoka castle",
                "matsue castle",
                "matsumoto castle",
                "matsuyama castle (iyo)",
                "matsuyama castle ropeway",
                "meiji jingu shrine",
                "minobusan ropeway",
                "miyajima ropeway",
                "mt aso ropeway",
                "mt hakodate ropeway",
                "mt moiwa ropeway",
                "mt tsukuba cable car",
                "mt usu ropeway",
                "nachi falls",
                "nagasaki inasayama ropeway",
                "nagoya castle",
                "nagoya railroad (meitetsu)",
                "nankai electric railway",
                "nara park",
                "nebuta museum wa rasse",
                "nidec kyoto tower",
                "nijo castle",
                "nikko shiranesan ropeway",
                "nikko toshogu shrine",
                "nishi-nippon railroad (nishitetsu)",
                "noboribetsu jigokudani",
                "nyuto onsen-kyo",
                "odakyu electric railway",
                "ohnaruto bridge",
                "ohori park",
                "oirase mountain stream",
                "okayama korakuen garden",
                "okinawa churaumi aquarium",
                "okinawa electric power",
                "okinawa urban monorail",
                "osaka castle",
                "osaka gas",
                "osaka metro",
                "otaru canal",
                "ote shitetsu",
                "rokko cable",
                "romen densha",
                "saikai bridge",
                "sapporo clock tower",
                "sapporo tv tower",
                "seibu railway",
                "senkoji ropeway",
                "senso-ji temple",
                "seto ohashi bridge",
                "shikoku electric power",
                "shin-saikai bridge",
                "shinhotaka ropeway",
                "shinjuku gyoen national garden",
                "shirakawa-go gassho-style village",
                "shiretoko national park",
                "shirogane blue pond",
                "shodoshima olive park",
                "shuri castle",
                "taketomi island water buffalo cart",
                "tatara bridge",
                "tateyama kurobe alpine route",
                "tateyama ropeway",
                "td garden",
                "tobu railway",
                "todai-ji temple",
                "toden arakawa line",
                "toei subway",
                "togetsukyo bridge",
                "tohoku electric power",
                "tojinbo tower",
                "tokyo bay aqua-line",
                "tokyo disneyland",
                "tokyo electron",
                "tokyo gas",
                "tokyo gate bridge",
                "tokyo metro",
                "tokyo skytree",
                "tokyo tower",
                "tokyu railways",
                "toyama chihō railway",
                "tsuruga castle",
                "tsutenkaku tower",
                "tsunoshima bridge",
                "ueno park",
                "umeda sky building",
                "universal studios japan (usj)",
                "uwajima castle",
                "yakushima (jomon sugi)",
                "yamadera temple",
                "yokohama air cabin",
                "yokohama bay bridge",
                "yokohama marine tower",
                "yonaha maehama beach (miyako island)",
                "zao ropeway",
                "zao snow monsters",
                "mount fuji",
                "mount aso",
                "mount koya",
                "mount takao",
                "nagoya city subway",
                "fukuoka city subway",
                "sendai city subway",
                "nok air",
                "ryukyu air commuter (rac)",
                "port of naha",
                "mount hakodate night view"]},
            {"id": "D-2", "label": "D-2｜中華文化 Chinese", "keywords": [
                "anhui","chongqing","dongguan","fujian","gansu","guangxi","harbin",
                "hebei","heilongjiang","hubei","jiangsu","jilin","jinan","liaoning",
                "macao","ningbo","ningxia","shaanxi","shanxi","tianjin","wuhan",
                "xinjiang","zhejiang","suzhou","longmen","ancestor tablet","dragon dance",
                "incense","joss paper","lantern festival","mazu","qixi festival",
                "shangsi festival","temple fair","totem","xiayuan festival","taiwan",
                "taiwanese","chinese","mandarin","mien","beijing","shanghai","guangzhou",
                "dynasty","lontong","wonton","potsticker",
                "ancient city of pingyao",
                "ancient town",
                "chengdu research base of giant panda breeding",
                "classical gardens of suzhou",
                "cultural heritage",
                "cultural relics",
                "giant panda sanctuary",
                "guangxi zhuang autonomous region",
                "hong kong sar",
                "humble administrator's garden",
                "incense bundle",
                "inner mongolia autonomous region",
                "intangible cultural heritage",
                "jilin city",
                "jiuzhaigou valley",
                "karst topography",
                "longmen grottoes",
                "macao sar (macau)",
                "mogao caves",
                "mount huangshan",
                "mount kumgang",
                "mount myohyang",
                "mount paektu",
                "ningxia hui autonomous region",
                "old town of lijiang",
                "oriental pearl tower",
                "qian dynasty",
                "qing dynasty",
                "qixi festival or chinese valentine's day",
                "qinghai-tibet plateau",
                "shangsi festival or double third festival",
                "sichuan basin",
                "tang dynasty",
                "terracotta army",
                "the bund",
                "the forbidden city",
                "the great wall",
                "the li river",
                "the palace museum (the forbidden city)",
                "the potala palace",
                "the summer palace",
                "the temple of heaven",
                "the three gorges",
                "tibet autonomous region (xizang)",
                "water town",
                "west lake",
                "xinjiang uygur autonomous region",
                "zhangjiajie national forest park",
                "taiwan power company (taipower)",
                "formosa petrochemical corporation",
                "cpc corporation, taiwan",
                "英文 台灣行政區",
                "mandarin chinese",
                "mandarin airlines",
                "china airlines (cal)"]},
            {"id": "D-3", "label": "D-3｜歐美文化 Western", "keywords": [
                "america","egypt","france","greece","norway","christmas","halloween",
                "thanksgiving","yule","arabic","bengali","english","french","greek",
                "hindi","indonesian","korean","marathi","portuguese","russian","spanish",
                "urdu","vietnamese","zulu","yoruba","korea","incheon","kaesong","wonsan",
                "dmz","panmunjom","seokguram grotto","seongsan ilchulbong","philippines",
                "jeepney","national september 11 memorial","geopark","manzamo","europe",
                "africa","australia","canada","germany","italy","japan","uk","usa",
                "british","cornbread","fellowship","irish","italian","schnitzel","yuletide","tortillas","flatbread","couscous",
                "bukchon hanok village",
                "bulguksa temple",
                "cheomseongdae observatory",
                "dmz (demilitarized zone)",
                "dmz (demilitarized zone)   panmunjom",
                "gamcheon culture village",
                "gyeongbokgung palace",
                "haedong yonggungsa temple",
                "haeundae beach",
                "haeundae beach english lesson",
                "hallasan national park",
                "jeju island",
                "manjanggul cave",
                "nami island",
                "n seoul tower",
                "seoraksan national park",
                "kim il sung square",
                "kumsusan palace of the sun",
                "mansu hill grand monument",
                "mount kumgang",
                "mount myohyang",
                "mount paektu",
                "pyongyang metro",
                "taedong river",
                "tomb of king kongmin",
                "west sea barrage",
                "bnk busan bank",
                "daesang corporation",
                "doosan group",
                "hanwha group",
                "hd hyundai heavy industries",
                "hyundai mobis",
                "hyundai motor group",
                "hyundai motor ulsan plant",
                "hyundai steel",
                "kakao corp",
                "kb financial group",
                "kia corporation",
                "korea electric power",
                "korea electric power corporation (kepco)",
                "korea ginseng corp",
                "korean air",
                "kumho tire",
                "lg group",
                "lotte group",
                "naver corporation",
                "posco",
                "samsung biologics",
                "samsung electronics",
                "samsung group",
                "shinhan financial group",
                "sk group",
                "air busan",
                "air seoul",
                "asiana airlines",
                "jeju air",
                "jin air",
                "t'way air",
                "korean air",
                "cebu pacific air",
                "philippine airlines",
                "philippines airasia",
                "airasia japan",
                "batik air",
                "batik air malaysia",
                "garuda indonesia",
                "lion air",
                "malaysia airlines",
                "nok air",
                "peach aviation",
                "thai airasia",
                "thai airways",
                "thai vietjet air",
                "vietjet air",
                "vietnam airlines",
                "singapore airlines",
                "neuschwanstein castle",
                "egyptian arabic",
                "modern standard arabic",
                "standard german",
                "nigerian pidgin"]},
            {"id": "D-4", "label": "D-4｜宗教/信仰 Religion", "keywords": [
                "altar","blessing","deity","exorcism","god","monk","nun","pilgrimage",
                "prayer","preacher","priest","religion","ritual","sacred","scriptures",
                "sermon","shrine","sutras","temple","worship","yom kippur",
                "zoroastrianism","ziggurat","zoroastrian","faith","belief","church",
                "mosque","buddhism","christianity","hinduism","islam","judaism",
                "anarchy","eternal","enlighten","enlightenment","tribe","yuletide","zealot",
                "ancestral tablet",
                "atsuta jingu shrine",
                "bulguksa temple",
                "cultural heritage",
                "cultural relics",
                "dazaifu tenmangu shrine",
                "exorcism document",
                "fushimi inari taisha",
                "gods procession",
                "guardian spirit",
                "haedong yonggungsa temple",
                "incense bundle",
                "intangible cultural heritage",
                "izumo taisha shrine",
                "kasuga taisha shrine",
                "kotohira-gu shrine",
                "kiyomizu-dera temple",
                "meiji jingu shrine",
                "nijo castle",
                "nikko toshogu shrine",
                "pilgrimage route",
                "prayer petition",
                "qixi festival or chinese valentine's day",
                "ritual petition",
                "sacred dance",
                "seokguram grotto",
                "senso-ji temple",
                "shangsi festival or double third festival",
                "shadow play",
                "shadow puppetry",
                "shuri castle",
                "tea ceremony",
                "the temple of heaven",
                "the potala palace",
                "todai-ji temple",
                "traditional architecture",
                "tsurugaoka hachimangu",
                "yamadera temple"]},
            {"id": "D-5", "label": "D-5｜藝術/娛樂 Arts", "keywords": [
                "aesthetics","album","ambience","art","artist","castanets","chorus",
                "dance","duet","exhibition","folk art","folk music","lyrics","melody",
                "movie","music","musical instruments","painting","performer","photograph",
                "portrait","quintet","show","singer","song","symphonic","proscenium",
                "quickstep","animation","arcade","bumper cars","carousel","drop tower",
                "ferris wheel","roller coaster","water ride","bloopers","dubbing",
                "script","teaser","vogue","film","television","entertainment",
                "biopic","broadcasted","broadcaster","broadcasting","comic","drama","flamenco","juxtaposition","magic","poem","radio","rhythm","saga","tempo","theatrical","storytelling","tv","violin","violinist",
                "mixed martial arts (mma)",
                "opera house",
                "publishing house",
                "complete edition",
                "simplified version",
                "behind the scenes (bts)",
                "broadway theatre district",
                "casting director",
                "cgi (computer-generated imagery",
                "carnegie hall",
                "director of photography (dp dop)",
                "drama series",
                "elephant parade",
                "green screen",
                "historical drama",
                "iconic landmarks",
                "iconic sport",
                "lincoln center for the performing arts",
                "limited series",
                "long take",
                "madison square garden",
                "metropolitan opera house",
                "period drama",
                "post-credits scene",
                "prime time",
                "production roles",
                "puppet show",
                "reality show",
                "rockefeller center",
                "sci-fi (science fiction)",
                "sequence shot",
                "solomon r guggenheim museum",
                "stages of production",
                "street dance hip-hop dance",
                "the metropolitan opera",
                "the new york public library for the performing arts",
                "tv series",
                "universal studios japan (usj)",
                "variety show",
                "voice actor (va)",
                "whitney museum of american art",
                "american museum of natural history (amnh)"]},
            {"id": "D-6", "label": "D-6｜旅遊 Travel", "keywords": [
                "abroad","adventure","backpack","base camp","booking","campsite",
                "concierge","destination","excursion","expedition","glamping","guide",
                "hotel","itinerary","journey","luggage","map","passport","picnic",
                "signpost","souvenir","tent","tour","tourism","tourist","travel","trip",
                "yurt","groundsheet","vacation","resort","hostel","sightseeing",
                "camping","ecotourism","hiker","hiking","longevity","nepal","sabbatical","sherpa","touring","trail","trek","yufuin",
                "round trip ticket",
                "travel pillow",
                "laundry basket",
                "leave home",
                "ancient city of pingyao",
                "ancient town",
                "chengdu research base of giant panda breeding",
                "goryokaku park",
                "hallasan national park",
                "huis ten bosch",
                "ibusuki sand bath",
                "imperial palace",
                "jigokudani monkey park",
                "kabira bay",
                "manjanggul cave",
                "mogao caves",
                "neuschwanstein castle",
                "shirakawa-go gassho-style village",
                "shiretoko national park",
                "the forbidden city",
                "the great wall",
                "the palace museum (the forbidden city)",
                "the summer palace",
                "traditional architecture",
                "zhangjiajie national forest park",
                "seoraksan national park",
                "summit station"]},
        ],
    },
    {
        "id": "E",
        "label": "Group E｜學術與抽象",
        "color": "amber",
        "children": [
            {"id": "E-1", "label": "E-1｜數學/邏輯 Math", "keywords": [
                "accuracy","accurate","addition","amount","angle","arithmetic","average",
                "axiom","calculate","fraction","geometry","gross","logic","math",
                "measure","number","parameter","percentage","proportion","statistics",
                "sum","syntax","zero","equation","algebra","calculus","probability",
                "theorem","variable","formula","proof","integer","decimal",
                "cents","circle","diagonal","dollars","eight","equal","five","four","gravity","hundred","inches","million","numeral","parallel","pattern","percent","perpendicular","pounds","rotation","six","seven","square","ten","thousand","thousands","three","total","triangle","two"]},
            {"id": "E-2", "label": "E-2｜時間/節奏 Time", "keywords": [
                "afternoon","april","august","autumn","blue hour","century","dawn","day",
                "daybreak","december","dusk","evening","february","friday","future",
                "gloaming","history","hour","january","july","june","late","midday",
                "midnight","midsummer","midwinter","minute","monday","month","morning",
                "night","noon","november","october","period","saturday","season",
                "september","spring","summer","sundown","sunday","sunrise","sunset",
                "thursday","time","today","tuesday","twilight","wednesday","winter",
                "witching hour","year","yesterday","dead of night","dawn","daybreak",
                "deadline","delay","duration","early","eternal","finally","forenoon","frequently","hiatus","interim","lasting","moment","pause","quarterly","recently","rhythm","routine","schedule","seasonal","sequence","shift","shortly","temporary","thereafter","timetable","transition","weekly","yearly","solstice","equinox","tempo",
                "all the time",
                "earlier today",
                "golden hour",
                "night light",
                "years old",
                "nap"]},
            {"id": "E-3", "label": "E-3｜空間/方位 Space & Direction", "keywords": [
                "above","across","adjacent","area","around","beside","boundary","center",
                "close","corner","depth","direction","distance","down","east","edge",
                "far","height","inside","left","length","location","north","opposite",
                "outside","position","right","side","south","space","surface","up",
                "west","width","zone","horizontal","vertical","diagonal","angle",
                "coordinate","axis","point","dimension",
                "aside","backyard","beyond","bottom","ceiling","central","circle","closet","corridor","downhill","entrance","external","gap","ground","interior","junction","loop","lower","margin","middle","outskirts","overhead","overseas","perpendicular","pit","plain","realm","remote","ridge","rim","slope","storage","surrounding","terrace","territory","top","tunnel","underneath","uphill","upward","vicinity","void",
                "path",
                "scale",
                "sign",
                "speed",
                "safe",
                "without",
                "action",
                "iron"]},
            {"id": "E-4", "label": "E-4｜學術 Academic", "keywords": [
                "abstract","theory","hypothesis","methodology","analysis","argument",
                "evidence","conclusion","citation","bibliography","peer review",
                "interdisciplinary","dissertation","abstracted","abstracting",
                "abbreviation","grammar","phonetics","vocabulary","morphology",
                "ethics","ideology","philosophy","principle","truth","behavior",
                "cognition","consciousness","instinct","memory","motivation",
                "perception","self-awareness","subconscious","archeology","anthropology",
                "sociology","psychology","economics","linguistics","rhetoric",
                "curriculum","academic","comply","contemplate","core","credibility",
                "ability","ambition","ambivalent","annual","apparent","appropriate","archive","artificial","aspect","assessment","assumption","capability","cause","cite","composition","concept","consistently","contradiction","creative","creativity","criteria","demonstration","determination","development","dictionary","difference","discovery","distinction","efficacy","element","enlightenment","experiment","exposure","fact","figure","fundamental","guarantee","guideline","illustrate","incentive","index","individual","information","insight","institution","interpretation","investigation","issue","judgment","juxtaposition","knowledge","literature","logic","magnitude","matter","means","method","mission","misconception","model","novel","outline","perspective","phenomenon","philosopher","pioneer","platitude","problem","process","project","publication","purpose","question","reality","realm","reason","record","reliability","resolution","response","result","role","scope","section","sequence","society","solution","statement","subsequent","survey","symbol","synopsis","system","transition","validity","version","vision","zeitgeist",
                "academic education",
                "academic paper",
                "academic research",
                "before the common era",
                "before christ (bc)",
                "republic of china era (roc era)",
                "semantic tree",
                "what-if analysis",
                "hypothetical scenario",
                "expected situations",
                "functional categories",
                "proactive measures",
                "information architect"]},
        ],
    },
    {
        "id": "F",
        "label": "Group F｜情感與溝通",
        "color": "pink",
        "children": [
            {"id": "F-1", "label": "F-1｜情感 Emotion", "keywords": [
                "adamant","afraid","anger","angry","anxious","ashamed","attitude",
                "atrocious","awe","awful","calm","courage","curiosity","empathy",
                "enthusiastic","euphoria","fear","furious","glad","happy","jealous",
                "lamentable","mad","optimism","passion","pride","sad","scare","smile",
                "stress","thrill","vociferous","weep","yearn","zeal","zealot","emotion",
                "feeling","mood","grief","joy","sorrow","despair","hope","love","hate",
                "boring","desperately",
                "amazed","amazing","ambition","awesome","bad","bemoan","benign","blameworthy","brave","broken","careful","charity","compassion","confident","curious","delighted","deplore","determined","disappointed","discouraged","disgust","dramatic","ecstasy","embarrassed","excited","exciting","faithful","faithfully","fascinate","fearful","fortunate","frightened","fun","funny","garish","gracious","grateful","guilt","horror","hurt","impressed","indifferent","innocent","inspired","intense","intrigued","irritated","isolated","joyful","kind","lonely","lost","melancholy","miserable","motivated","mysterious","nasty","nervous","nostalgia","optimistic","overwhelmed","painful","passionate","peaceful","plight","proud","relieved","remarkable","resentful","restless","scared","sensitive","shame","shocked","shy","silent","silly","stressed","stubborn","surprised","sympathetic","tired","tranquil","troubled","trust","uncertain","unhappy","upset","valiant","victorious","vigorous","wonder","worried"]},
            {"id": "F-2", "label": "F-2｜感官/描述 Sensory", "keywords": [
                "black","brown","gray","green","purple","red","white","yellow","blue",
                "able","absolute","amenable","ancient","atypical","beautiful","big",
                "brilliant","cold","cute","dark","dear","dull","fast","flawless",
                "grand","handsome","hard","heavy","hot","icy","large","lovely","medium",
                "mushy","old","perfect","quiet","rough","slight","small","soft","steep",
                "stiff","tall","tolerable","volatile","warm","young","youthful","zealous",
                "zigzag","color","colour","smell","sound","taste","touch","sight",
                "visible","audible","fragrant","sour","sweet","bitter","salty",
                "alight","beauty","bright","comfortable","cutest","dirty","dusty","enormous","fancy","fluffy","glossy","garish","huge","hypoallergenic","loud","louder","messy","narrow","noisy","pale","plain","pretty","prettier","pure","sharp","silky","slim","smooth","spotless","strange","sturdy","thin","thick","tiny","tidy","transparent","ugly","unattractive","uncomfortable","unique","velvet","vibrant","washable","wide"]},
            {"id": "F-3", "label": "F-3｜溝通/社交 Social", "keywords": [
                "bye","goodbye","hello","hey","hi","how are you","how have you been",
                "sorry","thank you","complain","discuss","express","greet","interact",
                "introduce","negotiate","persuade","reciprocity","socially","call",
                "message","phone","video call","answer the phone","hang up","hold on",
                "pick up","along with somebody","along with something","communication",
                "conversation","dialogue","speech","presentation","debate",
                "accordingly","advice","agree","agreed","agreement","ally","apologise","apologised","assure","aware","bemoan","censure","charity","cite","commute","congratulate","counsel","disagree","enlighten","fellowship","formal","guarantee","habit","hospitality","humor","invitation","invite","journal","junior","let's","liberal","manner","memorial","mess","misunderstanding","moral","mutual","nasty","promise","quarrel","reason","reckon","reunion","rude","rumor","scandal","sigh","solidarity","surrender","sympathy","trust","unanimous","unanimously",
                "all right",
                "can it",
                "care for",
                "each other",
                "get on with",
                "get up",
                "go out",
                "hang out",
                "how about it",
                "hurry up",
                "if only",
                "like it",
                "like this",
                "like us",
                "no offense",
                "pig out",
                "so far",
                "the whole story",
                "waking up",
                "would have",
                "can't cannot",
                "doesn't does not",
                "isn't is not",
                "wasn't was not",
                "won't will not",
                "wouldn't would not",
                "you're you are",
                "i'll i will",
                "we'll we will",
                "come out",
                "comes out",
                "clean up",
                "carry out",
                "depend on",
                "get off",
                "go to sleep",
                "had every intention of",
                "had it all arranged to",
                "i had intended to",
                "i meant to",
                "i was all set to",
                "i was going to",
                "i was planning to",
                "i was were all set to",
                "i were going to",
                "look at",
                "look for",
                "take a bath",
                "take a break",
                "take a rest",
                "take a walk",
                "take care of",
                "take it easy",
                "best of",
                "be interested in",
                "as a rule",
                "for here",
                "pigs might fly",
                "top dog",
                "yellow belly",
                "like us",
                "the other",
                "'scuse me",
                "a d ",
                "a, an",
                "and yourself",
                "best regards",
                "buh-bye now",
                "bye for now",
                "can i help",
                "ciao ciaooo",
                "don't be a stranger",
                "doing well",
                "excuse me",
                "feisty as ever",
                "for me",
                "get away",
                "going on",
                "goes on",
                "good afternoon",
                "good day",
                "good evening",
                "good morning",
                "good to see you",
                "great seeing you",
                "have a good one",
                "have a good rest of your day",
                "have a good rest of your week",
                "have a great evening",
                "have a great weekend",
                "have a nice day",
                "have a productive week",
                "hey there",
                "hi there",
                "hit the road",
                "gonna hit the road",
                "how about you",
                "how are things",
                "how are you doing",
                "how's everything",
                "how's it going",
                "how's school",
                "how's work",
                "how's your day going",
                "how's your family",
                "how's your week going",
                "i better get going",
                "i gotta bounce",
                "i gotta fly",
                "i gotta head out",
                "i gotta run",
                "i gotta split",
                "i had a long day",
                "i hope this email finds you well",
                "i hope you had a wonderful weekend",
                "i hope you're having a great week",
                "i must be going",
                "i woke up on the wrong side of the bed",
                "i'll check",
                "i'm gonna take off",
                "i'm off",
                "i'm out",
                "i'm out of here",
                "is this seat taken",
                "it was a pleasure meeting you",
                "it was nice meeting you",
                "it's a pleasure to meet you",
                "it's a pleasure to see you",
                "it's an honor to meet you",
                "it's time to go to bed",
                "just got here",
                "keep in touch with",
                "keep someone in the loop",
                "may i help",
                "nice looking",
                "nice to meet you",
                "pardon me",
                "pardon my galoshes",
                "peace out",
                "pleased to meet you",
                "pretty good",
                "safe travels",
                "see ya",
                "see you",
                "see you around",
                "see you later",
                "see you next time",
                "see you on monday",
                "see you soon",
                "see you then",
                "take care",
                "there's no time",
                "until next time",
                "we might as well go home",
                "what about you",
                "what have you been up to",
                "what's happening",
                "what's up",
                "you alright",
                "happy holidays",
                "merry christmas",
                "frohliche weihnachten",
                "i hope this email finds you well",
                "a great number of",
                "all the best",
                "all the way",
                "and now",
                "at all times",
                "boil down to",
                "catch fire",
                "day in and day out",
                "draw the line",
                "drag someone down",
                "favor us",
                "for heaven's sake",
                "get dressed",
                "get home safe",
                "go cold turkey",
                "go shopping",
                "go to bed",
                "gonna hit the road",
                "in advance",
                "in back of",
                "in case",
                "in front of",
                "in light of",
                "in ruins",
                "laugh something off",
                "look around",
                "look forward to",
                "looking around",
                "looking forward to + v-ing",
                "make it",
                "on average",
                "pay in advance",
                "run over",
                "side by side",
                "take a look",
                "take a shower",
                "take out the trash",
                "that's ours",
                "things out",
                "tuck away",
                "warmth",
                "wasn't that wonderful",
                "work it out",
                "work out",
                "as presented"]},
            {"id": "F-4", "label": "F-4｜成語/習語 Idioms", "keywords": [
                "add up","back to square one","beat around the bush","bite the bullet",
                "burn bridges","call it a day","call the shots","catch you later",
                "check out","cut it out","cut to the chase","dodge the draft",
                "drop the ball","escape the rat race","find out","flake out","freak out",
                "get cold feet","hang in there","keep in touch","keep in the loop",
                "kill two birds with one stone","let us","make out","make progress",
                "make up","make use of","on the fence","on the same page","on the whole",
                "pull oneself together","push someone's buttons","screw up",
                "sell someone short","spill the beans","step up","suck at something",
                "take your time","throw under the bus","turn off","turn on","wake up",
                "without fail","phrasal verb","idiom","expression","slang",
                "altho","hence","hereby","thereafter","whereby","whilst"]},
            {"id": "F-5", "label": "F-5｜生理行為 Physiological", "keywords": [
                "alive","awake","breathe","hungry","sick","sleep","tired","well",
                "blink","cough","exhale","inhale","nod","shake","sneeze","sweat","yawn",
                "heartbeat","pulse","digest","absorb","reflex","instinct","physical",
                "biological","physiological",
                "belch","breathable","burp","copulate","defecate","doze","drool","excrete","fart","gulp","hiccup","hydrating","hydration","hyperventilate","ingest","masturbate","masturbation","menstruate","nibble","oversleep","perspire","poop","procreate","puke","secrete","sex","sexual","sexy","shiver","slumber","snore","swallow","throb","urine","wank"]},
            {"id": "F-6", "label": "F-6｜寫作/修辭 Writing & Rhetoric", "keywords": [
                "afterword","appendix","asterisk","chapter","citation","conclusion",
                "format","grammar","introduction","layout","preface","punctuation",
                "revision","analogy","hyperbole","irony","metaphor","simile",
                "abridged","adjective","vocabulary","abbreviation","writing","rhetoric",
                "gregarious","haphazard","indefatigable","inscrutable","lethargic",
                "magnanimous","meticulous","personality","pragmatic","shortsighted",
                "sneaky","sycophantic","tolerant","paragraph","sentence","clause",
                "phrase","word","text","document","article","report","essay",
                "archive","articled","author","authoring","blameworthy","brainy","characterize","cite","censor","compose","composition","editorial","encyclopedia","juxtaposition","novelist","platitude","poem","publisher","script","storytelling","synopsis","zeitgeist"]},
        ],
    },
    {
        "id": "G",
        "label": "Group G｜財經與商業",
        "color": "green",
        "children": [
            {"id": "G-1", "label": "G-1｜金融 Finance", "keywords": [
                "account","allocation","bank","banking","bill","bloomberg","budget",
                "capital","commission","compliance","cost","credit","dollar","economy",
                "expenditure","fund","invest","levy","liability","money","pay","price",
                "profit","proforma","purchase","remittance","retail","sale","stock",
                "tax","underwrite","wholesale","amorepacific","celltrion","chaebol",
                "fanuc","formosa petrochemical","hyundai","keyence","posco","samsung",
                "shinsegae","sk hynix","sojitz","finance","financial","currency",
                "exchange rate","interest","loan","mortgage","debt","asset","equity",
                "dividend","portfolio","investment","market","deposit","withdrawal",
                "credit","debit","between jobs","appointment","assess","access",
                "annual","assets","audit","bond","cents","commercial","deal","deficit","dollars","donate","equitable","estate","fee","fiscal","foundation","grant","gross","guarantee","import","income","inflation","insurance","invoice","lease","lend","lender","license","liquidity","loss","margin","pension","premium","receipt","refund","rent","revenue","royalty","tariff","thrift","thrifty","toll","transaction","treasury","tuition","turnover","wage","wealth",
                "bank vault",
                "dear money",
                "pay the bill",
                "power bank",
                "tuition fees",
                "bank of ryukyus",
                "bloomberg l p",
                "digital payment",
                "electricity bill",
                "financial district"]},
            {"id": "G-2", "label": "G-2｜商業管理 Business Management", "keywords": [
                "agenda","business class","client","commerce","company","consumer",
                "corporate","customer","innovation","logistics","management","market",
                "operation","organization","supply chain","vendor","contract","regulation",
                "rights","strategy","planning","kpi","objective","milestone","roadmap",
                "agile","scrum","stakeholder","risk","compliance","audit","process",
                "annual","benchmark","bureau","chain","charter","collaboration","competitive","conference","consortium","contingent","contractor","cooperation","corporation","deadline","department","deployment","director","division","efficiency","enterprise","establishment","facility","federation","governance","guideline","headquarters","hierarchy","implementation","incorporate","initiative","jurisdiction","leadership","lease","legal","liability","license","manufacturing","margin","merger","mission","outsource","partnership","pipeline","procedure","productivity","project","protocol","quota","reporting","restructure","revenue","sector","shareholder","standard","structure","subsidiary","supervision","supply","task","trademark","union","venture","wholesale","workforce",
                "brother industries",
                "canon inc",
                "daesang corporation",
                "daikin industries",
                "doosan group",
                "eneos holdings",
                "fast retailing co , ltd",
                "formosa petrochemical corporation",
                "hanwha group",
                "hd hyundai heavy industries",
                "hitachi, ltd",
                "hmm co , ltd",
                "honda motor co , ltd",
                "hyundai mobis",
                "hyundai motor group",
                "hyundai motor ulsan plant",
                "hyundai steel",
                "idemitsu kosan",
                "imabari shipbuilding",
                "itochu corporation",
                "kakao corp",
                "kb financial group",
                "keyence",
                "kia corporation",
                "kumho tire",
                "kyocera corporation",
                "lg group",
                "lotte group",
                "marubeni corporation",
                "mazda motor corporation",
                "megmilk snow brand",
                "mitsubishi corporation",
                "mitsui & co",
                "naver corporation",
                "nintendo co , ltd",
                "nissan motor co , ltd",
                "nissin foods",
                "nitori holdings",
                "omron corporation",
                "panasonic holdings",
                "posco",
                "rakuten group",
                "samsung biologics",
                "samsung electronics",
                "samsung group",
                "sharp corporation",
                "shinhan financial group",
                "sk group",
                "softbank group",
                "sony group",
                "subaru corporation",
                "sumitomo corporation",
                "suntory holdings",
                "suzuki motor corporation",
                "toyota motor corporation",
                "toyota tsusho",
                "yamaha corporation",
                "yaskawa electric",
                "cpc corporation, taiwan",
                "formosa petrochemical corporation",
                "taiwan power company (taipower)",
                "associated press (ap)",
                "bloomberg l p",
                "carnegie council for ethics in international affairs",
                "council on foreign relations (cfr)",
                "fox news",
                "new york academy of sciences",
                "the boston globe",
                "the christian science monitor",
                "the new york times (the times , nyt)",
                "the wall street journal (wsj)",
                "boston business journal",
                "boston herald",
                "new york daily news",
                "new york post"]},
            {"id": "G-3", "label": "G-3｜電商/零售 E-commerce & Retail", "keywords": [
                "ad","advertise","advertisement","advertising","advertize","brand","buy",
                "delivery","discount","e-commerce","online shopping","platform","product",
                "sell","shop","store","consumer","customer","demand","spending",
                "checkout","cart","wishlist","review","rating","shipment","logistics",
                "warehouse","inventory","fulfillment","return","refund","coupon",
                "promotion","flash sale","marketplace","vendor","merchant",
                "bargain","catalog","deal","groceries","manufacture","outlet","package","packet"]},
            {"id": "G-4", "label": "G-4｜廣告/傳媒 Media & PR", "keywords": [
                "broadcast","clickbait","journalism","media","meme","news","press release",
                "public relations","yellow journalism","campaign","influencer","marketing",
                "sponsor","audience","reach","engagement","impression","click","conversion",
                "seo","social media","content","viral","trending","newsletter","podcast",
                "webinar","blog","vlog","channel","subscriber","follower",
                "biopic","broadcaster","broadcasting","comic","editorial","magazine","newspaper","press","program","publication","publisher","radio","script","television","trailer",
                "associated press (ap)",
                "bloomberg l p",
                "digital media",
                "fox news",
                "local news",
                "prominent media outlets",
                "the boston globe",
                "the christian science monitor",
                "the new york times (the times , nyt)",
                "the wall street journal (wsj)",
                "television network",
                "streaming platform"]},
        ],
    },
    {
        "id": "H",
        "label": "Group H｜環境與永續",
        "color": "teal",
        "children": [
            {"id": "H-1", "label": "H-1｜環境科學 Environmental Science", "keywords": [
                "biodiversity","biosecurity","brownfield","bycatch","carbon footprint",
                "conservation","depletion","ecosystem","environment","food waste",
                "general waste","hazardous waste","kitchen waste","non-recyclable",
                "plastic bottle","recyclable","recycling","reduction","sustainability",
                "sustainable","endangered","habitat","nature reserve","wildlife",
                "pollution","deforestation","desertification","erosion","extinction",
                "greenhouse gas","ozone","acid rain","biodegradable","compost",
                "ecology","ecotourism","grassland","groundwater","hibernation","pesticide","reservoir","vegetation","wilderness"]},
            {"id": "H-2", "label": "H-2｜永續發展 Sustainability", "keywords": [
                "carbon neutral","clean energy","climate change","green","net zero",
                "renewable","solar","upcycle","waste reduction","wind power",
                "electric vehicle","green building","sustainable development",
                "circular economy","fair trade","organic","eco-friendly","zero waste",
                "carbon offset","reforestation","water conservation","energy efficiency",
                "ecotourism","recycle","biodegradable","conservation","emission","fossil"]},
        ],
    },
]

# ==========================================
# 高頻詞標籤庫（內建精簡版）
# ==========================================
_BUILTIN_DOLCH = {
    "a","an","and","are","as","at","be","been","but","by","can","come","do",
    "down","find","for","from","get","go","good","had","has","have","he","her",
    "here","him","his","how","i","if","in","into","is","it","jump","know","let",
    "like","little","look","make","me","more","my","not","now","of","on","one",
    "our","out","play","put","run","said","see","she","so","some","the","their",
    "them","then","there","they","this","to","two","up","was","we","went","were",
    "what","when","where","which","who","will","with","you","your","apple","baby",
    "bird","birthday","boat","book","boy","brother","cake","car","cat","day","dog",
    "door","egg","eye","farm","father","fish","flower","girl","hand","home","horse",
    "house","milk","money","morning","mother","name","night","paper","picture",
    "rain","school","sister","snow","song","sun","table","time","tree","water",
    "wind","window","wood","after","again","around","because","before","both",
    "call","clean","cold","does","don't","fast","first","five","found","gave",
    "goes","green","its","made","many","off","or","pull","read","right","sing",
    "sit","sleep","tell","these","those","upon","us","use","very","wash","why",
    "wish","work","would","write","better","bring","carry","cut","done","draw",
    "drink","eight","fall","far","full","got","grow","hold","hot","hurt","keep",
    "kind","laugh","light","long","much","myself","never","only","own","pick",
    "seven","shall","show","six","small","start","ten","today","together","try",
    "warm","about","always","around","best","buy","dont","fast","first","found",
    "green","its","made","off","pull","right","wash",
}

_BUILTIN_FRY = {
    "about","after","again","against","ago","air","all","also","always","among",
    "animal","answer","any","around","ask","away","back","because","before","being",
    "between","big","both","bring","by","call","came","can","carry","change",
    "children","city","clean","come","could","country","cut","day","did","different",
    "do","does","done","down","draw","drink","during","each","earth","eat","end",
    "even","every","example","fall","far","farm","fast","father","feel","feet",
    "few","find","first","fish","five","fly","follow","food","form","four","full",
    "get","girl","give","go","going","good","got","great","green","group","grow",
    "had","hand","hard","has","have","he","head","hear","heat","help","her","here",
    "high","him","his","home","hot","house","how","idea","if","important","in",
    "into","is","it","its","just","keep","kind","know","land","large","last","learn",
    "leave","left","let","light","like","list","little","live","long","look","made",
    "make","man","many","may","me","mean","men","mile","might","money","more","most",
    "mother","mountain","move","much","my","name","near","need","never","new","next",
    "night","no","north","not","nothing","now","number","of","off","often","old",
    "on","once","only","open","or","order","other","our","out","over","own","page",
    "paper","part","people","picture","place","plant","play","point","put","read",
    "real","right","river","road","rock","room","round","run","said","same","saw",
    "say","school","sea","second","see","seem","set","she","should","show","side",
    "since","small","so","some","song","soon","south","spell","stand","start",
    "state","still","stop","story","study","such","sun","sure","take","talk","tell",
    "that","the","their","them","then","there","these","they","think","this","those",
    "thought","three","through","time","to","today","together","too","took","top",
    "toward","tree","try","turn","two","under","until","up","us","use","very","walk",
    "want","warm","was","water","way","we","well","went","were","what","when",
    "where","which","white","who","why","will","wind","with","without","word","work",
    "world","would","write","year","you","young","your","beautiful","science",
    "mountain","government","country","already","probably",
}

_BUILTIN_NGSL = {
    "abandon","ability","able","absence","absolute","accept","access","accident",
    "accompany","account","accurate","achieve","acknowledge","acquire","act","active",
    "actual","adapt","add","address","admit","adopt","adult","advance","advantage",
    "adventure","affect","afford","after","age","agency","agree","aim","allow","alter",
    "amount","analyze","announce","answer","appeal","appear","apply","appoint",
    "appreciate","approach","approve","argue","arise","arrange","ask","assess",
    "assist","assume","attempt","attend","attitude","avoid","base","become","begin",
    "believe","build","buy","call","carry","cause","change","check","choose","claim",
    "clean","clear","close","come","compare","complete","concern","consider",
    "continue","control","create","decide","define","develop","discuss","distribute",
    "drive","eat","enable","encourage","ensure","establish","exist","expect",
    "explain","express","fail","feel","find","focus","force","form","get","give",
    "go","grow","happen","have","hear","help","hold","identify","improve","include",
    "increase","indicate","influence","inform","involve","keep","know","lead","learn",
    "let","live","look","lose","make","manage","mean","meet","move","need","obtain",
    "offer","open","order","organize","pay","perform","place","plan","play",
    "produce","provide","put","raise","reach","realize","receive","recognize",
    "remain","remove","report","require","result","return","run","save","say","see",
    "seek","seem","send","serve","show","speak","spend","start","state","study",
    "suggest","support","take","teach","tell","tend","think","try","turn",
    "understand","use","want","watch","work","write","access","affect","allow",
    "argue","assess","assume","avoid","base","benefit","carry","cause","claim",
    "consider","context","create","define","describe","determine","develop",
    "discuss","economic","environment","establish","evidence","experience","explain",
    "factor","follow","identify","implement","important","include","increase",
    "indicate","individual","involve","issue","lead","likely","major","manage",
    "method","model","note","occur","offer","operate","opportunity","particular",
    "policy","political","potential","process","provide","refer","relate","require",
    "resource","respond","role","significant","social","specific","structure",
    "system","theory","therefore","thus","traditional","type","value","various",
}

# ==========================================
# CEFR 分級詞庫
# ------------------------------------------
# 設計依據：
#   A1  Cambridge English Profile / Oxford 3000 A1 tier / Dolch Pre-K~K
#   A2  Oxford 3000 A2 tier / NGSL top 1000 / Fry 1-300
#   B1  Oxford 3000 B1 tier / NGSL 1001-2000 / Fry 301-600
#   B2  Oxford 3000 B2 tier / NGSL 2001-2809 / Fry 601-1000
#   C1  Oxford 5000 C1 tier / Academic Word List (AWL)
#   C2  低頻專業詞彙 / 修辭 / 方言 / 文化俚語
#
# 過渡標籤：A1-A2, B1-B2, B2-C1（詞彙橫跨兩個等級時使用）
# 子標籤：CEFR-Academic（學術英語EAP）、CEFR-Idiom（慣用語/片語動詞）
# ==========================================

CEFR_DB: dict[str, str] = {}   # word -> cefr_level，在模組載入時填充

# ── A1：啟蒙與語音基石 ───────────────────────────────────────────
# 生存詞彙：問候、數字、顏色、基本名詞、Be動詞、人稱代詞
_CEFR_A1 = {
    # 人稱與指示
    "i","me","my","mine","myself","you","your","yours","yourself",
    "he","him","his","himself","she","her","hers","herself",
    "it","its","itself","we","us","our","ours","ourselves",
    "they","them","their","theirs","themselves",
    "this","that","these","those",
    # Be 動詞 & 助動詞核心
    "am","is","are","was","were","be","been","being",
    "can","can't","cannot","do","don't","does","doesn't","did","didn't",
    "have","has","had","will","won't","would",
    # 基礎動詞（A1 動作）
    "go","come","get","give","make","take","put","see","know","think",
    "look","want","use","find","tell","ask","seem","feel","try","leave",
    "call","keep","let","begin","show","hear","play","run","move","live",
    "walk","eat","drink","sleep","sit","stand","open","close","read","write",
    "speak","listen","watch","buy","pay","work","help","need","like","love",
    # 基礎名詞（人 / 地 / 物）
    "man","woman","boy","girl","child","baby","family","friend","person","people",
    "house","home","room","door","window","table","chair","bed","book","bag",
    "car","bus","train","plane","road","street","city","town","country",
    "school","class","teacher","student","shop","food","water","money",
    "day","week","month","year","morning","afternoon","evening","night","time",
    "hand","head","eye","ear","nose","mouth","face","body","arm","leg","foot",
    # 形容詞（A1 描述）
    "big","small","little","large","long","short","tall","high","low","old","new",
    "good","bad","great","hot","cold","fast","slow","hard","easy","free",
    "right","wrong","happy","sad","hungry","tired","sick","well",
    "black","white","red","blue","green","yellow","orange","pink","brown","gray",
    # 數字
    "zero","one","two","three","four","five","six","seven","eight","nine","ten",
    "eleven","twelve","hundred","thousand","first","second","third","last",
    # 疑問詞 & 連接詞
    "what","where","when","who","why","how","which",
    "and","but","or","so","because","if","when","that","as",
    # 介系詞（空間/時間）
    "in","on","at","to","for","of","from","with","by","about",
    "up","down","out","off","over","under","after","before","between","around",
    # 限定詞
    "a","an","the","this","that","some","any","all","every","no","not",
    # 問候 & 生存表達
    "hello","hi","bye","goodbye","yes","no","please","thank","sorry","ok","okay",
    "here","there","now","then","today","tomorrow","yesterday",
}

# ── A2：初級溝通實務 ─────────────────────────────────────────────
_CEFR_A2 = {
    # 時態擴展詞彙
    "going","going to","used to","already","just","yet","still","soon","again",
    # 情態動詞擴展
    "must","should","could","might","may","shall","need","ought",
    # 詞綴常見詞根
    "action","actor","active","activity","addition","agreement","apartment",
    "arrival","attention","beautiful","beginning","believe","birthday",
    "breakfast","brother","building","business","careful","carry","change",
    "choose","cinema","clean","clothes","colour","comfortable","communication",
    "company","computer","cook","corner","correct","cost","country","culture",
    "dangerous","decide","different","difficult","direction","discover",
    "distance","doctor","dream","drive","during","early","easy","education",
    "enjoy","enough","evening","example","exercise","experience","explain",
    "famous","father","finish","foreign","forget","forward","garden","general",
    "government","half","holiday","hospital","hotel","important","information",
    "interest","job","journey","kind","kitchen","language","letter","light",
    "message","minute","miss","modern","mother","mountain","museum","music",
    "nature","newspaper","office","often","opinion","order","parents","park",
    "party","past","phone","photo","picture","plant","police","popular",
    "practice","prepare","price","problem","programme","project","promise",
    "question","quick","rain","reason","receive","remember","restaurant",
    "result","return","rule","safe","season","send","sentence","service",
    "side","sign","simple","situation","size","sometimes","special","start",
    "station","subject","suggest","summer","supermarket","sure","surprise",
    "swim","temperature","together","travel","turn","understand","university",
    "usually","visit","wait","weather","wedding","weekend","welcome","while",
    "winter","wonderful","worry","young",
    # 場景詞彙
    "address","age","airport","answer","area","bank","bar","beach","bedroom",
    "bicycle","bill","boat","bookshop","bread","bridge","café","cake","camera",
    "camp","capital","card","chance","cheese","church","cinema","class",
    "club","coffee","concert","cost","countryside","cup","dance","desert",
    "dictionary","district","engineer","entrance","envelope","evening",
    "festival","flat","flight","floor","flower","forest","gate","gift",
    "glasses","guest","gym","hall","hill","hospital","island","lake","lamp",
    "library","lift","lunch","magazine","map","market","meal","meeting",
    "menu","mirror","miss","motorcycle","neighbor","north","south","east","west",
    "packet","parking","passport","path","petrol","pharmacy","piano","picnic",
    "pilot","platform","police","pool","post","poster","price","queue","receipt",
    "reception","record","seat","service","shelf","shirt","shoes","signal",
    "station","steps","sugar","suit","taxi","tea","ticket","timetable","town",
    "traffic","umbrella","valley","village","wall","way","website","zoo",
}

# ── B1：中級獨立運用 ─────────────────────────────────────────────
_CEFR_B1 = {
    # 抽象概念與觀點表達
    "ability","advantage","agree","although","argue","attitude","background",
    "benefit","brave","cause","certainly","character","claim","clearly",
    "compare","complex","concern","connect","consider","context","contribute",
    "control","convince","courage","creative","curious","currently","damage",
    "deal","decision","depend","describe","despite","develop","differ",
    "difficulty","discuss","effect","effective","efficient","emotion","encourage",
    "environment","especially","evidence","exactly","expect","experience",
    "fail","fair","familiar","feature","focus","follow","freedom","gradually",
    "grow","happen","honest","however","imagine","immediately","improve",
    "include","increase","independent","influence","instead","intend","involve",
    "issue","judge","knowledge","manage","manner","meanwhile","mention",
    "method","mind","miss","natural","necessary","nervous","notice","occur",
    "offer","opinion","opportunity","organize","otherwise","particular",
    "patient","perform","permit","point","position","positive","prefer",
    "pressure","prevent","probably","process","provide","purpose","quality",
    "realize","recent","recognize","refer","refuse","relate","relationship",
    "remain","replace","require","responsibility","role","serious","solve",
    "society","specific","state","succeed","suggest","suitable","support",
    "suppose","technology","therefore","throughout","typical","unless","until",
    "usual","various","view","whether","wide","worth",
    # 敘事能力（故事說法）
    "adventure","ancient","brave","century","complete","dangerous","discover",
    "escape","explore","hero","historical","imagine","journey","mystery",
    "overcome","personal","plot","real","response","scene","spirit","stage",
    "storm","sudden","survive","tale","tradition","triumph","truth",
    # 情緒 & 抽象
    "afraid","alone","angry","anxious","boring","calm","cheerful","confident",
    "confused","disappointed","embarrassed","excited","frightened","glad",
    "grateful","guilty","hopeful","jealous","lonely","nervous","pleased",
    "proud","relaxed","relieved","shocked","stressed","surprised","upset",
    "worried",
    # B1 職業/社會詞彙
    "accommodation","accommodation","agriculture","announcement","application",
    "appointment","career","certificate","colleague","complaint","contract",
    "council","court","deadline","debate","department","donation","election",
    "employment","exhibition","facility","fund","graduate","industry",
    "institution","journalist","lawyer","leadership","location","occupation",
    "patient","pension","permission","politician","poverty","presentation",
    "professional","profit","promotion","property","qualification","reform",
    "registration","regulation","retirement","salary","solution","survey",
    "trade","transport","unemployment","volunteer","welfare",
}

# ── B2：中高級流利表達 ────────────────────────────────────────────
_CEFR_B2 = {
    # 慣用語 & 短語動詞（非字面意義）
    "add up","back to square one","beat around the bush","bite the bullet",
    "burn bridges","call it a day","call the shots","check out","cut it out",
    "cut to the chase","drop the ball","flake out","freak out","get cold feet",
    "hang in there","keep in touch","keep in the loop",
    "kill two birds with one stone","make progress","on the fence",
    "on the same page","pull oneself together","screw up","sell someone short",
    "spill the beans","step up","throw under the bus","without fail",
    # 批判思維 & 論證
    "acknowledge","advocate","allegation","assert","assumption","coherent",
    "compelling","complex","compromise","consequently","contradict","critique",
    "declaration","demonstrate","distinguish","elaborate","evaluate","explicit",
    "furthermore","hypothesis","implication","inconsistency","integrate",
    "interpretation","justify","legitimate","logical","moreover","nevertheless",
    "nonetheless","objective","paradox","perspective","precisely","prerequisite",
    "regardless","reinforce","relevant","rhetoric","scope","subsequently",
    "sustain","thereby","thus","undermine","validity","whereas","whereby",
    # 職場英語
    "agenda","allocate","audit","authorize","benchmark","brainstorm",
    "collaborate","commission","compliance","coordinate","delegate","deploy",
    "diagnostic","effectiveness","efficiency","execute","facilitate","feedback",
    "framework","implement","initiative","innovate","integrate","leverage",
    "milestone","negotiate","objective","optimize","outcome","pipeline",
    "prioritize","productivity","proposal","prototype","restructure","revenue",
    "stakeholder","strategic","streamline","tender","turnaround","vendor",
    # 高階語法詞彙
    "albeit","despite","notwithstanding","whereby","insofar","hitherto",
    "pertaining","therein","thereto","whereas","whereupon",
    # 學術寫作基礎
    "abstract","analyze","bibliography","citation","classify","conclude",
    "contrast","define","evidence","framework","hypothesis","identify",
    "methodology","outline","paradigm","phenomenon","principle","proposal",
    "rationale","significance","summarize","synthesize","thesis",
}

# ── C1：高級精通與精準 ───────────────────────────────────────────
_CEFR_C1 = {
    # Academic Word List (AWL) 核心詞彙
    "accommodate","accumulate","acknowledge","acquisition","administration",
    "alleviate","ambiguous","ambivalent","analogous","anomaly","anticipate",
    "articulate","assertion","assessment","attribute","augment","autonomous",
    "brevity","bureaucracy","catalyst","coherence","coincide","collaborate",
    "commodity","component","conceive","conceptual","concurrent","configuration",
    "consolidate","constitute","constraint","contextual","controversial",
    "conviction","corporate","correlation","counterpart","criteria","cumulative",
    "deduce","deploy","deviation","discourse","displace","disposition",
    "disseminate","distinction","domain","dominant","duration","element",
    "empirical","encompass","enhance","entity","equate","ethnicity","evolve",
    "exclusion","exploit","explicit","exposure","extensive","fluctuation",
    "formulate","forthcoming","fundamental","generate","hierarchy","highlight",
    "hypothesis","ideology","illustrate","implicit","incentive","incorporate",
    "indication","infrastructure","inherent","initiate","innovation","input",
    "instance","integral","integrity","interpretation","intervention","invoke",
    "latitude","legislation","liability","mandatory","mechanism","mediate",
    "minimize","modify","monitor","moreover","notion","objective","orientation",
    "overlap","parameter","perceive","persistent","perspective","phenomenon",
    "philosophy","portion","preceding","preliminary","prestigious","principal",
    "protocol","quote","random","reinforce","relevance","resolution","retain",
    "revenue","revision","scope","sector","sequence","significant","simulate",
    "specify","status","subordinate","supplement","sustain","task","terminate",
    "theoretical","thereby","thesis","transport","trend","underlying","undermine",
    "uniquely","utilise","utilize","validity","variable","verify","virtue","volume",
    # 語域意識（語體分辨）
    "colloquial","connotation","denotation","diction","euphemism","jargon",
    "metaphor","nuance","paraphrase","register","syntax","terminology","tone",
    # 近義詞精準選用
    "content","contented","satisfied","satiated","aloof","detached",
    "apprehensive","dread","eloquent","articulate","frugal","thrifty",
    "haughty","arrogant","inquisitive","curious","meticulous","thorough",
    "perturbed","disturbed","prolific","productive","tenacious","persistent",
    "veracious","truthful","zealous","enthusiastic",
    # 即興演說詞彙
    "address","advocate","articulate","assert","contend","convey","denounce",
    "discourse","dispute","elaborate","envisage","expound","illustrate",
    "imply","infer","postulate","propose","rebut","refute","stipulate",
}

# ── C2：專業母語等級 ─────────────────────────────────────────────
_CEFR_C2 = {
    # 修辭與美學
    "allegory","alliteration","allusion","anachronism","anaphora","antithesis",
    "aphorism","apostrophe","archetype","assonance","bathos","cacophony",
    "chiasmus","circumlocution","climax","conundrum","diatribe","didactic",
    "elegy","ellipsis","enigma","epigram","epithet","euphony","hyperbole",
    "imagery","innuendo","irony","juxtaposition","litotes","malapropism",
    "metonymy","motif","onomatopoeia","oxymoron","panegyric","paradox",
    "parody","pastiche","pathos","periphrasis","personification","polemic",
    "prologue","prosody","rhetoric","satire","simile","soliloquy","stanza",
    "sublimity","synecdoche","tautology","understatement","vernacular",
    # 方言 & 語言靈活性
    "argot","cant","creole","dialect","idiolect","lexicon","lingua franca",
    "patois","pidgin","slang","sociolect","vernacular",
    # 專業領域（醫療/法律/科技）
    "adjudication","affidavit","appellant","arbitration","codification",
    "defendant","deposition","equitable","fiduciary","indictment","injunction",
    "jurisprudence","liability","litigation","plaintiff","precedent","subpoena",
    "tort","tribunal","verdict","writ",
    "aetiology","anaesthesia","carcinoma","contraindication","epidemiology",
    "haematology","immunosuppression","laparoscopy","morbidity","palliative",
    "prognosis","prophylaxis","sepsis","thrombosis","toxicology",
    "algorithm","cryptography","heuristic","latency","microservices",
    "obfuscation","polymorphism","recursion","refactoring","scalability",
    # 俚語 & 文化梗（C2 隱含理解）
    "banter","cheeky","gobsmacked","gutted","knackered","miffed","posh",
    "reckon","skive","snarky","wanker","bloke","chuffed","dodgy","flabbergasted",
}

# ── 過渡標籤 ─────────────────────────────────────────────────────
_CEFR_A1_A2 = {
    # A1/A2 邊界詞：稍比 A1 複雜但仍基礎
    "agree","angry","afraid","alone","almost","always","another","anything",
    "arrive","beautiful","between","birthday","both","bring","business",
    "colour","correct","decide","different","dream","during","early",
    "enough","every","everything","follow","forget","friendly","front",
    "funny","happen","help","idea","important","information","invite",
    "kind","know","language","later","learn","leave","letter","maybe",
    "meaning","message","modern","next","often","only","order","our",
    "outside","park","pay","phone","photo","plan","practice","problem",
    "programme","promise","quickly","quite","really","remember","same",
    "send","simple","sometimes","station","strange","sure","things",
    "think","travel","understand","usually","visit","wait","wear","without",
}

_CEFR_B1_B2 = {
    # B1/B2 邊界：脫離基礎進入流利表達的關鍵詞
    "acknowledge","adequate","advocate","alternative","ambiguous","analyze",
    "apparent","approximately","aspect","assert","assess","assumption",
    "automatically","awareness","bias","capability","capacity","circumstance",
    "clarify","cognitive","coherent","compile","comprehensive","concept",
    "conclude","conflict","consequence","constraint","constructive","consume",
    "contradict","cope","criteria","decline","deduce","emphasize","encounter",
    "enforce","enormous","establish","explicit","expose","facilitate","function",
    "fundamental","generate","gradually","illustrate","implicit","impose",
    "inherent","initiate","input","integrate","justify","maintain","mechanism",
    "methodology","minimize","moderate","modify","monitor","moreover","mutual",
    "notion","objective","obtain","outcome","perceive","persist","phenomenon",
    "policy","preliminary","presume","primary","priority","proceed","promote",
    "propose","rational","relevance","rely","resolve","restrict","retain",
    "revolution","scope","shift","significant","straightforward","strategy",
    "structure","substantial","sufficient","summarize","theory","thereby",
    "traditional","transfer","trend","underlying","valid","whereas",
}

_CEFR_B2_C1 = {
    # B2/C1 邊界：學術與職場精準度關鍵詞
    "abstraction","accountability","accreditation","acquiescence","adjunct",
    "affiliation","aggregate","alleviate","ambivalence","ameliorate","anomaly",
    "apparatus","arbitrate","archaic","articulation","aspiration","attribute",
    "autonomy","auxiliary","cardinal","caveat","coherence","commensurate",
    "competency","concede","concurrent","conjecture","constituency","contention",
    "contingent","controversy","conviction","correlation","culminate","debilitate",
    "delineate","denote","derivative","desirable","deterministic","deviate",
    "diffusion","dilemma","discern","discrepancy","discretion","disposition",
    "diverge","domain","efficacy","embodiment","empirical","encompass","entity",
    "epistemology","equilibrium","equivocal","eradicate","exemplify","exponent",
    "extrapolate","fluctuate","formidable","forthright","governance","imperative",
    "infer","inherent","institutional","integrity","intrinsic","legislature",
    "lucid","manifestation","meticulous","nuance","obfuscate","paradigm",
    "plausible","pragmatic","precedent","prerequisite","proliferate","rationale",
    "reconcile","reinforce","reiterate","retrospective","scrutinize","subsidiary",
    "synthesis","tenuous","trajectory","transparent","ubiquitous","unequivocal",
    "unprecedented","validate","viable","volatile","watershed",
}

# ── 子標籤 ───────────────────────────────────────────────────────
_CEFR_ACADEMIC = {
    # Academic Word List (AWL) + EAP 核心
    "abstract","acknowledge","acquire","administration","affect","aggregate",
    "aid","albeit","allocate","amend","analogous","analyze","annual","apparent",
    "approximate","arbitrary","area","aspect","assemble","assess","assign",
    "assist","assume","attitude","attribute","authority","available","benefit",
    "bias","capable","category","cease","challenge","chapter","circumstance",
    "cite","civil","clarify","classic","coherent","coincide","colleague",
    "commence","communicate","community","compile","complex","concentrate",
    "conclude","conduct","confer","confirm","conflict","consent","considerable",
    "context","contract","contribute","controversial","convince","correspond",
    "criterion","crucial","culture","data","debate","decline","deduce","define",
    "demonstrate","denote","derive","design","differentiate","discuss","displace",
    "distribute","document","dominate","draft","emphasis","empirical","enable",
    "encounter","evaluate","exclude","explicit","expose","final","focus",
    "generate","global","guideline","hence","hierarchical","hypothesis","identify",
    "illustrate","impact","implement","implicit","incentive","indicate",
    "initial","innovate","insight","integrate","investigate","involve","isolate",
    "justify","layer","locate","logic","maintain","major","maximize","mechanism",
    "method","minimize","module","monitor","mutual","neutral","normalize",
    "notion","obtain","occur","outcome","overlap","parallel","parameter",
    "phenomenon","perspective","policy","preliminary","principle","proceed",
    "process","prohibit","publish","ratio","refine","relate","rely","remove",
    "require","research","resolve","respond","retain","section","select",
    "simulate","source","specify","structure","supplement","survey","sustain",
    "symbol","synthesize","task","target","technique","theory","trace",
    "transfer","transform","vary","verify","vision","volume",
}

_CEFR_IDIOM = {
    # 慣用語 & 片語動詞（B2-C1 範圍）
    "add up","back to square one","beat around the bush","bite the bullet",
    "bite the dust","blow hot and cold","break a leg","break the ice",
    "burn bridges","burn midnight oil","call it a day","call the shots",
    "catch someone off guard","check out","cost an arm and a leg",
    "cut corners","cut it out","cut to the chase","dodge the draft",
    "drop the ball","escape the rat race","face the music","find out",
    "flake out","freak out","get cold feet","get the ball rolling",
    "go back to the drawing board","hang in there","hit the nail on the head",
    "keep in touch","keep in the loop","kill two birds with one stone",
    "let sleeping dogs lie","let the cat out of the bag","make a long story short",
    "make out","make progress","make up","miss the boat","on the fence",
    "on the same page","on the whole","once in a blue moon","over the moon",
    "pass the buck","piece of cake","pull oneself together","pull someone's leg",
    "push someone's buttons","read between the lines","rock the boat",
    "screw up","sell someone short","sit on the fence","spill the beans",
    "steal the spotlight","step up","suck at something","take it with a grain of salt",
    "take your time","the ball is in your court","think outside the box",
    "throw in the towel","throw under the bus","tip of the iceberg",
    "turn a blind eye","turn off","turn on","under the weather","wake up",
    "without fail","word of mouth","wrap one's head around",
}


def build_cefr_db() -> dict:
    """
    建立 word → CEFR level 對照表。
    優先順序（高等級覆蓋低等級，以最精確分級為準）：
    C2 > C1 > B2-C1 > B2 > B1-B2 > B1 > A1-A2 > A2 > A1
    子標籤（Academic / Idiom）獨立附加，不影響主等級。
    """
    db: dict[str, str] = {}
    # 由低到高填入，高等級可覆蓋低等級
    for word in _CEFR_A1:
        db[word.lower()] = "A1"
    for word in _CEFR_A1_A2:
        db[word.lower()] = "A1-A2"
    for word in _CEFR_A2:
        db[word.lower()] = "A2"
    for word in _CEFR_B1:
        db[word.lower()] = "B1"
    for word in _CEFR_B1_B2:
        db[word.lower()] = "B1-B2"
    for word in _CEFR_B2:
        db[word.lower()] = "B2"
    for word in _CEFR_B2_C1:
        db[word.lower()] = "B2-C1"
    for word in _CEFR_C1:
        db[word.lower()] = "C1"
    for word in _CEFR_C2:
        db[word.lower()] = "C2"
    return db


def get_cefr_subtags(word: str) -> list:
    """回傳此詞的子標籤清單（Academic / Idiom），可能為空"""
    subtags = []
    w = word.lower()
    if w in _CEFR_ACADEMIC:
        subtags.append("CEFR-Academic")
    if w in _CEFR_IDIOM:
        subtags.append("CEFR-Idiom")
    return subtags


# 模組載入時建立 CEFR 資料庫
CEFR_DB = build_cefr_db()

# ==========================================
# CEFR 擴充詞庫 (行動3：人工標記 + Tier 2 推導覆蓋)
# 共 2,092 個詞彙，補充 build_cefr_db() 未收錄的詞根
# 注入順序在 CEFR_DB 之後，相同詞以此處為準（可覆蓋）
# ==========================================
_CEFR_EXTENSION = {
"able":"A1","above":"A1","across":"A1","act":"A1","add":"A1","ago":"A1",
"ahead":"A1","aim":"A1","air":"A1","alarm":"A1","alive":"A1","along":"A1",
"also":"A1","among":"A1","amount":"A1","animal":"A1","ankle":"A1",
"another":"A1","answer":"A1","apart":"A1","apple":"A1","april":"A1",
"arm":"A1","arrive":"A1","art":"A1","ask":"A1","august":"A1",
"aunt":"A1","away":"A1","bag":"A1","ball":"A1","band":"A1","bath":"A1",
"bear":"A1","beat":"A1","bed":"A1","bell":"A1","best":"A1","bird":"A1",
"bit":"A1","bite":"A1","block":"A1","blow":"A1","boat":"A1","book":"A1",
"born":"A1","bowl":"A1","box":"A1","boy":"A1","bread":"A1","bright":"A1",
"bring":"A1","broken":"A1","brush":"A1","bus":"A1","call":"A1","came":"A1",
"cap":"A1","care":"A1","case":"A1","catch":"A1","cell":"A1","chance":"A1",
"change":"A1","chicken":"A1","child":"A1","choose":"A1","chose":"A1",
"city":"A1","class":"A1","clean":"A1","close":"A1","clothes":"A1",
"cloud":"A1","coast":"A2","coat":"A1","code":"A1","cold":"A1","color":"A1",
"come":"A1","common":"A2","cook":"A1","cool":"A1","copy":"A2","corn":"A1",
"cover":"A2","cup":"A1","cut":"A1","dark":"A1","day":"A1","dead":"A2",
"deal":"A1","deep":"A1","dinner":"A1","dog":"A1","door":"A1","draw":"A1",
"dream":"A1","dress":"A1","drink":"A1","drive":"A1","drop":"A2","drum":"A1",
"duck":"A1","ear":"A1","early":"A1","earth":"A1","east":"A1","easy":"A1",
"egg":"A1","eight":"A1","else":"A1","end":"A1","engine":"A2","enter":"A2",
"eye":"A1","face":"A1","fact":"A2","fair":"A2","fall":"A1","fat":"A1",
"feel":"A1","feet":"A1","fell":"A1","fig":"A2","fill":"A2","find":"A1",
"fine":"A1","fire":"A1","fish":"A1","fit":"A2","five":"A1","flag":"A2",
"flat":"A2","floor":"A1","flow":"A2","fly":"A1","food":"A1","fork":"A1",
"found":"A1","four":"A1","free":"A1","fresh":"A2","front":"A2","full":"A1",
"fun":"A1","funny":"A1","game":"A1","garden":"A1","gas":"A1","gift":"A1",
"girl":"A1","give":"A1","glass":"A1","goal":"A1","gold":"A1","gone":"A1",
"good":"A1","got":"A1","grass":"A1","green":"A1","group":"A1","grow":"A1",
"gun":"A1","hair":"A1","half":"A1","hall":"A1","hand":"A1","happy":"A1",
"hard":"A1","hat":"A1","head":"A1","health":"A1","healthy":"A1",
"hear":"A1","heart":"A1","heat":"A2","heavy":"A1","held":"A1","help":"A1",
"here":"A1","high":"A1","hill":"A1","hit":"A1","hole":"A1","home":"A1",
"hope":"A2","hour":"A1","house":"A1","huge":"A1","hurt":"A1","ice":"A1",
"idea":"A2","iron":"A2","item":"A2","jaw":"A2","join":"A2","jump":"A1",
"keep":"A1","key":"A1","kid":"A1","kind":"A1","king":"A1","kiss":"A1",
"knee":"A1","know":"A1","land":"A1","last":"A1","laugh":"A1","lay":"A1",
"lead":"A2","leaf":"A2","learn":"A1","leg":"A1","level":"A1","life":"A1",
"light":"A1","line":"A1","lip":"A2","list":"A1","live":"A1","lock":"A2",
"long":"A1","look":"A1","lose":"A2","lost":"A2","lot":"A1","loud":"A2",
"low":"A1","lunch":"A1","main":"A2","make":"A1","mall":"A2","man":"A1",
"mark":"A1","match":"A2","mean":"A1","meet":"A1","mile":"A2","milk":"A1",
"mind":"A2","mine":"A2","miss":"A2","mix":"A2","money":"A1","month":"A1",
"moon":"A1","mouth":"A2","move":"A1","much":"A1","music":"A1","name":"A1",
"nap":"A2","nest":"A2","next":"A1","nice":"A1","night":"A1","nose":"A2",
"note":"A2","number":"A1","nurse":"A2","oil":"A1","open":"A1","order":"A1",
"pace":"B1","page":"A1","paint":"A2","pair":"A2","paper":"A1","part":"A1",
"path":"A2","pay":"A1","peace":"A2","pick":"A2","picture":"A1","piece":"A2",
"pig":"A1","place":"A1","plan":"A2","plant":"A1","play":"A1","please":"A1",
"point":"A1","police":"A1","pool":"A2","poor":"A1","power":"A2","pull":"A1",
"push":"A1","race":"A2","rain":"A1","read":"A1","rich":"A1","ring":"A1",
"rise":"A2","road":"A1","rock":"A1","role":"A2","roll":"A2","room":"A1",
"rope":"A2","round":"A2","row":"A1","safe":"A1","salt":"A1","sat":"A1",
"save":"A2","say":"A1","scale":"A2","seat":"A2","seem":"A1","sense":"A2",
"set":"A1","seven":"A1","shape":"A2","share":"A2","sheep":"A1","sign":"A2",
"simple":"A1","since":"A1","sing":"A1","sir":"A2","site":"A2","six":"A1",
"size":"A2","sky":"A1","sleep":"A1","slow":"A1","small":"A1","smell":"A2",
"snow":"A1","soccer":"A1","soft":"A1","soil":"A2","sort":"A2","south":"A1",
"speak":"A1","speed":"A2","spend":"A2","spoke":"A2","spot":"A2",
"spread":"A2","stand":"A1","star":"A1","stay":"A1","step":"A1","stick":"A1",
"stone":"A1","stop":"A1","story":"A1","street":"A1","strong":"A1",
"sun":"A1","sure":"A1","swim":"A1","tall":"A1","teen":"A2","ten":"A1",
"thank":"A1","thick":"A2","thin":"A2","think":"A1","three":"A1",
"throw":"A2","tied":"A2","tire":"A2","title":"A2","today":"A1","tone":"A2",
"tool":"A1","top":"A1","toy":"A1","tree":"A1","trip":"A2","try":"A1",
"tube":"A2","two":"A1","type":"A2","ugly":"A2","uncle":"A2","unit":"A2",
"upon":"A1","use":"A1","value":"A2","very":"A1","view":"A2","voice":"A2",
"wait":"A1","wake":"A2","walk":"A1","wall":"A1","warm":"A1","wash":"A1",
"watch":"A1","wave":"A2","way":"A1","wear":"A2","week":"A1","went":"A1",
"west":"A1","whole":"A1","wide":"A2","wild":"A1","win":"A1","wind":"A1",
"wire":"A2","wish":"A2","within":"A1","wood":"A1","word":"A1","world":"A1",
"yard":"A1","year":"A1","yoga":"A2","yolk":"A2","zone":"A2",
# A2
"abandon":"A2","abroad":"A2","absolute":"A2","abuse":"A2","accept":"A2",
"access":"A2","account":"A2","accurate":"A2","achieve":"A2","accuse":"A2",
"ache":"A2","acquire":"A2","adapt":"A2","adjective":"A2","adjust":"A2",
"admire":"A2","admission":"A2","admit":"A2","adopt":"A2","adult":"A2",
"advance":"A2","advertise":"A2","advertisement":"A2","advice":"A2",
"advise":"A2","affect":"A2","afford":"A2","afraid":"A2","africa":"A2",
"aid":"A2","album":"A2","alcohol":"A2","alcoholic":"A2","alley":"A2",
"allow":"A2","alter":"A2","anger":"A2","anniversary":"A2","announce":"A2",
"annoy":"A2","anybody":"A2","anymore":"A2","anyway":"A2","anywhere":"A2",
"apologize":"A2","appear":"A2","apply":"A2","aquarium":"A2","arrange":"A2",
"attend":"A2","attract":"A2","author":"A2","available":"A2","award":"A2",
"awareness":"A2","backyard":"A2","basement":"A2","battery":"A2",
"beauty":"A2","begin":"A2","believe":"A2","belong":"A2","blood":"A2",
"boot":"A2","bottle":"A1","bought":"A1","bounce":"A2","bow":"A2",
"branch":"A2","brave":"A2","budget":"B1","build":"A1","burn":"A2",
"business":"A2","calculate":"B1","calm":"A2","captain":"A2","celebrate":"A2",
"celebrity":"A2","century":"A2","chapter":"A2","character":"A2",
"chew":"A2","citizen":"B1","code":"A1","collect":"A2","comfortable":"A2",
"community":"A2","compare":"A2","compete":"B1","complain":"A2",
"complete":"A2","contact":"A2","contain":"A2","control":"A2","correct":"A2",
"couple":"A1","coworker":"A2","create":"A2","crime":"A2","culture":"A2",
"decide":"A2","depend":"A2","describe":"A2","desert":"A2","design":"A2",
"detail":"A2","device":"A2","die":"A2","difference":"A2","direct":"A2",
"discover":"A2","discuss":"A2","disease":"A2","display":"A2","divide":"A2",
"dust":"A2","earthquake":"A2","educate":"A2","embarrass":"A2","enemy":"A2",
"energy":"A2","engineer":"A2","enjoy":"A2","environment":"A2",
"especially":"A2","event":"A2","evil":"A2","except":"A2","expect":"A2",
"explain":"A2","fail":"A2","fear":"A2","fight":"A2","finally":"A2",
"force":"A2","form":"A2","future":"A2","general":"A2","government":"A2",
"grab":"A2","grade":"A2","growth":"A2","guide":"A2","happen":"A2",
"hate":"A2","history":"A2","hospital":"A2","human":"A2","hunger":"A2",
"hunt":"A2","imagine":"A2","improve":"A2","include":"A2","increase":"A2",
"interest":"A2","introduce":"A2","invite":"A2","island":"A2","journey":"A2",
"language":"A2","launch":"B1","law":"A2","learn":"A1","leave":"A1",
"limit":"A2","lion":"A1","listen":"A1","local":"A2","machine":"A2",
"market":"A2","matter":"A2","measure":"A2","member":"A2","message":"A2",
"mistake":"A2","mountain":"A2","nation":"A2","nature":"A2","negative":"A2",
"news":"A2","notice":"A2","object":"A2","offer":"A2","officer":"A2",
"pain":"A2","patient":"A2","perform":"B1","period":"A2","person":"A1",
"phone":"A1","photo":"A1","planet":"A2","popular":"A2","position":"B1",
"positive":"A2","possible":"A2","practice":"A2","prepare":"A2",
"produce":"A2","project":"A2","protect":"A2","quick":"A2","radio":"A2",
"reaction":"B1","record":"A2","relax":"A2","report":"A2","result":"A2",
"return":"A2","reward":"B1","rice":"A1","ride":"A1","river":"A1",
"season":"A2","serious":"A2","situation":"A2","skill":"A2","spirit":"A2",
"stage":"A2","state":"A2","station":"A2","success":"A2","support":"A2",
"surprise":"A2","technology":"A2","temperature":"A2","test":"A2",
"track":"A2","trouble":"A2","truth":"A2","universe":"A2","useful":"A2",
"usually":"A2","village":"A1","virus":"A2","volleyball":"A2","worry":"A2",
"youth":"A2",
# B1
"aikido":"B1","alien":"B1","altitude":"B1","ambition":"B1","ambassador":"B1",
"analyze":"B1","annual":"B1","appeal":"B1","appoint":"B1","appreciate":"B1",
"approach":"B1","approve":"B1","aquatics":"B1","archeology":"B1","arena":"B1",
"argue":"B1","argument":"B1","army":"A2","arrest":"B1","arrogant":"B1",
"article":"A2","artificial":"B1","artistic":"B1","aspect":"B1",
"assess":"B1","assist":"B1","assume":"B1","attempt":"B1","attitude":"B1",
"benefit":"B1","broadcast":"B1","capability":"B1","cargo":"B1","charity":"B1",
"claim":"B1","climate":"B1","complex":"B1","compose":"B1","concern":"B1",
"confident":"B1","confirm":"B1","crew":"B1","damage":"B1","debate":"B1",
"debt":"B1","decline":"B1","dedicate":"B1","defeat":"B1","define":"B1",
"delay":"B1","demonstrate":"B1","discipline":"B1","drama":"B1","drone":"B1",
"duty":"B1","ecology":"B1","economy":"B1","effect":"B1","election":"B1",
"element":"B1","emotion":"B1","employ":"B1","encourage":"B1",
"examine":"B1","exist":"B1","express":"B1","factor":"B1","faith":"B1",
"fascinate":"B1","formal":"B1","fund":"B1","global":"B1","grace":"B1",
"grant":"B1","gravity":"B1","guarantee":"B1","guilt":"B1","hire":"B1",
"identify":"B1","ignore":"B1","illegal":"B1","impact":"B1","income":"B1",
"industry":"B1","influence":"B1","injure":"B1","issue":"B1","judge":"B1",
"legal":"B1","lesbian":"B1","license":"B1","logic":"B1","maintain":"B1",
"manage":"B1","manner":"B1","mental":"B1","method":"B1","military":"B1",
"mission":"B1","modify":"B1","monitor":"B1","nasty":"B1","negotiate":"B2",
"novel":"B1","obtain":"B1","occur":"B1","operate":"B1","organization":"B1",
"overcome":"B1","perform":"B1","permit":"B1","physical":"B1","policy":"B1",
"prevent":"B1","prison":"B1","process":"B1","profession":"B1",
"progress":"B1","publish":"B1","purchase":"B1","quality":"B1",
"recognize":"B1","reduce":"B1","refer":"B1","region":"B1","relation":"B1",
"release":"B1","replace":"B1","request":"B1","research":"B1","respond":"B1",
"revolution":"B1","salary":"B1","section":"B1","series":"B1","settle":"B1",
"sexual":"B1","society":"B1","solution":"B1","staff":"B1","strategy":"B1",
"suffer":"B1","suggest":"B1","supply":"B1","system":"B1","tension":"B1",
"theory":"B1","trade":"B1","translate":"B1","transport":"B1","typical":"B1",
"union":"B1","urban":"B1","vaccine":"B1","vehicle":"B1","violence":"B1",
"visible":"B1","vocabulary":"B1","volunteer":"B1","vote":"B1","weapon":"B1",
"welfare":"B1","witness":"B1",
# B2
"aerodynamics":"C1","aesthetics":"C1","affair":"B1","appendix":"B2",
"archeology":"B2","negotiate":"B2","appendix":"B2",
# C1
"anarchy":"C1","archive":"C1","artery":"C1","asylum":"C1","censure":"C1",
"conquer":"C1","enlighten":"C1","enlightenment":"C1","exile":"C1",
"fascinate":"B1","gallbladder":"C1","guerrilla":"C1","hijack":"C1",
"hypoallergenic":"C1","instinct":"B1","intestines":"C1","intimacy":"C1",
"intimate":"C1","juxtaposition":"C1","longevity":"C1","lubrication":"C1",
"masturbate":"C1","masturbation":"C1","menstruate":"C1","microgravity":"C1",
"misconception":"C1","pioneer":"C1","platitude":"C2","procreate":"C1",
"prostate":"C1","realm":"C1","secrete":"C1","synopsis":"C1","throb":"C1",
"tonsil":"C1","treason":"C1","tuberculosis":"C1","urine":"C1","wank":"C1",
"zeitgeist":"C2","zoologist":"C1","zoology":"C1",
}
# Merge into CEFR_DB (extension overrides where conflicts exist)
CEFR_DB.update(_CEFR_EXTENSION)

# 行動4補充：39個數字變體的基礎詞 CEFR
_CEFR_ACTION4 = {
    "abnormality":"B1","action":"A2","air":"A1","alternative":"B1",
    "athlete":"B1","bag":"A1","baggage rack":"A2","book":"A1",
    "brake":"A2","brief":"B1","brood":"C1","cargo":"B1",
    "continually":"B1","corn":"A1","doll":"A1","favorite":"A2",
    "flown":"A2","gasoline":"B1","gift":"A1","home":"A1",
    "invariably":"C1","irascible":"C2","iron":"A2","material":"B1",
    "nap":"A2","office":"A2","party":"A1","path":"A2",
    "picture":"A1","please":"A1","prejudice":"C1","prospect":"B1",
    "safe":"A1","scale":"A2","sign":"A2","speed":"A2",
    "treasure":"B1","wax":"B1","without":"A2",
}
CEFR_DB.update(_CEFR_ACTION4)



CEFR_LEVEL_META = {
    "A1":     {"label": "A1 啟蒙與語音基石",   "color": "#16A34A", "bg": "#DCFCE7", "text": "#14532D"},
    "A1-A2":  {"label": "A1-A2 過渡",           "color": "#22C55E", "bg": "#F0FDF4", "text": "#166534"},
    "A2":     {"label": "A2 初級溝通實務",       "color": "#2563EB", "bg": "#DBEAFE", "text": "#1E3A8A"},
    "B1":     {"label": "B1 中級獨立運用",       "color": "#7C3AED", "bg": "#EDE9FE", "text": "#4C1D95"},
    "B1-B2":  {"label": "B1-B2 過渡",           "color": "#9333EA", "bg": "#F5F3FF", "text": "#581C87"},
    "B2":     {"label": "B2 中高級流利表達",     "color": "#DB2777", "bg": "#FCE7F3", "text": "#831843"},
    "B2-C1":  {"label": "B2-C1 過渡",           "color": "#E11D48", "bg": "#FFF1F2", "text": "#9F1239"},
    "C1":     {"label": "C1 高級精通與精準",     "color": "#D97706", "bg": "#FEF3C7", "text": "#78350F"},
    "C2":     {"label": "C2 專業母語等級",       "color": "#0891B2", "bg": "#ECFEFF", "text": "#164E63"},
    "CEFR-Academic": {"label": "學術英語 EAP",   "color": "#64748B", "bg": "#F1F5F9", "text": "#334155"},
    "CEFR-Idiom":    {"label": "慣用語/片語動詞", "color": "#78350F", "bg": "#FEF3C7", "text": "#78350F"},
}


def load_tag_db(config: dict) -> dict:
    """載入高頻詞標籤庫，外部檔案優先，fallback 至內建版"""
    tag_db = {}

    def add_tag(word: str, tag: str):
        w = word.strip().lower()
        if w:
            tag_db.setdefault(w, set()).add(tag)

    # Dolch
    dolch_path = config.get("dolch_txt_path")
    if dolch_path and os.path.exists(dolch_path):
        print(f"  📖 Dolch: 載入外部檔案 {dolch_path}")
        current = None
        for line in open(dolch_path, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            if re.match(r"^[A-Z\-]+[\s]*[A-Z]*【\d+】", line):
                current = line
            elif current:
                add_tag(line, "dolch")
    else:
        print("  📖 Dolch: 使用內建精簡版")
        for w in _BUILTIN_DOLCH:
            add_tag(w, "dolch")

    # Fry
    fry_paths = config.get("fry_txt_paths")
    if fry_paths and isinstance(fry_paths, list):
        print(f"  📖 Fry: 載入外部檔案 ({len(fry_paths)} 個)")
        for path in fry_paths:
            if os.path.exists(path):
                for word in open(path, encoding="utf-8").read().lower().split():
                    clean = re.sub(r"[^a-z']", "", word)
                    if clean:
                        add_tag(clean, "fry")
    else:
        print("  📖 Fry: 使用內建精簡版")
        for w in _BUILTIN_FRY:
            add_tag(w, "fry")

    # NGSL
    ngsl_path = config.get("ngsl_csv_path")
    if ngsl_path and os.path.exists(ngsl_path):
        print(f"  📖 NGSL: 載入外部檔案 {ngsl_path}")
        for line in open(ngsl_path, encoding="utf-8"):
            parts = [p.strip().lower() for p in line.strip().split(",") if p.strip()]
            for form in parts:
                add_tag(form, "ngsl")
    else:
        print("  📖 NGSL: 使用內建精簡版")
        for w in _BUILTIN_NGSL:
            add_tag(w, "ngsl")

    return tag_db


def get_tags(word: str, tag_db: dict) -> list:
    """回傳高頻詞標籤（dolch / fry / ngsl）"""
    tags = tag_db.get(word.lower(), set())
    return [t for t in ("dolch", "fry", "ngsl") if t in tags]


# ==========================================
# CEFR 三層推算引擎
# ==========================================

# 字尾 → 繼承詞根的 CEFR（詞根已知時適用）
_SUFFIX_STRIP = [
    # 動詞變形
    ("ing", ""),("ed", ""),("er", ""),("est", ""),("s", ""),
    ("tion","te"),("sion","de"),("ation","ate"),("ify",""),
    # 名詞化
    ("ment",""),("ness",""),("ity",""),("ance",""),("ence",""),
    ("ship",""),("hood",""),("dom",""),("ism",""),("ist",""),
    # 形容詞化
    ("able",""),("ible",""),("ful",""),("less",""),("ous",""),
    ("al",""),("ic",""),("ive",""),("ary",""),("ory",""),
    # 副詞化
    ("ly",""),
]

# 詞根前綴（移除前綴後查詞根）
_PREFIX_STRIP = [
    "un","re","pre","dis","mis","over","under","out","sub","super",
    "inter","trans","co","counter","anti","non","semi","mid",
]

# BERT 語意推算（全域快取，只初始化一次）
_SBERT_MODEL   = None
_CEFR_EMBEDDINGS: dict = {}   # level -> 平均向量
_CEFR_WORD_EMBEDDINGS: dict = {}  # word -> (embedding, level)


def _init_sbert():
    """懶加載 SBERT 模型，只在第一次推算時初始化"""
    global _SBERT_MODEL
    if _SBERT_MODEL is not None:
        return True
    try:
        from sentence_transformers import SentenceTransformer
        print("  ⏳ 載入 BERT 語意模型 (all-MiniLM-L6-v2)...")
        _SBERT_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
        print("  ✅ BERT 模型載入完成")
        return True
    except ImportError:
        print("  ⚠️  sentence-transformers 未安裝，Tier 3 BERT 推算停用")
        print("     安裝指令：pip install sentence-transformers")
        return False


def _build_cefr_embeddings():
    """為每個 CEFR 等級建立代表詞向量池（每等級取 50 詞平均）"""
    global _CEFR_WORD_EMBEDDINGS, _CEFR_EMBEDDINGS
    if not _SBERT_MODEL or _CEFR_EMBEDDINGS:
        return

    from sentence_transformers import util
    import torch

    level_words: dict = {}
    for word, lvl in CEFR_DB.items():
        level_words.setdefault(lvl, []).append(word)

    print("  ⏳ 建立 CEFR 等級語意向量池...")
    for lvl, words in level_words.items():
        sample = words[:80]
        embs = _SBERT_MODEL.encode(sample, convert_to_tensor=True, show_progress_bar=False)
        _CEFR_EMBEDDINGS[lvl] = embs.mean(dim=0)
        # 同時建立個別詞向量快取
        for w, e in zip(sample, embs):
            _CEFR_WORD_EMBEDDINGS[w] = (e, lvl)
    print(f"  ✅ CEFR 向量池完成（{len(_CEFR_EMBEDDINGS)} 個等級）")


def _tier1_direct(word: str):
    """Tier 1：直接查 CEFR_DB（精確命中）"""
    lvl = CEFR_DB.get(word)
    if lvl:
        return lvl, "confirmed"
    return None, None


def _tier2_morphology(word: str):
    """
    Tier 2：詞形還原 + 字尾/前綴規則推導。
    嘗試順序：
      1. 字尾剝除規則（含拼字變化）
      2. 二層字尾剝除（複合詞形）
      3. NLTK WordNet 詞形還原（若有安裝）
      4. 前綴剝除後再查
    """
    # 字尾規則：(suffix, replacement, min_stem_len)
    suffix_rules = [
        ("ying",  "y",   3), ("ying", "ie",  3),
        ("ied",   "y",   3), ("ied",  "ie",  3),
        ("ing",   "e",   3), ("ing",  "",    4),
        ("ed",    "e",   3), ("ed",   "",    4),
        ("ier",   "y",   3), ("iest", "y",   3),
        ("er",    "e",   3), ("er",   "",    4),
        ("est",   "e",   3), ("est",  "",    4),
        ("ations","ate", 3), ("ation","ate", 3),
        ("sions", "de",  3), ("sion", "de",  3),
        ("tions", "te",  3), ("tion", "te",  3),
        ("izations","ize",3), ("ization","ize",3),
        ("isations","ise",3), ("isation","ise",3),
        ("ments", "",    4), ("ment", "",    4),
        ("nesses","",    4), ("ness", "",    4),
        ("ities", "y",   3), ("ity",  "e",   3), ("ity", "", 4),
        ("ances", "",    4), ("ance", "",    4),
        ("ences", "",    4), ("ence", "",    4),
        ("ships", "",    4), ("ship", "",    4),
        ("hoods", "",    4), ("hood", "",    4),
        ("doms",  "",    4), ("dom",  "",    4),
        ("isms",  "",    4), ("ism",  "",    4),
        ("ists",  "",    4), ("ist",  "",    4),
        ("ries",  "ry",  3), ("ry",   "",    4),
        ("ies",   "y",   3),
        ("ables", "",    4), ("able", "",    4),
        ("ibles", "",    4), ("ible", "",    4),
        ("fuls",  "",    4), ("ful",  "",    4),
        ("less",  "",    4),
        ("ous",   "",    4),
        ("als",   "",    4), ("al",   "",    4),
        ("ics",   "",    3), ("ic",   "",    3),
        ("ives",  "e",   3), ("ive",  "e",   3), ("ive", "", 4),
        ("aries", "ary", 3), ("ary",  "",    4),
        ("ories", "ory", 3), ("ory",  "",    4),
        ("ily",   "y",   3), ("ly",   "",    4),
        ("ves",   "f",   3), ("ves",  "fe",  3),
        ("ses",   "s",   3), ("xes",  "x",   3), ("zes", "z", 3),
        ("ches",  "ch",  3), ("shes", "sh",  3),
        ("s",     "",    3),
    ]

    def try_stem(stem):
        if stem in CEFR_DB:
            return CEFR_DB[stem], stem
        # doubled consonant: running→run, stopped→stop
        if len(stem) >= 2 and stem[-1] == stem[-2]:
            s2 = stem[:-1]
            if s2 in CEFR_DB:
                return CEFR_DB[s2], s2
        return None, None

    # 一層剝除
    for suffix, repl, minlen in suffix_rules:
        if word.endswith(suffix) and len(word) - len(suffix) >= minlen:
            stem = word[:-len(suffix)] + repl
            lvl, matched = try_stem(stem)
            if lvl:
                return lvl, f"inferred-suffix({matched})"

    # 二層剝除（e.g. organizations → organize）
    for s1, r1, m1 in suffix_rules:
        if word.endswith(s1) and len(word) - len(s1) >= m1:
            mid = word[:-len(s1)] + r1
            for s2, r2, m2 in suffix_rules:
                if mid.endswith(s2) and len(mid) - len(s2) >= m2:
                    stem2 = mid[:-len(s2)] + r2
                    lvl, matched = try_stem(stem2)
                    if lvl:
                        return lvl, f"inferred-suffix2({matched})"

    # NLTK 補充
    try:
        from nltk.stem import WordNetLemmatizer
        import nltk
        try:
            nltk.data.find("corpora/wordnet")
        except LookupError:
            nltk.download("wordnet", quiet=True)
            nltk.download("omw-1.4", quiet=True)
        lem = WordNetLemmatizer()
        for pos in ("v", "n", "a", "r"):
            lemma = lem.lemmatize(word, pos=pos)
            if lemma != word and lemma in CEFR_DB:
                return CEFR_DB[lemma], f"inferred-lemma({lemma})"
    except Exception:
        pass

    # 前綴剝除
    for prefix in _PREFIX_STRIP:
        if word.startswith(prefix) and len(word) - len(prefix) >= 3:
            base = word[len(prefix):]
            if base in CEFR_DB:
                return CEFR_DB[base], f"inferred-prefix({prefix}+{base})"
            for suffix, repl, minlen in suffix_rules:
                if base.endswith(suffix) and len(base) - len(suffix) >= minlen:
                    stem = base[:-len(suffix)] + repl
                    lvl, matched = try_stem(stem)
                    if lvl:
                        return lvl, f"inferred-prefix-suffix({prefix}+{matched})"

    return None, None


def _tier3_bert(word: str):
    """
    Tier 3：BERT 語意最近鄰推算。
    比對對象：CEFR 等級代表向量（由各等級詞彙平均而成）。
    回傳最高信心的等級 + 信心分數。
    """
    if not _SBERT_MODEL or not _CEFR_EMBEDDINGS:
        return None, None

    try:
        from sentence_transformers import util
        import torch

        unk_emb = _SBERT_MODEL.encode(word, convert_to_tensor=True, show_progress_bar=False)

        best_lvl   = None
        best_score = 0.0

        # 與等級中心向量比對
        for lvl, lvl_emb in _CEFR_EMBEDDINGS.items():
            score = util.cos_sim(unk_emb, lvl_emb).item()
            if score > best_score:
                best_score = score
                best_lvl   = lvl

        # 同時與個別詞向量比對（找最近鄰詞）
        best_word_score = 0.0
        best_word       = None
        best_word_lvl   = None
        for w, (emb, lvl) in _CEFR_WORD_EMBEDDINGS.items():
            score = util.cos_sim(unk_emb, emb).item()
            if score > best_word_score:
                best_word_score = score
                best_word       = w
                best_word_lvl   = lvl

        # 若個別詞比對信心更高，優先採用
        if best_word_score > best_score and best_word_score >= 0.55:
            return best_word_lvl, f"inferred-bert-nn({best_word},{best_word_score:.2f})"

        if best_score >= 0.45:
            return best_lvl, f"inferred-bert-centroid({best_lvl},{best_score:.2f})"

        return None, None

    except Exception as e:
        return None, None


# 信心等級定義
_CONFIDENCE_RANK = {
    "confirmed":    3,   # Tier 1 精確命中
    "inferred":     2,   # Tier 2 形態推導
    "bert":         1,   # Tier 3 語意推算
    "unknown":      0,
}

def _confidence_tier(reason: str) -> str:
    """從 reason 字串判斷信心層級名稱"""
    if not reason:
        return "unknown"
    if reason == "confirmed":
        return "confirmed"
    if reason.startswith("inferred-lemma") or reason.startswith("inferred-suffix") or reason.startswith("inferred-prefix"):
        return "inferred"
    if reason.startswith("inferred-bert"):
        return "bert"
    return "unknown"


def get_cefr(word: str) -> dict:
    """
    三層混合 CEFR 推算引擎。
    Tier 1 → Tier 2 → Tier 3，逐層升級直到命中。

    回傳:
    {
      "level":      "B1" | None,
      "confidence": "confirmed" | "inferred" | "bert" | "unknown",
      "reason":     "inferred-suffix(organize)",
      "subtags":    ["CEFR-Academic"],
      "meta":       {...CEFR_LEVEL_META entry...}
    }
    """
    w = word.lower()
    subtags = get_cefr_subtags(w)

    # Tier 1
    lvl, reason = _tier1_direct(w)
    if lvl:
        return {"level": lvl, "confidence": "confirmed", "reason": reason,
                "subtags": subtags, "meta": CEFR_LEVEL_META.get(lvl, {})}

    # Tier 2
    lvl, reason = _tier2_morphology(w)
    if lvl:
        return {"level": lvl, "confidence": "inferred", "reason": reason,
                "subtags": subtags, "meta": CEFR_LEVEL_META.get(lvl, {})}

    # Tier 3
    lvl, reason = _tier3_bert(w)
    if lvl:
        return {"level": lvl, "confidence": "bert", "reason": reason,
                "subtags": subtags, "meta": CEFR_LEVEL_META.get(lvl, {})}

    return {"level": None, "confidence": "unknown", "reason": "",
            "subtags": subtags, "meta": {}}


def stem_word(filename: str, suffix: str) -> str:
    """去除後綴，取得核心詞彙"""
    name = filename.replace(suffix, "")
    return name.strip().replace("_", " ").lower()


def _build_keyword_index(tree: list) -> dict:
    """建立 keyword → (cat_id, cat_label, grp_id, grp_label, color) 的快速查詢表"""
    index = {}
    for group in tree:
        for cat in group.get("children", []):
            for kw in cat.get("keywords", []):
                index[kw.lower()] = (
                    cat["id"], cat["label"],
                    group["id"], group["label"],
                    group.get("color", "gray"),
                )
    return index

_KW_INDEX: dict = {}

def _ensure_index():
    global _KW_INDEX
    if not _KW_INDEX:
        _KW_INDEX = _build_keyword_index(KNOWLEDGE_TREE)

_CLS_SUFFIX_RULES = [
    ("ying","y",3),("ying","ie",3),("ied","y",3),("ied","ie",3),
    ("ing","e",3),("ing","",4),("ed","e",3),("ed","",4),
    ("izations","ize",3),("ization","ize",3),("isations","ise",3),("isation","ise",3),
    ("ations","ate",3),("ation","ate",3),("sions","de",3),("sion","de",3),
    ("tions","te",3),("tion","te",3),("ments","",4),("ment","",4),
    ("nesses","",4),("ness","",4),("ities","y",3),("ity","",4),
    ("ances","",4),("ance","",4),("ences","",4),("ence","",4),
    ("ships","",4),("ship","",4),("hoods","",4),("hood","",4),
    ("doms","",4),("dom","",4),("isms","",4),("ism","",4),
    ("ists","",4),("ist","",4),("ries","ry",3),("ry","",4),
    ("ies","y",3),("ables","",4),("able","",4),("ibles","",4),("ible","",4),
    ("fuls","",4),("ful","",4),("less","",4),("ous","",4),
    ("als","",4),("al","",4),("ics","",3),("ic","",3),
    ("ives","e",3),("ive","e",3),("ive","",4),
    ("aries","ary",3),("ary","",4),("ories","ory",3),("ory","",4),
    ("ily","y",3),("ly","",4),
    ("ves","f",3),("ves","fe",3),("ses","s",3),("xes","x",3),
    ("ches","ch",3),("shes","sh",3),("zes","z",3),("s","",3),
    ("ier","y",3),("iest","y",3),("er","e",3),("er","",4),
    ("est","e",3),("est","",4),
]
_CLS_PREFIXES = [
    "un","re","pre","dis","mis","over","under","out","sub","super",
    "inter","trans","co","counter","anti","non","semi","mid","de","ad",
]


def classify_word(word: str) -> tuple:
    """
    Tier 1：精確命中 keyword index
    Tier 2：詞形還原 + 字尾/前綴推導後再命中
    數字變體：strip _2/_3 後指向主詞條
    回傳: (cat_id, cat_label, grp_id, grp_label, color)
    """
    _ensure_index()
    w = word.strip().lower()

    # 數字變體：strip 尾部 " 2" " 3" 等
    w_base = re.sub(r"\s+\d+$", "", w).strip()

    for candidate in ([w, w_base] if w_base != w else [w]):
        # Tier 1 精確命中
        if candidate in _KW_INDEX:
            return _KW_INDEX[candidate]

        # Tier 2a — 字尾剝除
        def try_stem(stem):
            if stem in _KW_INDEX:
                return _KW_INDEX[stem]
            if len(stem) >= 2 and stem[-1] == stem[-2]:
                s2 = stem[:-1]
                if s2 in _KW_INDEX:
                    return _KW_INDEX[s2]
            return None

        for suffix, repl, minlen in _CLS_SUFFIX_RULES:
            if candidate.endswith(suffix) and len(candidate) - len(suffix) >= minlen:
                stem = candidate[:-len(suffix)] + repl
                hit = try_stem(stem)
                if hit:
                    return hit

        # Tier 2b — 二層字尾剝除
        for s1, r1, m1 in _CLS_SUFFIX_RULES:
            if candidate.endswith(s1) and len(candidate) - len(s1) >= m1:
                mid = candidate[:-len(s1)] + r1
                for s2, r2, m2 in _CLS_SUFFIX_RULES:
                    if mid.endswith(s2) and len(mid) - len(s2) >= m2:
                        stem2 = mid[:-len(s2)] + r2
                        hit = try_stem(stem2)
                        if hit:
                            return hit

        # Tier 2c — 前綴剝除
        for prefix in _CLS_PREFIXES:
            if candidate.startswith(prefix) and len(candidate) - len(prefix) >= 3:
                base = candidate[len(prefix):]
                if base in _KW_INDEX:
                    return _KW_INDEX[base]
                for suffix, repl, minlen in _CLS_SUFFIX_RULES:
                    if base.endswith(suffix) and len(base) - len(suffix) >= minlen:
                        stem = base[:-len(suffix)] + repl
                        hit = try_stem(stem)
                        if hit:
                            return hit

    return ("?", "未分類 Uncategorized", "?", "未分類 Uncategorized", "gray")


def scan_folder(folder: str, file_type: str, tag_db: dict,
                phrase_index: dict = None, all_stems_set: set = None) -> list:
    """掃描資料夾，回傳檔案資訊列表（含語義網絡）"""
    items = []
    if not os.path.isdir(folder):
        print(f"  ⚠️  找不到資料夾: {folder}")
        return items

    for fname in sorted(os.listdir(folder)):
        if not fname.lower().endswith(".html"):
            continue

        suffix = f".{file_type}.html"
        if fname.endswith(suffix):
            core = stem_word(fname, suffix)
        else:
            core = os.path.splitext(fname)[0].replace("_", " ").lower()

        cat_id, cat_label, grp_id, grp_label, color = classify_word(core)
        tags = get_tags(core, tag_db)
        cefr = get_cefr(core)

        # 語義網絡（僅單字，有語義引擎時）
        sem_links = {}
        if _SEMANTIC_ENABLED and phrase_index is not None and all_stems_set is not None:
            sem_links = build_semantic_links(core, phrase_index, all_stems_set)

        items.append({
            "filename":         fname,
            "core_word":        core,
            "file_type":        file_type,
            "path":             os.path.join(folder, fname),
            "category_id":      cat_id,
            "category_label":   cat_label,
            "group_id":         grp_id,
            "group_label":      grp_label,
            "color":            color,
            "tags":             tags,
            "cefr_level":       cefr["level"],
            "cefr_confidence":  cefr["confidence"],
            "cefr_reason":      cefr["reason"],
            "cefr_subtags":     cefr["subtags"],
            "cefr_meta":        cefr["meta"],
            "classified":       cat_id != "?",
            "semantic_links":   sem_links,
        })

    return items


def build_tree_index(items: list) -> list:
    """
    將 items 依 KNOWLEDGE_TREE 結構組織，供前端渲染。
    回傳結構：
    [
      {
        id, label, color,
        children: [
          {
            id, label,
            essentials: [...files],
            full: [...files]
          }
        ]
      }
    ]
    """
    lookup = {}
    for item in items:
        key = (item["group_id"], item["category_id"])
        lookup.setdefault(key, {"essentials": [], "full": []})
        lookup[key][item["file_type"]].append(item)

    tree = []
    for group in KNOWLEDGE_TREE:
        grp_node = {
            "id": group["id"],
            "label": group["label"],
            "color": group.get("color", "gray"),
            "children": [],
        }
        for cat in group.get("children", []):
            key = (group["id"], cat["id"])
            bucket = lookup.get(key, {"essentials": [], "full": []})
            grp_node["children"].append({
                "id": cat["id"],
                "label": cat["label"],
                "essentials": bucket["essentials"],
                "full": bucket["full"],
                "total": len(bucket["essentials"]) + len(bucket["full"]),
            })
        tree.append(grp_node)

    # 未分類群組
    unclassified = [i for i in items if not i["classified"]]
    if unclassified:
        unc_e = [i for i in unclassified if i["file_type"] == "essentials"]
        unc_f = [i for i in unclassified if i["file_type"] == "full"]
        tree.append({
            "id": "?",
            "label": "未分類 Uncategorized",
            "color": "gray",
            "children": [{
                "id": "?-0",
                "label": "需人工審查",
                "essentials": unc_e,
                "full": unc_f,
                "total": len(unc_e) + len(unc_f),
            }],
        })

    return tree


# ==========================================
# REVIEW_MODE：驗證模式開關
# ------------------------------------------
# True  → 低信心分類（Tier3/unknown）暫不寫入，僅輸出 review_pending.csv
# False → 全部寫入，低信心仍輸出 CSV 供參考
# ==========================================
REVIEW_MODE = False   # ← 首次執行建議設 True，人工確認後改 False


def write_review_csv(review_list: list, output_path: str):
    """
    輸出低信心分類審查清單 review_pending.csv。
    欄位：filename, core_word, file_type, suggested_folder,
          match_reason, tags, cefr_level, cefr_confidence,
          ✏️ 人工修正（留空=接受建議）
    """
    import csv
    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow([
            "filename", "core_word", "file_type",
            "suggested_folder", "match_reason",
            "tags (dolch|fry|ngsl)",
            "cefr_level", "cefr_confidence",
            "✏️ 人工修正（留空=接受建議）",
        ])
        for row in review_list:
            w.writerow(row)


def write_tag_index(items: list, output_path: str):
    """
    輸出高頻詞標籤索引 tag_index.csv。
    收錄所有帶有 Dolch / Fry / NGSL 標籤的詞彙。
    欄位：filename, core_word, file_type, category_id,
          category_label, cefr_level, tags
    """
    import csv
    tagged = [i for i in items if i.get("tags")]
    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow([
            "filename", "core_word", "file_type",
            "category_id", "category_label",
            "cefr_level", "tags (dolch|fry|ngsl)",
        ])
        for item in tagged:
            w.writerow([
                item["filename"],
                item["core_word"],
                item["file_type"],
                item.get("category_id", "?"),
                item.get("category_label", ""),
                item.get("cefr_level") or "",
                "|".join(item["tags"]),
            ])
    return len(tagged)


def main():
    parser = argparse.ArgumentParser(description="build_index.py — 建立學習檔案索引")
    parser.add_argument("--config",   default="config.json", help="設定檔路徑")
    parser.add_argument("--no-bert",  action="store_true",   help="停用 Tier 3 BERT 推算（加速）")
    args = parser.parse_args()

    config_path = args.config
    if not os.path.exists(config_path):
        print(f"❌ 找不到設定檔: {config_path}")
        return

    with open(config_path, encoding="utf-8") as f:
        config = json.load(f)

    essentials_path = config.get("essentials_path", "")
    full_path        = config.get("full_path", "")
    output_json      = config.get("output_json", "index.json")
    cefr_csv_name    = config.get("cefr_review_csv", "cefr_review.csv")

    print("=" * 60)
    print("  build_index.py — v4 知識樹索引建立工具")
    print("=" * 60)
    print(f"  essentials : {essentials_path}")
    print(f"  full       : {full_path}")
    print(f"  輸出       : {output_json}")
    print()

    # ── 高頻詞標籤庫 ──────────────────────────────────────────
    print("⏳ 載入高頻詞標籤庫...")
    tag_db = load_tag_db(config)
    dolch_n = sum(1 for v in tag_db.values() if "dolch" in v)
    fry_n   = sum(1 for v in tag_db.values() if "fry"   in v)
    ngsl_n  = sum(1 for v in tag_db.values() if "ngsl"  in v)
    print(f"  ✅ 完成 (Dolch:{dolch_n} | Fry:{fry_n} | NGSL:{ngsl_n})")
    print()

    # ── BERT 初始化 ────────────────────────────────────────────
    bert_ready = False
    if not args.no_bert:
        print("⏳ 初始化 CEFR 三層推算引擎...")
        bert_ready = _init_sbert()
        if bert_ready:
            _build_cefr_embeddings()
        print()

    # ── 語義網絡準備 ───────────────────────────────────────────
    print("⏳ 建立語義網絡索引...")
    _all_paths_e = []
    _all_paths_f = []
    if os.path.isdir(essentials_path):
        _all_paths_e = [os.path.splitext(f)[0].replace(".essentials","").replace("_"," ").lower()
                        for f in os.listdir(essentials_path) if f.endswith(".html")]
    if os.path.isdir(full_path):
        _all_paths_f = [os.path.splitext(f)[0].replace(".full","").replace("_"," ").lower()
                        for f in os.listdir(full_path) if f.endswith(".html")]
    _all_stems_for_sem = list(dict.fromkeys(_all_paths_e + _all_paths_f))
    _all_stems_set     = set(_all_stems_for_sem)
    _phrase_index      = _build_phrase_index(_all_stems_for_sem) if _SEMANTIC_ENABLED else {}
    sem_count          = sum(1 for w in _all_stems_for_sem if ' ' not in w)
    print(f"  ✅ 語義索引完成（{len(_phrase_index)} 個單字 → 片語對應，{sem_count} 個詞彙待展開）")
    print()

    # ── 掃描檔案 ───────────────────────────────────────────────
    print("⏳ 掃描檔案並推算 CEFR + 語義網絡...")
    items_e = scan_folder(essentials_path, "essentials", tag_db, _phrase_index, _all_stems_set)
    items_f = scan_folder(full_path,       "full",       tag_db, _phrase_index, _all_stems_set)
    all_items = items_e + items_f

    sem_linked = sum(1 for i in all_items if i.get("semantic_links"))

    # ── 統計 ───────────────────────────────────────────────────
    classified   = sum(1 for i in all_items if i["classified"])
    unclassified = sum(1 for i in all_items if not i["classified"])
    tagged       = sum(1 for i in all_items if i["tags"])
    cefr_tagged  = sum(1 for i in all_items if i["cefr_level"])

    # 信心層級統計
    conf_counts = {"confirmed": 0, "inferred": 0, "bert": 0, "unknown": 0}
    for i in all_items:
        c = i.get("cefr_confidence", "unknown")
        conf_counts[c] = conf_counts.get(c, 0) + 1

    # CEFR 等級統計
    cefr_counts: dict = {}
    for item in all_items:
        lvl = item["cefr_level"]
        if lvl:
            cefr_counts[lvl] = cefr_counts.get(lvl, 0) + 1
        for st in item.get("cefr_subtags", []):
            cefr_counts[st] = cefr_counts.get(st, 0) + 1

    print(f"  essentials : {len(items_e)} 個檔案")
    print(f"  full       : {len(items_f)} 個檔案")
    print(f"  已分類     : {classified}")
    print(f"  未分類     : {unclassified}")
    print(f"  有標籤     : {tagged} (Dolch/Fry/NGSL)")
    print(f"  有CEFR     : {cefr_tagged}")
    print(f"    ✅ 精確命中  (Tier 1) : {conf_counts['confirmed']}")
    print(f"    🔶 形態推導  (Tier 2) : {conf_counts['inferred']}")
    print(f"    🤖 語意推算  (Tier 3) : {conf_counts['bert']}")
    print(f"    ❓ 無法推算           : {conf_counts['unknown']}")
    print(f"  語義網絡   : {sem_linked} 個詞彙有展開連結")
    print()
    print("  CEFR 等級分布：")
    for lvl in ["A1","A1-A2","A2","B1","B1-B2","B2","B2-C1","C1","C2","CEFR-Academic","CEFR-Idiom"]:
        if lvl in cefr_counts:
            print(f"    {lvl:14s}: {cefr_counts[lvl]}")
    print()

    # ── 低信心 CEFR 推算 → cefr_review.csv ─────────────────────
    low_conf = [i for i in all_items
                if i.get("cefr_confidence") in ("bert", "unknown") and i["cefr_level"] is not None
                or i.get("cefr_confidence") == "unknown"]

    cefr_csv_path = os.path.join(os.path.dirname(config_path), cefr_csv_name)
    if low_conf:
        review_rows = [
            [
                item["filename"], item["core_word"], item["file_type"],
                item.get("category_id", "?"),
                item.get("match_reason", ""),
                "|".join(item.get("tags", [])),
                item.get("cefr_level") or "(未知)",
                item.get("cefr_confidence", "unknown"),
                "",
            ]
            for item in low_conf
        ]
        write_review_csv(review_rows, cefr_csv_path)
        print(f"  📋 低信心 CEFR 清單已輸出：{cefr_csv_path}")
        print(f"     共 {len(low_conf)} 筆（Tier 3 語意推算 + 無法推算），建議人工複查。")
        print()

    # ── 高頻詞標籤索引 → tag_index.csv ──────────────────────────
    tag_index_path = os.path.join(os.path.dirname(config_path), "tag_index.csv")
    n_tagged = write_tag_index(all_items, tag_index_path)
    if n_tagged:
        print(f"  🏷️  高頻詞標籤索引已輸出：{tag_index_path}")
        print(f"     共 {n_tagged} 個詞彙帶有 Dolch / Fry / NGSL 標籤。")
        print()

    # ── 建立樹狀索引 ───────────────────────────────────────────
    print("⏳ 建立知識樹索引...")
    tree = build_tree_index(all_items)

    # ── 輸出 index.json ────────────────────────────────────────
    output = {
        "meta": {
            "essentials_path":  essentials_path,
            "full_path":        full_path,
            "total_essentials": len(items_e),
            "total_full":       len(items_f),
            "total":            len(all_items),
            "classified":       classified,
            "unclassified":     unclassified,
            "tagged":           tagged,
            "cefr_tagged":      cefr_tagged,
            "cefr_counts":      cefr_counts,
            "cefr_confidence":  conf_counts,
        },
        "cefr_level_meta": CEFR_LEVEL_META,
        "tree":      tree,
        "all_items": all_items,
    }

    output_path = os.path.join(os.path.dirname(config_path), output_json)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"  ✅ 輸出完成: {output_path}")
    print()
    print("=" * 60)
    print("  下一步：執行 python serve.py 啟動本地伺服器")
    if low_conf:
        print(f"  📋 請複查：{cefr_csv_path}")
    print("=" * 60)

if __name__ == "__main__":
    main()
