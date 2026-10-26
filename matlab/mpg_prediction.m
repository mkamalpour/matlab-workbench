function r=mpg_prediction(data,train_indices)
% Train-only imputation, inverse features and sample-standardized OLS.
% Explicit one-based indices refer to original source rows before dropping missing MPG.
assert(istable(data),'Supply table with MPG, Acceleration and Weight');
ids=find(~isnan(data.MPG));data=data(ids,:); y=data.MPG; x=[data.Acceleration data.Weight];
assert(all(isfinite(y)) && all(y>0),'Observed MPG must be positive and finite');
assert(~any(isinf(x(:))),'Infinite predictors');
assert(all(x(~isnan(x))>0),'Predictors must be positive');
n=height(data); assert(n>=8,'At least eight rows required');
if nargin<2, rng(42); p=randperm(n); train_indices=p(1:floor(.8*n+.5)); end
if nargin>=2,[found,tr]=ismember(train_indices(:),ids);assert(all(found),'Invalid original row IDs');else,tr=train_indices(:);end; assert(numel(unique(tr))==numel(tr)&&all(tr>=1&tr<=n)&numel(tr)>=5,'Invalid split');
te=setdiff((1:n)',tr); assert(~isempty(te),'Need test rows');
mu=zeros(1,2);
for j=1:2
 a=x(tr,j); a=a(~isnan(a)); assert(~isempty(a),'Training predictor entirely missing');
 mu(j)=mean(a); x(isnan(x(:,j)),j)=mu(j);
end
invx=1./x; invmean=mean(invx(tr,:),1); z=[x invx./invmean];
center=mean(z(tr,:),1); scale=std(z(tr,:),0,1); scale(scale==0)=1;
z=(z-center)./scale; design=[ones(n,1) z]; beta=pinv(design(tr,:))*y(tr);
pred=design(te,:)*beta; err=y(te)-pred;
r=struct('coefficients',beta,'imputation',mu,'inverse_mean',invmean,'center',center,'scale',scale,...
 'train_indices',ids(tr),'test_indices',ids(te),'actual',y(te),'predicted',pred,'rmse',sqrt(mean(err.^2)),'mae',mean(abs(err)));
sst=sum((y(te)-mean(y(te))).^2); if sst==0,r.r2=NaN;else,r.r2=1-sum(err.^2)/sst;end
end


