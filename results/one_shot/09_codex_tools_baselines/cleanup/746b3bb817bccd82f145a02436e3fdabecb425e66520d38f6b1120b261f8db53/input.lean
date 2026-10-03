open OldExpressions in
theorem substOldPostSubset:
  (Imperative.HasVarsPure.getVars (P:=Expression)
    (substOld h2 (Lambda.LExpr.fvar m h1 ty) post)).Subset
    (Imperative.HasVarsPure.getVars (P:=Expression) post ++ [h1]) := by
  have join {a b c d : List Expression.Ident}
      (ha : a ⊆ c ++ [h1]) (hb : b ⊆ d ++ [h1]) :
      a ++ b ⊆ (c ++ d) ++ [h1] := by
    intro x hx
    simp only [List.mem_append] at hx ⊢
    exact hx.elim
      (fun hx => (List.mem_append.mp (ha hx)).imp Or.inl id)
      (fun hx => (List.mem_append.mp (hb hx)).imp Or.inr id)
  induction post <;> simp only [substOld]
  case const | bvar | fvar | op =>
    exact fun _ hx => List.mem_append_left _ hx
  case abs ih => exact ih
  case quant ih1 ih2 => exact join ih1 ih2
  case eq ih1 ih2 => exact join ih1 ih2
  case ite ih1 ih2 ih3 => exact join (join ih1 ih2) ih3
  case app ih1 ih2 =>
    split
    · split
      · exact fun _ hx => List.mem_append_right _ hx
      · exact fun _ hx => List.mem_append_left _ hx
    · exact join ih1 ih2