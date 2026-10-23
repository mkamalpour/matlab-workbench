function transport_cli(directory)
% Explicit private session directory; snapshots retain state across sessions.
assert(nargin==1&&isfolder(directory),'Supply an existing session directory');
path=fullfile(directory,'transport-state.json');[s,~]=transport_system();
if isfile(path)
 s=validate_transport_state(jsondecode(fileread(path)));
else
 assert(~any(cellfun(@(n)isfile(fullfile(directory,n)),{'driver.txt','new_order.txt','order.txt'})),'Legacy files exist without snapshot; choose a fresh directory');
end
while true
 command=input('transport> ','s');
 if strcmpi(strtrim(command),'Exit'),break;end
 try
  [candidate,msg]=transport_system(s,command);
  temp=[tempname(directory) '.json'];f=fopen(temp,'w');assert(f~=-1,'Cannot write snapshot');
  cleanup=onCleanup(@()fclose(f));fprintf(f,'%s',transport_json(candidate));clear cleanup;
  [ok,message]=movefile(temp,path,'f');assert(ok,message);s=candidate;disp(msg);
  exportText(s,directory);
 catch e,fprintf(2,'%s\n',e.message);end
end
end
function exportText(s,directory)
names={'driver.txt','new_order.txt','order.txt'};
for k=1:3
 temp=[tempname(directory) '.txt'];f=fopen(temp,'w');assert(f~=-1,'Cannot export');c=onCleanup(@()fclose(f));
 if k==1
  for j=1:numel(s.drivers),d=s.drivers(j);fprintf(f,'%s (%d,%d) %s\n',d.username,d.x,d.y,d.category);end
 else
  if k==2,orders=s.active;else,orders=s.completed;end
  for j=1:numel(orders),o=orders(j);fprintf(f,'%s (%d,%d) (%d,%d) %s\n',o.category,o.start,o.finish,o.username);end
 end
 clear c;[ok,message]=movefile(temp,fullfile(directory,names{k}),'f');assert(ok,message);
end
end


