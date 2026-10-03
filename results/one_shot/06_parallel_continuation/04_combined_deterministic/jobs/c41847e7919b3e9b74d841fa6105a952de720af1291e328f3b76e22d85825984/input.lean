open OldExpressions in
theorem extractedOldExprInVars :
  NormalizedOldExpr post →
  (extractOldExprVars post).Subset
  (Imperative.HasVarsPure.getVars post) := by
  intros Hnorm
  induction post <;>
    simp [Imperative.HasVarsPure.getVars, extractOldExprVars,
          Lambda.LExpr.LExpr.getVars] at * <;>
    try simp_all
  case app fn e fn_ih e_ih =>
    unfold extractOldExprVars
    split
    . simp [Lambda.LExpr.LExpr.getVars]
      intros x Hin
      omega
    . next Hfalse =>
      cases Hnorm with
      | app H1 H2 Hn =>
      exfalso
      specialize Hn ?_
      constructor
      cases Hn
      apply Hfalse
      rfl
    . cases Hnorm with
      | app H1 H2 Hn =>
      exact List.Subset.app
        (List.Subset.trans (fn_ih H1) (fun x Hin => List.mem_append_left _ Hin))
        (List.Subset.trans (e_ih H2) (fun x Hin => List.mem_append_right _ Hin))
  case abs ih =>
    cases Hnorm
    exact ih (by assumption)
  case quant trih eih =>
    cases Hnorm
    exact List.Subset.app
      (List.Subset.trans (trih (by assumption)) (fun x Hin => List.mem_append_left _ Hin))
      (List.Subset.trans (eih (by assumption)) (fun x Hin => List.mem_append_right _ Hin))
  case ite cih tih eih =>
    cases Hnorm
    exact List.Subset.app
      (List.Subset.trans (cih (by assumption)) (fun x Hin => List.mem_append_left _ Hin))
      (List.Subset.app
        (List.Subset.trans (tih (by assumption)) (fun x Hin => List.mem_append_right _ (List.mem_append_left _ Hin)))
        (List.Subset.trans (eih (by assumption)) (fun x Hin => List.mem_append_right _ (List.mem_append_right _ Hin))))
  case eq ih1 ih2 =>
    cases Hnorm
    exact List.Subset.app
      (List.Subset.trans (ih1 (by assumption)) (fun x Hin => List.mem_append_left _ Hin))
      (List.Subset.trans (ih2 (by assumption)) (fun x Hin => List.mem_append_right _ Hin))