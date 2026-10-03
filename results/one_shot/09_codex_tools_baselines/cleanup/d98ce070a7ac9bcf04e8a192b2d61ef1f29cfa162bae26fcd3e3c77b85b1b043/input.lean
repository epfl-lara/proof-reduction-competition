open OldExpressions in
theorem extractedOldExprInVars :
  NormalizedOldExpr post →
  (extractOldExprVars post).Subset
  (Imperative.HasVarsPure.getVars post) := by
  have happ {α : Type} {a b c d : List α} (ha : a.Subset c) (hb : b.Subset d) :
      (a ++ b).Subset (c ++ d) := by
    intro x hx
    simp only [List.mem_append] at hx ⊢
    rcases hx with hx | hx
    · exact Or.inl (ha hx)
    · exact Or.inr (hb hx)
  intro h
  induction h <;> simp_all [Imperative.HasVarsPure.getVars, extractOldExprVars, Lambda.LExpr.LExpr.getVars]
  case app =>
    unfold extractOldExprVars
    split
    · intro x hx
      exact hx
    · next Hfalse =>
      exfalso
      have hf := (show IsOldPred _ → IsFvar _ from by assumption) IsOldPred.oldPred
      cases hf
      apply Hfalse
      rfl
    · exact happ (by assumption) (by assumption)