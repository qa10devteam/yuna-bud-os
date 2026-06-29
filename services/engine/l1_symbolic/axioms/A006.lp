% A006: cpv_zgodnosc — fires only if cpv_mismatch(1) asserted by facts builder
violation("A006", "warn",
  "Niezgodnosc CPV ogloszenia z zakresem robot w STWiOR",
  "cpv_mismatch") :- cpv_mismatch(1).
