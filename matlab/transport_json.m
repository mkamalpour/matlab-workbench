function text=transport_json(state)
% Canonical snapshot arrays even when MATLAB has zero or one struct element.
state=validate_transport_state(state);
for key={'drivers','active','completed'}
 name=key{1};state.(name)=num2cell(state.(name));
end
text=jsonencode(state);
end
