open OldExpressions in
theorem extractedOldExprInVars :
  NormalizedOldExpr post →
  (extractOldExprVars post).Subset
  (Imperative.HasVarsPure.getVars post) := by
  have app {a b c d : List Expression.Ident} (ha : a.Subset c) (hb : b.Subset d) :
      (a ++ b).Subset (c ++ d) :=
    List.Subset.app (fun _ h => List.mem_append_left _ (ha h))
      (fun _ h => List.mem_append_right _ (hb h))
  intro h
  clear h
  induction post <;>
    simp only [Imperative.HasVarsPure.getVars, extractOldExprVars,
      Lambda.LExpr.LExpr.getVars] at *
  all_goals try (solve | assumption | exact List.Subset.empty | apply app <;> first | assumption | apply app <;> assumption)
  case app fn e ihfn ihe =>
    unfold extractOldExprVars
    split
    · simp only [Lambda.LExpr.LExpr.getVars, List.nil_append]
      exact fun _ h => h
    · exact List.Subset.empty
    · exact app ihfn ihe
