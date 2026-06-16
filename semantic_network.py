"""
semantic_network.py
===================
語義網絡展開引擎。

三層展開：
  ① 片語動詞 / 相關片語  (phrasal_verbs)   → 從清單中自動抽取
  ② 搭配詞 Collocation   (collocations)    → 靜態手建 + 清單抽取
  ③ 詞形家族 Word Family  (word_family)     → 規則推導 + 靜態手建

輸出格式（寫入 index.json 每個 item 的 semantic_links 欄位）：
{
  "phrasal_verbs": [
    {"word": "work out",    "in_list": true,  "file_type": "essentials"},
    {"word": "work things out", "in_list": true,  "file_type": "essentials"},
    {"word": "work on",     "in_list": false, "file_type": null}
  ],
  "collocations":  [...],
  "word_family":   [...]
}
"""

import re
from collections import defaultdict

# ==========================================
# 靜態搭配詞庫 (Collocation DB)
# 格式：base_word → [collocation_phrase, ...]
# ==========================================
COLLOCATION_DB: dict[str, list[str]] = {
    # ── 動詞搭配 ──────────────────────────────────────────
    "make": ["make a decision","make a mistake","make a plan","make an effort",
             "make an excuse","make an offer","make a difference","make a meal",
             "make a move","make a point","make friends","make money",
             "make progress","make sense","make time","make use of",
             "make up","make out","make it"],
    "take": ["take a bath","take a break","take a look","take a shower",
             "take a walk","take a rest","take action","take care of",
             "take it easy","take notes","take off","take out","take part",
             "take place","take turns","take your time","take over",
             "take a trip","take a picture","take out the trash"],
    "get": ["get along","get away","get back","get cold feet","get dressed",
            "get home safe","get in touch","get on","get off","get out",
            "get ready","get up","get together","get used to",
            "get over","get rid of","get to know"],
    "do": ["do exercise","do homework","do laundry","do research",
           "do the cleaning","do the dishes","do your best","do without"],
    "have": ["have a meeting","have breakfast","have fun","have lunch",
             "have dinner","have a look","have a break","have a conversation",
             "have a good time","have no choice","have trouble"],
    "go": ["go abroad","go camping","go cold turkey","go out","go shopping",
           "go to bed","go to sleep","go for a walk","go on a trip",
           "go back","go ahead","go through"],
    "give": ["give advice","give a speech","give up","give back",
             "give a hand","give way","give birth"],
    "come": ["come across","come back","come from","come in","come on",
             "come out","come up with","come true"],
    "look": ["look after","look at","look for","look forward to",
             "look around","look out","look up","look like","look into"],
    "put": ["put away","put back","put down","put off","put on",
            "put out","put together","put up with"],
    "turn": ["turn down","turn into","turn off","turn on","turn out",
             "turn over","turn up"],
    "break": ["break down","break free","break in","break out",
              "break the ice","break up","break a leg","break the rules",
              "take a break"],
    "bring": ["bring about","bring back","bring together","bring up"],
    "run": ["run away","run into","run out of","run over","run on electricity",
            "run for office"],
    "set": ["set free","set off","set out","set up","set aside","set a goal"],
    "keep": ["keep in mind","keep in touch","keep in the loop","keep up",
             "keep going","keep trying"],
    "hold": ["hold on","hold back","hold up","hold a meeting","hold your breath"],
    "call": ["call back","call it a day","call off","call on","call the shots"],
    "work": ["work out","work on","work through","work together","work things out",
             "hard work","work experience","work from home","work it out"],
    "play": ["play a role","play fair","play safe","play sports"],
    "stand": ["stand for","stand out","stand up"],
    "move": ["move forward","move on","move out","move in"],
    "find": ["find out","find a way","find fault"],
    "show": ["show off","show up","show interest"],
    "think": ["think about","think over","think outside the box","think ahead"],
    "speak": ["speak up","speak out","speak fluently"],
    "write": ["write down","write up","write about"],
    "read": ["read between the lines","read aloud","read carefully"],
    "help": ["help out","help with","help each other"],
    "start": ["start over","start fresh","start with","start a business"],
    "stop": ["stop by","stop doing","stop and think"],
    "open": ["open up","open a door","open minded"],
    "close": ["close down","close off","close a deal"],
    "build": ["build up","build on","build a team","build confidence"],
    "cut": ["cut back","cut down","cut off","cut it out","cut to the chase",
            "cut corners"],
    "draw": ["draw attention","draw a line","draw the line","draw a conclusion"],
    "carry": ["carry on","carry out","carry over"],
    "pass": ["pass on","pass out","pass away","pass the time"],
    "fall": ["fall apart","fall back","fall in love","fall out","fall behind"],
    "pull": ["pull back","pull off","pull out","pull together",
             "pull oneself together","pull someone's leg"],
    "push": ["push back","push forward","push someone's buttons"],
    "pick": ["pick up","pick out","pick on"],
    "check": ["check in","check out","check on","check up"],
    "fill": ["fill in","fill out","fill up"],
    "use": ["use up","make use of","use to"],
    "try": ["try on","try out","try hard"],
    "wait": ["wait for","wait on","wait out"],
    "ask": ["ask for","ask out","ask around"],
    "catch": ["catch up","catch on","catch someone off guard"],
    "hold": ["hold on","hold back","hold up"],
    "hang": ["hang in there","hang out","hang up"],
    "lay": ["lay down","lay off","lay out"],
    "lead": ["lead to","lead by example","lead the way"],
    "leave": ["leave behind","leave out","leave alone"],
    "lose": ["lose track of","lose your mind","lose ground"],
    "reach": ["reach out","reach a goal","reach an agreement"],
    "spend": ["spend time","spend money","spend on"],
    "hit": ["hit the nail on the head","hit the road","hit a target"],
    "throw": ["throw away","throw under the bus","throw in the towel"],
    "buy": ["buy time","buy in","buy out"],
    "sell": ["sell out","sell someone short"],
    "pay": ["pay attention","pay back","pay off","pay in advance"],
    "send": ["send out","send back","send for"],
    "bring": ["bring about","bring up","bring back","bring together"],
    "blow": ["blow up","blow away","blow off steam"],
    "burn": ["burn out","burn bridges","burn midnight oil"],
    "drop": ["drop off","drop out","drop the ball"],
    "eat": ["eat out","eat in","eat up"],
    "drink": ["drink up","drink in"],
    "sleep": ["sleep in","sleep on it","sleep through"],
    "walk": ["walk away","walk in","walk out"],
    "ride": ["ride out","ride along"],
    "drive": ["drive away","drive home","drive someone crazy"],
    "fly": ["fly out","fly high","fly off the handle"],
    "swim": ["swim through"],
    "climb": ["climb up","climb out"],
    "jump": ["jump in","jump out","jump to conclusions","jump at the chance"],
    # ── 名詞搭配 ──────────────────────────────────────────
    "time": ["full time","part time","spare time","free time","hard time",
             "good time","bad time","on time","in time","at the same time",
             "take your time","spend time","waste time","save time"],
    "hand": ["by hand","on hand","give a hand","shake hands","wash your hands",
             "lend a hand","in hand","out of hand","hand in hand","first hand"],
    "mind": ["change your mind","keep in mind","never mind","make up your mind",
             "peace of mind","open mind"],
    "eye": ["keep an eye on","turn a blind eye","eye contact","see eye to eye"],
    "heart": ["from the heart","change of heart","take heart","lose heart",
              "at heart","broken heart"],
    "back": ["back to square one","back to basics","fall back","look back",
             "step back","hold back"],
    "head": ["head of","head start","keep your head","use your head",
             "head to head","off the top of your head"],
    "face": ["face to face","face the music","lose face","face up to"],
    "word": ["in other words","have a word","keep your word","word for word",
             "spread the word","by word of mouth"],
    "way": ["by the way","on the way","give way","way out","make way",
            "find a way","out of the way","in a way"],
    "place": ["take place","in place","out of place","first place"],
    "day": ["day by day","day in and day out","these days","one day",
            "every day","all day","day off","day trip","call it a day"],
    "life": ["way of life","full of life","life expectancy","quality of life"],
    "work": ["hard work","teamwork","work experience","work of art",
             "out of work","in the works","framework"],
    "school": ["school year","school trip","after school","boarding school",
               "cram school","high school","medical school"],
    "water": ["water down","still water","running water","drinking water",
              "mineral water","hot water","in deep water"],
    "food": ["food for thought","junk food","street food","fast food",
             "food court","food waste","health food"],
    "air": ["fresh air","open air","on air","air out","thin air","mid-air",
            "air quality","hot air","air pressure"],
    "bed": ["go to bed","in bed","bed and breakfast","bed frame","get out of bed",
            "make the bed","flower bed"],
    "light": ["in light of","light up","come to light","green light",
              "traffic light","in a new light"],
    "top": ["on top of","top of the morning","over the top","top secret",
            "from top to bottom","top priority"],
    "end": ["in the end","at the end","come to an end","dead end","end result",
            "end up","make ends meet","loose ends"],
    "line": ["draw the line","in line","on the line","out of line",
             "bottom line","front line","punch line"],
    "point": ["to the point","make a point","at this point","breaking point",
              "point of view","beside the point","starting point"],
    "power": ["in power","power off","power on","power plant","power grid",
              "manpower","willpower","firepower","electric power"],
    "level": ["on a level","high level","low level","level up","level out"],
    "side": ["side by side","on the other side","bright side","downside",
             "upside","inside out","outside in"],
    "room": ["room for","make room","dining room","living room","bedroom",
             "classroom","bathroom","reading room","study room"],
    "case": ["in any case","in case","just in case","lower case","upper case"],
    "business": ["mind your own business","funny business","business class",
                 "go out of business","mean business"],
    "door": ["open a door","door to door","next door","out of doors"],
    "road": ["on the road","road trip","hit the road","end of the road"],
    "ground": ["on the ground","from the ground up","lose ground","stand your ground"],
    "step": ["step by step","step up","step back","step in","out of step"],
    "stand": ["take a stand","stand for","last stand","one-night stand"],
    "turn": ["in turn","take turns","turn of events","out of turn"],
    "run": ["in the long run","home run","trial run","on the run"],
    "play": ["fair play","child's play","play on words","power play"],
    "course": ["of course","in due course","stay the course","main course"],
    "age": ["age group","coming of age","ice age","middle age","new age"],
    "change": ["climate change","exchange","change of heart","spare change"],
    "deal": ["a big deal","deal with","done deal","real deal"],
    "matter": ["as a matter of fact","mind over matter","no matter what",
               "what's the matter"],
    "piece": ["piece of cake","piece of mind","all in one piece","give a piece of your mind"],
    "sense": ["make sense","sense of humor","in a sense","sixth sense","common sense"],
    "interest": ["in the interest of","take interest in","area of interest"],
    "pressure": ["under pressure","peer pressure","put pressure on","high pressure"],
    "energy": ["clean energy","renewable energy","save energy","full of energy"],
    "health": ["in good health","public health","mental health","health care"],
    "sport": ["good sport","water sport","air sports","winter sport","extreme sport"],
    "money": ["save money","spend money","make money","money back","value for money"],
    "family": ["family member","nuclear family","extended family","start a family"],
    "team": ["team up","team player","dream team","home team","visiting team"],
    "answer": ["in answer to","know the answer","find the answer"],
    "question": ["out of the question","beg the question","raise a question"],
    "problem": ["solve a problem","face a problem","no problem"],
    "plan": ["make a plan","plan ahead","go according to plan","backup plan"],
    "idea": ["good idea","have an idea","no idea","idea of"],
    "number": ["a number of","phone number","number one","by the numbers"],
    "place": ["in place","first place","take someone's place","out of place"],
    "space": ["outer space","personal space","save space","breathing space"],
    "music": ["live music","background music","music video","make music"],
    "art": ["work of art","state of the art","art form","fine art"],
    "language": ["body language","sign language","first language","foreign language"],
    "city": ["city center","city hall","capital city","garden city"],
    "country": ["country side","home country","across the country","developing country"],
    "world": ["world record","world class","around the world","in the world"],
    "nature": ["by nature","human nature","second nature","mother nature"],
    "future": ["in the future","near future","future perfect","back to the future"],
    "past": ["in the past","get over the past","past tense","things of the past"],
    "hot": ["hot spring","hot dog","hot topic","get into hot water"],
    "cold": ["cold front","cold turkey","cold water","stone cold"],
    "long": ["before long","as long as","long run","long shot","along"],
    "short": ["in short","fall short","short cut","short notice","for short"],
    "free": ["free time","for free","set free","feel free","free of charge"],
    "open": ["wide open","open up","open minded","in the open"],
    "high": ["high school","high time","run high","high pressure","high speed"],
    "low": ["low key","low profile","hit an all-time low","run low"],
    "fast": ["hold fast","fast food","fast track","stand fast"],
    "slow": ["slow down","slow motion","go slow","slow burn"],
    "hard": ["hard work","work hard","hard time","die hard","hard copy"],
    "easy": ["take it easy","go easy on","easy going","over easy"],
    "big": ["big deal","big picture","think big","big time"],
    "small": ["small talk","small print","small business","start small"],
    "good": ["for good","good for nothing","make good","as good as"],
    "right": ["all right","right away","in the right","right now"],
    "wrong": ["go wrong","right or wrong","in the wrong"],
    "old": ["old fashioned","old school","grow old","old hand"],
    "new": ["brand new","new to","ring in the new","turn over a new leaf"],
    "full": ["full time","in full","full of","to the full"],
    "half": ["half time","half hearted","in half","half way"],
    "whole": ["as a whole","on the whole","whole heartedly"],
    "own": ["on your own","all your own","come into your own","hold your own"],
    "like": ["feel like","look like","sound like","just like","would like"],
    "love": ["fall in love","love at first sight","in love with"],
    "fear": ["for fear of","in fear","face your fears"],
    "hope": ["hope for the best","pin your hopes on","beyond hope"],
    "power": ["in power","power of attorney","man power","will power"],
    "key": ["key point","key role","off key","under lock and key"],
    "book": ["book in","by the book","cook the books","open book"],
    "paper": ["on paper","paper over","white paper","newspaper"],
    "game": ["game plan","fair game","give the game away","name of the game"],
    "fire": ["fire away","fire back","catch fire","set fire to","open fire"],
    "water": ["in hot water","water down","hold water","test the water"],
    "ice": ["break the ice","on thin ice","put on ice","keep on ice"],
    "stone": ["leave no stone unturned","set in stone","stone cold"],
    "ball": ["get the ball rolling","on the ball","have a ball","in someone's court"],
    "door": ["close the door on","keep the door open","door to door"],
    "table": ["on the table","turn the tables","bring to the table","under the table"],
    "chair": ["take the chair","step down from the chair"],
    "bed": ["bed and breakfast","flower bed","river bed","make your bed"],
    "window": ["window of opportunity","window shopping","window seat"],
    "street": ["on the street","street smart","main street","wall street"],
    "bridge": ["bridge the gap","burn your bridges","bridge over"],
    "wall": ["off the wall","hit the wall","up against the wall","drive up the wall"],
    "line": ["bottom line","draw the line","front line","on the line"],
    "box": ["out of the box","black box","think outside the box","open box"],
    "bike": ["bike lane","bike light","bike lock","bike computer","road bike"],
    "train": ["train of thought","on the right track","training","train station"],
    "school": ["school of thought","school of fish","boarding school","cram school",
               "cooking school","culinary school","high school","medical school"],
    "park": ["park and ride","car park","theme park","national park","business park"],
    "bridge": ["bridge the gap","burn your bridges","suspension bridge",
               "cable-stayed bridge","pedestrian bridge"],
    "tower": ["tower of strength","ivory tower","tokyo tower","control tower"],
    "island": ["island of","no man is an island","island hopping"],
    "garden": ["garden party","garden variety","botanical garden","rock garden"],
    "star": ["star sign","rock star","five-star","shooting star","star struck"],
    "moon": ["once in a blue moon","over the moon","shoot for the moon","new moon"],
    "sun": ["in the sun","fun in the sun","place in the sun","sunrise","sunset"],
    "sky": ["sky high","the sky is the limit","out of the blue sky","blue sky"],
    "earth": ["down to earth","move heaven and earth","on earth","earth shattering"],
    "wind": ["break wind","wind down","in the wind","sail close to the wind"],
    "rain": ["brain drain","right as rain","rain check","under the rain"],
    "fire": ["add fuel to the fire","catch fire","fire away","rapid fire"],
    "rock": ["between a rock and a hard place","rock bottom","rock solid"],
    "sea": ["at sea","sea change","sea legs","all at sea","out to sea"],
    "land": ["land on","by land","live off the land","over the land"],
    "field": ["field day","in the field","play the field","out of left field"],
    "river": ["sell down the river","river of","across the river"],
}

