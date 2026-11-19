import pickle, re, collections, math
D=pickle.load(open('/home/claude/work/pooled/weeks.pkl','rb'))
W=re.compile(r"[a-z][a-z0-9'_]+"); URL=re.compile(r'https?://\S+|\[.*?\]\(.*?\)|/?u/\w+|/?r/\w+')
authors=set(); C=collections.defaultdict(collections.Counter); U=collections.defaultdict(lambda: collections.defaultdict(set))
for wk in list(D):
    recs,home=D.pop(wk)
    for a,s,sc,l,t,b in recs:
        authors.add(a.lower()); h=home[a]
        txt=' '.join(x for x in b.split('\n') if not x.lstrip().startswith('>'))
        ws=W.findall(URL.sub(' ',txt.lower()))
        terms=set(ws)|{ws[i]+' '+ws[i+1] for i in range(len(ws)-1)}
        for x in terms:
            C[h][x]+=1
    del recs
    # prune rare
    tot=collections.Counter()
    for h in C: tot.update(C[h])
    keep={x for x,n in tot.items() if n>=10}
    for h in C: C[h]=collections.Counter({x:n for x,n in C[h].items() if x in keep})
    print(wk,len(keep),flush=True)
pickle.dump((dict(C),authors),open('counts.pkl','wb'))
