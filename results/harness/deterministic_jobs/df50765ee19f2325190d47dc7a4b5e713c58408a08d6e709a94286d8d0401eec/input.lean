open OldExpressions in
theorem extractedOldExprInVars :
  NormalizedOldExpr post →
  (extractOldExprVars post).Subset
  (Imperative.HasVarsPure.getVars post) := by
  intro h
  have append_mono {α} {a b c d : List α}
      (ha : a ⊆ c) (hb : b ⊆ d) : (a ++ b) ⊆ (c ++ d) :=
    List.append_subset.mpr ⟨List.subset_append_of_subset_left d ha,
      List.subset_append_of_subset_right c hb⟩
  induction h with
  | const | op | bvar | fvar =>
      simp [extractOldExprVars, Imperative.HasVarsPure.getVars,
        Lambda.LExpr.LExpr.getVars]
  | abs hn ih => exact ih
  | quant htr he ihtr ihe =>
      simpa only [extractOldExprVars, Imperative.HasVarsPure.getVars] using append_mono ihtr ihe
  | app hfn he valid ihfn ihe =>
      unfold extractOldExprVars
      split
      · simp [Imperative.HasVarsPure.getVars, Lambda.LExpr.LExpr.getVars,
          List.Subset]
      · next Hfalse =>
        exfalso
        cases valid (by constructor)
        apply Hfalse
        rfl
      · simpa only [Imperative.HasVarsPure.getVars]
          using append_mono ihfn ihe
  | ite hc ht he ihc iht ihe =>
      simpa only [extractOldExprVars, Imperative.HasVarsPure.getVars,
        Lambda.LExpr.LExpr.getVars, List.append_assoc] using append_mono ihc (append_mono iht ihe)
  | eq h1 h2 ih1 ih2 =>
      simpa only [extractOldExprVars, Imperative.HasVarsPure.getVars] using append_mono ih1 ih2