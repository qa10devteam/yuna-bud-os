% A003: cena rynkowa — placeholder (full SEKOCENBUD lookup in config)
% In offline mode: no violation emitted (requires external price table)
% violation fires only if explicitly asserted
violation("A003", "warn",
  "Cena jednostkowa kosztorysu wymaga weryfikacji z cennikiem SEKOCENBUD",
  "cena_rynkowa") :- cena_rynkowa_flag(1).
