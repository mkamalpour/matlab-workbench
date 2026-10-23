function r=AudioNoiseCancellation(noisy,reference,fs,clean,options)
% Toolbox-free LMS/NLMS/RLS comparison. No argument runs reproducible demo.
% options: taps,lms_step,nlms_step,forgetting,delta,plots.
if nargin==0
 fs=8000; t=(0:fs-1)'/fs; clean=.3*sin(2*pi*440*t)+.15*sin(2*pi*880*t);
 rng(42); reference=randn(fs,1); noise=filter([.8 .3 -.2],1,reference);
 factor=sqrt(mean(clean.^2)/(10^.5*mean(noise.^2)));
 reference=reference*factor; noisy=clean+noise*factor;
end
if nargin<4 && nargin~=0,clean=[];end
if nargin<5,options=struct;end
options=defaults(options); noisy=noisy(:);reference=reference(:);clean=clean(:);
validateattributes(noisy,{'double'},{'real','finite','nonempty'});
validateattributes(reference,{'double'},{'real','finite','numel',numel(noisy)});
validateattributes(fs,{'numeric'},{'scalar','positive','integer'});
assert(isempty(clean)||numel(clean)==numel(noisy),'Clean signal length mismatch');
assert(all(isfinite(clean)),'Invalid clean signal');
validateattributes(options.taps,{'numeric'},{'scalar','integer','>=',1,'<=',256});
assert(options.taps<=numel(noisy),'More taps than samples');
assert(isempty(clean)||sum(clean.^2)>0,'Clean reference must have positive power');
assert(isscalar(options.lms_step)&&options.lms_step>0&&isfinite(options.lms_step),'Invalid LMS step');
assert(isscalar(options.nlms_step)&&options.nlms_step>0&&options.nlms_step<2,'NLMS step must be in (0,2)');
assert(isscalar(options.forgetting)&&isscalar(options.delta)&&isfinite(options.forgetting)&&isfinite(options.delta)&&options.forgetting>0&&options.forgetting<=1&&options.delta>0,'Invalid RLS parameters');
names={'LMS','NLMS','RLS'}; r=struct('fs',fs,'noisy',noisy,'reference',reference,'clean',clean);
for k=1:3
 tic;
 switch names{k}
 case 'LMS', [e,w]=lms(noisy,reference,options.taps,options.lms_step);
 case 'NLMS', [e,w]=nlms(noisy,reference,options.taps,options.nlms_step);
 case 'RLS', [e,w]=rls(noisy,reference,options.taps,options.forgetting,options.delta);
 end
 elapsed=toc; assert(all(isfinite(e))&&all(isfinite(w)),'Filter diverged; reduce step');
 o=struct('cleaned',e,'weights',w,'estimated_noise',noisy-e,'seconds',elapsed,'mse',NaN,'snr_db',NaN,'snr_gain_db',NaN);
 if ~isempty(clean)
 o.mse=mean((clean-e).^2);o.snr_db=quality(clean,e);o.snr_gain_db=o.snr_db-quality(clean,noisy);
 end
 r.(names{k})=o;
end
if nargout==0
 fprintf('Algorithm Seconds MSE SNR_dB Gain_dB\n');
 for j=1:3,o=r.(names{j});fprintf('%s %.6g %.6g %.6g %.6g\n',names{j},o.seconds,o.mse,o.snr_db,o.snr_gain_db);end
end
if options.plots
 figure('Name','Adaptive cancellation: waveforms and learning');t=(0:numel(noisy)-1)'/fs;
 for k=1:3
  o=r.(names{k});subplot(3,2,2*k-1);plot(t,noisy,'Color',[.75 .75 .75]);hold on;plot(t,o.cleaned);title(names{k});xlabel('Seconds');ylabel('Amplitude');
  subplot(3,2,2*k);
  if isempty(clean),plot(t,movmean(o.cleaned.^2,100));title('Output power (not ground-truth error)');
  else,plot(t,movmean((o.cleaned-clean).^2,100));title('Smoothed squared reconstruction error');end
  xlabel('Seconds');grid on;
 end
 figure('Name','One-sided periodogram');
 signals={noisy,r.LMS.cleaned,r.NLMS.cleaned,r.RLS.cleaned}; labels={'Noisy','LMS','NLMS','RLS'};
 for k=1:4,subplot(2,2,k);periodogramPlot(signals{k},fs);title(labels{k});end
end
end
function o=defaults(o)
d=struct('taps',16,'lms_step',.01,'nlms_step',.2,'forgetting',.995,'delta',1,'plots',true);
f=fieldnames(d);for j=1:numel(f),if ~isfield(o,f{j}),o.(f{j})=d.(f{j});end,end
end
function [e,w]=lms(d,r,m,mu)
w=zeros(m,1);x=w;e=zeros(size(d));
for n=1:numel(d),x=[r(n);x(1:end-1)];e(n)=d(n)-w'*x;w=w+mu*e(n)*x;end
end
function [e,w]=nlms(d,r,m,mu)
w=zeros(m,1);x=w;e=zeros(size(d));
for n=1:numel(d),x=[r(n);x(1:end-1)];e(n)=d(n)-w'*x;w=w+mu*e(n)*x/(1e-12+x'*x);end
end
function [e,w]=rls(d,r,m,lambda,delta)
w=zeros(m,1);x=w;e=zeros(size(d));P=eye(m)/delta;
for n=1:numel(d)
 x=[r(n);x(1:end-1)];px=P*x;g=px/(lambda+x'*px);e(n)=d(n)-w'*x;w=w+g*e(n);P=(P-g*(x'*P))/lambda;P=(P+P')/2;
end
end
function q=quality(c,y)
a=sum(c.^2);b=sum((c-y).^2);q=10*log10(a/b);
end
function periodogramPlot(x,fs)
n=numel(x);p=abs(fft(x)).^2/(fs*n);p=p(1:floor(n/2)+1);
if rem(n,2)==0,p(2:end-1)=2*p(2:end-1);else,p(2:end)=2*p(2:end);end
plot((0:numel(p)-1)*fs/n,10*log10(p+realmin));xlabel('Hz');ylabel('dB/Hz');grid on;
end

