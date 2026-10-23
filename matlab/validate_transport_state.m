function s=validate_transport_state(s)
% Validate untrusted JSON snapshots before assigning simulator state.
assert(isstruct(s)&&isscalar(s),'Snapshot must be an object');
required={'version','drivers','active','completed','next_order_id'};
assert(all(isfield(s,required))&&isscalar(s.version)&&s.version==1,'Unsupported snapshot');
assert(isnumeric(s.next_order_id)&&isscalar(s.next_order_id)&&isfinite(s.next_order_id)&&s.next_order_id>=1&&fix(s.next_order_id)==s.next_order_id,'Invalid next order ID');
dfields={'username','x','y','category'};ofields={'order_id','username','category','start','finish'};
if isempty(s.drivers),s.drivers=struct('username',{},'x',{},'y',{},'category',{});end
for j=1:numel(s.drivers)
 d=s.drivers(j);assert(all(isfield(d,dfields)),'Invalid driver');checkName(d.username);checkCategory(d.category);assert(isscalar(d.x)&&isscalar(d.y),'Driver coordinates must be scalar');checkCoord([d.x d.y]);
end
s.drivers=orderfields(s.drivers,dfields);
assert(numel(unique({s.drivers.username}))==numel(s.drivers),'Duplicate driver');
ids=[];
for field={'active','completed'}
 k=field{1};
 if isempty(s.(k)),s.(k)=struct('order_id',{},'username',{},'category',{},'start',{},'finish',{});end
 assert(isstruct(s.(k)),'Orders must be objects');
 s.(k)=orderfields(s.(k),ofields);
 for j=1:numel(s.(k))
  o=s.(k)(j);assert(all(isfield(o,ofields)),'Invalid order');checkName(o.username);checkCategory(o.category);checkCoord(o.start);checkCoord(o.finish);s.(k)(j).start=reshape(o.start,1,2);s.(k)(j).finish=reshape(o.finish,1,2);
  assert(isscalar(o.order_id)&&isfinite(o.order_id)&&o.order_id>=1&&fix(o.order_id)==o.order_id,'Invalid order ID');ids(end+1)=o.order_id;
  d=find(strcmp({s.drivers.username},o.username));assert(numel(d)==1&&strcmp(s.drivers(d).category,o.category),'Invalid order driver');
 end
end
assert(numel(unique(ids))==numel(ids)&&all(ids<s.next_order_id),'Duplicate or future order ID');
assert(numel(unique({s.active.username}))==numel(s.active),'Driver is double booked');
end
function checkName(v)
assert(ischar(v)&&~isempty(regexp(v,'^[A-Za-z0-9_-]{1,64}$','once')),'Invalid username');
end
function checkCategory(v)
assert(ischar(v)&&any(strcmp(v,{'BIKE','VAN','TRUCK'})),'Invalid category');
end
function checkCoord(v)
assert(isnumeric(v)&&numel(v)==2&&all(isfinite(v(:)))&&all(abs(v(:))<=1e9)&&all(fix(v(:))==v(:)),'Invalid coordinates');
end




