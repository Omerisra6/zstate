import math

MAX_GOALS = 5
PTS_EXACT = 15
PTS_DIRECTION = 8
PTS_WINNER = 12
PTS_SCORER = 12

CURRENT_POINTS = {"omer": 124, "shahar": 130, "itay": 117}
CURRENT_OMER_PRED = (1, 2)

TEAM_GOAL_MEAN = {"ARG": 1.3, "ESP": 1.3}
MESSI_GOAL_SHARE = 0.35
ESP_PENALTY_WIN_PROB = 0.5
ITAY_PRED_SPACE = "esp_wins"

ALL_SCORES = [(a, s) for a in range(MAX_GOALS + 1) for s in range(MAX_GOALS + 1)]


def sign(x):
    return (x > 0) - (x < 0)


def match_points(pred, actual):
    if pred == actual:
        return PTS_EXACT
    if sign(pred[0] - pred[1]) == sign(actual[0] - actual[1]):
        return PTS_DIRECTION
    return 0


def scorer_points(pick, messi_goals):
    if messi_goals >= 3:
        tops = {"MESSI"}
    elif messi_goals == 2:
        tops = {"MESSI", "MBAPPE"}
    else:
        tops = {"MBAPPE"}
    return PTS_SCORER if pick in tops else 0


def winner_points(pick, winner):
    return PTS_WINNER if pick == winner else 0


def poisson_dist(mean):
    weights = [mean ** k / math.factorial(k) for k in range(MAX_GOALS + 1)]
    total = sum(weights)
    return [w / total for w in weights]


def binomial_dist(n, p):
    return [math.comb(n, k) * (p ** k) * ((1 - p) ** (n - k)) for k in range(n + 1)]


def build_scenarios():
    arg_dist = poisson_dist(TEAM_GOAL_MEAN["ARG"])
    esp_dist = poisson_dist(TEAM_GOAL_MEAN["ESP"])
    scenarios = []
    for a, s in ALL_SCORES:
        p_score = arg_dist[a] * esp_dist[s]
        if a > s:
            pens = [("ARG", 1.0)]
        elif s > a:
            pens = [("ESP", 1.0)]
        else:
            pens = [("ESP", ESP_PENALTY_WIN_PROB), ("ARG", 1.0 - ESP_PENALTY_WIN_PROB)]
        messi_dist = binomial_dist(a, MESSI_GOAL_SHARE)
        for winner, p_pen in pens:
            for m, p_m in enumerate(messi_dist):
                p = p_score * p_pen * p_m
                if p > 0:
                    scenarios.append(((a, s), winner, m, p))
    return scenarios


def pred_distribution(space):
    arg_dist = poisson_dist(TEAM_GOAL_MEAN["ARG"])
    esp_dist = poisson_dist(TEAM_GOAL_MEAN["ESP"])
    if space == "esp_wins":
        preds = [(pa, ps) for pa, ps in ALL_SCORES if ps > pa]
    else:
        preds = list(ALL_SCORES)
    weights = [arg_dist[pa] * esp_dist[ps] for pa, ps in preds]
    total = sum(weights)
    return [(pred, w / total) for pred, w in zip(preds, weights)]


def match_points_distribution(pred_dist):
    table = {}
    for actual in ALL_SCORES:
        dist = {0: 0.0, PTS_DIRECTION: 0.0, PTS_EXACT: 0.0}
        for pred, w in pred_dist:
            dist[match_points(pred, actual)] += w
        table[actual] = dist
    return table


def omer_total(cand, actual, winner, messi_goals):
    return (CURRENT_POINTS["omer"] + match_points(cand, actual)
            + winner_points("ESP", winner) + scorer_points("MBAPPE", messi_goals))


def itay_extra(winner, messi_goals):
    return winner_points("ESP", winner) + scorer_points("MBAPPE", messi_goals)


def compare_vs_dist(omer, rival_base, mp_dist):
    below = eq = 0.0
    for mp, w in mp_dist.items():
        total = rival_base + mp
        if total < omer:
            below += w
        elif total == omer:
            eq += w
    return below, eq


