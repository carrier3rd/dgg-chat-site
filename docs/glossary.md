# Community glossary (v1, Nov 1, 2026)

Machine-readable version: `data/glossary.csv` (55 terms). Count script: `scripts/glossary_count.py`.

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
