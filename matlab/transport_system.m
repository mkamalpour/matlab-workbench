function [s,message]=transport_system(s,command)
% Functional state updates: a rejected command leaves caller state untouched.
if nargin==0,s=struct('drivers',struct('username',{},'x',{},'y',{},'category',{}),'active',struct('order_id',{},'username',{},'category',{},'start',{},'finish',{}),'completed',struct('order_id',{},'username',{},'category',{},'start',{},'finish',{}),'next_order_id',1,'version',1);message='Ready';return;end
s=validate_transport_state(s);
coord='\(\s*([+-]?\d+)\s*,\s*([+-]?\d+)\s*\)';
t=regexpi(strtrim(command),['^ADD-DRIVER\s+([A-Za-z0-9_-]{1,64})\s+' coord '\s+(BIKE|VAN|TRUCK)$'],'tokens','once');
if ~isempty(t)
 assert(~any(strcmp({s.drivers.username},t{1})),'Driver already exists');
 assert(all(isfinite([str2double(t{2}) str2double(t{3})]) & abs([str2double(t{2}) str2double(t{3})])<=1e9),'Coordinates must be finite');
 s.drivers(end+1)=struct('username',t{1},'x',str2double(t{2}),'y',str2double(t{3}),'category',upper(t{4}));message='Driver added';return;
end
t=regexpi(strtrim(command),['^CREATE-ORDER\s+(BIKE|VAN|TRUCK)\s+' coord '\s+' coord '$'],'tokens','once');
if ~isempty(t)
 start=[str2double(t{2}) str2double(t{3})];finish=[str2double(t{4}) str2double(t{5})];
 assert(all(isfinite([start finish])&abs([start finish])<=1e9),'Coordinates must be finite');
 candidates=find(strcmp({s.drivers.category},upper(t{1}))&~ismember({s.drivers.username},{s.active.username}));assert(~isempty(candidates),'No available driver');
 [~,p]=sort({s.drivers(candidates).username});candidates=candidates(p);dist=zeros(size(candidates));
 for j=1:numel(candidates),d=s.drivers(candidates(j));dist(j)=abs(d.x-start(1))+abs(d.y-start(2));end
 [~,p]=min(dist);d=s.drivers(candidates(p));
 o=struct('order_id',s.next_order_id,'username',d.username,'category',upper(t{1}),'start',start,'finish',finish);
 s.active(end+1)=o;s.next_order_id=s.next_order_id+1;message=['Assigned ' d.username];return;
end
t=regexpi(strtrim(command),['^REC(EI|IE)VE-ORDER\s+' coord '\s+' coord '\s+([A-Za-z0-9_-]{1,64})$'],'tokens','once');
if ~isempty(t)
 start=[str2double(t{2}) str2double(t{3})];finish=[str2double(t{4}) str2double(t{5})];idx=[];
 for j=1:numel(s.active),o=s.active(j);if strcmp(o.username,t{6})&&isequal(o.start,start)&&isequal(o.finish,finish),idx=j;break;end,end
 assert(~isempty(idx),'No matching active order');o=s.active(idx);s.completed(end+1)=o;s.active(idx)=[];
 d=find(strcmp({s.drivers.username},o.username));s.drivers(d).x=finish(1);s.drivers(d).y=finish(2);message='Order completed';return;
end
if strcmpi(strtrim(command),'Exit'),message='Session retained';return;end
error('Unknown command. See README for grammar.');
end




