open OldExpressions in
theorem extractedOldExprInVars :
  NormalizedOldExpr post →
  (extractOldExprVars post).Subset
  (Imperative.HasVarsPure.getVars post) := by
  intro h
  have append_mono {α : Type} {a b c d : List α}
      (ha : a.Subset c) (hb : b.Subset d) :
      (a ++ b).Subset (c ++ d) := by
    intro x hx
    simp only [List.mem_append] at hx ⊢
    rcases hx with hx | hx
    · exact Or.inl (ha hx)
    · exact Or.inr (hb hx)
  induction h with
  | const => simp [extractOldExprVars, Imperative.HasVarsPure.getVars,
      Lambda.LExpr.LExpr.getVars]
  | op => simp [extractOldExprVars, Imperative.HasVarsPure.getVars,
      Lambda.LExpr.LExpr.getVars]
  | bvar => simp [extractOldExprVars, Imperative.HasVarsPure.getVars,
      Lambda.LExpr.LExpr.getVars]
  | fvar => simp [extractOldExprVars, Imperative.HasVarsPure.getVars,
      Lambda.LExpr.LExpr.getVars]
  | abs hn ih => simpa [extractOldExprVars, Imperative.HasVarsPure.getVars,
      Lambda.LExpr.LExpr.getVars] using ih
  | quant htr he ihtr ihe =>
      simpa [extractOldExprVars, Imperative.HasVarsPure.getVars,
        Lambda.LExpr.LExpr.getVars] using append_mono ihtr ihe
  | app hfn he valid ihfn ihe =>
      unfold extractOldExprVars
      split
      · simp [Imperative.HasVarsPure.getVars, Lambda.LExpr.LExpr.getVars]
        intro x hx
        exact hx
      · next Hfalse =>
        exfalso
        specialize valid ?_
        · constructor
        cases valid
        apply Hfalse
        rfl
      · simpa [Imperative.HasVarsPure.getVars, Lambda.LExpr.LExpr.getVars]
          using append_mono ihfn ihe
  | ite hc ht he ihc iht ihe =>
      simpa [extractOldExprVars, Imperative.HasVarsPure.getVars,
        Lambda.LExpr.LExpr.getVars] using append_mono ihc (append_mono iht ihe)
  | eq h1 h2 ih1 ih2 =>
      simpa [extractOldExprVars, Imperative.HasVarsPure.getVars,
        Lambda.LExpr.LExpr.getVars] using append_mono ih1 ih2