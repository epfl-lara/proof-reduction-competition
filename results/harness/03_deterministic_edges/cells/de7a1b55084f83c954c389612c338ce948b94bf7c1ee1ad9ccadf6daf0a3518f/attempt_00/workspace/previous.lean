open OldExpressions in
theorem extractedOldExprInVars :
  NormalizedOldExpr post →
  (extractOldExprVars post).Subset
  (Imperative.HasVarsPure.getVars post) := by
  have app {a b c d : List Expression.Ident} (h : a.Subset c) (k : b.Subset d) :
      (a ++ b).Subset (c ++ d) :=
    List.Subset.app (List.subset_append_of_subset_left _ h)
      (List.subset_append_of_subset_right _ k)
  intro h
  induction h <;>
    simp only [Imperative.HasVarsPure.getVars, extractOldExprVars,
      Lambda.LExpr.LExpr.getVars]
  all_goals try exact List.nil_subset _
  all_goals try assumption
  all_goals try exact app ‹_› ‹_›
  all_goals try exact app (app ‹_› ‹_›) ‹_›
  unfold extractOldExprVars
  split
  · exact fun _ hx => hx
  · next bad =>
      have hf := ‹IsOldPred _ → IsFvar _› (by constructor)
      cases hf
      exfalso
      apply bad
      rfl
  · exact app ‹_› ‹_›
