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
  have hl := UpdateStatesLength hu
  have hl' := InitStatesLength hi
  have hn := InitStatesNotDefined hi
  refine ⟨_, rfl,
    updatedStatesInit hl' (UpdateStatesNotDefMonotone' hn hu) (InitStatesNodup hi), ?_⟩
  rw [InitStatesUpdated hi, UpdateStatesUpdated hu]
  unfold updatedStates
  rw [updatedStatesComm]
  · exact updatedStatesUpdate hl (updatedStatesDefMonotone (UpdateStatesDefined' hu))
  · rw [List.unzip_zip hl, List.unzip_zip hl']
    intro k hk hk'
    exact Option.isSome_iff_ne_none.mp (UpdateStatesDefined hu k hk) (hn k hk')
