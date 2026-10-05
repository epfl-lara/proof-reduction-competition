theorem InitsUpdatesComm
  {P : PureExpr} {σ σ' σ'' : SemanticStore P}
  {ks ks' : List P.Ident} {vs vs' : List P.Expr} :
  UpdateStates σ ks vs σ' →
  InitStates σ' ks' vs' σ'' →
  ∃ σ₁,
    σ₁ = (updatedStates σ ks' vs') ∧
    InitStates σ ks' vs' σ₁ ∧
    UpdateStates σ₁ ks vs σ'' := by
  intro hu hi
  have hl := InitStatesLength hi
  have hd := InitStatesNotDefined hi
  refine ⟨_, rfl, updatedStatesInit hl (UpdateStatesNotDefMonotone' hd hu)
    (InitStatesNodup hi), ?_⟩
  simp [InitStatesUpdated hi, UpdateStatesUpdated hu, updatedStates]
  refine updatedStatesComm ?_ ▸ updatedStatesUpdate (UpdateStatesLength hu)
    (updatedStatesDefMonotone (UpdateStatesDefined' hu))
  simp [List.unzip_zip, UpdateStatesLength hu, hl]
  intro k hk' hk
  cases hd k hk' ▸ UpdateStatesDefined hu k hk
