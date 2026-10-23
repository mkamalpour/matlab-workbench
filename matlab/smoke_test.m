function smoke_test()
% Native toolbox-free smoke checks. Run in MATLAB; does not write files.
r=outlier_detection([NaN 1 2 3 4 5 6 7 100]);assert(r.row_index==9&&r.removed_count==1);
[s,~]=transport_system();[s,~]=transport_system(s,'ADD-DRIVER ali (0,0) BIKE');
[s,~]=transport_system(s,'CREATE-ORDER BIKE (1,1) (3,4)');
[s,~]=transport_system(s,'RECIEVE-ORDER (1,1) (3,4) ali');
text=transport_json(s);assert(contains(text,'"drivers":[{'),'Drivers must encode as JSON array');
s=validate_transport_state(jsondecode(text));assert(s.drivers(1).x==3&&isempty(s.active)&&numel(s.completed)==1);
a=(1:12)';data=table(20+a,10+a,1000+10*a,'VariableNames',{'MPG','Acceleration','Weight'});
r=mpg_prediction(data,1:9);p=mpg_predict(r,data(10:12,:));assert(max(abs(p-r.predicted))<1e-10);
o=struct('plots',false,'taps',4);t=(0:99)'/8000;clean=sin(2*pi*440*t);reference=cos(2*pi*123*t);
r=AudioNoiseCancellation(clean+.3*reference,reference,8000,clean,o);assert(all(isfinite(r.NLMS.cleaned)));
fprintf('Native smoke checks passed.\n');
end

