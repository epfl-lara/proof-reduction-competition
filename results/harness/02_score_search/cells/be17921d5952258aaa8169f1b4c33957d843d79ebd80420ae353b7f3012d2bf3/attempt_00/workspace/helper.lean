open OldExpressions in
theorem extractedOldExprInVars :
  NormalizedOldExpr post →
  (extractOldExprVars post).Subset
  (Imperative.HasVarsPure.getVars post) := by
  have app {a b c d : List Expression.Ident}
      (h : a.Subset c) (k : b.Subset d) : (a ++ b).Subset (c ++ d) :=
    fun _ hx => (List.mem_append.mp hx).elim
      (fun hx => List.mem_append_left _ (h hx))
      (fun hx => List.mem_append_right _ (k hx))
  intro h
  induction h <;>
    simp only [Imperative.HasVarsPure.getVars, extractOldExprVars,
      Lambda.LExpr.LExpr.getVars] at *
  all_goals try exact List.nil_subset _
  all_goals try assumption
  all_goals try exact app ‹_› ‹_›
  all_goals try exact app (app ‹_› ‹_›) ‹_›
  rename_i hn ih₁ ih₂
  unfold extractOldExprVars
  split
  · exact fun _ hx => hx
  · next hf =>
    cases hn .oldPred
    exact False.elim (hf _ _ _ rfl)
  · exact app ih₁ ih₂
