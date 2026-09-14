from sva_common import samples_for, pred_atoms, pool_items, CORPUS
S70 = set(pool_items("s70", CORPUS))
def other_samples(iid):
    ss = samples_for(iid, "dev")[1:] + (samples_for(iid, "s70") if iid in S70 else [])
    return [pred_atoms(s, iid) for s in ss]
