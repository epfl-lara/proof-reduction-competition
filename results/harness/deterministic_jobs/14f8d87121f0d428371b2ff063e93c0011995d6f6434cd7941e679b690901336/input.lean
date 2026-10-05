open OldExpressions in
theorem extractedOldExprInVars :
  NormalizedOldExpr post →
  (extractOldExprVars post).Subset
  (Imperative.HasVarsPure.getVars post) := by
  have app {a b c d : List Expression.Ident}
      (h : a.Subset c) (k : b.Subset d) : (a ++ b).Subset (c ++ d) := by
    intro x hx
    cases List.mem_append.mp hx with
    | inl hx => exact List.mem_append_left _ (h hx)
    | inr hx => exact List.mem_append_right _ (k hx)
  intro h
  induction h <;>
    simp only [Imperative.HasVarsPure.getVars, extractOldExprVars,
      Lambda.LExpr.LExpr.getVars] at *
  all_goals try solve | exact List.Subset.empty | assumption | apply app <;> assumption | apply app <;> first | assumption | apply app <;> assumption
  case app hn he hnold ih₁ ih₂ =>
    unfold extractOldExprVars
    split
    · simp [Lambda.LExpr.LExpr.getVars]; exact fun _ h => h
    · next hf =>
      cases hnold .oldPred
      exfalso; apply hf; rfl
    · exact app ih₁ ih₂