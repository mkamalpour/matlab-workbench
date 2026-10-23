function predictions=mpg_predict(model,data)
% Predict new rows using fitted training metadata; no refitting.
x=[data.Acceleration data.Weight];assert(~any(isinf(x(:)))&&all(x(~isnan(x))>0),'Invalid predictors');
for j=1:2,x(isnan(x(:,j)),j)=model.imputation(j);end
features=[x (1./x)./model.inverse_mean];
predictions=[ones(size(x,1),1) (features-model.center)./model.scale]*model.coefficients;
end
