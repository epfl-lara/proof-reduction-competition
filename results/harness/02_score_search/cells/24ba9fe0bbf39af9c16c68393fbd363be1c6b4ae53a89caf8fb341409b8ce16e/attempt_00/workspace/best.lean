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
  have ln := InitStatesLength hi
  have lu := UpdateStatesLength hu
  have hn := InitStatesNotDefined hi
  refine ⟨_, rfl, updatedStatesInit ln (UpdateStatesNotDefMonotone' hn hu) (InitStatesNodup hi), ?_⟩
  rw [InitStatesUpdated hi, UpdateStatesUpdated hu]
  unfold updatedStates
  rw [updatedStatesComm]
  · exact updatedStatesUpdate lu (updatedStatesDefMonotone (UpdateStatesDefined' hu))
  · rw [List.unzip_zip lu, List.unzip_zip ln]
    intro k hk hk'
    have hd := UpdateStatesDefined hu k hk
    rw [hn k hk'] at hd
    contradiction