# ==========================================
# 詞形家族規則
# ==========================================
WORD_FAMILY_SUFFIXES = [
    # 動詞形式
    ("", "s"),    ("", "ed"),   ("", "ing"),  ("e", "ing"),  ("e", "ed"),
    ("", "er"),   ("", "ers"),
    # 名詞化
    ("", "ment"), ("", "ments"),("e", "ation"),("", "ation"),("", "ations"),
    ("e", "ment"),("", "ness"), ("", "ment"),  ("y", "ies"),  ("e", "ity"),
    ("", "ity"),  ("", "ship"), ("", "hood"),  ("", "dom"),
    # 形容詞化
    ("", "ful"),  ("", "less"), ("", "able"),  ("e", "able"), ("", "ible"),
    ("", "al"),   ("", "ous"),  ("", "ic"),    ("", "ive"),   ("e", "ive"),
    ("", "ary"),  ("", "ory"),
    # 副詞化
    ("", "ly"),   ("l", "lly"),
    # 比較級
    ("", "er"),   ("", "est"),  ("e", "er"),   ("e", "est"),
]

WORD_FAMILY_PREFIXES = [
    ("", "un"),   ("", "re"),   ("", "pre"),   ("", "dis"),   ("", "mis"),
    ("", "over"), ("", "under"),("", "out"),   ("", "sub"),   ("", "non"),
    ("", "de"),   ("", "co"),   ("", "anti"),  ("", "semi"),
]

