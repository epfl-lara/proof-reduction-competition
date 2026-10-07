open OldExpressions in
theorem extractedOldExprInVars :
  NormalizedOldExpr post →
  (extractOldExprVars post).Subset
  (Imperative.HasVarsPure.getVars post) := by
  intro H
  refine List.Sublist.subset ?_
  induction H
  case app i₁ i₂ =>
    unfold extractOldExprVars
    split
    · exact List.Sublist.refl _
    · exact List.nil_sublist _
    · exact i₁.append i₂
  any_goals exact List.nil_sublist _
  any_goals assumption
  all_goals refine List.Sublist.append ?_ ?_ <;> first | assumption | refine List.Sublist.append ?_ ?_ <;> assumption