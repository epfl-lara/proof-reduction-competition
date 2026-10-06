open OldExpressions in
theorem extractedOldExprInVars :
  NormalizedOldExpr post →
  (extractOldExprVars post).Subset
  (Imperative.HasVarsPure.getVars post) := by
  have sapp {a b c d : List CoreIdent} (h1 : a.Subset c) (h2 : b.Subset d) :=
    List.Subset.app (List.subset_append_of_subset_left _ h1) (List.subset_append_of_subset_right _ h2)
  intro Hnorm
  induction Hnorm <;> try exact List.Subset.empty
  case abs => assumption
  case quant a b | eq a b => exact sapp a b
  case ite cih tih eih => exact sapp (sapp cih tih) eih
  case app Hn fn_ih e_ih =>
    unfold extractOldExprVars
    split
    · apply List.subset_append_right
    · exfalso
      cases Hn ⟨⟩
      apply ‹_›
      rfl
    exact sapp fn_ih e_ih