# 靜態詞形家族庫（不規則變化 + 重要詞族）
WORD_FAMILY_DB: dict[str, list[str]] = {
    "go":    ["goes","going","went","gone","ago","undergo","outgo","forgo"],
    "be":    ["am","is","are","was","were","been","being"],
    "have":  ["has","had","having"],
    "do":    ["does","did","done","doing","undo","redo","overdo"],
    "make":  ["makes","made","making","maker","unmake","remake"],
    "take":  ["takes","took","taken","taking","intake","mistake","retake","overtake"],
    "get":   ["gets","got","gotten","getting","forget","beget"],
    "give":  ["gives","gave","given","giving","forgive","regive"],
    "come":  ["comes","came","coming","become","outcome","income","welcome","overcome"],
    "see":   ["sees","saw","seen","seeing","foresee","oversee"],
    "know":  ["knows","knew","known","knowing","knowledge","unknown","foreknow"],
    "think": ["thinks","thought","thinking","thinker","rethink","overthink","unthinkable"],
    "say":   ["says","said","saying","unsaid","hearsay"],
    "tell":  ["tells","told","telling","teller","untold","foretell","storytelling"],
    "find":  ["finds","found","finding","findings","refind","unfound"],
    "write": ["writes","wrote","written","writing","writer","rewrite","overwrite","handwriting","typewrite"],
    "read":  ["reads","read","reading","reader","unread","reread","misread","proofread"],
    "speak": ["speaks","spoke","spoken","speaking","speaker","outspeak","bespeak"],
    "run":   ["runs","ran","running","runner","outrun","overrun","runoff","rerun"],
    "work":  ["works","worked","working","worker","workers","workout","overwork","teamwork","rework","framework","network","homework","woodwork","artwork","handiwork"],
    "play":  ["plays","played","playing","player","replay","wordplay","gameplay","horseplay","swordplay"],
    "move":  ["moves","moved","moving","mover","movement","remove","improve","immovable"],
    "turn":  ["turns","turned","turning","turner","return","overturn","upturn","downturn"],
    "break": ["breaks","broke","broken","breaking","breaker","outbreak","breakdown","breakthrough","heartbreak","groundbreaking"],
    "call":  ["calls","called","calling","caller","recall","miscall","roll call"],
    "try":   ["tries","tried","trying","trial","retry"],
    "use":   ["uses","used","using","user","reuse","misuse","disuse","overuse","useful","useless","usable"],
    "set":   ["sets","setting","onset","offset","reset","upset","subset","mindset","dataset","dataset","inset","sunset"],
    "put":   ["puts","putting","output","input","throughput"],
    "show":  ["shows","showed","shown","showing","shower","show-off","showcase"],
    "keep":  ["keeps","kept","keeping","keeper","upkeep","bookkeeping"],
    "live":  ["lives","lived","living","liver","alive","lively","livelihood","lifestyle","outlive"],
    "love":  ["loves","loved","loving","lover","lovely","beloved","loveable"],
    "help":  ["helps","helped","helping","helper","helpful","helpless","self-help"],
    "learn": ["learns","learned","learning","learner","relearn","unlearned"],
    "teach": ["teaches","taught","teaching","teacher","reteach"],
    "build": ["builds","built","building","builder","rebuild","built-in","upbuild"],
    "grow":  ["grows","grew","grown","growing","grower","growth","grown-up","overgrow","regrow","outgrow"],
    "feel":  ["feels","felt","feeling","feelings","heartfelt"],
    "hear":  ["hears","heard","hearing","hearer","mishear","overhear","rehearse"],
    "pay":   ["pays","paid","paying","payment","repay","overpay","underpay","prepay"],
    "stand": ["stands","stood","standing","standout","withstand","outstanding","understand","bystander","standard","standby","standoff","standpoint","grandstand"],
    "lead":  ["leads","led","leading","leader","leadership","mislead","unleaded","reload"],
    "hold":  ["holds","held","holding","holder","uphold","withhold","behold","stronghold","threshold","household"],
    "follow":["follows","followed","following","follower","unfollow"],
    "start": ["starts","started","starting","starter","restart","kickstart","headstart","fresh start"],
    "stop":  ["stops","stopped","stopping","non-stop"],
    "begin": ["begins","began","begun","beginning","beginner"],
    "end":   ["ends","ended","ending","endless","unending","weekend","blend"],
    "open":  ["opens","opened","opening","opener","reopen","wide-open"],
    "close": ["closes","closed","closing","closely","closure","disclose","foreclose","enclose"],
    "change":["changes","changed","changing","changer","exchange","interchange","rearrange","unchanged"],
    "decide":["decides","decided","deciding","decision","undecided","indecisive"],
    "allow":  ["allows","allowed","allowing","allowance","disallow"],
    "create": ["creates","created","creating","creator","creation","creative","recreation","procreate"],
    "produce":["produces","produced","producing","producer","product","production","reproductive","byproduct"],
    "increase":["increases","increased","increasing","decrease"],
    "develop":["develops","developed","developing","developer","development","redevelop","underdeveloped"],
    "include":["includes","included","including","inclusion","inclusive","exclude","exclusive"],
    "consider":["considers","considered","considering","consideration","reconsider"],
    "provide":["provides","provided","providing","provision","provider"],
    "involve": ["involves","involved","involving","involvement"],
    "identify":["identifies","identified","identifying","identity","identification"],
    "require": ["requires","required","requiring","requirement"],
    "support": ["supports","supported","supporting","supporter","supportive","unsupported"],
    "control": ["controls","controlled","controlling","controller","uncontrolled","self-control"],
    "manage":  ["manages","managed","managing","manager","management","mismanage"],
    "reduce":  ["reduces","reduced","reducing","reduction","reductive","irreducible"],
    "improve": ["improves","improved","improving","improvement","unimproved"],
    "achieve": ["achieves","achieved","achieving","achievement","underachieve","overachieve"],
    "prepare": ["prepares","prepared","preparing","preparation","unprepared","preparedness"],
    "protect": ["protects","protected","protecting","protection","protective","unprotected","self-protect"],
    "connect": ["connects","connected","connecting","connection","disconnect","reconnect","interconnect"],
    "compete": ["competes","competed","competing","competition","competitive","incompetent"],
    "imagine": ["imagines","imagined","imagining","imagination","imaginative","unimaginable"],
    "organize":["organizes","organized","organizing","organization","reorganize","disorganized"],
    "realize":["realizes","realized","realizing","realization","surreal"],
    "trust":  ["trusts","trusted","trusting","trustworthy","distrust","mistrust","entrust"],
    "hope":   ["hopes","hoped","hoping","hopeful","hopeless","hopefully"],
    "care":   ["cares","cared","caring","careful","careless","caregiver","caretaker","healthcare","daycare"],
    "power":  ["powers","powered","powerful","powerless","empower","willpower","manpower","firepower","overpower","superpower"],
    "light":  ["lights","lit","lighting","enlighten","delight","highlight","moonlight","sunlight","daylight","spotlight","twilight","flashlight","lightweight","lighthearted"],
    "water":  ["waters","watered","watering","underwater","waterfall","waterproof","watercolor","waterfront"],
    "air":    ["airs","aired","airing","airborne","aircraft","airline","airfield","airport","airflow","airspace","midair","fresh air","open air"],
    "hand":   ["hands","handed","handing","handy","handout","handmade","handwriting","firsthand","secondhand","backhand","forehand","shorthand","underhanded","overhanded","handshake","handful","handover"],
    "head":   ["heads","headed","heading","headache","headline","headphones","headquarters","overhead","ahead","deadhead","forehead","figurehead"],
    "eye":    ["eyes","eyed","eyeing","eyebrow","eyelid","eyesight","eyebrow","eye-catching","bird's-eye","bull's-eye"],
    "heart":  ["hearts","hearted","heartfelt","heartbeat","heartbreak","heartwarming","wholehearted","brokenhearted","lionhearted","faint-hearted"],
    "mind":   ["minds","minded","mindful","mindset","mindless","remind","mastermind","open-minded","broad-minded"],
    "body":   ["bodies","bodily","bodywork","bodyguard","anybody","everybody","nobody","somebody"],
    "life":   ["lives","lifelong","lifestyle","lifetime","lifelike","midlife","afterlife","wildlife","nightlife"],
    "time":   ["times","timed","timing","timely","overtime","pastime","sometime","daytime","nighttime","bedtime","lifetime","part-time","full-time","real-time","halftime"],
    "day":    ["days","daily","daytime","daylight","birthday","holiday","weekday","today","yesterday","everyday"],
    "night":  ["nights","nightly","nightmare","midnight","overnight","nightfall","nightlife","goodnight"],
    "week":   ["weeks","weekly","weekday","weekend","midweek"],
    "year":   ["years","yearly","annual","yearbook","midyear"],
    "word":   ["words","wording","wordy","keyword","password","watchword","buzzword","wordplay","crossword"],
    "book":   ["books","booked","booking","booklet","notebook","textbook","bookstore","bookshelf","bookmark","handbook","cookbook"],
    "school": ["schools","schooling","schoolwork","preschool","homeschool","graduate school","high school","boarding school"],
    "road":   ["roads","roadway","roadside","roadblock","crossroad","railroad","offroad"],
    "street": ["streets","streetcar","streetlight","mainstream","side street"],
    "house":  ["houses","housed","housing","household","greenhouse","warehouse","courthouse","schoolhouse","storehouse","housekeeper"],
    "room":   ["rooms","roomy","roommate","bedroom","bathroom","classroom","living room","dining room","courtroom","restroom","mushroom","legroom"],
    "door":   ["doors","doorstep","doorbell","doorknob","doorway","outdoor","indoor"],
    "window": ["windows","windowed","windowpane","windowsill","showcase window"],
    "floor":  ["floors","flooring","floorboard","downstairs","upstairs","groundfloor"],
    "table":  ["tables","tabled","tablecloth","turntable","timetable","roundtable"],
    "chair":  ["chairs","chaired","chairperson","chairman","armchair","wheelchair"],
    "money":  ["monetary","moneymaker","fundraise"],
    "food":   ["foods","foodie","foodbank","seafood","junk food","fast food"],
    "work":   ["works","worked","working","worker","workers","workout","workplace","overwork","teamwork","rework","framework","network","homework","woodwork","artwork"],
    "bike":   ["bikes","biked","biking","biker","mountain bike","road bike","motorbike","e-bike"],
    "train":  ["trains","trained","training","trainer","trainee","retrain","overtraining"],
    "play":   ["plays","played","playing","player","replay","gameplay","horseplay","swordplay","workplace"],
    "dance":  ["dances","danced","dancing","dancer","ballroom dance","street dance"],
    "music":  ["musical","musician","musicianship"],
    "sport":  ["sports","sporting","sportsman","sportswoman","sportswear","water sport","air sports"],
    "art":    ["arts","artistic","artistry","artwork","artisan","artist","state-of-the-art"],
    "science":["sciences","scientific","scientist","prescience"],
    "health": ["healthy","healthful","healthcare","unhealthy","mental health","public health"],
    "energy": ["energies","energize","energetic","unenergetic"],
    "nature": ["natural","naturally","naturalist","supernatural","unnatural"],
    "culture":["cultural","culturally","multiculture","subculture","agriculture"],
    "economy":["economies","economic","economical","economize","macroeconomy"],
    "society":["societies","social","socially","socialize","antisocial","unsocial"],
    "family": ["families","familiar","familiarize","unfamiliar"],
    "friend": ["friends","friendly","friendship","unfriendly","befriend"],
    "child":  ["children","childhood","childlike","childish","childcare"],
    "person": ["persons","personal","personally","personality","impersonal","personnel"],
    "people": ["peoples","populate","population","overpopulate","underpopulate"],
    "student":["students","study","studious","studies","postgraduate","undergraduate"],
    "teacher":["teachers","teach","taught","teachings","reteach"],
    "doctor": ["doctors","doctoral","doctorate","medical doctor"],
    "city":   ["cities","citywide","city-state"],
    "country":["countries","countryside","countrywide","cross-country"],
    "world":  ["worlds","worldwide","worldly","otherworldly"],
    "earth":  ["earthly","earthen","earthquake","earthworm","unearth","down-to-earth"],
    "sea":    ["seas","seashore","seabed","seabird","seawater","seaport","seafood","seaside","overseas","seascape"],
    "sky":    ["skies","skyline","skylight","skyscraper","sky-high"],
    "sun":    ["suns","sunny","sunshine","sunlight","sunrise","sunset","sunscreen","sunburn","sunflower"],
    "moon":   ["moons","moony","moonlight","moonrise","moonshine","honeymoon"],
    "star":   ["stars","starry","stardom","starfish","starburst","star-shaped"],
    "fire":   ["fires","fired","firing","fireplace","firework","firefly","firefighter","campfire","crossfire","gunfire","wildfire"],
    "ice":    ["ices","iced","icy","iceberg","icecap","ice cream","ice hockey","icebreaker","de-ice","black ice"],
    "snow":   ["snows","snowy","snowfall","snowflake","snowboard","snowman","snowstorm","snowplow"],
    "rain":   ["rains","rainy","rainfall","rainforest","rainbow","rainstorm","rainwater","raincoat","raindrops"],
    "wind":   ["winds","windy","windfall","windmill","windshield","windstorm","downwind","upwind"],
    "cloud":  ["clouds","cloudy","cloud-based","overcast"],
    "storm":  ["storms","stormy","brainstorm","snowstorm","thunderstorm"],
    "rock":   ["rocks","rocky","rockstar","bedrock","shamrock","cornerstone"],
    "sand":   ["sands","sandy","sandstorm","sandcastle","quicksand"],
    "gold":   ["golden","goldfish","gold rush","gold medal"],
    "silver": ["silvery","silver medal","silver lining"],
    "iron":   ["irons","irony","ironically","cast-iron"],
    "steel":  ["steels","steely","stainless steel"],
    "wood":   ["woods","wooden","woodland","woodwork","woodpecker","firewood","hardwood","softwood"],
    "glass":  ["glasses","glassy","fiberglass","looking glass","sandglass","hourglass"],
    "paper":  ["papers","paperwork","paperback","newspaper","wallpaper","sandpaper"],
    "phone":  ["phones","phoned","phoning","telephone","smartphone","earphone","headphone","microphone"],
    "computer":["computers","compute","computing","computerized"],
    "screen": ["screens","screening","screensaver","touchscreen","widescreen"],
    "data":   ["database","dataset","data-driven","big data"],
    "network":["networks","networked","networking","social network","neural network"],
}


