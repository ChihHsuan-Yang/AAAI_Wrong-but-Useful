import json, sys
d = json.load(open(sys.argv[1]))
print("analysis_version:", d.get("analysis_version"))
tot = {}
for bench, blk in sorted(d.get("benchmarks", {}).items()):
    for cls, c in sorted(blk.get("classes", {}).items()):
        if cls not in ("wrong", "correct"): continue
        ci = c.get("problem_cluster_bootstrap_95ci_helpful_share")
        print("  %-10s %-8s changing=%5s eligible=%6s share=%.4f ci=[%.4f, %.4f] pairs=%6s both=%4s" % (
            bench, cls, c.get("changing_loo_observations"), c.get("eligible_loo_observations"),
            c.get("helpful_share_among_changing_observations", float('nan')),
            ci[0] if ci else float('nan'), ci[1] if ci else float('nan'),
            c.get("unique_problem_hypothesis_pairs"), c.get("problems_with_both_help_and_harm")))
        k = cls
        t = tot.setdefault(k, {"chg":0,"elig":0,"help":0,"pairs":0,"both":0})
        t["chg"] += c.get("changing_loo_observations",0) or 0
        t["elig"] += c.get("eligible_loo_observations",0) or 0
        t["help"] += round((c.get("helpful_share_among_changing_observations",0) or 0)*(c.get("changing_loo_observations",0) or 0))
        t["pairs"] += c.get("unique_problem_hypothesis_pairs",0) or 0
        t["both"] += c.get("problems_with_both_help_and_harm",0) or 0
print("  -- POOLED --")
for k,v in tot.items():
    print("  %-8s changing=%5d eligible=%6d helpful=%5d share=%.4f pairs=%6d both=%4d" % (
        k, v["chg"], v["elig"], v["help"], v["help"]/v["chg"] if v["chg"] else 0, v["pairs"], v["both"]))
