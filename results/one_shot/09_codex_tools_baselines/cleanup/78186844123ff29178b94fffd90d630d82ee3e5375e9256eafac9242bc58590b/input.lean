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
  have hm := UpdateStatesLength hu
  have hn := InitStatesNotDefined hi
  refine ⟨_, rfl, updatedStatesInit hl
    (UpdateStatesNotDefMonotone' hn hu) (InitStatesNodup hi), ?_⟩
  rw [InitStatesUpdated hi, UpdateStatesUpdated hu]
  unfold updatedStates
  rw [updatedStatesComm]
  · exact updatedStatesUpdate hm
      (updatedStatesDefMonotone (UpdateStatesDefined' hu))
  · simp only [List.unzip_zip, hm, hl]
    intro k hk hk'
    simpa [hn k hk'] using (UpdateStatesDefined hu k hk)