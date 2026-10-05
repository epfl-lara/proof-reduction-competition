open OldExpressions in
theorem extractedOldExprInVars :
  NormalizedOldExpr post →
  (extractOldExprVars post).Subset
  (Imperative.HasVarsPure.getVars post) := by
  intro h
  induction h <;>
    simp only [Imperative.HasVarsPure.getVars, extractOldExprVars,
      Lambda.LExpr.LExpr.getVars] at *
  all_goals try solve | exact List.Subset.empty | assumption
  case app hn he hnold ih₁ ih₂ =>
    unfold extractOldExprVars
    split
    · simp [Lambda.LExpr.LExpr.getVars]; exact fun _ h => h
    · next hf =>
      cases hnold .oldPred
      exfalso; apply hf; rfl
    · grind [List.Subset]
  all_goals grind [List.Subset]