# ==========================================
# 主要函數
# ==========================================

def _build_phrase_index(all_stems: list[str]) -> dict[str, list[str]]:
    """
    從完整詞彙清單建立「單字 → 含此單字的片語」快速索引。
    這是「動態」的：直接從你的學習檔案清單抽取，永遠是最新的。
    """
    phrases = [w for w in all_stems if ' ' in w and not re.search(r'\s\d+$', w)]
    index: dict[str, list[str]] = defaultdict(list)
    for phrase in phrases:
        for token in phrase.split():
            t = token.strip().lower().rstrip('.,!?;:')
            if len(t) > 2:
                index[t].append(phrase)
    return dict(index)


def get_phrasal_verbs(word: str, phrase_index: dict, all_stems_set: set) -> list[dict]:
    """
    ① 片語動詞 / 相關片語
    來源：動態從清單抽取 + 靜態 COLLOCATION_DB
    """
    results: dict[str, dict] = {}
    w = word.lower()

    # 從清單動態抽取
    for phrase in phrase_index.get(w, []):
        if phrase != w:
            results[phrase] = {
                "word":      phrase,
                "in_list":   phrase in all_stems_set,
                "source":    "list",
            }

    # 從靜態搭配詞庫補充
    for phrase in COLLOCATION_DB.get(w, []):
        if phrase not in results and phrase != w:
            results[phrase] = {
                "word":    phrase,
                "in_list": phrase in all_stems_set,
                "source":  "collocation_db",
            }

    # 排序：清單中存在的優先
    return sorted(results.values(), key=lambda x: (0 if x["in_list"] else 1, x["word"]))


