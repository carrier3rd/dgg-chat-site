"""Shared language features for chat messages and Reddit comments (socialscope).

One function, features(text, emotes), returns per-message counts. Chat (OverRustle archive, live DGG log) and Reddit
use the same code so their numbers compare directly. Rates are computed later as per-100-words or per-message shares.

Word lists are short, hand-picked and fixed before the analysis (docs/orl-pass2-predictions.md). They measure style,
not meaning: "argument markers" counts words people use when giving reasons, whether or not the reasoning is good.
"""
import re

WORD = re.compile(r"[A-Za-z0-9_']+")
LINK = re.compile(r"(https?://\S+|www\.\S+|\S+\.(com|gg|tv|be|io|org|net|co)(/\S*)?)", re.I)

ARGUE = set("because therefore however although though since thus hence evidence source sources argument argue "
            "argues point premise conclusion reason reasons implies means unless whereas consequently "
            "contradiction contradicts fallacy logically logic".split())
HEDGE_WORDS = set("maybe perhaps probably possibly likely seems seem apparently arguably somewhat presumably "
                  "imo imho guess".split())
HEDGE_PHRASES = re.compile(r"\b(i think|i feel like|i believe|kind of|sort of|i'm not sure|im not sure|not sure|"
                           r"it seems|i suspect|could be|might be|i'd say|id say)\b", re.I)
FIRST_SING = set("i i'm im i've ive i'd id i'll me my mine myself".split())
FIRST_PLUR = set("we we're we've us our ours ourselves".split())
SECOND = set("you you're youre you've youve you'd youd you'll youll your yours yourself yourselves u ur".split())
THIRD = set("he he's hes him his himself she she's shes her hers herself they they're theyre them their theirs "
            "themselves".split())
PROFANE = set("fuck fucking fucked fucker fuckin fk fking shit shitty bullshit damn goddamn bitch bitches ass "
              "asshole dick dickhead cunt crap piss pissed bastard wtf stfu lmfao".split())
INSULT = set("idiot idiots moron morons stupid dumb dumbass clown clowns loser losers pathetic trash garbage "
             "braindead brainlet fraud grifter grifters liar liars coward cowards scum pos virgin incel snake hack "
             "shill shills unfunny cringe bozo dork degenerate degen subhuman rat rats leech parasite simp "
             "dipshit jackass retard retarded regarded".split())
HOSTILE_PHRASES = re.compile(r"\b(fuck (you|u|off|this|him|her)|kys|kill yourself|shut up|shut the fuck up|stfu|"
                             r"you suck|u suck|hate (you|u|him|her|this guy)|go away|nobody likes|no one likes|"
                             r"get banned|get cancelled|end your|ur done|you're done|youre done|fell off|"
                             r"(is|so|such) (a )?(joke|fraud|loser|clown)|worst streamer|unwatchable)\b", re.I)
SLUR = re.compile(r"(n[i1!]gg|f[a@]gg?(ot)?s?\b|tr[a@]nn(y|ie)|k[i1]ke|ch[i1]nk|sp[i1]c\b|beaner|wetback|"
                  r"\bcoons?\b|dyke|g[o0]{2}k)", re.I)
NEGATION = set("not no never nothing nobody none nor isn't isnt aren't arent wasn't wasnt don't dont doesn't "
               "doesnt didn't didnt can't cant won't wont shouldn't shouldnt wouldn't wouldnt".split())
POLITICS = set("trump biden bernie sanders warren obama hillary clinton election vote voting democrat democrats "
               "republican republicans gop liberal liberals conservative conservatives maga leftist leftists left "
               "right socialism socialist capitalism communist communism fascist fascism policy policies".split())

# Feature names, in the order every output table uses.
FIELDS = ["words", "chars", "types", "argue", "hedge", "first_sing", "first_plur", "second", "third", "profane",
          "insult", "slur", "negation", "politics", "emotes", "caps_words", "question", "exclaim", "link", "numbers"]


def features(text, emotes=frozenset()):
    """Counts for one message. 'words' excludes emotes and links; booleans are 0/1."""
    no_link = LINK.sub(" ", text)
    raw = no_link.split()
    em = sum(1 for w in raw if w in emotes)
    toks = [w for w in WORD.findall(no_link) if w not in emotes]
    low = [w.lower() for w in toks]
    n = len(low)
    f = dict.fromkeys(FIELDS, 0)
    if not n and not em:
        return f
    lowtext = " ".join(low)
    f["words"] = n
    f["chars"] = sum(len(w) for w in low)
    f["types"] = len(set(low))
    for w in low:
        if w in ARGUE: f["argue"] += 1
        if w in HEDGE_WORDS: f["hedge"] += 1
        if w in FIRST_SING: f["first_sing"] += 1
        elif w in FIRST_PLUR: f["first_plur"] += 1
        elif w in SECOND: f["second"] += 1
        elif w in THIRD: f["third"] += 1
        if w in PROFANE: f["profane"] += 1
        if w in INSULT: f["insult"] += 1
        if w in NEGATION: f["negation"] += 1
        if w in POLITICS: f["politics"] += 1
        if w.isdigit(): f["numbers"] += 1
    f["hedge"] += len(HEDGE_PHRASES.findall(lowtext))
    f["slur"] = len(SLUR.findall(no_link))
    f["emotes"] = em
    f["caps_words"] = sum(1 for w in toks if len(w) >= 3 and w.isupper() and w.isalpha())
    f["question"] = int("?" in text)
    f["exclaim"] = int("!" in text)
    f["link"] = int(bool(LINK.search(text)))
    return f


def is_hostile(text, low_words):
    """Insult, slur or hostile phrase anywhere in the message."""
    return bool(INSULT & set(low_words)) or bool(SLUR.search(text)) or bool(HOSTILE_PHRASES.search(text))


class Acc:
    """Sums features over messages; rates come out of summary()."""

    def __init__(self):
        self.n = 0
        self.s = dict.fromkeys(FIELDS, 0)
        self.vader_sum = 0.0
        self.vader_n = 0
        self.ttr_sum = 0.0

    def add(self, f, vader=None):
        self.n += 1
        for k in FIELDS:
            self.s[k] += f[k]
        if f["words"]:
            self.ttr_sum += f["types"] / f["words"]
        if vader is not None:
            self.vader_sum += vader
            self.vader_n += 1

    def summary(self):
        n, s = self.n, self.s
        w = s["words"] or 1
        out = {"messages": n, "mean_words": round(s["words"] / n, 2) if n else None,
               "mean_word_len": round(s["chars"] / w, 2), "type_token": round(self.ttr_sum / n, 3) if n else None}
        for k in ("argue", "hedge", "first_sing", "first_plur", "second", "third", "profane", "insult", "negation",
                  "politics", "emotes", "caps_words", "numbers"):
            out[k + "_per100w"] = round(100 * s[k] / w, 2)
        for k in ("question", "exclaim", "link"):
            out[k + "_share"] = round(s[k] / n, 4) if n else None
        out["slur_per10k_msgs"] = round(1e4 * s["slur"] / n, 2) if n else None
        out["vader_mean"] = round(self.vader_sum / self.vader_n, 3) if self.vader_n else None
        return out
