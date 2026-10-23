function workbench()
% Native MATLAB coursework dashboard. No Python or optional toolbox needed.
f=uifigure('Name','MATLAB Workbench','Position',[80 80 1100 760]);
g=uigridlayout(f,[2 1]);g.RowHeight={55,'1x'};
uilabel(g,'Text','MATLAB Workbench | signals, data and simulation','FontSize',22,'FontWeight','bold');
tabs=uitabgroup(g); player=[];result=[];[state,~]=transport_system();
f.CloseRequestFcn=@closeApp;
a=uitab(tabs,'Title','Audio cancellation');ag=uigridlayout(a,[7 2]);ag.RowHeight={30,35,35,35,35,35,'1x'};
uilabel(ag,'Text','Compare LMS, NLMS and RLS. Demo or clean WAV + simulated correlated noise.');uilabel(ag,'Text','Ground truth metrics require clean audio.');
uibutton(ag,'Text','Run demo + comparison figures','ButtonPushedFcn',@demo);
uibutton(ag,'Text','Load clean WAV and compare','ButtonPushedFcn',@loadClean);
uibutton(ag,'Text','Load noisy + reference WAV','ButtonPushedFcn',@loadPair);
uibutton(ag,'Text','Load input MAT fixture','ButtonPushedFcn',@loadMat);
select=uidropdown(ag,'Items',{'LMS','NLMS','RLS'},'Value','NLMS');
uibutton(ag,'Text','Play selected output','ButtonPushedFcn',@playOutput);
uibutton(ag,'Text','Stop playback','ButtonPushedFcn',@stopPlayer);
uibutton(ag,'Text','Export selected output WAV','ButtonPushedFcn',@exportAudio);
status=uilabel(ag,'Text','Ready. Computation opens waveform, learning and PSD figures.');uilabel(ag,'Text','Export warns before scaling amplitudes beyond WAV range.');
metrics=uitable(ag);metrics.Layout.Column=[1 2];
b=uitab(tabs,'Title','Outliers');bg=uigridlayout(b,[3 1]);bg.RowHeight={60,35,'1x'};
values=uitextarea(bg,'Value',{'1,2,3,4,5,6,7,100'});uibutton(bg,'Text','Detect outliers','ButtonPushedFcn',@outliers);out=uitextarea(bg,'Editable','off');
c=uitab(tabs,'Title','Transport');cg=uigridlayout(c,[6 1]);cg.RowHeight={55,35,35,35,35,'1x'};
uilabel(cg,'Text','ADD-DRIVER ali (0,0) BIKE | CREATE-ORDER BIKE (1,1) (3,4) | RECEIVE-ORDER (1,1) (3,4) ali','WordWrap','on');
command=uieditfield(cg,'text','Value','ADD-DRIVER ali (0,0) BIKE');uibutton(cg,'Text','Execute command','ButtonPushedFcn',@execute);uibutton(cg,'Text','Import validated snapshot JSON','ButtonPushedFcn',@importState);uibutton(cg,'Text','Export snapshot JSON','ButtonPushedFcn',@exportState);log=uitextarea(cg,'Editable','off');
d=uitab(tabs,'Title','MPG prediction');dg=uigridlayout(d,[4 1]);dg.RowHeight={60,35,35,'1x'};
uilabel(dg,'Text','Load a CSV with MPG, Acceleration and Weight. Missing predictors use training means only. Positive predictors required.','WordWrap','on');
uibutton(dg,'Text','Load CSV and train baseline','ButtonPushedFcn',@mpg);uibutton(dg,'Text','Train on optional installed carbig data','ButtonPushedFcn',@carbigDemo);report=uitextarea(dg,'Editable','off');
    function demo(~,~)
        try,result=AudioNoiseCancellation();showMetrics();catch e,uialert(f,e.message,'Audio error');end
    end
    function loadClean(~,~)
        [p,q]=uigetfile('*.wav');if isequal(p,0),return;end
        try
            [clean,fs]=audioread(fullfile(q,p));clean=mean(clean,2);rng(42);ref=randn(size(clean));noise=filter([.8 .3 -.2],1,ref);
            factor=sqrt(mean(clean.^2)/(10^.5*mean(noise.^2)));assert(isfinite(factor)&&factor>0,'Clean audio must have nonzero power');
            candidate=AudioNoiseCancellation(clean+factor*noise,factor*ref,fs,clean);result=candidate;showMetrics();
        catch e,uialert(f,e.message,'Load failed');end
    end
    function loadPair(~,~)
        [p,q]=uigetfile('*.wav','Select noisy WAV');if isequal(p,0),return;end
        [v,w]=uigetfile('*.wav','Select reference noise WAV');if isequal(v,0),return;end
        try
            [n,fs]=audioread(fullfile(q,p));[r,fr]=audioread(fullfile(w,v));assert(fs==fr,'Sample rates must match');
            candidate=AudioNoiseCancellation(mean(n,2),mean(r,2),fs,[]);result=candidate;showMetrics();
        catch e,uialert(f,e.message,'Load failed');end
    end
    function loadMat(~,~)
        [p,q]=uigetfile('*.mat');if isequal(p,0),return;end
        try
            v=load(fullfile(q,p));if ~isfield(v,'clean'),v.clean=[];end
            options=struct;keys={'taps','lms_step','nlms_step','forgetting','delta'};
            for j=1:numel(keys),if isfield(v,keys{j}),options.(keys{j})=v.(keys{j});end,end
            candidate=AudioNoiseCancellation(v.noisy,v.reference,v.fs,v.clean,options);result=candidate;showMetrics();
        catch e,uialert(f,e.message,'Invalid fixture');end
    end
    function showMetrics()
        names={'LMS','NLMS','RLS'};rows=cell(3,5);
        for k=1:3,o=result.(names{k});rows(k,:)={names{k},o.seconds,o.mse,o.snr_db,o.snr_gain_db};end
        metrics.Data=rows;metrics.ColumnName={'Algorithm','Seconds','MSE','SNR dB','Gain dB'};status.Text='Computed. NaN metrics mean clean ground truth is unavailable.';
    end
    function playOutput(~,~)
        if isempty(result),return;end
        stopPlayer();x=result.(select.Value).cleaned;
        if max(abs(x))>1,uialert(f,'Playback may clip. Export can scale explicitly.','Amplitude warning');end
        player=audioplayer(x,result.fs);play(player);
    end
    function stopPlayer(varargin)
        if ~isempty(player),stop(player);player=[];end
    end
    function exportAudio(~,~)
        if isempty(result),return;end
        x=result.(select.Value).cleaned;
        if max(abs(x))>1
            answer=uiconfirm(f,'Scale output to avoid clipping?','Export amplitude','Options',{'Scale','Cancel'},'DefaultOption',2);
            if ~strcmp(answer,'Scale'),return;end;x=x/max(abs(x));
        end
        [p,q]=uiputfile('*.wav');if isequal(p,0),return;end
        try,audiowrite(fullfile(q,p),x,result.fs);catch e,uialert(f,e.message,'Export failed');end
    end
    function outliers(~,~)
        try
            text=strjoin(values.Value,' ');tokens=regexp(strtrim(text),'[,;\s]+','split');v=str2double(tokens);
            assert(all(~isnan(v)|strcmpi(tokens,'nan')),'Use numbers separated by commas or spaces');r=outlier_detection(v);
            out.Value={sprintf('Q1 %.6g | Q3 %.6g | IQR %.6g',r.q1,r.q3,r.iqr),sprintf('Fences [%.6g, %.6g]',r.lower,r.upper),['Original row indices: ' mat2str(r.row_index')],['Outlier values: ' mat2str(r.values')]};
        catch e,uialert(f,e.message,'Invalid input');end
    end
    function execute(~,~)
        try,[candidate,msg]=transport_system(state,command.Value);state=candidate;log.Value={msg,transport_json(state)};catch e,uialert(f,e.message,'Command rejected');end
    end
    function importState(~,~)
        [p,q]=uigetfile('*.json');if isequal(p,0),return;end
        try
            candidate=validate_transport_state(jsondecode(fileread(fullfile(q,p))));
            answer=uiconfirm(f,'Replace current simulator state with this snapshot?','Restore snapshot','Options',{'Replace','Cancel'},'DefaultOption',2);
            if strcmp(answer,'Replace'),state=candidate;log.Value={transport_json(state)};end
        catch e,uialert(f,e.message,'Invalid snapshot');end
    end
    function exportState(~,~)
        [p,q]=uiputfile('*.json');if isequal(p,0),return;end
        try
            h=fopen(fullfile(q,p),'w');assert(h~=-1,'Cannot write snapshot');cleanup=onCleanup(@()fclose(h));fprintf(h,'%s',transport_json(state));
        catch e,uialert(f,e.message,'Export failed');end
    end
    function mpg(~,~)
        [p,q]=uigetfile('*.csv');if isequal(p,0),return;end
        try,r=mpg_prediction(readtable(fullfile(q,p)));report.Value={sprintf('Test RMSE %.6g | MAE %.6g | R2 %.6g',r.rmse,r.mae,r.r2),['Coefficients: ' mat2str(r.coefficients')],['Train rows: ' mat2str(r.train_indices')],['Test rows: ' mat2str(r.test_indices')]};catch e,uialert(f,e.message,'Training failed');end
    end
    function carbigDemo(~,~)
        try
            v=load('carbig','MPG','Acceleration','Weight');r=mpg_prediction(table(v.MPG,v.Acceleration,v.Weight,'VariableNames',{'MPG','Acceleration','Weight'}));
            report.Value={sprintf('carbig held-out RMSE %.6g | MAE %.6g | R2 %.6g',r.rmse,r.mae,r.r2)};
        catch e,uialert(f,['Install the optional carbig example dataset, or load your CSV. ' e.message],'Dataset unavailable');end
    end
    function closeApp(~,~)
        stopPlayer();delete(f);
    end
end