def evaluate_probabilities():
    scenarios = build_scenarios()
    shahar_mp = match_points_distribution(pred_distribution("any"))
    itay_mp = match_points_distribution(pred_distribution(ITAY_PRED_SPACE))
    results = []
    for cand in ALL_SCORES:
        p_strict = 0.0
        p_with_tie = 0.0
        for actual, winner, m, p in scenarios:
            omer = omer_total(cand, actual, winner, m)
            sh_below, sh_eq = compare_vs_dist(omer, CURRENT_POINTS["shahar"], shahar_mp[actual])
            it_base = CURRENT_POINTS["itay"] + itay_extra(winner, m)
            it_below, it_eq = compare_vs_dist(omer, it_base, itay_mp[actual])
            p_strict += p * sh_below * it_below
            p_with_tie += p * (sh_below + sh_eq) * (it_below + it_eq)
        results.append((cand, p_strict, p_with_tie))
    results.sort(key=lambda r: (-r[1], -r[2]))
    return results


def family_of(actual, winner, messi_goals):
    a, s = actual
    if s > a:
        result = "ESP wins 120'"
    elif a > s:
        result = "ARG wins 120'"
    elif winner == "ESP":
        result = "Draw, ESP pens"
    else:
        result = "Draw, ARG pens"
    if messi_goals >= 3:
        messi = "Messi 3+"
    elif messi_goals == 2:
        messi = "Messi 2"
    else:
        messi = "Messi 0-1"
    return result, messi


def space_preds(space):
    if space == "esp_wins":
        return [(pa, ps) for pa, ps in ALL_SCORES if ps > pa]
    return list(ALL_SCORES)


def max_match_points(space, actual):
    return max(match_points(pred, actual) for pred in space_preds(space))


def worst_case_by_family(cand):
    scenarios = build_scenarios()
    families = {}
    for actual, winner, m, _ in scenarios:
        key = family_of(actual, winner, m)
        omer = omer_total(cand, actual, winner, m)
        sh_max = CURRENT_POINTS["shahar"] + max_match_points("any", actual)
        it_max = (CURRENT_POINTS["itay"] + max_match_points(ITAY_PRED_SPACE, actual)
                  + itay_extra(winner, m))
        diff_sh = omer - sh_max
        diff_it = omer - it_max
        prev = families.get(key)
        if prev is None:
            families[key] = [diff_sh, diff_it]
        else:
            prev[0] = min(prev[0], diff_sh)
            prev[1] = min(prev[1], diff_it)
    return families


def status_label(diff):
    if diff > 0:
        return "WIN"
    if diff == 0:
        return "TIEBREAK"
    return f"RISK({diff})"


def print_family_table(cand):
    print(f"\nWorst-case analysis for prediction ARG {cand[0]} - {cand[1]} ESP")
    print(f"{'scenario family':<22}{'vs Shahar':<14}{'vs Itay':<14}")
    families = worst_case_by_family(cand)
    order = ["ESP wins 120'", "Draw, ESP pens", "Draw, ARG pens", "ARG wins 120'"]
    messi_order = ["Messi 0-1", "Messi 2", "Messi 3+"]
    for result in order:
        for messi in messi_order:
            key = (result, messi)
            if key in families:
                diff_sh, diff_it = families[key]
                label = f"{result} / {messi}"
                print(f"{label:<32}{status_label(diff_sh):<14}{status_label(diff_it):<14}")


def main():
    print("Assumptions: Mbappe frozen +2 over Messi, Kane frozen below Mbappe,")
    print("exact = 15 total, winner decided after pens, match score after 120'.")
    print(f"Goal model: Poisson mean {TEAM_GOAL_MEAN}, Messi share {MESSI_GOAL_SHARE},")
    print(f"Itay hidden pred space: {ITAY_PRED_SPACE}, Shahar hidden pred space: any.")

    results = evaluate_probabilities()
    print("\nRanking of Omer's candidate final-score predictions")
    print(f"{'pred (ARG-ESP)':<16}{'P(strictly 2nd)':<18}{'P(2nd incl. ties)':<18}")
    for cand, p_strict, p_tie in results[:10]:
        label = f"{cand[0]}-{cand[1]}"
        print(f"{label:<16}{p_strict:<18.4f}{p_tie:<18.4f}")
    current = next(r for r in results if r[0] == CURRENT_OMER_PRED)
    rank = results.index(current) + 1
    print(f"\nCurrent prediction {CURRENT_OMER_PRED[0]}-{CURRENT_OMER_PRED[1]}: "
          f"rank {rank}/36, P(strictly 2nd)={current[1]:.4f}, incl. ties={current[2]:.4f}")

    print_family_table(CURRENT_OMER_PRED)
    best = results[0][0]
    if best != CURRENT_OMER_PRED:
        print_family_table(best)


if __name__ == "__main__":
    main()
