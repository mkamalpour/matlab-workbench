function run_shared_fixtures(directory)
% Execute when MATLAB is available; Python generation is not MATLAB validation.
if nargin==0,directory=fullfile(fileparts(fileparts(mfilename('fullpath'))),'fixtures');end
s=jsondecode(fileread(fullfile(directory,'shared.json')));
r=outlier_detection(s.outliers.values);
fields={'q1','q3','iqr','lower','upper'};
for j=1:numel(fields),k=fields{j};assert(abs(r.(k)-s.outliers.expected.(k))<1e-10,['Outlier ' k]);end
expected=s.outliers.expected.rows;
assert(isequal(r.row_index(:),[expected.row_index]'),'Outlier original indices');
assert(isequal(r.values(:),[expected.value]'),'Outlier values');
[state,~]=transport_system();commands=s.transport.commands;
for j=1:numel(commands),[state,~]=transport_system(state,commands{j});end
expected=validate_transport_state(s.transport.expected);
assert(state.next_order_id==expected.next_order_id,'Next order ID');
for field={'drivers','active','completed'}
 name=field{1};actual=state.(name);want=expected.(name);
 assert(numel(actual)==numel(want),['Count ' name]);
 for j=1:numel(actual)
  keys=fieldnames(want(j));
  for h=1:numel(keys)
   key=keys{h};a1=actual(j).(key);a2=want(j).(key);
   if isnumeric(a1),assert(isequal(a1(:),a2(:)),['Transport ' key]);else,assert(strcmp(a1,a2),['Transport ' key]);end
  end
 end
end
a=load(fullfile(directory,'audio.mat'));options=struct('taps',4,'plots',false);
r=AudioNoiseCancellation(a.noisy,a.reference,a.fs,a.clean,options);
for k={'LMS','NLMS','RLS'}
 name=k{1};target=a.(['cleaned_' name]);assert(max(abs(r.(name).cleaned(:)-target(:)))<1e-8,['Audio ' name]);
 target=a.(['weights_' name]);assert(max(abs(r.(name).weights(:)-target(:)))<1e-8,['Weights ' name]);
end
r=mpg_prediction(readtable(fullfile(directory,'mpg.csv')),s.mpg.train_indices);
assert(max(abs(r.predicted(:)-s.mpg.expected_predictions(:)))<1e-7,'MPG predictions');
assert(isequal(r.test_indices(:),s.mpg.expected_test_indices(:)),'MPG test rows');
fprintf('Shared fixtures passed in MATLAB.\n');
end


