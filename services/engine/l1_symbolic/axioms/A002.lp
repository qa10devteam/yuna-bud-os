% A002: odwodnienie — wykop >150cm AND teren mokry → wymagana pozycja odwodnienia
% excavation_depth_cm > 150 means depth > 1.5m
violation("A002", "block",
  "Brak pozycji odwodnienia: wykop gleboki (>1.5m) na terenie mokrym",
  "brak_odwodnienia") :-
    excavation_depth_cm(D), D > 150,
    teren_mokry(1),
    has_odwodnienie(0).
