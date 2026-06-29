% A004: pzp_abnormal_low — estimate ≤ 70% of buyer's estimate (grosze arithmetic)
violation("A004", "warn",
  "Oferta ponizej 70% wartosci szacunkowej zamawiajacego: ryzyko razaco niskiej ceny (art. 224 PZP)",
  "abnormal_low_price") :-
    estimate_total(E), E > 0,
    buyer_estimate(B), B > 0,
    100 * E < 70 * B.
