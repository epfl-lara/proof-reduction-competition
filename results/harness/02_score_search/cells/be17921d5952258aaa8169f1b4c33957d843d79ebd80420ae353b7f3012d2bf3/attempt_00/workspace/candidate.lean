open OldExpressions in
theorem extractedOldExprInVars :
  NormalizedOldExpr post →
  (extractOldExprVars post).Subset
  (Imperative.HasVarsPure.getVars post) := by
  have app {a b c d : List Expression.Ident}
      (h : a.Subset c) (k : b.Subset d) : (a ++ b).Subset (c ++ d) :=
    List.Subset.app (List.subset_append_of_subset_left _ h)
      (List.subset_append_of_subset_right _ k)
  intro h
  induction h
  all_goals first
    | exact List.nil_subset _
    | assumption
    | exact app ‹_› ‹_›
    | exact app (app ‹_› ‹_›) ‹_›
    | skip
  rename_i hn ih₁ ih₂
  unfold extractOldExprVars
  split
  · exact fun _ hx => hx
  · next hf =>
    cases hn .oldPred
    exact False.elim (hf _ _ _ rfl)
  · exact app ih₁ ih₂
