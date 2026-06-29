% A001: masa_bilans — masa wykopu ≈ masa nasypu ± 15%
% Only fires when both sides are >0 (earthworks present)
violation("A001", "block",
  "Bilans mas niezgodny: masa wykopu i nasypu roznia sie o ponad 15%",
  "mass_balance") :-
    mass_wykop(W), mass_nasyp(N),
    W > 0, N > 0,
    D = W - N, D >= 0,
    100 * D > 15 * W.

violation("A001", "block",
  "Bilans mas niezgodny: masa wykopu i nasypu roznia sie o ponad 15%",
  "mass_balance") :-
    mass_wykop(W), mass_nasyp(N),
    W > 0, N > 0,
    D = N - W, D > 0,
    100 * D > 15 * W.
