theorem InitsUpdatesComm
  {P : PureExpr} {σ σ' σ'' : SemanticStore P}
  {ks ks' : List P.Ident} {vs vs' : List P.Expr} :
  UpdateStates σ ks vs σ' →
  InitStates σ' ks' vs' σ'' →
  ∃ σ₁,
    σ₁ = (updatedStates σ ks' vs') ∧
    InitStates σ ks' vs' σ₁ ∧
    UpdateStates σ₁ ks vs σ'' := fun hu hi =>
  let hl := UpdateStatesLength hu
  let := InitStatesLength hi
  ⟨_, rfl, updatedStatesInit this
    (UpdateStatesNotDefMonotone' (InitStatesNotDefined hi) hu) (InitStatesNodup hi), by
    cases UpdateStatesUpdated hu ▸ InitStatesUpdated hi
    unfold updatedStates
    rewrite [updatedStatesComm]
    exact updatedStatesUpdate hl
        (updatedStatesDefMonotone (UpdateStatesDefined' hu))
    simp_all [List.unzip_zip]
    intro k hk hk'
    cases InitStatesNotDefined hi k hk' ▸ UpdateStatesDefined hu k hk
  ⟩