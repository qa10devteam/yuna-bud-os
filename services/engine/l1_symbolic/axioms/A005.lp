% A005: suma_zgodnosc — sum of lines vs total_net_pln (1% tolerance, grosze)
violation("A005", "block",
  "Niezgodnosc sumy pozycji z wartoscia tytulowa kosztorysu (odchylenie >1%)",
  "sum_mismatch") :-
    estimate_total(T), T > 0,
    estimate_lines_sum(S), S > 0,
    D = T - S, D > 0,
    100 * D > 1 * T.

violation("A005", "block",
  "Niezgodnosc sumy pozycji z wartoscia tytulowa kosztorysu (odchylenie >1%)",
  "sum_mismatch") :-
    estimate_total(T), T > 0,
    estimate_lines_sum(S), S > 0,
    D = S - T, D > 0,
    100 * D > 1 * T.
