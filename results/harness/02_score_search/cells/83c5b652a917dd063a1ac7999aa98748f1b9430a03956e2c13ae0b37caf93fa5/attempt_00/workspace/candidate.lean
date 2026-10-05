open OldExpressions in
theorem extractedOldExprInVars :
  NormalizedOldExpr post →
  (extractOldExprVars post).Subset
  (Imperative.HasVarsPure.getVars post) := by
  change _ → (extractOldExprVars post).Subset (Lambda.LExpr.LExpr.getVars post)
  have appMono {a b c d : List CoreIdent}
      (h₁ : a.Subset b) (h₂ : c.Subset d) : (a ++ c).Subset (b ++ d) :=
    List.Subset.app
      (List.Subset.subset_app_of_or_2 (Or.inl h₁))
      (List.Subset.subset_app_of_or_2 (Or.inr h₂))
  intro h
  induction h with
  | const | op | bvar | fvar => simp [extractOldExprVars, Lambda.LExpr.LExpr.getVars]
  | abs _ ih => exact ih
  | quant _ _ ih₁ ih₂ => exact appMono ih₁ ih₂
  | app _ _ hn ih₁ ih₂ =>
    unfold extractOldExprVars
    split
    · exact List.Subset.refl
    · next hf =>
      cases hn (by constructor)
      exact False.elim (hf _ _ _ rfl)
    · exact appMono ih₁ ih₂
  | ite _ _ _ ih₁ ih₂ ih₃ => exact appMono (appMono ih₁ ih₂) ih₃
  | eq _ _ ih₁ ih₂ => exact appMono ih₁ ih₂
