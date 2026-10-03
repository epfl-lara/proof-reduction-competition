open OldExpressions in
theorem extractedOldExprInVars :
  NormalizedOldExpr post →
  (extractOldExprVars post).Subset
  (Imperative.HasVarsPure.getVars post) := by
  intro h
  induction post <;>
    simp [Imperative.HasVarsPure.getVars, extractOldExprVars,
      Lambda.LExpr.LExpr.getVars] at * <;> try simp_all
  case app fn e ihf ihe =>
    unfold extractOldExprVars
    split
    · simp [Lambda.LExpr.LExpr.getVars]
      intro x hx
      exact hx
    · next hfalse =>
      cases h with
      | app _ _ hn =>
        exfalso
        specialize hn ?_
        constructor
        cases hn
        apply hfalse
        rfl
    · cases h with
      | app hf he _ =>
        apply List.Subset.app
        · exact List.Subset.trans (ihf hf) (by intro x hx; simp_all)
        · exact List.Subset.trans (ihe he) (by intro x hx; simp_all)
  case abs ih =>
    cases h
    exact ih ‹_›
  case quant ihT ihE =>
    cases h
    apply List.Subset.app
    · exact List.Subset.trans (ihT ‹_›) (by intro x hx; simp_all)
    · exact List.Subset.trans (ihE ‹_›) (by intro x hx; simp_all)
  case ite ihc iht ihe =>
    cases h
    apply List.Subset.app
    · exact List.Subset.trans (ihc ‹_›) (by intro x hx; simp_all)
    · apply List.Subset.app
      · exact List.Subset.trans (iht ‹_›) (by intro x hx; simp_all)
      · exact List.Subset.trans (ihe ‹_›) (by intro x hx; simp_all)
  case eq ih1 ih2 =>
    cases h
    apply List.Subset.app
    · exact List.Subset.trans (ih1 ‹_›) (by intro x hx; simp_all)
    · exact List.Subset.trans (ih2 ‹_›) (by intro x hx; simp_all)