def get_collocations(word: str, all_stems_set: set) -> list[dict]:
    """
    ② 搭配詞 Collocation
    主要來自靜態 COLLOCATION_DB，找包含此詞的搭配組合。
    """
    results: dict[str, dict] = {}
    w = word.lower()

    # 此詞作為 head word
    for phrase in COLLOCATION_DB.get(w, []):
        if phrase not in results:
            results[phrase] = {
                "word":    phrase,
                "in_list": phrase in all_stems_set,
                "role":    "head",
            }

    # 此詞出現在其他 head word 的搭配中
    for head, phrases in COLLOCATION_DB.items():
        for phrase in phrases:
            if re.search(r'\b' + re.escape(w) + r'\b', phrase) and phrase not in results:
                results[phrase] = {
                    "word":    phrase,
                    "in_list": phrase in all_stems_set,
                    "role":    "modifier",
                }

    return sorted(results.values(), key=lambda x: (0 if x["in_list"] else 1, x["word"]))


def get_word_family(word: str, all_stems_set: set) -> list[dict]:
    """
    ③ 詞形家族 Word Family
    來源：靜態 WORD_FAMILY_DB + 規則推導
    """
    results: dict[str, dict] = {}
    w = word.lower()

    # 靜態詞形家族庫
    if w in WORD_FAMILY_DB:
        for form in WORD_FAMILY_DB[w]:
            if form != w and form not in results:
                results[form] = {
                    "word":    form,
                    "in_list": form in all_stems_set,
                    "source":  "family_db",
                }

    # 也找此詞是否是別人的 family 成員
    for base, forms in WORD_FAMILY_DB.items():
        if base != w and w in forms:
            # 把整個家族加入
            results[base] = {
                "word":    base,
                "in_list": base in all_stems_set,
                "source":  "family_db",
            }
            for form in forms:
                if form != w and form not in results:
                    results[form] = {
                        "word":    form,
                        "in_list": form in all_stems_set,
                        "source":  "family_db",
                    }

    # 規則推導
    for strip_end, add_end in WORD_FAMILY_SUFFIXES:
        if strip_end:
            if not w.endswith(strip_end):
                continue
            stem = w[:-len(strip_end)]
        else:
            stem = w
        candidate = stem + add_end
        if candidate != w and len(candidate) >= 3 and candidate not in results:
            results[candidate] = {
                "word":    candidate,
                "in_list": candidate in all_stems_set,
                "source":  "rule",
            }

    for strip_start, add_start in WORD_FAMILY_PREFIXES:
        if strip_start:
            if not w.startswith(strip_start):
                continue
            base = w[len(strip_start):]
        else:
            base = w
        candidate = add_start + base
        if candidate != w and len(candidate) >= 3 and candidate not in results:
            results[candidate] = {
                "word":    candidate,
                "in_list": candidate in all_stems_set,
                "source":  "rule",
            }

    # 只保留：在清單中存在 或 規則推導的常見形式（過濾噪音）
    filtered = {k: v for k, v in results.items()
                if v["in_list"] or v["source"] in ("family_db",)}

    return sorted(filtered.values(), key=lambda x: (0 if x["in_list"] else 1, x["word"]))


def build_semantic_links(word: str, phrase_index: dict, all_stems_set: set) -> dict:
    """
    對單一詞彙建立完整語義網絡。
    只處理單字（非片語），片語另做處理。
    """
    if ' ' in word:
        return {}

    phrasal = get_phrasal_verbs(word, phrase_index, all_stems_set)
    colloc  = get_collocations(word, all_stems_set)
    family  = get_word_family(word, all_stems_set)

    # 去重：三層之間互相去重，避免同一詞出現多次
    seen = set()
    def dedup(items):
        out = []
        for item in items:
            if item["word"] not in seen and item["word"] != word:
                seen.add(item["word"])
                out.append(item)
        return out

    phrasal = dedup(phrasal)
    colloc  = dedup(colloc)
    family  = dedup(family)

    if not phrasal and not colloc and not family:
        return {}

    return {
        "phrasal_verbs": phrasal[:20],   # 最多 20 個
        "collocations":  colloc[:20],
        "word_family":   family[:25],
    }