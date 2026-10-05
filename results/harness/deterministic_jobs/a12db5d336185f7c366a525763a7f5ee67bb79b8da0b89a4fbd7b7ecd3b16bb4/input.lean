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
  have hn := InitStatesNotDefined hi
  have hl := UpdateStatesLength hu
  have hl' := InitStatesLength hi
  refine ⟨_, rfl, updatedStatesInit hl'
    (UpdateStatesNotDefMonotone' hn hu) (InitStatesNodup hi), ?_⟩
  have hd : ks.Disjoint ks' := by
    intro k hk hk'
    have h := UpdateStatesDefined hu k hk
    simp [isNotDefined] at hn
    simp [hn k hk'] at h
  rw [InitStatesUpdated hi, UpdateStatesUpdated hu]
  unfold updatedStates
  rw [updatedStatesComm]
  · exact updatedStatesUpdate hl (updatedStatesDefMonotone (UpdateStatesDefined' hu))
  · simpa only [List.unzip_zip hl, List.unzip_zip hl'] using hd