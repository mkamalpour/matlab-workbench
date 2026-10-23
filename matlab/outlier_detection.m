function r = outlier_detection(values)
% Manual Tukey fences; original one-based indices survive NaN removal.
validateattributes(values,{'numeric'},{'real','vector'});
v=values(:); assert(~any(isinf(v)),'Infinite values are not supported');
a=v(~isnan(v)); assert(~isempty(a),'No finite observations');
[q1,q3]=computeQuartiles(a);
spread=q3-q1; low=q1-1.5*spread; high=q3+1.5*spread;
mask=detectOutliers(v,low,high);
r=struct('q1',q1,'q3',q3,'iqr',spread,'lower',low,'upper',high,...
 'row_index',find(mask),'values',v(mask),'clean_values',v(~isnan(v)),'removed_count',sum(isnan(v)));
end
function [q1,q3]=computeQuartiles(a)
s=bubbleSort(a); n=numel(s);
if n==1, q1=s(1); q3=s(1); else
 h=floor(n/2); q1=middle(s(1:h)); q3=middle(s(end-h+1:end));
end
end
function mask=detectOutliers(v,low,high)
mask=v<low|v>high;
end
function s=bubbleSort(s)
for last=numel(s):-1:2
 changed=false;
 for j=1:last-1
  if s(j)>s(j+1), t=s(j); s(j)=s(j+1); s(j+1)=t; changed=true; end
 end
 if ~changed, break; end
end
end
function m=middle(a)
n=numel(a); if mod(n,2), m=a((n+1)/2); else, m=(a(n/2)+a(n/2+1))/2; end
end


