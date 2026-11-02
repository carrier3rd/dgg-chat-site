# Community glossary (v1, Nov 1, 2026)

Machine-readable version: `data/glossary.csv` (55 terms). Count script: `scripts/glossary_count.py`.
Source tags in the CSV: [verified] = checked against news coverage; [per the owner] = his community knowledge; untagged = read from comment context only.

## What this is
Terms that mark where a comment comes from. For each of the 18 communities, I took every comment its regulars wrote
(home = the sub where the account commented most that week), in any sub, across the five pulled weeks (Aug 18, Sep 8,
Sep 22, Oct 13, Oct 20; 1.55M comments). I ranked words and two-word phrases by weighted log-odds against everyone else
(Monroe et al.'s "Fightin' Words", with an informative Dirichlet prior). I dropped quoted lines, URLs, u/ and r/ links,
and any token that matches a Reddit username in the data. For the slang candidates, I read four random usage examples
each and computed rates per 10,000 comments by home community.

"rate_top" is how often the most frequent community's regulars use the term, per 10k of their comments. "rate_all" is
the rate across all 18 communities. A term is a good marker when rate_top is many times rate_all and the term appears
mainly in one community.

## Predictions (stated before the run) and results
1. **Held.** Names and out-group labels dominate every community's top 20: Ethan, Hila, crew and Tamara for h3;
   Pisco, Hutch, Mehdi and Lonerbox for Destiny; Sam and "Islamist" for samharris; Zohran, Abdul and Tisch for Hasan.
   True coded slang is a minority of the markers.
2. **Mostly held, one miss.** Mocking nicknames do sit in the rival community. "Pestiny" is 11x the average rate among
   LeftoversH3 regulars (9.8 per 10k), and "sexpestiny" is highest in LeftoversH3 (5.9), then Hasan regulars (4.7).
   The miss: "dggers" is used most by Destiny's own regulars (7.1), as a self-label.
3. **Held.** PCM's markers are flair and quadrant language: auth, unflaired, lib left, "based and", pilled.
4. **Partly held.** Tankie's markers are lib(s), imperialist, imperial core, global south, material conditions, comrade,
   DPRK, PSL and CPC. "AES" is not a Tankie marker in this data. It means Abdul El-Sayed, and pakman regulars use it most
   (123 per 10k).
5. **Held, with a different term than I guessed.** "Lib" is near the top in both PCM and Tankie with opposite meanings.
   In PCM it means libertarian (lib left, lib right). In Tankie it means liberal, as an insult. "Zionist" never appeared
   as a self-description in any top list. It shows up only as an accusation (Hasan, Palestine, LeftoversH3) or in
   neutral debate (IsraelPalestine).

## The strongest markers by community (from the full ranked lists)
- **LeftoversH3 (h3 snark):** fungi (h3 fans, 118 per 10k vs 8 overall), pedo troll (Ethan), Frogan, Denims, gwam, egg,
  skulls, CPS, "your post has" (automod). Also the highest rate of pestiny and hasbara among drama subs.
- **h3h3productions:** Kate, AB, Harley, Lena, "the crew", "the pod", Teddy Fresh, unfollowed, parasocial, snarkers.
- **Destiny:** regarded/regard, dgg, Pisco, Hutch, Mehdi, Whick, Soypill, Lonerbox, Connor, "dear leader" (about
  Destiny), brain broken, slopulism, sweeping, lefties, tankies.
- **Hasan_Piker:** Zohran, Tisch (NYPD commissioner), Angie, electoralism, meat pic, "the flame" (ironic Kirk chant),
  liberal zionist, misogyny, Shane Gillis, Ed Sheeran, Macklemore.
- **Palestine:** free palestine, fuck israel, IOF, zio/zios, genocidal, boycott.
- **TankieTheDeprogram:** comrade, imperial core, global south, material conditions, bourgeois, proletariat, PSL, CPC,
  DPRK, campist (shared with DSA).
- **dsa:** chapter, "in dsa", organizing, democratic socialism, caucus, campist.
- **PoliticalCompassMemes:** auth, unflaired, lib left, "based and", pilled, the r-word (95% of all uses), culture war.
- **neoliberal:** !ping, DT, waow, succ, median, "the linked", Claude/Anthropic/OpenAI/AI (the subs' AI threads), Lula.
- **Conservative:** mostly peaceful, sharia (law), the Bee, SAVE Act, Thune, Ilhan/Omar, jurors.
- **ukraine:** slava ukraini, orcs, vatnik, stay strong, refineries, Starlink.
- **thebulwark:** Sarah, Tim, JVL, Kristol, Carville, Manchin, M4A.
- **thedavidpakmanshow:** AES, uncommitted (movement), blue MAGA, Jeffries, Kushner.
- **samharris:** Islamist/Islamism, Muslim Brotherhood, IRGC, condemn/disavow, meditation, lab leak.
- **Asmongold:** roach king, Kaise, Sony, devs, DEI, woke, Veilguard. **atrioc:** glizzy, Pangram, Poki.

## How to use it
- **Combinations, not single terms:** one word is weak evidence, and several markers from the same community are strong.
  "Sexpestiny" plus "fungi" in one comment almost certainly comes from h3 snark. "Sexpestiny" plus "Zohran" or "Tisch"
  points to Hasan regulars.
- **Reading a coded sheet:** these terms tell a coder where a comment is coming from. Keep them out of anything meant to
  be blind to community, or flag them as "community-revealing" so we can measure how much they sway codes.
- **Same word, different meaning:** lib (PCM vs Tankie), based (everywhere), snarkers (h3 fans and Destiny use it as an
  insult; snark uses it about itself), AES (Abdul El-Sayed vs Actually Existing Socialism).
- **Slurs:** zio and the r-word are slurs, and "orcs" for Russian soldiers is dehumanizing. They are listed because they
  are among the strongest markers, not as endorsements.

## Caveats
- **Topical:** five weeks, dominated by the Ethan affair, the Michigan Senate race and the RNC's Hasan photo. Many names
  are topical and will fade. The durable slang is the short list: regarded, dggers, fungi, pestiny, waow, succ, ping/DT,
  unflaired/flair, imperial core, IOF, orcs, mostly peaceful.
- **Description, not detection:** these markers show where a commenter comes from. They are not evidence of
  coordination or bots.
- **Refresh needed:** the counts need refreshing with each new weekly pull. The script reruns on the pooled pickle in
  about ten minutes.

## Full term list

Rates are per 10,000 comments by that community's regulars ("top") and across all 18 communities ("all").
Source tags: [verified] = checked against news coverage; [per the owner] = the owner's community knowledge; untagged = read from comment context.

| Term | Used most by | Rate (top / all) | Kind | Meaning | What it signals |
|---|---|---|---|---|---|
| roach king | Asmongold | 14.2 / 0.7 | nickname | Nickname for Asmongold [per the owner; matches context] | Asmongold regular when affectionate; LSF when mocking |
| glizzy | atrioc | 78.6 / 0.3 | nickname | Atrioc in-joke | atrioc regular |
| pangram | atrioc | - | name | Pangram, an AI-text detector; atrioc threads about scripts flagged as AI-written [verified product; atrioc link from context] | atrioc regular |
| bee | Conservative | 21.0 / 1.4 | name | Babylon Bee satire site | Conservative regular |
| mostly peaceful | Conservative | 19.0 / 0.9 | ironic | Mocking 2020 media phrasing about protests | Conservative or right regular |
| brain broken | Destiny | 11.2 / 1.9 | house phrase | Someone whose politics got warped by an issue or audience | Destiny regular |
| dear leader | Destiny | 14.0 / 2.7 | ironic | Destiny regulars joking about Destiny; elsewhere used for Trump | Destiny regular when about Destiny |
| dggers | Destiny | 7.1 / 1.2 | self-label | Destiny's community (destiny.gg); used by members about themselves | Destiny regular when used neutrally; rival when sneering |
| hutch | Destiny | 53.3 / 8.9 | name | Commentator in the Destiny orbit; also discussed in LeftoversH3 (23.5) | Destiny regular or H3 snark |
| lefties | Destiny | 39.7 / 8.6 | out-group label | Dismissive term for the online left | Destiny or PCM or Bulwark regular; center-left or right critic of the left |
| lonerbox | Destiny | 19.2 / 3.1 | name | Commentator in the Destiny orbit | Destiny regular |
| omnicause | Destiny | 1.7 / 0.7 | out-group label | Left bundling all causes together (often I/P) | Center or right critic of the left; weak signal |
| pisco | Destiny | 94.2 / 11.5 | name | Former lawyer and debater; hosts the Lib and Learn panel (some members have left); now feuding with Destiny; liberal to left [per the owner; Lib and Learn matches comment context] | Destiny regular; Destiny-orbit drama |
| regard | Destiny | - | in-group slur | Same as regarded (noun) | Destiny regular |
| regarded | Destiny | 86.4 / 13.1 | in-group slur | Softened r-word; DGG house style | Destiny regular |
| slopulism | Destiny | 7.1 / 1.6 | house phrase | Slop + populism; low-effort populist politics left or right | Destiny or pakman regular |
| soypill | Destiny | 28.5 / 3.5 | name | Liberal-to-left commentator, sympathetic to Hasan; recently traveled to the West Bank [per the owner] | Destiny regular |
| sweeping | Destiny | 13.7 / 3.7 | house phrase | Defending or covering for someone (sweeping for X) | Destiny regular in political threads |
| whick | Destiny | 24.8 / 3.1 | name | Online debate-panel host; liberal [per the owner] | Destiny regular |
| angie | dsa | 31.3 / 1.8 | name | Angie Nixon; Florida state rep and DSA-backed 2026 Democratic US Senate nominee (won Aug primary; later distanced from DSA) [verified] | DSA or Hasan regular |
| campist | dsa | 13.2 / 0.6 | charged term | Siding with any anti-US bloc; insult from left anti-campists and defended by Tankie | DSA or Tankie regular; intra-left fight |
| snarkers | h3h3productions | 45.8 / 15.3 | out-group label | Members of snark communities; used by h3 fans and Destiny regulars (32.0) as an insult; snark also self-applies | h3 fan or Destiny regular when hostile |
| teddy fresh | h3h3productions | 26.3 / 6.1 | name | Hila Klein's clothing brand | h3 fan or snark |
| meat pic | Hasan_Piker | 13.2 / 0.6 | event | RNC's shirtless Hasan photo | Hasan regular; also H3 snark |
| the flame | Hasan_Piker | 17.5 / 2.0 | ironic | We carry the flame; Charlie Kirk memorial chant used mockingly | Hasan regular when mocking; PCM or right when sincere |
| tisch | Hasan_Piker | 21.5 / 1.2 | name | NYPD commissioner Jessica Tisch; Mamdani's choice to keep her | Hasan or DSA regular; NYC left politics |
| hasbara | IsraelPalestine | 36.0 / 3.6 | charged term | Israeli state public diplomacy; used as accusation of pro-Israel propaganda | Pro-Palestine side (IsraelPalestine or Palestine or H3 snark) |
| denims | LeftoversH3 | 49.7 / 5.6 | name | Twitch streamer who streams before Hasan goes live, known as 'Hasan's waiting room' [per the owner]; sued by Ethan Klein in 2025 for copyright; ruled fair use [verified] | H3 snark regular; lawsuit threads |
| egg | LeftoversH3 | 45.6 / 6.2 | nickname | Nickname about baldness for a person in the h3 orbit [per the owner]; comments also use it about body shape | H3 snark regular |
| frogan | LeftoversH3 | 54.8 / 6.4 | name | Left-leaning streamer in the Hasan orbit; the owner's assessment: unironically pro-terrorism and anti-American [per the owner, unsourced]; sued by Ethan Klein in 2025 for copyright; default later lifted [verified] | H3 snark regular; lawsuit threads |
| fungi | LeftoversH3 | 118.0 / 8.4 | out-group label | Snark term for h3 podcast fans | H3 snark regular; hostile to h3 fanbase |
| gwam | LeftoversH3 | 59.9 / 5.6 | name | H3 crew member and co-host | H3 snark or h3 fan |
| pedo troll | LeftoversH3 | 29.7 / 2.2 | nickname | Snark epithet for Ethan Klein | H3 snark regular |
| pestiny | LeftoversH3 | 9.8 / 0.9 | nickname | Mocking name for Destiny (sex pest + Destiny) | H3 snark or Hasan side; hostile to Destiny |
| sexpestiny | LeftoversH3 | 5.9 / 1.1 | nickname | Same as pestiny; also used by Hasan regulars (4.7) | H3 snark or Hasan side; hostile to Destiny |
| chud | neoliberal | 11.4 / 7.3 | out-group label | Right-wing person; spread across neoliberal and LSF and PCM and Destiny | Weak signal; general left or center use |
| dt | neoliberal | - | house mechanic | Discussion Thread (99% of uses are neoliberal regulars) | neoliberal regular |
| ping | neoliberal | 84.1 / 20.7 | house mechanic | !ping bot that alerts topic groups | neoliberal regular |
| succ | neoliberal | 17.0 / 4.1 | house label | Social democrat (succdem) | neoliberal regular |
| waow | neoliberal | 22.8 / 5.8 | house reaction | Reaction to an edgy take that the poster half agrees with but will not say so [per the owner] | neoliberal regular |
| iof | Palestine | 47.7 / 1.7 | charged term | Israeli Occupation Forces; hostile rename of IDF | Strongly pro-Palestine; Palestine or H3 snark or Hasan regulars |
| zio | Palestine | 44.1 / 1.4 | slur | Short for Zionist; widely treated as a slur | Palestine regular; also quoted by critics |
| auth right | PoliticalCompassMemes | 23.8 / 2.5 | flair | Political compass quadrant | PCM regular |
| based | PoliticalCompassMemes | 222.9 / 103.7 | approval | Approval; heavy in PCM; Destiny 153.7 | PCM or Destiny regular; weak signal alone |
| lib left | PoliticalCompassMemes | 24.2 / 2.6 | flair | Political compass quadrant; lib = libertarian here | PCM regular |
| unflaired | PoliticalCompassMemes | - | flair | PCM user without a quadrant flair; ritual insult | PCM regular |
| global south | TankieTheDeprogram | - | house phrase | Non-Western countries; heavy Tankie use (48% of all uses) | Tankie regular |
| imperial core | TankieTheDeprogram | - | house phrase | Western countries in Marxist-Leninist framing | Tankie regular |
| libs | TankieTheDeprogram | 79.6 / 11.7 | out-group label | Liberals as an insult from the left | Tankie regular (also PCM and Destiny at lower rates) |
| material conditions | TankieTheDeprogram | - | house phrase | Marxist framing phrase | Tankie regular |
| aes | thedavidpakmanshow | 122.9 / 13.6 | abbreviation | Abdul El-Sayed (Michigan Senate candidate); not Actually Existing Socialism in this data | Pakman or Bulwark or Destiny regular discussing the Michigan race |
| blue maga | thedavidpakmanshow | 22.0 / 1.1 | out-group label | Hyper-partisan Democrats; insult from left or center | Pakman regular (both directions) |
| zog | thedavidpakmanshow | 5.1 / 0.5 | charged term | Antisemitic conspiracy term; mostly appears in accusations of zog-posting | Mostly critics quoting it; check context |
| orcs | ukraine | 49.2 / 2.0 | dehumanizing | Russian soldiers | r/ukraine regular; strongly pro-Ukraine |
| slava ukraini | ukraine | - | slogan | Glory to Ukraine (90% of uses are r/ukraine regulars) | r/ukraine regular |
| vatnik | ukraine | 5.4 / 0.3 | out-group label | Pro-Kremlin person | r/ukraine or neoliberal regular |
